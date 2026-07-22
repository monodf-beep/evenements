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
# UA navigateur pour lire les PAGES officielles (certains sites servent une page
# vide/403 à un bot mais tout à un navigateur). Le _UA descriptif reste pour l'API
# Commons (Wikimedia demande un UA identifiable).
_PAGE_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr,it;q=0.8,en;q=0.6",
}
_OK_MIME = ("image/jpeg", "image/png")

# Chemins typiques d'une VRAIE photo de contenu (CMS) — sert à préférer une image
# éditoriale à un élément d'habillage.
_CONTENT_HINT = re.compile(r"/(uploads|content|media|photos?|images?|wp-content|fichiers)/", re.I)
# Habillage à rejeter (logo, icône, sprite, pixel de tracking, avatar…).
_CHROME_IMG = re.compile(
    r"logo|icon|sprite|favicon|placeholder|pixel|spinner|avatar|blank|1x1|"
    r"loader|badge|banniere|banner|header-|/theme/|/assets/(?:img/)?ui", re.I)

# Sous ce seuil (plus petit côté, en px), une image reste visiblement floue une fois
# étirée aux formats sociaux (1080 px et +) — un og:image standard (souvent 600×315
# pour les cartes de partage) est SOUS ce seuil. Mieux vaut chercher plus loin dans
# la chaîne (page → Commons → bannière) qu'accepter une image connue trop petite.
MIN_DIM = 700
_MAX_CHECK_BYTES = 3 * 1024 * 1024


def _image_size(data: bytes) -> tuple[int, int]:
    try:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(data)) as img:
            return img.size
    except Exception:
        return (0, 0)


def remote_min_side(url: str, timeout: int = 10) -> int:
    """Plus petit côté (px) d'une image distante — 0 si injoignable/illisible.
    Télécharge de façon bornée (l'URL seule ne dit rien de la taille réelle)."""
    if not url or not url.startswith("http"):
        return 0
    try:
        r = requests.get(url, timeout=timeout, headers=_PAGE_UA, stream=True)
        if r.status_code != 200:
            return 0
        buf = b""
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > _MAX_CHECK_BYTES:
                break
        w, h = _image_size(buf)
        return min(w, h)
    except requests.RequestException:
        return 0


def _big_enough(url: str, timeout: int = 8) -> bool:
    """Télécharge (borné) une image candidate pour vérifier sa VRAIE résolution —
    l'URL seule ne dit rien de la taille réelle du fichier."""
    return remote_min_side(url, timeout) >= MIN_DIM


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
            if img.startswith("http") and _big_enough(img):
                return img
    return ""


def fetch_content_image(url: str, timeout: int = 8) -> str:
    """Repli quand la page n'a PAS d'og:image : la 1re vraie photo de CONTENU.

    Beaucoup de pages d'offices de tourisme / institutions ne posent pas de balise
    og:image mais affichent une belle photo dans le corps (ex. lac-annecy.com). On
    scanne les <img> (y compris lazy-load data-src / srcset), on écarte l'habillage
    (logo, icône, pixel, bannière) et on privilégie une image de dossier éditorial
    (/uploads/, /content/…). Renvoie '' si rien de convaincant."""
    if not url or url.startswith("gmail:") or "news.google.com" in url:
        return ""
    try:
        r = requests.get(url, timeout=timeout, headers=_PAGE_UA)
        if r.status_code != 200 or not r.text:
            return ""
        page = r.text
    except requests.RequestException:
        return ""

    candidates: list[str] = []
    for m in re.finditer(r"<img\b[^>]*>", page, re.I):
        tag = m.group(0)
        src = ""
        for attr in ("data-src", "data-lazy-src", "data-original", "src"):
            a = re.search(rf'{attr}=["\']([^"\']+)', tag, re.I)
            if a:
                src = a.group(1)
                break
        if not src:
            a = re.search(r'srcset=["\']([^"\']+)', tag, re.I)
            if a:
                src = a.group(1).split(",")[-1].strip().split(" ")[0]  # la + grande
        src = htmlmod.unescape((src or "").strip())
        if src.startswith("//"):
            src = "https:" + src
        low = src.lower()
        if not low.startswith("http"):
            continue
        if not re.search(r"\.(jpg|jpeg|png|webp)(\?|#|$)", low):
            continue
        if is_logo_image(src) or _CHROME_IMG.search(low):
            continue
        candidates.append(src)

    if not candidates:
        return ""
    # Priorité aux photos de dossier éditorial (/uploads/…), sinon la 1re valable —
    # dans chaque groupe, on écarte les images trop petites (floues une fois étirées).
    hinted = [c for c in candidates if _CONTENT_HINT.search(c)]
    for src in hinted + [c for c in candidates if c not in hinted]:
        if _big_enough(src):
            return src
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
