#!/usr/bin/env python3
"""Publie un événement vers WordPress via l'endpoint maison « cs/v1/event ».

Architecture (Phase 6) : tout le travail The Events Calendar se fait CÔTÉ SERVEUR
dans le mu-plugin deploy/wordpress/cs-publish.php (tribe_create_event, lieu,
catégorie tribe_events_cat, taxonomie « territoire », méta « as_* », SEO Rank Math,
image à la une, auteur selon le score). Ici on ne fait que construire un JSON propre
et l'envoyer. TOUJOURS status=draft côté serveur — jamais publish automatiquement.

Le score décide la SIGNATURE (Cultura Sabauda ≥ 7 / Agenda Sabauda < 7), pas
« publier ou pas » : tous les événements retenus partent vers WordPress en brouillon.
"""
from __future__ import annotations
import base64
import html
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("publisher")

# Certaines protections anti-bot (WAF/nginx) renvoient un 403 sans User-Agent de
# navigateur. On se présente comme un navigateur.
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}

# Valeurs de prix qui signifient « entrée libre » → badge as_gratuit=1.
_FREE = {"gratuit", "gratuite", "gratuit·e", "entrée libre", "entree libre",
         "libre", "free", "0", "0€", "0 €"}


def _headers(auth) -> dict:
    """Navigateur + auth de secours via en-tête PERSONNALISÉ. Beaucoup d'hébergeurs
    (nginx/LiteSpeed) suppriment l'en-tête `Authorization` → l'app-password n'atteint
    pas WordPress (rest_not_logged_in). On envoie donc AUSSI les identifiants dans
    `X-CS-Auth` (non filtré), lu par le mu-plugin cs-rest-auth.php. L'auth Basic
    normale reste en place : si l'en-tête n'est pas supprimé, elle suffit."""
    token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode("utf-8")).decode("ascii")
    return {**_UA, "X-CS-Auth": token}


def _md_inline(s: str) -> str:
    """Échappe le HTML puis rend **gras** et *italique* (markdown léger)."""
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*(?!\*)", r"<em>\1</em>", s)
    return s


def _md_to_html(text: str) -> str:
    """Convertit un texte markdown-léger (paragraphes, titres ##, gras/italique) en HTML."""
    out = []
    for block in re.split(r"\n\s*\n", (text or "").strip()):
        block = block.strip()
        if not block:
            continue
        if block.startswith("### "):
            out.append(f"<h4>{_md_inline(block[4:])}</h4>")
        elif block.startswith("## "):
            out.append(f"<h3>{_md_inline(block[3:])}</h3>")
        else:
            out.append("<p>" + _md_inline(block).replace("\n", "<br>") + "</p>")
    return "\n".join(out)


def build_post(event: dict) -> tuple[str, str]:
    """(titre, contenu HTML) à publier. PRIORITÉ à l'article enrichi par l'agent ;
    repli sur le titre + la description bruts si l'événement n'a pas été enrichi."""
    data = None
    if event.get("enrich_data"):
        try:
            data = json.loads(event["enrich_data"])
        except (ValueError, TypeError):
            data = None

    art = (data or {}).get("article") or {}
    title = (event.get("article_title") or art.get("titre")
             or event.get("title") or "").strip()

    if art:
        parts = []
        if art.get("chapo"):
            parts.append(f"<p><strong>{_md_inline(art['chapo'].strip())}</strong></p>")
        if art.get("corps"):
            parts.append(_md_to_html(art["corps"]))
        if art.get("encadre"):
            parts.append("<h3>En pratique</h3>")
            parts.append(_md_to_html(art["encadre"]))
        # NB : les sources RADAR ne sont jamais listées (charte §8) ; l'agent ne met
        # dans « sources » que des sources officielles publiables.
        sources = [s for s in (data.get("sources") or []) if s]
        if sources:
            parts.append("<h3>Sources</h3><ul>")
            parts += [f'<li><a href="{html.escape(s)}" target="_blank" '
                      f'rel="noopener">{html.escape(s)}</a></li>' for s in sources]
            parts.append("</ul>")
        return title, "\n".join(parts)

    # Repli : article non enrichi → description brute (nettoyée des balises).
    raw = re.sub(r"(?s)<[^>]+>", " ", event.get("description") or "")
    raw = re.sub(r"\s+", " ", html.unescape(raw)).strip()
    return title, f"<p>{html.escape(raw)}</p>" if raw else ""


_WP_CATEGORIES_FILE = ROOT / "config" / "wp_categories.txt"


def _map_category(name: str) -> str:
    """Traduit une catégorie interne (les 11) vers le libellé/slug WordPress réel,
    d'après config/wp_categories.txt (lignes « interne = WordPress »). L'endpoint
    résout ensuite par slug puis par nom dans tribe_events_cat. Sans correspondance,
    renvoie le nom interne inchangé."""
    name = (name or "").strip()
    if not name or not _WP_CATEGORIES_FILE.exists():
        return name
    try:
        for line in _WP_CATEGORIES_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            src, dst = (p.strip() for p in line.split("=", 1))
            if src.lower() == name.lower() and dst:
                return dst
    except OSError:
        pass
    return name


def _is_free(prix: str) -> int:
    """1 si le prix signifie « gratuit », sinon 0."""
    return 1 if (prix or "").strip().lower() in _FREE else 0


def _build_payload(event: dict) -> dict:
    """Construit le JSON envoyé à cs/v1/event depuis une ligne events_raw."""
    title, content = build_post(event)

    # Le radar n'est jamais crédité ni lié (charte §8) : on ne pousse pas son URL.
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

    payload = {
        "wp_post_id":  event.get("wp_post_id_cs") or None,
        "title":       title,
        "content":     content,
        "start_date":  event.get("date_event_start") or event.get("date_start") or "",
        "end_date":    event.get("date_event_end") or "",
        "category":    _map_category(event.get("llm_categorie")),
        "territoire":  event.get("territoire", "") or "",
        "score":       event.get("llm_score"),
        "image_url":   event.get("url_image", "") or "",
        "image_alt":   event.get("seo_keyphrase") or event.get("title", "") or "",
        "meta":        meta,
    }

    # Lieu (Venue) : nom + ville si disponibles.
    if (event.get("lieu") or "").strip():
        payload["venue"] = {"Venue": event["lieu"].strip(),
                            "City": (event.get("ville") or "").strip()}

    # SEO Rank Math (uniquement si l'événement a été traité par l'étape SEO).
    if event.get("seo_at"):
        payload["seo"] = {
            "title":         event.get("seo_title", "") or "",
            "description":   event.get("seo_meta", "") or "",
            "focus_keyword": event.get("seo_keyphrase", "") or "",
        }

    return payload


def publish_to_cs(event: dict) -> int | None:
    """Publie/actualise l'événement en brouillon WordPress (événement TEC).
    Retourne le wp_post_id ou None. Le nom historique est conservé pour ne pas
    toucher à l'appelant (app.py) ; le routage CS/AS se fait via le score, côté serveur."""
    load_dotenv(ROOT / ".env")
    wp_url  = os.getenv("WP_URL", "").rstrip("/")
    wp_user = os.getenv("WP_USER", "")
    wp_pass = os.getenv("WP_APP_PASSWORD", "")

    if not all([wp_url, wp_user, wp_pass]):
        log.error("Variables WordPress manquantes (WP_URL, WP_USER, WP_APP_PASSWORD)")
        return None

    auth = (wp_user, wp_pass)
    payload = _build_payload(event)
    endpoint = f"{wp_url}/?rest_route=/cs/v1/event"

    try:
        resp = requests.post(endpoint, json=payload, auth=auth,
                             headers=_headers(auth), timeout=60)
        resp.raise_for_status()
        body = resp.json()
        post_id = body.get("id")
        verb = "mis à jour" if body.get("updated") else "créé"
        log.info("Événement WP %s id=%s : %s", verb, post_id,
                 (event.get("title", "") or "")[:60])
        return post_id
    except requests.HTTPError as exc:
        log.error("Erreur WordPress API (%s) : %s", exc.response.status_code,
                  exc.response.text[:300])
        return None
    except (requests.RequestException, ValueError) as exc:
        log.error("Connexion WordPress impossible : %s", exc)
        return None
