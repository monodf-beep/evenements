#!/usr/bin/env python3
"""Fixture : les images d'une page officielle se LISENT, elles ne se cherchent pas.

Franck, 2026-09-08 : « on doit passer par des scripts pour les images ! on a la source
officielle, dans l'événement de la source officielle il y a l'image, on la prend, voilà ».
Mesuré le même jour : `images_wide` payait un agent de recherche web pour retrouver une
page déjà en base — 60 fiches tentées, 5 images trouvées, 8,91 $ (1,80 $ l'image).

`utils.images.page_image_candidates` lit la page : og:image, JSON-LD `image`, <img>.
Cette fixture vérifie l'ORDRE de confiance, le dédoublonnage, l'écartement de
l'habillage, les URL relatives, et — le cas qui doit passer près de la frontière — qu'une
page sans aucun balisage de partage rend quand même sa photo de contenu.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_images_page
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.images import page_image_candidates, orientation  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


PAGE = '''<html><head>
<meta property="og:image" content="https://www.malrauxchambery.fr/uploads/charcot-1200x630.jpg">
<meta name="twitter:image" content="https://www.malrauxchambery.fr/uploads/charcot-1200x630.jpg">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"Organization","name":"Malraux","logo":"https://www.malrauxchambery.fr/logo.png"},
 {"@type":"Event","name":"Charcot Antartica","startDate":"2026-09-25",
  "image":["https://www.malrauxchambery.fr/uploads/charcot-affiche-portrait.jpg",
           {"@type":"ImageObject","url":"https://www.malrauxchambery.fr/uploads/charcot-bandeau.jpg"}]}]}</script>
</head><body>
<img src="/assets/img/ui/logo-malraux.png" alt="">
<img data-src="/uploads/2026/07/charcot-scene.jpg" alt="scène">
<img srcset="/uploads/2026/07/charcot-salle-400.jpg 400w, /uploads/2026/07/charcot-salle-1600.jpg 1600w">
<img src="https://cdn.tracker.example/pixel.gif">
<img src="https://www.malrauxchambery.fr/uploads/charcot-1200x630.jpg">
</body></html>'''

c = page_image_candidates(PAGE, "https://www.malrauxchambery.fr/evenement/charcot-antartica-26-27/")
print("──── ordre de confiance : partage, puis JSON-LD, puis contenu ────")
_check("og:image en premier", c and c[0].endswith("charcot-1200x630.jpg"), str(c))
_check("JSON-LD : l'affiche portrait (chaîne) est lue",
       "https://www.malrauxchambery.fr/uploads/charcot-affiche-portrait.jpg" in c, str(c))
_check("JSON-LD : l'ImageObject (dict) est lu",
       "https://www.malrauxchambery.fr/uploads/charcot-bandeau.jpg" in c, str(c))
_check("JSON-LD avant les <img> de contenu",
       c.index("https://www.malrauxchambery.fr/uploads/charcot-affiche-portrait.jpg")
       < c.index("https://www.malrauxchambery.fr/uploads/2026/07/charcot-scene.jpg"), str(c))

print("\n──── nettoyage ────")
_check("og:image répété (twitter, <img>) compté une fois",
       c.count("https://www.malrauxchambery.fr/uploads/charcot-1200x630.jpg") == 1, str(c))
_check("logo du site écarté", not any("logo" in u for u in c), str(c))
_check("pixel de suivi écarté", not any("pixel" in u for u in c), str(c))
_check("URL relative résolue sur la page (data-src lazy-load)",
       "https://www.malrauxchambery.fr/uploads/2026/07/charcot-scene.jpg" in c, str(c))
_check("srcset : la plus grande source retenue",
       "https://www.malrauxchambery.fr/uploads/2026/07/charcot-salle-1600.jpg" in c
       and not any("salle-400" in u for u in c), str(c))
_check("cinq candidates, pas une de plus", len(c) == 5, str(c))

print("\n──── le cas qui doit PASSER : page sans og:image ni JSON-LD ────")
NUE = '<html><body><p>Programme</p><img src="https://x.fr/wp-content/uploads/affiche.jpg"></body></html>'
_check("la photo de contenu suffit", page_image_candidates(NUE) == ["https://x.fr/wp-content/uploads/affiche.jpg"],
       str(page_image_candidates(NUE)))
_check("page vide → rien, sans exception", page_image_candidates("") == [])
_check("JSON-LD cassé → les <img> passent quand même",
       page_image_candidates('<script type="application/ld+json">{pas du json</script>'
                             '<img src="https://x.fr/uploads/a.jpg">') == ["https://x.fr/uploads/a.jpg"])

print("\n──── orientation d'après les dimensions ────")
_check("1600×900 → paysage", orientation(1600, 900) == "wide")
_check("800×1200 → portrait", orientation(800, 1200) == "portrait")
_check("1000×1000 → ni l'un ni l'autre (carré)", orientation(1000, 1000) == "")
_check("1200×1000 → ni l'un ni l'autre (presque carré)", orientation(1200, 1000) == "")
_check("dimensions inconnues → ''", orientation(0, 500) == "")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
