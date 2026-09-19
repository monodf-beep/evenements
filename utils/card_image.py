#!/usr/bin/env python3
"""Standardise l'image d'un événement en une VIGNETTE 4:3 uniforme (« carte-événement »).

Problème : les sources mélangent paysage (photos) et portrait (affiches). Une grille
n'est lisible que si toutes les cartes ont le MÊME ratio. On fige donc le 4:3 — mais
sans mutiler l'affiche ni couper une tête. Deux stratégies, choisies automatiquement :

  • image assez PAYSAGE (ratio ≥ seuil) → recadrage « cover » 4:3 ANCRÉ sur un point
    focal (x, y). Défaut = centre ; l'humain peut l'ajuster (haut de l'affiche, visage…)
    dans le back-office → la carte se régénère.
  • image PORTRAIT → « letterbox » : l'affiche ENTIÈRE, centrée sur un fond flou d'elle-
    même, pour remplir le 4:3 sans rien couper.

L'ORIGINAL n'est jamais modifié (il reste affiché en entier sur la fiche). Ce module ne
produit QUE la vignette de carte. Pur calcul d'image (Pillow), aucune dépendance réseau.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps

# Ratio cible de la carte (validé avec Franck) : 4:3 paysage.
RATIO_W, RATIO_H = 4, 3
# Largeur de sortie par défaut (× 3/4 = hauteur). 1200×900 = net sur écran Retina.
DEFAULT_WIDTH = 1200
# En dessous de ce ratio largeur/hauteur, l'image est jugée « portrait » → letterbox
# (un vrai portrait recadré en 4:3 perdrait trop de contenu). ≥ 1.0 = carré/paysage.
LETTERBOX_BELOW = 1.0
# Mixte intelligent (mode 'auto', validé avec Franck le 2026-07-29) : une photo dont le
# ratio est déjà PROCHE du 4:3 cible peut être recadrée « cover » sans perte visible —
# un carré (1:1) ou un 3:2 photo classique n'y perdent quasi rien. Au-delà de cet écart
# relatif au ratio cible, on repasse en letterbox (affiche/portrait, panorama large : le
# recadrage couperait trop). ~0.30 laisse passer 1:1 et 3:2, exclut le 16:9 (0,78 d'écart).
COVER_TOLERANCE = 0.30
# Force du flou du fond letterbox (px).
BLUR_RADIUS = 40
# Qualité JPEG de sortie.
JPEG_QUALITY = 85


@dataclass
class CardResult:
    image: Image.Image
    mode: str          # "cover" | "letterbox"
    source_ratio: float


def _load(data) -> Image.Image:
    """Charge une image depuis des bytes, un chemin ou un objet PIL ; corrige l'EXIF."""
    if isinstance(data, Image.Image):
        img = data
    elif isinstance(data, (bytes, bytearray)):
        img = Image.open(io.BytesIO(data))
    else:  # chemin
        img = Image.open(data)
    img = ImageOps.exif_transpose(img)          # respecte l'orientation photo
    return img.convert("RGB")


def _cover(img: Image.Image, tw: int, th: int, fx: float, fy: float) -> Image.Image:
    """Recadrage « cover » : l'image REMPLIT tw×th, recadrée en gardant le point focal.

    fx, fy ∈ [0,1] : position (0=gauche/haut, 1=droite/bas) du point à préserver."""
    fx = min(max(fx, 0.0), 1.0)
    fy = min(max(fy, 0.0), 1.0)
    scale = max(tw / img.width, th / img.height)
    rw, rh = round(img.width * scale), round(img.height * scale)
    resized = img.resize((rw, rh), Image.LANCZOS)
    if scale > 1.05:
        # Agrandissement réel (source plus petite que la cible) : LANCZOS seul rend
        # l'image visiblement molle. Un renforcement léger de netteté compense sans
        # créer d'artefacts, tant que l'agrandissement reste raisonnable.
        resized = resized.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    # Fenêtre tw×th positionnée pour que le point focal reste visible et centré si possible.
    left = round((rw - tw) * fx)
    top = round((rh - th) * fy)
    left = min(max(left, 0), rw - tw)
    top = min(max(top, 0), rh - th)
    return resized.crop((left, top, left + tw, top + th))


def _letterbox(img: Image.Image, tw: int, th: int) -> Image.Image:
    """Affiche ENTIÈRE centrée sur un fond flou d'elle-même (remplit tw×th sans couper)."""
    bg = _cover(img, tw, th, 0.5, 0.5).filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
    # Assombrit légèrement le fond pour faire ressortir l'affiche nette.
    bg = Image.blend(bg, Image.new("RGB", (tw, th), (0, 0, 0)), 0.15)
    # Affiche nette « contain » dans le cadre (petite marge).
    scale = min(tw / img.width, th / img.height) * 0.96
    fw, fh = max(1, round(img.width * scale)), max(1, round(img.height * scale))
    fg = img.resize((fw, fh), Image.LANCZOS)
    bg.paste(fg, ((tw - fw) // 2, (th - fh) // 2))
    return bg


def make_card(data, *, focal=(0.5, 0.5), width: int = DEFAULT_WIDTH,
              mode: str = "auto", ratio: "tuple[int, int] | None" = None) -> CardResult:
    """Renvoie la vignette (CardResult) au ratio `ratio` (largeur, hauteur) — 4:3 par
    défaut (grille). `mode` : 'auto' | 'cover' | 'letterbox'.

    'auto' : cover si l'image est assez paysage, sinon letterbox (affiche préservée).
    `ratio` permet de réutiliser la même logique focal-aware pour un autre format,
    ex. (16, 9) pour le grand visuel de fiche (plus large que la carte de grille)."""
    rw, rh = ratio if ratio else (RATIO_W, RATIO_H)
    img = _load(data)
    tw = int(width)
    th = round(tw * rh / rw)
    src_ratio = img.width / img.height if img.height else 1.0
    use = mode
    if mode == "auto":
        # Mixte intelligent (Franck, 2026-07-29) : cover seulement si la source est déjà
        # proche du ratio cible (perte de recadrage négligeable) — sinon letterbox, qui
        # préserve l'affiche/le portrait EN ENTIER. 'cover' forcé reste possible en manuel
        # via card_mode.
        target_ratio = rw / rh
        close_to_target = (src_ratio >= 1.0 and
                            abs(src_ratio - target_ratio) / target_ratio <= COVER_TOLERANCE)
        use = "cover" if close_to_target else "letterbox"
    out = _cover(img, tw, th, focal[0], focal[1]) if use == "cover" else _letterbox(img, tw, th)
    return CardResult(image=out, mode=use, source_ratio=src_ratio)


def make_card_bytes(data, *, focal=(0.5, 0.5), width: int = DEFAULT_WIDTH,
                    mode: str = "auto", ratio: "tuple[int, int] | None" = None) -> tuple[bytes, str]:
    """Comme make_card mais renvoie (bytes JPEG, mode) — prêt à uploader vers WordPress."""
    res = make_card(data, focal=focal, width=width, mode=mode, ratio=ratio)
    buf = io.BytesIO()
    res.image.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue(), res.mode
