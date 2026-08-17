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
import os
import sys
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
        if not slack.notify(entete + texte):
            log.warning("Rapport WordPress de %s non pris en charge — laissé sur place.", heure)
            break
        pris_ids.append(mid)
        pris += 1

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
