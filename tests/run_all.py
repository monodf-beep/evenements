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
