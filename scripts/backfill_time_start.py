#!/usr/bin/env python3
"""Rattrapage DÉTERMINISTE (zéro coût API) de l'heure de début (`time_start`) pour les
événements déjà enrichis/publiés AVANT ce champ (scripts.dates.extract_time,
2026-07-29). Ne relit QUE la matière déjà en base (enrich_data, description) — aucun
appel LLM, aucune recherche web.

Pour les événements DÉJÀ publiés sur l'Agenda (wp_post_id_as renseigné) dont une heure
est trouvée, republie en TEXTE SEUL (skip_media=True) pour que la fiche WordPress/
Schema.org Event reflète la vraie heure, pas seulement la base locale.

SÛR : --dry-run par défaut (affiche ce qui serait fait), --apply pour écrire, --cap
pour borner le nombre de republications WordPress par run.

Usage (VPS) :
    .venv/bin/python -m scripts.backfill_time_start                  # simulation
    .venv/bin/python -m scripts.backfill_time_start --apply --cap 50
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.dates import extract_time
from scripts.scraper_events import init_db

log = get_logger("backfill-time-start")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _time_from_event(ev: dict) -> str:
    """Même ordre de priorité qu'à l'enrichissement (scripts/enrich.py) : infos
    pratiques et encadré (factuels) avant programme/prose, repli sur la description
    brute pour les événements jamais enrichis."""
    texts = []
    if ev.get("enrich_data"):
        try:
            result = json.loads(ev["enrich_data"])
        except (ValueError, TypeError):
            result = {}
        art = result.get("article") or {}
        prog = art.get("programme")
        prog_text = " ".join(str(p) for p in prog) if isinstance(prog, list) else str(prog or "")
        texts = [result.get("infos_pratiques", ""), art.get("encadre", ""),
                 prog_text, art.get("chapo", ""), art.get("corps", "")]
    texts.append(ev.get("description") or "")
    for t in texts:
        found = extract_time(t or "")
        if found:
            return found
    return ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Rattrape time_start (déterministe, zéro coût API) sur les événements déjà en base.")
    parser.add_argument("--apply", action="store_true", help="Écrit + republie (sinon simulation).")
    parser.add_argument("--cap", type=int, default=50,
                        help="Nb max de republications WordPress par run (défaut 50).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(time_start,'')='' "
        "AND duplicate_of IS NULL "
        "AND (COALESCE(enrich_data,'')!='' OR COALESCE(description,'')!='')"
    ).fetchall()]
    log.info("%d événement(s) sans time_start à examiner", len(rows))

    found_local = republished = 0
    to_republish = []
    for ev in rows:
        t = _time_from_event(ev)
        if not t:
            continue
        found_local += 1
        log.info("[%d] heure trouvée : %s — %s", ev["id"], t, (ev.get("title") or "")[:60])
        if args.apply:
            conn.execute("UPDATE events_raw SET time_start=? WHERE id=?", (t, ev["id"]))
            conn.commit()
        if ev.get("wp_post_id_as"):
            to_republish.append((ev, t))

    log.info("=== %d heure(s) trouvée(s) localement (sur %d examinés)%s ===",
             found_local, len(rows), "" if args.apply else "  (simulation : rien écrit)")

    if not args.apply:
        log.info("%d événement(s) déjà publiés seraient republiés pour refléter l'heure "
                 "(relance avec --apply).", len(to_republish))
        conn.close()
        return 0

    if to_republish:
        from scripts.publisher_as import publish_to_as
        capped = to_republish[:args.cap]
        if len(to_republish) > args.cap:
            log.info("%d événement(s) publiés éligibles, borné à --cap %d (relance pour "
                     "traiter le reste).", len(to_republish), args.cap)
        ok = 0
        for ev, t in capped:
            ev["time_start"] = t
            wp_id, _permalink, _raw = publish_to_as(ev, skip_media=True)
            if wp_id:
                ok += 1
            else:
                log.warning("[%d] republication échouée.", ev["id"])
        log.info("=== Republication terminée : %d/%d fiche(s) WordPress mise(s) à jour. ===",
                 ok, len(capped))

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
