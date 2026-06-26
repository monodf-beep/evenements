#!/usr/bin/env python3
"""Publie un événement vers WordPress CS via REST API + Application Password.

TOUJOURS en status='draft' — jamais 'publish' automatiquement.
Sprint 1 : post_type='post' + taxonomie 'agenda' + meta fields.
Sprint 2 : migrer vers CPT 'agenda' JetEngine.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("publisher")


def publish_to_cs(event: dict) -> int | None:
    """Publie l'événement en draft WordPress. Retourne le wp_post_id ou None."""
    load_dotenv(ROOT / ".env")
    wp_url  = os.getenv("WP_URL", "").rstrip("/")
    wp_user = os.getenv("WP_USER", "")
    wp_pass = os.getenv("WP_APP_PASSWORD", "")  # Application Password WP

    if not all([wp_url, wp_user, wp_pass]):
        log.error("Variables WordPress manquantes (WP_URL, WP_USER, WP_APP_PASSWORD)")
        return None

    payload = {
        "title":   event.get("title", ""),
        "content": event.get("description", ""),
        "status":  "draft",   # TOUJOURS draft — Franck publie manuellement
        "meta": {
            "event_date_start":      event.get("date_start", ""),
            "event_lieu":            event.get("lieu", ""),
            "event_ville":           event.get("ville", ""),
            "event_territoire":      event.get("territoire", ""),
            "event_categorie":       event.get("llm_categorie", ""),
            "event_organisateur":    event.get("organisateur", ""),
            "event_prix":            event.get("prix", ""),
            "event_url_source":      event.get("url_source", ""),
            "event_llm_score":       str(event.get("llm_score", 0)),
            "event_llm_justification": event.get("llm_justification", ""),
        },
    }
    # Image à la une si disponible
    if event.get("url_image"):
        payload["_thumbnail_url"] = event["url_image"]

    try:
        resp = requests.post(
            f"{wp_url}/wp-json/wp/v2/posts",
            json=payload,
            auth=(wp_user, wp_pass),
            timeout=30,
        )
        resp.raise_for_status()
        post_id = resp.json().get("id")
        log.info("Draft créé WP id=%s : %s", post_id, event.get("title", "")[:60])
        return post_id
    except requests.HTTPError as exc:
        log.error("Erreur WordPress API (%s) : %s", exc.response.status_code,
                  exc.response.text[:200])
        return None
    except requests.RequestException as exc:
        log.error("Connexion WordPress impossible : %s", exc)
        return None
