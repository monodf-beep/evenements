#!/usr/bin/env python3
"""Rattrape wp_permalink_as pour les événements Agenda Sabauda publiés AVANT
l'ajout de cette colonne — nécessaire pour que le DM automatique (webhook
Instagram) puisse donner le lien précis de la fiche (voir app.webhook_instagram).

Utilise le short-link WordPress natif `?p=<id>` (fonctionne pour n'importe quel
post type, sans dépendre du REST API ni de The Events Calendar) et suit la
redirection vers l'URL réelle — lecture seule côté WordPress, aucune écriture,
aucun risque pour le site.

Usage (sur le VPS) :
    .venv/bin/python scripts/backfill_permalinks_as.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("backfill-permalinks-as")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main() -> int:
    load_dotenv(ROOT / ".env")
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    if not wp_url:
        log.error("WP_AS_URL manquant dans .env")
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, wp_post_id_as, title FROM events_raw "
        "WHERE COALESCE(wp_post_id_as,'') <> '' AND COALESCE(wp_permalink_as,'') = ''"
    ).fetchall()
    log.info("%d événement(s) sans permalien à rattraper.", len(rows))
    if not rows:
        conn.close()
        return 0

    done = 0
    for r in rows:
        shortlink = f"{wp_url}/?p={r['wp_post_id_as']}"
        title = (r["title"] or "")[:55]
        try:
            resp = requests.head(shortlink, allow_redirects=True, timeout=15)
            url = resp.url
            if resp.status_code == 200 and url and url != shortlink:
                conn.execute("UPDATE events_raw SET wp_permalink_as=? WHERE id=?", (url, r["id"]))
                conn.commit()
                done += 1
                log.info("[%s] wp#%s -> %s — %s", r["id"], r["wp_post_id_as"], url[:70], title)
            else:
                log.warning("[%s] wp#%s : pas de redirection exploitable (status=%s) — %s",
                           r["id"], r["wp_post_id_as"], resp.status_code, title)
        except requests.RequestException as exc:
            log.warning("[%s] wp#%s : erreur (%s) — %s", r["id"], r["wp_post_id_as"], exc, title)

    log.info("Terminé : %d/%d permaliens récupérés.", done, len(rows))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
