#!/usr/bin/env python3
"""Triage EN LECTURE SEULE des 85 fiches du chantier « contenu cassé »
(docs/CHANTIER_CONTENU_CASSE_2026-07-29.md), à partir du résultat de
scripts.audit_wp_ids_local_match : classe chaque id dans un des 3 paniers d'action, pour
éviter de réécrire à coup de LLM ce qui devrait juste être dépublié ou simplement republié.

- CORBEILLE  : statut local déjà 'rejected'/'merged' (la fiche a été jugée à ne pas publier
  APRÈS avoir été mise en ligne — le nettoyage WP n'a jamais suivi), ou événement déjà PASSÉ.
  Zéro coût, zéro écriture de contenu : juste dépublier le post WP existant.
- REPUBLIER SEULEMENT : déjà enrichi localement (enrich_status='enriched', contenu
  substantiel) et statut PAS rejeté — le bon contenu existe déjà en base, WordPress affiche
  juste une version périmée (jamais repoussée). Zéro coût LLM : publish_batch_as --ids suffit
  (build_post relit enrich_data à chaque republication).
- À RÉ-ENRICHIR : statut retenu (evaluated/published_sub) mais jamais vraiment enrichi
  (enrich_status vide ou contenu trop mince) — seul cas qui justifie un vrai passage par
  scripts.enrich (voix + panel de personas + révision automatiques).

Rien n'est écrit ici. Usage (VPS) :
    .venv/bin/python -m scripts.triage_chantier_casse
"""
from __future__ import annotations
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.scraper_events import init_db
from scripts.translate_events import _ensure_cols
from scripts.audit_wp_ids_local_match import BUG1_WP_IDS, BUG2_WP_IDS, PRIORITY

log = get_logger("triage-casse")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

MIN_SUBSTANTIAL = 800  # enrich_data_len en dessous duquel on ne considère PAS "déjà bon"


def _classify(row: dict, today: str) -> tuple[str, str]:
    """Renvoie (panier, raison)."""
    statut = row.get("statut")
    end = row.get("date_event_end") or row.get("date_event_start") or ""
    if statut in ("rejected", "merged"):
        return "CORBEILLE", f"statut local = {statut}"
    if end and end < today:
        return "CORBEILLE", f"événement déjà passé ({end})"
    enrich_len = len(row.get("enrich_data") or "")
    if row.get("enrich_status") == "enriched" and enrich_len >= MIN_SUBSTANTIAL:
        return "REPUBLIER", f"déjà enrichi ({enrich_len} car.) — juste jamais republié"
    return "RÉ-ENRICHIR", "pas encore de contenu substantiel en base"


def main() -> int:
    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _ensure_cols(conn)
    today = date.today().isoformat()

    buckets: dict[str, list] = {"CORBEILLE": [], "REPUBLIER": [], "RÉ-ENRICHIR": []}
    all_ids = [(wp_id, "bug1") for wp_id in BUG1_WP_IDS] + [(wp_id, "bug2") for wp_id in BUG2_WP_IDS]
    for wp_id, label in all_ids:
        row = conn.execute("SELECT * FROM events_raw WHERE wp_post_id_as=?", (wp_id,)).fetchone()
        if not row:
            buckets.setdefault("ORPHELIN", []).append((wp_id, label, "aucune ligne locale", ""))
            continue
        row = dict(row)
        panier, raison = _classify(row, today)
        tag = f" [{PRIORITY[wp_id]}]" if wp_id in PRIORITY else ""
        buckets[panier].append((wp_id, row["id"], row.get("title", "")[:55], raison + tag))
    conn.close()

    for panier in ("CORBEILLE", "REPUBLIER", "RÉ-ENRICHIR", "ORPHELIN"):
        items = buckets.get(panier, [])
        if not items:
            continue
        log.info("=== %s (%d) ===", panier, len(items))
        for wp_id, local_id, title, raison in items:
            log.info("  WP#%s (id=%s) « %s » — %s", wp_id, local_id, title, raison)

    log.info("=== Résumé : %d corbeille · %d republier seulement (zéro coût LLM) · "
             "%d à ré-enrichir · %d orphelin(s) ===",
             len(buckets["CORBEILLE"]), len(buckets["REPUBLIER"]),
             len(buckets["RÉ-ENRICHIR"]), len(buckets.get("ORPHELIN", [])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
