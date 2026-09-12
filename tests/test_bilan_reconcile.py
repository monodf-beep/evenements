#!/usr/bin/env python3
"""Fixture : le bilan final de reconcile_wp_deleted, celui que lit le digest du dimanche.

D'OÙ ÇA VIENT — 2026-08-18. `weekly_audits` résume chaque étape par ses TROIS DERNIÈRES
lignes. Or ce script finissait au milieu d'un listing : le message Slack du dimanche
montrait deux fiches prises au hasard, puis « …et 90 autre(s) ».

Le lecteur y voyait une file de 92 tâches. Il n'y en avait, ce jour-là, aucune : ces
lignes sont des constats que `--apply` enregistre tout seul, et les fiches citées
dataient de mai et juin. C'est le compteur du 2026-08-11 qui recommence — « 548 tâches !
c'est ingérable » — non par un mauvais chiffre, mais par un chiffre SANS PÉRIMÈTRE ni
geste au bout.

CE QUE LA FIXTURE EXIGE DONC : que la dernière ligne dise le périmètre, isole le SEUL cas
qui demande un arbitrage humain, et range le reste sous « sans geste de votre part ». Et
qu'un zéro se distingue d'une absence de mesure.

Lancer : .venv/bin/python -m tests.test_bilan_reconcile
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.reconcile_wp_deleted import bilan  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# La situation réelle du dimanche 2026-08-17 : beaucoup de constats, aucun arbitrage.
r = bilan(disparus=0, corbeille=2, dormants=90, repartiraient=0, revenus=0, indetermines=0)
verifier("le total est annoncé", "92 fiche(s)" in r, r)
verifier("le périmètre est écrit à côté du nombre", "périmètre" in r, r)
verifier("quand rien n'est à trancher, il le DIT",
         "Aucune contradiction à trancher" in r, r)
verifier("les 90 dormantes sont rangées sous « sans geste »",
         "Sans geste de votre part" in r and "90 sans effet de bord" in r, r)
verifier("le bilan tient en trois lignes (c'est ce que _tail retient)",
         len(r.splitlines()) == 3, str(len(r.splitlines())))

# Le cas qui demande un humain doit sortir du lot, et en premier.
r2 = bilan(disparus=1, corbeille=2, dormants=90, repartiraient=3, revenus=0, indetermines=1)
lignes = r2.splitlines()
verifier("l'arbitrage apparaît en deuxième ligne, avant le reste",
         "À TRANCHER À LA MAIN : 3" in lignes[1], lignes[1])
verifier("il explique la conséquence si on ne fait rien",
         "repartiraient en ligne" in r2, r2)
verifier("le total inclut toutes les catégories", "97 fiche(s)" in r2, r2)

# Un dispositif qui n'a rien vérifié ne doit pas ressembler à un dispositif serein.
r3 = bilan(0, 0, 0, 0, 0, 0)
verifier("zéro fiche vérifiée : le total le dit franchement", "0 fiche(s)" in r3, r3)

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
