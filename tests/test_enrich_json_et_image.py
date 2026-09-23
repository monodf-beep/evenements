#!/usr/bin/env python3
"""Fixture : deux défauts d'enrich vus sur le lot de Plaisirs de Culture, 23/09/2026.

1. « JSON invalide … Extra data » — 4 fiches sur 23 non rédigées : la capture allait de la
   première accolade à la dernière, et un texte à accolades APRÈS l'objet faisait tout
   échouer. premier_objet_json relit le premier objet complet.
2. L'og:image de la page-programme partagée (ancre #…) reposée en vignette : ce lecteur-ci
   ne demandait pas à utils.pages s'il en avait le droit.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_enrich_json_et_image
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.enrich import premier_objet_json  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


ART = '{"titre": "Tissus d\'histoire", "article": "Un texte {avec} accolades", "n": 1}'
_check("objet suivi d'un second objet : le premier est retenu",
       premier_objet_json(ART + '\n{"note": "vérifier"}') == {
           "titre": "Tissus d'histoire", "article": "Un texte {avec} accolades", "n": 1})
_check("objet suivi de prose à accolades : retenu",
       (premier_objet_json("Voici :\n" + ART + "\nRemarque {sic}.") or {}).get("n") == 1)
_check("FRONTIÈRE : un objet TRONQUÉ n'est pas rattrapé (None, la fiche reste à rédiger)",
       premier_objet_json('{"titre": "x", "article": "coupé') is None)
_check("FRONTIÈRE : une liste n'est pas une fiche", premier_objet_json("[1, 2]") is None)
_check("pas d'accolade du tout → None", premier_objet_json("rien") is None)

print("\n──── lecteur d'image d'enrich ────")
src = (ROOT / "scripts" / "enrich.py").read_text(encoding="utf-8")
i = src.index('image récupérée (og:image)')
bloc = src[i - 1500:i]
_check("la vignette de secours passe par utils.pages.peut_illustrer",
       "_peut_illustrer(" in bloc and "is_logo_image(og)" in bloc)

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
