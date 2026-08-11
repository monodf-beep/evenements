#!/usr/bin/env python3
"""Fixture : un agenda annonce, il ne raconte pas.

Le cas d'entrée est réel — l'article de Stefano Mancuso publié sur agendasabauda.eu, que
Franck a signalé le 2026-08-11 : « c'est plutôt du journalisme qui pourrait se trouver
dans Nos Alpes. L'événement est déjà passé, on dit ce qui s'est fait. Ce n'est pas du tout
ce que je veux pour Agenda Sabauda. »

CE QUE LA FIXTURE PROTÈGE AVANT TOUT, et c'est l'exigence de la règle 3 de CLAUDE.md
(« la fixture doit contenir un cas qui doit PASSER, choisi près de la frontière ») : un
article d'annonce a parfaitement le droit d'employer le passé pour le CONTEXTE. « Mancuso
a publié plusieurs ouvrages », « le festival, créé en 1998, revient » : ce passé-là parle
de ce qui entoure l'événement, pas de son déroulement. Un détecteur qui refuserait tout
passé condamnerait la moitié des articles corrects et serait retiré en deux jours.

Ce qui trahit le compte rendu, c'est un verbe de DÉROULÉ conjugué au passé : quelqu'un est
intervenu, a défendu, le public a découvert.

Lancer : .venv/bin/python -m tests.test_temps_recit
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.temps_recit import extraits_de_recit, raconte  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# Texte réel, recopié de la page publiée.
MANCUSO = (
    "Le chercheur italien Stefano Mancuso est intervenu jeudi 23 juillet 2026 au Fort de "
    "Bard (Vallée d'Aoste), pour une conférence intitulée « La révolution des plantes », "
    "dans le cadre du cycle Rencontres de la manifestation Estate al Forte 2026. "
    "Devant le public du Fort, il a défendu l'idée que les végétaux produisent et gèrent "
    "leur propre énergie, communiquent entre eux et coopèrent pour survivre. Il a "
    "notamment évoqué les réseaux souterrains d'échange et d'entraide."
)

print("──── le cas signalé par Franck ────")
_check("l'article de Mancuso est reconnu comme un compte rendu", raconte(MANCUSO))
ex = extraits_de_recit(MANCUSO)
_check("… et les passages fautifs sont rendus, pas un score", len(ex) >= 2, str(ex))
_check("… « est intervenu » en fait partie",
       any("intervenu" in e for e in ex), str(ex))

print("\n──── LES CAS QUI DOIVENT PASSER — passé de CONTEXTE, près de la frontière ────")
CORRECTS = [
    "Stefano Mancuso donnera une conférence jeudi 23 juillet au Fort de Bard. Professeur "
    "à l'université de Florence, il a publié plusieurs ouvrages sur l'intelligence des "
    "plantes et dirige le Laboratoire de neurobiologie végétale.",

    "Le festival se tient du 3 au 6 décembre. Créé en 1998, il est devenu le rendez-vous "
    "des amateurs de musique baroque de la vallée.",

    "L'exposition est visible jusqu'au 20 septembre. Marc Chagall a vécu à Vence de 1950 "
    "à 1966, où il a réalisé une partie de son œuvre monumentale.",

    "La compagnie reviendra sur scène le 12 mars avec une pièce de Marivaux. Elle avait "
    "présenté L'Île des esclaves la saison précédente.",

    "Le marché a lieu chaque premier dimanche du mois sur la place du village.",
]
for texte in CORRECTS:
    _check(f"annonce correcte : « {texte[:52]}… »", not raconte(texte),
           str(extraits_de_recit(texte)))

print("\n──── d'autres formes de compte rendu, à refuser ────")
FAUTIFS = [
    "Le concert s'est tenu samedi soir dans la cour du château.",
    "Les visiteurs ont pu découvrir une trentaine d'œuvres inédites.",
    "Devant un public nombreux, la troupe a interprété la pièce en deux actes.",
    "La soirée s'est achevée par un feu d'artifice.",
]
for texte in FAUTIFS:
    _check(f"refusé : « {texte[:52]}… »", raconte(texte))

print("\n──── défensif ────")
_check("texte vide → rien", extraits_de_recit("") == [])
_check("None ne lève pas", extraits_de_recit(None) == [])
_check("trois extraits au plus (on ne recopie pas l'article)",
       len(extraits_de_recit(MANCUSO * 5)) <= 3)

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
