#!/usr/bin/env python3
"""Publication AUTOMATIQUE sur la Page Facebook d'un territoire (Graph API).

Complète utils.instagram_publish : « un contenu, 3 canaux » (cf.
docs/RESEAUX_SOCIAUX_PLAN.md §4) — le même visuel + la même légende que le post
Instagram part aussi sur la Page Facebook liée, sans travail supplémentaire.

Config par variables d'environnement, même convention que Brevo/Instagram :
`FB_PAGE_ID_<SLUG>` + `FB_PAGE_TOKEN_<SLUG>` (jeton de PAGE, permission
`pages_manage_posts` — différent du jeton Instagram). Tant qu'un territoire n'a
pas ses 2 variables, `configured()` renvoie False et on ne tente rien : jamais
bloquant pour la publication Instagram, qui reste l'action principale.
"""
from __future__ import annotations

import os
import re
import unicodedata

import requests

from utils.logger import get_logger

log = get_logger("facebook_publish")

GRAPH = "https://graph.facebook.com/v21.0"


def _slug(label: str) -> str:
    """Même normalisation que instagram_publish._slug (cohérence des noms d'env-var)."""
    n = unicodedata.normalize("NFKD", (label or "").lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = re.sub(r"[^a-z0-9]+", "_", n).strip("_")
    return n.upper()


def _page_id(territoire_label: str) -> str:
    return os.getenv(f"FB_PAGE_ID_{_slug(territoire_label)}", "")


def _token(territoire_label: str) -> str:
    return os.getenv(f"FB_PAGE_TOKEN_{_slug(territoire_label)}", "")


def configured(territoire_label: str) -> bool:
    return bool(_page_id(territoire_label) and _token(territoire_label))


def _api_error(resp) -> str:
    try:
        return resp.json().get("error", {}).get("message", resp.text[:200])
    except ValueError:
        return resp.text[:200]


def publish_photo(territoire_label: str, image_url: str, caption: str) -> dict:
    """Publie une photo + légende sur la Page. Renvoie {ok: True, post_id} ou {ok: False, error}."""
    if not configured(territoire_label):
        return {"ok": False, "error": f"Page Facebook non configurée pour "
                f"« {territoire_label} » (FB_PAGE_ID_{_slug(territoire_label)} / "
                f"FB_PAGE_TOKEN_{_slug(territoire_label)} manquants)."}
    page_id, token = _page_id(territoire_label), _token(territoire_label)
    try:
        r = requests.post(f"{GRAPH}/{page_id}/photos",
                          data={"url": image_url, "caption": caption, "access_token": token},
                          timeout=30)
        r.raise_for_status()
        post_id = r.json().get("post_id") or r.json().get("id")
        log.info("Publié Facebook (%s) : post_id=%s", territoire_label, post_id)
        return {"ok": True, "post_id": post_id}
    except requests.HTTPError as exc:
        msg = _api_error(exc.response)
        log.warning("Échec publication Facebook (%s) : %s", territoire_label, msg)
        return {"ok": False, "error": msg}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}
