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

Trois passes, du plus sûr/gratuit au dernier recours :
  1. TEXTE (titre + description) — regex FR/IT, gratuit et instantané ;
  2. PAGE structurée — JSON-LD schema.org Event + <time datetime> (déterministe) ;
  3. LLM — jugement de langue sur la prose de la page, quand 1 et 2 échouent
     (beaucoup de sites, surtout IT, ne donnent la date qu'en toutes lettres).
     Économique, borné, idempotent ; désactivable par DATES_LLM=0.

Sortie stockée : date_event_start / date_event_end (ISO AAAA-MM-JJ) + date_source
('parsed' | 'page' | 'llm' | 'none' | 'nodate' | 'llm_none'). Les non-datés vont
dans le bac « date à confirmer ». Cron : après dedupe, avant l'évaluation.
"""
from __future__ import annotations
import argparse
import html as htmlmod
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.scraper_events import init_db
from dotenv import load_dotenv

log = get_logger("dates")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
# Récupération de la date sur la PAGE de l'événement (2ᵉ passe, déterministe).
FETCH_CAP = int(os.getenv("DATES_FETCH_CAP", "200"))   # pages fetchées par run (max)
FETCH_TIMEOUT = int(os.getenv("DATES_FETCH_TIMEOUT", "10"))
# UA de NAVIGATEUR : beaucoup de sites (WAF/CDN) renvoient 403/404 à un robot déclaré.
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
       "Accept-Language": "fr,it;q=0.8,en;q=0.6"}


def _swap_www(url: str) -> str:
    """Bascule www ↔ non-www dans l'hôte (redirections mal configurées → 404)."""
    from urllib.parse import urlsplit, urlunsplit
    p = urlsplit(url)
    host = p.netloc[4:] if p.netloc.startswith("www.") else "www." + p.netloc
    return urlunsplit((p.scheme, host, p.path, p.query, p.fragment))


def _robust_get(url: str):
    """GET avec UA navigateur ; si échec/non-200, retente l'hôte www↔non-www.
    Renvoie une réponse 200 non vide, ou None."""
    tried = []
    for u in (url, _swap_www(url)):
        if u in tried:
            continue
        tried.append(u)
        try:
            r = requests.get(u, timeout=FETCH_TIMEOUT, headers=_UA, allow_redirects=True)
            if r.status_code == 200 and r.text:
                return r
        except requests.RequestException:
            continue
    return None
# 3ᵉ passe : datation LLM (jugement de langue) sur les non-datés que le regex et le
# JSON-LD n'ont pas su lire — beaucoup de pages (surtout IT) donnent la date en prose.
# Économique et borné. Actif si une clé Anthropic est présente (désactivable : DATES_LLM=0).
DATES_LLM = os.getenv("DATES_LLM", "1") not in ("0", "false", "False", "")
DATES_LLM_CAP = int(os.getenv("DATES_LLM_CAP", "150"))
DATES_LLM_MODEL = os.getenv("DATES_LLM_MODEL") or os.getenv("ANTHROPIC_MODEL_EXTRACT",
                                                            "claude-haiku-4-5-20251001")

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

    # 2) Plage même mois : « du 5 au 8 juillet », « dal 5 al 8 luglio », « 5 e 6 luglio »,
    #    « sabato 5 e domenica 6 luglio » (un mot — ex. jour de semaine — toléré après le lien)
    m = re.search(rf"(?:du|dal|dall'|dall’|da)?\s*(?<!\d)(\d{{1,2}})(?!\d)\s*(?:au|al|all'|all’|et|e|&|[-–—à])\s*"
                  rf"(?:[a-zà-ÿ]+\s+)?(?<!\d)(\d{{1,2}})(?!\d)\s+({_MONTH_RE})\.?\s*(\d{{4}})?", t)
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
        # Année : si UNE SEULE borne la porte (« du 2 mars au 27 avril 2025 »), on la
        # PROPAGE à l'autre au lieu de la deviner — sinon _year() peut inventer une
        # année délirante pour la borne nue (ex. « 2 mars » → 2027) et créer une plage
        # de deux ans à l'envers. On recule/avance d'un an si l'ordre des mois l'impose.
        if y1 and y2:
            yy1, yy2 = int(y1), int(y2)
        elif y2 and not y1:            # année seulement sur la fin → la propager au début
            yy2 = int(y2)
            yy1 = yy2 if mon1 <= mon2 else yy2 - 1
        elif y1 and not y2:            # année seulement sur le début → la propager à la fin
            yy1 = int(y1)
            yy2 = yy1 if mon2 >= mon1 else yy1 + 1
        else:                          # aucune année → inférence + cohérence des mois
            yy1 = _year(d1, mon1, ref)
            yy2 = yy1 if mon2 >= mon1 else yy1 + 1
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


def dates_from_page(html: str) -> tuple[str, str, str]:
    """Extrait une date depuis le HTML d'une page d'événement, du plus FIABLE au moins :
    1) JSON-LD schema.org Event (startDate/endDate) — le standard des sites d'événements ;
    2) balises <time datetime="…"> ;
    3) meta (article:published_time n'est PAS la date d'événement → ignoré).
    Ne devine JAMAIS depuis le texte libre de la page (trop de faux positifs)."""
    # 1) JSON-LD "startDate": "2026-07-05" (ou avec heure "2026-07-05T21:00")
    ms = re.search(r'"startDate"\s*:\s*"(\d{4}-\d{2}-\d{2})', html)
    if ms:
        me = re.search(r'"endDate"\s*:\s*"(\d{4}-\d{2}-\d{2})', html)
        s = ms.group(1)
        e = me.group(1) if me else s
        if _iso(*map(int, s.split("-"))):
            return (min(s, e), max(s, e), "page")
    # 2) <time datetime="2026-07-05">
    times = re.findall(r'<time[^>]+datetime=["\'](\d{4}-\d{2}-\d{2})', html, re.I)
    times = [t for t in times if _iso(*map(int, t.split("-")))]
    if times:
        return (min(times), max(times), "page")
    return ("", "", "")


def fetch_event_dates(url: str) -> tuple[str, str, str]:
    """Télécharge la page et en extrait la date (JSON-LD/<time>). ('','','nodate') si rien."""
    if not url or url.startswith("gmail:") or "news.google.com" in url:
        return ("", "", "nodate")
    r = _robust_get(url)
    if r is None:
        return ("", "", "nodate")
    s, e, src = dates_from_page(r.text)
    return (s, e, "page") if src == "page" else ("", "", "nodate")


def fetch_page_text(url: str) -> str:
    """Texte visible d'une page (pour la datation LLM). '' si inaccessible/hors périmètre."""
    if not url or url.startswith("gmail:") or "news.google.com" in url:
        return ""
    r = _robust_get(url)
    if r is None:
        return ""
    doc = r.text
    doc = re.sub(r"(?is)<(script|style|nav|header|footer|noscript)[^>]*>.*?</\1>", " ", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    return re.sub(r"\s+", " ", htmlmod.unescape(doc)).strip()[:5000]


def llm_dates(material: str, ref: date, client, model: str) -> tuple[str, str, str]:
    """Le LLM lit la matière et rend la période de l'ÉVÉNEMENT. ('','','llm_none') si rien.

    Jugement de langue (FR/IT), pas de parsing structuré : on ne l'utilise qu'en
    dernier recours, quand regex + JSON-LD ont échoué (voir docs/LLM_OU_CODE.md).
    """
    material = (material or "").strip()
    if not material:
        return ("", "", "llm_none")
    prompt = (
        "Tu extrais la DATE de déroulement d'un événement culturel à partir du texte "
        "fourni (français ou italien). Ignore les dates de publication, d'inscription "
        "ou de vernissage isolé : ce qui compte, c'est QUAND l'événement a lieu.\n"
        f"Date du jour (pour déduire l'année si absente) : {ref.isoformat()}.\n"
        "Règles : une seule date → start = end ; une plage → les deux ; une fin seule "
        "(« jusqu'au… ») → start vide, end rempli ; si aucune date d'événement n'est "
        "trouvable, found=false.\n\n"
        f"TEXTE :\n{material[:4000]}\n\n"
        'Réponds en JSON STRICT et rien d\'autre : '
        '{"start": "AAAA-MM-JJ" ou "", "end": "AAAA-MM-JJ" ou "", "found": true|false}'
    )
    try:
        msg = client.messages.create(
            model=model, max_tokens=150,
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:  # jamais bloquant
        log.warning("Datation LLM échouée : %s", exc)
        return ("", "", "llm_none")
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text").strip()
    blob = raw[raw.find("{"):raw.rfind("}") + 1] if "{" in raw else ""
    try:
        data = json.loads(blob or raw)
    except (ValueError, TypeError):
        return ("", "", "llm_none")
    if not data.get("found"):
        return ("", "", "llm_none")
    s, e = (data.get("start") or "").strip(), (data.get("end") or "").strip()
    # Validation stricte : on n'accepte que des dates ISO réelles.
    s = s if (re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) and _iso(*map(int, s.split("-")))) else ""
    e = e if (re.fullmatch(r"\d{4}-\d{2}-\d{2}", e) and _iso(*map(int, e.split("-")))) else ""
    if s and e:
        return (min(s, e), max(s, e), "llm")
    if s or e:
        return (s, e or s, "llm") if s else ("", e, "llm")
    return ("", "", "llm_none")


def ensure_columns(conn: sqlite3.Connection) -> None:
    for col, decl in (("date_event_start", "TEXT"),
                      ("date_event_end", "TEXT"),
                      ("date_source", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Datation des événements (texte + page).")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Ne pas aller lire les pages (parsing texte seulement).")
    parser.add_argument("--fetch-cap", type=int, default=FETCH_CAP,
                        help="Nombre max de pages à télécharger sur ce run.")
    parser.add_argument("--no-llm", action="store_true",
                        help="Ne pas utiliser la datation LLM de dernier recours.")
    parser.add_argument("--llm-cap", type=int, default=DATES_LLM_CAP,
                        help="Nombre max d'événements datés par LLM sur ce run.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    ensure_columns(conn)

    # --- Passe 1 : texte (titre + description), gratuit et instantané ---
    rows = conn.execute(
        "SELECT id, title, description FROM events_raw "
        "WHERE (date_source IS NULL OR date_source = '') AND statut != 'merged'"
    ).fetchall()
    log.info("Passe texte : %d événement(s) à dater", len(rows))
    parsed = 0
    for r in rows:
        s, e, src = parse_dates(f"{r['title']}\n{r['description'] or ''}")
        conn.execute(
            "UPDATE events_raw SET date_event_start=?, date_event_end=?, date_source=? WHERE id=?",
            (s, e, src, r["id"]))
        if src == "parsed":
            parsed += 1
    conn.commit()
    log.info("Passe texte : %d daté(s) par le texte", parsed)

    # --- Passe 2 : page de l'événement (JSON-LD/<time>), pour les restants ---
    from_page = 0
    if not args.no_fetch:
        todo = conn.execute(
            "SELECT id, url_source FROM events_raw "
            "WHERE date_source = 'none' AND statut != 'merged' "
            "  AND url_source NOT LIKE 'gmail:%' AND url_source NOT LIKE '%news.google.com%' "
            "LIMIT ?", (args.fetch_cap,)).fetchall()
        log.info("Passe page : %d page(s) à lire (cap %d)", len(todo), args.fetch_cap)
        for r in todo:
            s, e, src = fetch_event_dates(r["url_source"])
            # 'page' = trouvé ; 'nodate' = lu mais rien (ne sera plus re-fetché).
            conn.execute(
                "UPDATE events_raw SET date_event_start=?, date_event_end=?, date_source=? WHERE id=?",
                (s, e, src, r["id"]))
            if src == "page":
                from_page += 1
            conn.commit()
        log.info("Passe page : %d daté(s) via la page", from_page)

    # --- Passe 3 : datation LLM (dernier recours) pour les non-datés restants ---
    from_llm = 0
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if DATES_LLM and not args.no_llm and api_key:
        todo = conn.execute(
            "SELECT id, title, description, url_source FROM events_raw "
            "WHERE date_source IN ('none', 'nodate') AND statut != 'merged' "
            "  AND url_source NOT LIKE 'gmail:%' AND url_source NOT LIKE '%news.google.com%' "
            "LIMIT ?", (args.llm_cap,)).fetchall()
        log.info("Passe LLM : %d événement(s) à dater (modèle %s, cap %d)",
                 len(todo), DATES_LLM_MODEL, args.llm_cap)
        if todo:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
            ref = date.today()
            for r in todo:
                # La page porte la vraie date ; à défaut, le titre + la description.
                material = fetch_page_text(r["url_source"]) or f"{r['title']}\n{r['description'] or ''}"
                s, e, src = llm_dates(material, ref, client, DATES_LLM_MODEL)
                conn.execute(
                    "UPDATE events_raw SET date_event_start=?, date_event_end=?, date_source=? WHERE id=?",
                    (s, e, src, r["id"]))
                conn.commit()
                if src == "llm":
                    from_llm += 1
            log.info("Passe LLM : %d daté(s) par le LLM", from_llm)
    elif DATES_LLM and not args.no_llm and not api_key:
        log.info("Passe LLM ignorée : ANTHROPIC_API_KEY absente.")

    total_dated = conn.execute(
        "SELECT COUNT(*) n FROM events_raw WHERE date_source IN ('parsed','page','llm') "
        "AND statut != 'merged'").fetchone()["n"]
    undated = conn.execute(
        "SELECT COUNT(*) n FROM events_raw WHERE COALESCE(date_event_start,'')='' "
        "AND COALESCE(date_event_end,'')='' AND statut != 'merged'").fetchone()["n"]
    conn.close()
    log.info("=== Datation : +%d texte +%d page +%d LLM ce run · %d datés au total, %d sans date ===",
             parsed, from_page, from_llm, total_dated, undated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
