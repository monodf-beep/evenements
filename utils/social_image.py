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

from PIL import Image, ImageDraw, ImageFont

from utils import card_image

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


def _chip(draw, xy, text, accent):
    x, y = xy
    f = _font("bold", 30)
    tw = draw.textlength(text, font=f)
    pad = 18
    draw.rounded_rectangle([x, y, x + tw + pad * 2, y + 52], radius=10, fill=accent)
    draw.text((x + pad, y + 9), text, font=f, fill=(255, 255, 255))


def _terr_key(territoire: str) -> str:
    t = (territoire or "").lower()
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


def single_post(photo, *, title, date_str, territoire, site="agendasabauda.eu", size=1080):
    """Post carré 1080×1080 : photo + bandeau signé (titre, date, territoire)."""
    tk = _terr_key(territoire)
    accent = TERR_ACCENT.get(tk, TERR_ACCENT[""])
    canvas = _photo(photo, size, size).convert("RGBA")
    canvas.alpha_composite(_scrim((size, size), int(size * 0.5)))
    d = ImageDraw.Draw(canvas)
    m = 64
    if tk:
        _chip(d, (m, m), TERR_LABEL.get(tk, tk.upper()), accent)
    # Titre + date en bas.
    ft = _font("bold", 66)
    lines = _wrap(d, title, ft, size - 2 * m)[:3]
    fd = _font("bold", 40)
    total_h = len(lines) * 78 + 64
    y = size - m - total_h
    d.text((m, y), date_str, font=fd, fill=(255, 236, 200))
    y += 64
    for ln in lines:
        d.text((m, y), ln, font=ft, fill=(255, 255, 255))
        y += 78
    # Signature.
    fs = _font("bold", 30)
    d.text((m, size - m - 6), "⛰  " + site, font=fs, fill=(255, 255, 255))
    return canvas.convert("RGB")


def story(photo, *, title, date_str, territoire, site="agendasabauda.eu"):
    """Story 1080×1920 : photo + texte, SANS légende (l'API Instagram n'accepte pas
    de texte séparé sur les stories — tout doit être « cuit » dans l'image). Marges
    hautes/basses réservées pour ne pas passer sous l'UI Instagram (avatar/minuteur
    en haut, barre de réponse en bas)."""
    W, H = 1080, 1920
    TOP_SAFE, BOTTOM_SAFE = 230, 260
    tk = _terr_key(territoire)
    accent = TERR_ACCENT.get(tk, TERR_ACCENT[""])
    canvas = _photo(photo, W, H).convert("RGBA")
    canvas.alpha_composite(_scrim((W, H), int(H * 0.42)))
    d = ImageDraw.Draw(canvas)
    m = 70
    if tk:
        _chip(d, (m, TOP_SAFE), TERR_LABEL.get(tk, tk.upper()), accent)
    ft = _font("bold", 70)
    lines = _wrap(d, title, ft, W - 2 * m)[:4]
    fd = _font("bold", 42)
    total_h = len(lines) * 88 + 66
    y = H - BOTTOM_SAFE - total_h
    d.text((m, y), date_str, font=fd, fill=(255, 236, 200)); y += 66
    for ln in lines:
        d.text((m, y), ln, font=ft, fill=(255, 255, 255)); y += 88
    if y < H - BOTTOM_SAFE:
        fs = _font("bold", 34)
        d.text((m, y + 10), "⛰  " + site, font=fs, fill=(255, 255, 255))
    return canvas.convert("RGB")


def _slide_bg(size):
    return Image.new("RGB", size, BRAND_BG)


def carousel(photo, *, title, date_str, where, territoire, bullets=None,
             cta="Enregistre ce post — et invite qui tu veux y emmener.",
             site="agendasabauda.eu"):
    """Renvoie une liste de slides 1080×1350 : [accroche, détails, appel à l'action]."""
    W, H = 1080, 1350
    tk = _terr_key(territoire)
    accent = TERR_ACCENT.get(tk, TERR_ACCENT[""])
    slides = []

    # Slide 1 — accroche (photo plein cadre + titre/date).
    s1 = _photo(photo, W, H).convert("RGBA")
    s1.alpha_composite(_scrim((W, H), int(H * 0.5)))
    d = ImageDraw.Draw(s1)
    m = 70
    if tk:
        _chip(d, (m, m), TERR_LABEL.get(tk, tk.upper()), accent)
    ft = _font("bold", 74)
    lines = _wrap(d, title, ft, W - 2 * m)[:4]
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
        _chip(d, (m, m), TERR_LABEL.get(tk, tk.upper()), accent)
    y = m + 110
    fh = _font("bold", 60)
    for ln in _wrap(d, title, fh, W - 2 * m)[:3]:
        d.text((m, y), ln, font=fh, fill=INK); y += 72
    y += 20
    fi = _font("bold", 40)
    for label, val in (("📅", date_str), ("📍", where)):
        if val:
            for ln in _wrap(d, f"{label}  {val}", fi, W - 2 * m)[:2]:
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
    d.text((m, H - m - 50), "⛰  " + site, font=fs, fill=accent)
    slides.append(s3)
    return slides


def to_jpeg(img, quality=88) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()
