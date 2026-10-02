#!/usr/bin/env python3
"""Fixture : le rapport « doublons EN LIGNE » ne confond pas deux occurrences d'un
même titre avec un doublon.

INCIDENT RÉEL, 30/09 → 01/10/2026. Quatre groupes signalés chaque matin, 12 posts
interrogés un par un par le cerveau : 0 vrai doublon, et la commande du digest aurait
corbeillé six fiches saines. Cas mesuré sur le site (API TEC) : WP#12989, #12990, #12991,
« Giornata di porte aperte all'Ecomuseo del Cossatese », les 25/10, 04/10 et 11/10.
`_groups` tolère 14 jours d'écart (pensé pour des SOURCES qui citent des bornes différentes
d'un même festival, avant fusion) ; sur des pages déjà en ligne, chacune avec sa date, ce
n'est pas un doublon.

Les deux moitiés, la seconde étant celle qui compte (CLAUDE.md, règle 3 — près de la
frontière, ce qui DOIT rester signalé) :
  A. trois occurrences à dates disjointes → rien de signalé, et le groupe défait est COMPTÉ ;
  B. même titre, même jour ; période qui en contient une autre ; une fiche sans date ;
     et un groupe mixte dont la vraie paire doit survivre au départ de la troisième.

Aucune base, aucun réseau : `analyser` reçoit des dictionnaires.
Lancer : .venv/bin/python -m tests.test_doublons_dates_disjointes
"""
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.verifier_doublons_publies as vd  # noqa: E402

AUJ = date.today()


def j(n):
    return (AUJ + timedelta(days=n)).isoformat()


echecs = 0


def _check(nom, ok, detail=""):
    global echecs
    print(("  ok   " if ok else "  ECHEC"), nom, "" if ok else f"-> {detail}")
    if not ok:
        echecs += 1


def fiche(i, titre, d1, d2="", wp=None, **kw):
    return {"id": i, "title": titre, "wp_post_id_as": wp or 9000 + i,
            "date_event_start": d1, "date_event_end": d2 or d1,
            "territoire": "piemont", "translation_of": None, "ville": "Cossato",
            "lieu": "Ecomuseo", "duplicate_of": None, **kw}


def ids(suspects):
    return {tuple(sorted(e["id"] for e in g)) for g in suspects}


T = "Giornata di porte aperte all'Ecomuseo del Cossatese e delle Baragge"

print("A. trois ouvertures hebdomadaires : pas un doublon")
s, c = vd.analyser([fiche(1, T, j(20)), fiche(2, T, j(27)), fiche(3, T, j(41))], j(0))
_check("rien n'est signalé", ids(s) == set(), ids(s))
_check("le groupe défait est COMPTÉ (règle 6), pas perdu en silence",
       c.get("dates_disjointes") == 1, c)

print("B. ce qui doit RESTER signalé")
s, c = vd.analyser([fiche(1, T, j(20)), fiche(2, T, j(20))], j(0))
_check("même titre, même jour : signalé", ids(s) == {(1, 2)}, ids(s))
_check("   et rien n'est compté comme redécoupé", not c.get("dates_disjointes"), c)

s, c = vd.analyser([fiche(1, T, j(20), j(40)), fiche(2, T, j(25))], j(0))
_check("une période qui contient l'autre : signalé", ids(s) == {(1, 2)}, ids(s))

s, c = vd.analyser([fiche(1, T, j(20)), fiche(2, T, "")], j(0))
_check("une fiche SANS date n'est pas « disjointe » (donnée manquante) : signalé",
       ids(s) == {(1, 2)}, ids(s))

s, c = vd.analyser([fiche(1, T, j(20)), fiche(2, T, j(20)), fiche(3, T, j(27))], j(0))
_check("groupe mixte : la vraie paire (1,2) survit au départ de la fiche 3",
       ids(s) == {(1, 2)}, ids(s))
_check("   et le groupe redécoupé est compté", c.get("dates_disjointes") == 1, c)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
