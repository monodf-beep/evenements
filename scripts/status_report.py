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

    # `traduction_tentatives` est ajoutée par `translate_events._ensure_cols`, donc elle
    # existe en production — mais un rapport d'état ne doit JAMAIS tomber en panne parce
    # qu'une colonne manque sur une base neuve : le rapport est ce qu'on lit quand ça va
    # mal. Sans la colonne, le compteur ne compte simplement pas les fiches garées, et le
    # libellé le dira.
    _a_garage = any(r[1] == "traduction_tentatives"
                    for r in conn.execute("PRAGMA table_info(events_raw)"))
    _garees_sql = ("OR COALESCE(traduction_tentatives,0) >= 3 " if _a_garage else "")

    return {
        "à enrichir (score suffisant, jamais rédigé)": one(
            "SELECT COUNT(*) FROM events_raw WHERE statut IN ('evaluated','published_sub') "
            "AND (enrich_status IS NULL OR enrich_status='') AND COALESCE(translation_of,0)=0 "
            "AND duplicate_of IS NULL AND llm_score >= 1"),
        # LE PÉRIMÈTRE DU CRON, PAS UN AUTRE — corrigé le 2026-09-15. Ce compteur annonçait
        # « score ≥ 6 » et n'avait AUCUN filtre de date, alors que crontab.txt lance la
        # traduction avec `--min-score 1` et que la file, elle, écarte le passé depuis le
        # 14/09. Il comptait donc autre chose que ce qui se fait : des fiches terminées
        # depuis des mois, et pas les fiches à 1-5 points que le cron traduit pourtant.
        # Deux compteurs qui portent le même nom et comptent deux choses se contrediront
        # un jour, et c'est le plus gros qu'on croira (règle 6).
        #
        # Ce nombre ne dit PAS pourquoi elles ne sont pas traduites : pour ça,
        # `.venv/bin/python -m scripts.audit_traduction_manquante`, qui range chaque fiche
        # dans sa famille et donne la commande de reprise de chacune.
        "à traduire (en ligne, à venir ou en cours, score ≥ 1, pas de jumelle)": one(
            "SELECT COUNT(*) FROM events_raw WHERE COALESCE(wp_post_id_as,0)>0 "
            "AND duplicate_of IS NULL AND COALESCE(translation_of,0)=0 "
            "AND COALESCE(url_source,'') NOT LIKE 'translated:%' "
            "AND COALESCE(translated_at,'')='' AND COALESCE(user_score,llm_score,0) >= 1 "
            "AND (COALESCE(date_event_end, date_event_start, '') = '' "
            "     OR COALESCE(date_event_end, date_event_start) >= date('now')) "
            "AND id NOT IN (SELECT translation_of FROM events_raw WHERE COALESCE(translation_of,0)!=0)"),
        # ET CELUI-CI EST LE PLUS IMPORTANT DES DEUX : une fiche publiée en français, encore
        # devant nous, SANS jumelle italienne et SANS être dans la file ci-dessus, est une
        # fiche que plus rien ne reprendra. C'est le trou que Franck a vu le 15/09 (« encore
        # des événements sans traduction ! ») : 117 fiches françaises sans jumelle, dont 63
        # à venir, invisibles dans tous les compteurs parce qu'aucun ne les cherchait.
        "publiées sans jumelle ET hors de la file (à expliquer, cf. audit)": one(
            "SELECT COUNT(*) FROM events_raw WHERE COALESCE(wp_post_id_as,0)>0 "
            "AND duplicate_of IS NULL AND COALESCE(translation_of,0)=0 "
            "AND COALESCE(url_source,'') NOT LIKE 'translated:%' "
            "AND (COALESCE(date_event_end, date_event_start, '') = '' "
            "     OR COALESCE(date_event_end, date_event_start) >= date('now')) "
            "AND id NOT IN (SELECT translation_of FROM events_raw WHERE COALESCE(translation_of,0)!=0) "
            "AND (COALESCE(translated_at,'')<>'' OR COALESCE(user_score,llm_score,0) < 1 "
            + _garees_sql + ")"),
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
