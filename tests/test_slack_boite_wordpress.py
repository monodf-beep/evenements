#!/usr/bin/env python3
"""Fixture : la boîte du jour de WordPress (deploy/wordpress/cs-slack-formulaires.php).

Deux volets, comme tests/test_php_syntax.py :

  1. la fixture PHP passe sur le fichier LIVRÉ ;
  2. CONTRE-ÉPREUVE — la même fixture, rejouée sur une version délibérément
     fautive, doit ÉCHOUER. Le défaut rejoué est celui du 2026-08-17 : purger la
     boîte par une BORNE D'HORODATAGE au lieu d'identifiants. Il détruisait un
     rapport écrit après la lecture mais dans la même seconde que le dernier
     message lu — les horodatages WordPress sont à la seconde, et quatre audits
     lancés par le même cron naissent dans la même seconde. Sans ce second volet,
     une fixture qui ne casse jamais passerait au vert sur un code faux.

`php` absent (c'est le cas sur le VPS, qui n'héberge pas WordPress) : le test le
DIT et sort en 0 — un contrôle qu'on ne peut pas faire ne doit pas bloquer, mais
il ne doit pas non plus se déguiser en succès.

Lancer : .venv/bin/python -m tests.test_slack_boite_wordpress
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "cs_slack_boite_fixture.php"
LIVRE = ROOT / "deploy" / "wordpress" / "cs-slack-formulaires.php"

# La purge par identifiants, telle qu'elle est livrée…
PURGE_LIVREE = """    $restants = [];
    foreach ($boite as $ligne) {
        if (!in_array((string) ($ligne['id'] ?? ''), $ids, true)) { $restants[] = $ligne; }
    }"""

# …et la borne d'horodatage du 2026-08-17, qui perdait un rapport.
PURGE_FAUTIVE = """    $jusqu_a = 0;
    foreach ($boite as $ligne) {
        if (in_array((string) ($ligne['id'] ?? ''), $ids, true)) {
            $jusqu_a = max($jusqu_a, (int) ($ligne['at'] ?? 0));
        }
    }
    $restants = [];
    foreach ($boite as $ligne) {
        if ((int) ($ligne['at'] ?? 0) > $jusqu_a) { $restants[] = $ligne; }
    }"""


def _jouer(fichier: Path) -> tuple[int, str]:
    r = subprocess.run(["php", str(FIXTURE)], capture_output=True, text=True,
                       env={"CS_SLACK_FICHIER": str(fichier), "PATH": "/usr/bin:/bin"})
    return r.returncode, r.stdout + r.stderr


def main() -> int:
    if not shutil.which("php"):
        print("php absent de cette machine — contrôle NON EFFECTUÉ (ce n'est pas un "
              "succès). À jouer là où php existe : php " + str(FIXTURE))
        return 0

    echecs = 0

    code, sortie = _jouer(LIVRE)
    print(sortie.rstrip())
    if code != 0:
        echecs += 1
        print("ÉCHEC la fixture ne passe pas sur le fichier livré")

    print("\n──── contre-épreuve : la borne d'horodatage du 2026-08-17 est refusée ────")
    source = LIVRE.read_text(encoding="utf-8")
    if PURGE_LIVREE not in source:
        echecs += 1
        print("ÉCHEC la purge par identifiants n'a pas été retrouvée dans le fichier — "
              "contre-épreuve impossible, donc la fixture ne prouve plus rien")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            faux = Path(tmp) / "cs-slack-formulaires-faux.php"
            faux.write_text(source.replace(PURGE_LIVREE, PURGE_FAUTIVE), encoding="utf-8")
            code, sortie = _jouer(faux)
            perdu = "le rapport écrit après la lecture SURVIT" in sortie and "ÉCHEC" in sortie
            if code != 0 and perdu:
                print("OK    la version fautive est REFUSÉE, et sur le bon motif "
                      "(le rapport écrit après la lecture est perdu)")
            else:
                echecs += 1
                print(f"ÉCHEC la version fautive n'est pas refusée (code {code}) — "
                      "la fixture ne mord pas")

    print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
    return 0 if echecs == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
