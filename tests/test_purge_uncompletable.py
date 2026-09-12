#!/usr/bin/env python3
"""Fixture : `scripts.purge_uncompletable`, fusionné le 04/09 avec
`discard_uncompletable` (audit du 31/08, §2.1 — décision de Franck : « fais ce qui
te semble le plus adéquat »).

Avant la fusion, les deux scripts tournaient l'un après l'autre dans le hebdo du
dimanche avec la MÊME requête de sélection et le MÊME prédicat radar — mesuré :
`discard_uncompletable --no-page` ne trouvait jamais rien de nouveau, purge_uncompletable
ayant déjà tout pris. Seule sa branche « année révolue dans le titre » était distincte ;
elle vit maintenant ici, sous le motif « année révolue dans le titre ».

Six cas, chacun décidant seul du sort de la fiche :
  1. radar, sans date                         → ÉCARTÉE (motif « radar (presse) ») ;
  2. sans-page (Google News), sans lieu        → ÉCARTÉE (motif « sans page ») ;
  3. année révolue dans le titre, sans date    → ÉCARTÉE (motif « année révolue »,
     repris de discard_uncompletable --past) ;
  4. newsletter (gmail:), année révolue, sans date → JAMAIS touchée (rattrapable via
     gmail_relink — exclusion reprise de discard_uncompletable) ;
  5. source officielle, page réelle, sans date → JAMAIS touchée (le gisement récupérable,
     pas du bruit) ;
  6. déjà complète                             → JAMAIS touchée.

⚠️ BASE JETABLE — jamais data/events.db. Le dry-run (sans --execute) ne doit RIEN écrire.

Lancer : .venv/bin/python -m tests.test_purge_uncompletable
"""
import os
import sqlite3
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.purge_uncompletable as pu  # noqa: E402

pu.DB_PATH = tmp

conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
init_db(conn)

ANNEE_PASSEE = date.today().year - 1

FICHES = [
    # id, title, url_source, source_type, statut, lieu, ville, territoire,
    # llm_categorie, url_image, date_event_start, date_start
    (1, "Chambéry. Cirque, danse, théâtre", "https://www.ledauphine.com/a1", "radar",
     "evaluated", "", "", "Savoie", "", "", "", ""),
    (2, "Nice : trois expositions à voir", "https://news.google.com/a2", "officielle",
     "evaluated", "", "", "Nice", "Expositions", "https://x/i.jpg", "2026-10-01", ""),
    (3, f"Festival {ANNEE_PASSEE} — édition passée jamais mise à jour",
     "https://www.exemple.fr/a3", "officielle", "evaluated", "Salle des fêtes",
     "Annecy", "Savoie", "Concerts", "https://x/i.jpg", "", f"{ANNEE_PASSEE}"),
    (4, f"Newsletter {ANNEE_PASSEE} — bulletin municipal", "gmail:msg-4",
     "officielle", "evaluated", "Mairie", "Cluses", "Savoie", "Concerts",
     "https://x/i.jpg", "", f"{ANNEE_PASSEE}"),
    (5, "Saison 2026-2027 de l'Espace Malraux", "https://www.malrauxchambery.fr/a5",
     "officielle", "evaluated", "Espace Malraux", "Chambéry", "Savoie", "Théâtre",
     "https://x/i.jpg", "", ""),
    (6, "Concert complet, prêt pour WordPress", "https://www.exemple.fr/a6",
     "officielle", "evaluated", "Salle X", "Torino", "Piemonte", "Concerts",
     "https://x/i.jpg", "2026-11-01", ""),
]
for (eid, title, url_source, source_type, statut, lieu, ville, territoire,
     categorie, image, date_start_evt, date_start) in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, source_type, statut, lieu, "
        "ville, territoire, llm_categorie, url_image, date_event_start, date_start, "
        "duplicate_of) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
        (eid, title, url_source, source_type, statut, lieu, ville, territoire,
         categorie, image, date_start_evt, date_start))
conn.commit()
conn.close()

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── dry-run : rien n'est écrit ────")
pu.main([])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
statuts_avant = {r["id"]: r["statut"] for r in conn.execute("SELECT id, statut FROM events_raw")}
conn.close()
_check("dry-run n'a rien modifié", all(s == "evaluated" for s in statuts_avant.values()),
      str(statuts_avant))

print("\n──── --execute : chaque fiche décide seule de son sort ────")
pu.main(["--execute"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
rows = {r["id"]: dict(r) for r in conn.execute(
    "SELECT id, statut, llm_justification FROM events_raw")}
conn.close()

_check("1) radar sans date → écartée (motif radar)",
      rows[1]["statut"] == "rejected" and "radar" in (rows[1]["llm_justification"] or ""),
      str(rows[1]))
_check("2) sans-page (Google News) sans lieu → écartée (motif sans page)",
      rows[2]["statut"] == "rejected"
      and "sans page" in (rows[2]["llm_justification"] or ""),
      str(rows[2]))
_check("3) année révolue dans le titre, sans date → écartée (motif année révolue, "
      "repris de discard_uncompletable --past)",
      rows[3]["statut"] == "rejected"
      and "révolue" in (rows[3]["llm_justification"] or ""),
      str(rows[3]))
_check("4) newsletter (gmail:) année révolue → JAMAIS touchée (rattrapable via "
      "gmail_relink, exclusion reprise de discard_uncompletable)",
      rows[4]["statut"] == "evaluated", str(rows[4]))
_check("5) source officielle avec vraie page, sans date → JAMAIS touchée (gisement "
      "récupérable)", rows[5]["statut"] == "evaluated", str(rows[5]))
_check("6) déjà complète → JAMAIS touchée", rows[6]["statut"] == "evaluated", str(rows[6]))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
