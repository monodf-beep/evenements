#!/usr/bin/env python3
"""Fixture : scripts/corriger_dates.py corrige tout le groupe (original + traductions),
n'écrit rien sans --apply, et REFUSE une fiche dont la base ne porte pas la date fausse
déclarée (quelqu'un est passé entre-temps). Cas qui doit PASSER : l'id WordPress de la
traduction atteint l'original. Lancer : .venv/bin/python -m tests.test_corriger_dates
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.corriger_dates as cd  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    print(("OK    " if cond else "ÉCHEC ") + label + ("" if cond else f"  {detail}"))
    echecs += 0 if cond else 1


tmp = Path(tempfile.mkdtemp())
db = tmp / "e.db"
c = sqlite3.connect(db)
c.execute("CREATE TABLE events_raw (id INTEGER PRIMARY KEY, translation_of INT, duplicate_of INT, "
          "wp_post_id_as INT, statut TEXT, date_event_start TEXT, date_event_end TEXT)")
c.executemany("INSERT INTO events_raw VALUES (?,?,?,?,?,?,?)", [
    (1, None, None, 100, "p", "2027-03-27", "2027-06-21"),
    (2, 1, None, 200, "p", "2027-03-27", "2027-06-21"),
    (3, None, None, 300, "p", "2026-11-01", "2026-11-01"),   # déjà corrigée par quelqu'un
])
c.commit(); c.close()
cd.DB_PATH = db
src = "Texte publié : « s est tenu du 27 mars au 21 juin 2026 »"
l = tmp / "l.tsv"
l.write_text(f"200\t2026-03-27\t2026-06-21\t2027-03-27\t{src}\n"
             f"300\t2026-05-15\t2026-05-15\t2027-05-15\t{src}\n", encoding="utf-8")


def dates():
    k = sqlite3.connect(db)
    return {r[0]: (r[1], r[2]) for r in k.execute("SELECT id, date_event_start, date_event_end FROM events_raw")}


cd.main([str(l)])
_check("sans --apply : rien n'est écrit", dates()[1] == ("2027-03-27", "2027-06-21"))
rc = cd.main([str(l), "--apply"])
d = dates()
_check("id de la TRADUCTION → l'original corrigé", d[1] == ("2026-03-27", "2026-06-21"), d[1])
_check("… et la traduction", d[2] == ("2026-03-27", "2026-06-21"), d[2])
_check("fiche dont la base ne porte pas la date fausse : REFUSÉE, intacte",
       d[3] == ("2026-11-01", "2026-11-01"), d[3])
_check("un refus se voit dans le code retour", rc == 1, rc)
m = tmp / "m.tsv"
m.write_text("6453\t2026-13-01\t2026-06-21\t2027-03-27\t" + src + "\n", encoding="utf-8")
try:
    cd.main([str(m)]); _check("date illisible refusée", False)
except SystemExit as e:
    _check("date illisible refusée", "mal formée" in str(e))

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)"); sys.exit(1)
print("Tout passe.")
