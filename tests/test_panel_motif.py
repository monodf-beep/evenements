#!/usr/bin/env python3
"""Fixture : le MOTIF du panel de lecteurs, celui qui n'arrivait jamais sur WordPress.

D'OÙ ÇA VIENT. Une session WordPress a relevé le 2026-08-12 que huit verdicts `revise`
avaient `as_panel_revision` vide, et en a conclu qu'« un verdict sans motif est
inexploitable ». Le constat visait juste, la cause était fausse : `as_panel_revision` est
un STATUT ('aucune' | 'appliquée' | 'tentée'), pas un motif. Le motif, lui, n'a jamais
existé côté WordPress — alors qu'il dort dans `enrich_data`, sous forme des `manques` que
chaque persona a énoncés.

CE QUE LA FIXTURE SURVEILLE, dans cet ordre :

  1. les cas où le motif doit rester VIDE — c'est un champ vide mal interprété qui a
     produit toute cette histoire, il faut savoir exactement quand il l'est ;
  2. on ne cite QUE les personas qui ont voté la révision : agréger les manques de ceux
     qui ont dit « ok » ferait dire au motif l'inverse du verdict ;
  3. la déduplication : trois lecteurs réclament souvent la même chose ;
  4. le repli sur les conseils quand aucun manque n'est énoncé — parce que rendre "" là
     recréerait exactement le silence qu'on répare.

Lancer : .venv/bin/python -m tests.test_panel_motif
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publisher_as import motif_du_panel  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── 1. quand le motif doit rester VIDE ────")
_check("panel absent → ''", motif_du_panel({}) == "")
_check("aucune relecture → ''", motif_du_panel({"reviews": []}) == "")
_check("le panel a tout validé → '' (un « ok » n'a rien à justifier)",
       motif_du_panel({"verdict": "ok", "reviews": [
           {"persona": "Karine", "verdict": "ok", "manques": ["rien"]},
           {"persona": "Rémy", "verdict": "ok", "manques": []},
       ]}) == "")
_check("une entrée mal formée ne fait pas tomber la publication",
       motif_du_panel({"reviews": ["pas un dict", None, 42]}) == "")

print("\n──── 2. on ne cite QUE ceux qui ont voté la révision ────")
m = motif_du_panel({"verdict": "revise", "reviews": [
    {"persona": "Karine", "verdict": "ok",
     "manques": ["le prix de la buvette"]},
    {"persona": "Rémy", "verdict": "revise",
     "manques": ["aucun nom d'artiste", "pas d'horaire"]},
]})
_check("le manque du persona qui a voté la révision est là", "aucun nom d'artiste" in m, m)
_check("celui du persona qui a dit « ok » n'y est PAS — sinon le motif "
       "contredirait le verdict", "buvette" not in m, m)

print("\n──── 3. la déduplication ────")
m = motif_du_panel({"verdict": "revise", "reviews": [
    {"verdict": "revise", "manques": ["aucun nom d'artiste"]},
    {"verdict": "revise", "manques": ["Aucun nom d'artiste", "pas de tarif"]},
    {"verdict": "revise", "manques": ["aucun nom d'artiste "]},
]})
_check("trois fois le même manque ne s'écrit qu'une fois (casse et espaces ignorés)",
       m.lower().count("aucun nom d'artiste") == 1, m)
_check("   mais le manque distinct est gardé", "pas de tarif" in m, m)

print("\n──── 4. le repli, pour ne pas recréer le silence qu'on répare ────")
m = motif_du_panel({"verdict": "revise", "reviews": [
    {"verdict": "revise", "manques": [],
     "note": "Dis ce qu'on y voit, pas seulement qu'il y a un festival."},
]})
_check("aucun manque énoncé → on rend le conseil au rédacteur, jamais ''",
       "Dis ce qu'on y voit" in m, m)
m = motif_du_panel({"verdict": "revise", "reviews": [{"verdict": "revise"}]})
_check("ni manque ni conseil → '' assumé (il n'y a vraiment rien à dire)", m == "")

print("\n──── 5. la longueur reste tenable pour un méta WordPress ────")
m = motif_du_panel({"verdict": "revise", "reviews": [
    {"verdict": "revise", "manques": [f"manque numéro {i} " + "x" * 200
                                      for i in range(12)]},
]})
_check("le motif est borné", len(m) <= 400, f"→ {len(m)}")
_check("   et chaque manque est tronqué proprement, pas coupé au hasard du total",
       "manque numéro 0" in m)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
