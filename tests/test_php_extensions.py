#!/usr/bin/env python3
"""Fixture : distinguer « une extension PHP manque » de « le code est faux ».

⚠️ Aucun réseau. Lit des fichiers du dépôt et interroge `php -m` — rien d'autre.

D'OÙ ÇA VIENT (2026-09-29). `php` venait d'être installé sur le VPS pour que deux
contrôles de mu-plugins s'exercent enfin. Ils se sont exercés et ont planté :

    Call to undefined function mb_strlen() in …/cs-index-budget.php:158

`php8.3-cli` s'installe sans `mbstring`. L'erreur avait la FORME d'un bogue (une trace
d'appels) et la NATURE d'un outil absent (un paquet à installer). Une demi-heure pour
l'établir.

CE QUE LA FIXTURE SURVEILLE, et le deuxième point est le plus important :
  1. un fichier qui appelle `mb_strlen` réclame bien `mbstring` ;
  2. ⚠️ LE CAS QUI DOIT PASSER, et il protège contre le pire : une fonction INCONNUE —
     un nom mal tapé dans un mu-plugin — ne réclame RIEN. Elle plantera donc avec sa
     trace, comptée ROUGE, comme un vrai défaut. Si ce contrôle-ci tombait, le dépôt se
     mettrait à déguiser ses bogues PHP en « non exécutable » ;
  3. une extension PRÉSENTE n'est jamais annoncée manquante ;
  4. sans `php`, on ne rend rien : ce cas a déjà son message, et deux diagnostics pour
     une même panne finissent par se contredire ;
  5. le message nomme l'extension ET la commande d'installation.

Lancer : .venv/bin/python -m tests.test_php_extensions
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests import _php_extensions as X  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


tmp = Path(tempfile.mkdtemp())
(tmp / "avec_mb.php").write_text("<?php\nfunction f($s){ return mb_strlen($s); }\n",
                                 encoding="utf-8")
# Un nom de fonction MAL TAPÉ : c'est un vrai défaut, il doit planter et rester rouge.
(tmp / "faute_de_frappe.php").write_text("<?php\nfunction f(){ return cs_hub_listte(); }\n",
                                         encoding="utf-8")
(tmp / "rien.php").write_text("<?php\nfunction f($s){ return strlen($s); }\n",
                              encoding="utf-8")

print("──── ce qu'un fichier réclame ────")
_check("mb_strlen → mbstring", X.requises([tmp / "avec_mb.php"]) == {"mbstring"},
       X.requises([tmp / "avec_mb.php"]))
_check("⚠️ une fonction INCONNUE ne réclame RIEN (elle doit rester un vrai rouge)",
       X.requises([tmp / "faute_de_frappe.php"]) == set(),
       X.requises([tmp / "faute_de_frappe.php"]))
_check("   `strlen`, qui est dans le cœur de PHP, ne réclame rien non plus",
       X.requises([tmp / "rien.php"]) == set(), X.requises([tmp / "rien.php"]))
_check("un fichier absent ne fait pas tomber la lecture",
       X.requises([tmp / "jamais_ecrit.php"]) == set())

print("\n──── le fichier réel du dépôt, celui qui a planté sur le VPS ────")
reel = ROOT / "deploy" / "wordpress" / "cs-index-budget.php"
_check("cs-index-budget.php réclame bien mbstring", "mbstring" in X.requises([reel]),
       X.requises([reel]))

print("\n──── ce que cette machine a, et ce qu'elle annonce ────")
if shutil.which("php"):
    ch = X.chargees()
    _check("php -m rend une liste non vide", len(ch) > 5, len(ch))
    _check("une extension PRÉSENTE n'est jamais annoncée manquante",
           X.manquantes([reel]) == [] if "mbstring" in ch else True,
           (X.manquantes([reel]), "mbstring" in ch))
    if "mbstring" not in ch:
        _check("   (mbstring absente ici : elle EST annoncée)",
               X.manquantes([reel]) == ["mbstring"], X.manquantes([reel]))
else:
    _check("sans php, on ne rend rien — ce cas a déjà son propre message",
           X.manquantes([reel]) == [], X.manquantes([reel]))

print("\n──── le message ────")
m = X.message(["mbstring"])
_check("il nomme l'extension", "mbstring" in m, m)
_check("il dit que ce n'est PAS un succès", "pas un succès" in m, m)
_check("il donne la commande d'installation", "apt install php8.3-mbstring" in m, m)
# Et run_all doit le reconnaître — sinon la fixture compterait rouge malgré tout.
from tests.run_all import _outil_manquant  # noqa: E402
_check("run_all le classe « outil absent »", bool(_outil_manquant(m)), _outil_manquant(m))
_check("⚠️ mais il ne classe PAS une vraie trace de bogue PHP",
       not _outil_manquant("PHP Fatal error: Uncaught Error: Call to undefined "
                           "function cs_hub_listte() in cs-index-budget.php:158"))

shutil.rmtree(tmp, ignore_errors=True)
print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
