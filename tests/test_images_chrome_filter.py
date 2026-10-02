#!/usr/bin/env python3
"""Fixture : un nom de fichier composé n'est pas un logo (utils.images._is_chrome).

Incident du 2026-09-08, fiche « Musicastelle Autumn Edition » (WP#4113) : la page
officielle (musicastellevda.it/musicastelle-autumn-edition/) porte un og:image tout à
fait normal — la photo de foule au concert que le site affiche lui-même en tête,
nommée « 02_Cover_LogoEdizioneAutunnale.png » (« Logo dell'Edizione Autunnale », pas
un logo isolé). L'ancien filtre `_CHROME_IMG` cherchait « logo » en SOUS-CHAÎNE dans
l'URL entière : il rejetait ce fichier, la chaîne d'images ne trouvait plus rien
d'acceptable sur cette page, et la fiche est retombée sur la bannière générique de
territoire. `utils.sources.is_logo_image` avait déjà résolu ce même piège par des
tokens de nom de fichier bornés ; `_CHROME_IMG`, plus ancien et dans un autre module,
ne l'avait jamais reçu.

Cas près de la frontière qui DOIT passer : un mot d'habillage comme fragment d'un mot
composé plus long. Cas qui DOIT rester refusé : le même mot, isolé, comme token de nom
de fichier — y compris derrière un underscore ou un tiret.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_images_chrome_filter
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.images import _is_chrome, page_image_candidates  # noqa: E402
from utils.sources import is_logo_image  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


D = "https://www.musicastellevda.it/wp-content/uploads/2026/07"

# ── Cas de l'incident, près de la frontière : DOIT passer ───────────────────────────
_check("« LogoEdizioneAutunnale » (mot composé) n'est pas un logo",
       not _is_chrome(f"{D}/02_Cover_LogoEdizioneAutunnale.png"))
_check("« catalogo.jpg » (contenait déjà « logo » en sous-chaîne) reste éligible",
       not _is_chrome("https://site.it/catalogo.jpg"))
_check("« bannerets-du-festival.jpg » (mot composé sur « banner ») reste éligible",
       not _is_chrome("https://site.fr/bannerets-du-festival.jpg"))

# ── Le même mot, isolé : DOIT rester refusé ──────────────────────────────────────────
_check("« site-logo-2026.jpg » (token isolé) reste refusé",
       _is_chrome("https://site.it/site-logo-2026.jpg"))
_check("« header-visuel.jpg » (token isolé) reste refusé",
       _is_chrome("https://site.fr/header-visuel.jpg"))
_check("« Logo_Orizzontale.png » (token isolé, underscore) reste refusé",
       _is_chrome(f"{D}/Logo_Orizzontale.png"))
_check("dossier /theme/ reste refusé (chemin, pas nom de fichier)",
       _is_chrome("https://site.fr/wp-content/theme/hero.jpg"))
_check("URL vide → non", not _is_chrome(""))

# ── Images d'INTERFACE servies en og:image (2026-09-21, fiche WP#7666) ─────────────
# La page « comunicati stampa » du Torino Film Festival déclare en og:image
# « main-hover-comunicati-2.jpg » : l'image de SURVOL d'un bouton de téléchargement. Elle
# est partie en ligne comme visuel de la fiche « Ambra Angiolini » — un rectangle blanc
# bordé de rouge avec une flèche grise. C'est `is_logo_image` qui doit l'attraper : c'est
# lui que `_acceptable` appelle sur l'og:image, là où `_is_chrome` ne voit que les images
# LUES dans la page.
_check("« main-hover-comunicati-2.jpg » est une image d'interface",
       is_logo_image("https://www.torinofilmfest.org/tt-contenuto/uploads/2019/11/"
                     "main-hover-comunicati-2.jpg"))
_check("« bouton-rollover.png » aussi", is_logo_image("https://x.fr/uploads/bouton-rollover.png"))
# Le cas qui doit PASSER, près de la frontière : le token est borné, jamais une sous-chaîne.
_check("« hovercraft-sur-le-lac.jpg » reste une photo",
       not is_logo_image("https://x.fr/uploads/hovercraft-sur-le-lac.jpg"))

# ── Bout en bout sur la vraie page (fixture, sans réseau) ───────────────────────────
PAGE = f'''<html><head>
<meta property="og:image" content="{D}/02_Cover_LogoEdizioneAutunnale.png">
</head><body>
<img src="{D}/05_NinaZilli-1-2.png">
</body></html>'''
c = page_image_candidates(PAGE, "https://www.musicastellevda.it/musicastelle-autumn-edition/")
_check("le og:image officiel est bien le premier candidat, plus jamais écarté",
       bool(c) and c[0] == f"{D}/02_Cover_LogoEdizioneAutunnale.png", str(c))

# 23/09/2026 : chiffres collés au mot — logo2025.webp (valledaostaheritage.com) passait.
_check("logo2025.webp est un logo", is_logo_image(
    "https://valledaostaheritage.com/wp-content/uploads/2025/07/logo2025.webp"))
_check("FRONTIÈRE : « biologo » et un millésime seul restent des photos",
       not is_logo_image("https://x.it/biologo-alpino.jpg")
       and not is_logo_image("https://x.it/castello-2024.jpg"))

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)")
    sys.exit(1)
print("Tout passe.")
