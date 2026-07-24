#!/usr/bin/env python3
"""RATTRAPAGE : bascule les événements encore sur l'ANCIENNE bannière générique par
territoire (config/territory_images.txt, 5 images hébergées sur Brevo/Mailinblue)
vers la NOUVELLE bannière territoire × catégorie (config/territory_category_images.txt,
48 images auto-hébergées sur agendasabauda.eu) — voir utils.sources.pick_banner_image,
maintenant la priorité partout (newsletter, résolution d'image, push WordPress).

Symptôme observé : le composeur de newsletter affichait un aplat "Savoie" tronqué en
« …voie » (bannière générique, sans rapport avec la catégorie de l'événement) au lieu
d'une image liée au sujet — cf. config/territory_images.txt. Le code produit
maintenant la bonne image pour tout NOUVEL événement, mais les événements déjà en
base gardent l'ANCIENNE url_image tant qu'on ne la remplace pas explicitement.

Aucun appel API (Anthropic, Wikimedia…) : on ne RE-RÉSOUT rien, on ne fait que
recalculer quelle bannière pick_banner_image choisirait aujourd'hui et remplacer
l'URL si elle a changé. Rapide, gratuit, aucun risque de limite/429.

Deux effets selon l'état de l'événement :
  - pas encore publié sur Agenda Sabauda : la mise à jour DB suffit — la newsletter
    (qui lit events_raw directement) prend la nouvelle image au prochain chargement.
  - déjà publié (wp_post_id_as renseigné) : la mise à jour DB est suivie d'un RE-PUSH
    de l'image à la une vers WordPress (même logique que refill_images_as.py).

Usage :
    .venv/bin/python3 scripts/upgrade_category_banners_as.py --dry-run   # aperçu
    .venv/bin/python3 scripts/upgrade_category_banners_as.py             # applique
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.sources import load_territory_images, load_territory_category_images, pick_banner_image
from scripts.scraper_events import init_db
from scripts.publisher_as import publish_to_as

log = get_logger("upgrade-category-banners-as")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Bascule les événements en bannière générique vers la bannière territoire × catégorie.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche ce qui serait changé sans toucher ni la base ni WordPress.")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    conn.row_factory = sqlite3.Row

    banners = load_territory_images()
    cat_banners = load_territory_category_images()

    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(image_source,'') = 'banner' "
        "AND duplicate_of IS NULL").fetchall()]
    log.info("%d événement(s) sur bannière générique à réévaluer.", len(rows))

    updated = pushed = unchanged = 0
    for ev in rows:
        title = (ev.get("title") or "")[:55]
        old_url = (ev.get("url_image") or "").strip()
        new_url = pick_banner_image(ev.get("territoire", ""), ev.get("llm_categorie", ""),
                                    str(ev["id"]), cat_banners, banners)

        if not new_url or new_url == old_url:
            unchanged += 1
            log.info("[%s] déjà correcte — %s", ev["id"], title)
            continue

        log.info("[%s] %s → %s — %s", ev["id"], old_url[-40:] or "(vide)", new_url, title)
        updated += 1
        if args.dry_run:
            continue

        conn.execute("UPDATE events_raw SET url_image=?, image_credit='' WHERE id=?",
                     (new_url, ev["id"]))
        conn.commit()

        if not (ev.get("wp_post_id_as") or "").strip():
            continue  # pas encore publié : la mise à jour DB suffit (newsletter à jour)

        ev["url_image"] = new_url
        ev["image_credit"] = ""
        new_id, permalink, raw_url = None, "", ""
        for attempt in range(3):
            new_id, permalink, raw_url = publish_to_as(ev)
            if new_id:
                break
            if attempt < 2:
                log.warning("[%s] re-push tentative %d échouée — retry dans %ds…",
                            ev["id"], attempt + 1, 5 * (attempt + 1))
                time.sleep(5 * (attempt + 1))
        if new_id:
            if permalink or raw_url:
                conn.execute("UPDATE events_raw SET wp_permalink_as=COALESCE(NULLIF(?,''), wp_permalink_as), "
                             "wp_raw_image_url_as=COALESCE(NULLIF(?,''), wp_raw_image_url_as) WHERE id=?",
                             (permalink, raw_url, ev["id"]))
                conn.commit()
            pushed += 1
        else:
            log.error("[%s] re-push WordPress échoué après 3 tentatives — %s", ev["id"], title)

    log.info("Terminé — %d à jour en base, %d re-poussé(s) sur WordPress, %d déjà correct(s)%s",
             updated, pushed, unchanged, "  (dry-run : rien touché)" if args.dry_run else "")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
