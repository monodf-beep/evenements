#!/usr/bin/env python3
"""Met à la CORBEILLE WordPress (RÉVERSIBLE, cs/v1/trash) des événements ciblés PAR ID
WORDPRESS directement — sert quand on n'a QUE des WP#id (ex. issus d'un audit fait en lisant
le site en direct), sans correspondance locale confirmée pour tous. Contrairement à
scripts.trash_by_ids (qui prend des ids LOCAUX), celui-ci ne requiert aucune ligne locale :
il corbeille sur WordPress, puis met à jour en base UNIQUEMENT les lignes locales qui ont
justement ce wp_post_id_as (best-effort, silencieux si aucune ligne ne correspond).

force=True (nécessaire : ces posts sont publiés, cs/v1/trash refuse sinon un post publié par
mesure de sécurité). DRY-RUN par défaut.

Usage :
    .venv/bin/python -m scripts.trash_wp_ids 22 38 1892 ...           # liste (dry-run)
    .venv/bin/python -m scripts.trash_wp_ids 22 38 1892 ... --apply
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.cleanup_as_trash import trash_one

log = get_logger("trash-wp-ids")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(description="Corbeille WordPress (réversible) par id WordPress direct.")
    p.add_argument("wp_ids", nargs="+", type=int, help="Ids WORDPRESS (post ID TEC) à corbeiller.")
    p.add_argument("--apply", action="store_true", help="Exécute (sinon dry-run).")
    p.add_argument("--delay", type=float, default=0.5, help="Pause (s) entre deux appels.")
    args = p.parse_args(argv)

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ph = ",".join("?" * len(args.wp_ids))
    local_by_wp = {r["wp_post_id_as"]: dict(r) for r in conn.execute(
        f"SELECT id, title, statut, wp_post_id_as FROM events_raw WHERE wp_post_id_as IN ({ph})",
        args.wp_ids).fetchall()}

    mode = "EXÉCUTION" if args.apply else "DRY-RUN (rien ne bouge)"
    log.info("%s — %d id(s) WordPress à corbeiller :", mode, len(args.wp_ids))
    for wp_id in args.wp_ids:
        local = local_by_wp.get(wp_id)
        if local:
            log.info("  WP#%s ↔ id local=%s statut=%s « %s »", wp_id, local["id"], local["statut"],
                     (local["title"] or "")[:50])
        else:
            log.info("  WP#%s — aucune ligne locale correspondante (rien à réconcilier en base)", wp_id)

    if not args.apply:
        log.info("DRY-RUN : relance avec --apply pour agir.")
        conn.close()
        return 0

    if not all([wp_url, auth[0], auth[1]]):
        log.error("WP_AS_URL/USER/APP_PASSWORD manquants — impossible d'agir.")
        conn.close()
        return 1

    ok = fail = 0
    for i, wp_id in enumerate(args.wp_ids, 1):
        if trash_one(wp_url, auth, wp_id, force=True):
            local = local_by_wp.get(wp_id)
            if local:
                conn.execute(
                    "UPDATE events_raw SET wp_post_id_as=NULL, published_as_date=NULL, "
                    "statut='rejected' WHERE id=?", (local["id"],))
                conn.commit()
                log.info("  ✓ WP#%s corbeillé (id local=%s réconcilié, statut='rejected').",
                         wp_id, local["id"])
            else:
                log.info("  ✓ WP#%s corbeillé (aucune ligne locale à réconcilier).", wp_id)
            ok += 1
        else:
            fail += 1
        if args.delay and i < len(args.wp_ids):
            time.sleep(args.delay)

    conn.close()
    log.info("=== %d corbeillé(s), %d échec(s) ===", ok, fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
