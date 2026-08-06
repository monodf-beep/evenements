#!/usr/bin/env python3
"""Fixture : `scripts.purge_radar` écoule le stock radar non résolu laissé par la
désactivation du tier (config/sources.txt, 2026-08-05 : « trop de bruit »).

Sept cas, chacun décidant seul du sort de la fiche :
  1. radar, pending, non résolue, pas en ligne     → REJETÉE ;
  2. radar, evaluated, non résolue, pas en ligne   → REJETÉE (même motif, autre statut) ;
  3. radar, non résolue, DÉJÀ EN LIGNE             → LISTÉE, jamais touchée ;
  4. radar RÉSOLUE (url_officiel valide)           → jamais touchée (le radar a
     fait son travail) ;
  5. radar déjà 'rejected'                          → ignorée (déjà dehors) ;
  6. radar 'merged'                                  → ignorée (déjà absorbée ailleurs) ;
  7. NON radar (source officielle)                  → jamais touchée, quel que
     soit son état.

⚠️ BASE JETABLE — jamais data/events.db. Aperçu (sans --apply) ne doit RIEN écrire.

Lancer : .venv/bin/python -m tests.test_purge_radar
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.purge_radar as purge_radar  # noqa: E402

purge_radar.DB_PATH = tmp

conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
init_db(conn)

FICHES = [
    # id, title, url_source, source_type, source_name, statut, url_officiel, wp_post_id_as
    (1, "Chambéry. Cirque, danse, théâtre", "https://www.ledauphine.com/a1",
     "radar", "Le Dauphiné - Savoie", "pending", "", None),
    (2, "Turin : la semaine culturelle", "https://www.guidatorino.com/a2",
     "radar", "GuidaTorino (guide)", "evaluated", "", None),
    (3, "Nice : trois expositions à voir", "https://www.nicerendezvous.com/a3",
     "radar", "NiceRendezVous - Culture", "published_sub", "", 999),
    (4, "Musilac 2026 — Aix-les-Bains", "https://www.ledauphine.com/a4",
     "radar", "Le Dauphiné - Savoie", "evaluated", "https://www.musilac.com/", None),
    (5, "Ancien article déjà écarté", "https://www.ledauphine.com/a5",
     "radar", "Le Dauphiné - Savoie", "rejected", "", None),
    (6, "Doublon absorbé ailleurs", "https://www.ledauphine.com/a6",
     "radar", "Le Dauphiné - Savoie", "merged", "", None),
    (7, "Saison 2026-2027 de l'Espace Malraux", "https://www.malrauxchambery.fr/a7",
     "officielle", "Malraux scène nationale Chambéry", "pending", "", None),
]
for eid, title, url_source, source_type, source_name, statut, url_officiel, wp_id in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, source_type, source_name, "
        "statut, url_officiel, wp_post_id_as, duplicate_of) "
        "VALUES (?,?,?,?,?,?,?,?, NULL)",
        (eid, title, url_source, source_type, source_name, statut, url_officiel, wp_id))
conn.commit()
conn.close()

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ── 1. Aperçu (sans --apply) : rien n'est écrit ─────────────────────────────────
print("──── aperçu (sans --apply) ────")
rc = purge_radar.main([])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
statuts = {r["id"]: r["statut"] for r in conn.execute("SELECT id, statut FROM events_raw")}
conn.close()
_check("rc=0", rc == 0)
_check("id=1 toujours 'pending' (rien écrit en aperçu)", statuts[1] == "pending")
_check("id=2 toujours 'evaluated'", statuts[2] == "evaluated")

# ── 2. --apply : rejette 1 et 2, laisse tout le reste intact ────────────────────
print("\n──── --apply ────")
rc = purge_radar.main(["--apply"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
rows = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM events_raw")}
conn.close()

_check("rc=0", rc == 0)
_check("id=1 (pending, non résolue, pas en ligne) → rejetée", rows[1]["statut"] == "rejected",
       rows[1]["statut"])
_check("id=2 (evaluated, non résolue, pas en ligne) → rejetée", rows[2]["statut"] == "rejected",
       rows[2]["statut"])
_check("id=3 (non résolue, DÉJÀ EN LIGNE) → intacte", rows[3]["statut"] == "published_sub",
       rows[3]["statut"])
_check("id=4 (résolue, url_officiel Musilac) → intacte", rows[4]["statut"] == "evaluated",
       rows[4]["statut"])
_check("id=5 (déjà 'rejected') → intacte", rows[5]["statut"] == "rejected", rows[5]["statut"])
_check("id=6 (déjà 'merged') → intacte", rows[6]["statut"] == "merged", rows[6]["statut"])
_check("id=7 (NON radar) → intacte", rows[7]["statut"] == "pending", rows[7]["statut"])

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
