#!/usr/bin/env python3
"""Fixture : `scripts.repair_pied_rss` nettoie les descriptions au pied RSS et ne
republie QUE ce qui est en ligne et encore devant nous.

Cinq lignes, chacune décidant seule :
  1. pied RSS + en ligne + à venir        → nettoyée ET republiée (le cas nominal) ;
  2. pied RSS + en ligne + PASSÉE          → nettoyée, PAS republiée (règle 5) ;
  3. pied RSS + PAS en ligne               → nettoyée, rien à republier ;
  4. « L'article 5 du règlement… » sans pied → INTOUCHÉE (le cas qui doit passer :
     la marque seule ne suffit pas) ;
  5. description propre                     → intouchée (contre-épreuve).
Et le dry-run n'écrit rien.

⚠️ BASE JETABLE — jamais data/events.db.

Lancer : .venv/bin/python -m tests.test_repair_pied_rss
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.repair_pied_rss as rp  # noqa: E402

conn = sqlite3.connect(tmp)
init_db(conn)

PIED = " L’article Truc est apparu en premier sur Mairie de Villefranche-sur-Mer ."
LIGNES = [
    (1, "Bal", "Bal gratuit à la Citadelle." + PIED, 601, "2099-09-15", None),
    (2, "Régates", "Régates dans la rade." + PIED, 602, "2020-06-01", None),
    (3, "Expo", "Expo en cours." + PIED, None, "2099-01-01", None),
    (4, "Règlement", "L'article 5 du règlement précise que l'entrée est libre.", 604, "2099-03-03", None),
    (5, "Propre", "Concert sur la place à 21h.", 605, "2099-03-03", None),
]
for i, t, d, wp, fin, _ in LIGNES:
    conn.execute("INSERT INTO events_raw (id, title, description, wp_post_id_as, "
                 "date_event_start, date_event_end, statut, url_source) "
                 "VALUES (?,?,?,?,?,?,'published_cs',?)", (i, t, d, wp, fin, fin, f"u{i}"))
conn.commit()
conn.close()

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


def desc(i):
    c = sqlite3.connect(tmp)
    v = c.execute("SELECT description FROM events_raw WHERE id=?", (i,)).fetchone()[0]
    c.close()
    return v


republies: list[list[int]] = []
rp.republier = lambda ids: republies.append(list(ids))

rp.main([])
verifier("dry-run : la description polluée n'a pas bougé", "apparu" in desc(1))
verifier("dry-run : rien n'est republié", republies == [])

rp.main(["--apply"])
verifier("① en ligne + à venir : nettoyée", desc(1) == "Bal gratuit à la Citadelle.", desc(1))
verifier("① en ligne + à venir : republiée", republies and 1 in republies[0], str(republies))
verifier("② passée : nettoyée en base", desc(2) == "Régates dans la rade.", desc(2))
verifier("② passée : PAS republiée (règle 5)", not any(2 in lot for lot in republies), str(republies))
verifier("③ pas en ligne : nettoyée", desc(3) == "Expo en cours.", desc(3))
verifier("③ pas en ligne : pas republiée", not any(3 in lot for lot in republies))
verifier("④ « L'article 5 du règlement » : INTOUCHÉE (le cas qui doit passer)",
         desc(4) == LIGNES[3][2], desc(4))
verifier("④ et pas republiée", not any(4 in lot for lot in republies))
verifier("⑤ description propre : intouchée", desc(5) == LIGNES[4][2])
verifier("une seule republication, d'un seul id", republies == [[1]], str(republies))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
