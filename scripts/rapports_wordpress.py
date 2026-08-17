#!/usr/bin/env python3
"""Rapatrie les rapports que WORDPRESS tient en réserve, dans la boîte du jour du VPS.

D'OÙ ÇA VIENT — 2026-08-17, Franck : « j'ai trop de messages dans slack. les messages ne
doivent arriver uniquement dans la chaîne #agendasabauda et non pas dans formulaire. »

Cinq rapports par jour arrivaient dans #formulaire : quatre audits quotidiens écrits en
Code Snippets (doctrine éditoriale, garde-fous dates/sources, garde-fous panel/formes/
lieux, fraîcheur des guides) et les refus de publication de `cs-completude.php`. Tous
appelaient `cs_slack_notify_form()`, une fonction dont le webhook était VOLONTAIREMENT
réservé aux formulaires publics — « une soumission de spam ne doit jamais polluer le
canal opérationnel ». Le canal prévu pour le bruit du public recevait donc les seuls
messages qui demandaient une décision, dont le refus de la fiche #7686 (source
officielle manquante).

POURQUOI ON TIRE, PLUTÔT QUE WORDPRESS QUI POUSSE. La réponse évidente était de mettre le
webhook de #agendasabauda dans une option WordPress. Franck l'a refusée le jour même :
« Mais tu publies déjà dans ce canal. Pourquoi je devrais te donner de nouveau le
webhook ? » — et il a raison. Ce secret vit dans le `.env` du VPS, dont ce pipeline se
sert chaque jour ; le recopier dans la base WordPress ferait DEUX copies à révoquer, sur
un site public, pour un problème qui n'est que d'acheminement. Le pipeline sait déjà
parler à WordPress (même authentification que la publication). C'est donc lui qui vient
chercher, et les rapports WordPress finissent DANS son récapitulatif : un canal, un
message, aucun secret déplacé.

CE QUI DÉCIDE DU SUCCÈS : `slack.notify` renvoie True quand le message est PRIS EN CHARGE
(rangé dans la boîte du jour, ou posté si SLACK_DIGEST n'est pas actif). On ne supprime
côté WordPress que ce qui a été pris en charge, et jamais plus loin que le dernier message
LU — un rapport écrit entre le GET et le DELETE ne doit pas disparaître sans avoir servi.

JAMAIS BLOQUANT. Ce script est appelé par `scripts.slack_digest` avant le vidage : si
WordPress est injoignable, si les identifiants manquent ou si la route n'est pas encore
déployée, on loggue et on rend (0, 0). Le récapitulatif du matin doit partir de toute
façon — c'est le seul message de la matinée.

CÔTÉ WORDPRESS : `deploy/wordpress/cs-slack-formulaires.php` (route cs/v1/slack-boite).
Ce fichier reprend la parole tout seul, sur son propre webhook, si PERSONNE ne vient
vider sa boîte pendant 26 h — donc si ce script cesse de tourner, les rapports
réapparaissent dans #formulaire au lieu de dormir. C'est volontaire : un message mal
rangé se voit, une file silencieuse non (règle 3).

Usage :
    .venv/bin/python -m scripts.rapports_wordpress            # récupère et vide
    .venv/bin/python -m scripts.rapports_wordpress --voir     # montre, ne touche à rien
"""
from __future__ import annotations
import argparse
import base64
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import slack  # noqa: E402
from utils.logger import get_logger  # noqa: E402

log = get_logger("rapports_wordpress")

_UA = {"User-Agent": "agenda-sabauda-backoffice/1.0"}
_ROUTE = "/?rest_route=/cs/v1/slack-boite"

# ══ LA TENDANCE, PARCE QUE « DE MOINS EN MOINS » NE SE PROMET PAS ═══════════════════
#
# Franck, 2026-08-17 : « J'aimerais que les messages slack d'erreur soient de moins en
# moins. » C'est le bon objectif, et il ne se tient pas par bonne volonté : un rapport
# quotidien qui affiche « 18 points » ne dit pas s'il y en avait 25 hier ou 12. Sans
# comparaison, personne — ni lui, ni moi la semaine prochaine — ne sait si le dispositif
# s'assainit ou s'enfonce, et une file qui stagne finit par ne plus être lue.
#
# On garde donc, par rapport, le NOMBRE DE POINTS SIGNALÉS chaque jour, et on l'affiche
# à côté du nombre du jour. Trois usages, dans l'ordre d'utilité :
#   • voir la baisse quand elle a lieu (c'est la demande) ;
#   • voir la HAUSSE tout de suite, au lieu de la découvrir trois semaines plus tard ;
#   • voir ce qui NE BOUGE PAS. Un point signalé quinze jours de suite n'est pas une
#     alerte, c'est une décision qui n'a pas été prise — ou un contrôle qui se rejoue
#     sur la même matière, ce que CLAUDE.md (règle 3) interdit précisément.
#
# Ce n'est qu'un COMPTEUR DE LIGNES, et il le dit : il compare des rapports, pas des
# fiches, et deux fiches réparées le même jour qu'une nouvelle apparaît donnent un
# nombre identique. Il désigne une direction, il ne remplace pas la lecture du rapport.
_HISTO = ROOT / "logs" / "tendance_wordpress.json"
_HISTO_JOURS = 30  # au-delà, la comparaison n'apprend plus rien et le fichier gonfle


def _wp() -> tuple[str, tuple[str, str]] | None:
    """(url, auth) du site Agenda Sabauda, ou None si non configuré."""
    load_dotenv(ROOT / ".env")
    url = (os.getenv("WP_AS_URL") or "").rstrip("/")
    user = os.getenv("WP_AS_USER") or ""
    mdp = os.getenv("WP_AS_APP_PASSWORD") or ""
    if not (url and user and mdp):
        log.info("WP_AS_URL/USER/APP_PASSWORD absents — rien à récupérer.")
        return None
    return url, (user, mdp)


def _headers(auth: tuple[str, str]) -> dict:
    """X-CS-Auth : secours quand l'hébergeur supprime l'en-tête Authorization
    (même mécanisme que scripts/publisher_as.py, lu par cs-rest-auth.php)."""
    jeton = base64.b64encode(f"{auth[0]}:{auth[1]}".encode("utf-8")).decode("ascii")
    return {**_UA, "X-CS-Auth": jeton}


def cle_rapport(texte: str) -> str:
    """Identifiant stable d'un rapport : son titre, sans emoji ni gras.

    Le titre est ce qui ne change pas d'un jour à l'autre, alors que le corps change
    tous les jours. Si un audit est renommé, sa série repart de zéro et le rapport le
    DIT (« premier relevé ») plutôt que de comparer deux choses différentes.
    """
    premiere = (texte or "").strip().splitlines()[0] if (texte or "").strip() else ""
    nue = re.sub(r":[a-z0-9_+-]+:", " ", premiere)      # :shield:, :triangular_ruler:…
    nue = nue.replace("*", " ").replace("_", " ")
    return re.sub(r"\s+", " ", nue).strip().lower()


def compter_points(texte: str) -> int:
    """Nombre de POINTS signalés : les lignes du rapport qui commencent par `*`.

    C'est la forme que ces audits donnent à chaque constat (`*troncature* : 11 -> …`).
    La ligne de titre et la mention de périmètre n'en sont pas et ne comptent pas.
    """
    return sum(1 for l in (texte or "").splitlines() if l.strip().startswith("*"))


def tendance(cle: str, n: int, histo: dict, aujourdhui: str) -> str:
    """Phrase de tendance à coller sous un rapport. `histo` est modifié (jour enregistré).

    Fonction PURE hormis l'écriture dans `histo` : elle ne lit ni fichier ni horloge, pour
    qu'une fixture puisse la mettre à l'épreuve sur des séries choisies (voir
    tests/test_tendance_wordpress.py).

    RÈGLE 6 — un « 0 » doit dire d'où il vient. Le premier relevé d'une série l'annonce au
    lieu de laisser croire à une baisse : sans historique, « 0 point » et « rien mesuré »
    ont exactement la même tête.
    """
    jours = histo.setdefault(cle, {})
    veille = {j: v for j, v in jours.items() if j < aujourdhui}
    jours[aujourdhui] = n
    # On ne garde qu'une fenêtre glissante.
    for vieux in sorted(jours)[:-_HISTO_JOURS]:
        del jours[vieux]

    if not veille:
        return f"_{n} point(s) signalé(s). Premier relevé : rien à comparer encore._"

    dernier_jour = max(veille)
    precedent = veille[dernier_jour]
    serie = [veille[j] for j in sorted(veille)][-7:]
    plus_ancien = serie[0]

    if n < precedent:
        sens = "en baisse"
    elif n > precedent:
        sens = "EN HAUSSE"
    else:
        sens = "inchangé"
    phrase = (f"_{n} point(s) signalé(s), {sens} — {precedent} au relevé précédent "
              f"({dernier_jour}), {plus_ancien} il y a {len(serie)} relevé(s)._")

    # Ce qui ne bouge pas est le vrai sujet : ni une alerte, ni un progrès.
    stables = [j for j in sorted(veille, reverse=True) if veille[j] == n]
    if len(stables) >= 5 and n > 0:
        phrase += (f"\n_Ce nombre n'a pas bougé depuis {len(stables)} relevés : ce ne sont "
                   f"plus des alertes, c'est une décision en attente (les faire corriger, "
                   f"ou les taire explicitement)._")
    return phrase


def _charger_histo() -> dict:
    try:
        return json.loads(_HISTO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _enregistrer_histo(histo: dict) -> None:
    """Jamais bloquant : une tendance non enregistrée ne doit pas retenir un rapport."""
    try:
        _HISTO.parent.mkdir(parents=True, exist_ok=True)
        _HISTO.write_text(json.dumps(histo, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as exc:
        log.warning("Tendance non enregistrée (%s) — les rapports partent quand même.", exc)


def collecter(vider: bool = True) -> tuple[int, int]:
    """Range les rapports WordPress dans la boîte du jour.

    Renvoie (nombre lu sur WordPress, nombre confirmé retiré de WordPress).
    RÈGLE 6 : deux nombres et pas un seul, parce qu'ils peuvent différer — et
    quand ils diffèrent, c'est ça qu'il faut voir.
    """
    cfg = _wp()
    if not cfg:
        return 0, 0
    url, auth = cfg
    try:
        r = requests.get(f"{url}{_ROUTE}", auth=auth, headers=_headers(auth), timeout=20)
        if r.status_code == 404:
            log.warning("Route cs/v1/slack-boite absente (404) — mu-plugin "
                        "cs-slack-formulaires.php pas encore déployé ?")
            return 0, 0
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as exc:
        log.warning("Rapports WordPress non récupérés (%s) — le récapitulatif part sans eux.", exc)
        return 0, 0

    messages = data.get("messages") or []
    if not messages:
        log.info("Aucun rapport en attente sur WordPress (passage enregistré).")
        return 0, 0

    # On range un par un et on collectionne les IDENTIFIANTS de ceux qui sont
    # réellement pris en charge — jamais une borne d'horodatage. Les timestamps
    # WordPress sont à la seconde, et quatre audits lancés par le même cron
    # naissent dans la même seconde : une borne effacerait un rapport écrit
    # après la lecture. Éprouvé le 2026-08-17, la borne a perdu un message.
    histo = _charger_histo()
    aujourdhui = date.today().isoformat()
    pris_ids: list[str] = []   # à retirer de WordPress (postés OU vides)
    pris = 0                   # réellement ajoutés au récapitulatif
    for m in messages:
        mid = (m.get("id") or "").strip()
        texte = (m.get("texte") or "").strip()
        if not mid:
            # Sans identifiant, on ne peut pas le retirer proprement : on le
            # laisse plutôt que de risquer d'effacer le voisin.
            log.warning("Rapport WordPress sans identifiant — laissé sur place.")
            continue
        if not texte:
            pris_ids.append(mid)  # vide : rien à dire, mais à retirer de la file
            continue
        heure = m.get("heure") or ""
        entete = f"_(WordPress{', ' + heure if heure else ''})_\n"
        # La tendance est calculée sur une COPIE, et la série n'est mise à jour que si le
        # rapport est effectivement parti : un envoi manqué ne doit pas laisser un relevé
        # fantôme, sinon le lendemain se compare à un jour qui n'a jamais été affiché.
        provisoire = {k: dict(v) for k, v in histo.items()}
        suite = tendance(cle_rapport(texte), compter_points(texte), provisoire, aujourdhui)
        if not slack.notify(entete + texte + ("\n" + suite if suite else "")):
            log.warning("Rapport WordPress de %s non pris en charge — laissé sur place.", heure)
            break
        histo = provisoire
        pris_ids.append(mid)
        pris += 1

    if pris:
        _enregistrer_histo(histo)
    retires = 0
    if vider and pris_ids:
        try:
            d = requests.delete(f"{url}{_ROUTE}&ids={','.join(pris_ids)}", auth=auth,
                                headers=_headers(auth), timeout=20)
            d.raise_for_status()
            retires = int((d.json() or {}).get("supprimes") or 0)
        except (requests.RequestException, ValueError) as exc:
            # Pas dramatique : les mêmes rapports reviendront au prochain passage.
            # Un doublon dans le récapitulatif est moins grave qu'un rapport perdu.
            log.warning("Rapports non retirés de WordPress (%s) — ils reviendront.", exc)

    log.info("Rapports WordPress : %d lu(s), %d pris en charge, %d retiré(s).",
             len(messages), pris, retires)
    return pris, retires


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Rapatrie les rapports WordPress.")
    p.add_argument("--voir", action="store_true",
                   help="Montre ce qui attend sur WordPress, sans rien ranger ni retirer.")
    args = p.parse_args(argv)

    if args.voir:
        cfg = _wp()
        if not cfg:
            print("WP_AS_URL/USER/APP_PASSWORD absents — rien à lire.")
            return 0
        url, auth = cfg
        try:
            r = requests.get(f"{url}{_ROUTE}", auth=auth, headers=_headers(auth), timeout=20)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"Lecture impossible : {exc}")
            return 1
        msgs = data.get("messages") or []
        print(f"{len(msgs)} rapport(s) en attente sur WordPress :")
        for m in msgs:
            print(f"  {m.get('heure') or '?'} — {len(m.get('texte') or '')} caractères")
        return 0

    pris, retires = collecter()
    print(f"{pris} rapport(s) WordPress rangé(s) dans la boîte du jour, "
          f"{retires} retiré(s) de WordPress.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
