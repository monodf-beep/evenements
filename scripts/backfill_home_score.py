#!/usr/bin/env python3
"""Backfill de la colonne `home_score` depuis `enrich_data` (JSON).

Les fiches enrichies AVANT l'ajout de la colonne `home_score` ont le score dans
`enrich_data["home"]["score"]` mais `home_score = NULL`. Ce one-shot recopie la valeur en
colonne, pour que la sélection de la home (méta `as_home_score`) puisse trier dessus.

Idempotent : ne touche que les lignes où `home_score IS NULL` et où le JSON porte un score.
Usage : python -m scripts.backfill_home_score   (puis republier : python -m scripts.publish_batch_as --update)
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.scraper_events import init_db  # garantit la présence de la colonne

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)  # crée home_score si absente (migration idempotente)
    rows = conn.execute(
        "SELECT id, enrich_data FROM events_raw "
        "WHERE enrich_data IS NOT NULL AND enrich_data != '' AND home_score IS NULL"
    ).fetchall()
    done = 0
    for id_, ed in rows:
        try:
            score = (json.loads(ed).get("home") or {}).get("score")
        except (ValueError, TypeError):
            score = None
        if isinstance(score, (int, float)):
            conn.execute("UPDATE events_raw SET home_score=? WHERE id=?", (score, id_))
            done += 1
    conn.commit()
    conn.close()
    print(f"home_score rempli pour {done} fiche(s) (sur {len(rows)} candidates).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
