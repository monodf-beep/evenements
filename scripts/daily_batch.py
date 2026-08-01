#!/usr/bin/env python3
"""Automatise le PROTOCOLE DE LOT (docs/BACKLOG.md, 2026-08-01) : sélectionne un lot
d'événements, les enrichit, vérifie CHACUN avec les mêmes règles que
`scripts/batch_report.py`, ne publie QUE ceux qui sont COMPLETS, et notifie Slack —
pour que le protocole tourne seul au lieu d'être déroulé à la main sur le VPS.

Rien n'est publié à moitié fait : un événement qui reste INCOMPLET (score/article/
panel/date manquant) est laissé en base tel quel, il retentera au prochain run
(cap quotidien, mode auto : score bas → court, score haut/matière officielle →
long+panel, cf. scripts/enrich.py). Slack liste les incomplets avec la RAISON
précise, pour que Franck sache s'il doit intervenir sans avoir à se connecter.

Usage (cron) :
    .venv/bin/python -m scripts.daily_batch                # lot du jour (DAILY_BATCH_SIZE)
    .venv/bin/python -m scripts.daily_batch --cap 5         # override ponctuel
"""
from __future__ import annotations
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import slack
from scripts.enrich import select_events, main as enrich_main
from scripts.batch_report import _row_report
from scripts.publish_batch_as import main as publish_main

log = get_logger("daily_batch")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
DAILY_BATCH_SIZE = int(os.getenv("DAILY_BATCH_SIZE", "10"))


def _fetch(conn: sqlite3.Connection, ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    return {r["id"]: dict(r) for r in
            conn.execute(f"SELECT * FROM events_raw WHERE id IN ({ph})", ids).fetchall()}


def main(argv: list[str]) -> int:
    load_dotenv(ROOT / ".env")
    cap = DAILY_BATCH_SIZE
    if "--cap" in argv:
        try:
            cap = int(argv[argv.index("--cap") + 1])
        except (IndexError, ValueError):
            pass

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = select_events(conn, [], "", "")
    conn.close()
    ids = [r["id"] for r in rows][:cap]

    if not ids:
        log.info("Lot du jour : rien à enrichir (file vide sous le seuil MIN_SCORE).")
        slack.notify("📭 Lot quotidien : rien à enrichir aujourd'hui (file vide).")
        return 0

    log.info("Lot du jour : %d id(s) sélectionné(s) : %s", len(ids), ids)
    enrich_main([str(i) for i in ids])

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    events = _fetch(conn, ids)
    conn.close()

    complet, incomplet = [], []
    for i in ids:
        ev = events.get(i)
        if not ev:
            incomplet.append((i, "— introuvable en base —", ["  ✗ disparu de la base"]))
            continue
        ok, lines = _row_report(ev)
        (complet if ok else incomplet).append((i, ev.get("title") or "", lines))

    log.info("Lot du jour : %d complet(s), %d incomplet(s) avant publication",
             len(complet), len(incomplet))

    published_lines = []
    if complet:
        publish_main(["--ids", *[str(i) for i, _, _ in complet]])
        # Re-vérification POST-publication (image réelle + wp id désormais posés).
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        events2 = _fetch(conn, [i for i, _, _ in complet])
        conn.close()
        for i, title, _ in complet:
            ev2 = events2.get(i) or {}
            ok2, lines2 = _row_report(ev2)
            wp_id = ev2.get("wp_post_id_as")
            if ok2:
                published_lines.append(f"✅ [{i}] {title[:60]} — WP#{wp_id}")
            else:
                # Publié mais un contrôle post-publication a quand même échoué
                # (ex. échec réseau au push) : signalé, pas silencieux.
                bad = "; ".join(l.strip() for l in lines2 if l.strip().startswith("✗"))
                published_lines.append(f"⚠️ [{i}] {title[:60]} — WP#{wp_id} mais {bad}")

    incomplet_lines = []
    for i, title, lines in incomplet:
        reasons = "; ".join(l.strip() for l in lines if l.strip().startswith("✗"))
        incomplet_lines.append(f"⏳ [{i}] {title[:60]} — {reasons or 'incomplet'}")

    msg = (f"📰 *Lot quotidien Agenda Sabauda* — {len(complet)} publié(s), "
           f"{len(incomplet)} laissé(s) pour un prochain run\n")
    if published_lines:
        msg += "\n".join(published_lines) + "\n"
    if incomplet_lines:
        msg += "\n" + "\n".join(incomplet_lines)
    slack.notify(msg)
    log.info("=== Lot quotidien terminé : %d publié(s), %d laissé(s) incomplet(s) ===",
             len(complet), len(incomplet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
