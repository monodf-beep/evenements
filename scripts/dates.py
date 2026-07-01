#!/usr/bin/env python3
"""Extraction de la VRAIE date d'un événement (déterministe, sans LLM).

Le flux RSS ne donne que sa date de PUBLICATION (`entry.published`) — pas la date de
l'événement. Or on veut pouvoir circonscrire le travail (évaluation/rédaction) à une
PÉRIODE (« ce week-end », « week-end prochain »). Il faut donc extraire la période
réelle depuis le TEXTE (titre + description), en FR et IT.

LLM ? NON — parsing structuré à fort volume = code (voir docs/LLM_OU_CODE.md). On
gère les cas courants d'une programmation culturelle :
  - « le 5 juillet », « 5 juillet 2026 », « du 5 au 8 juillet », « du 30 juin au 3 juillet »
  - « dal 5 all'8 luglio », « dal 30 giugno al 3 luglio », « 5-8 luglio »
  - « jusqu'au 30 août » / « fino al 30 agosto » (fin seule → en cours jusqu'à…)
  - ISO 2026-07-05, dates numériques 05/07/2026, 05.07.2026 (jj/mm/aaaa, format européen)

Sortie stockée : date_event_start / date_event_end (ISO AAAA-MM-JJ) + date_source
('parsed' | 'none'). Les événements non datés vont dans le bac « date à confirmer ».
Cron : après dedupe, avant l'évaluation.
"""
from __future__ import annotations
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.scraper_events import init_db
from dotenv import load_dotenv

log = get_logger("dates")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

_MONTHS = {
    # français
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
    # italien
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6,
    "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))


def _strip(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def _iso(y: int, m: int, d: int) -> str | None:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def _year(day: int, month: int, ref: date) -> int:
    """Année sous-entendue (année absente du texte). On suppose un événement « à venir » :
    on garde l'année courante tant que la date n'est pas trop dans le passé (grâce de
    60 j pour les événements en cours / qui viennent de commencer) ; au-delà = l'an prochain.
    Ex. (réf. 1er juillet) : « 30 juin » → cette année ; « 5 janvier » → l'an prochain."""
    y = ref.year
    cand = _iso(y, month, day)
    if cand and (ref - date.fromisoformat(cand)).days > 60:
        y += 1
    return y


def parse_dates(text: str, ref: date | None = None) -> tuple[str, str, str]:
    """(date_start_iso, date_end_iso, source). source = 'parsed' | 'none'."""
    ref = ref or date.today()
    t = _strip(text)
    M = _MONTHS

    # 1) ISO explicite (éventuellement en plage)
    iso = re.findall(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if iso:
        starts = [f"{y}-{m}-{d}" for y, m, d in iso]
        starts = [s for s in starts if _iso(*map(int, s.split("-")))]
        if starts:
            return (min(starts), max(starts), "parsed")

    # 2) Plage « du 5 au 8 juillet [2026] » / « dal 5 al 8 luglio » (même mois)
    m = re.search(rf"(?:du|dal|dall'|dall’|da)?\s*(\d{{1,2}})\s*(?:au|al|all'|all’|[-–—à])\s*"
                  rf"(\d{{1,2}})\s+({_MONTH_RE})\.?\s*(\d{{4}})?", t)
    if m:
        d1, d2, mon, yr = int(m[1]), int(m[2]), M[m[3]], m[4]
        y = int(yr) if yr else _year(min(d1, d2), mon, ref)
        s, e = _iso(y, mon, d1), _iso(y, mon, d2)
        if s and e:
            return (min(s, e), max(s, e), "parsed")

    # 3) Plage inter-mois « du 30 juin au 3 juillet [2026] » / « dal 30 giugno al 3 luglio »
    m = re.search(rf"(?:du|dal|dall'|dall’|da)\s*(\d{{1,2}})\s+({_MONTH_RE})\.?\s*(\d{{4}})?\s*"
                  rf"(?:au|al|all'|all’)\s*(\d{{1,2}})\s+({_MONTH_RE})\.?\s*(\d{{4}})?", t)
    if m:
        d1, mon1, y1, d2, mon2, y2 = int(m[1]), M[m[2]], m[3], int(m[4]), M[m[5]], m[6]
        yy1 = int(y1) if y1 else _year(d1, mon1, ref)
        yy2 = int(y2) if y2 else (yy1 if mon2 >= mon1 else yy1 + 1)
        s, e = _iso(yy1, mon1, d1), _iso(yy2, mon2, d2)
        if s and e:
            return (min(s, e), max(s, e), "parsed")

    # 4) Fin seule « jusqu'au 30 août » / « fino al 30 agosto » → en cours jusqu'à…
    m = re.search(rf"(?:jusqu['’ ]?au|fino all?['’ ]?|sino al)\s*(\d{{1,2}})\s+"
                  rf"({_MONTH_RE})\.?\s*(\d{{4}})?", t)
    if m:
        d2, mon, yr = int(m[1]), M[m[2]], m[3]
        y = int(yr) if yr else _year(d2, mon, ref)
        e = _iso(y, mon, d2)
        if e:
            return ("", e, "parsed")  # début inconnu = en cours

    # 5) Date simple « [le] 5 juillet [2026] » / « 5 luglio »
    m = re.search(rf"\b(\d{{1,2}})\s+({_MONTH_RE})\.?\s*(\d{{4}})?", t)
    if m:
        d1, mon, yr = int(m[1]), M[m[2]], m[3]
        y = int(yr) if yr else _year(d1, mon, ref)
        s = _iso(y, mon, d1)
        if s:
            return (s, s, "parsed")

    # 6) Numérique jj/mm/aaaa ou jj.mm.aaaa (format européen)
    m = re.search(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b", t)
    if m:
        d1, mon, y = int(m[1]), int(m[2]), int(m[3])
        s = _iso(y, mon, d1)
        if s:
            return (s, s, "parsed")

    return ("", "", "none")


def ensure_columns(conn: sqlite3.Connection) -> None:
    for col, decl in (("date_event_start", "TEXT"),
                      ("date_event_end", "TEXT"),
                      ("date_source", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()


def main() -> int:
    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    ensure_columns(conn)
    # On (re)date les événements pas encore datés et non fusionnés.
    rows = conn.execute(
        "SELECT id, title, description FROM events_raw "
        "WHERE (date_source IS NULL OR date_source = '') AND statut != 'merged'"
    ).fetchall()
    log.info("%d événement(s) à dater", len(rows))
    parsed = 0
    for r in rows:
        text = f"{r['title']}\n{r['description'] or ''}"
        s, e, src = parse_dates(text)
        conn.execute(
            "UPDATE events_raw SET date_event_start=?, date_event_end=?, date_source=? WHERE id=?",
            (s, e, src, r["id"]))
        if src == "parsed":
            parsed += 1
    conn.commit()
    conn.close()
    log.info("=== Datation terminée : %d/%d datés (%d sans date) ===",
             parsed, len(rows), len(rows) - parsed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
