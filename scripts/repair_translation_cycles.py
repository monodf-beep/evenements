#!/usr/bin/env python3
"""Casse les CYCLES de traduction : A.translation_of = B **et** B.translation_of = A.

Pourquoi c'est grave, et pas seulement inesthétique : `scripts/enrich.py` et (depuis le
2026-08-02) `scripts/dates.py` excluent tous deux les fiches dont `translation_of` est
renseigné — une traduction ne doit jamais être rédigée ni datée depuis son propre texte.
Dans un cycle, **les DEUX côtés sont vus comme des traductions** : ni l'un ni l'autre
n'est donc jamais enrichi ni daté. Ces événements sont durablement affamés (constaté :
« Marc Chagall » côté FR, resté sans date parce que personne ne la lui donnerait jamais).

Origine : un défaut de `link_translations_as.py` (mécanisme B) qui pouvait ré-apparier une
paire DÉJÀ établie par `translate_events.py` (mécanisme A) et écraser la relation avec une
direction contradictoire. **Corrigé à la source le 2026-07-29** (filtre excluant les deux
côtés d'une paire existante) : les cycles restants sont des dégâts ANTÉRIEURS, aucun
nouveau ne se forme. Ce script ne fait donc que réparer l'existant.

Règle de décision (qui est l'original ?), du plus sûr au moins sûr :
  1. `url_source` commençant par « translated: » = fiche FABRIQUÉE par translate_events →
     c'est la traduction ; l'autre côté est l'original, on efface SON translation_of.
  2. Aucun des deux n'est « translated: » (source réellement bilingue, les deux ont été
     scrapés) → primaire = FR, même règle que `link_translations_as._mark_pair_in_db`
     (« le site est français d'abord »).
  3. Les DEUX sont « translated: » → cas incohérent, SIGNALÉ sans être touché.

On ne supprime aucun contenu : on efface seulement `translation_of`/`translated_lang` du
côté original, ce qui le rend de nouveau éligible à l'enrichissement et à la datation. Le
lien Polylang côté WordPress n'est pas modifié (la paire reste jumelée sur le site).

SÛR : dry-run par défaut, --apply pour écrire. AUCUN appel API.

Usage (VPS) :
    .venv/bin/python -m scripts.repair_translation_cycles            # liste
    .venv/bin/python -m scripts.repair_translation_cycles --apply    # répare
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.lang import detect_lang

log = get_logger("repair_translation_cycles")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _is_machine(row: dict) -> bool:
    """La fiche a-t-elle été FABRIQUÉE par translate_events (url_source synthétique) ?"""
    return (row.get("url_source") or "").startswith("translated:")


def _lang(row: dict) -> str:
    return detect_lang(row.get("title") or "", row.get("description") or "",
                       row.get("territoire") or "")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Casse les cycles de traduction A<->B.")
    parser.add_argument("--apply", action="store_true", help="Écrit (sinon dry-run).")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = {r["id"]: dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(translation_of,0) <> 0").fetchall()}

    # Paires uniques (a < b) telles que a->b et b->a.
    paires = set()
    for rid, r in rows.items():
        other = rows.get(r["translation_of"] or 0)
        if other and (other.get("translation_of") or 0) == rid:
            paires.add(tuple(sorted((rid, other["id"]))))

    a_casser, ambigus = [], []
    for a_id, b_id in sorted(paires):
        a, b = rows[a_id], rows[b_id]
        ma, mb = _is_machine(a), _is_machine(b)
        if ma and mb:
            ambigus.append((a, b, "les deux sont des traductions machine"))
            continue
        if ma != mb:
            original = b if ma else a               # règle 1 : le non-machine est l'original
            motif = "l'autre côté est une traduction machine (url_source « translated: »)"
        else:
            la, lb = _lang(a), _lang(b)
            if la == lb:
                ambigus.append((a, b, f"les deux détectés en « {la} » — jumelage douteux"))
                continue
            original = a if la == "fr" else b       # règle 2 : FR primaire
            motif = "aucun des deux n'est machine → FR primaire (site français d'abord)"
        a_casser.append((original, a if original is b else b, motif))

    print(f"\n{len(paires)} cycle(s) détecté(s)\n")

    if a_casser:
        print(f"--- {len(a_casser)} à CASSER (translation_of effacé sur l'ORIGINAL) ---")
        for orig, trad, motif in a_casser:
            print(f"  original [{orig['id']}] WP#{orig.get('wp_post_id_as')} "
                  f"{(orig.get('title') or '')[:46]}")
            print(f"       ↳ garde comme traduction [{trad['id']}] "
                  f"{(trad.get('title') or '')[:44]}")
            print(f"       motif : {motif}")

    if ambigus:
        print(f"\n--- {len(ambigus)} AMBIGU(S) — non touché(s), à regarder à la main ---")
        for a, b, motif in ambigus:
            print(f"  [{a['id']}] ↔ [{b['id']}] : {motif}")
            print(f"       {(a.get('title') or '')[:52]}")
            print(f"       {(b.get('title') or '')[:52]}")

    if not args.apply:
        print(f"\n(dry-run : rien écrit — relance avec --apply pour casser les {len(a_casser)}.)")
        conn.close()
        return 0

    for orig, _trad, _motif in a_casser:
        conn.execute("UPDATE events_raw SET translation_of=NULL, translated_lang=NULL "
                     "WHERE id=?", (orig["id"],))
    conn.commit()
    conn.close()

    log.info("%d cycle(s) cassé(s) — les originaux redeviennent éligibles enrich/dates.",
             len(a_casser))
    print(f"\n✅ {len(a_casser)} cycle(s) cassé(s). Ces originaux vont maintenant être repris "
          f"par le lot quotidien (rédaction + datation) — rien d'autre à lancer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
