#!/usr/bin/env python3
"""Audit RÉTROACTIF des sources citées dans les articles déjà enrichis : repère les fiches
dont le champ « sources » contient une URL au domaine NON VÉRIFIÉ officiel (agrégateur,
guide touristique tiers…) — cas vécu : guidatorino.com cité comme source d'un événement
dont il n'est ni l'organisateur ni une institution, en violation de la charte §8 (seules les
sources institutionnelles/officielles sont créditées/liées).

Zéro coût API, zéro écriture : ce script ne fait QUE lire et rapporter, avec la même règle
que le garde-fou déjà en place (scripts.enrich.filter_official_sources — appliqué aux
NOUVEAUX enrichissements, et par scripts.publisher.build_post à CHAQUE republication depuis
enrich_data). Rien à corriger en base : la prochaine republication de chaque fiche listée
régénère un contenu propre automatiquement. Ce script sert juste à savoir QUOI republier.

Usage (VPS) :
    .venv/bin/python -m scripts.audit_bad_sources                 # toutes les fiches enrichies
    .venv/bin/python -m scripts.audit_bad_sources --published-only # seulement sur l'agenda (wp_post_id_as)

Après la liste, republie PRÉCISÉMENT les fiches concernées (--ids, aucun coût LLM, juste une
réécriture depuis enrich_data — la commande exacte est imprimée en fin de run s'il y en a).
"""
from __future__ import annotations
import argparse
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
from scripts.enrich import filter_official_sources

log = get_logger("audit-bad-sources")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Liste les fiches dont une source citée n'est pas d'un domaine officiel vérifié.")
    parser.add_argument("--published-only", action="store_true",
                        help="Limite aux fiches déjà publiées sur Agenda Sabauda (wp_post_id_as).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    where = "enrich_data IS NOT NULL AND enrich_data != ''"
    if args.published_only:
        where += " AND COALESCE(wp_post_id_as,0) > 0"
    rows = [dict(r) for r in conn.execute(
        f"SELECT id, title, wp_post_id_as, url_officiel, url_source, enrich_data "
        f"FROM events_raw WHERE {where}").fetchall()]
    conn.close()

    flagged = []
    for r in rows:
        try:
            data = json.loads(r["enrich_data"])
        except (ValueError, TypeError):
            continue
        sources = data.get("sources") or []
        if not sources:
            continue
        official_pages = [{"url": u} for u in ((data.get("source") or {}).get("pages") or [])]
        kept, dropped = filter_official_sources(
            sources, official_pages, r.get("url_officiel"), r.get("url_source"))
        if dropped:
            flagged.append({**r, "dropped": dropped, "kept": kept})

    if not flagged:
        log.info("Aucune fiche avec une source non institutionnelle — rien à republier (%d fiche(s) scannée(s)).",
                 len(rows))
        return 0

    log.warning("%d fiche(s) sur %d avec une source NON institutionnelle citée :",
               len(flagged), len(rows))
    for f in flagged:
        pub = f"WP#{f['wp_post_id_as']}" if f.get("wp_post_id_as") else "non publiée"
        log.warning("  id=%s (%s) « %s » — écarté(s) : %s", f["id"], pub,
                   (f["title"] or "")[:60], ", ".join(f["dropped"]))
    ids = " ".join(str(f["id"]) for f in flagged if f.get("wp_post_id_as"))
    log.info("Rien n'a été modifié. Pour pousser la correction aux fiches déjà publiées "
             "(relit enrich_data, zéro coût LLM) :")
    if ids:
        log.info("  .venv/bin/python -m scripts.publish_batch_as --ids %s", ids)
    else:
        log.info("  (aucune des fiches listées n'est encore publiée — rien à republier)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
