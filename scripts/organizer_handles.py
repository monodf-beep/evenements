#!/usr/bin/env python3
"""Recherche du compte Instagram OFFICIEL d'un ORGANISATEUR, par AGENT WEB.

Le handle Instagram d'un organisme n'est JAMAIS devinable depuis son nom (sigle,
abréviation...) : ce script se contente de PROPOSER un candidat (avec preuve) —
c'est Franck qui CONFIRME (ou refuse) dans le back-office (/semaine). Rien n'est
jamais écrit en status='confirmed' ici : seule la confirmation manuelle autorise
utils.social.caption à mentionner un compte dans une légende publiée.

Exemples :
  .venv/bin/python3 -m scripts.organizer_handles --dry-run
  .venv/bin/python3 -m scripts.organizer_handles --cap 10
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import completeness as comp
from utils import organizers

log = get_logger("organizer_handles")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
SEARCH_MODEL = (os.getenv("ANTHROPIC_MODEL_SEARCH") or os.getenv("ANTHROPIC_MODEL")
                or "claude-sonnet-5")


def _select(conn: sqlite3.Connection, cap: int, today: str) -> list[str]:
    """Organisateurs distincts d'événements retenus à venir, non vides, encore
    absents de organizer_ig_handles (jamais recherchés)."""
    rows = conn.execute(
        f"SELECT DISTINCT organisateur FROM events_raw WHERE statut IN "
        f"({','.join('?' * len(comp.RETAINED_STATUTS))}) AND duplicate_of IS NULL "
        "AND COALESCE(organisateur,'') <> '' "
        "AND COALESCE(date_event_end, date_event_start,'') >= ?",
        (*comp.RETAINED_STATUTS, today)).fetchall()
    existing = {r["organisateur_key"] for r in
                conn.execute("SELECT organisateur_key FROM organizer_ig_handles").fetchall()}
    out: list[str] = []
    seen: set[str] = set()
    for r in rows:
        name = (r["organisateur"] or "").strip()
        key = organizers.normalize(name)
        if not key or key in existing or key in seen:
            continue
        seen.add(key)
        out.append(name)
        if len(out) >= cap:
            break
    return out


def search_handle(name: str, client) -> dict:
    """Agent web : propose le compte Instagram officiel de l'organisme. {} si aucun
    trouvé avec certitude — on ne devine jamais un handle plausible mais non sourcé."""
    prompt = (
        "Tu cherches le compte Instagram OFFICIEL de cet organisme culturel "
        "(association, lieu, festival, collectivité...). Utilise la recherche web. "
        "Réponds UNIQUEMENT si tu es SÛR qu'il s'agit bien du compte officiel de cet "
        "organisme précis (pas un homonyme, pas un fan-compte).\n\n"
        f"Organisme : {name}\n\n"
        "Réponds en JSON STRICT et rien d'autre :\n"
        '{"handle": "identifiant sans @ ou vide", '
        '"evidence": "où/comment tu l\'as vérifié (2-15 mots) ou vide", '
        '"found": true|false}'
    )
    try:
        msg = client.messages.create(
            model=SEARCH_MODEL, max_tokens=400,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:  # jamais bloquant
        log.warning("Recherche handle échouée (%s) : %s", name, exc)
        return {}
    try:
        from utils import usage
        usage.record_message(SEARCH_MODEL, msg, label="organizer_handle_search")
    except Exception:
        pass
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text").strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group())
    except (ValueError, TypeError):
        return {}
    return data if data.get("found") else {}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Recherche du compte Instagram officiel d'organisateurs (agent web).")
    parser.add_argument("--cap", type=int, default=10, help="Nombre max d'organisateurs par run.")
    parser.add_argument("--delay", type=float, default=1.0, help="Pause (s) entre deux organisateurs.")
    parser.add_argument("--dry-run", action="store_true", help="Lister sans appeler l'agent.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    organizers.ensure_table(conn)
    names = _select(conn, args.cap, today)
    log.info("Sélection : %d organisateur(s) sans recherche préalable (cap %d)",
             len(names), args.cap)

    if args.dry_run:
        for n in names:
            print(f"  · {n}")
        print(f"\n{len(names)} organisateur(s) SERAIENT traités (dry-run — aucun appel).")
        conn.close()
        return 0

    if not names:
        conn.close()
        return 0

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY absente — recherche de handle impossible.")
        conn.close()
        return 1

    import anthropic
    client = anthropic.Anthropic(api_key=api_key, timeout=90.0)
    found = 0
    for i, name in enumerate(names, 1):
        key = organizers.normalize(name)
        now = datetime.now().isoformat(timespec="seconds")
        result = search_handle(name, client)
        handle = (result.get("handle") or "").lstrip("@").strip()
        if handle:
            conn.execute(
                "INSERT OR REPLACE INTO organizer_ig_handles "
                "(organisateur_key, organisateur_label, handle, candidate, evidence, "
                " status, checked_at, confirmed_at) "
                "VALUES (?,?,NULL,?,?,'pending',?,NULL)",
                (key, name, handle, (result.get("evidence") or "").strip(), now))
            found += 1
            log.info("Candidat trouvé pour « %s » : @%s", name, handle)
        else:
            conn.execute(
                "INSERT OR REPLACE INTO organizer_ig_handles "
                "(organisateur_key, organisateur_label, handle, candidate, evidence, "
                " status, checked_at, confirmed_at) "
                "VALUES (?,?,NULL,NULL,NULL,'none',?,NULL)",
                (key, name, now))
        conn.commit()
        if args.delay and i < len(names):
            time.sleep(args.delay)

    conn.close()
    log.info("=== Handles organisateurs : %d candidat(s) sur %d ===", found, len(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
