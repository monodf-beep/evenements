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

print("\n──── LE CONTEXTE PARTAGÉ ENTRE CHAMPS (2026-08-31, décision de Franck) ────")
# D'OÙ ÇA VIENT : la consigne s'applique à la rédaction, champ par champ (titre, chapô,
# corps…). Sans contexte PARTAGÉ, un sigle présent dans le titre ET le corps serait
# développé DEUX FOIS — chaque appel à developper() ne voit que son propre texte. C'est
# le cas réel que scripts/enrich.py et scripts/translate_events.py doivent éviter.
vus = set()
titre = developper("Concert au TNN", "fr", vus)
corps = developper("Rendez-vous au TNN ce soir, entrée libre.", "fr", vus)
_check("le PREMIER champ développe le sigle", "Théâtre national de Nice (TNN)" in titre, titre)
_check("le SECOND champ ne le redéveloppe pas — déjà vu dans le premier",
       "Théâtre national de Nice" not in corps and "TNN" in corps, corps)
_check("le sigle est bien passé dans l'ensemble partagé", vus == {"TNN"}, vus)
# Contre-épreuve : SANS contexte partagé, le défaut se reproduit — pour être sûr que
# le test précédent prouve quelque chose, pas un hasard de formulation.
sans_contexte = developper("Rendez-vous au TNN ce soir, entrée libre.", "fr")
_check("   (contre-épreuve : sans contexte partagé, ce même champ SE développe, seul)",
       "Théâtre national de Nice (TNN)" in sans_contexte, sans_contexte)

print("\n──── LES DEUX SCRIPTS DE RÉDACTION SONT CÂBLÉS, PAS SEULEMENT LE MODULE ────")
# Décision de Franck, 2026-08-31 : « une consigne dans le ton de rédaction, comme le
# vocabulaire déjà » — ET déterministe (une consigne de FORMATAGE au milieu d'un prompt
# long peut être oubliée par le LLM ; utils.acronymes ne peut pas l'oublier). Appliqué
# SEULEMENT à la rédaction (enrich = FR, translate_events = IT), jamais en rattrapage :
# conform_articles.py (passe RÉTROACTIVE sur le stock déjà publié) n'y touche pas exprès.
enrich_src = (ROOT / "scripts" / "enrich.py").read_text(encoding="utf-8")
_check("enrich.py porte la consigne de prompt (comme le vocabulaire)",
       "config/acronymes.json" in enrich_src and "SIGLES" in enrich_src)
_check("enrich.py applique developper() de façon déterministe, contexte partagé",
       "_sigles_vus" in enrich_src and "acronymes.developper(" in enrich_src)
translate_src = (ROOT / "scripts" / "translate_events.py").read_text(encoding="utf-8")
_check("translate_events.py applique developper() en italien, même logique de contexte",
       "_sigles_vus_it" in translate_src and 'acronymes.developper(' in translate_src)
conform_src = (ROOT / "scripts" / "conform_articles.py").read_text(encoding="utf-8")
_check("conform_articles.py (rattrapage RÉTROACTIF) n'applique PAS l'expansion des sigles "
       "— décision explicite de Franck : « ce sera pour les prochaines », pas le stock",
       "acronymes.developper(" not in conform_src)

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
