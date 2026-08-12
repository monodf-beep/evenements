#!/usr/bin/env python3
"""Fixture : le rattrapage du panel. Base jetable, panel simulé — aucun appel réel.

CE QU'ELLE SURVEILLE, ET L'ORDRE COMPTE.

Ce script est le premier de la journée qui DÉPENSE de l'argent et qui touche à
`enrich_data`, la colonne où vivent les articles. Les deux risques ne sont donc pas les
mêmes que d'habitude :

  1. qu'un DRY-RUN appelle le modèle. Le panel est l'appel le plus répété du pipeline
     (plusieurs personas par fiche) : une simulation qui facture serait un piège, et on ne
     le découvrirait qu'à la facture ;
  2. qu'un ARTICLE soit réécrit. La charte l'interdit — le panel rend un verdict, jamais
     une publication. Le contrôle est explicite ici parce qu'aucune relecture de code ne
     rattrape une écriture qu'on n'a pas voulue ;
  3. qu'une fiche DÉJÀ jugée soit re-jugée : ce serait payer pour un second avis sur la
     même matière, et ne plus savoir lequel croire ;
  4. et seulement ensuite : que le verdict arrive bien là où publisher_as va le chercher.

Lancer : .venv/bin/python -m tests.test_panel_rattrapage
"""
import contextlib
import io
import json
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import panel_rattrapage  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


tmp = Path(tempfile.mkdtemp(prefix="fixture-panelrat-"))
db = tmp / "fixture.db"
conn = sqlite3.connect(db)
init_db(conn)

AVENIR = (date.today() + timedelta(days=30)).isoformat()
PASSE = (date.today() - timedelta(days=30)).isoformat()

LONG = "Le festival réunit cette année quatre ensembles baroques. " * 12
COURT = "Marché de producteurs, place du village."


def _ed(corps="", panel=None):
    d = {"article": {"corps": corps}}
    if panel is not None:
        d["reader_panel"] = panel
    return json.dumps(d, ensure_ascii=False)


CAS = [
    # id, titre, enrich_data, début, fin, wp
    (1, "Festival baroque", _ed(LONG), AVENIR, AVENIR, 7001),          # à relire
    (2, "Nuits de la guitare", _ed(LONG), AVENIR, AVENIR, 7002),       # à relire
    (3, "Déjà jugée", _ed(LONG, {"verdict": "ok", "mean": 4}), AVENIR, AVENIR, 7003),
    (4, "Entrée de catalogue", _ed(COURT), AVENIR, AVENIR, 7004),
    (5, "Jamais rédigée", _ed(""), AVENIR, AVENIR, 7005),
    (6, "Concert de mai", _ed(LONG), PASSE, PASSE, 7006),              # règle 5
    (7, "Brouillon", _ed(LONG), AVENIR, AVENIR, None),                 # non publiée
]
for eid, titre, ed, deb, fin, wp in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, enrich_data, url_source, source_name, "
        " date_event_start, date_event_end, statut, wp_post_id_as) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (eid, titre, ed, f"https://exemple.fr/{eid}", "Source officielle",
         deb, fin, "pending", wp))
conn.commit()
conn.close()
panel_rattrapage.DB_PATH = db


def _sortie(argv=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        panel_rattrapage.main(argv or [])
    return buf.getvalue()


print("──── 1. la sélection, et ce qu'elle ÉCARTE en le disant ────")
s = _sortie()
_check("les deux fiches sans verdict sont retenues", "[    1]" in s and "[    2]" in s)
_check("la fiche DÉJÀ jugée est écartée — on ne paie pas deux fois le même avis",
       "[    3]" not in s and "a déjà un verdict" in s)
_check("l'entrée de catalogue est écartée (le panel n'y a pas de prise)",
       "[    4]" not in s and "catalogue" in s)
_check("la fiche jamais rédigée est écartée", "[    5]" not in s and "rien à faire relire" in s)
_check("le PASSÉ est hors périmètre (règle 5)", "[    6]" not in s)
_check("une fiche non publiée est hors périmètre par défaut", "[    7]" not in s)
_check("… et --tout la fait entrer", "[    7]" in _sortie(["--tout"]))
_check("chaque écart est COMPTÉ, pas seulement subi", "écartées —" in s)

print("\n──── 2. le dry-run ne doit RIEN appeler ni RIEN écrire ────")


class _Explose:
    """Toute construction de client anthropic pendant un dry-run est une faute."""
    def __init__(self, *a, **k):
        raise AssertionError("le dry-run a tenté de construire un client anthropic")


import anthropic  # noqa: E402
_vrai = anthropic.Anthropic
anthropic.Anthropic = _Explose
try:
    s = _sortie()
    _check("aucun client de modèle n'est construit en simulation", "DRY-RUN" in s)
finally:
    anthropic.Anthropic = _vrai

avant = sqlite3.connect(db).execute(
    "SELECT enrich_data FROM events_raw WHERE id=1").fetchone()[0]
_check("   et enrich_data n'a pas bougé", "reader_panel" not in avant)

print("\n──── 3. --apply : le verdict arrive, l'article ne bouge pas ────")
_appels = []


def _faux_panel(article, ev, client, model):
    _appels.append(ev["id"])
    return {"verdict": "revise", "mean": 2.0, "votes": 2,
            "reviews": [{"verdict": "revise", "manques": ["aucun nom d'artiste"]}]}


import scripts.enrich as _enrich  # noqa: E402
_vrai_panel = _enrich.reader_panel
_enrich.reader_panel = _faux_panel
anthropic.Anthropic = lambda *a, **k: object()
import os  # noqa: E402
os.environ["ANTHROPIC_API_KEY"] = "fixture"
try:
    s = _sortie(["--apply", "--cap", "1"])
finally:
    _enrich.reader_panel = _vrai_panel
    anthropic.Anthropic = _vrai

_check("une seule fiche relue quand --cap 1", len(_appels) == 1, f"→ {_appels}")
_check("   et le plafond est ANNONCÉ, jamais silencieux", "au-delà de --cap" in s)

c = sqlite3.connect(db)
apres = json.loads(c.execute("SELECT enrich_data FROM events_raw WHERE id=?",
                             (_appels[0],)).fetchone()[0])
_check("le verdict est rangé là où publisher_as va le chercher",
       apres.get("reader_panel", {}).get("verdict") == "revise")
_check("   avec un statut de révision explicite, jamais vide",
       apres["reader_panel"].get("revision") == "aucune")
# LE CONTRÔLE QUI COMPTE LE PLUS DE TOUT CE FICHIER.
_check("L'ARTICLE N'A PAS ÉTÉ RÉÉCRIT — un verdict n'est pas une publication",
       apres["article"]["corps"] == LONG)
_check("le bilan RECOMPTE en base au lieu d'annoncer une longueur de liste",
       "vérifié(s) en base" in s)
_check("et il rappelle qu'aucun article n'a été touché",
       "AUCUN ARTICLE N'A ÉTÉ RÉÉCRIT" in s)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
