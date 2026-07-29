#!/usr/bin/env python3
"""Audit RÉTROACTIF qualité des articles déjà publiés : deux défauts concrets constatés
par Franck en relisant le site (« poltrona » laissé en italien dans un article français ;
infos pratiques — parking, navette, réservation — qui fuitent dans le CORPS au lieu de
l'encadré). Le prompt d'enrich.py interdit désormais les deux (voir scripts/enrich.py),
mais ça ne corrige pas ce qui est déjà publié. Ce script ne réécrit RIEN automatiquement
(la correction — reformuler le corps, déplacer une phrase vers l'encadré — demande une
décision rédactionnelle) : il détecte et pousse un point « à vérifier » (table `checks`,
même mécanisme que les autres audits).

Deux vérifications, purement déterministes (zéro coût API) :
  1. MOT ITALIEN laissé tel quel dans un corps par ailleurs français (liste de mots
     italiens courants qui n'ont pas leur place en français : poltrona, biglietteria…).
  2. LOGISTIQUE dans le corps (parking/navette/réservation/accessibilité…) — ce contenu
     appartient à l'encadré pratique, pas au récit.

Usage (VPS) :
    .venv/bin/python -m scripts.audit_article_quality            # liste, ne touche rien
    .venv/bin/python -m scripts.audit_article_quality --apply    # pousse les points à vérifier
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.lang import detect_lang
from scripts.scraper_events import init_db

log = get_logger("audit-article-quality")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Mots italiens courants qui n'ont AUCUNE raison de survivre dans un corps français —
# constaté en vrai : « poltrona » (fauteuil/place) laissé tel quel dans un article FR.
# Volontairement des mots DU QUOTIDIEN (billetterie, horaires…), jamais des noms propres
# (lieux, titres d'œuvres) qui peuvent légitimement rester en italien.
_IT_LOANWORDS = {
    "poltrona": "fauteuil / place", "poltrone": "fauteuils / places",
    "biglietteria": "billetterie", "biglietto": "billet", "biglietti": "billets",
    "ingresso": "entrée", "ingressi": "entrées", "ingresso gratuito": "entrée gratuite",
    "prenotazione": "réservation", "prenotazioni": "réservations",
    "orario": "horaire", "orari": "horaires", "gratuito": "gratuit", "gratuita": "gratuite",
    "chiuso": "fermé", "chiusura": "fermeture", "apertura": "ouverture",
    "posti disponibili": "places disponibles", "info e prenotazioni": "infos et réservations",
}
_IT_PAT = re.compile(r"\b(" + "|".join(re.escape(w) for w in _IT_LOANWORDS) + r")\b",
                     re.IGNORECASE | re.UNICODE)

# Logistique = matière de l'ENCADRÉ, jamais du corps (retour Franck : « pour moi ça
# devrait pas être dans l'article mais en infos complémentaires »).
_LOGISTICS_PAT = re.compile(
    r"\b(parking|navette[s]?|covoiturage|r[ée]servation obligatoire|r[ée]servez\b|"
    r"accessibilit[ée]|personnes? [àa] mobilit[ée] r[ée]duite|\bPMR\b|"
    r"billetterie ouverte|guichet[s]?)\b", re.IGNORECASE | re.UNICODE)


def _ensure_checks_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, label TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', created_at TEXT DEFAULT (datetime('now')),
        resolved_at TEXT)""")


def _flag(conn: sqlite3.Connection, event_id: int, label: str, apply_: bool) -> bool:
    already = conn.execute(
        "SELECT 1 FROM checks WHERE event_id=? AND status='pending' AND label=?",
        (event_id, label)).fetchone()
    if already:
        return False
    if apply_:
        conn.execute("INSERT INTO checks (event_id, label) VALUES (?, ?)", (event_id, label))
        conn.commit()
    return True


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Audit rétroactif qualité des articles déjà publiés.")
    parser.add_argument("--apply", action="store_true", help="Pousse les points à vérifier (sinon liste seule).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _ensure_checks_table(conn)

    rows = conn.execute(
        "SELECT id, title, territoire, translated_lang, enrich_data FROM events_raw "
        "WHERE COALESCE(wp_post_id_as,0) > 0 AND duplicate_of IS NULL "
        "AND COALESCE(enrich_data,'') <> ''").fetchall()
    log.info("%d article(s) publié(s) à auditer.", len(rows))

    suspects = 0
    pushed = 0
    for r in rows:
        r = dict(r)
        try:
            art = (json.loads(r["enrich_data"]) or {}).get("article") or {}
        except (ValueError, TypeError):
            continue
        corps = art.get("corps") or ""
        encadre = art.get("encadre") or ""
        if not corps:
            continue
        # Langue attendue de CE côté (fiche traduite en it → l'italien y est légitime).
        expected = (r.get("translated_lang") or "fr").strip() or "fr"

        problems = []
        if expected != "it":
            hits = sorted({m.group(0).lower() for m in _IT_PAT.finditer(corps)})
            if hits:
                problems.append(f"mot(s) italien(s) laissé(s) dans le corps français : "
                                 f"{', '.join(hits)} (à traduire : "
                                 f"{', '.join(_IT_LOANWORDS.get(h, h) for h in hits)})")

        log_hits = sorted({m.group(0).lower() for m in _LOGISTICS_PAT.finditer(corps)})
        if log_hits:
            problems.append(f"logistique dans le corps (devrait être dans l'encadré) : "
                             f"{', '.join(log_hits)}")

        if not problems:
            continue
        suspects += 1
        label = ("Audit rétroactif qualité article : " + " ; ".join(problems) +
                 f" — « {(r.get('title') or '')[:50]} »")
        log.warning("[%s] %s", r["id"], " ; ".join(problems))
        if _flag(conn, r["id"], label, args.apply):
            pushed += 1

    if args.apply:
        log.info("=== Audit terminé : %d suspect(s) / %d article(s), %d point(s) poussé(s) dans `checks`. ===",
                  suspects, len(rows), pushed)
    else:
        log.info("=== Audit terminé (diagnostic seul) : %d suspect(s) / %d article(s). "
                  "Relance avec --apply pour pousser les points à vérifier. ===", suspects, len(rows))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
