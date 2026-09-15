#!/usr/bin/env python3
"""LES FICHES DÉJÀ EN LIGNE dont le corps mélange les deux langues — lecture seule.

D'OÙ ÇA VIENT (2026-09-15). Franck, devant WP#8324 : « problème de traduction (comment
c'est encore possible !?!?) ». La fiche est italienne sans ambiguïté — URL `/it/`,
territoire « Piemonte », langue Polylang `it` — son titre et son premier paragraphe sont
en italien, et TROIS paragraphes du corps sont en français.

Le trou est réparé à la source : `utils.lang.paragraphes_mauvaise_langue` est désormais
un portillon dans `scripts/translate_events.py`, qui refuse un article dont le corps est
resté dans l'autre langue. Mais un correctif de code ne répare pas les fiches déjà
écrites — règle de livraison du 08/09 : il s'accompagne de la liste des fiches touchées
et de la commande qui les répare. C'est ce fichier.

CE QU'IL MESURE, et sur quoi. L'article stocké en base (`enrich_data.article`), pas la
page WordPress : c'est lui qui sera republié, donc c'est lui qu'il faut juger. Mesuré le
15/09 sur les 321 fiches publiées du site, 1 777 paragraphes : DIX fiches, 33 paragraphes.

LA MARGE VIENT DES DONNÉES, pas d'un choix a priori (cf. `utils.lang.MARGE_PARAGRAPHE`) :
à 4, la règle attrapait une phrase française énumérant des titres de chansons italiennes ;
le plus faible des vrais cas est à 5.

Aucun réseau, aucun appel LLM, aucune écriture. La réparation se fait ensuite avec
`translate_events --retranslate`, qui refera l'article — et le nouveau portillon refusera
s'il rate encore, au lieu de publier un mélange.

    .venv/bin/python -m scripts.audit_langue_articles
    .venv/bin/python -m scripts.audit_langue_articles --tout    # passé compris
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.lang import effective_lang, paragraphes_mauvaise_langue, MARGE_PARAGRAPHE

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def suspects(ev: dict) -> "tuple[str, list]":
    """(langue attendue, [(écart, paragraphe), …]) pour une ligne de base."""
    langue = effective_lang(ev)
    try:
        art = (json.loads(ev.get("enrich_data") or "{}") or {}).get("article") or {}
    except (ValueError, TypeError):
        return langue, []
    if not isinstance(art, dict):
        return langue, []
    trouves = []
    for champ in ("chapo", "corps", "encadre"):
        v = art.get(champ)
        if isinstance(v, str) and v.strip():
            trouves += paragraphes_mauvaise_langue(v, langue)
    trouves.sort(key=lambda x: -x[0])
    return langue, trouves


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Fiches dont le corps mélange FR et IT.")
    p.add_argument("--tout", action="store_true",
                   help="Inclut les événements passés (par défaut : ce qui est devant nous).")
    p.add_argument("--marge", type=int, default=MARGE_PARAGRAPHE)
    args = p.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    where = ["COALESCE(enrich_data,'') <> ''", "COALESCE(wp_post_id_as,0) > 0"]
    if not args.tout:
        where.append("(COALESCE(date_event_end, date_event_start, '') = '' "
                     "OR COALESCE(date_event_end, date_event_start) >= date('now'))")
    rows = conn.execute("SELECT * FROM events_raw WHERE " + " AND ".join(where)).fetchall()

    touchees = []
    for r in rows:
        ev = dict(r)
        langue, trouves = suspects(ev)
        trouves = [t for t in trouves if t[0] >= args.marge]
        if trouves:
            touchees.append((ev, langue, trouves))

    touchees.sort(key=lambda x: -x[2][0][0])
    for ev, langue, trouves in touchees:
        print(f"\n[{ev['id']:>5} WP#{ev.get('wp_post_id_as') or '—':>5}] langue {langue} · "
              f"{len(trouves)} paragraphe(s) dans l'autre langue · "
              f"{(ev.get('title') or '')[:52]}")
        for ecart, para in trouves[:2]:
            print(f"      +{ecart}  {para[:96]}…")

    total_par = sum(len(t[2]) for t in touchees)
    print(f"\n{len(rows)} fiche(s) examinée(s)"
          + ("" if args.tout else " (en ligne, encore devant nous)")
          + f" — {len(touchees)} avec un corps mélangé, {total_par} paragraphe(s), "
            f"marge {args.marge}.")
    if touchees:
        ids = " ".join(str(t[0]["id"]) for t in touchees)
        print("\nPour refaire ces articles (le nouveau portillon refusera s'il rate encore) :")
        print(f"    .venv/bin/python -m scripts.translate_events --retranslate --apply {ids}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
