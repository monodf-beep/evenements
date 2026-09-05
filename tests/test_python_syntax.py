#!/usr/bin/env python3
"""Fixture : TOUT fichier Python du dépôt doit se compiler — sur la version MINIMALE.

Aucun réseau, aucune base, aucun import : on compile le texte, on n'exécute rien.

D'OÙ ÇA VIENT (2026-08-31, audit de simplification). `scripts/slack_digest.py` ne se
compilait PAS sous Python 3.11 : une f-string coupée sur deux lignes avec des apostrophes
imbriquées, syntaxe valide à partir de 3.12 seulement (PEP 701), introduite le 13/08.

Ce qui rendait la chose sérieuse, et pourquoi cette fixture existe :

  • `install.sh` accepte **3.10+**. Le dépôt autorisait donc deux versions de Python sur
    lesquelles ce fichier ne pouvait même pas être IMPORTÉ ;
  • `slack_digest` est le SEUL canal vers Franck (vidages de 11h45 et 20h). Sa panne
    n'aurait pas ressemblé à une panne : à une journée calme. C'est le pire mode de
    défaillance de ce dépôt, celui que `consigne_bilan_matin.txt` nomme lui-même ;
  • **aucune fixture ne l'importait**, donc la porte de déploiement (`auto_deploiement`,
    qui joue toutes les fixtures avant de déployer) ne pouvait pas le voir. Un fichier que
    personne n'importe est un fichier que rien ne compile.

Le pendant Python de `tests/test_php_syntax.py`, et pour la même raison qu'elle : une
faute de syntaxe dans un fichier lancé par cron ne se voit qu'en production, le lendemain,
dans un journal que personne n'ouvre.

Lancer : .venv/bin/python -m tests.test_python_syntax
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# La version la plus BASSE que `install.sh` accepte. C'est elle qui doit compiler, pas
# celle qui tourne ici — sinon la fixture passe au vert sur une machine récente et laisse
# le piège intact pour la machine qui l'a réellement.
CIBLE = (3, 10)

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


fichiers = sorted(p for d in ("scripts", "utils", "app", "tests")
                  for p in (ROOT / d).rglob("*.py"))

print(f"──── compilation des {len(fichiers)} fichiers Python du dépôt ────")
# Un ensemble vide passerait au vert sans rien vérifier — le « zéro sans dénominateur »
# que ce dépôt traque. On l'interdit d'abord.
_check(f"le dépôt expose bien des fichiers à compiler ({len(fichiers)})",
       len(fichiers) >= 150, len(fichiers))

casses = []
for f in fichiers:
    try:
        ast.parse(f.read_text(encoding="utf-8"), filename=str(f),
                  feature_version=CIBLE[1])
    except SyntaxError as exc:
        casses.append(f"{f.relative_to(ROOT)}:{exc.lineno} — {exc.msg}")
    except (OSError, ValueError) as exc:  # illisible : à dire, pas à taire
        casses.append(f"{f.relative_to(ROOT)} — illisible ({exc})")

_check(f"tous compilent sous Python {CIBLE[0]}.{CIBLE[1]} (la version minimale "
       f"d'install.sh)", not casses,
       "\n      " + "\n      ".join(casses[:10]))

print("\n──── contre-épreuve : cette fixture sait-elle REFUSER ? ────")
# Sans ça, elle ne prouverait que sa capacité à dire oui — le défaut du portillon du
# 2026-08-06, passé au vert sur un design faux. On lui donne la faute RÉELLE du 13/08.
FAUTE_REELLE = ("x = f\"{n} rapport(s) — {'envoyé' if e else 'ÉCHEC, '\n"
                "     'suite de la chaîne'}.\"\n")
try:
    ast.parse(FAUTE_REELLE, feature_version=CIBLE[1])
    _check("la f-string PEP 701 du 13/08 est bien refusée en 3.10", False,
           "acceptée à tort")
except SyntaxError:
    _check("la f-string PEP 701 du 13/08 est bien refusée en 3.10", True)
# …et le cas qui doit PASSER, choisi juste à côté : la même intention, écrite autrement.
try:
    ast.parse("etat = 'envoyé' if e else 'ÉCHEC'\nx = f\"{n} rapport(s) — {etat}.\"\n",
              feature_version=CIBLE[1])
    _check("   tandis que la forme corrigée (variable extraite) passe", True)
except SyntaxError as exc:
    _check("   tandis que la forme corrigée (variable extraite) passe", False, str(exc))

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
