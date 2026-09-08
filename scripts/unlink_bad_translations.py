#!/usr/bin/env python3
"""Répare les 72 paires FR/IT signalées par `audit_translation_langs` : dans TOUS les cas
détectés (doublon probable ou à re-traduire), le lien translation_of/translated_lang
actuel est FAUX (les deux côtés sont dans la même langue réelle) — le DÉLIER est donc
toujours la correction sûre, quel que soit le sous-cas : ça ne supprime aucun contenu, ne
consomme aucune API, et est réversible (un vrai jumelage/une vraie traduction pourra être
refaite plus tard, proprement, avec translate_events / link_translations_as corrigés).

Ce script traite les points ouverts dans `checks` poussés par audit_translation_langs.py
(préfixe « Audit rétroactif jumelage FR/IT »— reconnaît les deux classifications) :
  - efface translation_of/translated_lang sur la fiche « traduction » ;
  - marque le point `checks` résolu (le problème signalé est corrigé).

LIMITE IMPORTANTE (à savoir avant --apply) : ceci ne touche que la base SQLite. Le lien
Polylang côté WordPress (le sélecteur de langue qui connecte les deux articles sur le
site) N'EST PAS défait ici — cs-polylang.php n'expose pas encore de route de déliaison.
Les deux fiches resteront visuellement liées sur le site jusqu'à un correctif WP séparé
(à déployer avec prudence, comme d'habitude, via Novamira). Ce script prépare le terrain
côté données ; il ne prétend pas nettoyer le site public à lui seul.

Usage (VPS) :
    .venv/bin/python -m scripts.unlink_bad_translations            # liste, ne touche rien
    .venv/bin/python -m scripts.unlink_bad_translations --apply    # délie + résout les points
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

log = get_logger("unlink-bad-translations")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
_LABEL_PREFIX = "Audit rétroactif jumelage FR/IT"


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Délie les paires FR/IT signalées par audit_translation_langs.")
    parser.add_argument("--apply", action="store_true", help="Délie réellement (sinon liste seule).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    points = conn.execute(
        "SELECT id, event_id, label FROM checks WHERE status='pending' AND label LIKE ?",
        (_LABEL_PREFIX + "%",)).fetchall()
    log.info("%d point(s) « à vérifier » de ce type, ouverts.", len(points))

    unlinked = 0
    for p in points:
        ev = conn.execute("SELECT id, title, translation_of, translated_lang, wp_post_id_as "
                          "FROM events_raw WHERE id=?", (p["event_id"],)).fetchone()
        if not ev or not ev["translation_of"]:
            continue  # déjà délié entre-temps (ex. par 2387/4122)
        log.warning("[%s] « %s » (WP#%s) : délie de l'original id=%s", ev["id"],
                    (ev["title"] or "")[:50], ev["wp_post_id_as"], ev["translation_of"])
        if args.apply:
            conn.execute("UPDATE events_raw SET translation_of=NULL, translated_lang=NULL WHERE id=?",
                         (ev["id"],))
            conn.execute("UPDATE checks SET status='resolved', resolved_at=datetime('now') WHERE id=?",
                         (p["id"],))
            conn.commit()
        unlinked += 1

    if args.apply:
        log.info("=== %d fiche(s) déliée(s) côté base. RAPPEL : le lien Polylang côté WordPress "
                  "(sélecteur de langue sur le site) n'est PAS encore défait — correctif WP séparé "
                  "à prévoir. ===", unlinked)
    else:
        log.info("=== Diagnostic seul : %d fiche(s) seraient déliées. Relance avec --apply. ===", unlinked)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
