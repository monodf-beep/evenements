#!/usr/bin/env python3
"""Purge DÉTERMINISTE du bruit (gratuit, sans LLM).

Rejette (ou supprime avec --hard) les événements 'pending' qui sont :
  • HORS ZONE — citent un lieu clairement hors des 4 territoires
    (config/out_of_zone.txt) sans aucun lieu couvert, ou source large sans lieu
    couvert ;
  • PASSÉS — déjà terminés (date de fin/début antérieure à aujourd'hui) : on
    n'informe que du à-venir / en cours.

Rattrape en plus, sur une file PLUS LARGE que 'pending' :
  • ARRONDISSEMENT DE GRASSE — `ville` ∈ arrondissement de Grasse (charte §2 :
    « Comté de Nice » = arrondissement de NICE). Ce motif ne peut pas vivre au
    scraping (`ville` y est vide) et l'évaluateur ne voit qu'une fois chaque fiche,
    à 9h : celles dont la `ville` a été renseignée APRÈS coup (venues.py plafonné,
    page injoignable, autocomplete.py déclenché depuis le back-office) lui ont
    échappé. On les reprend donc ici, en 'pending', 'evaluated' et 'published_sub'.
    ⚠️ Les fiches DÉJÀ EN LIGNE (wp_post_id_as/_cs non nul) sont seulement LISTÉES,
    jamais modifiées : ce script tourne chaque dimanche avec --apply via
    weekly_audits.py, et basculer en 'rejected' une fiche publiée laisserait un
    orphelin en ligne. Leur sort se décide à la main (voir scripts/count_grasse.py).

    python scripts/purge_out_of_zone.py            # aperçu (rien n'est modifié)
    python scripts/purge_out_of_zone.py --apply    # rejette (statut='rejected')
    python scripts/purge_out_of_zone.py --apply --hard   # supprime les lignes
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
from utils.logger import get_logger
from utils.sources import (is_broad_source, is_out_of_scope, load_broad_sources,
                           load_out_of_zone, load_perimeter_filter, mentions_perimeter)
from scripts.scraper_events import _domain
from scripts.perimetre import ville_hors_perimetre

log = get_logger("purge_zone")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Statuts repris par le rattrapage « arrondissement de Grasse » : la file d'attente
# ('pending'), le haut du panier en attente de rédaction ('evaluated') et le catalogue
# ('published_sub'). Volontairement PAS 'rejected' (déjà écarté), 'merged' (doublon
# absorbé) ni 'published_cs' (article Cultura Sabauda, décision éditoriale humaine).
GRASSE_STATUTS = ("pending", "evaluated", "published_sub")


def _colonnes(conn: sqlite3.Connection) -> set[str]:
    """Colonnes réellement présentes — wp_post_id_as est une colonne de MIGRATION,
    absente d'une base ancienne. On ne suppose pas, on regarde (PRAGMA)."""
    return {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}


def fiches_grasse(conn: sqlite3.Connection) -> tuple[list, list]:
    """(à purger, déjà en ligne) — fiches dont la `ville` est dans l'arrondissement
    de Grasse. Comparaison sur le CHAMP `ville` uniquement, jamais sur du texte libre.
    """
    cols = _colonnes(conn)
    wp_cols = [c for c in ("wp_post_id_as", "wp_post_id_cs") if c in cols]
    sel = ", ".join(["id", "title", "ville", "territoire", "source_name", "statut"] + wp_cols)
    marks = ",".join("?" * len(GRASSE_STATUTS))
    rows = conn.execute(
        f"SELECT {sel} FROM events_raw WHERE statut IN ({marks}) "
        f"AND duplicate_of IS NULL AND COALESCE(ville,'') != ''", GRASSE_STATUTS).fetchall()
    a_purger, en_ligne = [], []
    for r in rows:
        if not ville_hors_perimetre(r["ville"]):
            continue
        (en_ligne if any(r[c] for c in wp_cols) else a_purger).append(r)
    return a_purger, en_ligne


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Purge des événements hors zone.")
    parser.add_argument("--apply", action="store_true",
                        help="Applique (par défaut : aperçu seul, rien n'est modifié).")
    parser.add_argument("--hard", action="store_true",
                        help="Supprime les lignes au lieu de les passer en 'rejected'.")
    args = parser.parse_args(argv)

    perimeter_re = load_perimeter_filter()
    broad = load_broad_sources()
    out_re = load_out_of_zone()
    if perimeter_re is None and out_re is None:
        log.error("Aucun filtre configuré (perimeter_keywords.txt / out_of_zone.txt).")
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, title, description, url_source, territoire, source_name, "
        "date_event_start, date_event_end "
        "FROM events_raw WHERE statut = 'pending' AND duplicate_of IS NULL").fetchall()

    today = date.today().isoformat()
    hits = []
    for r in rows:
        material = f"{r['title']}\n{r['description'] or ''}"
        end = (r["date_event_end"] or r["date_event_start"] or "").strip()[:10]
        past_hit = bool(end) and end < today
        broad_hit = (broad and is_broad_source(_domain(r["url_source"]), broad)
                     and perimeter_re is not None
                     and not mentions_perimeter(material, perimeter_re))
        zone_hit = is_out_of_scope(material, out_re, perimeter_re)
        if past_hit:
            hits.append((r, "passé"))
        elif broad_hit or zone_hit:
            hits.append((r, "hors zone" if zone_hit else "source large"))

    # Rattrapage « arrondissement de Grasse » — file élargie (voir docstring). Dédoublonné
    # par id : une fiche 'pending' peut déjà avoir été retenue par un motif ci-dessus.
    deja = {r["id"] for r, _ in hits}
    grasse, grasse_en_ligne = fiches_grasse(conn)
    hits += [(r, "Grasse") for r in grasse if r["id"] not in deja]

    from collections import Counter
    par_motif = Counter(m for _, m in hits)
    detail = ", ".join(f"{n} {m}" for m, n in par_motif.items()) or "aucun"
    # Deux périmètres d'examen distincts : ne pas les additionner dans une seule
    # fraction (« 5 sur 7 ») — le motif Grasse va chercher au-delà de la file 'pending'.
    print(f"\n{len(hits)} à purger ({detail}).")
    print(f"  Examinés : {len(rows)} fiche(s) 'pending' pour les motifs passé/hors "
          f"zone/source large ;\n             toutes les fiches "
          f"{'/'.join(GRASSE_STATUTS)} pour le motif Grasse.\n")
    for r, motif in hits[:60]:
        print(f"  [{r['id']:>5}] {r['territoire'] or '—':<14} {motif:<12} "
              f"{(r['source_name'] or '')[:22]:<22} {r['title'][:60]}")
    if len(hits) > 60:
        print(f"  … et {len(hits) - 60} autres.")

    if grasse_en_ligne:
        print(f"\n⚠️  {len(grasse_en_ligne)} fiche(s) de l'arrondissement de Grasse "
              f"DÉJÀ EN LIGNE — listées, JAMAIS modifiées par ce script (un simple "
              f"'rejected' laisserait un orphelin publié). Décision à la main :")
        for r in grasse_en_ligne[:30]:
            print(f"  [{r['id']:>5}] {(r['ville'] or '—'):<22} {r['title'][:60]}")
        if len(grasse_en_ligne) > 30:
            print(f"  … et {len(grasse_en_ligne) - 30} autres.")
        print("  → inventaire complet : python scripts/count_grasse.py --list")

    if not args.apply:
        print("\nAperçu seul. Relance avec --apply pour rejeter "
              "(ou --apply --hard pour supprimer).")
        conn.close()
        return 0

    ids = [r["id"] for r, _ in hits]
    if args.hard:
        conn.executemany("DELETE FROM events_raw WHERE id=?", [(i,) for i in ids])
        verbe = "supprimé(s)"
    else:
        motifs = {
            "passé": "Événement passé (déjà terminé).",
            "hors zone": "Hors zone (lieu hors périmètre cité, aucun lieu couvert).",
            "source large": "Hors périmètre (source large, aucun lieu couvert cité).",
            "Grasse": "Hors périmètre — commune de l'arrondissement de Grasse ; le "
                      "Comté de Nice couvre l'arrondissement de Nice (charte §2).",
        }
        conn.executemany(
            "UPDATE events_raw SET statut='rejected', llm_justification=? WHERE id=?",
            [(motifs[m], r["id"]) for r, m in hits])
        verbe = "rejeté(s)"
    conn.commit()
    conn.close()
    print(f"\n✅ {len(ids)} événement(s) {verbe}.")
    log.info("Purge hors zone : %d %s", len(ids), verbe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
