#!/usr/bin/env python3
"""Journal des runs d'automatisation (table `pipeline_runs`) — pour que N'IMPORTE QUELLE
session (Franck en lisant le résultat de `scripts/status_report.py`, ou une IA à qui il
colle ce même résultat) sache en un coup d'œil ce qui a tourné, quand, avec quel résultat
— sans reconstituer l'état à partir des logs éparpillés dans `logs/*.log`.

Chaque script automatisé (cron) appelle `record_run()` une fois à la fin de son `main()`.
Ne remplace PAS la table `checks` (signalements PAR ÉVÉNEMENT, déjà utilisée par
enrich.py/audit_article_quality.py/etc.) : `pipeline_runs` est au niveau DU RUN (un script,
une exécution, un résumé), `checks` est au niveau DE LA FICHE.
"""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

_DDL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script TEXT NOT NULL,
    ran_at TEXT NOT NULL DEFAULT (datetime('now')),
    ok_count INTEGER DEFAULT 0,
    warn_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    summary TEXT DEFAULT ''
)"""


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(_DDL)


def record_run(script: str, ok: int = 0, warn: int = 0, error: int = 0,
               summary: str = "", conn: sqlite3.Connection | None = None) -> None:
    """Enregistre le résultat d'UN run. Jamais bloquant : une panne d'écriture ici ne doit
    jamais faire échouer le script appelant (le reporting est secondaire au travail réel)."""
    try:
        own = conn is None
        c = conn or sqlite3.connect(DB_PATH)
        _ensure(c)
        c.execute(
            "INSERT INTO pipeline_runs (script, ok_count, warn_count, error_count, summary) "
            "VALUES (?, ?, ?, ?, ?)",
            (script, ok, warn, error, summary[:2000]))
        c.commit()
        if own:
            c.close()
    except Exception:  # noqa: BLE001 — le reporting ne doit jamais casser le run
        pass


def last_runs(limit_per_script: int = 1) -> dict[str, list[dict]]:
    """{script: [runs les plus récents d'abord]} — `limit_per_script` runs par script."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure(conn)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM pipeline_runs ORDER BY script, ran_at DESC").fetchall()]
    conn.close()
    out: dict[str, list[dict]] = {}
    for r in rows:
        bucket = out.setdefault(r["script"], [])
        if len(bucket) < limit_per_script:
            bucket.append(r)
    return out
