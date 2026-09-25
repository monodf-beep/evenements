#!/usr/bin/env python3
"""Fixture : des ids donnés SANS --retranslate restreignent la file à ces fiches, sans
plancher de score — et ceux qui ne sont pas candidats sont NOMMÉS, pas tus.

Incident du 23/09/2026 : WP#10411 (Alto Forte di Gavi) et WP#10964 (Musei Reali), fiches
des Giornate notées 5, n'avaient aucune version italienne. Le plancher par défaut est 6
et les ids n'étaient lus qu'avec --retranslate : aucune commande ne pouvait les traduire.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_traduction_ids
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.translate_events as te  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


file_du_jour = [{"id": 9}, {"id": 5814}, {"id": 3}, {"id": 5850}]
gardes, absents = te.cibler_ids(file_du_jour, [5850, 5814, 5847])
_check("seules les fiches demandées restent", [r["id"] for r in gardes] == [5814, 5850],
       str(gardes))
_check("l'ordre de la file est conservé", gardes[0]["id"] == 5814)
_check("un id demandé mais absent de la file est RENDU (pour être dit)", absents == [5847],
       str(absents))
_check("FRONTIÈRE : sans ids, rien n'est filtré", te.cibler_ids(file_du_jour, [])[0] == [])

src = (ROOT / "scripts" / "translate_events.py").read_text(encoding="utf-8")
_check("le plancher de score tombe quand des ids sont donnés",
       "plancher = 0 if cibles else args.min_score" in src)
_check("avec --retranslate, les ids gardent leur ancien sens",
       "cibles = [] if args.retranslate else" in src)

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)")
    sys.exit(1)
print("Tout passe.")
