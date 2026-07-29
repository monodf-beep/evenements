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
from utils import completeness as comp
from scripts.publisher_as import publish_to_as

log = get_logger("publish_batch_as")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _select(conn, args, today: str):
    if args.ids:
        # Ciblage PRÉCIS (ex. republier après un correctif de contenu, cf.
        # scripts/audit_bad_sources.py) : ignore les filtres de sélection habituels,
        # republie ces ids tels quels (déjà publiés ou non).
        ph = ",".join("?" * len(args.ids))
        return conn.execute(
            f"SELECT * FROM events_raw WHERE id IN ({ph})", args.ids).fetchall()
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
    parser.add_argument("--ids", type=int, nargs="+", default=None,
                        help="Ne republie que ces ids précis (ignore statut/date/score, "
                             "republie même si déjà publiés). Ex. après un correctif de "
                             "contenu — cf. scripts/audit_bad_sources.py.")
    parser.add_argument("--min-score", type=int, default=None,
                        help="Score minimum (défaut : aucun seuil — toute la masse retenue).")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Pause (s) entre deux envois, pour ménager l'hébergement.")
    parser.add_argument("--update", action="store_true",
                        help="Réactualiser aussi les événements déjà sur l'agenda.")
    parser.add_argument("--include-past", action="store_true",
                        help="Inclure les événements déjà terminés (déconseillé).")
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="Publier MÊME les événements incomplets (contourne la porte "
                             "qualité). Par défaut, seuls les événements COMPLETS partent.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Lister la sélection sans rien publier.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in _select(conn, args, today)]

    # PORTE QUALITÉ : seuls les événements COMPLETS partent en brouillon (les
    # incomplets restent dans le dashboard, à charge de l'agent d'auto-complétion).
    # cf. utils/completeness.py + scripts/autocomplete.py. Ids EXPLICITES (--ids) : la
    # décision de republier est déjà prise (ex. correctif de contenu), on ne re-filtre pas.
    skipped = []
    if not args.allow_incomplete and not args.ids:
        kept = []
        for ev in rows:
            (kept if comp.is_complete(ev) else skipped).append(ev)
        rows = kept

    log.info("Sélection : %d complet(s) à publier, %d incomplet(s) écarté(s) "
             "(cap %d, min-score %s, %s)",
             len(rows), len(skipped), args.cap, args.min_score,
             "MAJ incluse" if args.update else "création seule")

    if args.dry_run:
        for r in rows:
            lieu = r.get("lieu") or "—"
            print(f"  [{r['id']}] {r['date_event_start']} · {(r['title'] or '')[:60]:60} "
                  f"· score={r['llm_score']} · lieu={lieu}")
        for ev in skipped:
            print(f"  ⤷ ÉCARTÉ [{ev['id']}] {(ev.get('title') or '')[:55]:55} "
                  f"· manque : {', '.join(comp.missing_labels(ev))}")
        print(f"\n{len(rows)} publié(s) / {len(skipped)} écarté(s) (dry-run — rien envoyé).")
        conn.close()
        return 0

    ok = fail = 0
    for i, r in enumerate(rows, 1):
        event = dict(r)
        wp_id, permalink, raw_url = publish_to_as(event)
        if wp_id:
            conn.execute(
                "UPDATE events_raw SET wp_post_id_as=?, wp_permalink_as=?, "
                "wp_raw_image_url_as=?, published_as_date=datetime('now') WHERE id=?",
                (wp_id, permalink, raw_url, event["id"]))
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
