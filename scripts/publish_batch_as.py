#!/usr/bin/env python3
"""Publication EN LOT vers Agenda Sabauda (mode « masse »).

Boucle publish_to_as() sur les événements RETENUS, DATÉS et À VENIR. Tout part en
BROUILLON (l'endpoint force draft — on ne publie jamais en ligne automatiquement) ;
tu fais ensuite une publication groupée dans WordPress quand tu veux.

Principes :
  - RETENU      : statut IN ('evaluated','published_cs','published_sub'), non-doublon.
  - DATÉ        : date_event_start non vide (sinon TEC daterait « aujourd'hui »).
  - À VENIR     : fin (ou début) >= aujourd'hui — on n'inonde pas l'agenda de passé.
  - IDEMPOTENT  : on saute ceux déjà sur l'agenda (wp_post_id_as), sauf --update.
  - BORNÉ       : --cap limite le nombre par run ; --delay espace les envois (OVH mutualisé).
  - On enregistre wp_post_id_as + published_as_date, SANS toucher au statut éditorial
    (la présence sur l'agenda est tracée par wp_post_id_as, pas par le statut).

Exemples :
  .venv/bin/python3 -m scripts.publish_batch_as --dry-run              # voir la sélection
  .venv/bin/python3 -m scripts.publish_batch_as --cap 30               # publier 30 brouillons
  .venv/bin/python3 -m scripts.publish_batch_as --min-score 5 --cap 100
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.publisher_as import publish_to_as

log = get_logger("publish_batch_as")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _select(conn, args, today: str):
    where = [
        "statut IN ('evaluated','published_cs','published_sub')",
        "duplicate_of IS NULL",
        "COALESCE(date_event_start,'') <> ''",                 # daté
    ]
    params: list = []
    if not args.include_past:
        where.append("COALESCE(date_event_end, date_event_start) >= ?")
        params.append(today)
    if not args.update:
        where.append("COALESCE(wp_post_id_as,0) = 0")          # pas déjà sur l'agenda
    if args.min_score is not None:
        where.append("COALESCE(llm_score,0) >= ?")
        params.append(args.min_score)
    sql = (f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
           f"ORDER BY date_event_start ASC LIMIT ?")
    params.append(args.cap)
    return conn.execute(sql, params).fetchall()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Publication en lot vers Agenda Sabauda.")
    parser.add_argument("--cap", type=int, default=50, help="Nombre max d'événements par run.")
    parser.add_argument("--min-score", type=int, default=None,
                        help="Score minimum (défaut : aucun seuil — toute la masse retenue).")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Pause (s) entre deux envois, pour ménager l'hébergement.")
    parser.add_argument("--update", action="store_true",
                        help="Réactualiser aussi les événements déjà sur l'agenda.")
    parser.add_argument("--include-past", action="store_true",
                        help="Inclure les événements déjà terminés (déconseillé).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Lister la sélection sans rien publier.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = _select(conn, args, today)

    log.info("Sélection : %d événement(s) (cap %d, min-score %s, %s)",
             len(rows), args.cap, args.min_score,
             "MAJ incluse" if args.update else "création seule")

    if args.dry_run:
        for r in rows:
            lieu = (r["lieu"] or "—") if "lieu" in r.keys() else "—"
            print(f"  [{r['id']}] {r['date_event_start']} · {(r['title'] or '')[:60]:60} "
                  f"· score={r['llm_score']} · lieu={lieu}")
        print(f"\n{len(rows)} événement(s) SERAIENT publiés (dry-run — rien n'a été envoyé).")
        conn.close()
        return 0

    ok = fail = 0
    for i, r in enumerate(rows, 1):
        event = dict(r)
        wp_id = publish_to_as(event)
        if wp_id:
            conn.execute(
                "UPDATE events_raw SET wp_post_id_as=?, published_as_date=datetime('now') "
                "WHERE id=?", (wp_id, event["id"]))
            conn.commit()
            ok += 1
        else:
            fail += 1
            log.warning("Échec pour id=%s : %s", event["id"], (event.get("title") or "")[:60])
        if i % 10 == 0 or i == len(rows):
            log.info("Progression : %d/%d (%d ok, %d échec)", i, len(rows), ok, fail)
        if args.delay and i < len(rows):
            time.sleep(args.delay)

    conn.close()
    log.info("=== Lot Agenda Sabauda : %d publié(s) en brouillon, %d échec(s) ===", ok, fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
