#!/usr/bin/env python3
"""Fixture : la presse n'entre plus, ni par les flux ni par les newsletters.

Franck, 2026-08-11 : « on a encore du guida torino ? alors que c'est du radar et qu'on
en veut pas ? il faut faire un vrai travail sur les sources en enlevant les radar, je
veux que des sources officielles. »

Le trou était précis. Le tier radar a été supprimé de config/sources.txt le 05/08 et 146
fiches purgées — mais les newsletters entrent par scripts/gmail_collect.py, qui ne
consultait AUCUNE des deux listes. guidatorino.com figurait pourtant déjà dans
config/non_institutional_sources.txt : la liste existait, ce canal ne la lisait pas.

Deux volets, parce qu'il y a deux moments :
  1. l'ENTRÉE — `gmail_collect.expediteur_officiel` refuse le mail avant l'extraction
     (donc avant l'appel LLM, et sans créer de fiche à purger ensuite) ;
  2. le PASSÉ — `purge_sources_non_officielles` traite ce qui est déjà en base.

Les cas sont pris des deux côtés de la frontière, et c'est là que tout se joue : une
newsletter de LA VENARIA REALE ou des MUSÉES DE CHAMBÉRY est parfaitement légitime. Un
filtre trop large couperait les meilleures sources du catalogue.

Lancer : .venv/bin/python -m tests.test_sources_non_officielles
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
from scripts.gmail_collect import expediteur_officiel  # noqa: E402
import scripts.purge_sources_non_officielles as pu  # noqa: E402

pu.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── entrée : quels expéditeurs sont acceptés ────")
EXPEDITEURS = [
    ("GuidaTorino <news@guidatorino.com>", False, "guide/presse turinois"),
    ("Newsletter Mentelocale <noreply@mentelocale.it>", False, "guide en ligne"),
    ('"Quotidiano Piemontese" <info@quotidianopiemontese.it>', False, "quotidien"),
    # ── Et surtout : ce qui doit PASSER. Ce sont nos meilleures sources ──────────
    ("La Venaria Reale <newsletter@lavenaria.it>", True, "le lieu lui-même"),
    ('"Musées" <musees.actualites@mairie-chambery.fr>', True, "une mairie"),
    ('"Département des Alpes-Maritimes" <alpes@departement06.fr>', True, "une collectivité"),
    ("Musei Reali Torino <info@museireali.it>", True, "un musée"),
    ("Expéditeur sans adresse lisible", True,
     "un doute n'est pas une preuve de presse — refuser ici couperait des légitimes"),
]
for sender, attendu, pourquoi in EXPEDITEURS:
    obtenu = expediteur_officiel(sender)
    _check(f"{'accepté' if obtenu else 'REFUSÉ '} — {sender[:44]:44} ({pourquoi})",
           obtenu == attendu, f"attendu {'accepté' if attendu else 'refusé'}")

print("\n──── base : ce qui est déjà passé ────")
conn = sqlite3.connect(tmp)
init_db(conn)
# (id, titre, source_name, url_source, wp_post_id_as, fin, non_officielle_attendue)
CAS = [
    (1, "Concert vu par la presse", "GuidaTorino <news@guidatorino.com>",
     "gmail:a#1", None, "2026-12-01", True),
    (2, "Expo presse DÉJÀ EN LIGNE", "GuidaTorino <news@guidatorino.com>",
     "gmail:a#2", 771, "2026-12-01", True),
    (3, "Presse mais PASSÉE", "Newsletter Mentelocale <no@mentelocale.it>",
     "gmail:b#1", None, "2026-05-01", True),
    (4, "Newsletter du lieu", "La Venaria Reale <newsletter@lavenaria.it>",
     "gmail:c#1", None, "2026-12-01", False),
    (5, "Flux officiel", "Malraux", "https://www.malrauxchambery.fr/x",
     None, "2026-12-01", False),
    (6, "Flux de presse", "Le Dauphiné", "https://www.ledauphine.com/y",
     None, "2026-12-01", True),
    (7, "Provenance illisible", "Inconnu", "gmail:d#1", None, "2026-12-01", False),
    # ── LE CAS QUI A FAILLI COÛTER CHER ────────────────────────────────────────
    # La première version ne regardait que le domaine d'origine et proposait donc de
    # sortir « La Saint-Ours 2026 », le « Festival Baroque de Tarentaise », « Monterosa
    # Classica », l'expo Vespa au MAUTO — de vrais événements du catalogue, détectés par
    # la presse puis RÉSOLUS vers la page de leur organisateur. C'est tout le principe du
    # tier radar : détecter, puis remonter. Une fois la remontée prouvée, la fiche ne doit
    # plus rien à la presse.
    (8, "Détectée par la presse mais RÉSOLUE", "GuidaTorino <news@guidatorino.com>",
     "gmail:e#1", None, "2026-12-01", False),
]
for eid, titre, src, url, wp, fin, _a in CAS:
    conn.execute(
        "INSERT INTO events_raw (id,title,source_name,url_source,statut,date_event_end,"
        "wp_post_id_as,url_officiel) VALUES (?,?,?,?, 'evaluated', ?,?,?)",
        (eid, titre, src, url, fin, wp,
         "https://www.museireali.it/mostra" if eid == 8 else ""))
conn.commit()
conn.close()

for eid, titre, src, url, wp, fin, attendu in CAS:
    ev = {"title": titre, "source_name": src, "url_source": url,
          "url_officiel": "https://www.museireali.it/mostra" if eid == 8 else ""}
    obtenu = pu._non_officielle(ev)
    _check(f"{'NON officielle' if obtenu else 'officielle   '} — {titre[:34]:34}",
           obtenu == attendu, f"attendu {attendu}")

print("\n──── --apply : qui est rejeté, qui ne l'est PAS ────")
pu.main(["--apply"])
conn = sqlite3.connect(tmp)
statuts = {r[0]: r[1] for r in conn.execute("SELECT id, statut FROM events_raw")}
conn.close()
_check("la fiche de presse pas en ligne est rejetée", statuts[1] == "rejected", str(statuts))
_check("la fiche de presse DÉJÀ EN LIGNE n'est PAS touchée (décision à part)",
       statuts[2] == "evaluated", str(statuts))
_check("la fiche de presse PASSÉE n'est pas touchée (règle 5)",
       statuts[3] == "evaluated", str(statuts))
_check("la newsletter de La Venaria n'est PAS touchée", statuts[4] == "evaluated", str(statuts))
_check("le flux officiel n'est PAS touché", statuts[5] == "evaluated", str(statuts))
_check("le flux de presse est rejeté", statuts[6] == "rejected", str(statuts))
_check("la fiche de provenance illisible n'est PAS touchée",
       statuts[7] == "evaluated", str(statuts))
_check("la fiche détectée par la presse mais RÉSOLUE n'est PAS touchée",
       statuts[8] == "evaluated", str(statuts))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
