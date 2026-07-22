#!/usr/bin/env python3
"""Compose les visuels sociaux à partir des overlays RÉELS (export du design system)
+ la photo de l'événement, en remplaçant le texte d'exemple par le vrai texte.

Chaîne : overlay PNG (transparent, texte d'exemple figé « en dur ») → on efface la
zone de texte en reconstruisant le dégradé ligne par ligne (prévisible, donc sans
artefact) → on redessine le VRAI texte par-dessus → on compose sur la photo source
(déjà passée par card_image : nette même agrandie, ou repli abstrait si trop petite —
voir utils.social_image). Renvoie None si aucun overlay n'existe pour ce territoire/
format : l'appelant retombe alors sur le rendu 100% Pillow (utils.social_image),
rien ne casse tant que tous les territoires n'ont pas leurs overlays.

Convention de fichiers (AUCUN code à toucher pour activer un nouveau territoire) :
    assets/social_overlays/<slug>/post-4x5.png
    assets/social_overlays/<slug>/story-9x16.png
    assets/social_overlays/<slug>/carrousel-1.png
slugs : savoie | piemonte | vallee-aoste | nice (mêmes que social_image._terr_key).
Chaque overlay doit suivre EXACTEMENT la mise en page de l'export Savoie (mêmes
dimensions, même zone de texte) — sinon les coordonnées d'effacement ci-dessous ne
correspondront plus et il faudra les ajuster par format.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from utils.social_image import (_abstract_bg, _fits_without_mush, _font,
                                 _photo, _terr_key, _wrap_ellipsis)

ROOT = Path(__file__).resolve().parent.parent
OVERLAY_DIR = ROOT / "assets" / "social_overlays"

# Par format : taille cible, bande [y0,y1) à effacer (repère le bloc titre/date/lieu
# de l'exemple d'origine), colonne d'échantillon du dégradé (x toujours hors texte).
_SPECS = {
    "post-4x5":    {"size": (1080, 1350), "erase": (985, 1215), "sample_x": 1030},
    "story-9x16":  {"size": (1080, 1920), "erase": (1145, 1515), "sample_x": 1000},
    "carrousel-1": {"size": (1080, 1350), "erase": (1010, 1205), "sample_x": 1030},
}


def overlay_path(territoire: str, fmt: str) -> Path | None:
    tk = _terr_key(territoire)
    if not tk:
        return None
    p = OVERLAY_DIR / tk / f"{fmt}.png"
    return p if p.is_file() else None


def _erase_band(overlay: Image.Image, y0: int, y1: int, sample_x: int) -> None:
    """Repeint la bande [y0,y1) ligne par ligne avec la couleur du dégradé lue hors
    texte (colonne sample_x) — reconstruit le fond d'origine sans artefact visible."""
    w, h = overlay.size
    px = overlay.load()
    y1 = min(y1, h)
    sample_x = min(sample_x, w - 1)
    for y in range(max(y0, 0), y1):
        color = px[sample_x, y]
        for x in range(w):
            px[x, y] = color


def _render_text(overlay, fmt, *, title, date_str, where):
    """Efface le texte d'exemple et redessine le texte réel, avec une mise en page
    proche de l'export (titre gras, date/lieu atténués) — adaptée par format."""
    spec = _SPECS[fmt]
    w, h = overlay.size
    y0, y1 = spec["erase"]
    _erase_band(overlay, y0, y1, spec["sample_x"])
    d = ImageDraw.Draw(overlay)
    m = 64
    has_where = fmt != "carrousel-1"  # le slide 1 du carrousel n'a pas de ligne lieu
    title_size = 70 if fmt == "story-9x16" else 62
    max_lines = 4 if fmt == "story-9x16" else (2 if has_where else 3)
    ft = _font("bold", title_size)
    lines = _wrap_ellipsis(d, title, ft, w - 2 * m, max_lines)
    leading = int(title_size * 1.18)
    y = y0 + 24
    for ln in lines:
        d.text((m, y), ln, font=ft, fill=(255, 255, 255))
        y += leading
    fd = _font("bold", 36)
    d.text((m, y + 6), date_str, font=fd, fill=(228, 231, 238))
    y += 50
    if has_where and where:
        fl = _font("reg", 32)
        d.text((m, y + 6), where, font=fl, fill=(206, 210, 222))
    return overlay


def compose(fmt: str, territoire: str, photo: bytes, *, title: str, date_str: str,
            where: str = "") -> "Image.Image | None":
    """Renvoie l'image composée (photo + overlay texté) ou None si pas d'overlay
    disponible pour ce territoire/format (l'appelant retombe sur social_image)."""
    if fmt not in _SPECS:
        return None
    path = overlay_path(territoire, fmt)
    if not path:
        return None
    overlay = Image.open(path).convert("RGBA")
    w, h = _SPECS[fmt]["size"]
    if overlay.size != (w, h):  # export incohérent avec la spec : on n'improvise pas
        return None
    overlay = _render_text(overlay, fmt, title=title, date_str=date_str, where=where)
    if _fits_without_mush(photo, w, h):
        bg = _photo(photo, w, h).convert("RGBA")
    else:
        bg = _abstract_bg((w, h), territoire)
    return Image.alpha_composite(bg, overlay).convert("RGB")
