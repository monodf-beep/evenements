#!/usr/bin/env python3
"""Fixture : le mode « sans appel API » compte le bon périmètre et n'appelle aucun modèle.

Le plafond API est atteint jusqu'au 2026-09-01. La chaîne peut pourtant continuer :
dater par le texte et par la page, apparier un lieu sur le référentiel, prendre l'og:image
de la page officielle, et publier — rien de tout cela n'a jamais eu besoin d'un modèle.
Encore faut-il que le compte affiché soit juste, sinon on lance un lot pour rien.

Ce que la fixture vérifie :
  • le périmètre suit la règle 5 — une fiche PASSÉE ne compte pas dans les manques, un
    RÉCURRENT compte même si sa date est derrière nous, une fiche SANS date compte comme
    « sans date » et non comme « passée » ;
  • les dérogations de utils/completeness sont respectées : un récurrent n'a pas besoin de
    date, un événement multi-lieux n'a pas besoin de lieu ;
  • en simulation, AUCUNE étape n'est exécutée — c'est la promesse du dry-run (règle 4) ;
  • le bilan compare deux photographies de la base, pas des intentions (règle 6).

Lancer : .venv/bin/python -m tests.test_sans_api
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
import scripts.sans_api as sa  # noqa: E402

sa.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


AUJOURDHUI = "2026-08-11"
conn = sqlite3.connect(tmp)
init_db(conn)
try:
    conn.execute("ALTER TABLE events_raw ADD COLUMN multi_lieux INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass

# (id, titre, date_start, lieu, image, date_end, wp, recurring, multi_lieux)
CAS = [
    (1, "Sans date, à venir",        "",           "Salle", "http://i", "2026-12-01", None, 0, 0),
    (2, "Sans lieu, à venir",        "2026-12-01", "",      "http://i", "2026-12-01", None, 0, 0),
    (3, "Sans image, à venir",       "2026-12-01", "Salle", "",         "2026-12-01", None, 0, 0),
    (4, "Complète et en ligne",      "2026-12-01", "Salle", "http://i", "2026-12-01", 771,  0, 0),
    (5, "Sans image mais PASSÉE",    "2026-05-01", "Salle", "",         "2026-05-01", None, 0, 0),
    (6, "Récurrent sans date",       "",           "Salle", "http://i", "",           None, 1, 0),
    (7, "Multi-lieux sans lieu",     "2026-12-01", "",      "http://i", "2026-12-01", None, 0, 1),
    (8, "En cours (mai→septembre)",  "2026-05-01", "Salle", "",         "2026-09-20", None, 0, 0),
]
for eid, titre, ds, lieu, img, fin, wp, rec, multi in CAS:
    conn.execute(
        "INSERT INTO events_raw (id,title,url_source,statut,date_event_start,lieu,"
        "url_image,date_event_end,wp_post_id_as,recurring,multi_lieux) "
        "VALUES (?,?,?, 'evaluated', ?,?,?,?,?,?,?)",
        (eid, titre, f"https://x/{eid}", ds, lieu, img, fin, wp, rec, multi))
conn.commit()

print("──── périmètre des manques ────")
etat = sa._etat(conn, AUJOURDHUI)
conn.close()

_check("sans date = 1 (la fiche 1 ; le récurrent 6 est dispensé de date)",
       etat["sans_date"] == 1, str(etat))
_check("sans lieu = 1 (la fiche 2 ; la multi-lieux 7 est dispensée de lieu)",
       etat["sans_lieu"] == 1, str(etat))
_check("sans image = 2 (fiches 3 et 8 ; la 5 est PASSÉE, elle ne compte pas)",
       etat["sans_image"] == 2, str(etat))
_check("en ligne = 1", etat["en_ligne"] == 1, str(etat))

# ── Le dry-run ne lance rien : c'est toute sa raison d'être ─────────────────────
print("\n──── simulation : aucune étape exécutée ────")
lancees = []
for mod in ("scripts.dates", "scripts.venues", "scripts.visuals",
            "scripts.publish_batch_as"):
    m = __import__(mod, fromlist=["main"])
    m.main = (lambda nom: (lambda argv=None: lancees.append(nom) or 0))(mod)
code = sa.main([])
_check("code retour 0", code == 0, str(code))
_check("aucune étape lancée en simulation", lancees == [], str(lancees))

# ── --apply les lance, dans l'ordre imposé par la porte qualité ─────────────────
print("\n──── --apply : les quatre étapes, dans l'ordre ────")
lancees.clear()
sa.main(["--apply"])
_check("les quatre étapes sont lancées dans l'ordre dater → lieu → image → publier",
       lancees == ["scripts.dates", "scripts.venues", "scripts.visuals",
                   "scripts.publish_batch_as"], str(lancees))

print("\n──── --sans-publication s'arrête avant la mise en ligne ────")
lancees.clear()
sa.main(["--apply", "--sans-publication"])
_check("la publication n'est pas lancée",
       "scripts.publish_batch_as" not in lancees, str(lancees))
_check("les trois étapes de complétion le sont", len(lancees) == 3, str(lancees))

# ── Une étape qui plante ne prive pas les suivantes de leur tour ────────────────
print("\n──── une étape en échec n'annule pas les autres ────")
lancees.clear()
import scripts.venues as venues
venues.main = lambda argv=None: (_ for _ in ()).throw(RuntimeError("panne simulée"))
sa.main(["--apply"])
_check("visuals et publish tournent malgré l'échec de venues",
       "scripts.visuals" in lancees and "scripts.publish_batch_as" in lancees,
       str(lancees))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
