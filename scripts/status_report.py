#!/usr/bin/env python3
"""Rapport d'état consolidé du pipeline — POUR FRANCK (lecture directe) ET POUR UNE IA
(colle la sortie de ce script dans une conversation Claude pour qu'elle reparte de l'état
réel au lieu de devoir reconstituer le contexte à partir des logs).

Deux sources :
  1. `pipeline_runs` (utils.pipeline_status) — dernier run de chaque automatisation.
  2. La file elle-même — combien reste-t-il à faire, par étape (texte non enrichi,
     événements non traduits, sans SEO, points « à vérifier » en attente).

Zéro écriture, zéro coût API.

Usage (VPS) :
    .venv/bin/python -m scripts.status_report
"""
from __future__ import annotations
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import pipeline_status

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

_KNOWN_SCRIPTS = ["daily_batch", "translate_events", "seo_batch", "weekly_audits",
                  "homepage_health"]


def _backlog_counts(conn: sqlite3.Connection) -> dict[str, int]:
    def one(sql: str, *params) -> int:
        return conn.execute(sql, params).fetchone()[0]

    return {
        "à enrichir (score suffisant, jamais rédigé)": one(
            "SELECT COUNT(*) FROM events_raw WHERE statut IN ('evaluated','published_sub') "
            "AND (enrich_status IS NULL OR enrich_status='') AND COALESCE(translation_of,0)=0 "
            "AND duplicate_of IS NULL AND llm_score >= 1"),
        "à traduire (en ligne, score ≥ 6, pas de jumelle)": one(
            "SELECT COUNT(*) FROM events_raw WHERE COALESCE(wp_post_id_as,0)>0 "
            "AND duplicate_of IS NULL AND COALESCE(translation_of,0)=0 "
            "AND COALESCE(translated_at,'')='' AND COALESCE(user_score,llm_score,0) >= 6 "
            "AND id NOT IN (SELECT translation_of FROM events_raw WHERE COALESCE(translation_of,0)!=0)"),
        "sans SEO (retenus, score ≥ 7)": one(
            "SELECT COUNT(*) FROM events_raw WHERE statut IN ('evaluated','published_cs','published_sub') "
            "AND duplicate_of IS NULL AND COALESCE(date_event_start,'')<>'' "
            "AND COALESCE(llm_score,0) >= 7 AND seo_at IS NULL"),
        "points « à vérifier » en attente (table checks)": one(
            "SELECT COUNT(*) FROM checks WHERE status='pending'"
            if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='checks'")
               .fetchone() else "SELECT 0"),
    }


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)

    print("=" * 70)
    print("RAPPORT D'ÉTAT — pipeline Agenda Sabauda")
    print("=" * 70)

    print("\n--- Dernier run de chaque automatisation ---")
    runs = pipeline_status.last_runs(limit_per_script=1)
    for script in _KNOWN_SCRIPTS:
        entries = runs.get(script)
        if not entries:
            print(f"[{script}] jamais exécuté (ou pas encore câblé sur pipeline_status)")
            continue
        r = entries[0]
        print(f"[{script}] {r['ran_at']} — ok={r['ok_count']} warn={r['warn_count']} "
              f"error={r['error_count']}")
        if r["summary"]:
            first_line = r["summary"].splitlines()[0]
            print(f"    {first_line}")

    print("\n--- Reste à faire (file actuelle) ---")
    for label, n in _backlog_counts(conn).items():
        print(f"  {n:5d}  {label}")

    conn.close()

    from utils import site_issues
    open_issues = site_issues.list_issues("open")
    print(f"\n--- Problèmes de site ouverts ({len(open_issues)}) — docs/site_issues.json ---")
    for i in open_issues:
        print(f"[{i['id']}] ({i['category']}) {i['title']} — ouvert {i['opened_at']}")

    print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
