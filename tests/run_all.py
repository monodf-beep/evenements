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


def main(argv: list[str] | None = None) -> int:
    verbeux = "-v" in (argv or sys.argv[1:])
    fixtures = sorted(p.stem for p in ICI.glob("test_*.py"))
    echecs: list[tuple[str, str]] = []

    for nom in fixtures:
        r = subprocess.run([sys.executable, "-m", f"tests.{nom}"],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  ok    {nom}")
        else:
            print(f"  ÉCHEC {nom}")
            echecs.append((nom, (r.stdout or "") + (r.stderr or "")))

    print(f"\n{len(fixtures)} fixture(s) — {len(fixtures) - len(echecs)} au vert, "
          f"{len(echecs)} au rouge.")
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
