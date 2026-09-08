#!/usr/bin/env python3
"""Rappel Slack hebdomadaire pour la session « Cette semaine » (demande de Franck :
un créneau de travail régulier, avec un rappel plutôt qu'un oubli silencieux).

Volontairement SIMPLE pour commencer (pas d'intégration calendrier live) : un
message Slack, le compte exact de tâches en attente (le MÊME calcul que la page
/semaine — utils.semaine, un seul endroit) + ce qui a déjà été traité les 7
derniers jours, pour le petit effet de progression.

Cron suggéré (pas quotidien — c'est un rappel de SESSION, pas une alerte) :
    0 9 * * 1  cd /root/evenements && .venv/bin/python3 -m scripts.semaine_reminder >> logs/semaine_reminder.log 2>&1

Usage :
    .venv/bin/python3 -m scripts.semaine_reminder
    .venv/bin/python3 -m scripts.semaine_reminder --dry-run
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import semaine as semaine_mod
from utils import slack

log = get_logger("semaine_reminder")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
_KIND_LABEL = {"photo": "photo(s)", "texte": "texte(s)",
              "organisateur": "compte(s) Instagram à confirmer", "instagram-manuel": "post(s) à finir"}


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Rappel Slack hebdomadaire pour /semaine.")
    parser.add_argument("--dry-run", action="store_true", help="Affiche le message sans l'envoyer.")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    all_tasks = semaine_mod.tasks(conn)
    counts: dict[str, int] = {}
    for t in all_tasks:
        counts[t["kind"]] = counts.get(t["kind"], 0) + 1

    since = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")
    done_week = conn.execute(
        "SELECT (SELECT COUNT(*) FROM events_raw WHERE image_reviewed_at >= ?) + "
        "(SELECT COUNT(*) FROM events_raw WHERE text_reviewed_at >= ?) n",
        (since, since)).fetchone()["n"]
    conn.close()

    base = (os.getenv("BACKOFFICE_BASE_URL") or "").rstrip("/")
    lien = f"{base}/semaine" if base else "/semaine"
    total = len(all_tasks)

    if total == 0:
        text = (f"🎉 *Cette semaine* — tout est à jour, rien en attente. "
                f"({done_week} traité(s) ces 7 derniers jours.)")
    else:
        detail = " · ".join(f"{n} {_KIND_LABEL.get(k, k)}" for k, n in sorted(counts.items()))
        text = (f"🗓️ *C'est l'heure de la session hebdo* — {total} tâche(s) t'attendent "
                f"sur <{lien}|Cette semaine> : {detail}.\n"
                f"Déjà traité ces 7 derniers jours : {done_week}.")

    log.info(text.replace("\n", " "))
    if args.dry_run:
        print(text)
        return 0
    slack.notify(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
