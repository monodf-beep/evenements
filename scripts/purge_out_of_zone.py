#!/usr/bin/env python3
"""Purge DÉTERMINISTE du bruit (gratuit, sans LLM).

Rejette (ou supprime avec --hard) les événements 'pending' qui sont :
  • HORS ZONE — citent un lieu clairement hors des 4 territoires
    (config/out_of_zone.txt) sans aucun lieu couvert, ou source large sans lieu
    couvert ;
  • PASSÉS — déjà terminés (date de fin/début antérieure à aujourd'hui) : on
    n'informe que du à-venir / en cours.

    python scripts/purge_out_of_zone.py            # aperçu (rien n'est modifié)
    python scripts/purge_out_of_zone.py --apply    # rejette (statut='rejected')
    python scripts/purge_out_of_zone.py --apply --hard   # supprime les lignes
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.sources import (is_broad_source, is_out_of_scope, load_broad_sources,
                           load_out_of_zone, load_perimeter_filter, mentions_perimeter)
from scripts.scraper_events import _domain

log = get_logger("purge_zone")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Purge des événements hors zone.")
    parser.add_argument("--apply", action="store_true",
                        help="Applique (par défaut : aperçu seul, rien n'est modifié).")
    parser.add_argument("--hard", action="store_true",
                        help="Supprime les lignes au lieu de les passer en 'rejected'.")
    args = parser.parse_args(argv)

    perimeter_re = load_perimeter_filter()
    broad = load_broad_sources()
    out_re = load_out_of_zone()
    if perimeter_re is None and out_re is None:
        log.error("Aucun filtre configuré (perimeter_keywords.txt / out_of_zone.txt).")
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, title, description, url_source, territoire, source_name, "
        "date_event_start, date_event_end "
        "FROM events_raw WHERE statut = 'pending' AND duplicate_of IS NULL").fetchall()

    today = date.today().isoformat()
    hits = []
    for r in rows:
        material = f"{r['title']}\n{r['description'] or ''}"
        end = (r["date_event_end"] or r["date_event_start"] or "").strip()[:10]
        past_hit = bool(end) and end < today
        broad_hit = (broad and is_broad_source(_domain(r["url_source"]), broad)
                     and perimeter_re is not None
                     and not mentions_perimeter(material, perimeter_re))
        zone_hit = is_out_of_scope(material, out_re, perimeter_re)
        if past_hit:
            hits.append((r, "passé"))
        elif broad_hit or zone_hit:
            hits.append((r, "hors zone" if zone_hit else "source large"))

    from collections import Counter
    par_motif = Counter(m for _, m in hits)
    detail = ", ".join(f"{n} {m}" for m, n in par_motif.items()) or "aucun"
    print(f"\n{len(hits)} à purger sur {len(rows)} en attente ({detail}) :\n")
    for r, motif in hits[:60]:
        print(f"  [{r['id']:>5}] {r['territoire'] or '—':<14} {motif:<12} "
              f"{(r['source_name'] or '')[:22]:<22} {r['title'][:60]}")
    if len(hits) > 60:
        print(f"  … et {len(hits) - 60} autres.")

    if not args.apply:
        print("\nAperçu seul. Relance avec --apply pour rejeter "
              "(ou --apply --hard pour supprimer).")
        conn.close()
        return 0

    ids = [r["id"] for r, _ in hits]
    if args.hard:
        conn.executemany("DELETE FROM events_raw WHERE id=?", [(i,) for i in ids])
        verbe = "supprimé(s)"
    else:
        motifs = {
            "passé": "Événement passé (déjà terminé).",
            "hors zone": "Hors zone (lieu hors périmètre cité, aucun lieu couvert).",
            "source large": "Hors périmètre (source large, aucun lieu couvert cité).",
        }
        conn.executemany(
            "UPDATE events_raw SET statut='rejected', llm_justification=? WHERE id=?",
            [(motifs[m], r["id"]) for r, m in hits])
        verbe = "rejeté(s)"
    conn.commit()
    conn.close()
    print(f"\n✅ {len(ids)} événement(s) {verbe}.")
    log.info("Purge hors zone : %d %s", len(ids), verbe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
