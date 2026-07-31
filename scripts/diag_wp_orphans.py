#!/usr/bin/env python3
"""Diagnostic LECTURE SEULE (aucune écriture WP ni base) sur 3 anomalies trouvées en
session : 5 WP#id orphelins, un lien wp_post_id_as cassé, une incohérence de titre.

Source principale : cs/v1/list (deploy/wordpress/cs-trash.php) — un seul appel réseau,
mais NE renvoie PAS les posts en CORBEILLE (post_status filtré côté PHP). Pour un id
absent de la liste, on retente via wp/v2/tribe_events/<id>?context=edit — route standard
WP core générée automatiquement dès qu'un CPT est show_in_rest=true (c'est le cas : la
liste de scripts/relink_wp_ids_as.py interroge déjà wp/v2/tribe_events avec succès) — elle
fait get_post() sans filtrer par statut, donc capable de révéler un post en trash là où
cs/v1/list ne peut que le taire.

Usage (sur le VPS, où .env est renseigné) :
    .venv/bin/python -m scripts.diag_wp_orphans
"""
from __future__ import annotations
import argparse
import difflib
import html
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.publisher_as import _headers
from scripts.cleanup_as_dupes import fetch_list

log = get_logger("diag_wp_orphans")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# 5 WP#id (WordPress) sans aucune ligne locale à wp_post_id_as correspondant.
TARGET_ORPHAN_WP_IDS = [1674, 1677, 1680, 2232, 4113]
# Lien cassé : id LOCAL 4199 avait wp_post_id_as=4121 ce matin, NULL quelques heures après.
LOCAL_ID_BROKEN_LINK, WP_ID_BROKEN_LINK = 4199, 4121
# Incohérence titre : id LOCAL 4113 → wp_post_id_as=3713 (attention : 4113 apparaît aussi
# ci-dessus comme WP#id orphelin — pure coïncidence numérique, deux entités DIFFÉRENTES :
# ici c'est un id de la base LOCALE, pas un WP#id).
LOCAL_ID_MISMATCH, WP_ID_MISMATCH = 4113, 3713
FUZZY_THRESHOLD = 0.55


def _norm_title(s: str) -> str:
    """Normalisation pour rapprochement flou : entités décodées, sans accents,
    minuscules, ponctuation aplatie."""
    t = html.unescape(s or "")
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def fetch_single(wp_url: str, auth, wp_id: int) -> dict:
    """GET wp/v2/tribe_events/<id> — voit un post quel que soit son statut (dont trash)
    si l'utilisateur authentifié en a le droit. found=True/False/None (None=erreur, pas
    de conclusion possible)."""
    endpoint = f"{wp_url}/wp-json/wp/v2/tribe_events/{wp_id}"
    try:
        resp = requests.get(endpoint, params={"context": "edit"}, auth=auth,
                            headers=_headers(auth), timeout=30)
    except requests.RequestException as exc:
        return {"id": wp_id, "found": None, "status": None, "title": None,
                "note": f"injoignable : {exc}"}
    if resp.status_code == 404:
        return {"id": wp_id, "found": False, "status": None, "title": None, "note": ""}
    try:
        resp.raise_for_status()
        data = resp.json()
    except (requests.HTTPError, ValueError) as exc:
        return {"id": wp_id, "found": None, "status": None, "title": None,
                "note": f"erreur ({resp.status_code}) : {str(exc)[:150]}"}
    title = html.unescape(((data.get("title") or {}).get("rendered") or "").strip())
    return {"id": wp_id, "found": True, "status": data.get("status"), "title": title, "note": ""}


def lookup(wp_id: int, by_id: dict, wp_url: str, auth) -> dict:
    """cs/v1/list d'abord (déjà en mémoire) ; sinon repli sur l'appel individuel —
    seul moyen de voir un post passé en CORBEILLE (absent de cs/v1/list par construction)."""
    if wp_id in by_id:
        ev = by_id[wp_id]
        return {"id": wp_id, "found": True, "status": ev.get("status"),
                "title": ev.get("title") or "", "note": "vu via cs/v1/list"}
    r = fetch_single(wp_url, auth, wp_id)
    if r["found"] is True:
        r["note"] = "absent de cs/v1/list → probablement en CORBEILLE (vu via wp/v2/tribe_events/<id>)"
    elif r["found"] is False:
        r["note"] = ("absent de cs/v1/list ET 404 sur wp/v2/tribe_events/<id> — probablement "
                     "supprimé définitivement (ou route REST par id indisponible : à vérifier "
                     "à la main en cas de doute)")
    return r


def fuzzy_candidates(conn: sqlite3.Connection, wp_title: str, top_n: int = 3,
                     threshold: float = FUZZY_THRESHOLD) -> list[tuple]:
    """Lignes locales dont le titre ressemble à `wp_title` (SequenceMatcher, stdlib)."""
    if not wp_title:
        return []
    target = _norm_title(wp_title)
    rows = conn.execute("SELECT id, title, wp_post_id_as FROM events_raw "
                        "WHERE COALESCE(title,'') <> ''").fetchall()
    scored = []
    for r in rows:
        ratio = difflib.SequenceMatcher(None, target, _norm_title(r["title"])).ratio()
        if ratio >= threshold:
            scored.append((ratio, r["id"], r["title"], r["wp_post_id_as"]))
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[:top_n]


def _print_lookup(wp_id: int, r: dict, conn: sqlite3.Connection | None = None) -> None:
    if r["found"] is True:
        print(f"  WP#{wp_id} · statut={r['status']} · « {r['title']} »  ({r['note']})")
        if conn is not None:
            for ratio, local_id, local_title, cur_wp in fuzzy_candidates(conn, r["title"]):
                lien = f"wp_post_id_as={cur_wp}" if cur_wp else "wp_post_id_as=NULL"
                print(f"      ↳ candidat local id={local_id} ({lien}) "
                     f"similarité={ratio:.2f} « {local_title} »")
    elif r["found"] is False:
        print(f"  WP#{wp_id} · INTROUVABLE (404) — probablement supprimé définitivement côté WordPress.")
    else:
        print(f"  WP#{wp_id} · ERREUR : {r['note']}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Diagnostic lecture seule : WP#id orphelins, lien cassé, incohérence de titre.")
    p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    if not all([wp_url, auth[0], auth[1]]):
        log.error("WP_AS_URL/WP_AS_USER/WP_AS_APP_PASSWORD manquants dans .env — abandon.")
        return 1

    try:
        events = fetch_list(wp_url, auth)
        by_id = {e["id"]: e for e in events}
        log.info("Inventaire WordPress (cs/v1/list) : %d événement(s) hors corbeille.", len(events))
    except (requests.RequestException, ValueError) as exc:
        log.error("cs/v1/list indisponible (%s) — repli à 100%% sur wp/v2/tribe_events/<id>.", exc)
        by_id = {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print(f"\n{'='*76}")
    print(f"DIAGNOSTIC WP ORPHELINS — Agenda Sabauda ({wp_url or 'WP_AS_URL non configurée'})")
    print(f"{'='*76}")

    print("\n① 5 WP#id orphelins (aucune ligne locale avec ce wp_post_id_as)\n")
    for wp_id in TARGET_ORPHAN_WP_IDS:
        _print_lookup(wp_id, lookup(wp_id, by_id, wp_url, auth), conn)

    print(f"\n② Lien cassé : id local {LOCAL_ID_BROKEN_LINK} avait "
          f"wp_post_id_as={WP_ID_BROKEN_LINK} ce matin (07:56), NULL à 08:39\n")
    local = conn.execute("SELECT id, title, wp_post_id_as FROM events_raw WHERE id=?",
                         (LOCAL_ID_BROKEN_LINK,)).fetchone()
    if local:
        print(f"  État local actuel : id={local['id']} wp_post_id_as={local['wp_post_id_as']} "
              f"« {(local['title'] or '')[:70]} »")
    else:
        print(f"  id local {LOCAL_ID_BROKEN_LINK} introuvable en base.")
    _print_lookup(WP_ID_BROKEN_LINK, lookup(WP_ID_BROKEN_LINK, by_id, wp_url, auth))

    print(f"\n③ Cohérence titre : id local {LOCAL_ID_MISMATCH} → "
          f"wp_post_id_as={WP_ID_MISMATCH}\n")
    row = conn.execute("SELECT title FROM events_raw WHERE id=?",
                       (LOCAL_ID_MISMATCH,)).fetchone()
    local_title = (row["title"] if row else "") or ""
    print(f"  Titre stocké en local (id={LOCAL_ID_MISMATCH}) : « {local_title[:90]} »")
    r = lookup(WP_ID_MISMATCH, by_id, wp_url, auth)
    if r["found"] is True:
        ratio = difflib.SequenceMatcher(None, _norm_title(local_title), _norm_title(r["title"])).ratio()
        verdict = ("COHÉRENT (le titre correspond désormais)" if ratio > 0.8 else
                  "TOUJOURS INCOHÉRENT — à investiguer (doublon d'un même wp_post_id_as ?)")
        print(f"  Titre ACTUEL sur WP#{WP_ID_MISMATCH} : « {r['title']} » · statut={r['status']} "
              f"· similarité={ratio:.2f} → {verdict}")
    else:
        _print_lookup(WP_ID_MISMATCH, r)

    conn.close()
    print(f"\n{'='*76}")
    print("Fin du diagnostic — lecture seule, rien n'a été modifié.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
