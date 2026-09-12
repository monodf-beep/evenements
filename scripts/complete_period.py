#!/usr/bin/env python3
"""Bouton « Tout compléter (période) » : enchaîne les étapes idempotentes du pipeline.

Un seul clic pour amener une période au maximum de complétude, SANS le gâchis du
méga-bouton : chaque étape ne retouche que ce qui manque (idempotente), donc
rejouer ne re-paie pas ce qui est déjà fait.

Séquence (l'ordre compte) :
    1. Datation ......... date les événements encore sans date (global, déterministe)
    2. Évaluation ....... note les « pending » de la période (LLM, coûteux)
    3. Visuels .......... image pour les retenus sans photo (og → Commons → bannière)
    4. Enrichissement ... rédige l'article des retenus de la période (LLM, coûteux)

La datation d'abord (sinon la sélection par période ignore les non-datés), puis
l'évaluation (sinon l'enrichissement n'a aucun retenu à traiter).

Usage :
    python scripts/complete_period.py --from 2026-07-01 --to 2026-07-31
    python scripts/complete_period.py            # 7 prochains jours par défaut
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("complete")

# (libellé, script, borné par la période ?)
STEPS = (
    ("Datation", "scripts/dates.py", False),
    ("Évaluation", "scripts/evaluator.py", True),
    ("Visuels", "scripts/visuals.py", True),
    ("Enrichissement", "scripts/enrich.py", True),
)


def run_step(label: str, script: str, period: bool, dfrom: str, dto: str) -> bool:
    cmd = [sys.executable, str(ROOT / script)]
    if period and dfrom and dto:
        cmd += ["--from", dfrom, "--to", dto]
    log.info("▶ %s …", label)
    # Best-effort : les sous-processus héritent des flux (tout va dans le même log).
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT))
        ok = proc.returncode == 0
    except Exception as exc:  # une étape ne doit jamais casser la suite
        log.error("✗ %s : lancement impossible (%s)", label, exc)
        return False
    log.info("%s %s (code %d)", "✓" if ok else "✗", label, proc.returncode)
    return ok


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Tout compléter sur une période.")
    parser.add_argument("--from", dest="dfrom", default="")
    parser.add_argument("--to", dest="dto", default="")
    args = parser.parse_args(argv)

    today = date.today()
    dfrom = args.dfrom or today.isoformat()
    dto = args.dto or (today + timedelta(days=7)).isoformat()

    log.info("=== Tout compléter — période %s → %s ===", dfrom, dto)
    results = {label: run_step(label, script, period, dfrom, dto)
               for label, script, period in STEPS}
    done = sum(results.values())
    log.info("=== Terminé : %d/%d étape(s) OK ===", done, len(results))
    for label, ok in results.items():
        log.info("   %s %s", "✓" if ok else "✗", label)
    return 0 if done == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
