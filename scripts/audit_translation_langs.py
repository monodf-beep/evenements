#!/usr/bin/env python3
"""Audit RÉTROACTIF des paires FR/IT déjà publiées : la langue assignée (translated_lang,
Polylang) correspond-elle à la langue RÉELLE de l'article déjà rédigé ?

Contexte : le bug corrigé sur l'événement 2387 (translate_events.py / link_translations_as.py
ne décidaient la langue que sur le TITRE brut scrapé, jamais sur l'article réellement rédigé —
qui peut être français même pour une source au titre italien, scripts.enrich écrivant toujours
en français par défaut) a pu produire d'AUTRES paires mal étiquetées AVANT le correctif. Ce
script ne re-répare rien automatiquement (chaque cas demande une décision différente : re-
traduire ? délier ? juste corriger le libellé ?) — il liste les paires suspectes et pousse un
point « à vérifier » (table `checks`, même mécanisme que enrich.py et link_translations_as.py).

Zéro coût API : uniquement de la lecture DB + utils.lang.effective_lang (déterministe).

Usage (VPS) :
    .venv/bin/python -m scripts.audit_translation_langs            # liste, ne touche rien
    .venv/bin/python -m scripts.audit_translation_langs --apply    # pousse les points à vérifier
"""
from __future__ import annotations
import argparse
import difflib
import json
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.lang import effective_lang
from scripts.scraper_events import init_db

log = get_logger("audit-translation-langs")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _ensure_checks_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, label TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', created_at TEXT DEFAULT (datetime('now')),
        resolved_at TEXT)""")


def _corps(row: dict) -> str:
    if not row.get("enrich_data"):
        return ""
    try:
        return ((json.loads(row["enrich_data"]) or {}).get("article") or {}).get("corps") or ""
    except (ValueError, TypeError):
        return ""


def _classify(src: dict, t: dict) -> str:
    """Regroupe chaque paire suspecte en une action : comparer le CORPS (pas juste le
    titre, souvent proche même sur deux événements différents) tranche entre « même texte
    republié dans l'autre langue par erreur » (à fusionner/délier) et « vrai contenu
    distinct mal étiqueté » (à re-traduire)."""
    a, b = _corps(src), _corps(t)
    if not a or not b:
        return "DOUBLON PROBABLE (à fusionner/délier)"  # rien à comparer : prudence
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return ("DOUBLON PROBABLE (à fusionner/délier)" if ratio >= 0.6
            else "À RE-TRADUIRE (contenu distinct, mauvaise langue)")


_LABEL_PREFIX = "Audit rétroactif jumelage FR/IT"


def _flag(conn: sqlite3.Connection, event_id: int, label: str, apply_: bool) -> bool:
    # Préfixe stable (pas le libellé exact) : une classification qui change d'un run à
    # l'autre (le CORPS a bougé entre-temps) MET À JOUR le point existant au lieu de le
    # dupliquer à côté de l'ancien.
    existing = conn.execute(
        "SELECT id, label FROM checks WHERE event_id=? AND status='pending' AND label LIKE ?",
        (event_id, _LABEL_PREFIX + "%")).fetchone()
    if existing:
        if existing["label"] == label:
            return False
        if apply_:
            conn.execute("UPDATE checks SET label=? WHERE id=?", (label, existing["id"]))
            conn.commit()
        return True
    if apply_:
        conn.execute("INSERT INTO checks (event_id, label) VALUES (?, ?)", (event_id, label))
        conn.commit()
    return True


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Audit rétroactif langue des paires FR/IT déjà publiées.")
    parser.add_argument("--apply", action="store_true", help="Pousse les points à vérifier (sinon liste seule).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _ensure_checks_table(conn)

    pairs = conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(translation_of,0) > 0 "
        "AND COALESCE(wp_post_id_as,0) > 0").fetchall()
    log.info("%d paire(s) FR/IT publiée(s) à auditer.", len(pairs))

    suspects = 0
    pushed = 0
    buckets: dict[str, list] = {}
    for t in pairs:
        t = dict(t)
        src_row = conn.execute("SELECT * FROM events_raw WHERE id=?", (t["translation_of"],)).fetchone()
        if not src_row:
            continue
        src = dict(src_row)
        tgt_lang = (t.get("translated_lang") or "").strip()
        found_tgt = effective_lang(t)
        found_src = effective_lang(src)
        problems = []
        if tgt_lang and found_tgt != tgt_lang:
            problems.append(f"traduction id={t['id']} étiquetée « {tgt_lang} » mais article "
                             f"détecté « {found_tgt} »")
        if found_src == found_tgt:
            problems.append(f"original id={src['id']} et traduction id={t['id']} détectés "
                             f"dans la MÊME langue « {found_src} » (quasi-doublon possible)")
        if not problems:
            continue
        suspects += 1
        classification = _classify(src, t)
        label = (f"Audit rétroactif jumelage FR/IT [{classification}] : " + " ; ".join(problems) +
                 f" — original « {(src.get('title') or '')[:45]}» (WP#{src.get('wp_post_id_as')}), "
                 f"traduction WP#{t.get('wp_post_id_as')}.")
        log.warning("[%s ↔ %s] %s | %s", src["id"], t["id"], classification, " ; ".join(problems))
        buckets.setdefault(classification, []).append((src["id"], t["id"]))
        if _flag(conn, t["id"], label, args.apply):
            pushed += 1

    for cls, items in buckets.items():
        log.info("  %s : %d paire(s) — ids traduction : %s", cls, len(items),
                 ", ".join(str(i[1]) for i in items))

    if args.apply:
        log.info("=== Audit terminé : %d suspect(s) / %d paire(s), %d point(s) poussé(s) dans `checks`. ===",
                  suspects, len(pairs), pushed)
    else:
        log.info("=== Audit terminé (diagnostic seul) : %d suspect(s) / %d paire(s). "
                  "Relance avec --apply pour pousser les points à vérifier. ===", suspects, len(pairs))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
