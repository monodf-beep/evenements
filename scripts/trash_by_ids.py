#!/usr/bin/env python3
"""Met à la CORBEILLE WordPress (RÉVERSIBLE, cs/v1/trash) des événements ciblés PAR ID
LOCAL — sert au panier « CORBEILLE » du chantier contenu cassé
(scripts.triage_chantier_casse) : des fiches déjà jugées statut='rejected'/'merged' en
local, mais restées PUBLIÉES sur WordPress faute d'avoir été nettoyées à l'époque.

force=True (nécessaire ici : ces posts sont bien publiés sur WP, cs/v1/trash refuse sinon
un post publié par mesure de sécurité). Après corbeille, efface wp_post_id_as/
published_as_date en base (l'événement n'est plus « sur l'agenda »), comme
scripts.cleanup_as_trash. DRY-RUN par défaut.

Usage :
    .venv/bin/python -m scripts.trash_by_ids 1120 2025 975 ...           # liste (dry-run)
    .venv/bin/python -m scripts.trash_by_ids 1120 2025 975 ... --apply
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

log = get_logger("trash-by-ids")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(description="Corbeille WordPress (réversible) par id local.")
    p.add_argument("ids", nargs="+", type=int, help="Ids LOCAUX (events_raw.id) à corbeiller.")
    p.add_argument("--apply", action="store_true", help="Exécute (sinon dry-run).")
    p.add_argument("--delay", type=float, default=0.5, help="Pause (s) entre deux appels.")
    args = p.parse_args(argv)

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ph = ",".join("?" * len(args.ids))
    rows = [dict(r) for r in conn.execute(
        f"SELECT id, title, statut, wp_post_id_as FROM events_raw WHERE id IN ({ph})",
        args.ids).fetchall()]
    missing = set(args.ids) - {r["id"] for r in rows}
    if missing:
        log.warning("id(s) introuvable(s), ignoré(s) : %s", sorted(missing))
    targets = [r for r in rows if (r.get("wp_post_id_as") or 0) > 0]
    skipped = [r for r in rows if not (r.get("wp_post_id_as") or 0) > 0]
    for r in skipped:
        log.info("id=%s « %s » — pas de wp_post_id_as, rien à corbeiller (déjà hors ligne).",
                 r["id"], (r["title"] or "")[:50])

    mode = "EXÉCUTION" if args.apply else "DRY-RUN (rien ne bouge)"
    log.info("%s — %d événement(s) à corbeiller :", mode, len(targets))
    for r in targets:
        log.info("  id=%s WP#%s statut=%s « %s »", r["id"], r["wp_post_id_as"], r["statut"],
                 (r["title"] or "")[:55])

    if not args.apply:
        log.info("DRY-RUN : relance avec --apply pour agir.")
        conn.close()
        return 0

    if not all([wp_url, auth[0], auth[1]]):
        log.error("WP_AS_URL/USER/APP_PASSWORD manquants — impossible d'agir.")
        conn.close()
        return 1

    ok = fail = 0
    for i, r in enumerate(targets, 1):
        if trash_one(wp_url, auth, r["wp_post_id_as"], force=True):
            conn.execute("UPDATE events_raw SET wp_post_id_as=NULL, published_as_date=NULL "
                         "WHERE id=?", (r["id"],))
            conn.commit()
            ok += 1
            log.info("  ✓ id=%s WP#%s corbeillé.", r["id"], r["wp_post_id_as"])
        else:
            fail += 1
        if args.delay and i < len(targets):
            time.sleep(args.delay)

    conn.close()
    log.info("=== %d corbeillé(s), %d échec(s) ===", ok, fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
