#!/usr/bin/env python3
"""Publie un événement vers WordPress CS via REST API + Application Password.

TOUJOURS en status='draft' — jamais 'publish' automatiquement.
Sprint 1 : post_type='post' + taxonomie 'agenda' + meta fields.
Sprint 2 : migrer vers CPT 'agenda' JetEngine.
"""
from __future__ import annotations
import html
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("publisher")

# Certaines protections anti-bot (WAF/nginx, ex. Hostinger) renvoient un 403 aux
# requêtes sans User-Agent de navigateur. On se présente comme un navigateur.
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}


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


def _upload_featured_media(wp_url: str, auth, image_url: str) -> int | None:
    """Télécharge l'image source et l'envoie dans la médiathèque WordPress.

    Retourne le media_id (à passer en featured_media) ou None si échec.
    Jamais bloquant : un échec d'upload laisse le post sans vignette.
    """
    try:
        img = requests.get(image_url, timeout=30, headers=_UA)
        img.raise_for_status()
        content_type = img.headers.get("Content-Type", "").split(";")[0].strip()
        if not content_type.startswith("image/"):
            log.warning("URL image non-image (%s) : %s", content_type or "?", image_url)
            return None

        # Nom de fichier : basename de l'URL, sinon dérivé du type MIME.
        name = os.path.basename(urlparse(image_url).path) or "image"
        if "." not in name:
            ext = mimetypes.guess_extension(content_type) or ".jpg"
            name = f"{name}{ext}"

        resp = requests.post(
            f"{wp_url}/wp-json/wp/v2/media",
            data=img.content,
            auth=auth,
            headers={
                **_UA,
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{name}"',
            },
            timeout=60,
        )
        resp.raise_for_status()
        media_id = resp.json().get("id")
        log.info("Média uploadé WP id=%s : %s", media_id, image_url)
        return media_id
    except requests.HTTPError as exc:
        log.warning("Upload média refusé (%s) : %s", exc.response.status_code,
                    exc.response.text[:200])
        return None
    except (requests.RequestException, ValueError) as exc:
        log.warning("Upload média impossible : %s", exc)
        return None


def publish_to_cs(event: dict) -> int | None:
    """Publie l'événement en draft WordPress. Retourne le wp_post_id ou None."""
    load_dotenv(ROOT / ".env")
    wp_url  = os.getenv("WP_URL", "").rstrip("/")
    wp_user = os.getenv("WP_USER", "")
    wp_pass = os.getenv("WP_APP_PASSWORD", "")  # Application Password WP

    if not all([wp_url, wp_user, wp_pass]):
        log.error("Variables WordPress manquantes (WP_URL, WP_USER, WP_APP_PASSWORD)")
        return None

    auth = (wp_user, wp_pass)
    # PRIORITÉ à l'article enrichi (titre + chapô + corps + encadré + sources) ;
    # repli sur le brut si l'événement n'a pas été rédigé par l'agent.
    title, content = build_post(event)
    payload = {
        "title":   title,
        "content": content,
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

    # Image à la une : upload dans la médiathèque puis featured_media.
    # _thumbnail_url en meta ne définit PAS la vignette via l'API REST.
    if event.get("url_image"):
        media_id = _upload_featured_media(wp_url, auth, event["url_image"])
        if media_id:
            payload["featured_media"] = media_id
        else:
            log.info("Post sans vignette (upload média échoué) : %s",
                     event.get("title", "")[:60])

    try:
        resp = requests.post(
            f"{wp_url}/wp-json/wp/v2/posts",
            json=payload,
            auth=auth,
            headers=_UA,
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
