#!/usr/bin/env python3
"""Fixture : TOUT fichier Python du dépôt doit se compiler — sur la version MINIMALE.

Aucun réseau, aucune base, aucun import : on compile le texte, on n'exécute rien.

D'OÙ ÇA VIENT (2026-08-31, audit de simplification). `scripts/slack_digest.py` ne se
compilait PAS sous Python 3.11 : une f-string coupée sur deux lignes avec des apostrophes
imbriquées, syntaxe valide à partir de 3.12 seulement (PEP 701), introduite le 13/08.

Ce qui rendait la chose sérieuse, et pourquoi cette fixture existe :

  • `install.sh` acceptait alors **3.10+**. Le dépôt autorisait donc deux versions de
    Python sur lesquelles ce fichier ne pouvait même pas être IMPORTÉ ;
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

PUIS LE PLANCHER LUI-MÊME A BOUGÉ, le même jour et pour la même raison. Corriger la
fixture l'avait rendue rouge en permanence sur le VPS : elle exigeait un interpréteur 3.10
que la machine n'a pas, et qu'`apt` n'y propose même plus (Ubuntu 24.04). Tenir cette
promesse aurait demandé un dépôt tiers en production pour faire tourner un test. Une
compatibilité que RIEN ne vérifie est une affirmation, pas une garantie : `install.sh`
annonce donc 3.12+ depuis le 2026-09-22, ce qui est le plancher réellement tenu. Le code
reste compatible 3.10 — mesuré ce jour-là, 388 fichiers sans une faute — simplement plus
personne ne le teste, donc on ne le promet plus.

CE QUE LA FIXTURE FAIT AUJOURD'HUI, en deux garanties qui ne se remplacent pas :
  1. tout compile sous L'INTERPRÉTEUR COURANT, celui qui exécutera le code. C'est le
     risque vivant — une syntaxe plus récente que le serveur, dans un script de cron, qui
     ne se verrait qu'en production le lendemain ;
  2. tout compile au PLANCHER annoncé par `install.sh`, avec un vrai interpréteur : le
     courant quand il EST le plancher (le cas du VPS), sinon un binaire `python3.12`.
     Sans aucun des deux, elle ÉCHOUE en le disant, jamais elle ne passe au vert sans
     avoir vérifié — une mesure impossible et une mesure réussie ne doivent pas rendre le
     même résultat.

La contre-épreuve, elle, ne repose plus sur une bizarrerie de version (au plancher 3.12,
la f-string du 13/08 est légale) : elle éprouve ce qui reste vrai partout, à savoir que
le détecteur sait dire NON à une faute franche, et OUI à une source correcte.

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
CIBLE = (3, 12)

# LE PLANCHER EST DÉSORMAIS CELUI DE LA MACHINE DE PRODUCTION (VPS : 3.12.3), donc il se
# vérifie avec un interpréteur qu'on a toujours sous la main — le sien, ou un binaire
# `python3.12` là où le dépôt est relu. Plus besoin de simuler une version absente, et
# plus de fixture rouge en permanence faute d'un paquet introuvable.
if sys.version_info[:2] == CIBLE:
    _MOYEN, _BINAIRE = "courant", ""
    _COMMENT = f"l'interpréteur courant, qui EST le plancher {CIBLE[0]}.{CIBLE[1]}"
elif shutil.which(f"python{CIBLE[0]}.{CIBLE[1]}"):
    _BINAIRE = shutil.which(f"python{CIBLE[0]}.{CIBLE[1]}")
    _MOYEN, _COMMENT = "binaire", f"un vrai python{CIBLE[0]}.{CIBLE[1]} ({_BINAIRE})"
else:
    _MOYEN, _BINAIRE = "aucun", ""
    _COMMENT = (f"AUCUN moyen de vérifier le plancher : ni interpréteur courant en "
                f"{CIBLE[0]}.{CIBLE[1]} (ici "
                f"{sys.version_info.major}.{sys.version_info.minor}), ni binaire "
                f"python{CIBLE[0]}.{CIBLE[1]}")


def _compile(source: str, nom: str = "<essai>") -> str:
    """"" si la source passe au plancher, le message d'erreur sinon.

    Pas de repli silencieux vers une mesure plus faible : c'est ce repli-là — `ast`
    et son `feature_version`, qui a cessé de brider les f-strings en 3.12 — qui avait
    laissé ce garde-fou vert sans rien garantir pendant tout l'été.
    """
    if _MOYEN == "courant":
        try:
            ast.parse(source, filename=nom)
            return ""
        except SyntaxError as exc:
            return f"{exc.lineno} — {exc.msg}"
    r = subprocess.run(
        [_BINAIRE, "-c",
         "import ast,sys;ast.parse(sys.stdin.read(),filename=sys.argv[1])", nom],
        input=source, text=True, capture_output=True)
    if r.returncode == 0:
        return ""
    lignes = [l for l in (r.stderr or "").strip().splitlines() if l.strip()]
    return lignes[-1] if lignes else "refusé, sans message"

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
# La faute du 13/08 ne sert plus de contre-épreuve : au plancher 3.12, cette f-string
# est LÉGALE. On éprouve donc ce qui reste vrai partout — le détecteur sait-il dire non ?
FAUTE_FRANCHE = "def cassee(:\n    return 1\n"
_check(f"une faute de syntaxe franche est bien refusée au plancher "
       f"{CIBLE[0]}.{CIBLE[1]}", bool(_compile(FAUTE_FRANCHE)), "acceptée à tort")
# …et le cas qui doit PASSER, sans quoi la fixture serait verte sur un moyen qui refuse
# TOUT — le défaut du portillon du 2026-08-06.
_SAIN = "etat = 'envoyé' if e else 'ÉCHEC'\nx = f\"{n} rapport(s) — {etat}.\"\n"
_check("   tandis qu'une source correcte passe", not _compile(_SAIN), _compile(_SAIN))

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
