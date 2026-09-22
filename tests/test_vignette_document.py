#!/usr/bin/env python3
"""Fixture : la vignette d'un PDF n'est pas la photo d'un événement.

Franck, 2026-09-21, capture de la fiche « Charcot Antartica » à l'appui : « c'est souvent
qu'on a l'image de malraux au lieu de l'événement […] il aurait sûrement fallu une image
de Charcot Antartica ».

MESURÉ le jour même, en rejouant le code du dépôt sur la vraie page :
`page_image_candidates` appliqué à https://www.malrauxchambery.fr/ressources/presse — la
source mémorisée de la fiche 8289 — rendait QUATRE candidats, tous des vignettes de PDF
(brochure de saison 26-27, journal BIM, programme Cinémalraux, plan de la grande salle).
Le premier, la couverture de la brochure 26-27 (706×907), est bien l'image qui était en
ligne : comparaison visuelle faite entre le fichier servi par WordPress et le fichier
servi par le CDN de Malraux.

CONTRE-ÉPREUVE (leçon du 14/09 : « un témoin ne prouve rien s'il n'a jamais été rouge ») —
les trois défenses qui existaient AVANT ce correctif laissaient toutes passer cette image,
et la fixture le vérifie explicitement : ce n'est ni un logo (`is_logo_image`), ni de
l'habillage de thème (`_is_chrome`), ni une forme de bandeau (`looks_like_banner_shape`
sur 706×907 : ratio 1,28, entre MIN_ASPECT et MAX_ASPECT), et elle dépasse MIN_DIM.
Sans `looks_like_document_thumb`, la page presse rendait donc ses quatre couvertures.

LE CAS QUI DOIT PASSER, près de la frontière (règle 3 du CLAUDE.md) : la vraie photo de
Charcot Antartica, que la page de l'événement porte en og:image, et deux noms de fichiers
où « pdf » n'est pas le suffixe de conversion WordPress. Le motif est un SUFFIXE, jamais
une sous-chaîne — c'est la leçon « LogoEdizioneAutunnale n'est pas un logo » (08/09).

Aucun réseau. Lancer : .venv/bin/python -m tests.test_vignette_document
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.images import (looks_like_document_thumb, page_image_candidates,  # noqa: E402
                          looks_like_banner_shape, _is_chrome, MIN_DIM)
from utils.sources import is_logo_image  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


CDN = "https://cdn.malrauxchambery.fr/wp-content/uploads"
# Les quatre candidats RÉELS de la page /ressources/presse, relevés le 2026-09-21.
BROCHURE = f"{CDN}/2026/06/12113435/M-Brochure-26-27-WEB-pdf.jpg"
BIM = f"{CDN}/2026/07/16173957/M-BIM-01-SEPT-OCT_WEB-01-pdf.jpg"
CINEMA = f"{CDN}/2026/09/08122506/M-Cinemalraux-08au22sept-pdf.jpg"
PLAN = f"{CDN}/2024/07/08105245/Plan_grande_salle_malraux-pdf.jpg"
# La vraie photo du spectacle, og:image de https://www.malrauxchambery.fr/evenement/charcot-antartica-26-27/
VRAIE = f"{CDN}/2026/07/16152913/charcot-Antartica-%C2%A9-Anne-Bouillot-WEB.jpg"

print("──── les quatre vignettes de la page presse de Malraux (cas réels) ────")
for u in (BROCHURE, BIM, CINEMA, PLAN):
    _check(f"écartée : {u.rsplit('/', 1)[-1]}", looks_like_document_thumb(u))
_check("déclinaison de taille (-pdf-212x300.jpg) écartée aussi",
       looks_like_document_thumb(f"{CDN}/2026/06/M-Brochure-26-27-WEB-pdf-212x300.jpg"))

print("\n──── contre-épreuve : AVANT, aucune défense ne la voyait ────")
_check("la brochure n'est pas un logo pour is_logo_image", not is_logo_image(BROCHURE))
_check("la brochure n'est pas de l'habillage pour _is_chrome", not _is_chrome(BROCHURE))
_check("706×907 n'est pas une forme de bandeau", not looks_like_banner_shape(706, 907))
_check("706×907 dépasse MIN_DIM (donc acceptée telle quelle)", min(706, 907) >= MIN_DIM)

print("\n──── les cas qui doivent PASSER, près de la frontière ────")
_check("la vraie photo de Charcot passe", not looks_like_document_thumb(VRAIE))
_check("« pdf » en tête de nom n'est pas un suffixe de conversion",
       not looks_like_document_thumb("https://x.fr/uploads/pdfweb-affiche.jpg"))
_check("« pdf » au milieu du nom non plus",
       not looks_like_document_thumb("https://x.fr/uploads/le-grand-pdf-journal.jpg"))
_check("un dossier nommé /pdf/ ne condamne pas la photo qu'il contient",
       not looks_like_document_thumb("https://x.fr/pdf/affiche-2026.jpg"))
_check("URL vide → False, sans exception", not looks_like_document_thumb(""))

print("\n──── de bout en bout : la page presse ne propose plus rien ────")
PRESSE = f'''<html><head><meta property="og:image" content=" " /></head><body>
<img src="{BROCHURE}"><img src="{BIM}"><img src="{CINEMA}"><img src="{PLAN}">
</body></html>'''
_check("aucune couverture retenue", page_image_candidates(PRESSE, "https://www.malrauxchambery.fr/ressources/presse") == [],
       str(page_image_candidates(PRESSE)))

PAGE_EVENEMENT = f'''<html><head><meta property="og:image" content="{VRAIE}" /></head><body>
<img src="{BROCHURE}"><img src="{VRAIE}">
</body></html>'''
_check("la page de l'événement rend sa vraie photo, et elle seule",
       page_image_candidates(PAGE_EVENEMENT, "https://www.malrauxchambery.fr/evenement/charcot-antartica-26-27/")
       == [VRAIE],
       str(page_image_candidates(PAGE_EVENEMENT)))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
