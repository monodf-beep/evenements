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
import os
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
# Habillage à rejeter (logo, icône, sprite, pixel de tracking, avatar…). Deux parts :
# des DOSSIERS d'UI de thème, déjà bornés par des « / » donc sûrs en sous-chaîne ; des
# mots de NOM DE FICHIER, comparés en tokens (comme utils.sources.is_logo_image), jamais
# en sous-chaîne brute.
#
# 2026-09-08 (Franck, fiche « Musicastelle Autumn Edition ») : cette regex cherchait
# « logo » n'importe où dans l'URL. Le og:image officiel de la page — la photo que le
# site affiche lui-même en tête — s'appelle « 02_Cover_LogoEdizioneAutunnale.png »
# (« Logo dell'Edizione Autunnale », pas un logo isolé) : rejeté à tort, le seul candidat
# restant ne convenait à rien, et la fiche est retombée sur la bannière générique de
# territoire. `is_logo_image` avait déjà résolu ce même piège par des tokens bornés
# (commentaire d'origine : « logo » matche « Logo-Escale.png » mais pas « catalogo.jpg » ) ;
# cette regex-ci, plus ancienne et dans un autre module, ne l'avait jamais reçu.
_CHROME_PATH = re.compile(r"/theme/|/assets/(?:img/)?ui", re.I)
_CHROME_NAME_TOKENS = frozenset((
    "logo", "icon", "icons", "sprite", "favicon", "placeholder", "pixel", "spinner",
    "avatar", "blank", "1x1", "loader", "badge", "banniere", "banner", "header",
))


def _is_chrome(url: str) -> bool:
    """Vrai si l'URL trahit de l'habillage de site (pas une photo de contenu) : un
    dossier d'UI de thème, ou un NOM DE FICHIER qui matche un des mots ci-dessus en
    TOKEN complet (jamais en sous-chaîne — « LogoEdizioneAutunnale » n'est pas « logo »)."""
    u = (url or "").lower()
    if not u:
        return False
    if _CHROME_PATH.search(u):
        return True
    from urllib.parse import urlparse as _up
    name = _up(u).path.rsplit("/", 1)[-1]
    words = set(re.split(r"[^a-z0-9]+", name))
    return bool(words & _CHROME_NAME_TOKENS)

# Sous ce seuil (plus petit côté, en px), une image reste visiblement floue une fois
# étirée aux formats sociaux (1080 px et +) — un og:image standard (souvent 600×315
# pour les cartes de partage) est SOUS ce seuil. Mieux vaut chercher plus loin dans
# la chaîne (page → Commons → bannière) qu'accepter une image connue trop petite.
MIN_DIM = 700
_MAX_CHECK_BYTES = 3 * 1024 * 1024

# Au-delà de ce ratio (grand côté / petit côté), la FORME trahit un bandeau/bannière
# d'habillage de site (large et plat, ou l'inverse — une colonne étroite et haute) plutôt
# qu'une vraie photo éditoriale : une photo « normale », même en paysage large, dépasse
# rarement le panoramique (~2:1 à 2.5:1). Vérification indépendante de MIN_DIM : une
# bannière peut très bien mesurer 3000×750 (côté court = 750px, passe MIN_DIM) tout en
# étant clairement un bandeau, pas une photo.
MAX_ASPECT = 2.5

# EN DESSOUS de ce ratio (grand côté / petit côté), l'image est jugée trop CARRÉE pour
# être une vraie affiche/photo éditoriale d'événement — une affiche est quasi toujours
# nettement portrait ou paysage (jamais 1:1 pile). Un carré trahit plutôt une vignette
# CMS générique (miniature de partage social 1200×1200, avatar, recadrage automatique
# d'un CMS) qui a perdu l'info réelle en la recadrant au carré. Repère de Franck.
MIN_ASPECT = 1.15


def looks_like_banner_shape(w: int, h: int) -> bool:
    """Vrai si les proportions (w, h) trahissent un bandeau/bannière (trop plat ou trop
    étroit — au-delà de MAX_ASPECT) OU une vignette générique recadrée au carré (en
    dessous de MIN_ASPECT), plutôt qu'une vraie affiche/photo éditoriale. False si
    dimensions inconnues (0)."""
    if not w or not h:
        return False
    ratio = max(w, h) / min(w, h)
    return ratio > MAX_ASPECT or ratio < MIN_ASPECT


def _image_size(data: bytes) -> tuple[int, int]:
    try:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(data)) as img:
            return img.size
    except Exception:
        return (0, 0)


def _dims_once(url: str, ua: dict, timeout: int) -> "tuple[int, int] | None":
    """Une tentative de mesure. Renvoie (largeur, hauteur), (0, 0) si l'image est
    lisible mais illisible en tant qu'image, ou None si la requête a ÉCHOUÉ (à retenter)."""
    try:
        r = requests.get(url, timeout=timeout, headers=ua, stream=True)
        if r.status_code != 200:
            return None
        buf = b""
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > _MAX_CHECK_BYTES:
                break
        return _image_size(buf)
    except requests.RequestException:
        return None


def remote_dims(url: str, timeout: int = 10, retries: int = 2) -> "tuple[int, int]":
    """(largeur, hauteur) d'une image distante — (0, 0) si injoignable/illisible.

    Télécharge de façon bornée (l'URL seule ne dit rien de la taille réelle). Fiabilisé
    par des retries : Wikimedia (upload.wikimedia.org) renvoie par intermittence un 400
    quand on enchaîne beaucoup de téléchargements — sans retry, une bonne photo serait
    faussement mesurée à 0 puis remplacée à tort. On tente le UA descriptif Wikimedia
    d'abord (Commons demande un UA identifiable), puis le UA navigateur en repli."""
    if not url or not url.startswith("http"):
        return (0, 0)
    wiki = "wikimedia.org" in url or "wikipedia.org" in url
    uas = [_UA, _PAGE_UA] if wiki else [_PAGE_UA]
    import time as _time
    for attempt in range(retries + 1):
        for ua in uas:
            dims = _dims_once(url, ua, timeout)
            if dims is not None:
                return dims
        if attempt < retries:
            _time.sleep(0.6 * (attempt + 1))  # petit backoff : laisse passer le throttle
    return (0, 0)


def remote_min_side(url: str, timeout: int = 10, retries: int = 2) -> int:
    """Plus petit côté (px) d'une image distante — 0 si injoignable/illisible."""
    return min(remote_dims(url, timeout, retries))


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
            if img.startswith("http"):
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

    candidates = _img_tags(page, url)

    if not candidates:
        return ""
    # Priorité aux photos de dossier éditorial (/uploads/…), sinon la 1re valable.
    # NB : PAS de filtre de taille ici — une PETITE image PERTINENTE (la vraie photo
    # de l'événement) vaut mieux qu'une GRANDE image PARASITE (bandeau/pub du site,
    # ex. « DON D'ORGANES »). Si l'image retenue est trop petite pour un visuel social,
    # c'est le rendu (utils.social_image) qui bascule sur le fond abstrait — jamais ici
    # qu'on va chercher « plus grand » au risque d'attraper un habillage hors-sujet.
    for src in candidates:
        if _CONTENT_HINT.search(src):
            return src
    return candidates[0]


def _absolu(src: str, base_url: str = "") -> str:
    """URL d'image absolue et propre ('' si inexploitable)."""
    src = htmlmod.unescape((src or "").strip())
    if not src:
        return ""
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("http"):
        return src
    if base_url and src.startswith("/"):
        from urllib.parse import urljoin
        return urljoin(base_url, src)
    return ""


def _img_tags(page: str, base_url: str = "") -> list[str]:
    """Les <img> d'une page (y compris lazy-load data-src et la plus grande source d'un
    srcset), sans l'habillage (logo, icône, pixel, bannière). Ordre du document."""
    candidates: list[str] = []
    for m in re.finditer(r"<img\b[^>]*>", page or "", re.I):
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
        src = _absolu(src, base_url)
        low = src.lower()
        if not low.startswith("http"):
            continue
        if not re.search(r"\.(jpg|jpeg|png|webp)(\?|#|$)", low):
            continue
        if is_logo_image(src) or _is_chrome(src):
            continue
        if src not in candidates:
            candidates.append(src)
    return candidates


def page_image_candidates(page: str, base_url: str = "") -> list[str]:
    """TOUTES les images plausibles d'une page officielle, par ordre de confiance, sans
    réseau : og:image / twitter:image, puis les `image` des blocs JSON-LD (l'affiche
    déclarée par le site lui-même), puis les <img> de contenu. Dédoublonné, habillage
    écarté.

    2026-09-08 (Franck) : « on doit passer par des scripts pour les images ! on a la
    source officielle, dans l'événement de la source officielle il y a l'image, on la
    prend, voilà ». Jusque-là `scripts/images_wide.py` payait un agent de recherche web
    (0,20 $ l'appel) pour RETROUVER une page que la base connaissait déjà : 60 fiches
    tentées, 5 images trouvées, 8,91 $ en quatre jours — 1,80 $ l'image. Cette fonction
    est la réponse : la page est en base (`url_officiel`, `url_source`), ses images sont
    dedans, leur orientation se mesure en les téléchargeant. Zéro appel de modèle."""
    page = page or ""
    out: list[str] = []

    def _add(u: str) -> None:
        u = _absolu(u, base_url)
        if u and u.startswith("http") and u not in out \
                and not is_logo_image(u) and not _is_chrome(u):
            out.append(u)

    for pat in (r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)'):
        for m in re.finditer(pat, page, re.I):
            _add(m.group(1))
    try:
        from utils import jsonld as _jsonld
        for n in _jsonld.noeuds(page):
            v = n.get("image")
            for item in (v if isinstance(v, list) else [v]):
                if isinstance(item, str):
                    _add(item)
                elif isinstance(item, dict):
                    _add(item.get("url") or item.get("contentUrl") or "")
    except Exception:  # un JSON-LD cassé ne doit pas priver des <img>
        pass
    for src in _img_tags(page, base_url):
        _add(src)
    return out


def page_images(url: str, timeout: int = 8) -> list[str]:
    """`page_image_candidates` sur une page officielle réellement téléchargée. [] si la
    page est injoignable ou n'est pas une page (gmail:, radar Google News)."""
    if not url or url.startswith("gmail:") or url.startswith("translated:") \
            or "news.google.com" in url:
        return []
    try:
        r = requests.get(url, timeout=timeout, headers=_PAGE_UA)
        if r.status_code != 200 or not r.text:
            return []
        return page_image_candidates(r.text, url)
    except requests.RequestException:
        return []


# Orientation d'une image d'après ses dimensions — partagée par images_wide et ses
# fixtures : 'wide' nettement plus large que haut, 'portrait' nettement plus haut que
# large, '' entre les deux (carré ou presque : ni l'un ni l'autre).
WIDE_MIN_RATIO = 1.3
PORTRAIT_MAX_RATIO = 0.9


def orientation(w: int, h: int) -> str:
    if not w or not h:
        return ""
    r = w / h
    if r >= WIDE_MIN_RATIO:
        return "wide"
    if r <= PORTRAIT_MAX_RATIO:
        return "portrait"
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
                   thumb_width: int = 2400, timeout: int = 10) -> tuple[str, str, str]:
    """Cherche une photo licenciable sur Commons. Renvoie (url, crédit, titre_fichier)
    ou ('', '', ''). Le titre (« File:Marché Saint-Ours Aoste.jpg ») est un indice
    textuel utile à l'agent vision quand l'image seule est ambiguë mais que le nom du
    fichier confirme (ou dément) le sujet — cf. utils.image_verify.verify_relevance.

    Filtre : vraie photo (JPEG/PNG), largeur suffisante, pas un logo/blason/icône, pas
    une forme de bandeau (cf. looks_like_banner_shape — un fichier très plat ou très
    étroit est un habillage, pas une photo, même large en pixels).

    thumb_width=2400 (pas 1200) : nos formats sociaux sont PORTRAIT (jusqu'à 1080×1920),
    et beaucoup de photos Commons sont PAYSAGE — une miniature de 1200px de large ne
    fait souvent que ~700px de haut sur une photo large, ce qui dépasse le seuil
    d'agrandissement (utils.social_image.MAX_UPSCALE) et déclenche le repli abstrait à
    tort, alors qu'une résolution suffisante existe (cas vécu : château de Montrottier,
    miniature 1280×753 refusée alors que l'original fait 5337×3138). 2400px de large
    couvre la hauteur nécessaire même sur une photo très large, pour un poids de fichier
    qui reste raisonnable (JPEG re-encodé par Wikimedia, pas l'original brut).
    """
    query = (query or "").strip()
    if not query:
        return "", "", ""
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": "6", "gsrlimit": str(limit),
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": str(thumb_width),
    }
    try:
        r = requests.get(_API, params=params, headers=_UA, timeout=timeout)
        if r.status_code != 200:
            return "", "", ""
        pages = (r.json().get("query") or {}).get("pages") or {}
    except (requests.RequestException, ValueError):
        return "", "", ""

    # Commons renvoie les pages dans un dict non ordonné : on suit l'ordre de
    # pertinence de la recherche (champ 'index').
    for page in sorted(pages.values(), key=lambda p: p.get("index", 1_000_000)):
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("mime") not in _OK_MIME:
            continue
        if int(info.get("width") or 0) < min_width:
            continue
        if looks_like_banner_shape(int(info.get("width") or 0), int(info.get("height") or 0)):
            continue
        full = info.get("url") or ""
        thumb = info.get("thumburl") or full
        if not thumb.startswith("http") or is_logo_image(full):
            continue
        meta = info.get("extmetadata") or {}
        license_short = _clean((meta.get("LicenseShortName") or {}).get("value", ""))
        title = (page.get("title") or "").removeprefix("File:")
        return thumb, _credit(meta, license_short), title
    return "", "", ""


# ── Europeana : musées, archives et bibliothèques européens (dont collections du
# territoire sabaud). Source LICENCIABLE complémentaire de Commons. INACTIVE tant
# qu'EUROPEANA_API_KEY n'est pas configurée (clé gratuite : pro.europeana.eu). Même
# posture de droits que Commons (reusability=open) + mêmes filtres (vraie image,
# taille, pas une forme de bandeau). EXPÉRIMENTAL : à valider en conditions réelles
# avant de s'y fier (la qualité/pertinence des retours Europeana varie selon les fonds).
_EUROPEANA_API = "https://api.europeana.eu/record/v2/search.json"


def _first(v):
    """Europeana renvoie souvent des listes ; on prend le 1er élément utile."""
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""


def _short_rights(rights_url: str) -> str:
    """Étiquette de licence courte depuis l'URL de droits Europeana."""
    u = (rights_url or "").lower()
    if "publicdomain" in u or "/zero/" in u:
        return "domaine public"
    m = re.search(r"/licenses/([a-z-]+)/([0-9.]+)", u)
    return f"CC {m.group(1).upper()} {m.group(2)}" if m else ""


def europeana_search(query: str, *, min_width: int = 800, limit: int = 8,
                     timeout: int = 10) -> tuple[str, str, str]:
    """Cherche une image librement réutilisable sur Europeana. Renvoie (url, crédit,
    titre) ou ('', '', ''). Inactive (renvoie vide) sans EUROPEANA_API_KEY.

    Filtre : licence ouverte (reusability=open : CC0 / domaine public / CC-BY…), vraie
    image (pas un logo/blason), largeur suffisante, pas une forme de bandeau. On préfère
    l'image plein format (edmIsShownBy) et on retombe sur l'aperçu (edmPreview)."""
    key = os.getenv("EUROPEANA_API_KEY", "").strip()
    query = (query or "").strip()
    if not key or not query:
        return "", "", ""
    params = {
        "wskey": key, "query": query, "rows": str(limit),
        "reusability": "open", "media": "true", "thumbnail": "true",
        "qf": "TYPE:IMAGE", "profile": "rich",
    }
    try:
        r = requests.get(_EUROPEANA_API, params=params, headers=_UA, timeout=timeout)
        if r.status_code != 200:
            return "", "", ""
        items = (r.json().get("items") or [])
    except (requests.RequestException, ValueError):
        return "", "", ""
    for it in items:
        url = _first(it.get("edmIsShownBy")) or _first(it.get("edmPreview"))
        url = str(url or "")
        if not url.startswith("http") or is_logo_image(url):
            continue
        w, h = remote_dims(url)
        if w and h and (min(w, h) < min_width or looks_like_banner_shape(w, h)):
            continue
        provider = _clean(_first(it.get("dataProvider")) or _first(it.get("provider")))
        rights = _short_rights(_first(it.get("rights")))
        credit = " · ".join(p for p in (provider or None, "Europeana", rights or None) if p)[:200]
        title = _clean(_first(it.get("title")))
        return url, credit, title
    return "", "", ""
