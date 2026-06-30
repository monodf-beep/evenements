#!/usr/bin/env python3
"""Collecte quotidienne des événements depuis les sources RSS.

Cron : 0 8 * * * (quotidien 8h)
"""
from __future__ import annotations
import sqlite3
import os
import re
import sys
from pathlib import Path
import feedparser
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.sources import is_blocked_image, load_blocked_image_domains

log = get_logger("scraper_events")

SOURCES_FILE = ROOT / "config" / "sources.txt"
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS events_raw (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        title            TEXT NOT NULL,
        description      TEXT,
        date_start       TEXT,
        lieu             TEXT,
        ville            TEXT,
        territoire       TEXT,
        url_source       TEXT NOT NULL UNIQUE,
        url_image        TEXT,
        organisateur     TEXT,
        source_name      TEXT,
        scrape_date      TEXT DEFAULT (datetime('now')),
        llm_score        INTEGER,
        llm_categorie    TEXT,
        llm_justification TEXT,
        llm_evaluated_at TEXT,
        llm_model        TEXT,
        statut           TEXT DEFAULT 'pending',
        published_cs_date TEXT,
        wp_post_id_cs    INTEGER,
        source_type      TEXT DEFAULT 'institutionnel'
    )
    """)
    # Migrations : colonnes ajoutées après coup sur une base déjà existante.
    for col, decl in (("source_type", "TEXT DEFAULT 'institutionnel'"),):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass  # colonne déjà présente
    conn.commit()


def load_sources() -> list[dict]:
    if not SOURCES_FILE.exists():
        log.warning("Fichier sources absent : %s", SOURCES_FILE)
        return []
    sources = []
    for line in SOURCES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ";" not in line:
            continue
        parts = line.split(";", 3)
        if len(parts) >= 2:
            sources.append({
                "url": parts[0].strip(),
                "territoire": parts[1].strip(),
                "name": parts[2].strip() if len(parts) > 2 else parts[0].strip(),
                # type : institutionnel (défaut) | radar (presse/Google News, détection seule)
                "type": (parts[3].strip().lower() if len(parts) > 3 and parts[3].strip()
                         else "institutionnel"),
            })
    return sources


def extract_image(entry: dict) -> str:
    """Cherche une image dans les champs RSS standards."""
    # media:content
    if hasattr(entry, "media_content") and entry.media_content:
        url = entry.media_content[0].get("url", "")
        if url:
            return url
    # enclosures
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image"):
            return enc.get("href", "")
    # media:thumbnail
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    # fallback : première <img> trouvée dans le résumé / contenu HTML
    blob = entry.get("summary", "") or ""
    for c in getattr(entry, "content", []) or []:
        blob += c.get("value", "")
    match = re.search(r'<img[^>]+src=["\']?(https?://[^"\'>\s]+)', blob, re.I)
    if match:
        return match.group(1)
    return ""


def best_content(entry: dict) -> str:
    """Texte le plus complet disponible : content:encoded prioritaire sur le résumé."""
    parts = []
    for c in getattr(entry, "content", []) or []:
        v = c.get("value", "")
        if v:
            parts.append(v)
    full = max(parts, key=len) if parts else ""
    summary = entry.get("summary", "") or ""
    text = full if len(full) >= len(summary) else summary
    return text.strip()[:10000]


def scrape_source(source: dict, conn: sqlite3.Connection, blocked: set) -> int:
    log.info("Scraping : %s", source["name"])
    try:
        feed = feedparser.parse(source["url"])
    except Exception as exc:
        log.warning("Échec scraping %s : %s", source["name"], exc)
        return 0
    inserted = 0
    for entry in feed.entries:
        url = entry.get("link", "").strip()
        if not url:
            continue
        # Déduplication stricte par url_source
        exists = conn.execute(
            "SELECT id FROM events_raw WHERE url_source = ?", (url,)
        ).fetchone()
        if exists:
            continue
        image = extract_image(entry)
        if is_blocked_image(image, blocked):
            image = ""
        try:
            conn.execute("""
            INSERT INTO events_raw
                (title, description, date_start, territoire, url_source,
                 url_image, source_name, organisateur, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.get("title", "").strip(),
                best_content(entry),
                entry.get("published", ""),
                source["territoire"],
                url,
                image,
                source["name"],
                (entry.get("author", "") or "").strip()[:200],
                source.get("type", "institutionnel"),
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # doublon race condition
    conn.commit()
    log.info("%s : %d nouveaux événements", source["name"], inserted)
    return inserted


def main() -> int:
    load_dotenv(ROOT / ".env")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    blocked = load_blocked_image_domains()
    sources = load_sources()
    if not sources:
        log.error("Aucune source configurée dans %s", SOURCES_FILE)
        return 1
    total = sum(scrape_source(s, conn, blocked) for s in sources)
    conn.close()
    log.info("=== Scraping terminé : %d nouveaux événements ===", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
