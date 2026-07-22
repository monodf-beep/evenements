#!/usr/bin/env python3
"""Repère (et, sur --apply, retire) les événements publiés qui correspondent à une
règle d'exclusion ÉDITORIALE (config/excluded_event_keywords.txt) — ex. « jamais le
27e/23e BCA ». Sert à rattraper les événements publiés AVANT l'ajout d'une règle
(scripts/evaluator.py ne l'applique qu'aux futurs événements évalués).

Retrait = mise à la CORBEILLE WordPress (réversible, via cs/v1/trash) + statut='rejected'
en base + effacement de wp_post_id_as. RIEN n'est supprimé définitivement.

SÛR : dry-run par défaut. --apply pour agir. N'appelle AUCUNE API LLM (règles
déterministes uniquement — mêmes mots-clés que l'évaluateur).

Usage (VPS) :
    .venv/bin/python -m scripts.audit_excluded_events            # liste (dry-run)
    .venv/bin/python -m scripts.audit_excluded_events --apply    # corbeille + rejette
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.sources import is_excluded_event, load_excluded_events_filter
from scripts.scraper_events import init_db
from scripts.cleanup_as_trash import trash_one

log = get_logger("audit-excluded-events")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Repère/retire les événements publiés qui matchent une règle d'exclusion éditoriale.")
    parser.add_argument("--apply", action="store_true", help="Exécute (sinon dry-run).")
    parser.add_argument("--db-only", action="store_true",
                        help="Ne touche PAS WordPress ; marque juste les fiches rejetées en "
                             "base (à utiliser si tu as déjà corbeillé les posts à la main).")
    parser.add_argument("--cap", type=int, default=0, help="Limite le nombre traité (0 = tout).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    excluded_re = load_excluded_events_filter()
    all_rows = [dict(r) for r in conn.execute(
        "SELECT id, title, description, wp_post_id_as FROM events_raw").fetchall()]
    flagged = [r for r in all_rows
              if is_excluded_event(r.get("title", ""), r.get("description", ""), excluded_re)]
    published = sum(1 for r in all_rows if (r.get("wp_post_id_as") or 0) > 0)
    targets = [r for r in flagged if (r.get("wp_post_id_as") or 0) > 0]
    if args.cap:
        targets = targets[:args.cap]

    log.info("%d fiche(s) publiée(s) · %d exclue(s) par règle éditoriale publiée(s) à retirer%s",
             published, len(targets), " (cap %d)" % args.cap if args.cap else "")
    for r in targets:
        log.info("  WP#%s [%s] « %s »", r["wp_post_id_as"], r["id"], (r.get("title") or "")[:60])

    if not targets:
        log.info("Rien à retirer. 👍")
        conn.close()
        return 0
    if not args.apply:
        log.info("=== DRY-RUN : %d à mettre à la corbeille. Relance avec --apply. ===", len(targets))
        conn.close()
        return 0

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    if not args.db_only and not (wp_url and auth[0] and auth[1]):
        log.error("WP_AS_URL/USER/APP_PASSWORD manquants — impossible d'agir.")
        conn.close()
        return 2

    ok = fail = 0
    for r in targets:
        wp_id = int(r["wp_post_id_as"])
        if args.db_only or trash_one(wp_url, auth, wp_id, force=True):
            conn.execute("UPDATE events_raw SET statut='rejected', wp_post_id_as=NULL, "
                         "published_as_date=NULL, "
                         "llm_justification='Retiré : exclu par règle éditoriale "
                         "(config/excluded_event_keywords.txt).' WHERE id=?", (r["id"],))
            conn.commit()
            ok += 1
            log.info("  WP#%s → %s, fiche %s rejetée.", wp_id,
                     "base seule" if args.db_only else "corbeille", r["id"])
        else:
            fail += 1
            log.warning("  WP#%s : mise à la corbeille échouée (fiche %s laissée).", wp_id, r["id"])

    log.info("=== Terminé : %d %s, %d échec(s). ===", ok,
             "réconcilié(s) en base" if args.db_only else "à la corbeille", fail)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
