#!/usr/bin/env python3
"""RATTRAPAGE : purge la FUITE DE MARQUE Observatoire (charte §9) sur les fiches
Agenda Sabauda déjà publiées, et les bascule vers la bannière territoire × catégorie
d'Agenda (config/territory_category_images.txt, 48 images auto-hébergées sur
agendasabauda.eu) — voir utils.sources.pick_banner_image, maintenant la priorité
partout (newsletter, résolution d'image, push WordPress).

MOTIF (charte §9) : des fiches Agenda portent à la une une BANNIÈRE DE L'OBSERVATOIRE
— les 5/6 aplats de marque de config/territory_images.txt, hébergés sur Brevo/
Mailinblue (URLs img.mailinblue.com/.../content_library/...). C'est une fuite de la
marque Observatoire vers le produit Agenda : à retirer partout. pick_banner_image a
été corrigé pour ne PLUS JAMAIS renvoyer de bannière Observatoire (il normalise le
territoire — « Comté de Nice », « Haute-Savoie », « Piémont », « Vallée d'Aoste »… →
Nice/Savoie/Piemonte/Vallee-Aoste — et résout dans le set Agenda, sinon ""). Ce
script s'APPUIE sur ce pick_banner_image corrigé (il ne réimplémente pas la sélection).

Symptôme historique (même cause) : le composeur de newsletter affichait un aplat
"Savoie" tronqué en « …voie » (bannière générique de marque, sans rapport avec la
catégorie de l'événement). Le code produit maintenant la bonne image pour tout NOUVEL
événement, mais les événements déjà en base gardent l'ANCIENNE url_image (la bannière
Observatoire) tant qu'on ne la remplace pas explicitement — d'où ce rattrapage.

Aucun appel API (Anthropic, Wikimedia…) : on ne RE-RÉSOUT rien, on ne fait que
recalculer quelle bannière pick_banner_image choisirait aujourd'hui et remplacer
l'URL si elle a changé. Rapide, gratuit, aucun risque de limite/429.

Deux effets selon l'état de l'événement :
  - pas encore publié sur Agenda Sabauda : la mise à jour DB suffit — la newsletter
    (qui lit events_raw directement) prend la nouvelle image au prochain chargement.
  - déjà publié (wp_post_id_as renseigné) : la mise à jour DB est suivie d'un RE-PUSH
    de l'image à la une vers WordPress (même logique que refill_images_as.py).

Cas où pick_banner_image renvoie "" (territoire hors des 4 couverts, ou set catégorie
vide) : on NE remplace JAMAIS l'image par "" — on ne remet pas de bannière Observatoire
mais on ne casse pas non plus la fiche. L'événement est LOGué « à traiter à la main »
et compté à part.

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
        description="Purge la fuite de bannière Observatoire (charte §9) et bascule vers "
                    "la bannière Agenda territoire × catégorie.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche ce qui serait changé sans toucher ni la base ni WordPress.")
    parser.add_argument("ids", nargs="*", type=int,
                        help="Limite à ces ids ET force le re-push WordPress même si l'image "
                             "en base est déjà à jour — rattrape un run interrompu (id déjà "
                             "corrigé en base mais jamais re-poussé sur WordPress).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    conn.row_factory = sqlite3.Row

    banners = load_territory_images()
    cat_banners = load_territory_category_images()

    # On cible DEUX populations qui se recouvrent en partie :
    #  1. image_source = 'banner' : critère historique (événement déjà sur une bannière
    #     de repli — à ré-évaluer vers la bannière catégorie la plus pertinente) ;
    #  2. url_image trahissant une FUITE Observatoire (charte §9) : URL Brevo/Mailinblue
    #     (img.mailinblue.com/.../content_library/...), QUEL QUE SOIT image_source. Un
    #     événement dont la bannière Observatoire a été posée sans passer par la source
    #     'banner' (image_source NULL/'og'/…) DOIT quand même être attrapé.
    q = ("SELECT * FROM events_raw WHERE duplicate_of IS NULL AND ("
         "COALESCE(image_source,'') = 'banner' "
         "OR url_image LIKE '%mailinblue%' "
         "OR url_image LIKE '%content_library%')")
    params: list = []
    if args.ids:
        q += f" AND id IN ({','.join('?' * len(args.ids))})"
        params = args.ids
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    log.info("%d événement(s) à réévaluer (bannière de repli ou fuite Observatoire).", len(rows))

    force = bool(args.ids)
    leaking = updated = pushed = unchanged = manual = 0
    for ev in rows:
        title = (ev.get("title") or "")[:55]
        old_url = (ev.get("url_image") or "").strip()
        old_low = old_url.lower()
        # Fuite de marque Observatoire (charte §9) : bannière Brevo/Mailinblue.
        is_leak = "mailinblue" in old_low or "content_library" in old_low
        if is_leak:
            leaking += 1
        new_url = pick_banner_image(ev.get("territoire", ""), ev.get("llm_categorie", ""),
                                    str(ev["id"]), cat_banners, banners)
        changed = bool(new_url) and new_url != old_url

        # pick_banner_image corrigé renvoie "" si le territoire est hors des 4 couverts
        # ou si le set catégorie est vide. On ne remplace JAMAIS une image par "" : ni
        # bannière Observatoire (fuite), ni fiche cassée. On signale pour traitement
        # manuel et on laisse l'image en place.
        if not new_url:
            if is_leak:
                manual += 1
                log.warning("[%s] FUITE Observatoire NON résolue (territoire « %s » / "
                            "catégorie « %s ») — À TRAITER À LA MAIN, image conservée — %s",
                            ev["id"], ev.get("territoire"), ev.get("llm_categorie"), title)
            else:
                unchanged += 1
                log.info("[%s] pas de bannière Agenda pour ce territoire — conservée — %s",
                         ev["id"], title)
            continue

        if not changed and not force:
            unchanged += 1
            log.info("[%s] déjà correcte — %s", ev["id"], title)
            continue

        log.info("[%s] %s%s → %s — %s", ev["id"], "FUITE→ " if is_leak else "",
                 old_url[-40:] or "(vide)", new_url, title)
        updated += 1
        if args.dry_run:
            continue

        if changed:
            conn.execute("UPDATE events_raw SET url_image=?, image_credit='' WHERE id=?",
                         (new_url, ev["id"]))
            conn.commit()

        if not ev.get("wp_post_id_as"):
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

    log.info("Terminé — %d fuite(s) Observatoire détectée(s) | %d corrigé(s) en base "
             "(nouvelle bannière Agenda) | %d re-poussé(s) sur WordPress | %d À TRAITER "
             "À LA MAIN (bannière Agenda introuvable, image conservée) | %d déjà correct(s)%s",
             leaking, updated, pushed, manual, unchanged,
             "  (dry-run : rien touché)" if args.dry_run else "")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
