#!/usr/bin/env python3
"""Répare les traductions qui ont ÉCRASÉ leur original (bug titre nom propre du
2026-07-20, avant le correctif force_create).

Symptôme : une fiche traduite (translation_of renseigné) porte le MÊME wp_post_id_as
que l'original → l'endpoint avait mis à jour l'original au lieu de créer une nouvelle
fiche. Résultat : le post WP a été remplacé par l'autre langue, et la liaison Polylang
pointe l'événement vers lui-même.

Réparation, par paire cassée :
  1. RÉ-PUBLIER l'original (restaure son contenu/langue sur son post WP) ;
  2. SUPPRIMER la fausse fiche traduite (redondante — elle pointait sur le même post) ;
  3. remettre translated_at à NULL sur l'original (pour pouvoir le re-traduire propre).
Ensuite : redéployer le correctif cs-publish (force_create) PUIS relancer
scripts.translate_events → la traduction créera cette fois une NOUVELLE fiche.

SÛR : dry-run par défaut. --apply pour agir. Ne consomme AUCUNE API LLM (juste des
appels de publication WordPress).

Usage (VPS) :
    .venv/bin/python -m scripts.repair_translation            # diagnostic
    .venv/bin/python -m scripts.repair_translation --apply    # répare
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
from scripts.scraper_events import init_db
from scripts.publisher_as import publish_to_as

log = get_logger("repair-translation")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Répare les traductions qui ont écrasé l'original.")
    parser.add_argument("--apply", action="store_true", help="Exécute (sinon diagnostic).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # Fiches traduites (translation_of renseigné) partageant le wp_post_id_as de leur original.
    trans = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(translation_of,0) > 0 "
        "AND COALESCE(wp_post_id_as,0) > 0").fetchall()]
    broken = []
    for t in trans:
        src = conn.execute("SELECT * FROM events_raw WHERE id=?", (t["translation_of"],)).fetchone()
        if src and int(src["wp_post_id_as"] or 0) == int(t["wp_post_id_as"] or 0):
            broken.append((dict(src), t))

    log.info("%d fiche(s) traduite(s) au total · %d paire(s) CASSÉE(S) (même post WP que l'original)",
             len(trans), len(broken))
    for src, t in broken:
        log.info("  CASSÉ : original id=%s (WP#%s) « %s » ← traduction id=%s pointe le même post",
                 src["id"], src["wp_post_id_as"], (src.get("title") or "")[:45], t["id"])

    if not broken:
        log.info("Rien à réparer.")
        conn.close()
        return 0
    if not args.apply:
        log.info("=== Diagnostic seul. Relance avec --apply pour réparer. ===")
        conn.close()
        return 0

    fixed = 0
    for src, t in broken:
        # 1. Restaurer l'original sur son post WP (branche mise à jour : wp_post_id_as présent).
        wp_id = publish_to_as(src)
        if not wp_id:
            log.warning("[%s] ré-publication de l'original échouée — on n'efface rien.", src["id"])
            continue
        # 2. Supprimer la fausse fiche traduite (redondante).
        conn.execute("DELETE FROM events_raw WHERE id=?", (t["id"],))
        # 3. Rendre l'original re-traduisible.
        conn.execute("UPDATE events_raw SET translated_at=NULL WHERE id=?", (src["id"],))
        conn.commit()
        fixed += 1
        log.info("[%s] réparé : original restauré sur WP#%s, fausse traduction id=%s supprimée.",
                 src["id"], wp_id, t["id"])

    log.info("=== Réparation terminée : %d/%d paire(s) réparée(s). "
             "Redéploie cs-publish (force_create) puis relance translate_events. ===",
             fixed, len(broken))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
