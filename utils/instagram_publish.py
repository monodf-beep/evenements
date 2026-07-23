#!/usr/bin/env python3
"""Publication AUTOMATIQUE sur Instagram (Graph API), un compte par territoire.

Chaque territoire a son propre compte Instagram Business/Creator relié à une Page
Facebook (prérequis Meta — cf. docs/RESEAUX_INSTAGRAM_SETUP.md). Config par
variables d'environnement, MÊME CONVENTION que les listes Brevo par territoire
(BREVO_LIST_<SLUG>) : `IG_ACCOUNT_ID_<SLUG>` + `IG_TOKEN_<SLUG>`. Tant qu'un
territoire n'a pas ses 2 variables renseignées, `configured()` renvoie False et on
ne tente rien — jamais bloquant pour le reste du back-office.

Flux Graph API (doc Meta « Content Publishing ») :
  1. POST /{ig-user-id}/media          (image_url [+ caption])  → creation_id
  2. POST /{ig-user-id}/media_publish  (creation_id)             → media_id publié
Carrousel : chaque image devient un enfant (is_carousel_item=true, SANS légende),
puis un conteneur parent (media_type=CAROUSEL, children=id1,id2,…) porte la légende.
"""
from __future__ import annotations

import os
import re
import time
import unicodedata

import requests

from utils.logger import get_logger

log = get_logger("instagram_publish")

# Les tokens émis par le NOUVEAU système (« API Instagram », connexion Instagram
# directe — préfixe IGAA...) doivent taper sur graph.instagram.com, PAS
# graph.facebook.com (réservé aux tokens de Page classiques, préfixe EAA...). Toute
# notre config (cf. RESEAUX_INSTAGRAM_SETUP.md) utilise le nouveau système.
GRAPH = "https://graph.instagram.com/v21.0"
_POLL_TRIES, _POLL_DELAY = 8, 2.0


def _slug(label: str) -> str:
    """Même normalisation que app._nl_slug (cohérence avec les listes Brevo)."""
    n = unicodedata.normalize("NFKD", (label or "").lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = re.sub(r"[^a-z0-9]+", "_", n).strip("_")
    return n.upper()


def _account_id(territoire_label: str) -> str:
    return os.getenv(f"IG_ACCOUNT_ID_{_slug(territoire_label)}", "")


def _token(territoire_label: str) -> str:
    return os.getenv(f"IG_TOKEN_{_slug(territoire_label)}", "")


def configured(territoire_label: str) -> bool:
    return bool(_account_id(territoire_label) and _token(territoire_label))


# Même liste que app._RESEAUX_ACCOUNTS (labels) — dupliquée ici volontairement :
# ce module n'importe pas app.py (pas de dépendance Flask), et cette liste ne
# change quasiment jamais (un territoire = un compte Instagram business).
_TERRITOIRES = ["Savoie / Haute-Savoie", "Piémont", "Vallée d'Aoste", "Nice / Alpes-Maritimes"]


def territoire_for_account_id(ig_account_id: str) -> str:
    """Retrouve le territoire (label) à partir d'un ig_account_id reçu par webhook —
    l'inverse de _account_id(). Sert à savoir quel IG_TOKEN_<SLUG> utiliser pour
    répondre à un commentaire arrivé sur CE compte Instagram. '' si aucun match."""
    ig_account_id = str(ig_account_id or "")
    for label in _TERRITOIRES:
        if ig_account_id and _account_id(label) == ig_account_id:
            return label
    return ""


def _wait_ready(container_id: str, token: str) -> bool:
    """Attend que le conteneur soit FINISHED (surtout utile pour les carrousels).
    N'échoue jamais bloquant : au-delà du délai, on tente la publication quand même."""
    for _ in range(_POLL_TRIES):
        try:
            r = requests.get(f"{GRAPH}/{container_id}",
                             params={"fields": "status_code", "access_token": token},
                             timeout=15)
            r.raise_for_status()
            status = r.json().get("status_code")
            if status == "FINISHED":
                return True
            if status == "ERROR":
                return False
        except requests.RequestException:
            pass
        time.sleep(_POLL_DELAY)
    return True


def _api_error(resp) -> str:
    try:
        return resp.json().get("error", {}).get("message", resp.text[:200])
    except ValueError:
        return resp.text[:200]


def publish_single(territoire_label: str, image_url: str, caption: str,
                   alt_text: str = "") -> dict:
    """Publie UNE image. Renvoie {ok: True, media_id} ou {ok: False, error}.

    alt_text : texte alternatif (accessibilité + recherche interne Instagram),
    supporté par l'API depuis mars 2025 pour les images — PAS pour les stories."""
    if not configured(territoire_label):
        return {"ok": False, "error": f"Compte Instagram non configuré pour "
                f"« {territoire_label} » (IG_ACCOUNT_ID_{_slug(territoire_label)} / "
                f"IG_TOKEN_{_slug(territoire_label)} manquants)."}
    ig_id, token = _account_id(territoire_label), _token(territoire_label)
    try:
        data = {"image_url": image_url, "caption": caption, "access_token": token}
        if alt_text:
            data["alt_text"] = alt_text[:1000]  # limite Meta
        r = requests.post(f"{GRAPH}/{ig_id}/media", data=data, timeout=30)
        r.raise_for_status()
        creation_id = r.json()["id"]
        _wait_ready(creation_id, token)
        r2 = requests.post(f"{GRAPH}/{ig_id}/media_publish",
                           data={"creation_id": creation_id, "access_token": token},
                           timeout=30)
        r2.raise_for_status()
        media_id = r2.json()["id"]
        log.info("Publié Instagram (%s) : media_id=%s", territoire_label, media_id)
        return {"ok": True, "media_id": media_id}
    except requests.HTTPError as exc:
        msg = _api_error(exc.response)
        log.warning("Échec publication Instagram (%s) : %s", territoire_label, msg)
        return {"ok": False, "error": msg}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def send_private_reply(territoire_label: str, comment_id: str, text: str) -> dict:
    """Répond en DM PRIVÉ à un commentaire (« Private Replies », API Meta depuis
    2024) — déclenché par le webhook (utils.instagram_webhook), jamais appelé
    directement au moment de la publication. Renvoie {ok, message_id} ou
    {ok: False, error}.

    Contraintes Meta (non contournables) : UNE seule réponse privée par
    commentaire, jamais deux ; fenêtre de 7 jours max après le commentaire
    (au-delà, Meta refuse) ; permissions requises côté app Meta :
    instagram_business_basic + instagram_business_manage_messages (+
    instagram_business_manage_comments pour recevoir le webhook)."""
    if not configured(territoire_label):
        return {"ok": False, "error": f"Compte Instagram non configuré pour « {territoire_label} »."}
    ig_id, token = _account_id(territoire_label), _token(territoire_label)
    try:
        r = requests.post(
            f"{GRAPH}/{ig_id}/messages",
            json={"recipient": {"comment_id": comment_id}, "message": {"text": text}},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=30)
        r.raise_for_status()
        message_id = r.json().get("message_id")
        log.info("Réponse privée envoyée (%s) sur commentaire %s : message_id=%s",
                 territoire_label, comment_id, message_id)
        return {"ok": True, "message_id": message_id}
    except requests.HTTPError as exc:
        msg = _api_error(exc.response)
        log.warning("Échec réponse privée (%s) sur commentaire %s : %s",
                    territoire_label, comment_id, msg)
        return {"ok": False, "error": msg}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def publish_story(territoire_label: str, image_url: str) -> dict:
    """Publie une STORY (24h). L'API Instagram n'accepte ni légende ni texte
    alternatif sur les stories (limitation de l'API, pas de nous) : le texte doit
    être « cuit » dans l'image (cf. utils.social_image.story)."""
    if not configured(territoire_label):
        return {"ok": False, "error": f"Compte Instagram non configuré pour « {territoire_label} »."}
    ig_id, token = _account_id(territoire_label), _token(territoire_label)
    try:
        r = requests.post(f"{GRAPH}/{ig_id}/media",
                          data={"image_url": image_url, "media_type": "STORIES",
                                "access_token": token}, timeout=30)
        r.raise_for_status()
        creation_id = r.json()["id"]
        _wait_ready(creation_id, token)
        r2 = requests.post(f"{GRAPH}/{ig_id}/media_publish",
                           data={"creation_id": creation_id, "access_token": token},
                           timeout=30)
        r2.raise_for_status()
        media_id = r2.json()["id"]
        log.info("Story publiée Instagram (%s) : media_id=%s", territoire_label, media_id)
        return {"ok": True, "media_id": media_id}
    except requests.HTTPError as exc:
        msg = _api_error(exc.response)
        log.warning("Échec story Instagram (%s) : %s", territoire_label, msg)
        return {"ok": False, "error": msg}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def publish_carousel(territoire_label: str, image_urls: list[str], caption: str,
                     alt_text: str = "") -> dict:
    """Publie un CARROUSEL (2 à 10 images). Renvoie {ok: True, media_id} ou {ok: False, error}.

    alt_text : même texte alternatif appliqué à CHAQUE image du carrousel (l'API ne
    prend l'alt text que par enfant, pas au niveau du conteneur parent)."""
    if not configured(territoire_label):
        return {"ok": False, "error": f"Compte Instagram non configuré pour « {territoire_label} »."}
    if not (2 <= len(image_urls) <= 10):
        return {"ok": False, "error": "Un carrousel Instagram nécessite entre 2 et 10 images."}
    ig_id, token = _account_id(territoire_label), _token(territoire_label)
    try:
        children = []
        for url in image_urls:
            data = {"image_url": url, "is_carousel_item": "true", "access_token": token}
            if alt_text:
                data["alt_text"] = alt_text[:1000]
            r = requests.post(f"{GRAPH}/{ig_id}/media", data=data, timeout=30)
            r.raise_for_status()
            cid = r.json()["id"]
            _wait_ready(cid, token)
            children.append(cid)
        r3 = requests.post(f"{GRAPH}/{ig_id}/media",
                           data={"media_type": "CAROUSEL", "children": ",".join(children),
                                 "caption": caption, "access_token": token}, timeout=30)
        r3.raise_for_status()
        parent_id = r3.json()["id"]
        _wait_ready(parent_id, token)
        r4 = requests.post(f"{GRAPH}/{ig_id}/media_publish",
                           data={"creation_id": parent_id, "access_token": token}, timeout=30)
        r4.raise_for_status()
        media_id = r4.json()["id"]
        log.info("Carrousel publié Instagram (%s) : media_id=%s", territoire_label, media_id)
        return {"ok": True, "media_id": media_id}
    except requests.HTTPError as exc:
        msg = _api_error(exc.response)
        log.warning("Échec carrousel Instagram (%s) : %s", territoire_label, msg)
        return {"ok": False, "error": msg}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}
