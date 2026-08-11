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

La frontière a été DÉPLACÉE le jour même, après un second retour de Franck (« on a
encore trop de tâches !!! ») : j'avais rangé « non confirmé » parmi les doutes, alors que
le modèle l'emploie pour dire que la source se tait. L'absence est donc testée en premier
et l'emporte, même sur un point d'interrogation — un silence bien formulé reste un
silence.

Ce que la fixture protège désormais, c'est le doute qui doit SURVIVRE à ce durcissement :
« l'organisateur annoncé semble être la journaliste, pas l'organisatrice ». Celui-là vaut
à lui seul la file entière, et un tri trop sévère l'emporterait avec le reste.

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
    # ── SECONDE PASSE, même jour : « non confirmé » est une ABSENCE ─────────────
    # Après le premier tri il restait 138 points et Franck : « on a encore trop de
    # tâches !!! ». J'avais rangé « non confirmé » parmi les DOUTES. Or le modèle
    # l'emploie pour dire « la source ne le dit pas ». Ces quatre-là viennent de l'écran,
    # et aucun n'est vérifiable par qui que ce soit.
    ("Horaires d'ouverture quotidienne des jardins non confirmés", False),
    ("Gratuité de l'accès non confirmée explicitement par la matière", False),
    ("Date et horaire précis de la rencontre « Face à face » non confirmés", False),
    # Celui-ci passait grâce à son point d'interrogation : un silence bien formulé
    # reste un silence, donc l'absence l'emporte sur la question.
    ("Lieu exact de la rencontre (salle, foyer ?) non précisé dans la matière", False),
    # ── Et le doute qui doit SURVIVRE au durcissement : c'est le seul point de tout
    # l'écran sur lequel un humain peut agir, et il vaut à lui seul la file entière.
    ("Organisateur réel de la foire (Arabella Pezza semble être une journaliste, "
     "pas l'organisatrice)", True),
    # Voisins fabriqués exprès : MÊME SUJET que des absences ci-dessus, autre nature.
    # « Annoncée mais non confirmée » : le mot « non confirmée » l'emporte, et
    # c'est voulu — on ne peut pas confirmer ce que la source ne dit pas.
    ("Gratuité annoncée mais non confirmée par la source", False),
    ("Line-up : 1 ou 2 artistes ?", True),
    ("Nom de l'artiste peut-être mal orthographié", True),
    ("Deux dates contradictoires entre le flux et la page", True),
    # ── TROISIÈME PASSE : les questions qui RÉCLAMENT DU CONTENU ────────────────
    # 66 doutes restaient sur 453 points, et une famille entière passait encore grâce au
    # point d'interrogation. Toutes recopiées de la production. Ce qui les distingue d'un
    # vrai doute : elles demandent CE QU'IL Y A, jamais si ce qui est écrit est JUSTE.
    ("Contenu précis de l'exposition Chine : artefacts, maquettes, films ?", False),
    ("composition précise du programme : quelles œuvres exactement de Brahms ?", False),
    ("Thèmes concrets des ateliers (nature, histoire, archéologie ?)", False),
    ("Nombre et niveau des stagiaires (amateurs, tous âges ?)", False),
    ("y a-t-il d'autres musiciens à la distribution (piano) ?", False),
    ("Nationalités précises des troupes (Mexique, Bénin — autres pays ?)", False),
    # ── Et les questions d'IDENTITÉ, qui doivent survivre : elles demandent si ce
    # qui est écrit est juste, et un humain peut trancher en ouvrant la page.
    ("Stefania Marchiano : autrice de l'article ou organisatrice ?", True),
    ("Rôle exact d'Amelio Ambrosi : organisateur ou contact presse ?", True),
    ("Chef d'orchestre : Jonathan Nott est-il toujours en poste en 2026 ?", True),
    ("Vence fait-elle bien partie du territoire métropolitain annoncé ?", True),
    ("Date de fin de tournée : 28 août (Métropole) ou 29 août (site TNN) ?", True),
    ("Nom exact de l'organisateur (Emilie DUPONT confirmé ?)", True),
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
