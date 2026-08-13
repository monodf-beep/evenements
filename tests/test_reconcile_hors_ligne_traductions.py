#!/usr/bin/env python3
"""Fixture : ce que `--subis` REPUBLIERAIT, et pourquoi ça ne se ressemble pas.

⚠️ BASE JETABLE — jamais data/events.db. AUCUN RÉSEAU : `_etat` est remplacé par une
table post → état.

D'OÙ ÇA VIENT. Le 2026-08-13, le dry-run listait vingt-six « retraits présumés SUBIS »,
toutes lignes identiques à l'œil. J'ai averti Franck que republier 3533 et 4195
« recréerait les doublons qu'on vient de constater ».

C'était faux. 3533 est la version ITALIENNE de la fiche 49 (Montrottier), et 4195 la
version italienne de 3026 (Chagall) — deux fiches françaises encore en ligne. Les
republier ne fabrique aucun doublon : ça rend au site les pages italiennes qui lui
manquent. Je raisonnais sur une liste qui n'affichait pas ce qui distinguait ses lignes,
et j'ai comblé le silence par une inquiétude.

LA DISTINCTION QUI DÉCIDE, et que la base connaît déjà : la fiche est-elle la traduction
d'un original dont la page est ENCORE PUBLIQUE ?

  · oui  → republier rend la langue manquante. Réparation, pas pari.
  · non  → on remet en ligne une page que quelqu'un a peut-être retirée exprès.

CE QUE LA FIXTURE VÉRIFIE, dans l'ordre où ça compte :
  1. le cas « traduction d'un original EN LIGNE » est nommé, et nommé distinctement ;
  2. le cas « les deux langues sont hors ligne » ne se confond pas avec lui ;
  3. une fiche qui n'est pas une traduction ne reçoit AUCUNE de ces mentions — sinon on
     rassurerait sur des lignes où le pari demeure entier ;
  4. rien n'est écrit : ce script est en dry-run par défaut.

Lancer : .venv/bin/python -m tests.test_reconcile_hors_ligne_traductions
"""
import contextlib
import io
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.reconcile_hors_ligne as rh  # noqa: E402

rh.DB_PATH = tmp

FUTUR = (date.today() + timedelta(days=40)).isoformat()

# id, titre, wp, statut, translation_of
FICHES = [
    # ① l'original français, EN LIGNE — c'est lui qui rend l'italien légitime
    (49, "Visite au Château de Montrottier", 795, "published_sub", None),
    # ② sa traduction italienne, retirée du site : la republier rend la langue manquante
    (3533, "Visita al Castello di Montrottier", 2311, "published_sub", 49),
    # ③ une paire dont LES DEUX langues sont hors ligne — cas différent, à ne pas confondre
    (60, "Mostra fantasma", 900, "published_sub", None),
    (61, "Exposition fantôme", 901, "published_sub", 60),
    # ④ une fiche seule, sans traduction : le pari reste entier, on ne rassure pas
    (70, "Concert isolé", 910, "published_sub", None),
]

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, titre, wp, statut, trad in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, wp_post_id_as, statut, "
        "date_event_start, date_event_end, translation_of, duplicate_of) "
        "VALUES (?,?,?,?,?,?,?,?, NULL)",
        (eid, titre, f"https://a.fr/{eid}", wp, statut, FUTUR, FUTUR, trad))
conn.commit()
conn.close()

# Ce que WordPress répond. Seul le post 795 (fiche 49) est encore public.
ETATS = {795: "public", 2311: "non_public", 900: "non_public", 901: "non_public",
         910: "non_public"}
rh._etat = lambda wp_url, post_id: ETATS.get(int(post_id), "non_public")

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = rh.main(["--delay", "0"])
sortie = buf.getvalue()

_check("rc=0 (dry-run, lecture seule)", rc == 0, sortie[-300:])

print("\n──── 1. la traduction d'un original EN LIGNE est nommée ────")
ligne_3533 = next((l for l in sortie.splitlines() if "[ 3533]" in l or "[3533]" in l), "")
_check("la ligne 3533 dit que son original est en ligne",
       "dont la page est EN LIGNE" in ligne_3533, ligne_3533 or sortie[-1200:])
_check("   et elle dit ce que la republication PRODUIT, pas seulement ce qu'elle est",
       "rend la langue manquante" in ligne_3533, ligne_3533)

print("\n──── 2. les deux langues hors ligne, ce n'est PAS le même cas ────")
ligne_61 = next((l for l in sortie.splitlines() if "[   61]" in l or "[61]" in l), "")
_check("la ligne 61 le dit autrement", "les deux langues sont hors ligne" in ligne_61,
       ligne_61 or sortie[-1200:])
_check("   et surtout PAS « rend la langue manquante » — il n'y a rien à rendre",
       "rend la langue manquante" not in ligne_61, ligne_61)

print("\n──── 3. on ne rassure pas là où le pari reste entier ────")
ligne_70 = next((l for l in sortie.splitlines() if "[   70]" in l or "[70]" in l), "")
_check("une fiche sans traduction ne reçoit aucune mention de traduction",
       "traduction" not in ligne_70.lower(), ligne_70 or sortie[-1200:])
_check("   et l'avertissement général sur --subis reste affiché pour tout le lot",
       "annule en silence" in sortie, sortie[-1500:])

print("\n──── 4. rien n'a été écrit ────")
c = sqlite3.connect(tmp)
restants = c.execute("SELECT COUNT(*) FROM events_raw "
                     "WHERE COALESCE(wp_post_id_as,0) > 0").fetchone()[0]
statuts = dict(c.execute("SELECT id, statut FROM events_raw"))
c.close()
_check("les cinq liens WordPress sont intacts", restants == 5, str(restants))
_check("   et aucun statut n'a bougé",
       all(statuts[eid] == st for eid, _t, _w, st, _tr in FICHES), str(statuts))

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
