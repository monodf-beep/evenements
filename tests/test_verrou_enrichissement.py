#!/usr/bin/env python3
"""Fixture du verrou d'enrichissement de scripts/publish_batch_as._select.

POURQUOI CE VERROU. Mesuré le 22/09/2026 sur la base de production : 271 fiches publiées
en trente jours, dont 17 SANS enrichissement (6,3 %), et 6 encore à venir. `build_post`
retombe sur le titre + la description bruts quand `enrich_data` est vide, or la charte §3
dit « jamais la description brute ». Le déclencheur : 52 fiches italiennes entrées d'un
coup, dont le texte du ministère serait parti tel quel sur le versant français.

LES DEUX BORDS, comme l'exige la règle 3 du CLAUDE.md :
  • une fiche enrichie DOIT passer — sinon le verrou ne retarde pas, il bloque ;
  • une fiche identique mais sans enrich_data DOIT être retenue ;
  • et la contre-épreuve : cette même fiche non enrichie doit rester éligible à TOUT LE
    RESTE (statut, date, non-doublon), pour prouver que c'est bien ce verrou-là qui la
    retient et pas une autre condition.
"""
import sqlite3
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.scraper_events import init_db          # noqa: E402
from scripts.publish_batch_as import _select        # noqa: E402

DEMAIN = "2026-12-01"


def _fiche(conn, titre, url, enrich):
    conn.execute(
        "INSERT INTO events_raw (title, description, url_source, statut, llm_score, "
        " date_event_start, date_event_end, enrich_data) VALUES (?,?,?,?,?,?,?,?)",
        (titre, "texte brut de la source", url, "evaluated", 5, DEMAIN, DEMAIN, enrich))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def main() -> int:
    echecs = []
    with tempfile.TemporaryDirectory() as tmp:
        conn = sqlite3.connect(Path(tmp) / "jetable.db")
        conn.row_factory = sqlite3.Row
        init_db(conn)

        id_ok = _fiche(conn, "Fiche rédigée", "https://exemple.test/a", '{"article": "un vrai texte"}')
        id_brut = _fiche(conn, "Fiche non rédigée", "https://exemple.test/b", "")
        conn.commit()

        args = Namespace(ids=None, include_past=True, update=False, min_score=None, cap=50)
        pris = [r["id"] for r in _select(conn, args, "2026-09-22")]

        if id_ok in pris:
            print("OK    la fiche rédigée passe")
        else:
            echecs.append("la fiche rédigée est retenue : le verrou bloque au lieu de retarder")

        if id_brut in pris:
            echecs.append("la fiche sans enrich_data est passée : le verrou ne sert à rien")
        else:
            print("OK    la fiche sans rédaction est retenue")

        # Contre-épreuve : la fiche brute satisfait TOUTES les autres conditions.
        reste = conn.execute(
            "SELECT COUNT(*) FROM events_raw WHERE id = ? AND statut IN "
            "('evaluated','published_cs','published_sub') AND duplicate_of IS NULL "
            "AND COALESCE(date_event_start,'') <> '' AND COALESCE(wp_post_id_as,0) = 0",
            (id_brut,)).fetchone()[0]
        if reste == 1:
            print("OK    elle est retenue par CE verrou, pas par une autre condition")
        else:
            echecs.append("la fiche brute échouait déjà sur une autre condition : "
                          "la fixture ne prouve rien")

        # Elle doit rester visible pour enrich.py, sinon c'est un cul-de-sac.
        eligible = conn.execute(
            "SELECT COUNT(*) FROM events_raw WHERE id = ? AND statut IN "
            "('evaluated','published_sub') AND COALESCE(llm_score,0) >= 1",
            (id_brut,)).fetchone()[0]
        if eligible == 1:
            print("OK    elle reste éligible à enrich.py — le verrou retarde, il ne gare pas")
        else:
            echecs.append("la fiche retenue n'est plus éligible à l'enrichissement : cul-de-sac")

        conn.close()

    print()
    if echecs:
        for e in echecs:
            print("ÉCHEC", e)
        print(f"\nÉCHEC — {len(echecs)} problème(s).")
        return 1
    print("SUCCÈS — 0 problème(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
