#!/usr/bin/env python3
"""Publie un événement vers WordPress CS via REST API + Application Password.

TOUJOURS en status='draft' — jamais 'publish' automatiquement.
Sprint 1 : post_type='post' + taxonomie 'agenda' + meta fields.
Sprint 2 : migrer vers CPT 'agenda' JetEngine.
"""
from __future__ import annotations
import base64
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


def _headers(auth) -> dict:
    """En-têtes communs : navigateur + auth de secours via un en-tête PERSONNALISÉ.
    Beaucoup d'hébergeurs (nginx/LiteSpeed) suppriment l'en-tête `Authorization` →
    l'app-password n'atteint pas WordPress (rest_not_logged_in). On envoie donc AUSSI
    les identifiants dans `X-CS-Auth` (que le serveur ne filtre pas), lu côté WordPress
    par le mu-plugin cs-rest-auth.php (voir deploy/wordpress/). L'auth Basic normale
    reste en place : si l'en-tête n'est PAS supprimé, elle suffit."""
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
        # Programme (CHARTE §5 bis) : faits structurés en LISTE — horaires, séances,
        # line-up. Rendu en <ul> (défensif : absent/None/chaîne/liste).
        prog = art.get("programme")
        if isinstance(prog, str):
            prog = [prog]
        prog = [str(p).strip() for p in prog if str(p).strip()] if isinstance(prog, list) else []
        if prog:
            parts.append("<h3>Programme</h3>\n<ul>")
            parts += [f"<li>{_md_inline(p)}</li>" for p in prog]
            parts.append("</ul>")
        # PAS d'encadré « En pratique » ici : le bloc pratique (Quand/Où/Tarif/Catégorie)
        # est rendu NATIVEMENT par The Events Calendar (méta as_*). Le répéter en prose
        # ferait doublon. L'article reste ÉDITORIAL (chapô + corps + programme).
        # Sources : uniquement des URLs http(s) propres (on ignore prose/markdown/URL
        # bricolée que le LLM aurait glissée), dédupliquées, en excluant l'auto-lien.
        seen = set()
        clean_sources = []
        for s in (data.get("sources") or []):
            s = (s or "").strip()
            if (s.startswith("http://") or s.startswith("https://")) \
                    and " " not in s and s not in seen \
                    and "agendasabauda.eu" not in s:   # jamais un lien vers nous-mêmes
                seen.add(s)
                clean_sources.append(s)
        if clean_sources:
            parts.append("<h3>Sources</h3><ul>")
            parts += [f'<li><a href="{html.escape(s)}" target="_blank" '
                      f'rel="noopener">{html.escape(s)}</a></li>' for s in clean_sources]
            parts.append("</ul>")
        return title, "\n".join(parts)

    # Repli : article non enrichi → description brute (nettoyée des balises).
    raw = re.sub(r"(?s)<[^>]+>", " ", event.get("description") or "")
    raw = re.sub(r"\s+", " ", html.unescape(raw)).strip()
    return title, f"<p>{html.escape(raw)}</p>" if raw else ""


_WP_CATEGORIES_FILE = ROOT / "config" / "wp_categories.txt"


def _map_category(name: str) -> str:
    """Traduit une catégorie interne (les 11) vers la catégorie WordPress réelle,
    d'après config/wp_categories.txt (lignes « interne = WordPress »). Sans
    correspondance, renvoie le nom interne inchangé."""
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


def _resolve_term(wp_url: str, auth, taxonomy: str, name: str) -> int | None:
    """ID d'un terme (taxonomy = 'categories' | 'tags') par son nom ; le crée s'il
    n'existe pas. Jamais bloquant : renvoie None en cas d'échec."""
    name = (name or "").strip()
    if not name:
        return None
    try:
        r = requests.get(f"{wp_url}/?rest_route=/wp/v2/{taxonomy}",
                         params={"search": name, "per_page": 20},
                         auth=auth, headers=_headers(auth), timeout=20)
        r.raise_for_status()
        for t in r.json():
            if (t.get("name") or "").strip().lower() == name.lower():
                return t.get("id")
        c = requests.post(f"{wp_url}/?rest_route=/wp/v2/{taxonomy}",
                          json={"name": name}, auth=auth, headers=_headers(auth), timeout=20)
        c.raise_for_status()
        return c.json().get("id")
    except (requests.RequestException, ValueError) as exc:
        log.warning("Terme %s « %s » non résolu : %s", taxonomy, name, exc)
        return None


def _media_slug(title: str, suffix: str = "") -> str:
    """Nom de fichier/titre média LISIBLE dérivé du titre de l'événement — jamais le nom
    de fichier de l'URL source (souvent un hash opaque type CDN/Wikimedia, ex.
    « 6a1fec783405f1c822ac64fc.png » : illisible dans la médiathèque WordPress, repéré
    par Franck). '' si pas de titre (repli sur l'ancien comportement, cf. appelant)."""
    import re
    import unicodedata
    n = unicodedata.normalize("NFKD", (title or "").strip().lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")[:60]
    if not n:
        return ""
    return f"{n}-{suffix}" if suffix else n


def _upload_featured_media(wp_url: str, auth, image_url: str,
                           alt: str = "", caption: str = "", title: str = "",
                           card: bool = False, focal=(0.5, 0.5),
                           mode: str = "auto",
                           ratio: "tuple[int, int] | None" = None) -> "tuple[int | None, str]":
    """Télécharge l'image source et l'envoie dans la médiathèque WordPress.

    Retourne (media_id, source_url) — (None, '') si échec. Jamais bloquant : un échec
    d'upload laisse le post sans vignette.
    alt/caption : texte alternatif (SEO, avec l'expression clé) et légende (crédit photo).
    title : titre LISIBLE de l'événement — sert à nommer le fichier ET le champ « titre »
    du média dans la bibliothèque WordPress (sinon WordPress affiche le nom de fichier
    de la source, souvent un hash illisible). '' → repli sur l'ancien comportement
    (nom dérivé de l'URL).
    card : si True, l'image est standardisée (cover-focal ou letterbox, cf.
    utils.card_image) AVANT l'upload, au ratio `ratio` (4:3 par défaut, la grille — passer
    ex. (16, 9) pour un autre usage, ex. le grand visuel de fiche). `focal` (x,y) ∈ [0,1]
    ancre le recadrage. Si la transformation échoue (image exotique), on retombe sur
    l'original (jamais bloquant)."""
    try:
        # Retry sur échec TRANSITOIRE du téléchargement SOURCE (429/5xx) — Wikimedia
        # (upload.wikimedia.org) renvoie par intermittence un 429 sous charge (constaté
        # en masse lors d'un rattrapage --recheck : plusieurs dizaines d'images pourtant
        # bien choisies retombaient sur la bannière générique à cause de CE 429, pas d'un
        # vrai échec — voir utils.images.remote_min_side qui a le même souci ailleurs).
        img = None
        for attempt in range(3):
            img = requests.get(image_url, timeout=30, headers=_UA)
            if img.status_code < 400 or img.status_code not in (429, 500, 502, 503, 504):
                break
            if attempt < 2:
                log.warning("Téléchargement source tentative %d échoué (%s) — retry dans %ds… (%s)",
                            attempt + 1, img.status_code, 3 * (attempt + 1), image_url)
                import time as _time
                _time.sleep(3 * (attempt + 1))
        img.raise_for_status()
        content_type = img.headers.get("Content-Type", "").split(";")[0].strip()
        if not content_type.startswith("image/"):
            log.warning("URL image non-image (%s) : %s", content_type or "?", image_url)
            return None, ""

        # Nom de fichier LISIBLE dérivé du titre si fourni, sinon repli sur le nom de
        # l'URL source (souvent un hash opaque — cf. _media_slug).
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        slug = _media_slug(title)
        if slug:
            name = f"{slug}{ext}"
        else:
            name = os.path.basename(urlparse(image_url).path) or "image"
            if "." not in name:
                name = f"{name}{ext}"

        data = img.content
        if card:
            # Standardisation au ratio demandé (import paresseux : Pillow n'est requis
            # que si demandé).
            try:
                from utils.card_image import make_card_bytes
                data, used_mode = make_card_bytes(img.content, focal=focal, mode=mode or "auto",
                                                  ratio=ratio)
                content_type = "image/jpeg"
                stem = name.rsplit(".", 1)[0]
                name = f"{stem}-carte.jpg"
                log.info("Vignette générée (%s, ratio %s) pour %s", used_mode,
                         ratio or "4:3", image_url)
            except Exception as exc:  # jamais bloquant : on garde l'original
                log.warning("Vignette impossible (%s) — image d'origine conservée.", exc)

        # Retry sur échec TRANSITOIRE (504/502/timeout — fréquent sur l'hébergement
        # mutualisé OVH lors de l'upload d'une image). Sans retry, un aléa réseau fait
        # échouer l'upload de la vignette 4:3 déjà générée ci-dessus → cs-publish.php
        # retombe sur son repli `image_url` (l'affiche BRUTE, non recadrée) comme image
        # à la une, ce qui produit dans la grille une carte avec marges blanches au lieu
        # du letterbox flou — jamais généré côté serveur. Un 4xx (auth, payload rejeté)
        # ne se répare pas en réessayant : on abandonne tout de suite dans ce cas.
        resp = None
        for attempt in range(3):
            try:
                resp = requests.post(
                    f"{wp_url}/?rest_route=/wp/v2/media",
                    data=data,
                    auth=auth,
                    headers={
                        **_headers(auth),
                        "Content-Type": content_type,
                        "Content-Disposition": f'attachment; filename="{name}"',
                    },
                    timeout=60,
                )
                if resp.status_code < 500:
                    break
            except requests.RequestException:
                resp = None
            if attempt < 2:
                log.warning("Upload média tentative %d échouée (%s) — retry dans %ds…",
                            attempt + 1, image_url, 3 * (attempt + 1))
                import time as _time
                _time.sleep(3 * (attempt + 1))
        if resp is None:
            log.warning("Upload média impossible après 3 tentatives : %s", image_url)
            return None, ""
        resp.raise_for_status()
        payload = resp.json()
        media_id = payload.get("id")
        source_url = payload.get("source_url") or ""
        log.info("Média uploadé WP id=%s : %s", media_id, image_url)
        # Renseigne le texte alternatif (SEO), la légende (crédit photo) ET le TITRE —
        # sans ça, WordPress affiche le nom de fichier (donc le hash de la source) dans
        # la médiathèque au lieu du titre de l'événement.
        if media_id and (alt or caption or title):
            try:
                meta = {"alt_text": alt, "caption": caption}
                if title:
                    meta["title"] = title
                requests.post(
                    f"{wp_url}/?rest_route=/wp/v2/media/{media_id}",
                    json=meta,
                    auth=auth, headers=_headers(auth), timeout=20)
            except requests.RequestException:
                pass  # non bloquant : la vignette est déjà en place
        return media_id, source_url
    except requests.HTTPError as exc:
        log.warning("Upload média refusé (%s) : %s", exc.response.status_code,
                    exc.response.text[:200])
        return None, ""
    except (requests.RequestException, ValueError) as exc:
        log.warning("Upload média impossible : %s", exc)
        return None, ""


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
    # Méta événementielles publiques (lisibles via REST une fois le post publié).
    # On N'EXPOSE PAS le scoring interne (llm_score/justification), ni l'URL d'une
    # source RADAR (charte §8 : le radar n'est jamais crédité ni lié).
    is_radar = (event.get("source_type") == "radar"
                or "(radar)" in (event.get("source_name") or ""))
    meta = {
        "event_date_start":      event.get("date_start", ""),
        "event_lieu":            event.get("lieu", ""),
        "event_ville":           event.get("ville", ""),
        "event_territoire":      event.get("territoire", ""),
        "event_categorie":       event.get("llm_categorie", ""),
        "event_organisateur":    event.get("organisateur", ""),
        "event_prix":            event.get("prix", ""),
        "event_url_source":      "" if is_radar else event.get("url_source", ""),
    }
    # Le titre de l'ARTICLE reste le titre éditorial ; le title Yoast (SEO, avec
    # la marque) part séparément en méta (_yoast_wpseo_title) ci-dessous.
    payload = {
        "title":   title,
        "content": content,
        "status":  "draft",   # TOUJOURS draft — Franck publie manuellement
    }

    # --- SEO / Yoast : méta, expression clé, extrait, slug, aperçu social ------
    seo_desc = event.get("seo_meta") or ""
    social_desc = event.get("seo_answer") or seo_desc  # la réponse directe, + percutante
    if event.get("seo_at"):
        if event.get("seo_keyphrase"):
            meta["_yoast_wpseo_focuskw"] = event["seo_keyphrase"]
        if event.get("seo_title"):
            meta["_yoast_wpseo_title"] = event["seo_title"]
        if seo_desc:
            meta["_yoast_wpseo_metadesc"] = seo_desc
        # Aperçu réseaux sociaux (Open Graph = Facebook/LinkedIn/WhatsApp, + Twitter).
        # L'image OG est la vignette (featured_media) : Yoast la reprend d'office.
        if event.get("seo_title"):
            meta["_yoast_wpseo_opengraph-title"] = event["seo_title"]
            meta["_yoast_wpseo_twitter-title"] = event["seo_title"]
        if social_desc:
            meta["_yoast_wpseo_opengraph-description"] = social_desc
            meta["_yoast_wpseo_twitter-description"] = social_desc
        if event.get("seo_answer"):
            payload["excerpt"] = event["seo_answer"]
        if event.get("seo_slug"):
            payload["slug"] = event["seo_slug"]
    payload["meta"] = meta

    # --- Catégorie (les 11) + étiquettes → taxonomies WordPress natives -------
    # Mapping optionnel « catégorie interne → catégorie WordPress » via
    # config/wp_categories.txt (pour coller à la taxonomie réelle de CS sans
    # créer de doublons). À défaut, on utilise le nom interne tel quel.
    cat_name = _map_category(event.get("llm_categorie"))
    cat_id = _resolve_term(wp_url, auth, "categories", cat_name)
    if cat_id:
        payload["categories"] = [cat_id]
    tag_names = []
    if event.get("seo_tags"):
        try:
            tag_names = [t for t in json.loads(event["seo_tags"]) if t]
        except (ValueError, TypeError):
            tag_names = []
    if event.get("seo_keyphrase"):
        tag_names.append(event["seo_keyphrase"])
    tag_ids = [i for i in (_resolve_term(wp_url, auth, "tags", n)
                           for n in dict.fromkeys(tag_names)) if i]
    if tag_ids:
        payload["tags"] = tag_ids

    # Image à la une : upload dans la médiathèque puis featured_media.
    # _thumbnail_url en meta ne définit PAS la vignette via l'API REST.
    # alt = expression clé (SEO) ; légende = crédit photo.
    if event.get("url_image"):
        media_id, _ = _upload_featured_media(
            wp_url, auth, event["url_image"],
            alt=event.get("seo_keyphrase") or event.get("title", ""),
            caption=event.get("image_credit", ""), title=event.get("title", ""))
        if media_id:
            payload["featured_media"] = media_id
        else:
            log.info("Post sans vignette (upload média échoué) : %s",
                     event.get("title", "")[:60])

    # MISE À JOUR si un brouillon existe déjà pour cet événement (évite les
    # doublons quand on reclique « Publier CS ») ; création sinon. Si l'ancien
    # brouillon a été supprimé côté WP (404), on recrée.
    existing = event.get("wp_post_id_cs")
    endpoint = (f"{wp_url}/?rest_route=/wp/v2/posts/{existing}" if existing
                else f"{wp_url}/?rest_route=/wp/v2/posts")
    try:
        resp = requests.post(endpoint, json=payload, auth=auth,
                             headers=_headers(auth), timeout=30)
        if existing and resp.status_code == 404:
            log.info("Brouillon WP %s introuvable → recréation", existing)
            resp = requests.post(f"{wp_url}/?rest_route=/wp/v2/posts", json=payload,
                                 auth=auth, headers=_headers(auth), timeout=30)
        resp.raise_for_status()
        post_id = resp.json().get("id")
        verb = "mis à jour" if existing and post_id == existing else "créé"
        log.info("Brouillon WP %s id=%s : %s", verb, post_id, event.get("title", "")[:60])
        return post_id
    except requests.HTTPError as exc:
        log.error("Erreur WordPress API (%s) : %s", exc.response.status_code,
                  exc.response.text[:200])
        return None
    except requests.RequestException as exc:
        log.error("Connexion WordPress impossible : %s", exc)
        return None
