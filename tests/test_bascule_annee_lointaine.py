#!/usr/bin/env python3
"""Fixture : une date SANS ANNÉE dont l'année devinée bascule loin dans l'an prochain ne
date plus la fiche (scripts/dates._HORIZON_BASCULE).

Cas réel du 24/09/2026 : la Fondation Sapegno au Salone del Libro, « il 15 maggio », lu en
septembre → publié pour le 15 mai 2027, « à venir » huit mois durant. Rouge sur la version
d'avant.

Cas qui doivent PASSER, choisis près de la frontière : « le 5 janvier » lu le 20/09 (bascule
à 107 jours, légitime) ; « 15 décembre » lu en janvier (même année, 11 mois devant, pas de
bascule) ; une année ÉCRITE, même lointaine ; « 10 février » lu le 20/08 (174 jours, sous
l'horizon). Et la frontière elle-même : « 10 février » lu le 10/08 (184 jours) est refusé.

Lancer : .venv/bin/python -m tests.test_bascule_annee_lointaine
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.dates import parse_dates  # noqa: E402

echecs = 0


def cas(label, texte, ref, attendu):
    global echecs
    r = parse_dates(texte, ref)
    ok = r == attendu
    print(("OK    " if ok else "ÉCHEC ") + label + ("" if ok else f"  → {r}, attendu {attendu}"))
    echecs += 0 if ok else 1


SEPT = date(2026, 9, 20)
R = "annee_devinee_lointaine"
cas("Sapegno : « il 15 maggio » lu en septembre → refusé",
    "La Fondazione Sapegno sarà al Salone del Libro di Torino il 15 maggio", SEPT, ("", "", R))
cas("plage même mois sans année, lointaine → refusée", "dal 14 al 18 maggio", SEPT, ("", "", R))
cas("plage inter-mois sans année, lointaine → refusée", "du 27 mars au 21 juin", SEPT, ("", "", R))
cas("« le 5 janvier » lu le 20/09 → daté 2027 (bascule proche, légitime)",
    "le 5 janvier", SEPT, ("2027-01-05", "2027-01-05", "parsed"))
cas("« dal 3 al 6 dicembre » lu le 20/09 → daté 2026 (pas de bascule)",
    "dal 3 al 6 dicembre", SEPT, ("2026-12-03", "2026-12-06", "parsed"))
cas("« 15 décembre » lu en janvier → daté (même année, pas de bascule)",
    "le 15 décembre", date(2026, 1, 10), ("2026-12-15", "2026-12-15", "parsed"))
cas("année ÉCRITE, même lointaine → datée", "il 15 maggio 2027", SEPT,
    ("2027-05-15", "2027-05-15", "parsed"))
cas("plage avec année sur la fin → datée (Pizza Show)", "dal 27 marzo al 21 giugno 2026", SEPT,
    ("2026-03-27", "2026-06-21", "parsed"))
cas("« 10 febbraio » lu le 20/08 → 174 j, sous l'horizon → daté",
    "il 10 febbraio", date(2026, 8, 20), ("2027-02-10", "2027-02-10", "parsed"))
cas("« 10 febbraio » lu le 10/08 → 184 j, au-delà → refusé (la frontière)",
    "il 10 febbraio", date(2026, 8, 10), ("", "", R))

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)"); sys.exit(1)
print("Tout passe.")
