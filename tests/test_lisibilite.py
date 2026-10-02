#!/usr/bin/env python3
"""Fixture : `utils.lisibilite` compte les phrases longues et la voix passive comme
Yoast — et NE compte PAS ce qui n'en est pas.

Le journal du 2026-08-11 rappelle que le détecteur de comptes rendus prenait « est
présenté » pour un passé et « à ciel ouvert » pour l'auxiliaire avoir : un détecteur de
forme se prouve sur ses REFUS. D'où les cas qui doivent PASSER, choisis à la frontière :
  • une phrase de 20 mots pile n'est pas longue (le seuil est « plus de 20 ») ;
  • « est allée », « sont venus », « est né » : passé composé, pas passif ;
  • « est gratuit », « est ouvert » : adjectifs, pas passif ;
  • un titre « ## Programme » et une ligne de programme de deux mots ne sont pas des
    phrases ;
  • un texte vide donne 0 phrase — et l'appelant doit pouvoir le distinguer d'un texte
    parfait (règle du zéro).

Aucun réseau, fonctions pures. Lancer : .venv/bin/python -m tests.test_lisibilite
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.lisibilite import est_longue, marque_passive, mesurer, phrases  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# ── Longueur ────────────────────────────────────────────────────────────────────────
vingt = " ".join(["mot"] * 20) + "."
verifier("20 mots pile : PAS longue (le seuil est « plus de 20 »)", not est_longue(vingt))
verifier("21 mots : longue", est_longue(" ".join(["mot"] * 21) + "."))

# ── Passif : ce qui doit PASSER ─────────────────────────────────────────────────────
for ph in ["Elle est allée au festival avec ses enfants.",
           "Les artistes sont venus de cinq pays.",
           "Le peintre est né à Oran en 1936.",
           "L'entrée est gratuite pour les moins de douze ans.",
           "Le musée est ouvert tous les jours sauf le lundi.",
           # Lus dans les refus du 09/09 sur les fiches en ligne : pronominal, adverbe, adjectif.
           "Yves Saint Laurent s'est imposé comme l'un des couturiers majeurs.",
           "Le Palazzo Carignano est un monument où s’est écrite l'histoire du pays.",
           "Ce n'est jamais un simple décor pour les visiteurs.",
           "La salle est petite mais la file est longue le samedi."]:
    verifier(f"pas un passif : « {ph[:45]} »", marque_passive(ph) == "", marque_passive(ph))

# ── Passif : ce qui doit être attrapé (recopié des fiches publiées le 09/09) ────────
for ph in ["L'exposition est portée par deux commissaires.",
           "Les rencontres sont coordonnées par une bénévole.",
           "Plusieurs pièces ont été conçues à quatre mains.",
           "Son prix a été remis le jour de l'ouverture.",
           "L'exposition est annoncée au Castello di Rivoli jusqu'en octobre.",
           "Ce mercredi, c'est Le robot sauvage qui est projeté au four à pain."]:
    verifier(f"passif attrapé : « {ph[:45]} »", marque_passive(ph) != "")

# ── Découpage ───────────────────────────────────────────────────────────────────────
corps = ("Le festival ouvre le 3 août à 21 heures. ## Programme\n\n"
         "Lundi : concert. Mardi : conférence sur l'histoire des orgues de la vallée, "
         "avec un organiste venu de Turin et un historien de l'université de Grenoble, "
         "suivie d'une visite. Fin.")
ph = phrases(corps)
verifier("les titres de section et fragments < 3 mots ne sont pas des phrases",
         all(len(p.split()) >= 3 for p in ph) and not any(p.startswith("##") for p in ph), str(ph))
m = mesurer(corps)
verifier("une phrase longue sur les phrases mesurées", len(m["longues"]) == 1, str(m["longues"]))

# ── Le zéro qui ne dit rien ─────────────────────────────────────────────────────────
vide = mesurer("")
verifier("texte vide : 0 phrase (pas « 0 % de défauts »)", vide["phrases"] == 0 and vide["pc_longues"] == 0.0)

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
