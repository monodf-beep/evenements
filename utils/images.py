"""Recherche d'une photo RÉUTILISABLE (Wikimedia Commons) pour illustrer un événement.

Bonne pratique reprise de l'Observatoire : Cultura Sabauda est un média publié —
on n'affiche pas « une image trouvée sur le web » (risque de droit d'auteur, au
même titre que le paywall). On tire d'une source LICENCIABLE avec crédit :
Wikimedia Commons (CC / domaine public). Le LLM rédige la requête (jugement) ;
ce module ne fait que CHERCHER et FILTRER (déterministe) — voir docs/LLM_OU_CODE.md.

Aucune clé d'API (l'API Commons est ouverte).
"""
from __future__ import annotations

import html as htmlmod
import re

import requests

from utils.sources import is_logo_image

_API = "https://commons.wikimedia.org/w/api.php"
_UA = {"User-Agent": "CulturaSabaudaBot/1.0 (agenda; contact@culturasabauda.eu)"}
_OK_MIME = ("image/jpeg", "image/png")


def fetch_og_image(url: str, timeout: int = 8) -> str:
    """Image de partage (og:image / twitter:image) d'une page officielle.

    Vignette déterministe quand le flux ne fournit pas d'image. Skip radar/Gmail.
    """
    if not url or url.startswith("gmail:") or "news.google.com" in url:
        return ""
    try:
        r = requests.get(url, timeout=timeout, headers=_UA)
        if r.status_code != 200 or not r.text:
            return ""
        page = r.text
    except requests.RequestException:
        return ""
    for pat in (r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)'):
        m = re.search(pat, page, re.I)
        if m:
            img = htmlmod.unescape(m.group(1).strip())
            if img.startswith("//"):
                img = "https:" + img
            if img.startswith("http"):
                return img
    return ""


def _clean(text: str) -> str:
    """Retire le HTML (les champs extmetadata de Commons en contiennent)."""
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", text or "")).strip()


def _credit(meta: dict, license_short: str) -> str:
    """Construit une mention de crédit à afficher (auteur / Wikimedia Commons · licence)."""
    artist = _clean((meta.get("Artist") or {}).get("value", ""))
    artist = re.sub(r"https?://\S+", "", artist).strip(" ·-—")
    parts = [p for p in (artist or None, "Wikimedia Commons") if p]
    credit = " / ".join(parts)
    if license_short:
        credit += f" · {license_short}"
    return credit[:200]


def commons_search(query: str, *, min_width: int = 800, limit: int = 8,
                   thumb_width: int = 1200, timeout: int = 10) -> tuple[str, str]:
    """Cherche une photo licenciable sur Commons. Renvoie (url, crédit) ou ('', '').

    Filtre : vraie photo (JPEG/PNG), largeur suffisante, pas un logo/blason/icône.
    """
    query = (query or "").strip()
    if not query:
        return "", ""
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": "6", "gsrlimit": str(limit),
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": str(thumb_width),
    }
    try:
        r = requests.get(_API, params=params, headers=_UA, timeout=timeout)
        if r.status_code != 200:
            return "", ""
        pages = (r.json().get("query") or {}).get("pages") or {}
    except (requests.RequestException, ValueError):
        return "", ""

    # Commons renvoie les pages dans un dict non ordonné : on suit l'ordre de
    # pertinence de la recherche (champ 'index').
    for page in sorted(pages.values(), key=lambda p: p.get("index", 1_000_000)):
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("mime") not in _OK_MIME:
            continue
        if int(info.get("width") or 0) < min_width:
            continue
        full = info.get("url") or ""
        thumb = info.get("thumburl") or full
        if not thumb.startswith("http") or is_logo_image(full):
            continue
        meta = info.get("extmetadata") or {}
        license_short = _clean((meta.get("LicenseShortName") or {}).get("value", ""))
        return thumb, _credit(meta, license_short)
    return "", ""
