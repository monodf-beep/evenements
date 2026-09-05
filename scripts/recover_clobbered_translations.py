#!/usr/bin/env python3
"""Répare les dégâts d'un bug RACINE découvert le 2026-07-29 : `scripts.enrich` ne
savait pas reconnaître une fiche TRADUITE (translation_of renseigné) et pouvait la
reprendre comme n'importe quel événement jamais enrichi — or enrich écrit TOUJOURS en
français par défaut. Résultat, constaté en vrai sur l'id 4312 (traduction italienne de
Niccolò Fabi, id 2387) : la traduction fraîchement produite par `translate_events.py`
était silencieusement ÉCRASÉE par un article français au prochain passage d'enrich.
Le symptôme (langue détectée = français des deux côtés) a ensuite fait passer ces
paires pour de mauvais jumelages aux yeux de `audit_translation_langs.py`, qui les a
fait DÉLIER par `unlink_bad_translations.py` — alors que le jumelage d'origine était
correct, seul le CONTENU avait été corrompu après coup.

Le bug racine est corrigé (scripts/enrich.py exclut désormais translation_of!=0 de sa
sélection ; translate_events.py marque enrich_status='enriched' à la création). Ce
script répare l'EXISTANT : il retrouve les fiches créées par translate_events.py (leur
`url_source` synthétique commence par "translated:<id_original>:<langue>" — un marqueur
qui survient même après un délinkage) et, pour celles qui ont un `enriched_at` POSTÉRIEUR
à leur création (signe qu'enrich est repassé dessus après coup), restaure translation_of/
translated_lang. La restauration du lien est gratuite (DB seule) ; le CONTENU reste
français tant qu'une vraie re-traduction n'est pas relancée (`--retranslate`, coût API) —
ce script ne la lance pas lui-même, il liste seulement les ids à re-traduire ensuite.

Usage (VPS) :
    .venv/bin/python -m scripts.recover_clobbered_translations            # liste, ne touche rien
    .venv/bin/python -m scripts.recover_clobbered_translations --apply    # restaure les liens
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.scraper_events import init_db

log = get_logger("recover-clobbered-translations")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
_SRC_PAT = re.compile(r"^translated:(\d+):(fr|it)$")


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Restaure les liens de traduction cassés par le bug enrich/translate.")
    parser.add_argument("--apply", action="store_true", help="Restaure réellement (sinon liste seule).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # duplicate_of/statut='merged' exclus : ce sont des doublons déjà tranchés par ailleurs
    # (ex. id 4122, fusionné avec 2387 lors du tout premier correctif de cette session) —
    # les restaurer les ferait repasser à tort pour des victimes de CE bug-ci.
    rows = conn.execute(
        "SELECT id, url_source, translation_of, translated_lang, enriched_at, translated_at, "
        "wp_post_id_as, title FROM events_raw WHERE url_source LIKE 'translated:%' "
        "AND duplicate_of IS NULL AND COALESCE(statut,'') != 'merged'").fetchall()
    log.info("%d fiche(s) créée(s) historiquement par translate_events.py.", len(rows))

    broken = []
    for r in rows:
        m = _SRC_PAT.match(r["url_source"] or "")
        if not m:
            continue
        orig_id, lang = int(m.group(1)), m.group(2)
        if r["translation_of"]:
            continue  # jamais délié : rien à faire
        if not r["enriched_at"]:
            continue  # jamais repris par enrich : pas de corruption à ce titre
        broken.append((r["id"], orig_id, lang, r["title"], r["wp_post_id_as"]))

    log.info("%d fiche(s) délié(e)s ET reprise(s) par enrich après coup (contenu probablement "
             "corrompu en français) — à restaurer puis RE-TRADUIRE :", len(broken))
    for tid, orig_id, lang, title, wp_id in broken:
        log.warning("  id=%s (WP#%s) « %s » ← original id=%s, langue cible=%s",
                    tid, wp_id, (title or "")[:50], orig_id, lang)
        if args.apply:
            conn.execute("UPDATE events_raw SET translation_of=?, translated_lang=? WHERE id=?",
                         (orig_id, lang, tid))
    if args.apply:
        conn.commit()
        log.info("=== %d lien(s) restauré(s). PROCHAINE ÉTAPE (coût API) : relancer "
                 "translate_events --retranslate <id original> --apply pour chacun, afin de "
                 "régénérer un VRAI article dans la bonne langue (protégé désormais). "
                 "Ids originaux : %s ===", len(broken), ", ".join(str(b[1]) for b in broken))
    else:
        log.info("=== Diagnostic seul : %d lien(s) seraient restaurés. Relance avec --apply. ===",
                 len(broken))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
