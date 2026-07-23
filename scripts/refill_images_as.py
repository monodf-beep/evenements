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

Mode --unverified : rattrape les événements dont image_source est NULL — jamais
passés par resolve_image (typiquement : url_image posée directement depuis l'enclosure
du flux RSS, à l'ingestion, avant tout garde-fou). Invisibles à --lowres et --recheck,
qui filtrent tous les deux sur des valeurs précises de image_source. Trouvé en
production : un événement (« orchestre de la suisse romande ») affichait la photo
D'UN AUTRE ARTICLE SANS RAPPORT (un fait-divers), simplement parce qu'un item RSS
voisin partageait la même image d'illustration générique. --unverified force une
RÉSOLUTION COMPLÈTE (règles + agent vision) sans comparaison de taille — l'image
actuelle n'a aucune confiance a priori, même si elle est grande.

Mode --refocus : recalcule le SEUL point focal (card_focal_x/y) d'un événement déjà
publié, sans toucher à son image — pour les événements publiés AVANT l'ajout du point
focal auto (utils.image_verify), dont le recadrage 4:3 centré par défaut coupe mal un
titre composé sur l'affiche ou un visage. Cible ponctuelle (ids ou --wp-ids), écrase le
point focal existant (à la différence des autres modes, qui ne l'écrivent que si NULL).

Usage (sur le VPS) :
    .venv/bin/python scripts/refill_images_as.py --dry-run     # voir sans rien pousser
    .venv/bin/python scripts/refill_images_as.py               # tous les AS sans image
    .venv/bin/python scripts/refill_images_as.py 293 1662      # ces id précis
    .venv/bin/python scripts/refill_images_as.py --no-web      # sans Commons (og+page+bannière)
    .venv/bin/python scripts/refill_images_as.py --lowres --dry-run   # images trop petites
    .venv/bin/python scripts/refill_images_as.py --lowres      # les remplacer + re-pousser
    .venv/bin/python scripts/refill_images_as.py --unverified --dry-run   # jamais vérifiées
    .venv/bin/python scripts/refill_images_as.py --unverified   # les re-résoudre + re-pousser
    .venv/bin/python scripts/refill_images_as.py --wp-ids 1234 --refocus  # recadrage seul
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
                           load_territory_images, pick_image)
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
    """Événements AS publiés qui gagneraient une vraie photo ≥ min_dim :
      • image RÉELLE (og/page/web/commons) mais trop petite (floue une fois étirée) ;
      • OU repli bannière : générique, à remplacer par une vraie photo si on en trouve
        une (c'est le cas du château montré avec le fond abstrait alors qu'une photo
        Commons existe).
    La garde de non-dégradation (côté boucle) empêche tout remplacement qui n'améliore
    pas — mesurer ici ne fait que présélectionner les candidats."""
    q = ("SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,'') <> '' "
         "AND duplicate_of IS NULL AND COALESCE(url_image,'') <> '' "
         f"AND COALESCE(image_source,'') IN ({','.join('?' * (len(_REAL_SOURCES) + 1))})")
    params: list = [*_REAL_SOURCES, "banner"]
    if ids:
        q += f" AND id IN ({','.join('?' * len(ids))})"
        params += list(ids)
    out = []
    for r in conn.execute(q, params).fetchall():
        ev = dict(r)
        # Une bannière est un repli générique : toujours candidate (on tentera mieux).
        # Une vraie image n'est candidate que si elle est trop petite.
        if ev.get("image_source") == "banner":
            ev["_old_side"] = 0
            out.append(ev)
            continue
        side = images.remote_min_side(ev["url_image"])
        if side == 0 or side < min_dim:
            ev["_old_side"] = side
            out.append(ev)
    return out


def select_refocus(conn: sqlite3.Connection, ids, wp_ids) -> list[dict]:
    """Événements ciblés pour un recalcul du SEUL point focal — l'image ACTUELLE est
    conservée (pas de nouvelle recherche og/page/Commons), seul son cadrage 4:3 est
    revu. Sert quand un événement a été publié AVANT l'ajout du point focal auto
    (card_focal_x/y encore NULL) et que le recadrage centré par défaut coupe mal un
    titre/visage — ex. une affiche dont le texte composé sur le côté est tronqué."""
    if wp_ids:
        placeholders = ",".join("?" * len(wp_ids))
        q = (f"SELECT * FROM events_raw WHERE duplicate_of IS NULL "
             f"AND CAST(wp_post_id_as AS TEXT) IN ({placeholders})")
        rows = [dict(r) for r in conn.execute(q, [str(x) for x in wp_ids]).fetchall()]
    else:
        q = (f"SELECT * FROM events_raw WHERE duplicate_of IS NULL "
             f"AND id IN ({','.join('?' * len(ids))})")
        rows = [dict(r) for r in conn.execute(q, ids).fetchall()]
    return [r for r in rows
            if (r.get("url_image") or "").strip() and not is_logo_image(r["url_image"])]


def _run_refocus(conn: sqlite3.Connection, args) -> int:
    """Mode --refocus : recalcule le point focal de l'image ACTUELLE (aucune nouvelle
    recherche) et republie. Nécessite ids ou --wp-ids (pas de sélection en masse)."""
    if not args.ids and not args.wp_ids:
        log.error("--refocus nécessite des ids précis ou --wp-ids (pas de sélection en masse).")
        conn.close()
        return 1
    rows = select_refocus(conn, args.ids, args.wp_ids)
    log.info("%d événement(s) à recadrer (image conservée).", len(rows))
    if not rows:
        conn.close()
        return 0

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY absente — --refocus a besoin de l'agent vision.")
        conn.close()
        return 1
    import anthropic
    client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
    verify_model = os.getenv("ANTHROPIC_MODEL_VISION") or "claude-haiku-4-5"

    from utils import image_verify
    from utils.images import _PAGE_UA, _MAX_CHECK_BYTES
    import requests

    pushed = 0
    for ev in rows:
        title = (ev.get("title") or "")[:55]
        url = ev["url_image"]
        try:
            r = requests.get(url, headers=_PAGE_UA, timeout=15, stream=True)
            if r.status_code != 200:
                log.warning("[%s] image injoignable (%s) — %s", ev["id"], r.status_code, title)
                continue
            mime = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            buf = b""
            for chunk in r.iter_content(65536):
                buf += chunk
                if len(buf) > _MAX_CHECK_BYTES:
                    break
        except requests.RequestException as exc:
            log.warning("[%s] téléchargement échoué (%s) — %s", ev["id"], exc, title)
            continue
        ok, fx, fy = image_verify.verify_relevance(buf, mime, ev, client, verify_model)
        if not ok:
            log.warning("[%s] l'agent vision juge cette image hors-sujet (conservée quand même — "
                        "--refocus ne change QUE le cadrage) — %s", ev["id"], title)
        log.info("[%s] focal=(%.2f,%.2f) — %s", ev["id"], fx, fy, title)
        if args.dry_run:
            continue
        conn.execute("UPDATE events_raw SET card_focal_x=?, card_focal_y=? WHERE id=?",
                     (fx, fy, ev["id"]))
        conn.commit()
        ev["card_focal_x"], ev["card_focal_y"] = fx, fy
        new_id = None
        for attempt in range(3):
            new_id = publish_to_as(ev)
            if new_id:
                break
            if attempt < 2:
                log.warning("[%s] re-push tentative %d échouée — retry dans %ds…",
                            ev["id"], attempt + 1, 5 * (attempt + 1))
                time.sleep(5 * (attempt + 1))
        if new_id:
            pushed += 1
        else:
            log.error("[%s] re-push échoué après 3 tentatives — %s", ev["id"], title)

    log.info("Point focal recalculé — %d re-poussé(s) sur %d%s",
             pushed, len(rows), "  (dry-run : rien poussé)" if args.dry_run else "")
    conn.close()
    return 0


def select_unverified(conn: sqlite3.Connection, ids) -> list[dict]:
    """Événements AS publiés dont image_source est NULL — jamais passés par
    resolve_image, donc jamais vus par --lowres/--recheck (qui filtrent tous les deux
    sur des valeurs précises de image_source). L'image en base n'a AUCUNE confiance a
    priori, quelle que soit sa taille — voir le docstring du module."""
    q = ("SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,'') <> '' "
         "AND duplicate_of IS NULL AND COALESCE(url_image,'') <> '' AND image_source IS NULL")
    params: list = []
    if ids:
        q += f" AND id IN ({','.join('?' * len(ids))})"
        params += list(ids)
    return [dict(r) for r in conn.execute(q, params).fetchall()]


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
    parser.add_argument("--no-verify", action="store_true",
                        help="Désactive l'agent vision de vérification (plus rapide/moins cher, "
                             "mais ne détecte plus les bandeaux/images hors-sujet non listés).")
    parser.add_argument("--lowres", action="store_true",
                        help="Cible les images RÉELLES trop petites déjà en base (au lieu des "
                             "seules images manquantes) et ne remplace que par plus grand.")
    parser.add_argument("--min-dim", type=int, default=images.MIN_DIM,
                        help=f"Seuil du plus petit côté en mode --lowres (défaut {images.MIN_DIM}px).")
    parser.add_argument("--bad-url", default="",
                        help="RÉCUPÉRATION : cible les événements dont url_image contient cette "
                             "sous-chaîne (une image parasite partagée, ex. un bandeau de site), "
                             "les ré-résout et les re-pousse. Rejette toute nouvelle URL contenant "
                             "encore la sous-chaîne.")
    parser.add_argument("--recheck", default="",
                        help="RÉCUPÉRATION groupée : ré-résout tous les événements publiés dont "
                             "image_source est dans cette liste (ex. 'page,web') avec la chaîne "
                             "corrigée, et ne re-pousse QUE là où l'image change réellement. "
                             "Répare en masse les bandeaux attrapés par le scan de page.")
    parser.add_argument("--unverified", action="store_true",
                        help="Cible les événements dont image_source est NULL (jamais passés par "
                             "resolve_image — invisibles à --lowres/--recheck). Force une résolution "
                             "complète, sans confiance a priori dans l'image actuelle.")
    parser.add_argument("--refocus", action="store_true",
                        help="Recalcule UNIQUEMENT le point focal (card_focal_x/y) de l'image DÉJÀ "
                             "en place — aucune nouvelle recherche d'image. Sert aux événements "
                             "publiés avant l'ajout du point focal auto, dont le recadrage centré par "
                             "défaut coupe mal un titre/visage. ÉCRASE le point focal existant (à la "
                             "différence des autres modes) : usage ciblé (ids ou --wp-ids), pas en masse.")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    conn.row_factory = sqlite3.Row

    if args.refocus:
        return _run_refocus(conn, args)

    if args.bad_url:
        q = ("SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,'') <> '' "
             "AND duplicate_of IS NULL AND url_image LIKE ?")
        rows = [dict(r) for r in conn.execute(q, (f"%{args.bad_url}%",)).fetchall()]
        log.info("%d événement(s) avec l'image parasite « %s » à ré-résoudre.",
                 len(rows), args.bad_url)
    elif args.recheck:
        sources = [s.strip() for s in args.recheck.split(",") if s.strip()]
        ph = ",".join("?" * len(sources))
        q = (f"SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,'') <> '' "
             f"AND duplicate_of IS NULL AND COALESCE(image_source,'') IN ({ph})")
        rows = [dict(r) for r in conn.execute(q, sources).fetchall()]
        log.info("%d événement(s) (image_source ∈ %s) à ré-résoudre ; re-push seulement si l'image change.",
                 len(rows), sources)
    elif args.lowres:
        rows = select_lowres(conn, args.ids, args.min_dim)
        log.info("%d image(s) à réévaluer (réelles < %dpx, ou bannières remplaçables).",
                 len(rows), args.min_dim)
    elif args.unverified:
        rows = select_unverified(conn, args.ids)
        log.info("%d événement(s) jamais vérifiés (image_source NULL) à résoudre.", len(rows))
    else:
        rows = select_targets(conn, args.ids, args.wp_ids)
        log.info("%d événement(s) Agenda Sabauda sans image à traiter.", len(rows))
    if not rows:
        log.info("Rien à faire — aucun événement AS ciblé.")
        conn.close()
        return 0

    # LLM = requête visuelle Commons (étage 3) + AGENT vision de vérification. Optionnel.
    client = None
    if not args.no_web:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
        else:
            log.warning("ANTHROPIC_API_KEY absente : pas de Commons, og:image + page + bannière seulement.")
    # Chemin PUBLICATION : la pertinence prime → l'agent vision vérifie chaque image
    # (og/page/Commons) avant de la re-pousser, sauf --no-verify. Le modèle vision est
    # économique (haiku par défaut).
    verify_client = None if args.no_verify else client
    verify_model = os.getenv("ANTHROPIC_MODEL_VISION") or "claude-haiku-4-5"

    banners = load_territory_images()
    blocked = load_blocked_image_domains()
    stats = {"og": 0, "page": 0, "commons": 0, "banner": 0, "none": 0}
    pushed = 0

    skipped_lowres = 0
    for ev in rows:
        title = (ev.get("title") or "")[:55]
        old_url = (ev.get("url_image") or "").strip()
        # Récupération : on VIDE d'abord l'image parasite/non fiable pour que
        # resolve_image reparte de la chaîne (og:image → page → Commons → bannière)
        # sans jamais s'appuyer sur l'ancienne URL.
        if args.bad_url or args.unverified:
            ev["url_image"] = ""
        url, credit, source, focal_x, focal_y = resolve_image(
            ev, client, blocked, banners,
            verify_client=verify_client, verify_model=verify_model)

        # Garde --unverified : même si l'image résolue est IDENTIQUE à l'ancienne (elle
        # était donc déjà correcte), on enregistre sa source en base pour qu'elle ne
        # soit plus jamais NULL — mais on ne re-pousse pas sur WordPress pour rien.
        if args.unverified and url and url == old_url:
            if not args.dry_run:
                conn.execute("UPDATE events_raw SET image_credit=?, image_source=? WHERE id=?",
                             (credit, source, ev["id"]))
                conn.commit()
            skipped_lowres += 1
            log.info("[%s] confirmée (%s), pas de re-push — %s", ev["id"], source, title)
            continue

        # Récupération : si la ré-résolution retombe sur l'image parasite, on la refuse
        # (repli bannière territoire plutôt que de re-publier le bandeau hors-sujet).
        if args.bad_url and url and args.bad_url in url:
            url = pick_image(ev.get("territoire", ""), str(ev["id"]), banners) or ""
            credit, source = "", ("banner" if url else "none")

        # Garde --recheck : on ne re-pousse QUE si l'image change vraiment (sinon
        # l'événement était déjà correct — aucun appel WordPress inutile).
        if args.recheck and (not url or url == old_url):
            skipped_lowres += 1
            log.info("[%s] inchangée (%s) — %s", ev["id"], source or "aucune", title)
            continue

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
            # Point focal : seulement si l'événement n'en a pas déjà un choisi à la main
            # (back-office) — jamais écrasé par la suggestion automatique de l'agent.
            if ev.get("card_focal_x") is None and ev.get("card_focal_y") is None:
                ev["card_focal_x"] = focal_x
                ev["card_focal_y"] = focal_y
            stats[source] += 1
            if not args.dry_run:
                conn.execute(
                    "UPDATE events_raw SET url_image=?, image_credit=?, image_source=?, "
                    "card_focal_x=COALESCE(card_focal_x, ?), card_focal_y=COALESCE(card_focal_y, ?) "
                    "WHERE id=?",
                    (url, credit, source, focal_x, focal_y, ev["id"]))
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

    tail = (f" | gardées (pas mieux)={skipped_lowres}" if args.lowres
            else f" | inchangées={skipped_lowres}" if args.recheck
            else f" | confirmées sans re-push={skipped_lowres}" if args.unverified else "")
    log.info("Résolu — og=%d · page=%d · Commons=%d · bannière=%d · aucun=%d | re-poussés=%d%s%s",
             stats["og"], stats["page"], stats["commons"], stats["banner"], stats["none"],
             pushed, tail, "  (dry-run : rien poussé)" if args.dry_run else "")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
