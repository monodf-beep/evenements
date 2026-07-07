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


def notify(text: str, blocks: list | None = None) -> bool:
    """Poste un message sur Slack. Renvoie True si envoyé. Jamais d'exception levée."""
    url = _webhook()
    if not url:
        log.info("SLACK_WEBHOOK_URL absente — notification ignorée : %s", text[:80])
        return False
    payload: dict = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code >= 300:
            log.warning("Slack a répondu %s : %s", r.status_code, r.text[:200])
            return False
        return True
    except requests.RequestException as exc:
        log.warning("Envoi Slack impossible : %s", exc)
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
