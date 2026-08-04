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


def _webhook() -> str:
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


def notify(text: str, blocks: list | None = None) -> bool:
    """Poste un message sur Slack ET l'archive localement. Renvoie True si envoyé.
    Jamais d'exception levée."""
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


def notify_incomplete(event: dict, missing_labels: list[str]) -> bool:
    """Signal « pas bon » : il manque des champs après passage de l'agent."""
    title = (event.get("article_title") or event.get("title") or "?")[:90]
    manque = ", ".join(missing_labels) or "?"
    fiche = _fiche_url(event)
    lien = f"\n<{fiche}|Compléter dans le dashboard>" if fiche else ""
    slash = ""
    if event.get("id"):
        slash = (f"\n_Ou réponds :_ `/agenda complete {event['id']} "
                 f"lieu=… ville=… url_image=…`")
    return notify(
        f"⚠️ *À compléter* — {title}\n"
        f"Il manque : *{manque}*{lien}{slash}")
