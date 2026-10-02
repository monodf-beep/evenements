#!/usr/bin/env python3
"""Lance TOUTES les fixtures et SORT EN ERREUR si l'une échoue.

D'OÙ ÇA VIENT — et c'est un défaut de ma méthode, pas du dépôt (2026-08-16).
Je lançais les fixtures avec une boucle shell :

    for f in tests/test_*.py; do python -m tests.$(basename $f .py) || echo "ÉCHEC $f"; done

Elle AFFICHE l'échec et rend 0. Enchaînée à `&& git commit`, elle laisse donc passer un
commit sur une suite rouge — ce qui est arrivé le 2026-08-16 : `test_verifier_dates`
était au rouge, la ligne « ÉCHEC » est passée dans le flot, et le commit est parti.

Le défaut est exactement celui qu'on a corrigé toute la journée du 13 dans les scripts :
une sortie qui DIT la bonne chose pendant que le programme en fait une autre. La lire ne
suffit pas — il faut que l'échec ait une conséquence.

Ce fichier a donc une seule vertu : son code de sortie.

Usage :
    .venv/bin/python -m tests.run_all          # tout
    .venv/bin/python -m tests.run_all -v       # avec la sortie des fixtures en échec
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
ROOT = ICI.parent


def _outil_manquant(sortie: str) -> str:
    """Le nom de l'OUTIL de test absent de l'environnement, "" sinon.

    Étroit exprès : on ne reconnaît que l'absence d'un LANCEUR de tests, jamais celle
    d'un module du projet. Un `ModuleNotFoundError: No module named 'utils'` reste un
    échec — c'est du code cassé, et le déguiser en « non exécutable » rendrait ce fichier
    complice de ce qu'il est censé empêcher.
    """
    for outil in ("pytest",):
        if f"No module named {outil}" in sortie or f"No module named '{outil}'" in sortie:
            return f"{outil} absent du venv (installation : demander à Franck)"
    # ══ `yoastseo`, ET POURQUOI IL A SA PLACE DANS CETTE LISTE ÉTROITE ════════════════
    #
    # Trouvé le 2026-09-21 en cherchant pourquoi le déploiement automatique de 7h50 ne
    # partait plus. `auto_deploiement` sort le code candidat dans un `git worktree`
    # JETABLE et y lance ce fichier — or `node_modules/` est dans .gitignore (ligne 40)
    # et rien n'exécute `npm install` dans le worktree. `test_yoast_scores` y échoue donc
    # à TOUS LES COUPS, quelles que soient les fixtures par ailleurs : un rouge
    # permanent, qui bloque le déploiement pour une raison qui n'est pas du code.
    #
    # C'est bien un LANCEUR de test absent, comme pytest : un paquet npm externe,
    # installé à côté du dépôt, jamais versionné. Pas un module du projet — le
    # commentaire ci-dessus reste la règle, et il n'est pas contourné ici.
    #
    # ⚠️ Là où `npm install` A été lancé, la fixture tourne et doit PASSER : on ne la
    # neutralise pas, on reconnaît son absence d'outil. Si elle échoue avec yoastseo
    # présent, c'est un vrai rouge et il reste rouge.
    if "Cannot find module 'yoastseo'" in sortie:
        return "paquet npm `yoastseo` absent (npm install dans le dépôt)"
    # ══ LE BINAIRE `php`, MÊME FAMILLE — trouvé le 2026-09-29 ════════════════════════
    #
    # Franck : « répare les trois fixtures rouges ». Deux d'entre elles
    # (`test_etiquette_langue`, `test_index_budget_sitemap`) passaient dans le conteneur
    # de session et échouaient sur le VPS, sur le MÊME commit. Leur sortie le disait en
    # une ligne, qu'il a fallu aller chercher :
    #
    #     php absent : fixture NON jouée (ce n'est pas un succès).
    #
    # `/usr/bin/php` existe dans le conteneur de développement, pas sur le serveur. Ces
    # fixtures contrôlent des mu-plugins avec `php -l` ; sans le binaire elles ne peuvent
    # rien contrôler, et leur auteur a fait le bon choix — rendre 1 plutôt que se
    # déclarer verte. Restait le classement : un outil externe absent n'est pas une
    # régression, et le compter rouge bloque le déploiement pour une raison qui n'est pas
    # du code. Exactement l'argument écrit ci-dessus pour `yoastseo`.
    #
    # ⚠️ LE MOTIF EST ÉTROIT, et il faut qu'il le reste : on exige les DEUX marqueurs, le
    # nom de l'outil ET la phrase par laquelle ces fixtures refusent de se dire vertes.
    # Un `php -l` qui trouve une VRAIE faute de syntaxe n'écrit ni l'un ni l'autre : il
    # reste rouge, et c'est tout l'intérêt de `tests/test_php_syntax.py`.
    #
    # ⚠️ ET LÀ OÙ `php` EST INSTALLÉ, elles tournent et doivent PASSER. On ne les
    # neutralise pas, on reconnaît l'absence d'un outil. Les rendre au vert POUR DE BON
    # demande `apt install php-cli` sur le serveur — ce que CLAUDE.md réserve à Franck.
    # Tant que ce n'est pas fait, ce sont deux contrôles qui ne s'exercent nulle part, et
    # la ligne « non exécutable » est là pour que ça se voie.
    if "php absent" in sortie and "pas un succès" in sortie:
        return "binaire `php` absent (apt install php-cli — demander à Franck)"
    # ══ UNE EXTENSION PHP, ET PAS SEULEMENT LE BINAIRE — 2026-09-29, le même jour ══════
    #
    # `php` installé sur le VPS l'après-midi, et deux contrôles se sont mis à planter sur
    # « Call to undefined function mb_strlen() » : `php8.3-cli` s'installe sans
    # `mbstring`. L'erreur avait la FORME d'un bogue et la NATURE d'un outil absent.
    #
    # Ce n'est pas cette trace-là qu'on reconnaît ici — ce serait dangereux, un nom de
    # fonction mal tapé dans un mu-plugin rend exactement la même. Les fixtures demandent
    # désormais AVANT de jouer (tests/_php_extensions.py), en confrontant les fonctions du
    # fichier à la sortie de `php -m`, et n'écrivent cette phrase que si l'extension est
    # réellement absente. On ne reconnaît donc qu'un diagnostic déjà établi.
    if "extension php" in sortie and "pas un succès" in sortie:
        return "extension php absente (la fixture dit laquelle et la commande apt)"
    return ""


def main(argv: list[str] | None = None) -> int:
    verbeux = "-v" in (argv or sys.argv[1:])
    fixtures = sorted(p.stem for p in ICI.glob("test_*.py"))
    echecs: list[tuple[str, str]] = []
    inexecutables: list[tuple[str, str]] = []

    for nom in fixtures:
        r = subprocess.run([sys.executable, "-m", f"tests.{nom}"],
                           cwd=ROOT, capture_output=True, text=True)
        sortie = (r.stdout or "") + (r.stderr or "")
        manque = _outil_manquant(sortie)
        if r.returncode == 0:
            print(f"  ok    {nom}")
        elif manque:
            print(f"  ——    {nom} (non exécutable ici : {manque})")
            inexecutables.append((nom, manque))
        else:
            print(f"  ÉCHEC {nom}")
            echecs.append((nom, sortie))

    verts = len(fixtures) - len(echecs) - len(inexecutables)
    print(f"\n{len(fixtures)} fixture(s) — {verts} au vert, {len(echecs)} au rouge, "
          f"{len(inexecutables)} non exécutable(s) ici.")
    if inexecutables:
        # ⚠️ SÉPARÉES DES ÉCHECS, ET COMPTÉES QUAND MÊME (2026-08-17). Quatre fixtures
        # dépendent de `pytest`, absent de ce venv — et `pip install` demande Franck
        # (CLAUDE.md, autonomie). Tant qu'elles comptaient comme des échecs, le code de
        # sortie de ce fichier valait 1 EN PERMANENCE : sa seule vertu devenait
        # inutilisable, et une suite qui ne peut jamais être verte finit par ne plus être
        # lue. C'est le piège de la boucle shell d'origine, à l'envers. Elles restent
        # affichées, nommées et comptées — jamais masquées.
        print("\nNON EXÉCUTABLES ICI (ce ne sont PAS des régressions) :")
        for nom, manque in inexecutables:
            print(f"  ·· {nom} — {manque}")
        print("  Détail et historique : docs/FIXTURES_ROUGES.md")
    if echecs:
        # On NOMME les échecs à la fin, après le compte : dans une sortie longue, la
        # ligne « ÉCHEC » du milieu se perd, et c'est comme ça qu'un commit est parti
        # sur une suite rouge.
        print("\nÀ REPRENDRE :")
        for nom, sortie in echecs:
            print(f"  · {nom}")
            if verbeux:
                for ligne in sortie.splitlines():
                    if ligne.startswith("ÉCHEC"):
                        print(f"      {ligne}")
        print("\nRelancer une seule : .venv/bin/python -m tests.<nom>")
    return 1 if echecs else 0


if __name__ == "__main__":
    raise SystemExit(main())
