#!/usr/bin/env python3
"""Fixture : scripts/poser_source.py pose `url_officiel` sur TOUT le groupe (original +
traductions), ne touche à rien d'autre, et n'écrit RIEN sans --apply.

Cas qui doit PASSER près de la frontière : l'id WordPress de la TRADUCTION atteint aussi
l'original. Et la source posée doit être celle que publisher_as publie — sinon poser la
colonne ne servirait à rien.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_poser_source
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.poser_source as ps  # noqa: E402
from scripts.publisher_as import _source_publiable  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    print(("OK    " if cond else "ÉCHEC ") + label + ("" if cond else f"  {detail}"))
    echecs += 0 if cond else 1


tmp = Path(tempfile.mkdtemp())
db = tmp / "events.db"
c = sqlite3.connect(db)
c.execute("CREATE TABLE events_raw (id INTEGER PRIMARY KEY, translation_of INT, duplicate_of INT, "
          "wp_post_id_as INT, statut TEXT, url_officiel TEXT, url_source TEXT)")
FAUX = "https://museipiemonte.cultura.gov.it/2026/07/10/castello-di-racconigi/"
c.executemany("INSERT INTO events_raw VALUES (?,?,?,?,?,?,?)", [
    (1, None, None, 100, "published_sub", FAUX, "https://x/a"),
    (2, 1, None, 200, "published_sub", "", "translated:1:it"),
    (3, None, None, 300, "published_sub", "https://autre.it/p", "https://autre.it/p"),
])
c.commit(); c.close()
ps.DB_PATH = db
appels = []
ps.subprocess.call = lambda cmd: appels.append(cmd) or 0
BON = "https://museipiemonte.cultura.gov.it/2026/09/18/giornate-europee/"
liste = tmp / "l.tsv"
liste.write_text(f"# c\n200\t{BON}\tmotif\n", encoding="utf-8")

ps.main([str(liste)])
_check("sans --apply : rien n'est écrit",
       sqlite3.connect(db).execute("SELECT url_officiel FROM events_raw WHERE id=1").fetchone()[0] == FAUX)
_check("sans --apply : aucune republication", not appels)

ps.main([str(liste), "--apply"])
c = sqlite3.connect(db); c.row_factory = sqlite3.Row
g = {r["id"]: dict(r) for r in c.execute("SELECT * FROM events_raw")}
_check("id de la TRADUCTION → l'original reçoit la source", g[1]["url_officiel"] == BON)
_check("… et la traduction aussi", g[2]["url_officiel"] == BON)
_check("url_source intacte (UNIQUE, ancre de la paire)", g[2]["url_source"] == "translated:1:it")
_check("fiche sans rapport intacte", g[3]["url_officiel"] == "https://autre.it/p")
_check("c'est bien la source que publisher_as publie", _source_publiable(g[1], False) == BON,
       _source_publiable(g[1], False))
_check("republication des fiches en ligne du groupe", appels and appels[-1][-2:] == ["1", "2"], appels)

mauvaise = tmp / "m.tsv"
mauvaise.write_text("abc\thttps://x\tm\n", encoding="utf-8")
try:
    ps.main([str(mauvaise)]); _check("ligne mal formée refusée", False)
except SystemExit as e:
    _check("ligne mal formée refusée", "mal formée" in str(e))

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)"); sys.exit(1)
print("Tout passe.")
