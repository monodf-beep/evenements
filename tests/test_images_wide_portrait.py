#!/usr/bin/env python3
"""Fixture : une photo verticale n'est pas une affiche (étage 1 de images_wide).

Constat de Franck, 2026-09-08 : la carte de la Douja d'Or (fiche 5141, WP#8274) montrait
un portrait de sommelier pris sur doujador.it, alors que la page ouvre sur une photo
paysage. La carte 4:3 préfère url_image_portrait (format de l'AFFICHE) ; l'étage 1 y
posait la première photo verticale venue. Désormais un portrait n'est retenu que si son
NOM DE FICHIER annonce une affiche. Cas près de la frontière qui doit PASSER : un nom
d'affiche dans un chemin banal, ou avec suffixe de vignette WordPress.

Lancer : .venv/bin/python -m tests.test_images_wide_portrait
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.images_wide import nom_affiche  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


D = "https://www.doujador.it/wp-content/uploads"
_check("photo verticale de la Douja (nom de photographe) → pas une affiche",
       not nom_affiche(f"{D}/2026/07/LMR_Douja-dor_Valeria-Gallo_2025-031-bis-767x1024.jpg"))
_check("locandina avec suffixe de vignette WP → affiche",
       nom_affiche(f"{D}/2026/09/locandina-douja-2026-767x1024.jpg"))
_check("« affiche » dans le nom, chemin banal → affiche",
       nom_affiche("https://www.malrauxchambery.fr/uploads/affiche-saison-26-27.jpg"))
_check("« affiche » seulement dans le CHEMIN → non (on juge le nom)",
       not nom_affiche("https://site.fr/affiches/2026/photo-scene-12.jpg"))
_check("VERISMO_0.jpg (dossier cover, nom sans indice) → non",
       not nom_affiche("https://www.teatroregio.torino.it/sites/default/files/uploads/opera/8187/cover/VERISMO_0.jpg"))
_check("URL vide → non", not nom_affiche(""))

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)")
    sys.exit(1)
print("Tout passe.")
