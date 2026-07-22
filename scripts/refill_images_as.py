#!/usr/bin/env python3
"""Re-remplit l'image des événements DÉJÀ publiés sur Agenda Sabauda qui n'en ont
pas (ou dont l'image n'est qu'un logo), puis les RE-POUSSE vers WordPress.

Source de vérité = backoffice. Pour chaque événement ciblé :
  1. on RÉSOUT l'image via le pipeline existant (scripts/visuals.resolve_image) :
     og:image → 1re photo de la page source → Wikimedia Commons → bannière territoire ;
  2. on MET À JOUR la base (url_image, image_credit, image_source) ;
  3. on RE-POUSSE l'image à la une vers WordPress (scripts/publisher_as.publish_to_as,
     qui met à jour l'événement existant via wp_post_id_as).

Mode --lowres : rattrape RÉTROACTIVEMENT les images basse définition déjà en base.
Les garde-fous de résolution (utils.images.MIN_DIM) ne s'appliquent qu'aux nouvelles
images ; les articles déjà publiés gardent une photo trop petite (floue une fois
étirée en 1080 px). --lowres élargit la sélection aux événements dont l'image RÉELLE
(og/page/web/commons) mesure moins de --min-dim de côté, cherche mieux, et ne
remplace QUE par strictement plus grand (jamais de dégradation, jamais une vraie
photo troquée pour une bannière) avant de re-pousser.

⚠️ Prérequis : l'endpoint cs/v1/event doit préserver le statut à la mise à jour
   (correctif « unset post_status » de cs-publish.php) — sinon un événement publié
   serait repassé en brouillon au re-push. Vérifie que le correctif est déployé.

Usage (sur le VPS) :
    .venv/bin/python scripts/refill_images_as.py --dry-run     # voir sans rien pousser
    .venv/bin/python scripts/refill_images_as.py               # tous les AS sans image
    .venv/bin/python scripts/refill_images_as.py 293 1662      # ces id précis
    .venv/bin/python scripts/refill_images_as.py --no-web      # sans Commons (og+page+bannière)
    .venv/bin/python scripts/refill_images_as.py --lowres --dry-run   # images trop petites
    .venv/bin/python scripts/refill_images_as.py --lowres      # les remplacer + re-pousser
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
from utils import images
from utils.sources import (is_logo_image, load_blocked_image_domains,
                           load_territory_images)
from scripts.scraper_events import init_db
from scripts.visuals import resolve_image
from scripts.publisher_as import publish_to_as

log = get_logger("refill-images-as")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
# Sources d'image « réelles » réévaluées en mode --lowres (une bannière est un repli
# assumé, une image vide relève du mode normal ci-dessus).
_REAL_SOURCES = ("og", "page", "web", "commons")


def select_targets(conn: sqlite3.Connection, ids, wp_ids) -> list[dict]:
    """Événements à re-imager.

    --wp-ids : ON FORCE le retraitement des événements dont l'id WP (wp_post_id_as)
    est fourni, SANS filtre sur url_image — utile quand l'image existe en base mais a
    échoué à l'upload (donc pas de vignette côté WordPress). C'est le cas des 10 de la
    home. Sinon : événements publiés sur AS dont url_image est vide ou n'est qu'un logo.
    """
    if wp_ids:
        placeholders = ",".join("?" * len(wp_ids))
        q = ("SELECT * FROM events_raw WHERE duplicate_of IS NULL "
             f"AND CAST(wp_post_id_as AS TEXT) IN ({placeholders})")
        return [dict(r) for r in conn.execute(q, [str(x) for x in wp_ids]).fetchall()]

    q = ("SELECT * FROM events_raw "
         "WHERE COALESCE(wp_post_id_as,'') <> '' AND duplicate_of IS NULL")
    params: list = []
    if ids:
        q += f" AND id IN ({','.join('?' * len(ids))})"
        params += list(ids)
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    return [r for r in rows
            if not (r.get("url_image") or "").strip() or is_logo_image(r.get("url_image"))]


def select_lowres(conn: sqlite3.Connection, ids, min_dim: int) -> list[dict]:
    """Événements AS publiés dont l'image RÉELLE stockée est plus petite que min_dim
    (mesure réseau réelle — l'URL seule ne dit rien de la taille)."""
    q = ("SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,'') <> '' "
         "AND duplicate_of IS NULL AND COALESCE(url_image,'') <> '' "
         f"AND COALESCE(image_source,'') IN ({','.join('?' * len(_REAL_SOURCES))})")
    params: list = list(_REAL_SOURCES)
    if ids:
        q += f" AND id IN ({','.join('?' * len(ids))})"
        params += list(ids)
    out = []
    for r in conn.execute(q, params).fetchall():
        ev = dict(r)
        side = images.remote_min_side(ev["url_image"])
        if side == 0 or side < min_dim:
            ev["_old_side"] = side
            out.append(ev)
    return out


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Re-remplit et re-pousse l'image des événements Agenda Sabauda sans visuel.")
    parser.add_argument("ids", nargs="*", type=int, help="Ids backoffice précis (défaut : tous les AS sans image).")
    parser.add_argument("--wp-ids", nargs="*", type=int, default=None,
                        help="Cible par id WordPress (wp_post_id_as) — FORCE le retraitement, "
                             "même si url_image est renseigné (cas des events sans vignette côté WP).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Résout l'image mais ne met à jour NI la base NI WordPress.")
    parser.add_argument("--no-web", action="store_true",
                        help="Pas de recherche Commons (og:image + page + bannière seulement).")
    parser.add_argument("--lowres", action="store_true",
                        help="Cible les images RÉELLES trop petites déjà en base (au lieu des "
                             "seules images manquantes) et ne remplace que par plus grand.")
    parser.add_argument("--min-dim", type=int, default=images.MIN_DIM,
                        help=f"Seuil du plus petit côté en mode --lowres (défaut {images.MIN_DIM}px).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    conn.row_factory = sqlite3.Row
    if args.lowres:
        rows = select_lowres(conn, args.ids, args.min_dim)
        log.info("%d image(s) trop petite(s) (< %dpx) déjà publiée(s) à réévaluer.",
                 len(rows), args.min_dim)
    else:
        rows = select_targets(conn, args.ids, args.wp_ids)
        log.info("%d événement(s) Agenda Sabauda sans image à traiter.", len(rows))
    if not rows:
        log.info("Rien à faire — aucun événement AS ciblé.")
        conn.close()
        return 0

    # LLM = seulement la requête visuelle Commons (étage 3). Optionnel.
    client = None
    if not args.no_web:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
        else:
            log.warning("ANTHROPIC_API_KEY absente : pas de Commons, og:image + page + bannière seulement.")

    banners = load_territory_images()
    blocked = load_blocked_image_domains()
    stats = {"og": 0, "page": 0, "commons": 0, "banner": 0, "none": 0}
    pushed = 0

    skipped_lowres = 0
    for ev in rows:
        title = (ev.get("title") or "")[:55]
        old_url = (ev.get("url_image") or "").strip()
        url, credit, source = resolve_image(ev, client, blocked, banners)

        # Garde --lowres : on ne remplace QUE par strictement plus grand, et jamais une
        # vraie photo par une bannière — sinon on garde l'existante et on ne re-pousse
        # pas (rien ne s'aggrave, aucun appel WordPress inutile).
        if args.lowres:
            new_side = images.remote_min_side(url) if url else 0
            old_side = ev.get("_old_side", 0)
            if not url or source == "banner" or url == old_url or new_side <= max(old_side, args.min_dim - 1):
                skipped_lowres += 1
                log.info("[%s] gardée (%dpx — pas de meilleure trouvée : candidate=%s %dpx) — %s",
                         ev["id"], old_side, source or "aucune", new_side, title)
                continue

        if url:
            ev["url_image"] = url
            ev["image_credit"] = credit
            ev["image_source"] = source
            stats[source] += 1
            if not args.dry_run:
                conn.execute(
                    "UPDATE events_raw SET url_image=?, image_credit=?, image_source=? WHERE id=?",
                    (url, credit, source, ev["id"]))
                conn.commit()
            log.info("[%s] image %-7s %s — %s", ev["id"], source, url[:58], title)
        else:
            stats["none"] += 1
            log.warning("[%s] AUCUN visuel (bannière absente pour « %s » ?) — %s",
                        ev["id"], ev.get("territoire"), title)

        if args.dry_run:
            continue
        # publish_to_as refait sa PROPRE chaîne de repli (url_image → page source →
        # bannière) et met à jour l'événement existant (wp_post_id_as) sans le dépublier.
        # Retry : OVH mutualisé renvoie parfois un 504 sur l'upload d'une grande image.
        new_id = None
        for attempt in range(3):
            new_id = publish_to_as(ev)
            if new_id:
                break
            if attempt < 2:
                log.warning("[%s] re-push tentative %d échouée (504/timeout ?) — retry dans %ds…",
                            ev["id"], attempt + 1, 5 * (attempt + 1))
                time.sleep(5 * (attempt + 1))
        if new_id:
            pushed += 1
        else:
            log.error("[%s] re-push échoué après 3 tentatives — %s", ev["id"], title)

    tail = f" | gardées (pas mieux)={skipped_lowres}" if args.lowres else ""
    log.info("Résolu — og=%d · page=%d · Commons=%d · bannière=%d · aucun=%d | re-poussés=%d%s%s",
             stats["og"], stats["page"], stats["commons"], stats["banner"], stats["none"],
             pushed, tail, "  (dry-run : rien poussé)" if args.dry_run else "")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
