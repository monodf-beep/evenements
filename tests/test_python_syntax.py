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

CE QUI A CHANGÉ LE 2026-09-22, et c'est la fixture elle-même qui l'a dit. Sur le VPS
(Python 3.12.3), la contre-épreuve est passée au ROUGE : « la f-string PEP 701 du 13/08
est bien refusée en 3.10 — acceptée à tort ». Mesuré ici sur les trois interpréteurs
réels, la même faute est REFUSÉE par 3.10 et 3.11, et ACCEPTÉE par 3.12.

`ast.parse(..., feature_version=(3, 10))` n'a jamais promis de rejouer la grammaire de
3.10 : il ne bride que certaines constructions, et l'analyse lexicale des f-strings a été
réécrite en 3.12. Sur 3.12, ce garde-fou a donc CESSÉ DE GARDER — et pas seulement sa
contre-épreuve : le contrôle principal aussi. Un fichier portant la faute du 13/08 serait
passé au vert sur le VPS, puis aurait planté sur toute machine en 3.10 ou 3.11.

C'est le défaut que ce dépôt traque le plus souvent : un portillon qui ne peut plus
attraper sa propre cible, et qui reste vert. Ici la contre-épreuve a joué son rôle — elle
était rouge pendant que le contrôle principal, lui, mentait en vert. Sans elle, rien ne
l'aurait dit.

CE QU'ON FAIT À LA PLACE : on ne SIMULE plus l'ancienne version, on la LANCE. S'il existe
un vrai interpréteur au plancher de `install.sh`, c'est lui qui compile. À défaut, et si
l'interpréteur courant est antérieur à 3.12, `feature_version` reste digne de foi. Dans
tous les autres cas, la fixture ÉCHOUE en disant qu'elle ne peut pas tenir sa promesse —
jamais elle ne passe au vert sans avoir vérifié. Une mesure impossible et une mesure
réussie ne doivent pas rendre le même résultat.

Lancer : .venv/bin/python -m tests.test_python_syntax
"""
import ast
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# La version la plus BASSE que `install.sh` accepte. C'est elle qui doit compiler, pas
# celle qui tourne ici — sinon la fixture passe au vert sur une machine récente et laisse
# le piège intact pour la machine qui l'a réellement.
CIBLE = (3, 10)

# `feature_version` ne bride plus l'analyse des f-strings à partir de cette version.
_PREMIERE_VERSION_MENTEUSE = (3, 12)

_BINAIRE = shutil.which(f"python{CIBLE[0]}.{CIBLE[1]}")
if _BINAIRE:
    _MOYEN = "binaire"
    _COMMENT = f"un vrai python{CIBLE[0]}.{CIBLE[1]} ({_BINAIRE})"
elif sys.version_info[:2] < _PREMIERE_VERSION_MENTEUSE:
    _MOYEN = "feature_version"
    _COMMENT = (f"ast.feature_version, digne de foi sous "
                f"{_PREMIERE_VERSION_MENTEUSE[0]}.{_PREMIERE_VERSION_MENTEUSE[1]} "
                f"(ici {sys.version_info.major}.{sys.version_info.minor})")
else:
    _MOYEN = "aucun"
    _COMMENT = (f"AUCUN moyen de vérifier : Python "
                f"{sys.version_info.major}.{sys.version_info.minor} tourne ici, et "
                f"feature_version n'y bride plus les f-strings")


def _compile(source: str, nom: str = "<essai>") -> str:
    """"" si la source passe au plancher, le message d'erreur sinon.

    Le MOYEN est choisi une fois pour toutes ci-dessus. Il n'y a volontairement pas de
    repli silencieux du binaire vers feature_version : se rabattre sur une mesure plus
    faible sans le dire, c'est exactement ce qui a produit ce correctif.
    """
    if _MOYEN == "binaire":
        r = subprocess.run(
            [_BINAIRE, "-c",
             "import ast,sys;ast.parse(sys.stdin.read(),filename=sys.argv[1])", nom],
            input=source, text=True, capture_output=True)
        if r.returncode == 0:
            return ""
        derniere = [l for l in (r.stderr or "").strip().splitlines() if l.strip()]
        return derniere[-1] if derniere else "refusé, sans message"
    try:
        ast.parse(source, filename=nom, feature_version=CIBLE[1])
        return ""
    except SyntaxError as exc:
        return f"{exc.lineno} — {exc.msg}"
    except (ValueError, OSError) as exc:
        return f"illisible ({exc})"

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
print(f"      moyen de vérification : {_COMMENT}")
# LA PROMESSE D'ABORD. Sans moyen de vérifier le plancher, cette fixture ne peut rien
# garantir : elle le DIT et elle échoue, au lieu de passer au vert sur une vérification
# qu'elle n'a pas faite. Les deux sorties sont écrites, parce que c'est un arbitrage.
_check(f"un moyen existe de vérifier le plancher {CIBLE[0]}.{CIBLE[1]}",
       _MOYEN != "aucun",
       f"\n      → soit installer python{CIBLE[0]}.{CIBLE[1]} sur cette machine "
       f"(apt install python{CIBLE[0]}.{CIBLE[1]}),"
       f"\n      → soit relever le plancher d'install.sh à "
       f"{sys.version_info.major}.{sys.version_info.minor} si plus aucune machine "
       f"n'utilise {CIBLE[0]}.{CIBLE[1]} — et simplifier cette fixture en conséquence.")
# Un ensemble vide passerait au vert sans rien vérifier — le « zéro sans dénominateur »
# que ce dépôt traque. On l'interdit d'abord.
_check(f"le dépôt expose bien des fichiers à compiler ({len(fichiers)})",
       len(fichiers) >= 150, len(fichiers))

# D'ABORD LA GARANTIE TOUJOURS DISPONIBLE, et elle vaut pour elle-même : tout fichier
# doit compiler sous L'INTERPRÉTEUR QUI VA L'EXÉCUTER. C'est le risque vivant — une
# syntaxe plus récente que le serveur, dans un script lancé par cron, qui ne se verrait
# qu'en production le lendemain. Elle ne dépend d'aucun binaire annexe, donc elle reste
# verte même pendant qu'on discute du plancher.
casses_ici = []
for f in fichiers:
    try:
        ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
    except SyntaxError as exc:
        casses_ici.append(f"{f.relative_to(ROOT)}:{exc.lineno} — {exc.msg}")
    except OSError as exc:
        casses_ici.append(f"{f.relative_to(ROOT)} — illisible ({exc})")
_check(f"tous compilent sous l'interpréteur courant "
       f"({sys.version_info.major}.{sys.version_info.minor}, celui qui les exécutera)",
       not casses_ici, "\n      " + "\n      ".join(casses_ici[:10]))

casses = []
if _MOYEN != "aucun":
    for f in fichiers:
        try:
            texte = f.read_text(encoding="utf-8")
        except OSError as exc:  # illisible : à dire, pas à taire
            casses.append(f"{f.relative_to(ROOT)} — illisible ({exc})")
            continue
        souci = _compile(texte, str(f))
        if souci:
            casses.append(f"{f.relative_to(ROOT)}:{souci}")

    _check(f"tous compilent sous Python {CIBLE[0]}.{CIBLE[1]} (la version minimale "
           f"d'install.sh)", not casses,
           "\n      " + "\n      ".join(casses[:10]))

print("\n──── contre-épreuve : cette fixture sait-elle REFUSER ? ────")
# Sans ça, elle ne prouverait que sa capacité à dire oui — le défaut du portillon du
# 2026-08-06, passé au vert sur un design faux. On lui donne la faute RÉELLE du 13/08.
FAUTE_REELLE = ("x = f\"{n} rapport(s) — {'envoyé' if e else 'ÉCHEC, '\n"
                "     'suite de la chaîne'}.\"\n")
if _MOYEN == "aucun":
    print("      (sautée : sans moyen de vérifier, elle ne prouverait rien)")
else:
    _check(f"la f-string PEP 701 du 13/08 est bien refusée en "
           f"{CIBLE[0]}.{CIBLE[1]}", bool(_compile(FAUTE_REELLE)), "acceptée à tort")
    # …et le cas qui doit PASSER, choisi juste à côté : la même intention, écrite
    # autrement. Sans lui, la fixture serait verte sur un moyen qui refuse TOUT.
    _CORRIGE = ("etat = 'envoyé' if e else 'ÉCHEC'\n"
                "x = f\"{n} rapport(s) — {etat}.\"\n")
    _check("   tandis que la forme corrigée (variable extraite) passe",
           not _compile(_CORRIGE), _compile(_CORRIGE))

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
