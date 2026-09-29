#!/usr/bin/env python3
"""Fixture : un événement digne de la une reçoit un article LONG, et son score de rendu
atteint sa traduction. Base jetable, aucun appel de modèle.

⚠️ BASE JETABLE — jamais data/events.db.

D'OÙ ÇA VIENT (2026-09-29). Franck : « à la une, ça doit être les meilleurs événements,
donc forcément on doit avoir des événements ». Mesuré ce jour-là : 52 fiches en ligne et à
venir sans panel de lecteurs, donc sans score de rendu, donc exclues de la une — parce que
le palier court/long se décidait sur `llm_score` seul, et que le panel ne relit que les
articles longs. Deux détecteurs pour la même chose, un seul consulté.

CE QU'ELLE SURVEILLE :
  1. le PALIER — noté 5 mais 8/10 d'intérêt → LONG ; 5/10 d'intérêt → COURT ;
     ⚠️ le cas qui doit PASSER près de la frontière : intérêt pile au plancher (6) → LONG ;
     intérêt NON MESURÉ → COURT (« pas mesuré » n'est pas « digne ») ; `court` forcé
     reste court ;
  2. le GESTE que rescore_home désigne pour chaque fiche non calculable : la commande
     `enrich` ne doit viser QUE les articles courts dignes de la une — jamais une
     traduction, jamais une fiche sans intérêt pour la une (c'était 52 ids d'un bloc) ;
  3. la COPIE du score sur la traduction : absente en simulation, présente après --apply,
     et jamais sur une traduction dont l'original n'a pas de score.

Lancer : .venv/bin/python -m tests.test_une_palier_et_rendu
"""
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp())
os.environ["DB_PATH"] = str(TMP / "fixture.db")

from scripts import enrich  # noqa: E402
from scripts import rescore_home  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def _check(nom, ok, detail=""):
    global echecs
    print(("  ✓ " if ok else "  ✗ ") + nom + ("" if ok else f"\n      → {detail}"))
    if not ok:
        echecs += 1


def _detail(ray, spec, trad):
    """Intérêt = ray×2 + spec×3 + trad×1 (utils.deplacement._PONDERATION)."""
    return json.dumps({"rayonnement": {"points": ray},
                       "specificite_territoriale": {"points": spec},
                       "edition_tradition": {"points": trad}})


INTERET_8, INTERET_6, INTERET_5 = _detail(2, 1, 1), _detail(1, 1, 1), _detail(1, 1, 0)

print("1. Le palier suit aussi l'intérêt de la une")
cas = [
    ("noté 5, intérêt 8 → LONG", {"llm_score": 5, "llm_score_detail": INTERET_8}, "auto", False),
    ("noté 5, intérêt 5 → COURT", {"llm_score": 5, "llm_score_detail": INTERET_5}, "auto", True),
    ("⚠️ noté 5, intérêt PILE au plancher (6) → LONG (le cas qui doit passer)",
     {"llm_score": 5, "llm_score_detail": INTERET_6}, "auto", False),
    ("noté 5, intérêt non mesuré → COURT", {"llm_score": 5, "llm_score_detail": None}, "auto", True),
    ("noté 8, intérêt 5 → LONG (inchangé)", {"llm_score": 8, "llm_score_detail": INTERET_5}, "auto", False),
    ("mode « court » forcé → COURT même digne", {"llm_score": 5, "llm_score_detail": INTERET_8}, "court", True),
]
for nom, ev, mode, attendu in cas:
    court, _ = enrich._tier_model(ev, mode)
    _check(nom, court is attendu, f"court={court}")

print("\n2. rescore_home désigne le BON geste, fiche par fiche")
db = TMP / "fixture.db"
conn = sqlite3.connect(db)
init_db(conn)
cols = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
for col, decl in (("translation_of", "INTEGER"), ("enrich_data", "TEXT"), ("home_score", "REAL"),
                  ("llm_score_detail", "TEXT"), ("wp_post_id_as", "INTEGER"),
                  ("date_event_start", "TEXT"), ("date_event_end", "TEXT"),
                  ("url_officiel", "TEXT")):
    if col not in cols:
        conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
demain = (date.today() + timedelta(days=5)).isoformat()
LONG = "x" * 900
COURT = "y" * 200
AVEC_PANEL = {"article": {"corps": LONG}, "reader_panel": {"mean": 4.0},
              "source": {"officielle": True, "pages": []}}
fiches = [
    # id, titre, detail, enrich_data, translation_of
    (1, "Original noté", INTERET_8, AVEC_PANEL, None),
    (2, "Sa traduction", INTERET_8, {"article": {"corps": LONG}}, 1),
    (3, "Long sans panel", INTERET_5, {"article": {"corps": LONG}, "source": {}}, None),
    (4, "Court digne", INTERET_8, {"article": {"corps": COURT}, "source": {}}, None),
    (5, "Court sans intérêt", INTERET_5, {"article": {"corps": COURT}, "source": {}}, None),
    (6, "Traduction d'un sans-score", INTERET_8, {"article": {"corps": COURT}}, 4),
]
for i, titre, det, data, tr in fiches:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, statut, wp_post_id_as, date_event_start,"
        " date_event_end, llm_score, llm_score_detail, enrich_data, translation_of)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (i, titre, f"https://ex/{i}", "published_sub", 100 + i, demain, demain, 5, det,
         json.dumps(data), tr))
conn.commit()
conn.close()

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rescore_home.main(["--db", str(db)])
sortie = buf.getvalue()
cmd = next((l for l in sortie.splitlines() if "scripts.enrich" in l), "")
_check("la commande enrich ne vise QUE la fiche courte digne de la une (4)",
       cmd.strip().endswith("scripts.enrich 4"), cmd or sortie)
_check("le long sans panel part au panel (3), pas à la réécriture",
       "panel_rattrapage" in sortie and "[    3]" in sortie.split("panel_rattrapage")[1][:400],
       sortie)
_check("le court sans intérêt : « rien à faire » (5)", "rien à faire" in sortie, sortie)
_check("les traductions ne sont jamais envoyées à enrich", " 2" not in cmd and " 6" not in cmd, cmd)

conn = sqlite3.connect(db)
t = conn.execute("SELECT home_score FROM events_raw WHERE id=2").fetchone()[0]
conn.close()
_check("simulation : la traduction n'a rien reçu", t is None, t)

print("\n3. --apply : l'original est noté, sa traduction reçoit la copie")
with contextlib.redirect_stdout(io.StringIO()):
    rescore_home.main(["--db", str(db), "--apply"])
conn = sqlite3.connect(db)
sc = dict(conn.execute("SELECT id, home_score FROM events_raw").fetchall())
conn.close()
_check("original (1) noté", sc[1] is not None, sc)
_check("traduction (2) = score de l'original", sc[2] == sc[1], sc)
_check("traduction d'un original sans score (6) : toujours rien", sc[6] is None, sc)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
