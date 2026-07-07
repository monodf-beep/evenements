#!/usr/bin/env python3
"""Publie un événement vers AGENDA SABAUDA (agendasabauda.eu) — événement TEC.

Cible DISTINCTE de scripts/publisher.py :
  - publisher.py     → culturasabauda.eu (article, bouton « Publier CS »).
  - publisher_as.py  → agendasabauda.eu  (événement The Events Calendar, bouton
                       « Agenda Sabauda »).

Tout le travail TEC se fait CÔTÉ SERVEUR dans le mu-plugin deploy/wordpress/
cs-publish.php (route REST cs/v1/event : tribe_create_event, lieu, catégorie
tribe_events_cat, taxonomie « territoire », méta « as_* », SEO Rank Math, image à
la une, auteur selon le score). Ici on construit un JSON propre et on l'envoie.
TOUJOURS status=draft côté serveur — jamais publish automatiquement.

Variables .env dédiées (ne PAS réutiliser celles de culturasabauda.eu) :
  WP_AS_URL=https://agendasabauda.eu
  WP_AS_USER=agenda-bot
  WP_AS_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
"""
from __future__ import annotations
import base64
import os
import sys
from datetime import date
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
# On réutilise la mise en forme de l'article et le mapping de catégorie du
# publisher historique (mêmes règles éditoriales, y compris charte §8 sur le radar).
from scripts.publisher import build_post, _map_category

log = get_logger("publisher_as")

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}

# Valeurs de prix qui signifient « entrée libre » → badge as_gratuit=1.
_FREE = {"gratuit", "gratuite", "gratuit·e", "entrée libre", "entree libre",
         "libre", "free", "0", "0€", "0 €"}


def _headers(auth) -> dict:
    """Navigateur + auth de secours via l'en-tête X-CS-Auth (lu par cs-rest-auth.php)
    quand l'hébergeur supprime l'en-tête Authorization. L'auth Basic reste en place."""
    token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode("utf-8")).decode("ascii")
    return {**_UA, "X-CS-Auth": token}


def _is_free(prix: str) -> int:
    return 1 if (prix or "").strip().lower() in _FREE else 0


def _iso_dates(event: dict) -> tuple[str, str]:
    """(début, fin) en ISO AAAA-MM-JJ pour The Events Calendar.

    Priorité aux colonnes déjà normalisées (date_event_start/end). Si elles sont
    vides, on RÉ-EXTRAIT depuis le texte brut date_start via la logique française
    de scripts/dates.parse_dates — surtout NE PAS envoyer date_start tel quel :
    WordPress/PHP ne sait pas lire « 10 juin 2026 » et retombe sur la date du jour.
    """
    start = (event.get("date_event_start") or "").strip()
    end   = (event.get("date_event_end") or "").strip()
    if not start:
        raw = (event.get("date_start") or "").strip()
        if raw:
            try:
                from scripts.dates import parse_dates
                s, e, _ = parse_dates(raw)
                start = start or s
                end   = end or e
            except Exception as exc:  # ré-extraction non bloquante
                log.warning("Ré-extraction de date impossible (%s) : %s", raw, exc)
    if not start:
        log.warning("Événement sans date ISO exploitable : %s",
                    (event.get("title", "") or "")[:60])
    return start, end


def _build_payload(event: dict) -> dict:
    """Construit le JSON envoyé à cs/v1/event depuis une ligne events_raw."""
    title, content = build_post(event)

    # Le radar n'est jamais crédité ni lié (charte §8).
    is_radar = (event.get("source_type") == "radar"
                or "(radar)" in (event.get("source_name") or ""))
    prix = event.get("prix", "") or ""

    meta = {
        "as_score":                 event.get("llm_score", ""),
        "as_gratuit":               _is_free(prix),
        "as_tarif":                 "" if _is_free(prix) else prix,
        "as_horaire":               event.get("horaire", "") or "",
        "as_billetterie_url":       event.get("billetterie_url", "") or "",
        "as_source_officielle_url": "" if is_radar else (event.get("url_source", "") or ""),
        "as_verifie_le":            date.today().isoformat(),
        "as_image_credit":          event.get("image_credit", "") or "",
    }

    start_iso, end_iso = _iso_dates(event)
    payload = {
        "wp_post_id":  event.get("wp_post_id_as") or None,
        "title":       title,
        "content":     content,
        "start_date":  start_iso,
        "end_date":    end_iso,
        "category":    _map_category(event.get("llm_categorie")),
        "territoire":  event.get("territoire", "") or "",
        "score":       event.get("llm_score"),
        "image_url":   event.get("url_image", "") or "",
        "image_alt":   event.get("seo_keyphrase") or event.get("title", "") or "",
        "meta":        meta,
    }

    if (event.get("lieu") or "").strip():
        payload["venue"] = {"Venue": event["lieu"].strip(),
                            "City": (event.get("ville") or "").strip()}

    if event.get("seo_at"):
        payload["seo"] = {
            "title":         event.get("seo_title", "") or "",
            "description":   event.get("seo_meta", "") or "",
            "focus_keyword": event.get("seo_keyphrase", "") or "",
        }

    return payload


def publish_to_as(event: dict) -> int | None:
    """Publie/actualise l'événement en brouillon sur agendasabauda.eu (TEC).
    Retourne le wp_post_id (côté agenda) ou None."""
    load_dotenv(ROOT / ".env")
    wp_url  = os.getenv("WP_AS_URL", "").rstrip("/")
    wp_user = os.getenv("WP_AS_USER", "")
    wp_pass = os.getenv("WP_AS_APP_PASSWORD", "")

    if not all([wp_url, wp_user, wp_pass]):
        log.error("Variables Agenda Sabauda manquantes "
                  "(WP_AS_URL, WP_AS_USER, WP_AS_APP_PASSWORD)")
        return None

    auth = (wp_user, wp_pass)
    payload = _build_payload(event)
    endpoint = f"{wp_url}/?rest_route=/cs/v1/event"

    # Diagnostic : ce qu'on envoie réellement (dates, lieu, taxonomies) — permet de
    # savoir si un champ manquant vient d'ici (payload) ou de l'endpoint (TEC).
    log.info("→ AS payload : start=%r end=%r venue=%r cat=%r terr=%r img=%s",
             payload.get("start_date"), payload.get("end_date"),
             payload.get("venue"), payload.get("category"),
             payload.get("territoire"), bool(payload.get("image_url")))

    try:
        resp = requests.post(endpoint, json=payload, auth=auth,
                             headers=_headers(auth), timeout=60)
        resp.raise_for_status()
        body = resp.json()
        post_id = body.get("id")
        verb = "mis à jour" if body.get("updated") else "créé"
        log.info("Événement Agenda Sabauda %s id=%s : %s", verb, post_id,
                 (event.get("title", "") or "")[:60])
        return post_id
    except requests.HTTPError as exc:
        log.error("Erreur Agenda Sabauda API (%s) : %s", exc.response.status_code,
                  exc.response.text[:300])
        return None
    except (requests.RequestException, ValueError) as exc:
        log.error("Connexion Agenda Sabauda impossible : %s", exc)
        return None
