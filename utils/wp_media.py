#!/usr/bin/env python3
"""Upload d'un visuel généré (Pillow) vers la médiathèque WordPress d'agendasabauda.eu.

Sert de PONT entre le back-office et Instagram : l'API Instagram exige une URL
d'image PUBLIQUE (elle n'accepte pas un envoi de bytes en direct) — on héberge donc
le visuel sur agendasabauda.eu (déjà public) puis on donne cette URL à Instagram.
Réutilise EXACTEMENT les identifiants WP_AS_* du publisher existant
(scripts/publisher_as.py) : rien de nouveau à configurer côté WordPress.
"""
from __future__ import annotations

import base64
import os

import requests

from utils.logger import get_logger

log = get_logger("wp_media")

# Même contournement anti-WAF que scripts/publisher.py (certains hébergeurs
# suppriment l'en-tête Authorization ; on se présente comme un navigateur).
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}


def _headers(auth) -> dict:
    token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode("utf-8")).decode("ascii")
    return {**_UA, "X-CS-Auth": token}


def configured() -> bool:
    return bool(os.getenv("WP_AS_URL") and os.getenv("WP_AS_USER")
                and os.getenv("WP_AS_APP_PASSWORD"))


def upload_bytes(data: bytes, filename: str, *, content_type: str = "image/jpeg",
                 alt: str = "") -> str | None:
    """Upload et renvoie l'URL PUBLIQUE (source_url) du média, ou None si échec.
    Jamais bloquant pour le reste du back-office : les erreurs sont journalisées."""
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    wp_user = os.getenv("WP_AS_USER", "")
    wp_pass = os.getenv("WP_AS_APP_PASSWORD", "")
    if not (wp_url and wp_user and wp_pass):
        log.warning("WP_AS_URL/USER/APP_PASSWORD manquant — upload média social impossible.")
        return None
    auth = (wp_user, wp_pass)
    try:
        resp = requests.post(
            f"{wp_url}/?rest_route=/wp/v2/media",
            data=data, auth=auth,
            headers={**_headers(auth), "Content-Type": content_type,
                     "Content-Disposition": f'attachment; filename="{filename}"'},
            timeout=60)
        resp.raise_for_status()
        js = resp.json()
        media_id, url = js.get("id"), js.get("source_url")
        if media_id and alt:
            try:
                requests.post(f"{wp_url}/?rest_route=/wp/v2/media/{media_id}",
                              json={"alt_text": alt}, auth=auth,
                              headers=_headers(auth), timeout=20)
            except requests.RequestException:
                pass  # non bloquant : le média est déjà en ligne
        log.info("Média social uploadé WP id=%s : %s", media_id, url)
        return url
    except requests.HTTPError as exc:
        log.warning("Upload média social refusé (%s) : %s",
                    exc.response.status_code, exc.response.text[:200])
        return None
    except requests.RequestException as exc:
        log.warning("Upload média social impossible : %s", exc)
        return None
