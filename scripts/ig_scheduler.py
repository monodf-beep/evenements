#!/usr/bin/env python3
"""Publie les posts Instagram PROGRAMMÉS (table ig_scheduled_posts) dont l'heure
est arrivée — cron SÉPARÉ toutes les 15 minutes (cf. deploy/cron_pipeline.sh).

L'API Graph d'Instagram n'offre AUCUNE programmation native pour un outil tiers :
la seule façon de programmer, c'est nous-mêmes. Franck choisit jour/heure sur
/reseaux (app/app.py::reseaux_publish), qui INSÈRE l'intention ici plutôt que de
publier tout de suite ; ce script la reprend au bon moment.

Duplique volontairement le corps de app.py::_do_publish_instagram plutôt que
d'importer app.py entier : app.py démarre une app Flask et fait des migrations de
schéma à l'import, coûteux et hors sujet pour un simple cron CLI. Les DEUX chemins
(clic immédiat / cron programmé) doivent rester logiquement identiques — toute
évolution de l'un doit être reportée sur l'autre.

Exemples :
  .venv/bin/python3 -m scripts.ig_scheduler
  .venv/bin/python3 -m scripts.ig_scheduler --dry-run
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import completeness as comp
from utils import social as social_mod, social_image, social_overlay, wp_media
from utils import instagram_publish as ig

log = get_logger("ig_scheduler")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _publish(ev: dict, terr_label: str, lang: str, kind: str, conn) -> dict:
    """Même chemin que app.py::_do_publish_instagram (résolution image, légende,
    single/carousel/story, journal social_posts) — voir le docstring du module pour
    pourquoi ce n'est pas factorisé par import direct."""
    event_id = ev["id"]
    title = (ev.get("title") or "")[:70]

    if not ig.configured(terr_label):
        return {"ok": False, "error": f"Compte Instagram non configuré pour « {terr_label} »."}

    img_url = (ev.get("wp_raw_image_url_as") or "").strip() or (ev.get("url_image") or "")
    if not img_url:
        return {"ok": False, "error": f"« {title} » — aucune image disponible."}
    try:
        img_resp = requests.get(
            img_url, timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                   "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                     "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                     "Referer": f"{urlparse(img_url).scheme}://{urlparse(img_url).netloc}/"})
        img_resp.raise_for_status()
        content_type = img_resp.headers.get("Content-Type", "").split(";")[0].strip()
        if not content_type.startswith("image/"):
            return {"ok": False, "error": f"« {title} » — URL image invalide "
                                          f"(reçu : {content_type or 'inconnu'})."}
        src = img_resp.content
    except requests.RequestException as exc:
        return {"ok": False, "error": f"« {title} » — photo source injoignable ({exc})."}

    caption = ev.get(f"social_caption_{lang}") or social_mod.caption(ev, lang)
    date_str = social_mod.format_date(ev.get("date_event_start", ""),
                                      ev.get("date_event_end", ""), lang)
    where = ", ".join(p for p in (ev.get("lieu"), ev.get("ville")) if p)
    alt = social_mod.alt_text(ev, lang)
    territoire = ev.get("territoire", "")
    ville = ev.get("ville", "")
    full_title = ev.get("title", "")
    try:
        if kind == "carousel":
            slide1 = social_overlay.compose(
                "carrousel-1", territoire, src, title=full_title, date_str=date_str, ville=ville)
            slides = social_image.carousel(
                src, title=full_title, date_str=date_str, where=where,
                territoire=territoire, ville=ville, slide1_override=slide1)
            urls = []
            for i, sl in enumerate(slides):
                url = wp_media.upload_bytes(
                    social_image.to_jpeg(sl), f"ig-{event_id}-{lang}-{i}.jpg", alt=alt)
                if not url:
                    raise RuntimeError("upload WordPress échoué")
                urls.append(url)
            result = ig.publish_carousel(terr_label, urls, caption, alt_text=alt)
        elif kind == "story":
            img = social_overlay.compose(
                "story-9x16", territoire, src, title=full_title, date_str=date_str,
                where=where, ville=ville)
            if img is None:
                img = social_image.story(
                    src, title=full_title, date_str=date_str, territoire=territoire, ville=ville)
            url = wp_media.upload_bytes(
                social_image.to_jpeg(img), f"ig-{event_id}-{lang}-story.jpg", alt=alt)
            if not url:
                raise RuntimeError("upload WordPress échoué")
            result = ig.publish_story(terr_label, url)
        else:
            img = social_overlay.compose(
                "post-4x5", territoire, src, title=full_title, date_str=date_str,
                where=where, ville=ville)
            if img is None:
                img = social_image.single_post(
                    src, title=full_title, date_str=date_str, territoire=territoire, ville=ville)
            url = wp_media.upload_bytes(
                social_image.to_jpeg(img), f"ig-{event_id}-{lang}.jpg", alt=alt)
            if not url:
                raise RuntimeError("upload WordPress échoué")
            result = ig.publish_single(terr_label, url, caption, alt_text=alt)
    except Exception as exc:  # visuel/upload/API : jamais d'exception non gérée dans un cron
        result = {"ok": False, "error": str(exc)}

    conn.execute(
        "INSERT INTO social_posts (event_id, territoire_label, lang, kind, status, "
        "ig_media_id, error, platform) VALUES (?,?,?,?,?,?,?,?)",
        (event_id, terr_label, lang, kind, "ok" if result.get("ok") else "error",
         result.get("media_id"), result.get("error"), "instagram"))
    return result


def run_due_scheduled_posts(conn) -> tuple[int, int]:
    """Publie tout ce qui est 'pending' et arrivé à échéance. Renvoie (ok, erreurs)."""
    conn.row_factory = sqlite3.Row
    due = conn.execute(
        "SELECT * FROM ig_scheduled_posts WHERE status='pending' "
        "AND scheduled_at <= datetime('now') ORDER BY scheduled_at ASC").fetchall()
    n_ok = n_err = 0
    for sched in due:
        event_id = sched["event_id"]
        row = conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone()
        if row is None:
            conn.execute(
                "UPDATE ig_scheduled_posts SET status='error', error=? WHERE id=?",
                ("Événement introuvable", sched["id"]))
            conn.commit()
            n_err += 1
            continue
        ev = dict(row)
        if not comp.is_complete(ev):
            conn.execute(
                "UPDATE ig_scheduled_posts SET status='error', error=? WHERE id=?",
                ("Événement devenu incomplet", sched["id"]))
            conn.commit()
            n_err += 1
            continue
        result = _publish(ev, sched["territoire_label"], sched["lang"], sched["kind"], conn)
        if result.get("ok"):
            conn.execute(
                "UPDATE ig_scheduled_posts SET status='done', published_at=datetime('now') "
                "WHERE id=?", (sched["id"],))
            log.info("Publié : événement %s (%s, %s, %s)",
                     event_id, sched["territoire_label"], sched["lang"], sched["kind"])
            n_ok += 1
        else:
            conn.execute(
                "UPDATE ig_scheduled_posts SET status='error', error=? WHERE id=?",
                (result.get("error"), sched["id"]))
            log.warning("Échec publication programmée événement %s : %s",
                       event_id, result.get("error"))
            n_err += 1
        conn.commit()
    return n_ok, n_err


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Publie les posts Instagram programmés arrivés à échéance.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Lister les posts dus sans les publier.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row

    if args.dry_run:
        due = conn.execute(
            "SELECT * FROM ig_scheduled_posts WHERE status='pending' "
            "AND scheduled_at <= datetime('now') ORDER BY scheduled_at ASC").fetchall()
        for r in due:
            print(f"  [{r['id']}] événement {r['event_id']} · {r['territoire_label']} · "
                 f"{r['lang']} · {r['kind']} · prévu {r['scheduled_at']}")
        print(f"{len(due)} publication(s) due(s).")
        conn.close()
        return 0

    n_ok, n_err = run_due_scheduled_posts(conn)
    conn.close()
    log.info("Terminé : %d publié(s), %d en erreur.", n_ok, n_err)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
