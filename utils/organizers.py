#!/usr/bin/env python3
"""Mémoire des comptes Instagram d'ORGANISATEURS — mentions automatiques dans les
légendes (utils/social.py::caption). Le handle d'un organisme n'est JAMAIS
devinable depuis son nom (sigle, abréviation...) : un agent web PROPOSE un
candidat (scripts/organizer_handles.py), Franck CONFIRME une fois dans le
back-office (/semaine), puis le handle est réutilisé silencieusement pour tous
les événements futurs du même organisateur. Rien ici n'est jamais inventé côté
publication — seul un handle status='confirmed' est renvoyé.
"""
from __future__ import annotations

import sqlite3
import unicodedata


def normalize(name: str) -> str:
    """Clé stable pour un même organisateur malgré casse/accents/espaces
    (« Théâtre  de la Ville » == « theatre de la ville »)."""
    n = unicodedata.normalize("NFKD", (name or "").strip().lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    return " ".join(n.split())


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS organizer_ig_handles (
            organisateur_key   TEXT PRIMARY KEY,
            organisateur_label TEXT,
            handle              TEXT,
            candidate           TEXT,
            evidence            TEXT,
            status              TEXT NOT NULL DEFAULT 'pending',
            checked_at          TEXT,
            confirmed_at        TEXT
        )
    """)
    conn.commit()


def confirmed_handle(conn: sqlite3.Connection, organisateur: str) -> str:
    """Handle (sans @) mémorisé et CONFIRMÉ par Franck pour cet organisateur, '' sinon
    — seul cas où utils.social.caption est autorisée à mentionner un compte."""
    key = normalize(organisateur)
    if not key:
        return ""
    row = conn.execute(
        "SELECT handle FROM organizer_ig_handles WHERE organisateur_key=? AND status='confirmed'",
        (key,)).fetchone()
    if not row:
        return ""
    handle = row["handle"] if isinstance(row, sqlite3.Row) else row[0]
    return (handle or "").lstrip("@").strip()


def pending_candidates(conn: sqlite3.Connection) -> list[dict]:
    """Candidats trouvés par l'agent web, en attente de la décision de Franck."""
    rows = conn.execute(
        "SELECT * FROM organizer_ig_handles WHERE status='pending' "
        "AND candidate IS NOT NULL AND candidate <> '' "
        "ORDER BY checked_at ASC").fetchall()
    return [dict(r) for r in rows]
