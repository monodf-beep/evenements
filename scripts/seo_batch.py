#!/usr/bin/env python3
"""Génération SEO EN LOT (agent) — pour le HAUT DU PANIER seulement.

Lance utils.seo.optimize_seo() sur les événements retenus, datés, à venir et de
score élevé qui n'ont pas encore de SEO (seo_at IS NULL). Stocke seo_* + seo_at.
Ces champs sont ensuite poussés vers Yoast au (re)publish (publish_batch_as).

⚠️ Coût LLM : chaque événement = un appel. À réserver aux événements qui comptent
(le SEO de l'agenda se joue surtout sur les pages hubs, pas sur les fiches de masse).
Borné (--cap), seuil (--min-score, défaut 7), --dry-run.

Exemples :
  .venv/bin/python3 -m scripts.seo_batch --dry-run
  .venv/bin/python3 -m scripts.seo_batch --cap 30            # score >= 7 par défaut
  .venv/bin/python3 -m scripts.seo_batch --min-score 8 --cap 50
"""
from __future__ import annotations
import argparse
import json
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
from utils import seo as seo_mod

log = get_logger("seo_batch")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _select(conn, args, today: str):
    where = [
        "statut IN ('evaluated','published_cs','published_sub')",
        "duplicate_of IS NULL",
        "COALESCE(date_event_start,'') <> ''",              # daté
        "COALESCE(llm_score,0) >= ?",
    ]
    params: list = [args.min_score]
    if not args.redo:
        where.append("seo_at IS NULL")                      # pas déjà fait
    if not args.include_past:
        where.append("COALESCE(date_event_end, date_event_start) >= ?")
        params.append(today)
    sql = (f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
           f"ORDER BY COALESCE(llm_score,0) DESC, date_event_start ASC LIMIT ?")
    params.append(args.cap)
    return conn.execute(sql, params).fetchall()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Génération SEO en lot (agent).")
    parser.add_argument("--cap", type=int, default=30, help="Nombre max d'événements par run.")
    parser.add_argument("--min-score", type=int, default=7, help="Score minimum (défaut 7).")
    parser.add_argument("--delay", type=float, default=1.0, help="Pause (s) entre deux appels.")
    parser.add_argument("--redo", action="store_true", help="Régénérer même si déjà fait.")
    parser.add_argument("--include-past", action="store_true", help="Inclure les événements passés.")
    parser.add_argument("--dry-run", action="store_true", help="Lister la sélection sans appeler le LLM.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model = (os.getenv("ANTHROPIC_MODEL_SEO") or os.getenv("ANTHROPIC_MODEL_VISUALS")
             or "claude-haiku-4-5")
    today = date.today().isoformat()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = _select(conn, args, today)
    log.info("Sélection : %d événement(s) (cap %d, min-score %d, modèle %s)",
             len(rows), args.cap, args.min_score, model)

    if args.dry_run:
        for r in rows:
            print(f"  [{r['id']}] score={r['llm_score']} · {(r['title'] or '')[:70]}")
        print(f"\n{len(rows)} événement(s) SERAIENT optimisés (dry-run — aucun appel LLM).")
        conn.close()
        return 0

    if not api_key:
        log.error("ANTHROPIC_API_KEY absente — génération SEO impossible.")
        conn.close()
        return 1

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    ok = fail = 0
    for i, r in enumerate(rows, 1):
        try:
            result = seo_mod.optimize_seo(dict(r), client, model)
        except Exception as exc:                             # jamais bloquant
            log.warning("SEO échoué id=%s : %s", r["id"], exc)
            result = None
        if result:
            conn.execute(
                "UPDATE events_raw SET seo_title=?, seo_meta=?, seo_answer=?, seo_faq=?, "
                "seo_keyphrase=?, seo_slug=?, seo_tags=?, seo_model=?, seo_at=datetime('now') "
                "WHERE id=?",
                (result["seo_title"], result["seo_meta"], result["seo_answer"],
                 json.dumps(result["seo_faq"], ensure_ascii=False),
                 result["seo_keyphrase"], result["seo_slug"],
                 json.dumps(result["seo_tags"], ensure_ascii=False), model, r["id"]))
            conn.commit()
            ok += 1
        else:
            fail += 1
        if i % 10 == 0 or i == len(rows):
            log.info("Progression : %d/%d (%d ok, %d échec)", i, len(rows), ok, fail)
        if args.delay and i < len(rows):
            time.sleep(args.delay)

    conn.close()
    log.info("=== Lot SEO : %d optimisé(s), %d échec(s) ===", ok, fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
