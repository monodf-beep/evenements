#!/usr/bin/env python3
"""Digest Slack hebdomadaire — la version « pour Franck » de scripts/status_report.py,
postée automatiquement au lieu d'avoir à se connecter pour la lire.

Usage (cron, hebdo) :
    .venv/bin/python -m scripts.weekly_digest
"""
from __future__ import annotations
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import slack
from utils import pipeline_status
from scripts.status_report import _backlog_counts, _KNOWN_SCRIPTS

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)

    lines = ["📊 *Digest hebdomadaire — Agenda Sabauda*", "", "*Automatisations :*"]
    runs = pipeline_status.last_runs(limit_per_script=1)
    for script in _KNOWN_SCRIPTS:
        entries = runs.get(script)
        if not entries:
            lines.append(f"• `{script}` : jamais exécuté")
            continue
        r = entries[0]
        icon = "✅" if not r["error_count"] else "⚠️"
        lines.append(f"• {icon} `{script}` — {r['ran_at']} "
                     f"(ok={r['ok_count']} warn={r['warn_count']} error={r['error_count']})")

    lines.append("")
    lines.append("*Reste à faire :*")
    for label, n in _backlog_counts(conn).items():
        lines.append(f"• {n} — {label}")
    conn.close()

    msg = "\n".join(lines)
    slack.notify(msg)
    pipeline_status.record_run("weekly_digest", ok=1, summary=msg[:1900])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
