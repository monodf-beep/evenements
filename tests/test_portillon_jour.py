#!/usr/bin/env python3
"""Fixture : le portillon du JOUR DE SEMAINE à la collecte.

Franck, 2026-08-11 : « implacable au niveau de la collecte AVANT de passer par les LLM »,
puis le soir : « je ne veux plus que les informations ne soient pas prises via les sources
officielles ».

Le contradicteur (`verifier_dates`) vérifie APRÈS publication — il a trouvé vingt-deux
fiches en ligne annonçant des événements déjà passés. Ce portillon-ci agit AVANT : quand
le texte nomme le jour et que ce jour ne colle pas à la date calculée, on ne date pas.

CE QUE LA FIXTURE PROTÈGE, et c'est le contraire de ce qu'on croit :

  1. le portillon ne doit RIEN casser de ce qui marchait — un texte sans jour nommé, ou
     dont le jour colle, se date exactement comme avant. C'est l'écrasante majorité ;
  2. il refuse de DATER, il ne corrige pas l'année. Se servir du jour pour élire une année
     aurait daté Terra Madre en 2027 (seul millésime proche où le 27 septembre tombe un
     lundi) alors que l'édition est bien en 2026 : c'est la SOURCE qui se trompe de jour ;
  3. et ce n'est pas un cul-de-sac : la fiche reste sans date, donc dans la file
     « À compléter », donc devant l'agent quotidien. Le refus attend une lecture.

Lancer : .venv/bin/python -m tests.test_portillon_jour
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.dates import parse_dates  # noqa: E402
from utils import jours  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


REF = date(2026, 8, 11)

print("──── 1. ce qui marchait doit continuer de marcher ────")
_check("aucun jour nommé → daté comme avant",
       parse_dates("Rendez-vous le 21 août 2026 au kiosque", REF)[:2]
       == ("2026-08-21", "2026-08-21"))
_check("jour nommé et JUSTE → daté (le 21/08/2026 est bien un vendredi)",
       parse_dates("Le vendredi 21 août 2026 à 21h", REF)[:2]
       == ("2026-08-21", "2026-08-21"))
_check("plage dont les deux bornes collent → datée",
       parse_dates("du samedi 15 au dimanche 16 août 2026", REF)[:2]
       == ("2026-08-15", "2026-08-16"))
_check("italien juste → daté (il 15 agosto 2026 è un sabato)",
       parse_dates("sabato 15 agosto 2026, in piazza", REF)[:2]
       == ("2026-08-15", "2026-08-15"))

print("\n──── 2. les deux causes opposées, toutes deux refusées ────")
# 1069 Paratissima : annonce de 2022 que _year() projetait en 2027.
_check("annonce ancienne (« sabato 7 maggio » = 2022) → NON datée",
       parse_dates("ti bastera venire a trovarci sabato 7 maggio dalle 16", REF)[2]
       == "jour_incoherent")
# Terra Madre : la Ville de Turin s'est trompée de jour, l'édition est bien en 2026.
_check("source qui se trompe de jour → NON datée non plus",
       parse_dates("da venerdi 24 a lunedi 27 settembre, Terra Madre torna a Torino",
                   REF)[2] == "jour_incoherent")
_check("et SURTOUT : on ne la date pas en 2027 — le jour sert à DOUTER, pas à choisir",
       parse_dates("da venerdi 24 a lunedi 27 settembre", REF)[:2] == ("", ""))

print("\n──── 3. une seule borne fausse suffit ────")
_check("plage à moitié juste = plage fausse",
       parse_dates("du samedi 15 au lundi 16 août 2026", REF)[2] == "jour_incoherent")

print("\n──── 4. le vocabulaire, et ce qu'il refuse de dire ────")
_check("« sabato 7 maggio » est lu",
       jours.jours_nommes("venire a trovarci sabato 7 maggio dalle 16") == {(5, 7): {5}})
_check("un texte qui nomme DEUX fois le même quantième garde les deux mentions",
       jours.jours_nommes("da giovedi 24 a domenica 27 settembre. Lunedi 27 settembre.")
       == {(9, 27): {6, 0}})
_check("si le texte nomme NOTRE jour ne serait-ce qu'une fois, il nous confirme",
       jours.contredit("da giovedi 24 a domenica 27 settembre. Lunedi 27 settembre.",
                       "2026-09-27") == "")
_check("le désaccord est rendu EN FRANÇAIS, pas en booléen — il finira sous des yeux",
       "samedi" in jours.contredit("sabato 7 maggio", "2027-05-07"))
_check("un jour nommé pour une AUTRE date ne juge pas la nôtre",
       jours.contredit("sabato 7 maggio", "2026-08-21") == "")
_check("les années possibles se lisent, elles ne se choisissent pas",
       jours.annees_possibles(5, 7, 5, 2027) == [2022])

print(f"\n{'TOUT PASSE' if not echecs else str(echecs) + ' ÉCHEC(S)'}")
sys.exit(1 if echecs else 0)
