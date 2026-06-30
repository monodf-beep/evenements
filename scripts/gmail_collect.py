#!/usr/bin/env python3
"""Collecte des événements depuis les newsletters culturelles reçues sur Gmail.

Canal complémentaire au RSS : beaucoup d'institutions (offices de tourisme,
théâtres, musées) ne publient leur programmation QUE par newsletter.

Principe :
  1. Franck s'abonne aux newsletters et leur applique le label Gmail « Agenda »
     (via Claude-in-Chrome) ;
  2. ce script lit les mails portant ce label (OAuth2 read-only) ;
  3. un appel LLM extrait les ÉVÉNEMENTS distincts de chaque mail (un mail = N events) ;
  4. chaque événement est inséré dans events_raw (statut='pending'), comme pour le RSS.

Déduplication :
  - par message-id (table gmail_seen) → on ne re-facture jamais le LLM sur un mail
    déjà traité ;
  - par url_source (UNIQUE) → pas de doublon au niveau événement.

Modèle d'extraction : ANTHROPIC_MODEL_EXTRACT (défaut = ANTHROPIC_MODEL).
Setup OAuth (une fois, sur le VPS sans navigateur) : python scripts/gmail_collect.py --setup
Cron : 0 8 * * * (même créneau que le scraping RSS).
"""
from __future__ import annotations
import argparse
import base64
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import usage
from utils.google_auth import load_credentials
from scripts.scraper_events import init_db

log = get_logger("gmail_collect")

CONFIG_DIR = ROOT / "config"
WHITELIST_FILE = CONFIG_DIR / "whitelist_gmail.txt"
CREDENTIALS_PATH = Path(os.getenv("GMAIL_CREDENTIALS", CONFIG_DIR / "credentials.json"))
TOKEN_PATH = Path(os.getenv("GMAIL_TOKEN", CONFIG_DIR / "token.json"))
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
DEFAULT_MODEL = "claude-sonnet-5"

# Sentinel : panne d'appel API pendant l'extraction → on arrête sans marquer le
# mail comme traité (il sera repris au prochain run). Même logique que l'évaluateur.
API_ERROR = object()

EXTRACT_PROMPT = """Tu extrais les ÉVÉNEMENTS CULTURELS concrets (expositions, conférences,
spectacles, concerts, festivals, ateliers, visites, rencontres) d'une newsletter.

Un mail peut contenir plusieurs événements, ou aucun (édito, actu générale).
Pour CHAQUE événement réellement daté/identifiable, renvoie un objet :
- "titre" : le nom de l'événement
- "date_start" : la date (texte tel quel, ou ISO AAAA-MM-JJ si clair) — "" si absente
- "lieu" : salle/lieu précis si mentionné, sinon ""
- "ville" : ville si mentionnée, sinon ""
- "description" : 1 à 2 phrases factuelles en français (résumé réécrit, pas du copier-coller)
- "url" : le lien vers la page de l'événement si présent dans le mail, sinon ""

Réponds UNIQUEMENT par un tableau JSON valide, sans texte avant/après. Si aucun
événement concret : [].

Expéditeur : {sender}
Objet : {subject}
Contenu :
{body}"""


# --------------------------------------------------------------------------- #
# Whitelist territoire
# --------------------------------------------------------------------------- #
def load_whitelist() -> list[tuple[str, str]]:
    """Charge [(motif_expediteur, territoire), ...]."""
    if not WHITELIST_FILE.exists():
        log.warning("Whitelist Gmail absente : %s", WHITELIST_FILE)
        return []
    out: list[tuple[str, str]] = []
    for line in WHITELIST_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ";" not in line:
            continue
        motif, terr = (p.strip() for p in line.split(";", 1))
        if motif and terr:
            out.append((motif.lower(), terr))
    return out


def match_territory(sender: str, whitelist: list[tuple[str, str]]) -> str:
    """Devine le territoire depuis l'adresse d'expédition. '' si inconnu."""
    s = (sender or "").lower()
    for motif, terr in whitelist:
        if motif in s:
            return terr
    return ""


# --------------------------------------------------------------------------- #
# Gmail
# --------------------------------------------------------------------------- #
def build_service(manual: bool = False):
    """Construit le client Gmail API (OAuth2 read-only)."""
    from googleapiclient.discovery import build
    creds = load_credentials(SCOPES, TOKEN_PATH, CREDENTIALS_PATH, manual=manual)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def list_label_messages(service, label: str, lookback_days: int) -> list[str]:
    """Renvoie les ids des messages portant `label`, sur la fenêtre demandée."""
    query = f"label:{label} newer_than:{lookback_days}d"
    ids: list[str] = []
    req = service.users().messages().list(userId="me", q=query, maxResults=100)
    while req is not None:
        resp = req.execute()
        ids.extend(m["id"] for m in resp.get("messages", []))
        req = service.users().messages().list_next(req, resp)
    return ids


def _header(headers: list[dict], name: str) -> str:
    name = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name:
            return h.get("value", "")
    return ""


def _b64(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", "replace")
    except Exception:
        return ""


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;?", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _walk(payload: dict):
    """Itère récursivement sur toutes les parties MIME."""
    yield payload
    for part in payload.get("parts", []) or []:
        yield from _walk(part)


def parse_message(msg: dict) -> dict:
    """Extrait expéditeur, objet, date, corps texte et 1re image d'un message Gmail."""
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    text_plain, text_html, image = "", "", ""
    for part in _walk(payload):
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data", "")
        if mime == "text/plain" and data and not text_plain:
            text_plain = _b64(data)
        elif mime == "text/html" and data and not text_html:
            text_html = _b64(data)
        elif mime.startswith("image/") and not image:
            # image attachée — on garde l'URL si dispo (rare en newsletter), sinon ignore
            image = body.get("attachmentId", "") and ""
    body_text = text_plain or _strip_html(text_html)
    if not image:
        m = re.search(r'<img[^>]+src=["\']?(https?://[^"\'>\s]+)', text_html, re.I)
        if m:
            image = m.group(1)
    return {
        "message_id": msg.get("id", ""),
        "sender": _header(headers, "From"),
        "subject": _header(headers, "Subject"),
        "date": _header(headers, "Date"),
        "body": body_text[:6000],
        "image": image,
    }


# --------------------------------------------------------------------------- #
# Extraction LLM
# --------------------------------------------------------------------------- #
def extract_events(email: dict, client: anthropic.Anthropic, model: str):
    """Extrait la liste d'événements d'un mail. Renvoie list | [] | API_ERROR."""
    prompt = EXTRACT_PROMPT.format(
        sender=email.get("sender", ""),
        subject=email.get("subject", ""),
        body=email.get("body", ""),
    )
    try:
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        usage.record_message(model, message, label="extraction newsletter")
        raw = message.content[0].text.strip()
        match = re.search(r"\[.*\]", raw, re.S)
        if not match:
            return []
        data = json.loads(match.group())
        return data if isinstance(data, list) else []
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        usage.note_api_error(exc)
        log.error("Erreur API Anthropic (extraction) : %s", exc)
        return API_ERROR
    except (json.JSONDecodeError, IndexError, TypeError) as exc:
        log.warning("JSON d'extraction invalide pour '%s' : %s",
                    email.get("subject", "")[:50], exc)
        return []


# --------------------------------------------------------------------------- #
# Persistance
# --------------------------------------------------------------------------- #
def ensure_seen_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS gmail_seen (
        message_id  TEXT PRIMARY KEY,
        processed_at TEXT DEFAULT (datetime('now'))
    )
    """)
    conn.commit()


def already_seen(conn: sqlite3.Connection, message_id: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM gmail_seen WHERE message_id = ?", (message_id,)
    ).fetchone() is not None


def mark_seen(conn: sqlite3.Connection, message_id: str) -> None:
    conn.execute("INSERT OR IGNORE INTO gmail_seen (message_id) VALUES (?)", (message_id,))


def insert_events(conn: sqlite3.Connection, events: list, email: dict,
                  territoire: str) -> int:
    """Insère les événements extraits (statut='pending'). Dédup par url_source UNIQUE."""
    inserted = 0
    for idx, ev in enumerate(events):
        if not isinstance(ev, dict):
            continue
        title = (ev.get("titre") or ev.get("title") or "").strip()
        if not title:
            continue
        url = (ev.get("url") or "").strip()
        if not url.startswith("http"):
            url = f"gmail:{email.get('message_id','')}#{idx}"
        cur = conn.execute("""
        INSERT OR IGNORE INTO events_raw
            (title, description, date_start, lieu, ville, territoire,
             url_source, url_image, source_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            (ev.get("description") or "").strip()[:2000],
            (ev.get("date_start") or "").strip(),
            (ev.get("lieu") or "").strip(),
            (ev.get("ville") or "").strip(),
            territoire,
            url,
            email.get("image", ""),
            email.get("sender", "")[:200],
        ))
        if cur.rowcount:
            inserted += 1
    return inserted


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Collecte des newsletters Gmail.")
    parser.add_argument("--setup", action="store_true",
                        help="Autorise l'accès Gmail (génère token.json) puis quitte.")
    parser.add_argument("--manual", action="store_true",
                        help="Flux OAuth manuel (VPS sans navigateur).")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")

    if args.setup:
        build_service(manual=True)
        log.info("Autorisation Gmail effectuée (token enregistré).")
        return 0

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY non définie")
        return 1
    model = os.getenv("ANTHROPIC_MODEL_EXTRACT") or os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
    label = os.getenv("GMAIL_LABEL", "Agenda")
    lookback = int(os.getenv("GMAIL_LOOKBACK_DAYS", "7"))

    client = anthropic.Anthropic(api_key=api_key)
    whitelist = load_whitelist()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    ensure_seen_table(conn)

    service = build_service(manual=args.manual)
    ids = list_label_messages(service, label, lookback)
    log.info("%d mails sous le label '%s' (modèle extraction : %s)", len(ids), label, model)

    total = 0
    for mid in ids:
        if already_seen(conn, mid):
            continue
        raw = service.users().messages().get(userId="me", id=mid, format="full").execute()
        email = parse_message(raw)
        events = extract_events(email, client, model)
        if events is API_ERROR:
            log.warning("Arrêt : panne API pendant l'extraction (mails restants repris au prochain run).")
            break
        territoire = match_territory(email.get("sender", ""), whitelist)
        n = insert_events(conn, events, email, territoire)
        mark_seen(conn, mid)
        conn.commit()
        total += n
        log.info("[%s] %d événement(s) | %s | %s", mid[:8], n,
                 territoire or "??", email.get("subject", "")[:60])

    conn.close()
    log.info("=== Collecte Gmail terminée : %d nouveaux événements ===", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
