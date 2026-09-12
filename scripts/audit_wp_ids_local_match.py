#!/usr/bin/env python3
"""Diagnostic EN LECTURE SEULE (rien n'est écrit) pour le chantier « contenu cassé » listé
dans docs/CHANTIER_CONTENU_CASSE_2026-07-29.md (34 fiches IT au contenu resté en français +
~51 fiches au contenu vide/résidu RSS, trouvées via Novamira/PHP direct sur WordPress).

Ce chantier a été préparé par une AUTRE session (connectée à Novamira, sans accès à cette
base locale events_raw) — avant de réécrire quoi que ce soit, on croise chaque id de post
WordPress (wp_post_id_as) avec cette base : si une ligne existe ici, elle est RÉPARABLE via
le pipeline habituel (scripts.enrich / scripts.translate_events --retranslate), qui applique
déjà voix éditoriale + panel de personas + révision automatique — plus fiable qu'une
réécriture PHP à la main. Si aucune ligne ne correspond, le post est hors de portée de ce
pipeline (orphelin, ou jamais passé par lui) — à traiter côté Novamira.

Sert aussi à repérer les DOUBLONS potentiels entre les deux sessions (ex. un événement déjà
correctement enrichi ici mais listé comme cassé côté WordPress — signe d'un écart de
publication, pas d'un contenu réellement cassé).

Usage (VPS) :
    .venv/bin/python -m scripts.audit_wp_ids_local_match
"""
from __future__ import annotations
import json
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.scraper_events import init_db
from scripts.translate_events import _ensure_cols

log = get_logger("audit-wp-ids")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# BUG 1 — 34 fiches taguées IT (Polylang) mais contenu resté en français (source : doc).
BUG1_WP_IDS = [
    663, 1158, 694, 715, 779, 1202, 1931, 1938, 1888, 1890, 1892, 1894, 1899, 1905, 1914,
    1922, 902, 1207, 729, 739, 792, 725, 280, 578, 593, 606, 608, 718, 782, 786, 788, 2205,
    2277, 3964,
]

# BUG 2 — ~51 fiches contenu vide ou résidu RSS brut (id 702 déjà corrigé, exclu).
BUG2_WP_IDS = [
    835, 673, 681, 877, 686, 2036, 330, 1928, 1984, 1910, 1917, 898, 917, 921, 1209, 1212,
    736, 752, 754, 698, 712, 585, 590, 595, 601, 619, 653, 795, 809, 1147, 1856, 2188, 2192,
    2201, 2209, 2213, 2267, 2273, 2275, 2311, 2331, 2350, 2358, 2362, 3769, 3787, 3815, 3819,
    3823, 3969, 4117,
]

# Prioritaires signalés dans le doc — sujet sensible (attentat de Nice) et bug visible en
# ligne (template de prompt resté en clair).
PRIORITY = {2188: "sensible — manchette presse sur l'attentat de Nice, à traiter avec précaution éditoriale",
            3769: "URGENT — template de prompt en clair sur la page publique"}


def _row_for(conn, wp_id: int) -> dict | None:
    r = conn.execute("SELECT * FROM events_raw WHERE wp_post_id_as=?", (wp_id,)).fetchone()
    return dict(r) if r else None


def _summary(conn, wp_id: int, label: str) -> None:
    row = _row_for(conn, wp_id)
    tag = f" [{PRIORITY[wp_id]}]" if wp_id in PRIORITY else ""
    if not row:
        log.warning("WP#%s (%s) : AUCUNE ligne events_raw — orphelin, hors de portée du "
                    "pipeline local, à traiter côté Novamira.%s", wp_id, label, tag)
        return
    desc_len = len((row.get("description") or ""))
    enrich_len = len((row.get("enrich_data") or ""))
    sources = []
    if row.get("enrich_data"):
        try:
            sources = json.loads(row["enrich_data"]).get("sources") or []
        except (ValueError, TypeError):
            pass
    log.info(
        "WP#%s (%s) → id=%s « %s » | statut=%s enrich_status=%s | translation_of=%s "
        "translated_lang=%s | desc_len=%d enrich_data_len=%d home_score=%s | sources=%s%s",
        wp_id, label, row["id"], (row.get("title") or "")[:55], row.get("statut"),
        row.get("enrich_status"), row.get("translation_of"), row.get("translated_lang"),
        desc_len, enrich_len, row.get("home_score"), sources or "—", tag)


def main() -> int:
    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _ensure_cols(conn)  # translation_of/translated_lang/translated_at (scripts.translate_events)

    log.info("=== BUG 1 (%d ids) — IT tagué, contenu resté FR ===", len(BUG1_WP_IDS))
    for wp_id in BUG1_WP_IDS:
        _summary(conn, wp_id, "bug1")

    log.info("=== BUG 2 (%d ids) — contenu vide / résidu RSS ===", len(BUG2_WP_IDS))
    for wp_id in BUG2_WP_IDS:
        _summary(conn, wp_id, "bug2")

    # Cluster « attentat de Nice » : cherche TOUTE fiche (pas seulement les ids listés) dont
    # le titre évoque le sujet, pour repérer un éventuel doublon avec 2188/3964 (déjà connus
    # dans ce run comme référençant nice.fr correctement, cf. session du 2026-07-29).
    log.info("=== Cluster « attentat de Nice » (recherche large, pas juste les ids ci-dessus) ===")
    rows = [dict(r) for r in conn.execute(
        "SELECT id, wp_post_id_as, title, translation_of, translated_lang, statut, "
        "enrich_status, home_score FROM events_raw "
        "WHERE title LIKE '%attentat%' OR title LIKE '%attentato%' "
        "OR title LIKE '%14 juillet%' OR title LIKE '%14 luglio%'").fetchall()]
    for r in rows:
        log.info("  id=%s WP#%s « %s » | statut=%s enrich_status=%s translation_of=%s "
                 "lang=%s home_score=%s", r["id"], r.get("wp_post_id_as"),
                 (r.get("title") or "")[:60], r.get("statut"), r.get("enrich_status"),
                 r.get("translation_of"), r.get("translated_lang"), r.get("home_score"))
    if not rows:
        log.info("  (aucune fiche locale ne matche — le cluster n'existe peut-être que côté WP)")

    n1 = sum(1 for wp_id in BUG1_WP_IDS if _row_for(conn, wp_id))
    n2 = sum(1 for wp_id in BUG2_WP_IDS if _row_for(conn, wp_id))
    conn.close()
    log.info("=== Résumé : Bug1 %d/%d réparables via le pipeline local · "
             "Bug2 %d/%d réparables via le pipeline local ===",
             n1, len(BUG1_WP_IDS), n2, len(BUG2_WP_IDS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
