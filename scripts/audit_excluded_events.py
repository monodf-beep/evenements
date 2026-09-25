#!/usr/bin/env python3
"""Repère (et, sur --apply, retire) les événements qui correspondent à une règle
d'exclusion ÉDITORIALE (config/excluded_event_keywords.txt) — ex. « jamais le 27e/23e
BCA », le vocabulaire B2B. Sert à rattraper les fiches passées AVANT l'ajout d'une règle
(scripts/evaluator.py ne l'applique qu'aux fiches encore `pending`).

DEUX PANIERS, parce qu'un seul ne protégeait que le présent (angle mort trouvé le
2026-08-05 sur la fiche 3086) :

  • EN LIGNE — la fiche a un `wp_post_id_as` : mise à la CORBEILLE WordPress
    (réversible, via cs/v1/trash) + statut='rejected' + effacement de wp_post_id_as ;
  • EN FILE — aucun post, mais un statut RETENU : c'est le profil exact que
    publish_batch_as sélectionne pour une CRÉATION, donc la fiche partirait en ligne au
    prochain lot. Rejet en base, aucun appel WordPress (il n'y a rien à corbeiller).

RIEN n'est supprimé définitivement.

SÛR : dry-run par défaut. --apply pour agir. N'appelle AUCUNE API LLM (règles
déterministes uniquement — mêmes mots-clés que l'évaluateur).

Usage (VPS) :
    .venv/bin/python -m scripts.audit_excluded_events            # liste (dry-run)
    .venv/bin/python -m scripts.audit_excluded_events --apply    # corbeille + rejette
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.sources import is_excluded_event, load_excluded_events_filter
from scripts.scraper_events import init_db
from scripts.cleanup_as_trash import trash_one
# Même liste que scripts/publish_batch_as.py:61 et scripts/trash_by_ids.py : une fiche
# dans l'un de ces statuts est candidate à la publication.
from scripts.trash_by_ids import RETENUS

log = get_logger("audit-excluded-events")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Repère/retire les événements publiés qui matchent une règle d'exclusion éditoriale.")
    parser.add_argument("--apply", action="store_true", help="Exécute (sinon dry-run).")
    parser.add_argument("--db-only", action="store_true",
                        help="Ne touche PAS WordPress ; marque juste les fiches rejetées en "
                             "base (à utiliser si tu as déjà corbeillé les posts à la main).")
    parser.add_argument("--cap", type=int, default=0, help="Limite le nombre traité (0 = tout).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    excluded_re = load_excluded_events_filter()
    all_rows = [dict(r) for r in conn.execute(
        "SELECT id, title, description, url_source, wp_post_id_as, statut, duplicate_of, "
        "date_event_start FROM events_raw").fetchall()]
    flagged = [r for r in all_rows
              if is_excluded_event(r.get("title", ""), r.get("description", ""), excluded_re,
                                   url=r.get("url_source", ""))]
    published = sum(1 for r in all_rows if (r.get("wp_post_id_as") or 0) > 0)
    targets = [r for r in flagged if (r.get("wp_post_id_as") or 0) > 0]
    # Second panier, ajouté le 2026-08-05 après un angle mort DÉMONTRÉ : la fiche 3086
    # (« French riviera Beauty », doublon non apparié de la 2465) matchait la règle,
    # n'avait AUCUN post WordPress — et échappait donc à cet audit — tout en portant
    # `statut='published_sub'`. Or c'est EXACTEMENT le profil que publish_batch_as
    # sélectionne pour une CRÉATION (statut retenu + wp_post_id_as vide, cf. l.60-70) :
    # le salon B2B n'était pas dormant, il était en file de départ pour le lot de 9h30.
    # L'évaluateur ne l'aurait pas rattrapé, son pré-filtre ne voyant que les `pending`.
    # Une règle éditoriale qui ne protège que le présent ne protège rien.
    en_file = [r for r in flagged
               if (r.get("wp_post_id_as") or 0) == 0 and r.get("statut") in RETENUS]
    if args.cap:
        targets = targets[:args.cap]
        en_file = en_file[:args.cap]

    log.info("%d fiche(s) publiée(s) · %d exclue(s) par règle éditoriale publiée(s) à retirer%s",
             published, len(targets), " (cap %d)" % args.cap if args.cap else "")
    for r in targets:
        log.info("  WP#%s [%s] « %s »", r["wp_post_id_as"], r["id"], (r.get("title") or "")[:60])
    if en_file:
        log.info("%d fiche(s) exclue(s) PAS ENCORE en ligne mais en file de publication "
                 "(statut retenu, aucun post) — à rejeter en base :", len(en_file))
        for r in en_file:
            log.info("  [%s] statut=%s date=%s « %s »", r["id"], r.get("statut"),
                     r.get("date_event_start") or "?", (r.get("title") or "")[:60])

    if not targets and not en_file:
        log.info("Rien à retirer. 👍")
        conn.close()
        return 0
    if not args.apply:
        log.info("=== DRY-RUN : %d à mettre à la corbeille, %d à rejeter en base. "
                 "Relance avec --apply. ===", len(targets), len(en_file))
        conn.close()
        return 0

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    # Les fiches en file n'ont AUCUN post : aucun appel WordPress n'est nécessaire pour
    # elles, l'absence d'identifiants ne doit donc pas les bloquer.
    if targets and not args.db_only and not (wp_url and auth[0] and auth[1]):
        log.error("WP_AS_URL/USER/APP_PASSWORD manquants — impossible d'agir.")
        conn.close()
        return 2

    ok = fail = 0
    for r in targets:
        wp_id = int(r["wp_post_id_as"])
        if args.db_only or trash_one(wp_url, auth, wp_id, force=True):
            conn.execute("UPDATE events_raw SET statut='rejected', wp_post_id_as=NULL, "
                         "published_as_date=NULL, "
                         "llm_justification='Retiré : exclu par règle éditoriale "
                         "(config/excluded_event_keywords.txt).' WHERE id=?", (r["id"],))
            conn.commit()
            ok += 1
            log.info("  WP#%s → %s, fiche %s rejetée.", wp_id,
                     "base seule" if args.db_only else "corbeille", r["id"])
        else:
            fail += 1
            log.warning("  WP#%s : mise à la corbeille échouée (fiche %s laissée).", wp_id, r["id"])

    ferme = 0
    for r in en_file:
        conn.execute("UPDATE events_raw SET statut='rejected', "
                     "llm_justification='Rejeté avant publication : exclu par règle "
                     "éditoriale (config/excluded_event_keywords.txt).' WHERE id=?", (r["id"],))
        conn.commit()
        ferme += 1
        log.info("  [%s] sortie de la file de publication (statut rejected).", r["id"])

    # Règle 6 : on RECOMPTE en base, on ne rapporte pas la longueur des listes de départ.
    restant_en_ligne = restant_en_file = 0
    for r in conn.execute("SELECT id, title, description, url_source, wp_post_id_as, statut "
                          "FROM events_raw"):
        d = dict(r)
        if not is_excluded_event(d.get("title", ""), d.get("description", ""), excluded_re,
                                 url=d.get("url_source", "")):
            continue
        if (d.get("wp_post_id_as") or 0) > 0:
            restant_en_ligne += 1
        elif d.get("statut") in RETENUS:
            restant_en_file += 1

    log.info("=== Terminé : %d %s, %d rejetée(s) avant publication, %d échec(s). ===", ok,
             "réconcilié(s) en base" if args.db_only else "à la corbeille", ferme, fail)
    log.info("Recompté en base : %d exclue(s) encore liée(s) à un post, %d encore en file.",
             restant_en_ligne, restant_en_file)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
