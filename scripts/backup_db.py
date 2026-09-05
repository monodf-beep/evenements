#!/usr/bin/env python3
"""Sauvegarde de la base SQLite (data/events.db) — anti perte de données.

La base n'est PAS suivie par git (elle contient les données collectées). Sur un
VPS, une panne disque = tout perdu. Ce script fait une copie COHÉRENTE (API
sqlite backup, sûre même si l'app écrit en même temps), horodatée, et garde les
N dernières.

    python scripts/backup_db.py            # 1 sauvegarde + rotation (garde 14)
    BACKUP_KEEP=30 python scripts/backup_db.py

À planifier en cron, p. ex. quotidien à 3h :
    0 3 * * *  cd /root/evenements && .venv/bin/python scripts/backup_db.py >> logs/backup.log 2>&1
"""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", ROOT / "data" / "backups"))
KEEP = int(os.getenv("BACKUP_KEEP", "14"))


def main() -> int:
    if not DB_PATH.exists():
        print(f"⚠️  Base introuvable : {DB_PATH}")
        return 1
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"events-{stamp}.db"

    # Copie cohérente via l'API backup (verrou court, sûr en fonctionnement).
    src = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    size = dest.stat().st_size
    print(f"✅ Sauvegarde : {dest.name} ({size/1_048_576:.1f} Mo)")

    # Rotation : ne garde que les KEEP plus récentes.
    backups = sorted(BACKUP_DIR.glob("events-*.db"), reverse=True)
    for old in backups[KEEP:]:
        try:
            old.unlink()
            print(f"🗑  Supprimé (rotation) : {old.name}")
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
