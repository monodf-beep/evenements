#!/usr/bin/env python3
"""Recherche d'IMAGE par AGENT WEB + VÉRIFICATEUR (vision) — dernier étage visuel.

Quand la chaîne déterministe (flux RSS → og:image → Wikimedia Commons) n'a rien
donné de mieux qu'une bannière générique, on lance un agent Claude AVEC RECHERCHE
WEB pour trouver une PHOTO pertinente du sujet, puis un SECOND agent (vision)
VÉRIFIE que l'image correspond bien à l'événement avant de l'accepter. Deux garde-
fous, comme demandé par Franck : « un agent revérifie après pour dire oui ou non
que ça correspond au sujet ».

Posture de droits (charte §8) : on vise une image LICENCIABLE / institutionnelle —
la photo de partage (og:image) de la page OFFICIELLE de l'événement, du lieu ou de
l'artiste, ou un fichier Wikimedia Commons. On évite les photos d'agence/presse.

Réservé au haut du panier (coût : recherche web + vision) : retenu, daté, à venir,
score >= seuil, et pas encore de VRAIE image (bannière = à améliorer).

Exemples :
  .venv/bin/python3 -m scripts.images_web --dry-run
  .venv/bin/python3 -m scripts.images_web --cap 15 --min-score 7
"""
from __future__ import annotations
import argparse
import base64
import io
import json
import os
import re
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import images
from utils.images import fetch_og_image
from utils.sources import (is_blocked_image, is_logo_image,
                           load_blocked_image_domains)
from scripts.venues import _clean
from scripts.scraper_events import web_cooldown_sql, mark_web_attempt

log = get_logger("images_web")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
SEARCH_MODEL = (os.getenv("ANTHROPIC_MODEL_SEARCH") or os.getenv("ANTHROPIC_MODEL")
                or "claude-sonnet-5")
# Vérificateur vision : tâche de jugement simple → modèle économique par défaut.
VERIFY_MODEL = (os.getenv("ANTHROPIC_MODEL_VISION") or os.getenv("ANTHROPIC_MODEL_EXTRACT")
                or "claude-haiku-4-5")

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
_OK_MIME = ("image/jpeg", "image/png", "image/webp", "image/gif")
_MAX_BYTES = 5 * 1024 * 1024  # 5 Mo : on ne télécharge pas des images géantes.


def _dates(ev: dict) -> str:
    s = (ev.get("date_event_start") or "").strip()
    e = (ev.get("date_event_end") or "").strip()
    if s and e and e != s:
        return f"du {s} au {e}"
    return s or "date à confirmer"


def search_image(ev: dict, client) -> dict:
    """Agent web : propose une image (URL directe et/ou page à scraper) + un sujet
    ATTENDU pour la vérification. {} si rien de fiable."""
    prompt = (
        "Tu cherches une PHOTO pour illustrer un événement culturel, PERTINENTE et "
        "réutilisable. Ordre de préférence : (1) fichier Wikimedia Commons ; (2) "
        "image de partage de la PAGE OFFICIELLE de l'événement, du lieu ou de "
        "l'artiste. ÉVITE les photos d'agence de presse / sous copyright strict.\n"
        "Utilise la recherche web. Réponds UNIQUEMENT quand tu es sûr.\n\n"
        f"Événement : {_clean(ev.get('article_title') or ev.get('title'))}\n"
        f"Lieu : {_clean(ev.get('lieu'))} · Ville : {_clean(ev.get('ville'))}\n"
        f"Dates : {_dates(ev)}\n"
        f"Catégorie : {ev.get('llm_categorie') or ''} · Territoire : {ev.get('territoire') or ''}\n"
        f"Description : {_clean(ev.get('description'))[:400]}\n\n"
        "Réponds en JSON STRICT et rien d'autre :\n"
        '{"image_url": "URL directe .jpg/.png ou vide", '
        '"page_url": "page officielle à défaut ou vide", '
        '"credit": "auteur / source ou vide", '
        '"subject": "ce que la photo DEVRAIT montrer (2-8 mots)", '
        '"found": true|false}'
    )
    try:
        msg = client.messages.create(
            model=SEARCH_MODEL, max_tokens=500,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:  # jamais bloquant
        log.warning("Recherche image échouée : %s", exc)
        return {}
    try:
        from utils import usage
        usage.record_message(SEARCH_MODEL, msg, label="image_web_search")
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


def _download(url: str) -> tuple[bytes, str]:
    """Télécharge une image (bornée). Renvoie (octets, mime) ou (b'', '')."""
    if not url or not url.startswith("http"):
        return b"", ""
    try:
        r = requests.get(url, headers=_UA, timeout=15, stream=True)
        if r.status_code != 200:
            return b"", ""
        mime = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if mime not in _OK_MIME:
            return b"", ""
        buf = b""
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > _MAX_BYTES:
                return b"", ""
        return buf, mime
    except requests.RequestException:
        return b"", ""


def verify_image(ev: dict, subject: str, img_bytes: bytes, mime: str, client) -> tuple[bool, float, float]:
    """Vérificateur VISION : l'image correspond-elle vraiment au sujet ? Et quel point
    focal (x,y) préserve un visage / du texte informatif si l'image est recadrée ?

    Délègue à utils.image_verify.verify_relevance (agent partagé avec la chaîne
    principale). NB : verify_relevance renvoie ok=True en cas de panne technique (ne
    bloque pas), mais ici — agent web de dernier recours — on exige un OK franc :
    une image non lisible n'est pas acceptable, on refuse par défaut."""
    if not img_bytes or mime not in _OK_MIME:
        return False, 0.5, 0.5
    from utils import image_verify
    return image_verify.verify_relevance(img_bytes, mime, ev, client, VERIFY_MODEL, subject)


def find_verified_image(ev: dict, client, blocked: set[str]) -> tuple[str, str, float, float]:
    """Cherche puis VÉRIFIE une image. Renvoie (url, credit, focal_x, focal_y) ou ('', '', 0.5, 0.5)."""
    proposal = search_image(ev, client)
    if not proposal:
        return "", "", 0.5, 0.5
    # Candidat : URL directe si donnée, sinon og:image de la page officielle.
    candidate = (proposal.get("image_url") or "").strip()
    if not candidate and proposal.get("page_url"):
        candidate = fetch_og_image(proposal["page_url"].strip())
    if not candidate or not candidate.startswith("http"):
        return "", "", 0.5, 0.5
    if is_blocked_image(candidate, blocked) or is_logo_image(candidate):
        return "", "", 0.5, 0.5
    img_bytes, mime = _download(candidate)
    if not img_bytes:
        return "", "", 0.5, 0.5
    try:
        from PIL import Image
        with Image.open(io.BytesIO(img_bytes)) as im:
            w, h = im.size
    except Exception:
        w, h = 0, 0
    if min(w, h) < images.MIN_DIM:  # trop petite : floue une fois étirée aux formats sociaux
        log.info("Image écartée (résolution %dx%d < %dpx) : %s", w, h, images.MIN_DIM, candidate[:70])
        return "", "", 0.5, 0.5
    ok, fx, fy = verify_image(ev, proposal.get("subject", ""), img_bytes, mime, client)
    if not ok:
        return "", "", 0.5, 0.5
    return candidate, _clean(proposal.get("credit", "")), fx, fy


def _select(conn, args, today: str):
    where = [
        "statut IN ('evaluated','published_cs','published_sub')",
        "duplicate_of IS NULL",
        "COALESCE(date_event_start,'') <> ''",
        "COALESCE(llm_score,0) >= ?",
        # Pas de VRAIE image : soit rien, soit seulement la bannière de repli.
        "(COALESCE(url_image,'') = '' OR COALESCE(image_source,'') = 'banner')",
    ]
    params: list = [args.min_score]
    if not args.include_past:
        where.append("COALESCE(date_event_end, date_event_start) >= ?")
        params.append(today)
    if not args.force:                     # cooldown : on saute ce qu'on a tenté récemment
        where.append(web_cooldown_sql("image_web_at"))
    sql = (f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
           f"ORDER BY COALESCE(llm_score,0) DESC, date_event_start ASC LIMIT ?")
    params.append(args.cap)
    return conn.execute(sql, params).fetchall()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Recherche d'image par agent web + vérificateur vision.")
    parser.add_argument("--cap", type=int, default=15, help="Nombre max par run.")
    parser.add_argument("--min-score", type=int, default=7, help="Score minimum (défaut 7).")
    parser.add_argument("--delay", type=float, default=1.0, help="Pause (s) entre deux événements.")
    parser.add_argument("--include-past", action="store_true", help="Inclure les événements passés.")
    parser.add_argument("--force", action="store_true", help="Ignorer le cooldown (re-tenter tout de suite).")
    parser.add_argument("--dry-run", action="store_true", help="Lister sans appeler les agents.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = _select(conn, args, today)
    log.info("Sélection : %d événement(s) sans vraie image (cap %d, min-score %d)",
             len(rows), args.cap, args.min_score)

    if args.dry_run:
        for r in rows:
            src = r["image_source"] if "image_source" in r.keys() else ""
            print(f"  [{r['id']}] score={r['llm_score']} · {(r['title'] or '')[:60]:60} "
                  f"· image={src or 'aucune'}")
        print(f"\n{len(rows)} événement(s) SERAIENT traités (dry-run — aucun appel).")
        conn.close()
        return 0

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY absente — recherche image impossible.")
        conn.close()
        return 1

    import anthropic
    client = anthropic.Anthropic(api_key=api_key, timeout=90.0)
    blocked = load_blocked_image_domains()
    ok = 0
    for i, r in enumerate(rows, 1):
        url, credit, fx, fy = find_verified_image(dict(r), client, blocked)
        mark_web_attempt(conn, "image_web_at", r["id"])   # tentative armée (réussie ou non)
        if url:
            # card_focal_x/y : seulement si jamais réglé (NULL) — ne JAMAIS écraser un
            # cadrage choisi à la main au back-office (éditeur de point focal).
            conn.execute(
                "UPDATE events_raw SET url_image=?, image_credit=?, image_source='web', "
                "card_focal_x=COALESCE(card_focal_x, ?), card_focal_y=COALESCE(card_focal_y, ?) "
                "WHERE id=?",
                (url, credit, fx, fy, r["id"]))
            conn.commit()
            ok += 1
            log.info("Image vérifiée id=%s : %s", r["id"], url[:70])
        if args.delay and i < len(rows):
            time.sleep(args.delay)

    conn.close()
    log.info("=== Images (web + vérif) : %d posée(s) sur %d ===", ok, len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
