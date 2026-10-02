#!/usr/bin/env python3
"""Fixture : une création sans texte rédigé ne part pas en ligne, même par --ids.

2026-09-23 : 37 fiches de Plaisirs de Culture publiées avec le texte BRUT de la brochure
(WP#11814 « Una rilettura dei monumenti cittadini », signalée par Franck). Le verrou du
22/09 ne tenait que dans la sélection automatique ; --ids passait à côté.

Ce qui doit PASSER, près de la frontière : la republication d'une fiche déjà en ligne
(même brute — c'est le seul moyen de la réparer après enrichissement), et une traduction.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_verrou_redaction_ids
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publish_batch_as import retenir_creations_brutes  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


rows = [
    {"id": 1, "wp_post_id_as": None, "enrich_data": ""},                 # création brute
    {"id": 2, "wp_post_id_as": 0, "enrich_data": "   "},                 # blancs = vide
    {"id": 3, "wp_post_id_as": None, "enrich_data": '{"article": "…"}'}, # création rédigée
    {"id": 4, "wp_post_id_as": 11814, "enrich_data": ""},                # déjà en ligne
    {"id": 5, "wp_post_id_as": None, "enrich_data": "", "translation_of": 3},  # traduction
]
ok, retenues = retenir_creations_brutes(rows)
ids_ok, ids_ret = {r["id"] for r in ok}, {r["id"] for r in retenues}
_check("la création sans texte rédigé est retenue", 1 in ids_ret, str(ids_ret))
_check("… et des blancs ne comptent pas comme un texte", 2 in ids_ret, str(ids_ret))
_check("la création rédigée part", 3 in ids_ok, str(ids_ok))
_check("FRONTIÈRE : une fiche déjà en ligne repart, même brute (seul moyen de la réparer)",
       4 in ids_ok, str(ids_ok))
_check("FRONTIÈRE : une traduction n'est pas concernée", 5 in ids_ok, str(ids_ok))
_check("rien n'est perdu : toutes les fiches sont dans l'un des deux lots",
       ids_ok | ids_ret == {1, 2, 3, 4, 5} and not (ids_ok & ids_ret))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
