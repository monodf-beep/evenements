#!/usr/bin/env python3
"""Traduit les événements à BON SCORE dans l'autre langue et publie la fiche traduite
comme TRADUCTION Polylang liée — pour que le site soit bilingue (un événement savoyard
visible côté italien, un événement piémontais côté français) et que les newsletters des
deux côtés aient de la matière.

Sens : FR → IT et IT → FR, selon la langue détectée de l'événement source.

Périmètre volontairement RESSERRÉ (coût API + qualité) :
  • événement déjà EN LIGNE sur l'Agenda (wp_post_id_as renseigné),
  • non-doublon, pas déjà une traduction, pas déjà traduit,
  • score utile (--min-score, défaut 6),
  • pas de jumelle déjà existante dans la langue cible (même affiche = même événement
    bilingue déjà présent → on laisse scripts.link_translations_as le lier).

On traduit TITRE + DESCRIPTION (le contenu de la fiche traduite est bâti sur la
description traduite ; l'article enrichi FR n'est pas recopié). La langue est FORCÉE
(force_lang) à la publication. Puis on LIE les deux fiches via cs/v1/link-translations.

SÛR : dry-run par défaut (--apply pour agir), --cap pour de petits lots.

Usage (VPS) :
    .venv/bin/python -m scripts.translate_events                    # simulation
    .venv/bin/python -m scripts.translate_events --min-score 6 --cap 10 --apply
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.lang import detect_lang
from scripts.scraper_events import init_db
from scripts.publisher_as import publish_to_as
from scripts.link_translations_as import _post_link

log = get_logger("translate-events")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL_TRANSLATE", "claude-haiku-4-5")

_LANG_NAME = {"fr": "français", "it": "italien"}


def _ensure_cols(conn):
    for col, decl in (("translation_of", "INTEGER"), ("translated_at", "TEXT"),
                      ("translated_lang", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass


def _target(src_lang: str) -> str:
    return "it" if src_lang == "fr" else "fr"


def translate_title_desc(client, model, title: str, desc: str, target: str) -> dict | None:
    """Renvoie {'title':..., 'description':...} traduits, ou None si échec."""
    tgt = _LANG_NAME[target]
    prompt = (
        f"Traduis en {tgt} ce titre et cette description d'un événement culturel. "
        f"Garde les NOMS PROPRES (lieux, artistes, festivals) tels quels, ne traduis pas "
        f"les noms de villes qui n'ont pas d'exonyme courant, conserve les dates et les "
        f"chiffres. Ton neutre et informatif. Réponds UNIQUEMENT en JSON : "
        f'{{"title": "...", "description": "..."}}.\n\n'
        f"TITRE : {title}\n\nDESCRIPTION : {desc[:2000]}")
    try:
        resp = client.messages.create(
            model=model, max_tokens=1500,
            messages=[{"role": "user", "content": prompt}])
        txt = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        if txt.startswith("```"):
            txt = txt.strip("`")
            txt = txt[4:] if txt.lower().startswith("json") else txt
        data = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
        t, d = (data.get("title") or "").strip(), (data.get("description") or "").strip()
        return {"title": t, "description": d} if t else None
    except (anthropic.APIError, ValueError, KeyError, TypeError) as exc:
        log.warning("Traduction échouée : %s", exc)
        return None


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Traduit les événements à bon score (FR↔IT).")
    parser.add_argument("--apply", action="store_true", help="Exécute (sinon simulation).")
    parser.add_argument("--min-score", type=int, default=6, help="Score minimum (défaut 6).")
    parser.add_argument("--cap", type=int, default=10, help="Nb max par run (défaut 10).")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _ensure_cols(conn)

    # Index des affiches par langue (dédup : ne pas re-traduire un événement dont la
    # jumelle dans la langue cible existe déjà — même image = même événement bilingue).
    img_lang: dict[str, set] = {"fr": set(), "it": set()}
    for r in conn.execute("SELECT title, description, territoire, url_image FROM events_raw "
                          "WHERE COALESCE(url_image,'')<>'' AND COALESCE(wp_post_id_as,0)>0 "
                          "AND duplicate_of IS NULL"):
        img_lang[detect_lang(r["title"] or "", r["description"] or "", r["territoire"] or "")].add(r["url_image"])

    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0)>0 AND duplicate_of IS NULL "
        "AND COALESCE(translation_of,0)=0 AND COALESCE(translated_at,'')='' "
        "AND COALESCE(user_score, llm_score, 0) >= ? "
        "ORDER BY COALESCE(user_score, llm_score, 0) DESC, id ASC LIMIT ?",
        (args.min_score, args.cap)).fetchall()]
    log.info("%d événement(s) candidat(s) (score ≥ %d, en ligne, non traduits)",
             len(rows), args.min_score)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key) if (api_key and args.apply) else None
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))

    done = skipped = 0
    for ev in rows:
        src = detect_lang(ev.get("title", ""), ev.get("description", ""), ev.get("territoire", ""))
        tgt = _target(src)
        img = ev.get("url_image") or ""
        if img and img in img_lang.get(tgt, set()):
            skipped += 1
            log.info("[%s] jumelle %s déjà présente (même affiche) — ignoré : %s",
                     ev["id"], tgt, (ev.get("title") or "")[:50])
            continue
        log.info("[%s] %s→%s (score %s) : %s", ev["id"], src, tgt,
                 ev.get("user_score") if ev.get("user_score") is not None else ev.get("llm_score"),
                 (ev.get("title") or "")[:60])
        if not args.apply:
            continue
        if not (client and api_key):
            log.error("ANTHROPIC_API_KEY absente — impossible de traduire."); break
        tr = translate_title_desc(client, args.model, ev.get("title", ""),
                                  ev.get("description", "") or "", tgt)
        if not tr:
            continue
        new_ev = dict(ev)
        new_ev.update({
            "title": tr["title"], "description": tr["description"],
            "article_title": "", "article_md": "", "enrich_data": "",
            "seo_title": "", "seo_meta": "", "seo_slug": "", "seo_keyphrase": "",
            "force_lang": tgt, "wp_post_id_as": None, "wp_post_id_cs": None,
        })
        new_ev.pop("id", None)
        wp_id = publish_to_as(new_ev)
        if not wp_id:
            log.warning("[%s] publication de la traduction échouée.", ev["id"]); continue
        # Enregistre la fiche traduite (url_source synthétique — la colonne est UNIQUE).
        conn.execute(
            "INSERT INTO events_raw (title, description, date_start, date_event_start, "
            "date_event_end, lieu, ville, territoire, url_source, url_image, organisateur, "
            "source_name, source_type, llm_score, user_score, llm_categorie, statut, "
            "wp_post_id_as, published_as_date, translation_of, translated_lang, image_credit) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tr["title"], tr["description"], ev.get("date_start"), ev.get("date_event_start"),
             ev.get("date_event_end"), ev.get("lieu"), ev.get("ville"), ev.get("territoire"),
             f"translated:{ev['id']}:{tgt}", ev.get("url_image"), ev.get("organisateur"),
             ev.get("source_name"), ev.get("source_type"), ev.get("llm_score"),
             ev.get("user_score"), ev.get("llm_categorie"), ev.get("statut"), wp_id,
             datetime.now().isoformat(timespec="seconds"), ev["id"], tgt, ev.get("image_credit")))
        # Lie les deux fiches (Polylang) via l'endpoint.
        if all([wp_url, auth[0], auth[1]]):
            _post_link(wp_url, auth, {src: int(ev["wp_post_id_as"]), tgt: int(wp_id)})
        conn.execute("UPDATE events_raw SET translated_at=? WHERE id=?",
                     (datetime.now().isoformat(timespec="seconds"), ev["id"]))
        conn.commit()
        img_lang.setdefault(tgt, set()).add(img)
        done += 1
        log.info("[%s] traduit → WP#%s (%s), lié.", ev["id"], wp_id, tgt)

    log.info("=== Traduction terminée : %d traduit(s), %d ignoré(s)%s ===",
             done, skipped, "" if args.apply else "  (simulation : rien écrit)")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
