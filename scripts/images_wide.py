#!/usr/bin/env python3
"""Multi-format : l'affiche officielle en PORTRAIT **et** en PAYSAGE (haut de panier).

Les gros événements (festival, musée, mairie, grande fondation — score ≥ 7) ont en général
un vrai kit promo : l'affiche déclinée en **portrait** (verticale) ET en **paysage**
(horizontale). On veut les deux, pour servir chaque format à l'emplacement où il rend le
mieux, SANS jamais couper :

  • url_image_portrait (verticale) → carte 4:3 + réseaux ;
  • url_image_wide     (horizontale) → grand visuel 16:9 de la fiche.

Un seul appel d'agent web propose les deux orientations (source OFFICIELLE de l'événement,
du lieu ou de l'organisateur ; jamais d'agence, charte §8), un agent vision vérifie chacune
(vraiment portrait / vraiment paysage + pertinente), on stocke celles trouvées et on
re-pousse (publisher_as sert alors le bon format par emplacement).

Réservé au haut du panier : publié, score ≥ 7, au moins une orientation encore manquante.
Cooldown intégré (image_wide_at). DRY-RUN par défaut.

Exemples :
  .venv/bin/python3 -m scripts.images_wide --dry-run
  .venv/bin/python3 -m scripts.images_wide --apply --cap 15 --min-score 7
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
_WIDE_MIN_RATIO = 1.3     # paysage : nettement plus large que haut
_PORTRAIT_MAX_RATIO = 0.9  # portrait : nettement plus haut que large


def search_both(ev: dict, client) -> dict:
    """Agent web : propose l'affiche officielle en PORTRAIT et en PAYSAGE. {} si rien."""
    prompt = (
        "Tu cherches le VISUEL OFFICIEL d'un événement culturel, dans DEUX orientations si "
        "elles existent :\n"
        "  • PORTRAIT (verticale) : l'affiche du programme, format vertical ;\n"
        "  • PAYSAGE (horizontale) : un bandeau officiel ou une photo large du sujet.\n"
        "Source OFFICIELLE : page de l'événement, du lieu, de l'organisateur (institution, "
        "festival, mairie). ÉVITE les photos d'agence de presse / sous copyright strict. "
        "Utilise la recherche web. Ne renvoie une orientation QUE si tu es sûr, et que "
        "l'image est bien dans cette orientation ; laisse vide sinon.\n\n"
        f"Événement : {_clean(ev.get('article_title') or ev.get('title'))}\n"
        f"Lieu : {_clean(ev.get('lieu'))} · Ville : {_clean(ev.get('ville'))}\n"
        f"Catégorie : {ev.get('llm_categorie') or ''} · Territoire : {ev.get('territoire') or ''}\n"
        f"Description : {_clean(ev.get('description'))[:400]}\n\n"
        'Réponds en JSON STRICT : {"portrait_url": "URL directe .jpg/.png verticale ou vide", '
        '"wide_url": "URL directe .jpg/.png horizontale ou vide", "credit": "auteur/source ou '
        'vide", "subject": "ce que montre l\'affiche (2-8 mots)", "found": true|false}'
    )
    try:
        msg = client.messages.create(
            model=SEARCH_MODEL, max_tokens=600,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:  # jamais bloquant
        log.warning("Recherche multi-format échouée : %s", exc)
        return {}
    try:
        from utils import usage
        usage.record_message(SEARCH_MODEL, msg, label="image_multi_search")
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


def _verify_orientation(cand: str, ev: dict, subject: str, want: str, client,
                        blocked: set[str]) -> str:
    """Télécharge + contrôle qu'un candidat est bien dans l'orientation voulue ('wide' ou
    'portrait'), assez grand, non bloqué/logo, ET pertinent (vision). '' si refusé."""
    cand = (cand or "").strip()
    if not cand or not cand.startswith("http"):
        return ""
    if is_blocked_image(cand, blocked) or is_logo_image(cand):
        return ""
    img_bytes, mime = _download(cand)
    if not img_bytes:
        return ""
    try:
        from PIL import Image
        with Image.open(io.BytesIO(img_bytes)) as im:
            w, h = im.size
    except Exception:
        w, h = 0, 0
    if not w or not h or min(w, h) < images.MIN_DIM:
        log.info("  %s écarté (résolution %dx%d) : %s", want, w, h, cand[:60])
        return ""
    ratio = w / h
    if want == "wide" and ratio < _WIDE_MIN_RATIO:
        log.info("  écarté (pas paysage : %dx%d) : %s", w, h, cand[:60])
        return ""
    if want == "portrait" and ratio > _PORTRAIT_MAX_RATIO:
        log.info("  écarté (pas portrait : %dx%d) : %s", w, h, cand[:60])
        return ""
    ok, _, _ = verify_image(ev, subject, img_bytes, mime, client)
    return cand if ok else ""


def _select(conn, args, today: str) -> list[dict]:
    where = [
        "COALESCE(wp_post_id_as,0) > 0",           # publié sur Agenda Sabauda
        "duplicate_of IS NULL",
        "COALESCE(image_source,'') IN ('og','page','web','commons')",  # une VRAIE affiche
        "COALESCE(url_image,'') <> ''",
        "COALESCE(user_score, llm_score, 0) >= ?",  # haut de panier
        # au moins une des deux orientations manque encore
        "(COALESCE(url_image_wide,'') = '' OR COALESCE(url_image_portrait,'') = '')",
    ]
    params: list = [args.min_score]
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
        description="Multi-format : affiche officielle en portrait ET paysage (score ≥ 7).")
    parser.add_argument("ids", nargs="*", type=int, help="Ids précis (défaut : sélection auto).")
    parser.add_argument("--cap", type=int, default=15, help="Nombre max par run.")
    parser.add_argument("--min-score", type=int, default=7, help="Score minimum (défaut 7).")
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
    init_db(conn)  # garantit url_image_wide / url_image_portrait / image_wide_at
    conn.row_factory = sqlite3.Row
    rows = _select(conn, args, today)
    log.info("%d fiche(s) haut de panier à compléter (portrait/paysage, cap %d, score ≥ %d) — %s",
             len(rows), args.cap, args.min_score, "APPLIQUE" if args.apply else "DRY-RUN")

    got_wide = got_portrait = pushed = 0
    for i, r in enumerate(rows):
        ev = dict(r)
        title = (ev.get("title") or "")[:55]
        prop = search_both(ev, client)
        if args.apply:
            mark_web_attempt(conn, "image_wide_at", ev["id"])  # cooldown quel que soit le résultat
        subject = (prop.get("subject") or "") if prop else ""
        new_wide = new_portrait = ""
        if prop:
            if not (ev.get("url_image_wide") or "").strip():
                new_wide = _verify_orientation(prop.get("wide_url"), ev, subject, "wide", client, blocked)
            if not (ev.get("url_image_portrait") or "").strip():
                new_portrait = _verify_orientation(prop.get("portrait_url"), ev, subject, "portrait", client, blocked)
        if not new_wide and not new_portrait:
            log.info("[%s] aucune orientation fiable trouvée — %s", ev["id"], title)
            if args.delay and i < len(rows) - 1:
                time.sleep(args.delay)
            continue
        if new_wide:
            got_wide += 1
            log.info("[%s] paysage  → %s — %s", ev["id"], new_wide[:60], title)
        if new_portrait:
            got_portrait += 1
            log.info("[%s] portrait → %s — %s", ev["id"], new_portrait[:60], title)
        if args.apply:
            sets, vals = [], []
            if new_wide:
                sets.append("url_image_wide=?"); vals.append(new_wide)
            if new_portrait:
                sets.append("url_image_portrait=?"); vals.append(new_portrait)
            vals.append(ev["id"])
            conn.execute(f"UPDATE events_raw SET {', '.join(sets)} WHERE id=?", vals)
            conn.commit()
            ev["url_image_wide"] = new_wide or ev.get("url_image_wide")
            ev["url_image_portrait"] = new_portrait or ev.get("url_image_portrait")
            new_id, permalink, raw_url = publish_to_as(ev)
            if new_id:
                pushed += 1
        if args.delay and i < len(rows) - 1:
            time.sleep(args.delay)

    conn.close()
    log.info("Multi-format — paysages=%d · portraits=%d · re-poussés=%d%s",
             got_wide, got_portrait, pushed, "  (dry-run : rien écrit)" if not args.apply else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
