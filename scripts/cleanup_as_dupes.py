#!/usr/bin/env python3
"""Détecte et met à la CORBEILLE les DOUBLONS d'événements CÔTÉ WORDPRESS.

L'audit base (cleanup_as_audit) ne voit que les doublons tracés `duplicate_of`.
Or il reste des doublons NÉS DANS WORDPRESS : même événement poussé deux fois
(ex. « Palazzo D'Oria » en double). Ici on interroge WordPress (route cs/v1/list),
on regroupe par TITRE normalisé + DATE de début, et pour chaque groupe on GARDE
le meilleur exemplaire, on envoie les autres à la corbeille (RÉVERSIBLE).

Choix de l'exemplaire gardé :
  1. un exemplaire PUBLIÉ (jamais touché) l'emporte ;
  2. sinon, le plus complet (lieu + image), puis le plus ancien (id le plus bas).

Prérequis : snippet deploy/wordpress/cs-trash.php installé (routes cs/v1/list + trash).
DRY-RUN par défaut ; --execute pour agir.

Exemples :
  .venv/bin/python3 -m scripts.cleanup_as_dupes
  .venv/bin/python3 -m scripts.cleanup_as_dupes --execute
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.publisher_as import _headers, _norm
from scripts.cleanup_as_trash import trash_one

log = get_logger("cleanup_as_dupes")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _key(ev: dict) -> str:
    """Clé de doublon : titre normalisé + date (jour) de début."""
    title = _norm(ev.get("title", ""))[:90]
    start = (ev.get("start") or "")[:10]   # 'Y-m-d' de '_EventStartDate'
    return f"{title}|{start}"


def _keep_score(ev: dict) -> tuple:
    """Plus grand = meilleur à GARDER : publié > (lieu+image) > ancien (id bas)."""
    published = 1 if ev.get("status") in ("publish", "private") else 0
    completeness = (1 if ev.get("venue") else 0) + (1 if ev.get("thumb") else 0)
    return (published, completeness, -int(ev.get("id", 0)))


def fetch_list(wp_url: str, auth) -> list[dict]:
    endpoint = f"{wp_url}/?rest_route=/cs/v1/list"
    resp = requests.get(endpoint, auth=auth, headers=_headers(auth), timeout=60)
    resp.raise_for_status()
    return resp.json()


def find_duplicates(events: list[dict]) -> list[dict]:
    """Renvoie la liste des exemplaires À METTRE À LA CORBEILLE (les non-gardés)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        groups[_key(ev)].append(ev)
    to_trash: list[dict] = []
    for key, grp in groups.items():
        if len(grp) < 2:
            continue
        grp_sorted = sorted(grp, key=_keep_score, reverse=True)
        keep = grp_sorted[0]
        for dup in grp_sorted[1:]:
            # On ne met JAMAIS à la corbeille un exemplaire publié.
            if dup.get("status") in ("publish", "private"):
                continue
            dup["_keep_id"] = keep["id"]
            to_trash.append(dup)
    return to_trash


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Ménage des doublons WordPress (corbeille, réversible).")
    p.add_argument("--execute", action="store_true", help="Agir réellement (sinon DRY-RUN).")
    p.add_argument("--cap", type=int, default=200, help="Nombre max de doublons traités.")
    p.add_argument("--delay", type=float, default=0.4, help="Pause (s) entre deux appels.")
    args = p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    if not all([wp_url, auth[0], auth[1]]):
        log.error("WP_AS_URL/USER/APP_PASSWORD manquants.")
        return 1

    try:
        events = fetch_list(wp_url, auth)
    except (requests.RequestException, ValueError) as exc:
        log.error("Inventaire WordPress impossible (cs/v1/list installé ?) : %s", exc)
        return 1
    log.info("Inventaire WordPress : %d événement(s)", len(events))

    to_trash = find_duplicates(events)[:args.cap]
    mode = "EXÉCUTION" if args.execute else "DRY-RUN (rien ne bouge)"
    print(f"\nDoublons WordPress — {mode} · {len(to_trash)} exemplaire(s) en trop\n")
    for r in to_trash:
        print(f"  corbeille WP#{r['id']:>5} ({r['status']}) « {r['title'][:60]} » "
              f"→ on garde WP#{r['_keep_id']}")
    if not to_trash:
        print("Aucun doublon détecté. 🎉")
        return 0
    if not args.execute:
        print(f"\nDRY-RUN : {len(to_trash)} seraient mis à la corbeille. "
              "Relance avec --execute pour agir.")
        return 0

    conn = sqlite3.connect(DB_PATH)
    ok = fail = 0
    for i, r in enumerate(to_trash, 1):
        if trash_one(wp_url, auth, r["id"]):
            # Si un événement de la base pointait ce brouillon, on le délie.
            conn.execute("UPDATE events_raw SET wp_post_id_as=NULL, published_as_date=NULL "
                         "WHERE wp_post_id_as=?", (r["id"],))
            conn.commit()
            ok += 1
        else:
            fail += 1
        if args.delay and i < len(to_trash):
            time.sleep(args.delay)
    conn.close()
    print(f"\n=== Doublons : {ok} à la corbeille, {fail} échec(s) ===")
    print("Réversible : Événements → Corbeille dans WordPress.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
