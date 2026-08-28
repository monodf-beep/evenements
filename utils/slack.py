#!/usr/bin/env python3
"""Notifications SLACK du backoffice (sortant) — signaux de la porte qualité.

Deux signaux, comme demandé par Franck :
  • « bon »     → l'agent a réussi à compléter l'événement, il est poussé en
                  brouillon sur Agenda Sabauda (message de confirmation) ;
  • « pas bon » → l'agent n'a PAS pu compléter : il manque des champs. On informe
                  Franck avec la LISTE précise des manques + un lien vers la fiche,
                  pour qu'il complète (dans le dashboard, ou en répondant l'info
                  qu'il aurait trouvée lui-même — cf. app route /slack/complete).

Transport : un simple Incoming Webhook Slack (une seule variable .env, révocable) :
    SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ

Jamais bloquant : si la variable manque ou l'appel échoue, on loggue et on continue
(la publication ne doit pas dépendre de Slack).
"""
from __future__ import annotations
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("slack")


def _depuis_les_tests() -> bool:
    """Vrai si l'appel vient d'un fichier de `tests/`.

    INCIDENT RÉEL, 2026-08-17 à 01h05 : « :rotating_light: chaîne morte » et « message
    ordinaire » sont apparus dans #agendasabauda. Aucune panne — c'était
    `tests/test_slack_digest.py` qui postait POUR DE VRAI. Cette fixture retire pourtant
    `SLACK_WEBHOOK_URL` de l'environnement avant de commencer ; seulement `_webhook()`
    rappelle `load_dotenv()` à chaque envoi, ce qui RÉINJECTE l'URL depuis le `.env`. Le
    garde-fou était défait par le code qu'il testait.

    Le danger a changé d'échelle le jour même : `scripts/auto_deploiement` lance TOUTES
    les fixtures sur le VPS avant chaque déploiement. Une fausse alerte « chaîne morte »
    serait donc partie chaque matin — exactement le message qu'on ne peut pas se
    permettre de crier au loup.

    POSÉ ICI, ET PAS DANS LES SEPT FIXTURES qui appellent `notify` : une seule d'entre
    elles se protégeait, et une fixture écrite demain n'y penserait pas. Même raisonnement
    que SLACK_DIGEST — le point de passage obligé est le bon endroit.
    """
    import inspect
    dossier = str(ROOT / "tests")
    try:
        for frame in inspect.stack()[1:12]:
            if str(frame.filename).startswith(dossier):
                return True
    except Exception:  # noqa: BLE001 — jamais bloquant
        pass
    return False


def _webhook() -> str:
    if _depuis_les_tests():
        # Transport coupé, logique intacte : `notify` prend exactement le chemin
        # « webhook absent », celui que les fixtures veulent éprouver.
        return ""
    load_dotenv(ROOT / ".env")
    return (os.getenv("SLACK_WEBHOOK_URL") or "").strip()


def enabled() -> bool:
    return bool(_webhook())


# ARCHIVE LOCALE DES MESSAGES — demandée deux fois par Franck (« les rapports sont bien
# sur Slack, mais j'aimerais qu'ils soient aussi stockés quelque part »), et la seconde
# fois le 2026-08-04 : « est-ce que tu stockes ces retours que j'ai de Slack ? »
#
# CE QUE ÇA CORRIGE, ET C'EST PLUS QUE DU CONFORT. Slack est le SEUL endroit où passent
# les constats quotidiens du pipeline — sections vides, fiches bloquées, anomalies du
# site. Personne ne peut les relire ensuite : ni un audit, ni une session qui reprend le
# projet, ni Franck lui-même trois semaines plus tard. Résultat observé le 2026-08-04 :
# des messages annonçaient depuis des jours « LES 7 PROCHAINS JOURS : 0 carte », et il a
# fallu qu'il recolle son fil à la main pour qu'on le voie.
#
# Un fichier par JOUR, en JSONL : on retrouve un message par sa date sans lire le reste, et
# ça s'ouvre avec n'importe quoi. Sous `logs/` (déjà gitignoré) parce que c'est un journal
# du serveur, pas du code — `rapports/` reste réservé à ce qu'on veut transmettre exprès.
#
# JAMAIS BLOQUANT, exactement comme l'envoi lui-même : si l'écriture échoue, on loggue et
# on continue. Une archive qui ferait tomber une publication serait pire que pas d'archive.
_ARCHIVE = ROOT / "logs" / "slack"
# Sentinelle FIGÉE, jamais réaffectée : sert à détecter qu'une fixture a — ou n'a PAS —
# redirigé `_ARCHIVE`/`_DIFFERES` vers un dossier jetable avant d'appeler `notify()`.
# Voir le garde-fou dans `notify()`, plus bas.
_ARCHIVE_PAR_DEFAUT = _ARCHIVE


def _archive(text: str, envoye: bool) -> None:
    """Écrit le message dans logs/slack/AAAA-MM-JJ.jsonl. `envoye` est conservé : un
    message qui n'est PAS parti est justement celui qu'on cherchera plus tard."""
    import json
    from datetime import datetime
    try:
        _ARCHIVE.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        ligne = json.dumps({"at": now.isoformat(timespec="seconds"),
                            "envoye": envoye, "texte": text}, ensure_ascii=False)
        with (_ARCHIVE / f"{now:%Y-%m-%d}.jsonl").open("a", encoding="utf-8") as f:
            f.write(ligne + "\n")
    except (OSError, ValueError) as exc:
        log.warning("Archive Slack non écrite (%s) — le message est parti quand même", exc)


# ══ LA BOÎTE DU JOUR ═══════════════════════════════════════════════════════════════
#
# « J'ai trop de messages par jour. Il m'en faut un ou deux, mais c'est tout. »
# — Franck, 2026-08-13, après une matinée à sept messages : agent quotidien (9h20), lot
# de publication (9h50), SEO (10h30), traduction (10h48), bilan du matin (11h12),
# contradicteur de dates (11h30), contradicteur de lieux (11h35).
#
# Aucun de ces messages n'était de trop PRIS SÉPARÉMENT : chacun disait quelque chose de
# vrai et d'utile. C'est leur NOMBRE qui les rend illisibles — et un canal illisible ne
# protège plus rien. Le 🔴 « 48 fiches que la base croit en ligne ne sont pas publiques »
# est arrivé en cinquième position ce matin-là, entre un rapport SEO et deux
# contradicteurs à zéro.
#
# POURQUOI ICI ET PAS DANS LES 22 SCRIPTS. `notify` est le seul passage obligé. Un
# réglage posé là vaut pour tout ce qui existe ET pour ce qu'on écrira demain — alors
# qu'un `--slack` retiré d'une ligne de crontab se réajoute sans qu'on s'en aperçoive,
# et qu'un script neuf naîtrait bavard.
#
# CE QUI NE DOIT PAS ATTENDRE PASSE QUAND MÊME : `notify(..., urgent=True)`. Le chien de
# garde dit que la machine est cassée ; le différer d'un demi-tour d'horloge le viderait
# de son sens. C'est la SEULE exception, et elle se demande explicitement.
#
# LA BOÎTE N'EST PAS UNE POUBELLE. Ce qu'on y range part forcément — deux vidages par
# jour, et le fichier reste sur disque si l'envoi échoue. Un différé silencieusement
# perdu serait bien pire que sept messages : on croirait le canal sain.
_DIFFERES = _ARCHIVE / "differes"


def _digest_actif() -> bool:
    return (os.getenv("SLACK_DIGEST") or "").strip().lower() in ("1", "true", "oui", "yes")


def _fichier_du_jour() -> Path:
    from datetime import datetime
    return _DIFFERES / f"{datetime.now():%Y-%m-%d}.jsonl"


def _differer(text: str, source: str) -> bool:
    """Range un message dans la boîte du jour. Renvoie True — le message est PRIS EN
    CHARGE, pas envoyé ; c'est le vidage qui l'enverra. Si l'écriture échoue, on poste
    tout de suite plutôt que de perdre le message : la boîte ne doit jamais avaler."""
    import json
    from datetime import datetime
    try:
        _DIFFERES.mkdir(parents=True, exist_ok=True)
        ligne = json.dumps({"at": datetime.now().isoformat(timespec="seconds"),
                            "source": source, "texte": text}, ensure_ascii=False)
        with _fichier_du_jour().open("a", encoding="utf-8") as f:
            f.write(ligne + "\n")
        _archive(text, envoye=False)
        return True
    except (OSError, ValueError) as exc:
        log.warning("Boîte du jour inaccessible (%s) — le message part immédiatement", exc)
        return False


def _source_appelante() -> str:
    """Le module qui appelle, pour titrer sa part du digest. Best-effort : si
    l'introspection échoue, on rend '' plutôt que de faire tomber une notification."""
    import inspect
    try:
        for frame in inspect.stack()[1:8]:
            mod = (frame.frame.f_globals.get("__name__") or "")
            if mod and not mod.startswith("utils.slack"):
                return mod.rsplit(".", 1)[-1]
    except Exception:  # noqa: BLE001 — jamais bloquant, c'est du confort de lecture
        pass
    return ""


_LIGNES_MAX_PAR_RAPPORT = 12
_MARQUEURS_ALERTE = ("🔴", "⚠️", "🚨", "🚩", "⛔", "🅿️")


def condenser(texte: str, max_lignes: int = _LIGNES_MAX_PAR_RAPPORT) -> str:
    """Ramène un rapport trop long à l'essentiel pour le digest. Pure, donc éprouvable.

    D'OÙ ÇA VIENT — Franck, 2026-08-28 : « les résumés sont beaucoup trop longs, il y a
    trop d'informations. » Le digest du matin portait ce jour-là un compte rendu d'agent
    de ~40 lignes et un lot de 14 : illisible sur un téléphone — et un canal illisible ne
    protège plus rien, c'est le défaut qui a créé la boîte du jour (13/08) qui revient
    par la LONGUEUR au lieu du NOMBRE.

    Ce qui est gardé : TOUTES les lignes d'alerte (🔴 ⚠️ 🚨 🚩…), où qu'elles soient —
    tronquer une décision serait pire que tout — plus le début du rapport jusqu'au
    budget. Les coupes sont marquées, et la dernière ligne dit COMBIEN a été retranché
    et où lire le rapport complet : une liste tronquée doit annoncer son total
    (journal du 2026-08-18).
    """
    lignes = texte.splitlines()
    if len(lignes) <= max_lignes:
        return texte
    garde = {i for i, l in enumerate(lignes) if any(m in l for m in _MARQUEURS_ALERTE)}
    for i in range(len(lignes)):
        if len(garde) >= max_lignes:
            break
        garde.add(i)
    morceaux, precedent = [], -1
    for i in sorted(garde):
        if i > precedent + 1:
            morceaux.append("  …")
        morceaux.append(lignes[i])
        precedent = i
    retranchees = len(lignes) - len(garde)
    if retranchees > 0:
        morceaux.append(f"_({retranchees} ligne(s) retranchées du digest — rapport "
                        f"complet dans logs/slack/)_")
    return "\n".join(morceaux)


def vider_boite(entete: str = "") -> tuple[int, bool]:
    """Poste EN UN SEUL MESSAGE tout ce que la boîte du jour contient, et la vide.

    Renvoie (nombre de messages regroupés, envoyé ou non).

    Le fichier est renommé AVANT l'envoi : un script qui écrirait pendant le vidage
    alimente une boîte neuve au lieu de voir sa ligne disparaître. Si l'envoi échoue, on
    remet le fichier en place — le prochain vidage réessaiera, et rien n'est perdu.

    Ce qui porte un 🔴 remonte en tête. Un digest qui garde l'ordre chronologique
    reproduirait le défaut qu'il corrige : ce matin-là, la seule décision à prendre était
    en cinquième position.
    """
    import json
    from datetime import datetime
    src = _fichier_du_jour()
    if not src.exists():
        return 0, False
    tampon = src.with_suffix(f".{datetime.now():%H%M%S}.envoi")
    try:
        src.rename(tampon)
    except OSError as exc:
        log.warning("Boîte du jour non verrouillée (%s) — vidage abandonné", exc)
        return 0, False

    lignes = []
    for brut in tampon.read_text(encoding="utf-8").splitlines():
        try:
            lignes.append(json.loads(brut))
        except ValueError:
            continue
    if not lignes:
        tampon.unlink(missing_ok=True)
        return 0, False

    decisions = [l for l in lignes if "🔴" in (l.get("texte") or "")]
    autres = [l for l in lignes if l not in decisions]
    morceaux = []
    for l in decisions + autres:
        heure = (l.get("at") or "")[11:16]
        src_nom = l.get("source") or "?"
        morceaux.append(f"───── {heure} · {src_nom}\n{condenser(l.get('texte') or '')}")
    corps = "\n\n".join(morceaux)
    # Slack coupe au-delà de 40 000 caractères ; on tronque NOUS-MÊMES et on le dit,
    # plutôt que de laisser la fin disparaître sans trace.
    if len(corps) > 38000:
        corps = corps[:38000] + "\n\n… (digest tronqué — tout est dans logs/slack/)"
    # Le nombre est TOUJOURS là, même quand l'appelant fournit son propre titre : sans
    # lui, un digest de dix rapports et un digest d'un seul ont exactement la même tête,
    # et on ne saurait pas si la matinée a été calme ou si la chaîne s'est arrêtée.
    tete = f"{entete or '🗂️ *Récapitulatif*'} — {len(lignes)} rapport(s)"
    if decisions:
        tete += f" · 🔴 {len(decisions)} demande(nt) une décision"
    ok = notify(f"{tete}\n\n{corps}", urgent=True)
    if ok:
        tampon.unlink(missing_ok=True)
    else:
        # L'envoi a échoué : on rend son contenu à la boîte pour le prochain vidage.
        try:
            with _fichier_du_jour().open("a", encoding="utf-8") as f:
                f.write(tampon.read_text(encoding="utf-8"))
            tampon.unlink(missing_ok=True)
        except OSError as exc:
            log.error("Digest non envoyé ET non remis en boîte — contenu dans %s (%s)",
                      tampon, exc)
    return len(lignes), ok


def notify(text: str, blocks: list | None = None, urgent: bool = False) -> bool:
    """Poste un message sur Slack ET l'archive localement. Jamais d'exception levée.

    Renvoie True si le message est PARTI — ou, quand la boîte du jour est active, s'il y
    a été rangé pour le prochain vidage. Un appelant qui teste ce booléen demande « mon
    message est-il pris en charge ? », jamais « est-il déjà à l'écran ? ».

    `urgent=True` court-circuite la boîte : réservé à ce qui perdrait son sens différé
    d'un demi-tour d'horloge (chien de garde, plafond API atteint).

    RÉCIDIVE, 2026-08-25. `SLACK_DIGEST=1` est posé en PERMANENCE en tête du crontab réel,
    donc hérité par `auto_deploiement --apply`, qui rejoue TOUTES les fixtures avant
    chaque déploiement. Toute fixture qui appelle `notify()` pour de vrai (pas de mock)
    SANS rediriger `slack._ARCHIVE`/`slack._DIFFERES` vers un dossier jetable écrivait
    donc dans la VRAIE boîte du jour — et le vidage suivant (11h45/20h) l'a posté pour de
    vrai dans #agendasabauda. Constaté sur `tests/test_slack_jamais_depuis_les_tests.py`
    ET sur d'autres fixtures (SEO, autocomplete) qui n'y pensaient pas : huit jours de
    messages-canaris mêlés au digest réel, 18→25/08.

    Le garde-fou ci-dessous est donc CENTRAL, pas fixture par fixture — même raisonnement
    que `_depuis_les_tests()` dans `_webhook()` : depuis les tests, tant qu'une fixture n'a
    PAS explicitement redirigé `_DIFFERES` (donc tant qu'il pointe encore sur le dossier
    de PRODUCTION), on refuse de différer — le message retombe sur le chemin webhook, déjà
    coupé par `_depuis_les_tests()`. Une fixture qui redirige (test_slack_digest.py) n'est
    pas concernée : `_DIFFERES` n'est alors plus le dossier par défaut.
    """
    _bac_a_sable = not (_depuis_les_tests() and _DIFFERES == _ARCHIVE_PAR_DEFAUT / "differes")
    if _digest_actif() and not urgent and _bac_a_sable and _differer(text, _source_appelante()):
        return True
    url = _webhook()
    if not url:
        log.info("SLACK_WEBHOOK_URL absente — notification ignorée : %s", text[:80])
        _archive(text, envoye=False)
        return False
    payload: dict = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    try:
        r = requests.post(url, json=payload, timeout=15)
        ok = r.status_code < 300
        if not ok:
            log.warning("Slack a répondu %s : %s", r.status_code, r.text[:200])
        _archive(text, envoye=ok)
        return ok
    except requests.RequestException as exc:
        log.warning("Envoi Slack impossible : %s", exc)
        _archive(text, envoye=False)
        return False


def _fiche_url(event: dict) -> str:
    """Lien vers la fiche backoffice (si BACKOFFICE_BASE_URL est configurée)."""
    base = (os.getenv("BACKOFFICE_BASE_URL") or "").rstrip("/")
    eid = event.get("id")
    return f"{base}/preview/{eid}" if base and eid else ""


def notify_ready(event: dict, wp_id: int | None, wp_base: str = "") -> bool:
    """Signal « bon » : événement complété et poussé en brouillon sur l'agenda."""
    title = (event.get("article_title") or event.get("title") or "?")[:90]
    link = ""
    if wp_id and wp_base:
        link = f"\n<{wp_base.rstrip('/')}/wp-admin/post.php?post={wp_id}&action=edit|Ouvrir le brouillon WordPress>"
    return notify(
        f"✅ *Complété & poussé en brouillon* — {title}"
        f"{('  (id ' + str(wp_id) + ')') if wp_id else ''}{link}")


def notify_incomplete(event: dict, missing_labels: list[str], note: str = "") -> bool:
    """Signal « pas bon » : il manque des champs après passage de l'agent.

    `note` (ajouté le 2026-08-05) : contexte optionnel affiché avant le lien, ex.
    « bloqué depuis le 2026-08-01, retenté chaque jour sans succès » — c'est le
    RESURFAÇAGE de scripts/autocomplete.py qui le fournit, pour qu'une fiche coincée
    ne disparaisse pas de Slack après son premier signalement (anti-spam trop strict,
    corrigé le même jour : voir la docstring de la boucle principale)."""
    title = (event.get("article_title") or event.get("title") or "?")[:90]
    manque = ", ".join(missing_labels) or "?"
    fiche = _fiche_url(event)
    lien = f"\n<{fiche}|Compléter dans le dashboard>" if fiche else ""
    slash = ""
    if event.get("id"):
        slash = (f"\n_Ou réponds :_ `/agenda complete {event['id']} "
                 f"lieu=… ville=… url_image=…`")
    prefixe = f"\n_{note}_" if note else ""
    return notify(
        f"⚠️ *À compléter* — {title}\n"
        f"Il manque : *{manque}*{prefixe}{lien}{slash}")
