#!/usr/bin/env python3
"""Écarte les événements PASSÉS (date révolue) — nettoyage du stock retenu.

Un événement retenu quand il était à venir devient obsolète une fois sa date
passée. On le passe en 'rejected' (réversible : il suffit de le re-classer) pour
qu'il quitte « À compléter » / la file. Ne touche QUE les événements DATÉS dont la
fin est révolue — les non-datés (dont on ne connaît pas la date, ex. « Eccoci »)
ne peuvent pas être détectés ainsi : à écarter à la main (bouton « Écarter »).

⚠️ Côté WordPress : un brouillon déjà poussé et devenu passé se nettoie avec
scripts.cleanup_as_dupes --past (corbeille WP).

Exemples :
  .venv/bin/python3 -m scripts.purge_past                 # dry-run (liste)
  .venv/bin/python3 -m scripts.purge_past --execute
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("purge_past")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _select(conn, today: str):
    # Retenu, non-doublon, DATÉ, et fin (ou début à défaut) révolue.
    return conn.execute(
        "SELECT id, title, date_event_start, date_event_end, wp_post_id_as "
        "FROM events_raw "
        "WHERE statut IN ('evaluated','published_cs','published_sub') "
        "  AND duplicate_of IS NULL "
        "  AND COALESCE(NULLIF(date_event_end,''), NULLIF(date_event_start,'')) <> '' "
        "  AND COALESCE(NULLIF(date_event_end,''), date_event_start) < ? "
        "ORDER BY COALESCE(NULLIF(date_event_end,''), date_event_start)", (today,)
    ).fetchall()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Écarte les événements passés (date révolue).")
    p.add_argument("--execute", action="store_true", help="Agir (sinon DRY-RUN).")
    args = p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = _select(conn, today)

    mode = "EXÉCUTION" if args.execute else "DRY-RUN (rien ne bouge)"
    print(f"\nÉvénements passés à écarter — {mode} · {len(rows)}\n")
    on_wp = 0
    for r in rows:
        end = r["date_event_end"] or r["date_event_start"]
        flag = "  ⚠ sur l'agenda WP#%s" % r["wp_post_id_as"] if r["wp_post_id_as"] else ""
        if r["wp_post_id_as"]:
            on_wp += 1
        print(f"  [{r['id']}] fin {end} · {(r['title'] or '')[:60]}{flag}")
    if not rows:
        print("Aucun événement passé. 🎉")
        return 0
    if on_wp:
        print(f"\nℹ {on_wp} sont déjà sur l'agenda (brouillon WP) → pense à "
              "`scripts.cleanup_as_dupes --past --execute` pour les mettre à la corbeille.")
    if not args.execute:
        print(f"\nDRY-RUN : {len(rows)} seraient écartés. Relance avec --execute.")
        conn.close()
        return 0

    conn.executemany(
        "UPDATE events_raw SET statut='rejected', "
        "llm_justification='Événement passé (date révolue) — écarté automatiquement.' "
        "WHERE id=?", [(r["id"],) for r in rows])
    conn.commit()
    conn.close()
    print(f"\n=== {len(rows)} événement(s) passé(s) écarté(s) (réversible : re-classer). ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
