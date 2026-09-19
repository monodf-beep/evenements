#!/usr/bin/env python3
"""Écarte proprement les événements « à compléter » NON récupérables — pour que le
compteur du dashboard reflète le vrai reste de travail (et non un backlog fantôme).

Cible UNIQUEMENT les incomplets sans espoir d'auto-complétion (mêmes critères que
scripts.diagnose_backlog) :
  • sans-page   : aucune URL source, ou Google News, ou source RADAR (presse) →
                  impossible de retrouver la date automatiquement.
  • passés      : une année révolue apparaît dans le titre / la date brute.

NE touche PAS : les événements à VRAIE page (gisement complétable), ni les
newsletters (rattrapables via gmail_relink), ni ceux déjà complets.

Action : passe statut → 'rejected' (réversible : ils quittent la liste « À
compléter » sans être supprimés). AUCUN appel API. Lecture seule par défaut.

Usage (sur le VPS) :
    .venv/bin/python -m scripts.discard_uncompletable                 # dry-run
    .venv/bin/python -m scripts.discard_uncompletable --apply         # écarte tout
    .venv/bin/python -m scripts.discard_uncompletable --past --apply  # seulement les passés
    .venv/bin/python -m scripts.discard_uncompletable --no-page --apply
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import completeness as comp  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _is_radar(e):
    return e.get("source_type") == "radar" or "(radar)" in (e.get("source_name") or "")


def _is_newsletter(e):
    return (e.get("url_source") or "").startswith("gmail:")


def _no_page(e):
    u = e.get("url_source") or ""
    return (not u) or "news.google.com" in u or _is_radar(e)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Écarte les 'à compléter' non récupérables.")
    parser.add_argument("--apply", action="store_true", help="Écrit (sinon dry-run).")
    parser.add_argument("--past", action="store_true", help="Cibler seulement les passés.")
    parser.add_argument("--no-page", action="store_true", help="Cibler seulement les sans-page.")
    args = parser.parse_args(argv)
    # Par défaut (aucun filtre) : les deux catégories.
    do_past = args.past or not (args.past or args.no_page)
    do_nopage = args.no_page or not (args.past or args.no_page)

    today = date.today().isoformat()
    year = int(today[:4])
    past_years = "|".join(str(y) for y in range(2015, year))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE statut IN ('evaluated','published_cs','published_sub') "
        "AND duplicate_of IS NULL "
        "AND (COALESCE(date_event_end, date_event_start, '')='' "
        "     OR COALESCE(date_event_end, date_event_start) >= ?)", (today,)).fetchall()]

    incomplete = [e for e in rows if not comp.is_complete(e)]
    no_date = [e for e in incomplete if comp._empty(e.get("date_event_start"))]

    def is_past(e):
        blob = f"{e.get('title','')} {e.get('date_start','')}"
        return bool(re.search(rf"(?<!\d)({past_years})(?!\d)", blob))

    targets: dict[int, tuple[dict, str]] = {}
    for e in no_date:
        # On ne touche jamais les newsletters (rattrapables autrement).
        if _is_newsletter(e):
            continue
        if do_nopage and _no_page(e):
            targets[e["id"]] = (e, "sans-page")
        elif do_past and is_past(e):
            targets[e["id"]] = (e, "passé")

    print(f"\nÀ compléter incomplets : {len(incomplete)} · sans date : {len(no_date)}")
    print(f"À écarter (non récupérables{' — passés' if not do_nopage else ''}"
          f"{' — sans-page' if not do_past else ''}) : {len(targets)}\n")
    by_reason: dict[str, int] = {}
    for _id, (e, reason) in sorted(targets.items()):
        by_reason[reason] = by_reason.get(reason, 0) + 1
    for reason, n in sorted(by_reason.items()):
        print(f"    {reason:10} : {n}")
    print()
    for _id, (e, reason) in list(sorted(targets.items()))[:15]:
        print(f"    [{e['id']}] ({reason}) {(e.get('title') or '')[:60]}  ({(e.get('source_name') or '')[:24]})")
    if len(targets) > 15:
        print(f"    … et {len(targets) - 15} autre(s)")

    if args.apply and targets:
        conn.executemany("UPDATE events_raw SET statut='rejected' WHERE id=?",
                         [(i,) for i in targets])
        conn.commit()
        print(f"\n✅ {len(targets)} événement(s) écarté(s) (statut → 'rejected', réversible).")
    elif targets:
        print(f"\n(dry-run : rien écrit — relance avec --apply pour écarter les {len(targets)}.)")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
