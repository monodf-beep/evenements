#!/usr/bin/env python3
"""Version PAYSAGE de l'affiche (multi-format) — pour le grand visuel 16:9 de la fiche.

Beaucoup d'événements ont une AFFICHE PORTRAIT : belle sur la carte 4:3 et les réseaux,
mais qui laisse de grosses bandes une fois recadrée au format 16:9 du grand visuel de
fiche. Ce script cherche, via l'agent web, une VERSION PAYSAGE du même sujet (photo
horizontale de l'artiste / du lieu / de l'événement, bandeau officiel), la VÉRIFIE
(vraiment paysage + pertinente, agent vision), la stocke dans url_image_wide et re-pousse
la fiche pour que le 16:9 la prenne (cf. scripts.publisher_as, scripts.scraper_events).

Posture de droits (charte §8) : on vise l'image OFFICIELLE / institutionnelle (page de
l'événement, du lieu, de l'artiste, Wikimedia Commons), jamais une photo d'agence/presse.

Réservé au haut du panier : publié, VRAIE affiche PORTRAIT, pas encore de paysage. Cooldown
intégré (image_wide_at, WEB_COOLDOWN_DAYS). DRY-RUN par défaut.

Exemples :
  .venv/bin/python3 -m scripts.images_wide --dry-run
  .venv/bin/python3 -m scripts.images_wide --cap 15 --apply
"""
from __future__ import annotations
import argparse
import io
import json
import os
import re
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import images
from utils.sources import is_blocked_image, is_logo_image, load_blocked_image_domains
from scripts.venues import _clean
from scripts.scraper_events import init_db, web_cooldown_sql, mark_web_attempt
from scripts.images_web import _download, verify_image, SEARCH_MODEL
from scripts.publisher_as import publish_to_as

log = get_logger("images_wide")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
# Un « paysage » utile pour le 16:9 : nettement plus large que haut (au moins ~6:5).
_WIDE_MIN_RATIO = 1.2


def search_wide(ev: dict, client) -> dict:
    """Agent web : propose une image PAYSAGE (URL directe) + un sujet attendu. {} si rien."""
    prompt = (
        "Tu cherches une image PAYSAGE (horizontale, proche du 16:9) pour le GRAND visuel "
        "d'un événement culturel : une PHOTO large du sujet (artiste sur scène, salle, lieu, "
        "œuvre) ou un bandeau officiel HORIZONTAL. SURTOUT PAS une affiche portrait.\n"
        "Ordre de préférence : page OFFICIELLE de l'événement / du lieu / de l'artiste, puis "
        "Wikimedia Commons. ÉVITE les photos d'agence de presse / sous copyright strict. "
        "Utilise la recherche web. Réponds UNIQUEMENT si tu es sûr et que l'image est bien "
        "horizontale.\n\n"
        f"Événement : {_clean(ev.get('article_title') or ev.get('title'))}\n"
        f"Lieu : {_clean(ev.get('lieu'))} · Ville : {_clean(ev.get('ville'))}\n"
        f"Catégorie : {ev.get('llm_categorie') or ''} · Territoire : {ev.get('territoire') or ''}\n"
        f"Description : {_clean(ev.get('description'))[:400]}\n\n"
        'Réponds en JSON STRICT : {"image_url": "URL directe .jpg/.png paysage ou vide", '
        '"credit": "auteur / source ou vide", "subject": "ce que la photo montre (2-8 mots)", '
        '"found": true|false}'
    )
    try:
        msg = client.messages.create(
            model=SEARCH_MODEL, max_tokens=500,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:  # jamais bloquant
        log.warning("Recherche paysage échouée : %s", exc)
        return {}
    try:
        from utils import usage
        usage.record_message(SEARCH_MODEL, msg, label="image_wide_search")
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


def find_wide(ev: dict, client, blocked: set[str]) -> "tuple[str, str, float, float]":
    """Cherche PUIS vérifie une image PAYSAGE. (url, credit, fx, fy) ou ('', '', .5, .5)."""
    prop = search_wide(ev, client)
    if not prop:
        return "", "", 0.5, 0.5
    cand = (prop.get("image_url") or "").strip()
    if not cand or not cand.startswith("http"):
        return "", "", 0.5, 0.5
    if is_blocked_image(cand, blocked) or is_logo_image(cand):
        return "", "", 0.5, 0.5
    img_bytes, mime = _download(cand)
    if not img_bytes:
        return "", "", 0.5, 0.5
    try:
        from PIL import Image
        with Image.open(io.BytesIO(img_bytes)) as im:
            w, h = im.size
    except Exception:
        w, h = 0, 0
    if min(w, h) < images.MIN_DIM:
        log.info("Paysage écarté (résolution %dx%d < %dpx) : %s", w, h, images.MIN_DIM, cand[:70])
        return "", "", 0.5, 0.5
    if not (h and w >= h * _WIDE_MIN_RATIO):  # pas assez horizontale → inutile pour le 16:9
        log.info("Écarté (pas paysage : %dx%d) : %s", w, h, cand[:70])
        return "", "", 0.5, 0.5
    ok, fx, fy = verify_image(ev, prop.get("subject", ""), img_bytes, mime, client)
    if not ok:
        return "", "", 0.5, 0.5
    return cand, _clean(prop.get("credit", "")), fx, fy


def _select(conn, args, today: str) -> list[dict]:
    where = [
        "COALESCE(wp_post_id_as,0) > 0",           # publié sur Agenda Sabauda
        "duplicate_of IS NULL",
        "COALESCE(image_source,'') IN ('og','page','web','commons')",  # une VRAIE affiche
        "COALESCE(url_image_wide,'') = ''",        # pas encore de version paysage
        "COALESCE(url_image,'') <> ''",
    ]
    params: list = []
    if args.ids:
        where.append(f"id IN ({','.join('?' * len(args.ids))})")
        params += list(args.ids)
    if not args.force:
        where.append(web_cooldown_sql("image_wide_at"))
    sql = (f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
           "ORDER BY COALESCE(user_score, llm_score, 0) DESC, id ASC LIMIT ?")
    params.append(args.cap)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Cherche une version PAYSAGE de l'affiche (multi-format, grand visuel 16:9).")
    parser.add_argument("ids", nargs="*", type=int, help="Ids précis (défaut : sélection auto).")
    parser.add_argument("--cap", type=int, default=15, help="Nombre max par run.")
    parser.add_argument("--apply", action="store_true", help="Agir (sinon DRY-RUN).")
    parser.add_argument("--dry-run", action="store_true",
                        help="(défaut) simule sans rien écrire — présent pour cohérence.")
    parser.add_argument("--force", action="store_true", help="Ignorer le cooldown.")
    parser.add_argument("--delay", type=float, default=1.0, help="Pause (s) entre événements.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY non définie")
        return 1
    client = anthropic.Anthropic(api_key=api_key)
    blocked = load_blocked_image_domains()
    today = date.today().isoformat()

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)  # garantit url_image_wide / image_wide_at même sur une base ancienne
    conn.row_factory = sqlite3.Row
    rows = _select(conn, args, today)
    log.info("%d fiche(s) avec affiche à examiner pour une version paysage (cap %d) — %s",
             len(rows), args.cap, "APPLIQUE" if args.apply else "DRY-RUN")

    found = pushed = skipped_shape = 0
    for i, r in enumerate(rows):
        ev = dict(r)
        title = (ev.get("title") or "")[:55]
        # On cherche un paysage dès que l'affiche actuelle n'est PAS déjà assez large pour
        # le 16:9 (ratio < 1.6) : un 4:3, un 3:2 ou un portrait y perd du contenu au
        # recadrage (le cas Jazz Art). Une vraie image paysage (≥ 16:10) remplit déjà bien
        # → inutile de chercher. Dims illisibles (0×0) → on tente quand même.
        w, h = images.remote_dims(ev.get("url_image") or "")
        if w and h and (w / h) >= 1.6:
            skipped_shape += 1
            if args.apply:
                mark_web_attempt(conn, "image_wide_at", ev["id"])  # cooldown : déjà paysage
            log.info("[%s] affiche déjà paysage (%dx%d) — pas de paysage dédié — %s",
                     ev["id"], w, h, title)
            if args.delay and i < len(rows) - 1:
                time.sleep(args.delay)
            continue

        url, credit, fx, fy = find_wide(ev, client, blocked)
        if args.apply:
            mark_web_attempt(conn, "image_wide_at", ev["id"])  # cooldown quel que soit le résultat
        if not url:
            log.info("[%s] aucune version paysage fiable trouvée — %s", ev["id"], title)
            if args.delay and i < len(rows) - 1:
                time.sleep(args.delay)
            continue
        found += 1
        log.info("[%s] paysage → %s — %s", ev["id"], url[:65], title)
        if args.apply:
            conn.execute("UPDATE events_raw SET url_image_wide=? WHERE id=?", (url, ev["id"]))
            conn.commit()
            ev["url_image_wide"] = url
            # Re-push : le grand visuel 16:9 est régénéré à partir de la version paysage.
            new_id, permalink, raw_url = publish_to_as(ev)
            if new_id:
                pushed += 1
        if args.delay and i < len(rows) - 1:
            time.sleep(args.delay)

    conn.close()
    log.info("Paysage — trouvés=%d · re-poussés=%d · sautés (déjà paysage)=%d%s",
             found, pushed, skipped_shape, "  (dry-run : rien écrit)" if not args.apply else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
