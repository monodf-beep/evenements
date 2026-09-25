#!/usr/bin/env python3
"""Canal « dossiers de presse » — matière de première classe pour la rédaction.

En tant que média, Cultura Sabauda peut obtenir des ORGANISATEURS, gratuitement et
sans risque juridique, ce qu'aucun scraping ne donne : le dossier de presse complet
(PDF), des photos haute-déf avec droits d'usage, l'info avant le public. C'est la
meilleure matière possible (voir CHARTE §5, §8).

Fonctionnement (jumeau du canal newsletter) :
  1. Franck applique le label Gmail « Presse » aux mails d'accréditation / dossiers ;
  2. ce script lit ces mails (OAuth2 read-only, réutilise le canal Gmail) ;
  3. il extrait le TEXTE du corps + celui des PIÈCES JOINTES PDF (pypdf) et enregistre
     les photos jointes sur disque (data/press_kits/<id>/) ;
  4. il stocke le tout dans la table press_kits et tente de RATTACHER le dossier à un
     événement déjà en base (same_story sur le sujet ↔ titre, même territoire).

L'agent d'enrichissement (scripts/enrich.py) puise ensuite dans ces dossiers comme
matière PRIORITAIRE (source primaire, pas de la presse concurrente).

LLM ? NON pour ce script : collecte + extraction + rattachement = déterministe. Le LLM
n'intervient qu'à l'enrichissement/rédaction. Voir docs/LLM_OU_CODE.md.
Déclenché à la main (bouton) ; peut passer en cron plus tard.
Setup OAuth : identique au canal newsletter (scripts/gmail_collect.py --setup).
"""
from __future__ import annotations
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import re

from utils.logger import get_logger
from utils.sources import _STORY_PLACES, _STORY_STOP, _strip_accents
from scripts.scraper_events import init_db
# Réutilise toute la plomberie Gmail du canal newsletter (une seule source de vérité).
from scripts.gmail_collect import (
    build_service, parse_message, _walk, load_whitelist, match_territory,
)

log = get_logger("press_kits")

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
PRESS_DIR = ROOT / "data" / "press_kits"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")


def ensure_press_table(conn: sqlite3.Connection) -> None:
    """Crée la table des dossiers de presse (idempotent). Appelée aussi par enrich.py."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS press_kits (
        message_id      TEXT PRIMARY KEY,
        sender          TEXT,
        subject         TEXT,
        received_at     TEXT,
        territoire      TEXT,
        body_text       TEXT,
        pdf_text        TEXT,
        n_photos        INTEGER DEFAULT 0,
        photos_dir      TEXT,
        matched_event_id INTEGER,
        collected_at    TEXT DEFAULT (datetime('now'))
    )
    """)
    conn.commit()


def _extract_pdf_text(data: bytes) -> str:
    """Texte d'un PDF (pypdf). Dégrade proprement si la lib manque ou le PDF est illisible."""
    try:
        import io
        from pypdf import PdfReader
    except ImportError:
        log.warning("pypdf non installé → texte PDF ignoré (pip install pypdf)")
        return ""
    try:
        reader = PdfReader(io.BytesIO(data))
        parts = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(parts).strip()
    except Exception as exc:
        log.warning("PDF illisible : %s", exc)
        return ""


def _fetch_attachment(service, message_id: str, att_id: str) -> bytes:
    import base64
    att = service.users().messages().attachments().get(
        userId="me", messageId=message_id, id=att_id).execute()
    return base64.urlsafe_b64decode(att.get("data", "").encode("utf-8"))


def process_attachments(service, msg: dict) -> tuple[str, int, str]:
    """Extrait le texte des PDF et enregistre les photos. Retourne (pdf_text, n_photos, dir)."""
    message_id = msg.get("id", "")
    pdf_texts: list[str] = []
    photos = 0
    photos_dir = ""
    for part in _walk(msg.get("payload", {})):
        filename = (part.get("filename") or "").strip()
        if not filename:
            continue
        att_id = (part.get("body", {}) or {}).get("attachmentId")
        if not att_id:
            continue
        low = filename.lower()
        mime = part.get("mimeType", "")
        try:
            if low.endswith(".pdf") or mime == "application/pdf":
                data = _fetch_attachment(service, message_id, att_id)
                txt = _extract_pdf_text(data)
                if txt:
                    pdf_texts.append(f"[{filename}]\n{txt}")
            elif low.endswith(IMAGE_EXTS) or mime.startswith("image/"):
                data = _fetch_attachment(service, message_id, att_id)
                dst = PRESS_DIR / message_id
                dst.mkdir(parents=True, exist_ok=True)
                (dst / filename).write_bytes(data)
                photos += 1
                photos_dir = str(dst)
        except Exception as exc:
            log.warning("Pièce jointe '%s' ignorée : %s", filename, exc)
    return "\n\n".join(pdf_texts)[:20000], photos, photos_dir


def _sig_words(s: str) -> set:
    """Mots significatifs (≥3 lettres, hors lieux/stopwords), accents neutralisés.
    Réutilise les listes synchronisées de utils/sources.py (pas de divergence)."""
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'-]{2,}", s or "")
    return {_strip_accents(w).lower() for w in words} - _STORY_PLACES - _STORY_STOP


def kit_matches(subject: str, title: str) -> bool:
    """Le sujet d'un dossier et un titre d'événement désignent-ils le même événement ?

    Seuil adapté au cas dossier↔événement (≥ 2 mots significatifs communs, hors noms de
    lieux) : le sujet d'un dossier nomme souvent l'événement en 2-3 mots (« Exposition
    Matisse »). Plus souple que same_story (calibré, lui, pour la dédup de titres presse).
    """
    a, b = _sig_words(subject), _sig_words(title)
    return len(a & b) >= 2 if a and b else False


def match_event(conn: sqlite3.Connection, subject: str, territoire: str) -> int | None:
    """Rattache un dossier à un événement existant (kit_matches sujet ↔ titre)."""
    if not subject.strip():
        return None
    where = "WHERE statut != 'merged'"
    params: list = []
    if territoire:
        where += " AND territoire = ?"
        params.append(territoire)
    for row in conn.execute(
        f"SELECT id, title FROM events_raw {where} ORDER BY id DESC LIMIT 500", params):
        if kit_matches(subject, row["title"] or ""):
            return row["id"]
    return None


def rematch_unmatched(conn: sqlite3.Connection) -> int:
    """Retente le rattachement des dossiers encore orphelins (l'événement a pu être
    scrapé APRÈS l'arrivée du dossier). Le rattachement vit à un seul endroit : ici."""
    fixed = 0
    for r in conn.execute(
        "SELECT message_id, subject, territoire FROM press_kits "
        "WHERE matched_event_id IS NULL").fetchall():
        eid = match_event(conn, r["subject"] or "", r["territoire"] or "")
        if eid:
            conn.execute("UPDATE press_kits SET matched_event_id=? WHERE message_id=?",
                         (eid, r["message_id"]))
            fixed += 1
    if fixed:
        conn.commit()
    return fixed


def already_seen(conn: sqlite3.Connection, message_id: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM press_kits WHERE message_id = ?", (message_id,)).fetchone() is not None


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    label = os.getenv("GMAIL_PRESSE_LABEL", "Presse")
    lookback = int(os.getenv("GMAIL_PRESSE_LOOKBACK_DAYS", os.getenv("GMAIL_LOOKBACK_DAYS", "30")))

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    ensure_press_table(conn)

    whitelist = load_whitelist()
    manual = bool(argv and "--manual" in argv)
    service = build_service(manual=manual)

    query = f"label:{label} newer_than:{lookback}d"
    ids: list[str] = []
    req = service.users().messages().list(userId="me", q=query, maxResults=100)
    while req is not None:
        resp = req.execute()
        ids.extend(m["id"] for m in resp.get("messages", []))
        req = service.users().messages().list_next(req, resp)
    log.info("%d mail(s) sous le label '%s'", len(ids), label)

    collected = 0
    for mid in ids:
        if already_seen(conn, mid):
            continue
        raw = service.users().messages().get(userId="me", id=mid, format="full").execute()
        email = parse_message(raw)
        pdf_text, n_photos, photos_dir = process_attachments(service, raw)
        territoire = match_territory(email.get("sender", ""), whitelist)
        matched = match_event(conn, email.get("subject", ""), territoire)
        conn.execute("""
        INSERT OR IGNORE INTO press_kits
            (message_id, sender, subject, received_at, territoire,
             body_text, pdf_text, n_photos, photos_dir, matched_event_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mid, email.get("sender", "")[:200], email.get("subject", "")[:300],
            email.get("date", ""), territoire,
            (email.get("body", "") or "")[:20000], pdf_text, n_photos, photos_dir, matched,
        ))
        conn.commit()
        collected += 1
        log.info("[%s] dossier : %d photo(s), %d car. PDF, event=%s | %s",
                 mid[:8], n_photos, len(pdf_text),
                 matched if matched else "non rattaché", email.get("subject", "")[:60])

    # Rattache les dossiers orphelins dont l'événement est apparu depuis.
    refixed = rematch_unmatched(conn)
    conn.close()
    log.info("=== Dossiers de presse : %d nouveau(x), %d rattaché(s) a posteriori ===",
             collected, refixed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
