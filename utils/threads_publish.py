#!/usr/bin/env python3
"""Publication AUTOMATIQUE sur Threads (Threads API), un compte par territoire.

Complète utils.instagram_publish et utils.facebook_publish : « un contenu, 3
canaux » (cf. docs/RESEAUX_SOCIAUX_PLAN.md §4). API distincte de Facebook/Instagram
(hôte `graph.threads.net`, app Meta séparée avec permissions `threads_basic` +
`threads_content_publish`). Config par variables d'environnement, même convention :
`THREADS_USER_ID_<SLUG>` + `THREADS_TOKEN_<SLUG>`. Tant qu'un territoire n'a pas
ses 2 variables, `configured()` renvoie False et on ne tente rien.

Flux (comme Instagram) : POST /{threads-user-id}/threads (image_url + text) →
creation_id → POST /{threads-user-id}/threads_publish (creation_id) → id publié.
"""
from __future__ import annotations

import os
import re
import unicodedata

import requests

from utils.logger import get_logger

log = get_logger("threads_publish")

GRAPH = "https://graph.threads.net/v1.0"


def _slug(label: str) -> str:
    n = unicodedata.normalize("NFKD", (label or "").lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = re.sub(r"[^a-z0-9]+", "_", n).strip("_")
    return n.upper()


def _user_id(territoire_label: str) -> str:
    return os.getenv(f"THREADS_USER_ID_{_slug(territoire_label)}", "")


def _token(territoire_label: str) -> str:
    return os.getenv(f"THREADS_TOKEN_{_slug(territoire_label)}", "")


def configured(territoire_label: str) -> bool:
    return bool(_user_id(territoire_label) and _token(territoire_label))


def _api_error(resp) -> str:
    try:
        return resp.json().get("error", {}).get("message", resp.text[:200])
    except ValueError:
        return resp.text[:200]


def publish_single(territoire_label: str, image_url: str, caption: str) -> dict:
    """Publie une image + légende sur Threads. Renvoie {ok: True, media_id} ou {ok: False, error}."""
    if not configured(territoire_label):
        return {"ok": False, "error": f"Compte Threads non configuré pour "
                f"« {territoire_label} » (THREADS_USER_ID_{_slug(territoire_label)} / "
                f"THREADS_TOKEN_{_slug(territoire_label)} manquants)."}
    user_id, token = _user_id(territoire_label), _token(territoire_label)
    try:
        r = requests.post(f"{GRAPH}/{user_id}/threads",
                          data={"media_type": "IMAGE", "image_url": image_url,
                                "text": caption, "access_token": token}, timeout=30)
        r.raise_for_status()
        creation_id = r.json()["id"]
        r2 = requests.post(f"{GRAPH}/{user_id}/threads_publish",
                           data={"creation_id": creation_id, "access_token": token},
                           timeout=30)
        r2.raise_for_status()
        media_id = r2.json()["id"]
        log.info("Publié Threads (%s) : media_id=%s", territoire_label, media_id)
        return {"ok": True, "media_id": media_id}
    except requests.HTTPError as exc:
        msg = _api_error(exc.response)
        log.warning("Échec publication Threads (%s) : %s", territoire_label, msg)
        return {"ok": False, "error": msg}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}
