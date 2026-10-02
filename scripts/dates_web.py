#!/usr/bin/env python3
"""Recherche de la DATE par AGENT WEB (dernier recours, quand la source est muette).

Symétrique de scripts/venues_web.py (lieu) et scripts/images_web.py (image). Quand
ni le texte ni la page ne donnent de date exploitable (ex. « La Saint-Ours 2026 »,
« Orelsan »…), on lance un agent Claude AVEC RECHERCHE WEB pour trouver la/les
date(s) de l'édition À VENIR. Remplit date_event_start/end + date_source='web'.

Prudence : found=true UNIQUEMENT si une source fiable confirme (une mauvaise date
est pire que pas de date). Réservé au haut du panier (coût), borné (--cap), --dry-run.

Exemples :
  .venv/bin/python3 -m scripts.dates_web --dry-run
  .venv/bin/python3 -m scripts.dates_web --cap 15 --min-score 7
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
from scripts.scraper_events import web_cooldown_sql, mark_web_attempt

log = get_logger("dates_web")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
MODEL = (os.getenv("ANTHROPIC_MODEL_SEARCH") or os.getenv("ANTHROPIC_MODEL")
         or "claude-sonnet-5")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def web_date(ev: dict, client, today: str) -> tuple[str, str, str]:
    """(début, fin, source) via recherche web. ('','','web_none') si rien de fiable."""
    prompt = (
        "Tu trouves la ou les DATES EXACTES d'un événement culturel (jour de début et, "
        "s'il dure plusieurs jours, jour de fin).\n"
        "RÈGLES STRICTES :\n"
        f"1) Aujourd'hui = {today}. On veut l'édition/la séance À VENIR (date >= aujourd'hui). "
        "S'il n'y a qu'une édition passée, réponds found:false.\n"
        "2) Utilise la recherche web (site officiel, billetterie, presse). Ne réponds "
        "found:true QUE si une source fiable confirme la date. Ne DEVINE JAMAIS.\n"
        "3) Format ISO strict AAAA-MM-JJ.\n\n"
        f"Événement : {_clean(ev.get('article_title') or ev.get('title'))}\n"
        f"Lieu : {_clean(ev.get('lieu'))} · Ville : {_clean(ev.get('ville'))}\n"
        f"Territoire : {ev.get('territoire') or ''}\n"
        f"Description : {_clean(ev.get('description'))[:400]}\n\n"
        'Réponds en JSON STRICT et rien d\'autre : '
        '{"start": "AAAA-MM-JJ" ou "", "end": "AAAA-MM-JJ" ou "", "found": true|false}'
    )
    try:
        msg = client.messages.create(
            model=MODEL, max_tokens=400,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:
        # PLAFOND API ≠ échec de fiche (utils/api_limite.py) : ce dernier recours est
        # appelé en boucle par scripts/dates_web.py ET par scripts.autocomplete._fill_date
        # — sans cette garde, un plafond y était avalé comme une simple page muette et
        # martelé sur chaque fiche suivante, exactement le trou déjà trouvé et bouché le
        # 2026-08-04 dans dates.py/venues.py/visuals.py mais oublié ici (dernier recours,
        # jamais mesuré dans l'incident d'origine).
        from utils.api_limite import PlafondAPI, est_plafond
        if est_plafond(exc):
            raise PlafondAPI(str(exc)) from exc
        log.warning("Recherche date échouée : %s", exc)
        return ("", "", "web_none")
    try:
        from utils import usage
        usage.record_message(MODEL, msg, label="date_web")
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
    start = (data.get("start") or "").strip()
    end = (data.get("end") or "").strip()
    if not _ISO.match(start):
        return ("", "", "web_none")
    if not _ISO.match(end):
        end = start
    if end < start:
        end = start
    if end < today:                     # sécurité : jamais une édition passée
        return ("", "", "web_none")
    return (start, end, "web")


def _select(conn, args, today: str):
    where = [
        "statut IN ('evaluated','published_cs','published_sub')",
        "duplicate_of IS NULL",
        "COALESCE(date_event_start,'') = ''",                  # sans date ISO
        "COALESCE(llm_score,0) >= ?",
    ]
    params: list = [args.min_score]
    if not args.force:                     # cooldown : on saute ce qu'on a tenté récemment
        where.append(web_cooldown_sql("date_web_at"))
    sql = (f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
           f"ORDER BY COALESCE(llm_score,0) DESC LIMIT ?")
    params.append(args.cap)
    return conn.execute(sql, params).fetchall()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Recherche de la date par agent web.")
    parser.add_argument("--cap", type=int, default=15, help="Nombre max par run.")
    parser.add_argument("--min-score", type=int, default=7, help="Score minimum (défaut 7).")
    parser.add_argument("--delay", type=float, default=1.0, help="Pause (s) entre deux appels.")
    parser.add_argument("--force", action="store_true", help="Ignorer le cooldown (re-tenter tout de suite).")
    parser.add_argument("--dry-run", action="store_true", help="Lister sans appeler l'agent.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = _select(conn, args, today)
    log.info("Sélection : %d événement(s) sans date (cap %d, min-score %d, modèle %s)",
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
    from utils.api_limite import PlafondAPI
    ok = 0
    plafonne = False
    for i, r in enumerate(rows, 1):
        try:
            start, end, src = web_date(dict(r), client, today)
        except PlafondAPI as exc:
            log.error("PLAFOND API atteint sur la fiche %s — lot arrêté, %d fiche(s) "
                      "non tentée(s) : %s", r["id"], len(rows) - i + 1, exc)
            plafonne = True
            break
        mark_web_attempt(conn, "date_web_at", r["id"])   # tentative armée (réussie ou non)
        if src == "web" and start:
            conn.execute(
                "UPDATE events_raw SET date_event_start=?, date_event_end=?, date_source=? "
                "WHERE id=?", (start, end, "web", r["id"]))
            conn.commit()
            ok += 1
            log.info("Date trouvée (web) id=%s : %s%s", r["id"], start,
                     f" → {end}" if end != start else "")
        if args.delay and i < len(rows):
            time.sleep(args.delay)

    conn.close()
    log.info("=== Dates (web) : %d trouvée(s) sur %d ===", ok, len(rows))
    if plafonne:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
