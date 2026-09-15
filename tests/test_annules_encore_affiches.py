#!/usr/bin/env python3
"""Fixture : `scripts.weekly_audits._annules_encore_affiches` compte les fiches
ANNULÉES (canal 1, `annule_le` posé) et encore EN LIGNE — le compteur « à faire »
laissé ouvert dans docs/EVENEMENTS_ANNULES.md (« Où se voit le compte »).

Cinq cas, chacun décidant seul si la fiche entre dans le compte :
  1. annulée + en ligne + à venir           → COMPTÉE (le cas nominal) ;
  2. annulée + en ligne + PASSÉE             → PAS comptée (règle 5 : archivage
     normal, un compte à surveiller ne sert à rien pour du passé) ;
  3. annulée + en ligne + RÉCURRENTE (pas de date unique) → COMPTÉE (règle 5 :
     jamais « passée » par nature) ;
  4. annulée + en ligne + SANS DATE          → COMPTÉE (règle 5 : donnée
     manquante, pas événement terminé) ;
  5. annulée mais PAS en ligne (wp_post_id_as NULL) → PAS comptée (rien à afficher
     nulle part, le compte ne sert que ce qui est visible sur le site) ;
  6. en ligne mais PAS annulée               → PAS comptée (contre-épreuve de base).

⚠️ BASE JETABLE — jamais data/events.db.

Lancer : .venv/bin/python -m tests.test_annules_encore_affiches
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
import scripts.weekly_audits as wa  # noqa: E402

conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
init_db(conn)

FICHES = [
    # id, title, annule_le, wp_post_id_as, statut_recurring, date_event_start, date_event_end
    (1, "Marché de Noël annulé — à venir",       "2026-08-01", 111, 0, "2026-12-20", "2026-12-24"),
    (2, "Festival annulé — déjà passé",           "2026-07-01", 222, 0, "2026-07-01", "2026-07-05"),
    (3, "Atelier récurrent annulé",               "2026-08-01", 333, 1, "", ""),
    (4, "Concert annulé — sans date",             "2026-08-01", 444, 0, "", ""),
    (5, "Salon annulé — pas en ligne",            "2026-08-01", None, 0, "2026-12-20", "2026-12-24"),
    (6, "Concert normal — pas annulé",            None,         666, 0, "2026-12-20", "2026-12-24"),
]
for eid, title, annule_le, wp_id, recurrent, ds, de in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, annule_le, wp_post_id_as, "
        "recurring, date_event_start, date_event_end, statut, duplicate_of) "
        "VALUES (?,?,?,?,?,?,?,?, 'published_cs', NULL)",
        (eid, title, f"https://a.fr/{eid}", annule_le, wp_id, recurrent, ds, de))
conn.commit()

# La fiche 2 (2026-07-05) fixe la frontière passé/à-venir face à AUJOURD'HUI
# (2026-08-05, cf. CLAUDE.md « currentDate ») : elle doit tomber hors du compte.
resultat = wa._annules_encore_affiches(conn)
ids_comptes = sorted(r["id"] for r in resultat)
attendu = [1, 3, 4]

echecs = 0
if ids_comptes == attendu:
    print(f"OK    ids comptés = {ids_comptes} (nominal + récurrente + sans date, "
          "ni passée ni hors-ligne)")
else:
    print(f"ÉCHEC ids comptés = {ids_comptes}, attendu {attendu}")
    echecs += 1

conn.close()

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
