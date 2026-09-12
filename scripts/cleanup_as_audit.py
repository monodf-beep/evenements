#!/usr/bin/env python3
"""AUDIT (lecture seule) du ménage à faire sur Agenda Sabauda (agendasabauda.eu).

Ne modifie RIEN — ni la base, ni WordPress. Il liste, depuis notre base, les
événements DÉJÀ POUSSÉS sur l'agenda (wp_post_id_as renseigné) qui n'auraient pas
dû y être, en trois catégories :

  1. INCOMPLETS  — poussés avant la porte qualité, il leur manque un champ
                   obligatoire (date, lieu, ville, territoire, catégorie, image).
  2. DOUBLONS    — marqués duplicate_of (fusionnés après coup) mais restés sur
                   l'agenda avec leur propre brouillon.
  3. PASSÉS      — dont la date de fin est révolue (ne devraient plus être exposés).

Pour chacun : id interne, wp_post_id_as, titre, et le lien d'édition WordPress
(pour vérifier / supprimer à la main si tu veux). La suppression automatisée
(corbeille WordPress, réversible) fera l'objet d'un second outil, APRÈS ta
validation de ces listes.

Usage :
  .venv/bin/python3 -m scripts.cleanup_as_audit
  .venv/bin/python3 -m scripts.cleanup_as_audit --limit 200
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import completeness as comp

log = get_logger("cleanup_as_audit")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _edit_url(base: str, wp_id) -> str:
    return f"{base}/wp-admin/post.php?post={wp_id}&action=edit" if base and wp_id else ""


def _row(ev: dict, base: str, reason: str) -> dict:
    return {
        "id":       ev["id"],
        "wp":       ev.get("wp_post_id_as"),
        "title":    (ev.get("title") or "")[:70],
        "date":     ev.get("date_event_start") or "—",
        "reason":   reason,
        "edit_url": _edit_url(base, ev.get("wp_post_id_as")),
    }


def audit(conn, today: str, base: str, limit: int) -> dict:
    conn.row_factory = sqlite3.Row
    pushed = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]

    incomplets, doublons, passes = [], [], []
    seen = set()
    for ev in pushed:
        wp = ev.get("wp_post_id_as")
        # 1. Doublon fusionné mais resté sur l'agenda (priorité : c'est le plus net).
        if ev.get("duplicate_of"):
            doublons.append(_row(ev, base, f"doublon de #{ev['duplicate_of']}"))
            seen.add(wp)
            continue
        # 2. Incomplet (porte qualité) — n'aurait pas dû être poussé.
        miss = comp.missing_labels(ev)
        if miss:
            incomplets.append(_row(ev, base, "manque : " + ", ".join(miss)))
            seen.add(wp)
            continue
        # 3. Passé (date de fin révolue).
        end = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()
        if end and end < today:
            passes.append(_row(ev, base, f"terminé le {end}"))
            seen.add(wp)

    return {
        "total_pushed": len(pushed),
        "incomplets": incomplets,
        "doublons": doublons,
        "passes": passes,
    }


def _print_block(title: str, rows: list, base: str) -> None:
    print(f"\n=== {title} : {len(rows)} ===")
    if not rows:
        print("  (aucun)")
        return
    for r in rows:
        print(f"  DB#{r['id']:>4} · WP#{r['wp']:>5} · {r['date']:>10} · {r['title']:<70} · {r['reason']}")
    if base:
        print(f"  → liens d'édition WordPress disponibles (colonne edit_url).")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit (lecture seule) du ménage Agenda Sabauda.")
    parser.add_argument("--limit", type=int, default=1000,
                        help="Nombre max d'événements poussés à examiner.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    base = (os.getenv("WP_AS_URL", "") or "").rstrip("/")
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    res = audit(conn, today, base, args.limit)
    conn.close()

    print(f"\n{'='*72}\nAUDIT MÉNAGE — Agenda Sabauda ({base or 'WP_AS_URL non configurée'})")
    print(f"Événements poussés examinés : {res['total_pushed']} (limite {args.limit})")
    _print_block("① INCOMPLETS (à retirer — n'auraient pas dû partir)", res["incomplets"], base)
    _print_block("② DOUBLONS (fusionnés mais restés sur l'agenda)", res["doublons"], base)
    _print_block("③ PASSÉS (date révolue)", res["passes"], base)

    total = len(res["incomplets"]) + len(res["doublons"]) + len(res["passes"])
    ok = res["total_pushed"] - total
    print(f"\n{'='*72}")
    print(f"BILAN : {total} à nettoyer  ·  {ok} sains  (sur {res['total_pushed']} poussés)")
    print("Aucune modification effectuée (audit lecture seule).")
    print("Étape suivante (après ta validation) : mise à la CORBEILLE WordPress "
          "(réversible), via un second outil.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
