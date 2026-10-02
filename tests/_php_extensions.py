#!/usr/bin/env python3
"""Quelles extensions PHP un fichier réclame-t-il, et lesquelles manquent à cette machine ?

D'OÙ ÇA VIENT — 2026-09-29. Le binaire `php` venait d'être installé sur le VPS pour que
deux contrôles de mu-plugins s'exercent enfin. Ils se sont exercés, et ils ont échoué sur
ceci :

    RuntimeError: PHP Fatal error: Uncaught Error: Call to undefined function
    mb_strlen() in /tmp/…/cs-index-budget.php:158

`php8.3-cli` s'installe avec un jeu d'extensions minimal, sans `mbstring`. Une demi-heure
pour l'établir, alors que le message le disait — mais il le disait sous la forme d'une
trace d'appels, c'est-à-dire sous la forme d'un BOGUE, pas d'un outil absent. Or ce sont
deux choses opposées : l'un demande de corriger le code, l'autre d'installer un paquet.

CE MODULE SERT À LES DISTINGUER AVANT LA PANNE, et non à interpréter la panne après coup.
La fixture demande « de quoi ce fichier a-t-il besoin, et l'ai-je ? » ; si la réponse est
non, elle le DIT et rend 1, exactement comme elle le fait déjà pour le binaire absent.
`tests/run_all.py` reconnaît alors un outil manquant et ne compte pas une régression.

⚠️ CE QU'IL NE FAUT SURTOUT PAS FAIRE, et c'est la raison de ce choix : tolérer tous les
« Call to undefined function ». Un nom de fonction mal tapé dans un mu-plugin rend
EXACTEMENT la même erreur, et c'est un vrai défaut, qui doit rester rouge. On ne reconnaît
donc que les préfixes d'extensions CONNUES, et seulement quand `php -m` confirme que
l'extension n'est pas là.

La table est volontairement courte : une famille de fonctions n'y entre que le jour où un
fichier du dépôt s'en sert. Un préfixe inconnu ne déclenche rien — mieux vaut un rouge
opaque de plus qu'un vrai bogue déguisé en « non exécutable ».
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

# préfixe (ou nom exact) de fonction/classe → extension PHP qui la fournit.
# Chaque ligne a été posée parce qu'un fichier de `deploy/wordpress/` l'emploie.
FAMILLES = {
    "mb_": "mbstring",          # cs-index-budget.php, cs-slack-formulaires.php (29/09)
    "curl_": "curl",
    "simplexml_": "simplexml",
    "iconv": "iconv",
    "DOMDocument": "dom",
    "imagecreate": "gd",
}


def requises(fichiers) -> set[str]:
    """Les extensions que ces fichiers PHP réclament, d'après les fonctions qu'ils
    appellent. Fonction PURE (lecture de fichiers seulement) — donc éprouvable."""
    besoins: set[str] = set()
    for f in fichiers:
        chemin = Path(f)
        if not chemin.exists():
            continue
        texte = chemin.read_text(encoding="utf-8", errors="replace")
        for prefixe, ext in FAMILLES.items():
            if re.search(r"\b" + re.escape(prefixe) + r"[A-Za-z_]*\s*\(", texte):
                besoins.add(ext)
    return besoins


def chargees() -> set[str]:
    """Les extensions que CE php a réellement chargées ("" si php est absent)."""
    if not shutil.which("php"):
        return set()
    try:
        r = subprocess.run(["php", "-m"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return set()
    return {l.strip().lower() for l in r.stdout.splitlines() if l.strip()
            and not l.startswith("[")}


def manquantes(fichiers) -> list[str]:
    """Les extensions réclamées par ces fichiers et absentes de cette machine, triées.

    Rend [] quand `php` lui-même est absent : ce cas-là a déjà son message, posé par les
    fixtures elles-mêmes, et deux diagnostics pour une même panne se contrediraient un
    jour (docs/ERREURS_2026-09-08.md)."""
    if not shutil.which("php"):
        return []
    presentes = chargees()
    return sorted(e for e in requises(fichiers) if e.lower() not in presentes)


def message(absentes) -> str:
    """La phrase que `run_all._outil_manquant` sait reconnaître. Elle dit « ce n'est pas
    un succès » comme celle du binaire absent : une fixture non jouée n'est pas une
    fixture verte, et le relevé doit continuer à le rappeler."""
    noms = ", ".join(f"`{e}`" for e in absentes)
    return (f"extension php {noms} absente : fixture NON jouée (ce n'est pas un succès). "
            f"Installer : apt install " + " ".join(f"php8.3-{e}" for e in absentes))
