#!/usr/bin/env python3
"""Rattrape wp_permalink_as pour les événements Agenda Sabauda publiés AVANT
l'ajout de cette colonne — nécessaire pour que le DM automatique (webhook
Instagram) puisse donner le lien précis de la fiche (voir app.webhook_instagram).

Utilise le short-link WordPress natif `?p=<id>` (fonctionne pour n'importe quel
post type, sans dépendre du REST API ni de The Events Calendar) et suit la
redirection vers l'URL réelle — lecture seule côté WordPress, aucune écriture,
aucun risque pour le site.

Retry (3 tentatives, backoff court) sur les échecs RÉSEAU/5xx transitoires — sans
ça, un aléa ponctuel se confond avec un post réellement supprimé. Un 404 franc,
lui, n'est jamais retenté (le post n'existe plus côté WordPress, pas la peine
d'insister) — catégorisé séparément dans le résumé final pour distinguer
« à réessayer plus tard » de « probablement supprimé, action éditoriale à toi ».

Usage (sur le VPS) :
    .venv/bin/python scripts/backfill_permalinks_as.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("backfill-permalinks-as")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _resolve(shortlink: str, retries: int = 2):
    """Suit la redirection. Renvoie (url, status_code) — url='' si rien d'exploitable
    après les tentatives. Ne retente PAS un 404 (définitif), seulement réseau/5xx."""
    status = None
    for attempt in range(retries + 1):
        try:
            resp = requests.head(shortlink, allow_redirects=True, timeout=15)
            status = resp.status_code
            if status == 200 and resp.url and resp.url != shortlink:
                return resp.url, status
            if status == 404:
                return "", status  # définitif : le post n'existe plus
        except requests.RequestException:
            status = None
        if attempt < retries:
            time.sleep(3 * (attempt + 1))
    return "", status


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
    gone: list[tuple[int, str]] = []       # 404 franc : post probablement supprimé côté WP
    unresolved: list[tuple[int, str]] = []  # échec réseau/5xx persistant malgré le retry
    for r in rows:
        shortlink = f"{wp_url}/?p={r['wp_post_id_as']}"
        title = (r["title"] or "")[:55]
        url, status = _resolve(shortlink)
        if url:
            conn.execute("UPDATE events_raw SET wp_permalink_as=? WHERE id=?", (url, r["id"]))
            conn.commit()
            done += 1
            log.info("[%s] wp#%s -> %s — %s", r["id"], r["wp_post_id_as"], url[:70], title)
        elif status == 404:
            gone.append((r["id"], title))
            log.warning("[%s] wp#%s : 404 — post probablement supprimé côté WordPress — %s",
                       r["id"], r["wp_post_id_as"], title)
        else:
            unresolved.append((r["id"], title))
            log.warning("[%s] wp#%s : pas de redirection exploitable après retry (status=%s) — %s",
                       r["id"], r["wp_post_id_as"], status, title)

    log.info("Terminé : %d/%d permaliens récupérés · %d probablement supprimés (404) · "
             "%d à réessayer plus tard.", done, len(rows), len(gone), len(unresolved))
    if gone:
        log.info("Supprimés côté WP (id backoffice) : %s", ", ".join(str(i) for i, _ in gone))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
