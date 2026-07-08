#!/usr/bin/env python3
"""Diagnostic du backlog « À compléter » : POURQUOI ces événements sont coincés.

Lecture seule. Casse le mystère « 178 incomplets » en catégories actionnables :
quel champ manque, par type de source, combien sont sans page exploitable, combien
ont déjà été tentés en web, combien sont probablement passés.

Usage : .venv/bin/python3 -m scripts.diagnose_backlog
"""
from __future__ import annotations
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import completeness as comp

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main() -> int:
    today = date.today().isoformat()
    year = int(today[:4])
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE statut IN ('evaluated','published_cs','published_sub') "
        "AND duplicate_of IS NULL "
        "AND (COALESCE(date_event_end, date_event_start, '')='' "
        "     OR COALESCE(date_event_end, date_event_start) >= ?)", (today,)).fetchall()]
    conn.close()

    incomplete = [e for e in rows if not comp.is_complete(e)]
    print(f"\n{'='*66}\nBACKLOG « À COMPLÉTER » — {len(incomplete)} incomplets (sur {len(rows)} retenus à venir)")

    # 1) Quel champ manque
    from collections import Counter
    miss = Counter()
    for e in incomplete:
        for _k, lbl in comp.missing_fields(e):
            miss[lbl] += 1
    print("\n① Champ manquant (un événement peut en cumuler) :")
    for lbl, n in miss.most_common():
        print(f"    {lbl:12} : {n}")

    # 2) Focus sur les « manque Date »
    no_date = [e for e in incomplete if comp._empty(e.get("date_event_start"))]
    print(f"\n② Focus « manque Date » : {len(no_date)}")

    def is_radar(e):
        return e.get("source_type") == "radar" or "(radar)" in (e.get("source_name") or "")
    def no_page(e):
        u = e.get("url_source") or ""
        return (not u) or u.startswith("gmail:") or "news.google.com" in u

    radar = sum(1 for e in no_date if is_radar(e))
    nopage = sum(1 for e in no_date if no_page(e))
    tried_web = sum(1 for e in no_date if (e.get("date_web_at") or ""))
    # probablement passés : une année révolue apparaît dans le titre ou date_start brut
    past_years = "|".join(str(y) for y in range(2015, year))
    likely_past = 0
    for e in no_date:
        blob = f"{e.get('title','')} {e.get('date_start','')}"
        if re.search(rf"(?<!\d)({past_years})(?!\d)", blob):
            likely_past += 1
    print(f"    • source RADAR (presse, pas de page officielle)   : {radar}")
    print(f"    • sans page exploitable (gmail / google news)      : {nopage}")
    print(f"    • déjà tentés par l'agent web (cooldown actif)     : {tried_web}")
    print(f"    • probablement PASSÉS (année révolue dans le texte): {likely_past}")

    # 3) Les « datables » restants = vrai gisement pour l'automatisation
    datable = [e for e in no_date if not is_radar(e) and not no_page(e)
               and not e.get("date_web_at")]
    print(f"\n③ « Manque Date » avec une VRAIE page officielle, jamais tentés en web : {len(datable)}")
    print("    → ce sont les seuls où l'automatisation a encore une marge. Exemples :")
    for e in datable[:12]:
        print(f"      [{e['id']}] {(e.get('title') or '')[:64]}  ({e.get('source_name','')[:30]})")

    print(f"\n{'='*66}")
    print("LECTURE : radar + sans-page + passés = tail NON automatisable (à écarter ou")
    print("à saisir à la main). Le gisement réel = ③. Rien ici n'est lié aux 2 langues.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
