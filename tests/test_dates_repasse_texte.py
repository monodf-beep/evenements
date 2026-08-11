#!/usr/bin/env python3
"""Fixture : la passe texte de dates.py se rejoue, et n'efface jamais rien.

Franck, le 2026-08-11 au soir, devant la file « À compléter » à 68 : « on a toujours trop
de tâches ». La cause n'était pas la collecte, c'était une SÉLECTION.

La passe 1 de `scripts/dates.py` lit la date dans le titre et la description. Elle est
gratuite et instantanée. Elle ne passait pourtant qu'UNE FOIS par fiche : sa requête
portait sur `date_source` vide, or dès le premier échec cette colonne passait à 'none',
et la fiche sortait définitivement de son champ de vision.

Entre-temps la matière change — `dedupe` fusionne une fiche mieux titrée, `enrich` écrit
un `article_title` qui porte la date, le parseur s'améliore. Le parseur d'aujourd'hui lit
sans hésiter « les 8 et 9 août » dans le titre de la fiche 3083, affichée « date ? »
depuis des semaines. Et l'absence de date est un CERCLE VICIEUX : sans elle, la règle 5
interdit de classer la fiche en « passé » — donc elle ne quitte aucune file. Le Tour de
France Femmes, terminé le 9 août, occupait encore l'écran le 11 pour cette seule raison.

CE QUE LA FIXTURE PROTÈGE EN PREMIER : qu'en se rejouant, la passe n'EFFACE rien. C'est
le risque que la relance introduit et que l'ancienne version ne courait pas. Une fiche qui
n'a qu'une date de fin (« jusqu'au 20 septembre ») verrait cette fin réécrite à vide au
premier passage où le parseur échoue.

Lancer : .venv/bin/python -m tests.test_dates_repasse_texte
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import dates as dates_mod  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


tmp = Path(tempfile.mkdtemp(prefix="fixture-dates-"))
db = tmp / "events.db"
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
init_db(conn)
dates_mod.DB_PATH = db
dates_mod.ensure_columns(conn)
for col in ("article_title TEXT", "translation_of INTEGER"):
    try:
        conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col}")
    except sqlite3.OperationalError:
        pass

CAS = [
    # (id, titre, description, article_title, date_source, start, end)
    # 1 — LE CAS DU 11/08 : déjà déclarée « non datable », mais son titre porte la date.
    (1, "Le Tour de France Femmes 2026 s'achève à Nice les 8 et 9 août", "", "",
     "none", "", ""),
    # 2 — datable seulement par le titre d'ARTICLE (le titre brut du flux est muet).
    (2, "Communiqué de presse", "", "Cinéma de plein air : programmation du 11 au 29 août",
     "none", "", ""),
    # 3 — n'a QU'UNE date de fin, et son texte n'est plus datable : à ne pas effacer.
    (3, "Exposition permanente", "", "", "parsed", "", "2026-09-20"),
    # 4 — déjà datée : hors sélection, rien ne doit bouger.
    (4, "Concert du 5 mai", "", "", "page", "2026-05-05", "2026-05-05"),
    # 5 — vraiment indatable : doit rester à 'none' pour que la passe page la reprenne.
    (5, "Nice Jazz Fest", "Trois soirées au Théâtre de Verdure.", "", "", "", ""),
    # 6 — TRADUCTION : ses dates sont copiées de l'original, jamais re-dérivées.
    (6, "Il Tour de France Femmes si conclude l'8 e 9 agosto", "", "", "", "", ""),
]
for eid, titre, desc, art, src, s, e in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, article_title, "
        "date_source, date_event_start, date_event_end) VALUES (?,?,?,?,?,?,?,?)",
        (eid, titre, desc, f"https://exemple.fr/{eid}", art, src, s, e))
conn.execute("UPDATE events_raw SET translation_of=1 WHERE id=6")
conn.commit()
conn.close()


def _lire(eid):
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    r = c.execute("SELECT date_event_start s, date_event_end e, date_source src "
                  "FROM events_raw WHERE id=?", (eid,)).fetchone()
    c.close()
    return r["s"], r["e"], r["src"]


dates_mod.main(["--no-fetch", "--no-llm", "--no-republish"])

print("──── la fiche que l'ancienne sélection ne regardait plus ────")
_check("fiche 1 datée depuis son titre malgré date_source='none'",
       _lire(1)[:2] == ("2026-08-08", "2026-08-09"), str(_lire(1)))
_check("… et sa provenance est 'parsed'", _lire(1)[2] == "parsed", str(_lire(1)))

print("\n──── le titre d'article, quand le titre brut est muet ────")
_check("fiche 2 datée depuis article_title", _lire(2)[:2] == ("2026-08-11", "2026-08-29"),
       str(_lire(2)))
_check("… avec une provenance distincte, pour pouvoir y revenir",
       _lire(2)[2] == "parsed_article", str(_lire(2)))

print("\n──── CE QUI NE DOIT SURTOUT PAS ARRIVER : effacer ────")
_check("fiche 3 : la date de fin seule survit à une passe qui échoue",
       _lire(3)[1] == "2026-09-20", str(_lire(3)))
_check("fiche 4 : une fiche déjà datée n'est pas touchée",
       _lire(4)[:2] == ("2026-05-05", "2026-05-05"), str(_lire(4)))
_check("fiche 4 : sa provenance non plus", _lire(4)[2] == "page", str(_lire(4)))

print("\n──── les autres ────")
_check("fiche 5 indatable → 'none', pour que la passe page la reprenne",
       _lire(5) == ("", "", "none"), str(_lire(5)))
# La traduction ne doit JAMAIS être datée par le parseur : son titre italien passé à un
# parseur écrit pour le français a déjà produit des dates fausses (Jazz Art : 2 mois
# d'écart ; Matisse : 1 mois, incident du 2026-08-02). Elle reçoit ses dates par COPIE de
# son original — et c'est un effet secondaire heureux de cette correction : dater la
# fiche 1 date aussi sa traduction, dans le même run.
_check("fiche 6 (traduction) non datée par le TEXTE mais copiée de son original",
       _lire(6)[2] == "copie-traduction", str(_lire(6)))
_check("… et la copie porte bien les dates de l'original",
       _lire(6)[:2] == _lire(1)[:2], f"{_lire(6)} vs {_lire(1)}")

print("\n──── on rejoue : rien ne se dégrade ────")
avant = [_lire(i) for i in range(1, 7)]
dates_mod.main(["--no-fetch", "--no-llm", "--no-republish"])
_check("deuxième passage identique au premier",
       [_lire(i) for i in range(1, 7)] == avant,
       str([_lire(i) for i in range(1, 7)]))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s). Base jetable : {tmp}")
sys.exit(1 if echecs else 0)
