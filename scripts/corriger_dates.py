#!/usr/bin/env python3
"""Corrige les dates FAUSSES de fiches désignées par leur numéro WordPress, à partir d'une liste.

Né le 24/09/2026. Deux fiches passées comptaient comme « à venir » : Pizza Show (Verceil,
27 mars → 21 juin 2026) et la Fondation Sapegno au Salone del Libro (15 mai 2026),
datées toutes deux en 2027. Cause : `dates._year()` devine l'année absente du texte avec
une grâce de 60 jours, et une date passée de plus de 60 jours bascule à l'année SUIVANTE.
Lues en septembre, deux annonces du printemps sont devenues des événements de 2027.
`audit_annee_date` cherche le sens inverse (une date trop VIEILLE) ; celui-ci ne se voyait
nulle part.

`completer_verifie --depuis` sait remplacer une date, mais par numéro de BASE : le
lecteur du site n'a que le numéro WordPress. Ce script fait la traduction, applique au
groupe (original + traductions) et garde la même sûreté que la clause « remplace » : il
REFUSE d'écrire si la base ne porte plus la date fausse qu'on déclare corriger — quelqu'un
est passé entre-temps.

Format TSV : `id_wordpress<TAB>début<TAB>fin<TAB>début_faux_attendu<TAB>source`, dates
AAAA-MM-JJ. La source porte la PHRASE lue, pas seulement un nom de site.

Il ne republie PAS : `publish_batch_as` ne pousse que les événements À VENIR, une fiche
remise dans le passé ne repasserait pas. Le côté WordPress se corrige séparément
(tribe_update_event, par Novamira). Dry-run par défaut (règle 4).

    .venv/bin/python scripts/corriger_dates.py config/dates_corrigees_2026_09.tsv
    .venv/bin/python scripts/corriger_dates.py config/dates_corrigees_2026_09.tsv --apply
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "events.db"


def lire_liste(chemin: Path) -> list[tuple[int, str, str, str, str]]:
    out = []
    for n, brute in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
        ligne = brute.strip()
        if not ligne or ligne.startswith("#"):
            continue
        p = [x.strip() for x in ligne.split("\t")]
        try:
            if len(p) < 5 or not p[0].isdigit() or len(p[4]) < 20:
                raise ValueError
            for d in p[1:4]:
                date.fromisoformat(d)
        except ValueError:
            raise SystemExit(f"{chemin}:{n} : ligne mal formée — {ligne[:80]}")
        out.append((int(p[0]), p[1], p[2], p[3], p[4]))
    return out


def groupe(conn: sqlite3.Connection, wp_id: int) -> list[sqlite3.Row]:
    r = conn.execute("SELECT id, translation_of FROM events_raw WHERE wp_post_id_as=? "
                     "AND duplicate_of IS NULL", (wp_id,)).fetchone()
    if not r:
        return []
    racine = r["translation_of"] or r["id"]
    return conn.execute(
        "SELECT id, wp_post_id_as, statut, date_event_start, date_event_end FROM events_raw "
        "WHERE (id=? OR translation_of=?) AND duplicate_of IS NULL ORDER BY id",
        (racine, racine)).fetchall()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("liste", type=Path)
    ap.add_argument("--apply", action="store_true", help="écrire")
    args = ap.parse_args(argv)

    lignes = lire_liste(args.liste)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ecrites, refusees = [], []
    for wp_id, debut, fin, faux, source in lignes:
        g = groupe(conn, wp_id)
        if not g:
            print(f"WP#{wp_id} : AUCUNE fiche en base ne porte ce post — ignoré")
            refusees.append(wp_id)
            continue
        print(f"WP#{wp_id} → {debut} … {fin}\n   source : {source[:110]}")
        for r in g:
            actuel = (r["date_event_start"] or "")[:10]
            ok = actuel == faux
            print(f"   fiche {r['id']:>5} (WP#{r['wp_post_id_as'] or '-'}) en base "
                  f"{actuel} … {(r['date_event_end'] or '')[:10]}"
                  + ("" if ok else f"   ⚠ REFUSÉE : la base ne porte pas {faux}"))
            if not ok:
                refusees.append(r["id"])
                continue
            if args.apply:
                conn.execute("UPDATE events_raw SET date_event_start=?, date_event_end=? "
                             "WHERE id=?", (debut, fin, r["id"]))
                ecrites.append(r["id"])
    if args.apply:
        conn.commit()
        relues = conn.execute(
            f"SELECT id, date_event_start, date_event_end FROM events_raw WHERE id IN "
            f"({','.join('?' * len(ecrites)) or 'NULL'})", ecrites).fetchall()
        print("\nRelu en base :")
        for r in relues:
            print(f"   fiche {r['id']:>5} : {r['date_event_start']} … {r['date_event_end']}")
    conn.close()
    print(f"\n{len(lignes)} ligne(s), {len(refusees)} refus"
          + ("" if args.apply else " — SIMULATION, rien n'a été écrit (--apply pour écrire)."))
    return 1 if refusees else 0


if __name__ == "__main__":
    raise SystemExit(main())
