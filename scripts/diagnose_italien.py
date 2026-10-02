#!/usr/bin/env python3
"""Diagnostic : POURQUOI si peu d'événements italiens en ligne ?

Montre le FUNNEL par territoire (scrapé → évalué → publié sur Agenda Sabauda) et la
répartition de langue DÉTECTÉE, puis le rendement PAR SOURCE pour les territoires
italiens (Piémont, Vallée d'Aoste) — pour distinguer :
  • un problème de SCRAPING (peu d'événements récoltés malgré des sources)  →  flux morts
  • un problème de PUBLICATION (récoltés mais jamais mis en ligne)          →  filtres/validation

Lecture seule. À lancer sur le VPS :
    .venv/bin/python scripts/diagnose_italien.py
"""
from __future__ import annotations
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.lang import detect_lang  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
EVALUATED = ("evaluated", "published_cs", "published_sub")


def _lang(r) -> str:
    return "it" if detect_lang(r["title"] or "", r["description"] or "",
                               r["territoire"] or "") == "it" else "fr"


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, description, territoire, source_name, statut, llm_score, "
        "wp_post_id_as FROM events_raw WHERE COALESCE(duplicate_of,0)=0").fetchall()]

    territoires = ["Savoie", "Piemonte", "Vallee-Aoste", "Nice", "(autre/vide)"]

    def bucket(terr):
        t = (terr or "").strip()
        for known in ("Savoie", "Piemonte", "Vallee-Aoste", "Nice"):
            if known.lower() in t.lower() or t.lower() in known.lower():
                return known
        # variantes accentuées
        tl = t.lower()
        if "piemont" in tl:
            return "Piemonte"
        if "aost" in tl:
            return "Vallee-Aoste"
        if "haute-savoie" in tl or "savoie" in tl:
            return "Savoie"
        if "nice" in tl or "alpes" in tl or "azur" in tl:
            return "Nice"
        return "(autre/vide)"

    stats = {t: {"scrape": 0, "eval": 0, "pub": 0, "pub_fr": 0, "pub_it": 0,
                 "scrape_it": 0} for t in territoires}
    for r in rows:
        t = bucket(r["territoire"])
        s = stats[t]
        s["scrape"] += 1
        if _lang(r) == "it":
            s["scrape_it"] += 1
        if r["statut"] in EVALUATED:
            s["eval"] += 1
        if (r["wp_post_id_as"] or 0) > 0:
            s["pub"] += 1
            s["pub_it" if _lang(r) == "it" else "pub_fr"] += 1

    print("\n" + "=" * 74)
    print("FUNNEL PAR TERRITOIRE  (événements non-doublons)")
    print("=" * 74)
    print(f"{'Territoire':16} {'scrapé':>7} {'(dont IT)':>10} {'évalué':>7} "
          f"{'publié':>7} {'pub FR':>7} {'pub IT':>7}")
    print("-" * 74)
    for t in territoires:
        s = stats[t]
        if s["scrape"] == 0:
            continue
        print(f"{t:16} {s['scrape']:>7} {s['scrape_it']:>10} {s['eval']:>7} "
              f"{s['pub']:>7} {s['pub_fr']:>7} {s['pub_it']:>7}")

    # Rendement par source pour les territoires italiens.
    print("\n" + "=" * 74)
    print("RENDEMENT PAR SOURCE — territoires italiens (Piémont, Vallée d'Aoste)")
    print("  (scrapé → publié ; une source à 0 scrapé = flux probablement mort)")
    print("=" * 74)
    per_src: dict[str, dict] = {}
    for r in rows:
        if bucket(r["territoire"]) not in ("Piemonte", "Vallee-Aoste"):
            continue
        src = (r["source_name"] or "?").strip() or "?"
        d = per_src.setdefault(src, {"scrape": 0, "pub": 0, "it": 0})
        d["scrape"] += 1
        if (r["wp_post_id_as"] or 0) > 0:
            d["pub"] += 1
        if _lang(r) == "it":
            d["it"] += 1
    print(f"{'Source':40} {'scrapé':>7} {'publié':>7} {'dont IT':>8}")
    print("-" * 74)
    for src, d in sorted(per_src.items(), key=lambda kv: -kv[1]["scrape"]):
        print(f"{src[:40]:40} {d['scrape']:>7} {d['pub']:>7} {d['it']:>8}")

    # Sources italiennes configurées SANS aucun événement scrapé (flux muets).
    cfg = ROOT / "config" / "sources.txt"
    if cfg.exists():
        configured = []
        for line in cfg.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(";")
            if len(parts) >= 3 and parts[1].strip() in ("Piemonte", "Vallee-Aoste"):
                configured.append(parts[2].strip())
        seen = {s for s in per_src}
        muettes = [c for c in configured if c not in seen
                   and not any(c.lower() in s.lower() or s.lower() in c.lower() for s in seen)]
        print("\n" + "=" * 74)
        print(f"SOURCES ITALIENNES CONFIGURÉES MAIS SANS AUCUN ÉVÉNEMENT ({len(muettes)}/"
              f"{len(configured)}) — flux à vérifier :")
        print("=" * 74)
        for m in muettes:
            print(f"  • {m}")

    conn.close()
    print("\nLECTURE : si « scrapé » est élevé mais « publié » faible → goulot VALIDATION/"
          "score.\nSi « scrapé » est faible malgré les sources → goulot SCRAPING (flux "
          "morts ci-dessus).\n« dont IT » faible sur Piémont = les sources publient en FR "
          "ou la détection\nde langue coince.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
