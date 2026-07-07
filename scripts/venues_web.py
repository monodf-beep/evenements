#!/usr/bin/env python3
"""Recherche du LIEU par AGENT WEB (dernier recours, quand la source est muette).

Quand ni le JSON-LD ni le texte local ne donnent de lieu (ex. « Katy Perry en Savoie »),
on lance un agent Claude AVEC RECHERCHE WEB pour trouver la salle/le site + la ville.
Remplit lieu/ville + venue_source='web'. Réservé au haut du panier (coût recherche) :
retenu, daté, à venir, score >= seuil, et lieu encore vide.

⚠️ Coût : chaque événement = un appel LLM avec recherche web. Borné (--cap), --dry-run.

Exemples :
  .venv/bin/python3 -m scripts.venues_web --dry-run
  .venv/bin/python3 -m scripts.venues_web --cap 15 --min-score 7
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.venues import _clean

log = get_logger("venues_web")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
MODEL = (os.getenv("ANTHROPIC_MODEL_SEARCH") or os.getenv("ANTHROPIC_MODEL")
         or "claude-sonnet-5")


def _dates(ev: dict) -> str:
    s = (ev.get("date_event_start") or "").strip()
    e = (ev.get("date_event_end") or "").strip()
    if s and e and e != s:
        return f"du {s} au {e}"
    return s or "date à confirmer"


def web_venue(ev: dict, client) -> tuple[str, str, str]:
    """(lieu, ville, source) via recherche web. ('','','web_none') si rien de fiable."""
    prompt = (
        "Tu identifies le LIEU EXACT (salle, site, château, place, parc…) et la VILLE "
        "où se déroule un événement culturel.\n"
        "RÈGLES :\n"
        "1) Si le lieu est CLAIREMENT nommé dans le titre ou la description ci-dessous "
        "(ex. « al Valentino » → Parco del Valentino ; « au Forte di Bard » → Forte di "
        "Bard), utilise-le DIRECTEMENT — c'est l'info de l'événement lui-même — et "
        "complète/vérifie la ville par recherche web si besoin.\n"
        "2) Sinon, UTILISE la recherche web pour le trouver, et ne réponds found:true "
        "QUE si une source fiable (site officiel, billetterie, presse) le confirme.\n"
        "3) Ne devine JAMAIS un lieu au hasard.\n\n"
        f"Événement : {_clean(ev.get('article_title') or ev.get('title'))}\n"
        f"Dates : {_dates(ev)}\n"
        f"Territoire : {ev.get('territoire') or ''}\n"
        f"Description : {_clean(ev.get('description'))[:500]}\n\n"
        'Réponds en JSON STRICT et rien d\'autre : '
        '{"lieu": "…" ou "", "ville": "…" ou "", "found": true|false}'
    )
    try:
        msg = client.messages.create(
            model=MODEL, max_tokens=400,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:  # jamais bloquant
        log.warning("Recherche web échouée : %s", exc)
        return ("", "", "web_none")
    try:
        from utils import usage
        usage.record_message(MODEL, msg, label="venue_web")
    except Exception:
        pass
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text").strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return ("", "", "web_none")
    try:
        data = json.loads(m.group())
    except (ValueError, TypeError):
        return ("", "", "web_none")
    if not data.get("found"):
        return ("", "", "web_none")
    lieu, ville = _clean(data.get("lieu", "")), _clean(data.get("ville", ""))
    return (lieu, ville, "web") if lieu else ("", "", "web_none")


def _select(conn, args, today: str):
    where = [
        "statut IN ('evaluated','published_cs','published_sub')",
        "duplicate_of IS NULL",
        "COALESCE(lieu,'') = ''",                              # lieu encore vide
        "COALESCE(date_event_start,'') <> ''",                 # daté
        "COALESCE(llm_score,0) >= ?",
    ]
    params: list = [args.min_score]
    if not args.include_past:
        where.append("COALESCE(date_event_end, date_event_start) >= ?")
        params.append(today)
    sql = (f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
           f"ORDER BY COALESCE(llm_score,0) DESC, date_event_start ASC LIMIT ?")
    params.append(args.cap)
    return conn.execute(sql, params).fetchall()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Recherche du lieu par agent web.")
    parser.add_argument("--cap", type=int, default=15, help="Nombre max par run.")
    parser.add_argument("--min-score", type=int, default=7, help="Score minimum (défaut 7).")
    parser.add_argument("--delay", type=float, default=1.0, help="Pause (s) entre deux appels.")
    parser.add_argument("--include-past", action="store_true", help="Inclure les événements passés.")
    parser.add_argument("--dry-run", action="store_true", help="Lister sans appeler l'agent.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = _select(conn, args, today)
    log.info("Sélection : %d événement(s) sans lieu (cap %d, min-score %d, modèle %s)",
             len(rows), args.cap, args.min_score, MODEL)

    if args.dry_run:
        for r in rows:
            print(f"  [{r['id']}] score={r['llm_score']} · {(r['title'] or '')[:70]}")
        print(f"\n{len(rows)} événement(s) SERAIENT cherchés (dry-run — aucun appel).")
        conn.close()
        return 0

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY absente — recherche web impossible.")
        conn.close()
        return 1

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    ok = 0
    for i, r in enumerate(rows, 1):
        lieu, ville, src = web_venue(dict(r), client)
        if src == "web" and lieu:
            conn.execute(
                "UPDATE events_raw SET lieu=?, ville=?, venue_source=? WHERE id=?",
                (lieu, ville, src, r["id"]))
            conn.commit()
            ok += 1
            log.info("Lieu trouvé (web) id=%s : %s%s", r["id"], lieu,
                     f" · {ville}" if ville else "")
        if args.delay and i < len(rows):
            time.sleep(args.delay)

    conn.close()
    log.info("=== Lieux (web) : %d trouvé(s) sur %d ===", ok, len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
