#!/usr/bin/env python3
"""Fixture : les sigles se développent une fois, et rien d'autre ne bouge.

Aucun réseau, aucune base.

D'OÙ ÇA VIENT. Franck, 2026-08-18 : « TNN, personne ne comprend, alors mettre théâtre
national de Nice. Je ne sais pas s'il y en a d'autres, mettre en place une règle. »

CE QUE LA FIXTURE SURVEILLE — et l'essentiel est dans ce qu'elle interdit :

  1. la PREMIÈRE mention est développée, les suivantes non. Un texte republié chaque jour
     ne doit pas accumuler « Théâtre national de Nice (Théâtre national de Nice (TNN)) » ;
  2. ⚠️ un texte qui contient DÉJÀ le développement n'est pas retouché — le cas qui doit
     passer, et celui qui casse en production si on l'oublie ;
  3. ⚠️ un sigle INCONNU du dictionnaire est laissé tel quel. On n'invente jamais un
     développement : un sigle mal développé a l'air d'une information, donc personne ne le
     vérifie ;
  4. le sigle est reconnu en MOT ENTIER — « MAO » ne se déclenche pas dans « MAOÏSTE » ;
  5. le DÉTECTEUR de candidats écarte les titres en capitales et les chiffres romains,
     tous relevés dans le corpus réel : ESTATE REALE, NOTE D'ARTE, XII Monterosa.

Lancer : .venv/bin/python -m tests.test_acronymes
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.acronymes import (a_developper, candidats, deja_developpe,  # noqa: E402
                             developpement, developper, sigles_presents)

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── le cas de Franck ────")
titre = "Le TNN en tournée dans la Métropole cet été"
_check("« TNN » est reconnu", sigles_presents(titre) == ["TNN"], sigles_presents(titre))
_check("il est signalé comme à développer", a_developper(titre) == ["TNN"])
sorti = developper(titre)
_check(f"et développé : « {sorti[:52]}… »",
       sorti.startswith("Le Théâtre national de Nice (TNN) en tournée"), sorti)

print("\n──── une seule fois, jamais deux ────")
deux = "Le TNN joue ce soir ; le TNN rejoue demain."
r = developper(deux)
_check("la première mention est développée, la seconde non",
       r.count("Théâtre national de Nice") == 1 and r.count("TNN") == 2, r)

print("\n──── ⚠️ ce qui NE doit PAS bouger — les cas qui doivent passer ────")
# SANS CE CONTRÔLE, une fiche republiée tous les jours empilerait le développement à
# chaque passage. C'est le défaut qu'on ne voit qu'au bout d'une semaine, dans le texte
# publié, jamais en relisant le code.
deja = "Le Théâtre national de Nice (TNN) ouvre sa saison ; le TNN annonce dix créations."
_check("un texte DÉJÀ développé n'est pas retouché", developper(deja) == deja,
       developper(deja))
_check("   et il n'est pas signalé comme à faire", a_developper(deja) == [], a_developper(deja))
_check("   la détection du déjà-fait ignore la casse",
       deja_developpe("le théâtre national de nice (TNN)", "TNN"))

inconnu = "Le CRR de Chambéry accueille l'ADAC pour trois soirées."
_check("⚠️ un sigle INCONNU est laissé tel quel — on n'invente pas",
       developper(inconnu) == inconnu, developper(inconnu))
_check("   et il n'apparaît pas dans la file de travail", a_developper(inconnu) == [],
       a_developper(inconnu))

print("\n──── le sigle est un MOT, pas une suite de lettres ────")
# Trouvé en écrivant cette fixture, pas en relisant le code.
_check("« MAO » ne se déclenche pas dans « MAOÏSTE »",
       sigles_presents("un discours MAOÏSTE") == [], sigles_presents("un discours MAOÏSTE"))
_check("« TNN » ne se déclenche pas dans « TNNX »", sigles_presents("code TNNX") == [])
_check("mais il se déclenche collé à une ponctuation",
       sigles_presents("au TNN, ce soir") == ["TNN"])

print("\n──── la langue commande le développement ────")
_check("en italien, c'est la forme italienne",
       developpement("TNN", "it") == "Teatro nazionale di Nizza")
_check("   et le texte italien reçoit celle-là",
       "Teatro nazionale di Nizza (TNN)" in developper("Il TNN in tournée", "it"))
_check("une langue absente du dictionnaire ne développe rien",
       developper("Le TNN joue", "es") == "Le TNN joue")

print("\n──── le DÉTECTEUR de candidats : ce qu'il ne doit PAS ramasser ────")
# Tous ces exemples viennent du corpus réel du 2026-08-17. Un détecteur naïf de
# majuscules les prendrait tous pour des sigles, et la file serait inutilisable.
bruit = "ESTATE REALE 2026. UNA SERA AL MUSEO · NOTE D'ARTE · XII Monterosa Classica"
trouves = candidats(bruit)
_check(f"aucun titre en capitales n'est proposé ({trouves})", trouves == [], trouves)
_check("un chiffre romain non plus", "XII" not in candidats("XII Monterosa Classica"))
_check("mais un vrai sigle l'est", "MAUTO" in candidats("la mostra al MAUTO di Torino"))
_check("   et il n'est proposé qu'une fois",
       candidats("MAUTO puis MAUTO encore").count("MAUTO") == 1)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
