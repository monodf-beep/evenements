#!/usr/bin/env python3
"""Extraction du LIEU (nom + ville) d'un événement, pour remplir `lieu` / `ville`.

Le scraper ne remplit PAS ces colonnes : l'adresse ne vit souvent que dans la prose
de l'article. Or l'agenda a besoin d'un lieu structuré (Venue TEC : carte, ville,
schema.org location). On l'extrait comme les dates (voir dates.py), du plus sûr au
dernier recours :
  1. PAGE structurée — JSON-LD schema.org « location » (name + addressLocality),
     le standard des sites d'événements (déterministe, gratuit) ;
  2. LLM — jugement de langue (FR/IT) sur la prose de la page, quand le JSON-LD manque.
     Économique, borné, idempotent ; désactivable par VENUES_LLM=0.

Sortie stockée : lieu / ville + venue_source
('page' | 'llm' | 'novenue' | 'none' | 'llm_none'). Cron : après la datation.
"""
from __future__ import annotations
import argparse
import html as htmlmod
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.scraper_events import init_db
from scripts.dates import fetch_page_text, _UA, FETCH_TIMEOUT
from dotenv import load_dotenv

log = get_logger("venues")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
FETCH_CAP = int(os.getenv("VENUES_FETCH_CAP", "200"))
VENUES_LLM = os.getenv("VENUES_LLM", "1") not in ("0", "false", "False", "")
VENUES_LLM_CAP = int(os.getenv("VENUES_LLM_CAP", "150"))
VENUES_LLM_MODEL = os.getenv("VENUES_LLM_MODEL") or os.getenv("ANTHROPIC_MODEL_EXTRACT",
                                                             "claude-haiku-4-5-20251001")


def _clean(s: str) -> str:
    """Déséchappe un fragment de chaîne JSON/HTML et normalise les espaces."""
    s = (s or "").strip()
    if not s:
        return ""
    try:                     # gère les é, \/ … d'un littéral JSON
        s = json.loads(f'"{s}"')
    except (ValueError, TypeError):
        pass
    s = htmlmod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()[:160]


def venue_from_page(html: str) -> tuple[str, str, str]:
    """(lieu, ville, source) depuis le JSON-LD schema.org « location ». ('','','') si rien.

    Gère « location » en OBJET (Place : name + address.addressLocality) et en CHAÎNE.
    Ne devine JAMAIS depuis le texte libre (trop de faux positifs) — c'est le rôle du LLM.
    """
    idx = html.find('"location"')
    if idx != -1:
        window = html[idx:idx + 900]
        # location : { "name": "...", "address": { "addressLocality": "..." } }
        name = re.search(r'"name"\s*:\s*"([^"]{2,120})"', window)
        city = re.search(r'"addressLocality"\s*:\s*"([^"]{2,80})"', window)
        lieu = _clean(name.group(1)) if name else ""
        ville = _clean(city.group(1)) if city else ""
        if lieu or ville:
            return (lieu, ville, "page")
        # location : "Nom du lieu" (chaîne simple)
        strv = re.search(r'"location"\s*:\s*"([^"]{2,120})"', html[idx:idx + 200])
        if strv:
            return (_clean(strv.group(1)), "", "page")
    return ("", "", "")


def fetch_event_venue(url: str) -> tuple[str, str, str]:
    """Télécharge la page et en extrait le lieu (JSON-LD). ('','','novenue') si rien."""
    if not url or url.startswith("gmail:") or "news.google.com" in url:
        return ("", "", "none")
    from scripts.dates import _robust_get
    r = _robust_get(url)
    if r is None:
        return ("", "", "novenue")
    lieu, ville, src = venue_from_page(r.text)
    return (lieu, ville, "page") if src == "page" else ("", "", "novenue")


def llm_venue(material: str, client, model: str) -> tuple[str, str, str]:
    """Le LLM lit la matière et rend (lieu, ville). ('','','llm_none') si rien.

    Dernier recours uniquement (le JSON-LD a échoué). Jugement de langue FR/IT.
    """
    material = (material or "").strip()
    if not material:
        return ("", "", "llm_none")
    prompt = (
        "Tu extrais le LIEU d'un événement culturel à partir du texte fourni "
        "(français ou italien). Donne le NOM du lieu précis (musée, théâtre, salle, "
        "château, place, église…) et la VILLE. Ignore les adresses d'organisateurs "
        "ou de billetterie : ce qui compte, c'est OÙ se déroule l'événement. Si le "
        "lieu n'est pas clairement identifiable, found=false.\n\n"
        f"TEXTE :\n{material[:4000]}\n\n"
        'Réponds en JSON STRICT et rien d\'autre : '
        '{"lieu": "…" ou "", "ville": "…" ou "", "found": true|false}'
    )
    try:
        msg = client.messages.create(
            model=model, max_tokens=150,
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:  # jamais bloquant
        log.warning("Extraction lieu LLM échouée : %s", exc)
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
    lieu, ville = _clean(data.get("lieu", "")), _clean(data.get("ville", ""))
    return (lieu, ville, "llm") if (lieu or ville) else ("", "", "llm_none")


def apply_source_venues(conn: sqlite3.Connection) -> int:
    """Passe 0 — LIEU DE LA SOURCE (déterministe, gratuit, le plus fiable).

    Pour une source « officielle » (un lieu précis : théâtre, musée, festival…),
    le lieu EST la source : un événement de flowersfestival.it se passe au Flowers
    Festival, à Collegno. On applique le lieu/ville par défaut de la source (champs
    optionnels de config/sources.txt) AVANT d'aller chercher par page/LLM/web.
    On ne pose venue_source='source' que si on a rempli un LIEU (sinon on laisse les
    passes suivantes trouver le lieu)."""
    from scripts.scraper_events import load_sources
    defaults = {s["name"]: (s.get("lieu", ""), s.get("ville", ""))
                for s in load_sources() if (s.get("lieu") or s.get("ville"))}
    filled = 0
    for name, (lieu, ville) in defaults.items():
        rows = conn.execute(
            "SELECT id, lieu, ville FROM events_raw WHERE source_name = ? "
            "AND statut != 'merged' AND (COALESCE(lieu,'')='' OR COALESCE(ville,'')='')",
            (name,)).fetchall()
        for r in rows:
            updates: dict = {}
            if lieu and not (r["lieu"] or "").strip():
                updates["lieu"] = lieu
                updates["venue_source"] = "source"
            if ville and not (r["ville"] or "").strip():
                updates["ville"] = ville
            if not updates:
                continue
            sets = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE events_raw SET {sets} WHERE id=?",
                         [*updates.values(), r["id"]])
            filled += 1
        conn.commit()
    return filled


def ensure_columns(conn: sqlite3.Connection) -> None:
    for col, decl in (("lieu", "TEXT"), ("ville", "TEXT"), ("venue_source", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extraction du lieu des événements (page + LLM).")
    parser.add_argument("--fetch-cap", type=int, default=FETCH_CAP,
                        help="Nombre max de pages à télécharger sur ce run.")
    parser.add_argument("--no-llm", action="store_true",
                        help="Ne pas utiliser l'extraction LLM de dernier recours.")
    parser.add_argument("--llm-cap", type=int, default=VENUES_LLM_CAP,
                        help="Nombre max d'événements traités par LLM sur ce run.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    ensure_columns(conn)

    # --- Passe 0 : LIEU DE LA SOURCE (le lieu = la source pour les « officielle ») ---
    from_source = apply_source_venues(conn)
    log.info("Passe source : %d lieu/ville posé(s) depuis la source", from_source)

    # --- Passe 1 : page structurée (JSON-LD location), déterministe ---
    todo = conn.execute(
        "SELECT id, url_source FROM events_raw "
        "WHERE COALESCE(lieu,'') = '' AND (venue_source IS NULL OR venue_source = '') "
        "  AND statut != 'merged' "
        "  AND url_source NOT LIKE 'gmail:%' AND url_source NOT LIKE '%news.google.com%' "
        "LIMIT ?", (args.fetch_cap,)).fetchall()
    log.info("Passe page : %d page(s) à lire (cap %d)", len(todo), args.fetch_cap)
    from_page = 0
    for r in todo:
        lieu, ville, src = fetch_event_venue(r["url_source"])
        conn.execute(
            "UPDATE events_raw SET lieu=?, ville=?, venue_source=? WHERE id=?",
            (lieu, ville, src, r["id"]))
        conn.commit()
        if src == "page":
            from_page += 1
    log.info("Passe page : %d lieu(x) via la page", from_page)

    # --- Passe 2 : LLM (dernier recours) sur les restants ---
    from_llm = 0
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if VENUES_LLM and not args.no_llm and api_key:
        todo = conn.execute(
            "SELECT id, title, description, url_source FROM events_raw "
            "WHERE COALESCE(lieu,'') = '' AND venue_source IN ('novenue', 'none') "
            "  AND statut != 'merged' "
            "  AND url_source NOT LIKE 'gmail:%' AND url_source NOT LIKE '%news.google.com%' "
            "LIMIT ?", (args.llm_cap,)).fetchall()
        log.info("Passe LLM : %d événement(s) à situer (modèle %s, cap %d)",
                 len(todo), VENUES_LLM_MODEL, args.llm_cap)
        if todo:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
            for r in todo:
                material = fetch_page_text(r["url_source"], title=r["title"] or "") or f"{r['title']}\n{r['description'] or ''}"
                lieu, ville, src = llm_venue(material, client, VENUES_LLM_MODEL)
                conn.execute(
                    "UPDATE events_raw SET lieu=?, ville=?, venue_source=? WHERE id=?",
                    (lieu, ville, src, r["id"]))
                conn.commit()
                if src == "llm":
                    from_llm += 1
            log.info("Passe LLM : %d lieu(x) via le LLM", from_llm)
    elif VENUES_LLM and not args.no_llm and not api_key:
        log.info("Passe LLM ignorée : ANTHROPIC_API_KEY absente.")

    located = conn.execute(
        "SELECT COUNT(*) n FROM events_raw WHERE COALESCE(lieu,'') <> '' "
        "AND statut != 'merged'").fetchone()["n"]
    conn.close()
    log.info("=== Lieux : +%d page +%d LLM ce run · %d situés au total ===",
             from_page, from_llm, located)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
