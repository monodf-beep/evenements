#!/usr/bin/env python3
"""Fixture : la file « À vérifier » ne doit montrer que des DOUTES, pas des absences.

Franck, 2026-08-11, capture d'écran : « 548 tâches ! c'est ingérable. Soit c'est pas
assez regroupé et du coup ça fait peur, soit la collecte n'est pas bonne, soit les 2. »
454 points sur 118 fiches — quatre par fiche, mécaniquement.

Les points de la fixture sont RECOPIÉS de cet écran. Ils montrent que la file mélangeait
deux natures :
  • le DOUTE — l'article affirme un fait dont on n'est pas sûr. Risque réel de publier
    du faux, un humain peut trancher : c'est le garde-fou, il reste visible ;
  • l'ABSENCE — la source ne publie pas l'information. L'article ne l'affirme donc pas,
    et un article qui n'affirme rien ne se trompe pas. Rien à vérifier, et personne ne
    PEUT le vérifier : Franck ne connaît pas plus que le modèle la capacité d'accueil
    d'une sortie au lac.

La frontière est testée des deux côtés, avec des cas voisins qui se ressemblent
beaucoup : « Tarifs/gratuité des activités » (absence) contre « gratuité annoncée mais
non confirmée » (doute) — même sujet, deux natures.

Lancer : .venv/bin/python -m tests.test_checks_doute
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.checks import est_doute, repartition  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# (libellé, doute attendu) — tous recopiés de la production, sauf mention.
CAS = [
    # ── ABSENCES : la source ne publie pas, rien à vérifier ────────────────────
    ("Tarifs de la Fête du Fort du Mont, de la visite gourmande et du festiv'arts", False),
    ("Contenu précis (genre, horaires) du festiv'arts de Conflans", False),
    ("Détails de la reconstitution « Les feux de 1792 » (durée, intervenants)", False),
    ("Programme détaillé des ateliers (titres, horaires, jours précis)", False),
    ("Tarifs/gratuité des activités", False),
    ("Capacités d'accueil des sorties (lacs, grotte)", False),
    ("Âges recommandés par atelier", False),
    ("Durée des sorties en journée ou demi-journée", False),
    # ── DOUTES : l'article affirme, on n'est pas sûr ───────────────────────────
    ("Date de la seconde séance de ciné plein air (une seule date trouvée)", True),
    ("Horaires d'ouverture quotidienne des jardins non confirmés", True),
    # Voisins fabriqués exprès : MÊME SUJET que des absences ci-dessus, autre nature.
    ("Gratuité annoncée mais non confirmée par la source", True),
    ("Line-up : 1 ou 2 artistes ?", True),
    ("Nom de l'artiste peut-être mal orthographié", True),
    ("Deux dates contradictoires entre le flux et la page", True),
]

print("──── doute ou absence ────")
for libelle, attendu in CAS:
    obtenu = est_doute(libelle)
    _check(f"{'DOUTE  ' if obtenu else 'absence'} ← {libelle[:60]}", obtenu == attendu,
           f"attendu {'doute' if attendu else 'absence'}")

print("\n──── répartition ────")
doutes, absences = repartition([c[0] for c in CAS])
attendu_d = sum(1 for _l, a in CAS if a)
_check(f"{len(doutes)} doute(s) et {len(absences)} absence(s)",
       len(doutes) == attendu_d and len(absences) == len(CAS) - attendu_d)
_check("aucun point n'est perdu au passage", len(doutes) + len(absences) == len(CAS))

# La proportion est le vrai enjeu : sur cet échantillon réel, la file affichée est
# divisée par plus de deux. En production, sur 454 points, l'ordre de grandeur attendu
# est bien plus favorable encore — mais c'est la production qui le dira, pas moi.
_check("l'écran serait nettement allégé", len(doutes) < len(CAS) / 2,
       f"{len(doutes)}/{len(CAS)}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
