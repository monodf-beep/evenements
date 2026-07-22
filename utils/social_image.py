#!/usr/bin/env python3
"""Fabrique les VISUELS Instagram d'un événement (Pillow, sans navigateur ni réseau).

Deux formats publiables directement via l'API Instagram :
  • POST SIMPLE  — carré 1080×1080 : la photo recadrée + un bandeau signé (territoire,
    titre, date, agendasabauda.eu).
  • CARROUSEL    — portrait 1080×1350 : slide 1 accroche (photo + titre + date),
    slides intermédiaires « détails », dernière slide « appel à l'action ».

Le moteur de recadrage vient de utils.card_image (cover/letterbox → jamais de tête
coupée). On n'ajoute que du texte issu des champs réels de la fiche : rien d'inventé.
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from utils import card_image

_LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "brand" / "agenda-sabauda-logo-white.png"
_logo_cache: "Image.Image | None | bool" = False  # False = pas encore chargé


def _logo():
    """Logo « aS Agenda Sabauda » blanc (RGBA, fond transparent), ou None si absent."""
    global _logo_cache
    if _logo_cache is False:
        try:
            _logo_cache = Image.open(_LOGO_PATH).convert("RGBA")
        except Exception:
            _logo_cache = None
    return _logo_cache


def _paste_logo(canvas, x, y, target_h=56):
    """Colle le logo blanc (redimensionné à target_h de haut) en (x,y). No-op si absent."""
    logo = _logo()
    if logo is None:
        return
    w, h = logo.size
    if not h:
        return
    lw = round(w * target_h / h)
    canvas.alpha_composite(logo.resize((lw, target_h), Image.LANCZOS), (x, y))

# Palette marque (fond crème du site) + encre.
BRAND_BG = (250, 248, 243)
INK = (38, 32, 24)
MUTED = (91, 82, 64)

# Accent discret par territoire (puce + filet).
TERR_ACCENT = {
    "savoie":       (43, 74, 111),   # bleu Alpes
    "piemonte":     (122, 46, 58),   # bordeaux
    "vallee-aoste": (47, 107, 79),   # vert
    "nice":         (31, 111, 139),  # azur
    "":             (58, 47, 30),
}
TERR_LABEL = {
    "savoie": "SAVOIE", "piemonte": "PIEMONTE",
    "vallee-aoste": "VALLÉE D'AOSTE", "nice": "NICE",
}

# La Savoie a 2 départements (jamais « Haute-Savoie », voir docs/NOMMAGE_TERRITOIRES.md
# §2) — distingués par chef-lieu : Chambéry (73) / Annecy (74). Aucun champ en base ne
# porte le département (doc : « mapping ville → département, absent en base, à bâtir
# le jour venu ») — mapping ville → dept construit ici, volontairement borné aux
# communes plausibles pour un agenda culturel. Ville inconnue → pas de suffixe
# (mieux vaut « Savoie » seul qu'un département faux).
_DEPT_73 = {
    "chambery", "aix-les-bains", "aix les bains", "albertville", "moutiers",
    "saint-jean-de-maurienne", "modane", "bourg-saint-maurice", "la motte-servolex",
    "challes-les-eaux", "montmelian", "yenne", "la lechere", "ugine", "frontenex",
    "saint-michel-de-maurienne", "les arcs", "tignes", "val-thorens", "val thorens",
    "les menuires", "courchevel", "meribel", "la plagne", "valmorel",
    "pralognan-la-vanoise", "val-d'isere", "val d'isere", "termignon", "lanslebourg",
    "aussois", "valloire", "saint-francois-longchamp", "la rosiere", "peisey-nancroix",
    "landry", "seez", "saint-jean-de-belleville", "saint-martin-de-belleville",
}
_DEPT_74 = {
    "annecy", "thonon-les-bains", "thonon", "annemasse", "chamonix",
    "chamonix-mont-blanc", "megeve", "sallanches", "cluses", "evian-les-bains",
    "evian", "rumilly", "seynod", "cran-gevrier", "faverges", "bonneville",
    "saint-gervais-les-bains", "saint-gervais", "la clusaz", "le grand-bornand",
    "morzine", "les gets", "avoriaz", "talloires", "doussard", "duingt",
    "menthon-saint-bernard", "annecy-le-vieux", "publier", "sciez", "yvoire",
    "chatel", "samoens", "combloux", "praz-sur-arly", "ville-la-grand", "gaillard",
    "cranves-sales", "saint-julien-en-genevois", "passy",
}


def _norm_city(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", (name or "").strip().lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def chip_label(territoire: str, ville: str = "") -> str:
    """Texte de la puce territoire. Pour la Savoie, précise le département quand la
    ville est reconnue (« SAVOIE (DEPT. 73) ») ; sinon, libellé générique du territoire."""
    tk = _terr_key(territoire)
    if tk == "savoie":
        v = _norm_city(ville)
        if v in _DEPT_73:
            return "SAVOIE (DEPT. 73)"
        if v in _DEPT_74:
            return "SAVOIE (DEPT. 74)"
    return TERR_LABEL.get(tk, tk.upper())


_FONT_CANDIDATES = {
    "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"],
    "reg":  ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"],
}


def _font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES[kind]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _wrap_ellipsis(draw, text, font, max_w, max_lines):
    """Comme _wrap, mais si le texte dépasse max_lines, la dernière ligne affichée
    se termine par « … » (raccourcie si besoin pour tenir dans la largeur) — jamais
    de titre qui s'arrête net en plein mot sans indiquer qu'il continue."""
    lines = _wrap(draw, text, font, max_w)
    if len(lines) <= max_lines:
        return lines
    shown = lines[:max_lines]
    last, ell = shown[-1], "…"
    while last and draw.textlength(last + ell, font=font) > max_w:
        last = last[:-1].rstrip()
    shown[-1] = (last + ell) if last else ell
    return shown


def _scrim(size, height, strength=210):
    """Dégradé noir transparent (haut→bas) pour rendre le texte lisible sur la photo."""
    w, h = size
    grad = Image.new("L", (1, h), 0)
    for y in range(h):
        a = 0 if y < h - height else int(strength * (y - (h - height)) / height)
        grad.putpixel((0, y), a)
    alpha = grad.resize((w, h))
    black = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    black.putalpha(alpha)
    return black


def _top_scrim(size, height, strength=150):
    """Voile sombre en HAUT (fort→transparent vers le bas) : garantit que le logo
    et la puce restent lisibles même sur une photo à ciel clair."""
    w, h = size
    grad = Image.new("L", (1, h), 0)
    for y in range(h):
        a = int(strength * (1 - y / height)) if y < height else 0
        grad.putpixel((0, y), max(a, 0))
    alpha = grad.resize((w, h))
    black = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    black.putalpha(alpha)
    return black


def _chip(draw, xy, text, accent):
    x, y = xy
    f = _font("bold", 30)
    tw = draw.textlength(text, font=f)
    pad = 18
    draw.rounded_rectangle([x, y, x + tw + pad * 2, y + 52], radius=10, fill=accent)
    draw.text((x + pad, y + 9), text, font=f, fill=(255, 255, 255))


def _terr_key(territoire: str) -> str:
    t = _norm_city(territoire)  # normalise aussi les accents ("Piémont" -> "piemont")
    if "piemont" in t:
        return "piemonte"
    if "aost" in t or "aoste" in t:
        return "vallee-aoste"
    if "nice" in t or "nizza" in t or "maritim" in t:
        return "nice"
    if "savoie" in t or "savoia" in t:
        return "savoie"
    return ""


def _photo(data, w, h):
    res = card_image.make_card(data, width=w, mode="auto")
    img = res.image
    if img.size != (w, h):  # card_image rend du 4:3 ; on re-recadre au format voulu
        img = card_image._cover(card_image._load(data), w, h, 0.5, 0.45)
    return img.convert("RGB")


# Au-delà de cet agrandissement, même avec le renforcement de netteté de
# card_image._cover, une photo source trop petite reste visiblement floue en plein
# cadre — mieux vaut alors le repli abstrait (couleur de marque) que le mou.
MAX_UPSCALE = 1.5


def _fits_without_mush(data, w, h) -> bool:
    """La photo source est-elle assez grande pour remplir w×h sans agrandissement
    excessif ? False aussi si l'image est illisible (repli abstrait par sécurité)."""
    try:
        img = Image.open(io.BytesIO(data)) if isinstance(data, (bytes, bytearray)) else Image.open(data)
        iw, ih = img.size
    except Exception:
        return False
    if not iw or not ih:
        return False
    return max(w / iw, h / ih) <= MAX_UPSCALE


def _texture(size, opacity=36):
    """Filigrane de crêtes (esprit skyline agenda) — même rôle discret que la texture
    SVG du repli abstrait de la maquette, sans dépendre d'un asset externe."""
    w, h = size
    tex = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(tex)
    step, amp = 120, 30
    n_rows = h // step + 2
    for row in range(n_rows):
        base_y = 70 + row * step
        pts, x, up = [], -60, row % 2 == 0
        while x <= w + 60:
            pts.append((x, base_y - (amp if up else 0)))
            up = not up
            x += step // 2
        d.line(pts, fill=(255, 255, 255, opacity), width=3)
    return tex


def _abstract_bg(size, territoire):
    """Fond de repli quand la photo manque ou est trop petite pour être agrandie
    proprement : couleur de territoire + filigrane + filet clair en haut (spec
    « repli abstrait » de la maquette) — le reste (chip, titre, date, signature)
    se dessine ensuite exactement comme sur un fond photo."""
    w, h = size
    tk = _terr_key(territoire)
    accent = TERR_ACCENT.get(tk, TERR_ACCENT[""])
    canvas = Image.new("RGBA", size, accent + (255,))
    canvas.alpha_composite(_texture(size))
    ImageDraw.Draw(canvas).rectangle([0, 0, w, 14], fill=(255, 255, 255, 70))
    return canvas


def single_post(photo, *, title, date_str, territoire, ville="", site="agendasabauda.eu", size=1080):
    """Post carré 1080×1080 : photo + bandeau signé (titre, date, territoire)."""
    tk = _terr_key(territoire)
    accent = TERR_ACCENT.get(tk, TERR_ACCENT[""])
    if _fits_without_mush(photo, size, size):
        canvas = _photo(photo, size, size).convert("RGBA")
        canvas.alpha_composite(_scrim((size, size), int(size * 0.5)))
        canvas.alpha_composite(_top_scrim((size, size), int(size * 0.16)))
    else:
        canvas = _abstract_bg((size, size), territoire)
    d = ImageDraw.Draw(canvas)
    m = 64
    _paste_logo(canvas, m, m - 12)
    if tk:
        label = chip_label(territoire, ville)
        fchip = _font("bold", 30)
        chip_x = size - m - (d.textlength(label, font=fchip) + 18 * 2)
        _chip(d, (chip_x, m), label, accent)
    # Titre + date en bas ; la signature réserve SA propre place (jamais de
    # chevauchement avec la dernière ligne du titre).
    ft = _font("bold", 66)
    lines = _wrap_ellipsis(d, title, ft, size - 2 * m, 3)
    fd = _font("bold", 40)
    fs = _font("bold", 30)
    sig_h = 46
    total_h = len(lines) * 78 + 64 + sig_h
    y = size - m - total_h
    d.text((m, y), date_str, font=fd, fill=(255, 236, 200))
    y += 64
    for ln in lines:
        d.text((m, y), ln, font=ft, fill=(255, 255, 255))
        y += 78
    d.text((m, y + 8), "●  " + site, font=fs, fill=(255, 255, 255))
    return canvas.convert("RGB")


def story(photo, *, title, date_str, territoire, ville="", site="agendasabauda.eu"):
    """Story 1080×1920 : photo + texte, SANS légende (l'API Instagram n'accepte pas
    de texte séparé sur les stories — tout doit être « cuit » dans l'image). Marges
    hautes/basses réservées pour ne pas passer sous l'UI Instagram (avatar/minuteur
    en haut, barre de réponse en bas)."""
    W, H = 1080, 1920
    TOP_SAFE, BOTTOM_SAFE = 230, 260
    tk = _terr_key(territoire)
    accent = TERR_ACCENT.get(tk, TERR_ACCENT[""])
    if _fits_without_mush(photo, W, H):
        canvas = _photo(photo, W, H).convert("RGBA")
        canvas.alpha_composite(_scrim((W, H), int(H * 0.42)))
    else:
        canvas = _abstract_bg((W, H), territoire)
    d = ImageDraw.Draw(canvas)
    m = 70
    if tk:
        _chip(d, (m, TOP_SAFE), chip_label(territoire, ville), accent)
    ft = _font("bold", 70)
    lines = _wrap_ellipsis(d, title, ft, W - 2 * m, 4)
    fd = _font("bold", 42)
    total_h = len(lines) * 88 + 66
    y = H - BOTTOM_SAFE - total_h
    d.text((m, y), date_str, font=fd, fill=(255, 236, 200)); y += 66
    for ln in lines:
        d.text((m, y), ln, font=ft, fill=(255, 255, 255)); y += 88
    if y < H - BOTTOM_SAFE:
        fs = _font("bold", 34)
        d.text((m, y + 10), "●  " + site, font=fs, fill=(255, 255, 255))
    return canvas.convert("RGB")


def _slide_bg(size):
    return Image.new("RGB", size, BRAND_BG)


def carousel(photo, *, title, date_str, where, territoire, ville="", bullets=None,
             cta="Enregistre ce post. Invite qui tu veux y emmener.",
             site="agendasabauda.eu", slide1_override=None):
    """Renvoie une liste de slides 1080×1350 : [accroche, détails, appel à l'action].

    slide1_override : image déjà prête (ex. rendu utils.social_overlay) à utiliser
    telle quelle pour la 1re slide, au lieu de la construire ici."""
    W, H = 1080, 1350
    tk = _terr_key(territoire)
    accent = TERR_ACCENT.get(tk, TERR_ACCENT[""])
    slides = []
    m = 70  # marge commune, réutilisée pour la chip des slides 2/3 même si la
            # slide 1 vient toute faite (slide1_override) et saute ce bloc.

    if slide1_override is not None:
        slides.append(slide1_override.convert("RGB"))
    else:
        # Slide 1 — accroche (photo plein cadre + titre/date, ou repli abstrait si
        # la photo source est trop petite pour être agrandie proprement).
        if _fits_without_mush(photo, W, H):
            s1 = _photo(photo, W, H).convert("RGBA")
            s1.alpha_composite(_scrim((W, H), int(H * 0.5)))
        else:
            s1 = _abstract_bg((W, H), territoire)
        d = ImageDraw.Draw(s1)
        if tk:
            _chip(d, (m, m), chip_label(territoire, ville), accent)
        ft = _font("bold", 74)
        lines = _wrap_ellipsis(d, title, ft, W - 2 * m, 4)
        fd = _font("bold", 42)
        y = H - m - (len(lines) * 88 + 70)
        d.text((m, y), date_str, font=fd, fill=(255, 236, 200)); y += 70
        for ln in lines:
            d.text((m, y), ln, font=ft, fill=(255, 255, 255)); y += 88
        slides.append(s1.convert("RGB"))

    # Slide 2 — détails (fond crème).
    s2 = _slide_bg((W, H)); d = ImageDraw.Draw(s2)
    d.rectangle([0, 0, W, 12], fill=accent)
    if tk:
        _chip(d, (m, m), chip_label(territoire, ville), accent)
    y = m + 110
    fh = _font("bold", 60)
    for ln in _wrap_ellipsis(d, title, fh, W - 2 * m, 3):
        d.text((m, y), ln, font=fh, fill=INK); y += 72
    y += 20
    fi = _font("bold", 40)
    for val in (date_str, where):
        if val:
            for ln in _wrap(d, f"•  {val}", fi, W - 2 * m)[:2]:
                d.text((m, y), ln, font=fi, fill=MUTED); y += 54
            y += 8
    if bullets:
        y += 20
        fb = _font("reg", 38)
        for b in bullets[:5]:
            for ln in _wrap(d, "• " + b, fb, W - 2 * m)[:2]:
                d.text((m, y), ln, font=fb, fill=INK); y += 50
            y += 6
    slides.append(s2)

    # Slide 3 — appel à l'action.
    s3 = _slide_bg((W, H)); d = ImageDraw.Draw(s3)
    d.rectangle([0, 0, W, H], outline=accent, width=14)
    fc = _font("bold", 62)
    lines = _wrap(d, cta, fc, W - 2 * m)
    y = H // 2 - len(lines) * 40 - 60
    for ln in lines:
        d.text((m, y), ln, font=fc, fill=INK); y += 80
    fs = _font("bold", 40)
    d.text((m, H - m - 50), "●  " + site, font=fs, fill=accent)
    slides.append(s3)
    return slides


def to_jpeg(img, quality=88) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()
