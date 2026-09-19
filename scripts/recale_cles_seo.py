#!/usr/bin/env python3
"""Recale l'expression clé SEO des fiches DÉJÀ traitées sur le texte réellement publié.

D'OÙ ÇA VIENT — 2026-09-10. Franck : « je te dis qu'on a peu de vert pour le SEO des
événements ». Le correctif de fond est dans `utils.seo.recale_keyphrase` (appelé par
`optimize_seo`), mais il ne vaut que pour les fiches à VENIR : les fiches déjà passées
par `seo_batch` gardent en base une clé que le LLM a pu écrire autrement que le corps —
« Fiera del Bue Grasso Carrù » quand l'article dit « Fiera del Bue Grasso DI Carrù »
(WP#2283, mesuré ce jour-là). Yoast compte alors ZÉRO occurrence : expression clé absente
de l'introduction, densité nulle, absente des sous-titres. Trois points rouges pour une
préposition.

Ce script est DÉTERMINISTE et GRATUIT : aucun appel LLM, aucune écriture sur WordPress.
Il ne touche qu'à `seo_keyphrase`, et seulement quand la clé recalée est LITTÉRALEMENT
présente dans l'article. Il n'invente jamais une clé absente.

Pour que le site en profite, republier ensuite (le SEO est poussé au (re)publish) :
    .venv/bin/python3 -m scripts.publish_batch_as --update --skip-media

DRY-RUN PAR DÉFAUT (règle 4). Lire la sortie avant `--apply`, et sauvegarder d'abord :
    .venv/bin/python3 scripts/backup_db.py

Exemples :
  .venv/bin/python3 -m scripts.recale_cles_seo                 # dry-run, devant nous
  .venv/bin/python3 -m scripts.recale_cles_seo --apply
  .venv/bin/python3 -m scripts.recale_cles_seo --include-past --dry-run
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger          # noqa: E402
from utils.seo import recale_keyphrase, cle_dans_texte  # noqa: E402

log = get_logger("recale_cles_seo")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _matiere(row: sqlite3.Row) -> str:
    """La matière que Yoast lira : l'article rédigé s'il existe, sinon la description.
    Même ordre que `optimize_seo`, pour que les deux ne puissent pas diverger."""
    return (row["article_md"] or row["description"] or "").strip()


def _selection(conn, include_past: bool, today: str) -> list[sqlite3.Row]:
    """Fiches qui ONT une clé et de la matière. Périmètre par défaut : ce qui est encore
    devant nous (règle 5 — la date de FIN décide, et une fiche sans date n'est pas du
    passé, c'est une donnée manquante, donc elle reste dans le lot)."""
    where = ["COALESCE(seo_keyphrase,'') <> ''", "duplicate_of IS NULL"]
    params: list = []
    if not include_past:
        where.append("(COALESCE(date_event_end, date_event_start, '') = '' "
                     "OR COALESCE(date_event_end, date_event_start) >= ?)")
        params.append(today)
    return conn.execute(
        f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
        f"ORDER BY (COALESCE(wp_post_id_as,0) > 0) DESC, date_event_start ASC",
        params).fetchall()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="écrit en base (défaut : dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="explicite ; c'est le défaut")
    ap.add_argument("--include-past", action="store_true",
                    help="inclut les événements terminés (par défaut ils sont écartés)")
    ap.add_argument("--db", default=str(DB_PATH))
    args = ap.parse_args()

    today = date.today().isoformat()
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    rows = _selection(conn, args.include_past, today)

    changes: list[tuple] = []
    deja_ok = introuvables = sans_matiere = 0
    for r in rows:
        matiere = _matiere(r)
        if not matiere:
            sans_matiere += 1
            continue
        cle = (r["seo_keyphrase"] or "").strip()
        if cle_dans_texte(cle, matiere):
            deja_ok += 1
            continue
        neuve = recale_keyphrase(cle, matiere)
        if neuve != cle and cle_dans_texte(neuve, matiere):
            changes.append((r["id"], r["wp_post_id_as"], cle, neuve, r["title"]))
        else:
            # La clé ne se recale pas : le LLM a écrit des mots qui ne sont PAS dans le
            # texte. Ces fiches-là resteront rouges tant qu'elles ne repassent pas par
            # `seo_batch --redo` (là, un appel LLM est nécessaire, ce script ne l'est pas).
            introuvables += 1

    portee = "toutes dates" if args.include_past else f"à venir/en cours au {today}"
    print(f"\nPÉRIMÈTRE : {portee} — {len(rows)} fiche(s) avec une expression clé.")
    print(f"  clé déjà présente dans le texte  : {deja_ok}")
    print(f"  clé RECALABLE (ce script)        : {len(changes)}")
    print(f"  clé introuvable dans le texte    : {introuvables}"
          f"   → à repasser par `seo_batch --redo` (appel LLM)")
    print(f"  fiche sans article ni description: {sans_matiere}")

    if changes:
        print("\nRECALAGES PROPOSÉS (liste ENTIÈRE, non tronquée) :")
        for eid, wp, avant, apres, titre in changes:
            enligne = f"WP#{wp}" if wp else "hors ligne"
            print(f"  [{eid}] {enligne}  « {avant} » → « {apres} »   {(titre or '')[:60]}")

    if not args.apply:
        print("\nDRY-RUN — rien n'a été écrit. Relancer avec --apply pour appliquer.")
        return 0

    for eid, _wp, _avant, apres, _t in changes:
        conn.execute("UPDATE events_raw SET seo_keyphrase=? WHERE id=?", (apres, eid))
    conn.commit()

    # Règle 6 : on RECOMPTE en base, on n'annonce pas la longueur de la liste.
    ids = [c[0] for c in changes]
    ecrits = 0
    for eid, _wp, _avant, apres, _t in changes:
        cur = conn.execute("SELECT seo_keyphrase FROM events_raw WHERE id=?", (eid,)).fetchone()
        if cur and (cur[0] or "").strip() == apres:
            ecrits += 1
    print(f"\nAPPLIQUÉ — {ecrits} clé(s) relue(s) en base sur {len(ids)} proposée(s).")
    en_ligne = [c[0] for c in changes if c[1]]
    if en_ligne:
        print(f"{len(en_ligne)} de ces fiches sont EN LIGNE : le site ne changera qu'après")
        print("  .venv/bin/python3 -m scripts.publish_batch_as --update --skip-media")
    log.info("recale_cles_seo : %d clé(s) recalée(s) (%s)", ecrits, portee)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
