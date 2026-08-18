#!/usr/bin/env python3
"""Fixture : le rafraîchisseur doit reprendre AUSSI les fiches dont seule la une bouge.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau (on ne teste que le DRY-RUN, qui
n'interroge ni WordPress ni l'API).

D'OÙ ÇA VIENT (2026-08-18), et c'est une récidive dont le remède était déjà écrit.
`as_une_now` a été créé la veille : un score d'intérêt RELEVÉ PAR LA DATE, calculé par
`publisher_as` à la publication, donc GELÉ ensuite. Or `refresh_deplacement.py` existe
depuis le 2026-08-04 précisément parce qu'une méta de cette nature dérive — sa docstring
énumère les trois dérives, et la question de la règle 3 sous sa forme « qui RECALCULE ? ».

Personne ne recalculait `as_une_now`. Le correctif censé supprimer « ça fait des semaines
qu'ils sont à la une » aurait donc recréé la plainte par un autre chemin : le Tour de
l'Avenir, à 13 aujourd'hui, serait resté à 13 en octobre, en tête de la vitrine.

C'est Novamira qui l'a signalé en lisant la méta — pas moi en écrivant le code.

CE QUE LA FIXTURE SURVEILLE :
  1. une fiche dont SEULE la note de une change est reprise — c'est tout l'objet ;
  2. un événement PASSÉ sort de la une par une valeur VIDE, jamais par un « 0 » qui le
     rangerait dernier au lieu de le retirer ;
  3. ⚠️ le cas qui doit PASSER : une fiche dont AUCUNE des deux valeurs ne bouge n'est pas
     republiée. Sans lui, on ne prouverait que la capacité à tout reprendre — et republier
     360 fiches par jour pour rien est le défaut que ce script a été écrit pour éviter ;
  4. l'aperçu montre les DEUX transitions, pour qu'on sache laquelle des deux sections est
     concernée.

Lancer : .venv/bin/python -m tests.test_refresh_une_now
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

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)
os.environ["WP_AS_URL"] = "https://exemple.invalid"   # jamais appelé : dry-run seulement

from scripts.scraper_events import init_db          # noqa: E402
import scripts.refresh_deplacement as rd            # noqa: E402
from utils.une import une_now                       # noqa: E402
from utils.deplacement import deplacement_now       # noqa: E402

rd.DB_PATH = tmp
AUJ = date.today()
DANS_8_J = (AUJ + timedelta(days=8)).isoformat()
PASSE = (AUJ - timedelta(days=5)).isoformat()

DETAIL = json.dumps({"rayonnement": {"points": 2}, "specificite_territoriale": {"points": 1},
                     "edition_tradition": {"points": 2}, "notoriete_lieu": {"points": 3}})
ARTICLE = json.dumps({"article": {"chapo": "Le grand rendez-vous revient.",
                                  "corps": "Une journée entière de spectacles."},
                      "home": {"affiches": "deux"}})

# (id, titre, début, fin, deplacement_publie, une_publie)
FICHES = [
    # 1. IMMINENTE : sa note de une vaut 13 aujourd'hui. On l'enregistre comme publiée à
    #    une AUTRE valeur → elle doit être reprise.
    (1, "Tour de l'Avenir", DANS_8_J, DANS_8_J, None, "9"),
    # 2. PASSÉE : `une_now` renvoie None → la méta doit devenir VIDE, pas "0".
    (2, "Fête déjà passée", PASSE, PASSE, None, "11"),
    # 3. ⚠️ LE CAS QUI DOIT PASSER : déjà à jour sur les deux → aucune republication.
    (3, "Déjà à jour", DANS_8_J, DANS_8_J, None, None),
]

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, titre, deb, fin, dep_pub, une_pub in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, wp_post_id_as, statut, "
        "llm_categorie, llm_score_detail, date_event_start, date_event_end, territoire, "
        "duplicate_of, enrich_status, home_score, url_image, enrich_data, article_title) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,NULL,?,?,?,?,?)",
        (eid, titre, f"https://a.fr/{eid}", 900 + eid, "published_sub", "Festivals",
         DETAIL, deb, fin, "Piemonte", "enriched", 8.0,
         f"https://exemple.fr/p/{eid}.jpg", ARTICLE, titre))
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


# Les colonnes de suivi sont créées par le script lui-même ; on les remplit ensuite, en
# posant sur la fiche 3 la valeur EXACTE que le calcul rendra aujourd'hui — c'est ce qui
# la rend « déjà à jour » quelle que soit la date à laquelle la fixture tourne.
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
rd._ensure_col(conn)
for eid, _t, _d, _f, dep_pub, une_pub in FICHES:
    if une_pub is not None:
        conn.execute("UPDATE events_raw SET une_now_publie=? WHERE id=?", (une_pub, eid))
ligne3 = dict(conn.execute("SELECT * FROM events_raw WHERE id=3").fetchone())
conn.execute("UPDATE events_raw SET deplacement_now_publie=?, une_now_publie=? WHERE id=3",
             (rd._valeur(ligne3, AUJ), rd._valeur_une(ligne3, AUJ)))
# Les fiches 1 et 2 doivent aussi avoir leur déplacement à jour, sinon elles seraient
# reprises pour CE motif-là et la fixture ne prouverait rien sur la une.
for eid in (1, 2):
    l = dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())
    conn.execute("UPDATE events_raw SET deplacement_now_publie=? WHERE id=?",
                 (rd._valeur(l, AUJ), eid))
conn.commit()
conn.close()

print("──── ce que les deux formules disent, avant tout ────")
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
lignes = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM events_raw")}
conn.close()
_check(f"l'imminente vaut bien 13 en une ({une_now(lignes[1], AUJ)})",
       une_now(lignes[1], AUJ) == 13, str(une_now(lignes[1], AUJ)))
_check("la passée sort de la une (None, pas 0)", une_now(lignes[2], AUJ) is None)
_check("   et sa méta s'écrit VIDE, pas '0' — sortir n'est pas être classé dernier",
       rd._valeur_une(lignes[2], AUJ) == "", repr(rd._valeur_une(lignes[2], AUJ)))
_check("le déplacement des trois est déjà à jour — la une est donc le SEUL motif possible",
       all(lignes[i]["deplacement_now_publie"] == rd._valeur(lignes[i], AUJ)
           for i in (1, 2, 3)),
       {i: (lignes[i]["deplacement_now_publie"], rd._valeur(lignes[i], AUJ))
        for i in (1, 2, 3)})

print("\n──── ce que le dry-run reprend ────")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rd.main([])
sortie = buf.getvalue()

_check("la fiche dont seule la une a bougé est reprise",
       "[    1]" in sortie, sortie)
_check("   et l'aperçu montre sa transition de une (9 → 13)",
       "une          9 → 13" in sortie, sortie[sortie.find("[    1]"):][:220])
_check("la fiche passée est reprise pour sortir de la une",
       "[    2]" in sortie and "(hors une)" in sortie, sortie)
# ⚠️ ÉCRIT D'ABORD `"[    3]" in sortie is False`, qui est TOUJOURS faux : Python
# enchaîne les comparaisons, donc ça se lit `(x in sortie) and (sortie is False)`.
# L'assertion partait au rouge alors que le code faisait exactement ce qu'il fallait —
# une ligne qui dit une chose et en teste une autre, dans le fichier même qui est là
# pour empêcher ça.
_check("⚠️ celle qui n'a bougé sur AUCUNE des deux n'est PAS republiée "
       "(le cas qui doit passer)",
       "[    3]" not in sortie and "Déjà à jour" not in sortie, sortie)
_check("l'aperçu nomme les deux sections, pas seulement « republiée »",
       "déplacement" in sortie and "· une" in sortie, sortie[:600])
_check("rien n'a été écrit — c'est un dry-run",
       "Dry-run" in sortie, sortie[-300:])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
