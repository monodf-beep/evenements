#!/usr/bin/env python3
"""Rapport de complétude d'un LOT d'événements — le « portillon » entre les étapes du
protocole par lot (cf. docs/BACKLOG.md, journal 2026-07-31 : Franck refuse le rattrapage
au compte-gouttes qui répare un aspect — l'image — sans vérifier le reste : score,
rédaction, panel lecteurs, placement home).

Ne modifie RIEN. Pour chaque id demandé, affiche l'état RÉEL de chaque étage du
pipeline et un verdict COMPLET/INCOMPLET — pour décider si un lot est prêt à publier
(après enrich.py) ou prêt à clore (après publish_batch_as.py), au lieu de supposer que
"0 échec" au log veut dire "tout est fait".

Usage (VPS) :
    .venv/bin/python -m scripts.batch_report 834 840 843 1155 1447 2128 3506 3512
"""
from __future__ import annotations
import json
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("batch_report")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

LONG_MIN_SCORE = int(os.getenv("ENRICH_LONG_MIN_SCORE", "7"))


def _panel(enrich_data: str) -> dict:
    try:
        data = json.loads(enrich_data or "") or {}
    except (ValueError, TypeError):
        return {}
    return data.get("reader_panel") or {}


def _row_report(r: dict) -> tuple[bool, list[str]]:
    """(complet, lignes de détail) pour un événement."""
    ok = True
    lines = []

    score = r.get("llm_score")
    if score is None:
        ok = False
        lines.append("  ✗ score        : ABSENT (jamais enrichi)")
    else:
        lines.append(f"  · score        : {score} "
                     f"({'long' if int(score) >= LONG_MIN_SCORE else 'court'} attendu)")

    words = len((r.get("article_md") or "").split())
    # Plancher ABSOLU (20 mots) : attrape aussi un article « techniquement non vide »
    # mais réduit à peu près au titre (matière trouvée insuffisante malgré la matière
    # dite « officielle » — cas vécu id 843 : page officielle non pertinente détectée
    # trop tard, article réduit à 6 mots). Le seuil RELATIF (< 250 mots) ne s'applique
    # qu'aux événements qui visaient un article long (score élevé) — un article court
    # (catalogue) n'a pas vocation à être long.
    if words < 20:
        ok = False
        lines.append(f"  ✗ article      : {'VIDE' if words == 0 else f'{words} mots — quasi-vide'}")
    else:
        expect_long = (score or 0) >= LONG_MIN_SCORE
        thin = expect_long and words < 250
        marker = "⚠" if thin else "·"
        lines.append(f"  {marker} article      : {words} mots"
                     + (" (COURT alors que le score visait un long)" if thin else ""))

    # Panel lecteurs : seulement attendu pour un palier LONG (score ≥ LONG_MIN_SCORE) —
    # un événement court/catalogue ne passe JAMAIS par le panel (cf. enrich.py, appelé
    # seulement `if not court`). L'exiger pour un événement court serait un faux négatif.
    panel = _panel(r.get("enrich_data") or "")
    expect_panel = (score or 0) >= LONG_MIN_SCORE
    if expect_panel and not panel:
        ok = False
        lines.append("  ✗ panel lecteurs : jamais passé (attendu, score ≥ seuil long)")
    elif panel:
        lines.append(f"  · panel lecteurs : verdict={panel.get('verdict', '?')} "
                     f"mean={panel.get('mean', '?')} votes={panel.get('votes', '?')}")
    else:
        lines.append("  · panel lecteurs : — (non attendu, palier court)")

    home_score = r.get("home_score")
    lines.append(f"  · home_score   : {home_score if home_score is not None else '— (non calculé)'}"
                 f"  override={r.get('home_override') or '—'}")

    wp_id = r.get("wp_post_id_as")
    if not wp_id:
        lines.append("  · publication AS : PAS ENCORE publié")
    else:
        img_src = r.get("image_source") or "?"
        real_img = bool((r.get("url_image") or "").strip()) and img_src != ""
        lines.append(f"  · publication AS : WP#{wp_id} · image_source={img_src}"
                     f" ({'ok, vraie image' if real_img else 'AUCUNE image'})")
        if not real_img:
            ok = False

    return ok, lines


def main(argv: list[str]) -> int:
    ids = [int(a) for a in argv if a.isdigit()]
    if not ids:
        print("Usage : batch_report <id> [<id> ...]")
        return 1

    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ph = ",".join("?" * len(ids))
    rows = {r["id"]: dict(r) for r in
            conn.execute(f"SELECT * FROM events_raw WHERE id IN ({ph})", ids).fetchall()}
    conn.close()

    n_complete = 0
    for i in ids:
        r = rows.get(i)
        print(f"\n[{i}] {(r.get('title') if r else None) or '— INTROUVABLE EN BASE —'}")
        if not r:
            continue
        complete, lines = _row_report(r)
        for line in lines:
            print(line)
        print(f"  => {'COMPLET' if complete else 'INCOMPLET'}")
        n_complete += complete

    print(f"\n=== Lot : {n_complete}/{len(ids)} complet(s) "
          f"(score + article + panel + image réelle) ===")
    return 0 if n_complete == len(ids) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
