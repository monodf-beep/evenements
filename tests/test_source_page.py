#!/usr/bin/env python3
"""Fixture : la source mémorisée est la PAGE de l'événement, pas la racine du site.

Franck, 2026-09-08 : « quand on a une URL généraliste nom de domaine, c'est qu'on n'a pas
la source de la page qui nous donne l'événement ». Mesuré : 41 des 85 fiches publiées
encore devant nous étaient sourcées à la racine (montmelian.com/, camera.to/…).

Trois choses vérifiées sans réseau :
  1. `_programme_links(…, title=)` fait remonter la page dont l'ancre ou le chemin porte
     des mots du titre, devant une page « programme » générique ;
  2. `_page_evenement` choisit la sous-page qui mentionne l'événement, jamais la racine —
     et rend '' si aucune sous-page ne le mentionne (l'appelant garde la racine) ;
  3. `affiner_source.est_racine` reconnaît une racine avec ou sans « / ».
Cas près de la frontière qui doit PASSER : un titre dont les mots sont génériques
(« festival », « édition ») ne doit pas faire élire n'importe quelle page.

Lancer : .venv/bin/python -m tests.test_source_page
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.enrich import _programme_links, _page_evenement  # noqa: E402
from scripts.affiner_source import est_racine  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


ROOT_URL = "https://montmelian.com/"
ACCUEIL = '''<html><body>
<a href="/agenda/">Agenda</a>
<a href="/programme-culturel/">Programme culturel</a>
<a href="/festival-photo-de-montmelian/">Festival Photo de Montmélian</a>
<a href="/mentions-legales/">Mentions légales</a>
<a href="https://www.facebook.com/montmelian">Facebook</a>
</body></html>'''

liens = _programme_links(ACCUEIL, ROOT_URL, limit=3, title="Festival Photo de Montmélian : cinq regards")
_check("la page de l'événement passe devant la page « programme »",
       liens and liens[0] == "https://montmelian.com/festival-photo-de-montmelian/", str(liens))
_check("les liens externes et légaux restent écartés",
       all("facebook" not in u and "mentions" not in u for u in liens), str(liens))

sans_titre = _programme_links(ACCUEIL, ROOT_URL, limit=3)
_check("sans titre : comportement d'avant (programme d'abord, l'événement n'apparaît pas)",
       sans_titre and "programme" in sans_titre[0] and not any("festival-photo" in u for u in sans_titre),
       str(sans_titre))

# ── _page_evenement : la sous-page qui mentionne l'événement, jamais la racine
pages = [
    {"url": ROOT_URL, "html": "<h1>Bienvenue à Montmélian</h1> Festival Photo de Montmélian du 15 septembre au 15 octobre"},
    {"url": "https://montmelian.com/programme-culturel/", "html": "<h1>Saison culturelle</h1> concerts, théâtre"},
    {"url": "https://montmelian.com/festival-photo-de-montmelian/", "html": "<h1>Festival Photo de Montmélian</h1> cinq photographes, regards"},
]
_check("la sous-page qui parle de l'événement est élue, pas la racine qui en parle aussi",
       _page_evenement(pages, "Festival Photo de Montmélian : cinq regards")
       == "https://montmelian.com/festival-photo-de-montmelian/")
_check("aucune sous-page ne mentionne le titre → '' (la racine reste, on ne devine pas)",
       _page_evenement(pages[:2], "Nuit des chercheurs") == "")
_check("titre sans mot significatif → '' (frontière : on n'élit pas n'importe quoi)",
       _page_evenement(pages, "Festival édition") == "")

# ── est_racine
_check("racine avec /", est_racine("https://camera.to/"))
_check("racine sans /", est_racine("https://camera.to"))
_check("page → pas racine", not est_racine("https://camera.to/mostre/foto-album/"))
_check("gmail: → pas racine", not est_racine("gmail:abc"))

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)")
    sys.exit(1)
print("Tout passe.")
