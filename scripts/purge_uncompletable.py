#!/usr/bin/env python3
"""Écarte le BRUIT STRUCTUREL de « À compléter » : les incomplétables par nature.

Le diagnostic (scripts.diagnose_backlog) le montre : une grande part des incomplets
sont des événements RADAR (presse — détection seule, charte §8) ou SANS PAGE
exploitable (Google News, ou aucune URL) auxquels il MANQUE la date ou le lieu. Il
n'existe AUCUNE page officielle à lire → ils ne seront jamais complétés
automatiquement. On les passe en 'rejected' (réversible) pour qu'ils quittent la file.

⚠️ Les NEWSLETTERS (« gmail:… ») ne sont PAS visées ici : elles ont bien une page
d'article — on la rattrape d'abord avec scripts.gmail_relink. Ne les écarter à la
main que si le rattrapage n'a rien donné.

On ne touche PAS les événements qui ont une vraie page officielle (le « gisement »
récupérable) ni ceux déjà complets.

Exemples :
  .venv/bin/python3 -m scripts.purge_uncompletable                 # dry-run
  .venv/bin/python3 -m scripts.purge_uncompletable --execute
  .venv/bin/python3 -m scripts.purge_uncompletable --radar-only    # seulement le radar
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import completeness as comp

log = get_logger("purge_uncompletable")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _is_radar(e: dict) -> bool:
    return e.get("source_type") == "radar" or "(radar)" in (e.get("source_name") or "")


def _no_page(e: dict) -> bool:
    """Vraiment SANS page exploitable. ⚠️ Les newsletters (« gmail:… ») en sont
    EXCLUES : elles ont bien une page d'article — on la rattrape avec
    scripts.gmail_relink AVANT d'envisager de les écarter. Ici, seuls les agrégateurs
    à mur de redirection (Google News) et l'absence totale d'URL comptent."""
    u = e.get("url_source") or ""
    return (not u) or "news.google.com" in u


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Écarte le bruit incomplétable (radar / sans page).")
    p.add_argument("--execute", action="store_true", help="Agir (sinon DRY-RUN).")
    p.add_argument("--radar-only", action="store_true",
                   help="Ne viser que le radar presse (laisser les newsletters).")
    args = p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE statut IN ('evaluated','published_cs','published_sub') "
        "AND duplicate_of IS NULL "
        "AND (COALESCE(date_event_end, date_event_start, '')='' "
        "     OR COALESCE(date_event_end, date_event_start) >= ?)", (today,)).fetchall()]

    targets = []
    for e in rows:
        if comp.is_complete(e):
            continue
        # Incomplétable = source sans page officielle ET il manque un champ STRUCTUREL
        # (date ou lieu) qu'aucune page ne pourra fournir.
        radar, nopage = _is_radar(e), _no_page(e)
        source_bad = radar if args.radar_only else (radar or nopage)
        missing = {lbl for _k, lbl in comp.missing_fields(e)}
        if source_bad and (missing & {"Date", "Lieu"}):
            reason = "radar (presse)" if radar else "sans page (Google News)"
            targets.append((e, reason))

    mode = "EXÉCUTION" if args.execute else "DRY-RUN (rien ne bouge)"
    scope = "radar uniquement" if args.radar_only else "radar + sans-page"
    print(f"\nBruit incomplétable à écarter ({scope}) — {mode} · {len(targets)}\n")
    for e, why in targets[:60]:
        print(f"  [{e['id']}] {(e.get('title') or '')[:58]:58} · {why}")
    if len(targets) > 60:
        print(f"  … et {len(targets) - 60} autres.")
    if not targets:
        print("Rien à écarter. 🎉")
        conn.close()
        return 0
    if not args.execute:
        print(f"\nDRY-RUN : {len(targets)} seraient écartés. Relance avec --execute.")
        conn.close()
        return 0

    conn.executemany(
        "UPDATE events_raw SET statut='rejected', "
        "llm_justification='Incomplétable (source sans page officielle) — écarté.' "
        "WHERE id=?", [(e["id"],) for e, _ in targets])
    conn.commit()
    conn.close()
    print(f"\n=== {len(targets)} événement(s) incomplétable(s) écarté(s) (réversible). ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
