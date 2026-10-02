#!/usr/bin/env python3
"""Fixture : le garage des traductions refusées en boucle. Base JETABLE, jamais data/.

MESURÉ EN PRODUCTION, nuit du 2026-08-17 : le portillon de langue a refusé CINQ FOIS la
même fiche [473] « La Saint-Ours 2026 — Rendez Vous en Vallée d'Aoste », puis [4702]
« Glaciers, enquête sur une disparition ». Deux appels API par passage, chaque nuit, pour
le même résultat.

CE QUE ÇA DÉMENT, et c'était écrit dans translate_events : « le LLM étant stochastique un
titre correctement ancré passera ». CLAUDE.md (règle 3) interdit précisément de poser
cette hypothèse sans la tester. La production l'a testée : cinq fois le même refus.

ET LE VERDICT N'EST PAS FORCÉMENT FAUX — c'est ce qui rend le cas intéressant. « Rendez
Vous en Vallée d'Aoste » est le NOM PROPRE de l'événement : sa version italienne lui
ressemblera toujours, donc le portillon refusera toujours. Aucune heuristique plus fine ne
règle ça. C'est la RÉPÉTITION qu'on arrête, pas le verdict.

LES QUATRE PROPRIÉTÉS ÉPROUVÉES ICI :
  1. sous le seuil, la fiche reste candidate (on n'a rien cassé) ;
  2. au seuil, elle est garée — elle cesse de brûler des appels ;
  3. LE CAS QUI DOIT PASSER : sa matière change → elle repart D'ELLE-MÊME, sans commande
     ni humain. C'est l'exigence de la règle 3 ;
  4. matière inchangée → elle NE repart PAS. Sans ce volet, un rouvreur qui rouvrirait
     tout le temps ramènerait le martèlement en croyant bien faire.

Lancer : .venv/bin/python -m tests.test_traduction_garage
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.translate_events import (  # noqa: E402
    MAX_REFUS, _empreinte_traduction, _rearme_traductions, garees, marquer_refus,
)

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


FICHE = {"id": 473, "title": "La Saint-Ours 2026 - Rendez Vous en Vallée d'Aoste",
         "description": "La foire millénaire d'Aoste.", "lieu": "Bourg", "ville": "Aoste",
         "organisateur": "Région", "enrich_data": ""}

# ── L'empreinte : stable, et sensible à ce qui compte ───────────────────────────
verifier("la même matière donne la même empreinte",
         _empreinte_traduction(FICHE) == _empreinte_traduction(dict(FICHE)))
verifier("un titre corrigé change l'empreinte",
         _empreinte_traduction({**FICHE, "title": "Autre titre"}) != _empreinte_traduction(FICHE))
verifier("une description réparée change l'empreinte",
         _empreinte_traduction({**FICHE, "description": "Texte réparé"}) != _empreinte_traduction(FICHE))
verifier("un champ hors du jugement ne change RIEN (pas de faux ré-armement)",
         _empreinte_traduction({**FICHE, "llm_score": 9}) == _empreinte_traduction(FICHE))

# ── Le garage : qui reste candidat, qui sort de la file ─────────────────────────
lot = [{"id": 1, "title": "a", "traduction_tentatives": 0},
       {"id": 2, "title": "b", "traduction_tentatives": MAX_REFUS - 1},
       {"id": 3, "title": "c", "traduction_tentatives": MAX_REFUS},
       {"id": 4, "title": "d"}]
actives, garage = garees(lot)
verifier("une fiche jamais refusée reste candidate", 1 in [r["id"] for r in actives])
verifier("une fiche sous le seuil reste candidate (rien n'est cassé)",
         2 in [r["id"] for r in actives])
verifier("une fiche au seuil est garée", [r["id"] for r in garage] == [3])
verifier("une colonne absente vaut zéro, pas une erreur", 4 in [r["id"] for r in actives])

# ── Le cycle complet, sur une vraie base jetable ────────────────────────────────
with tempfile.TemporaryDirectory() as tmp:
    conn = sqlite3.connect(str(Path(tmp) / "essai.db"))
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE events_raw (id INTEGER PRIMARY KEY, title TEXT, "
                 "description TEXT, lieu TEXT, ville TEXT, organisateur TEXT, "
                 "enrich_data TEXT, traduction_tentatives INTEGER DEFAULT 0, "
                 "traduction_matiere TEXT)")
    conn.execute("INSERT INTO events_raw (id, title, description, lieu, ville, organisateur, "
                 "enrich_data) VALUES (?,?,?,?,?,?,?)",
                 (473, FICHE["title"], FICHE["description"], FICHE["lieu"], FICHE["ville"],
                  FICHE["organisateur"], FICHE["enrich_data"]))
    conn.commit()

    for _ in range(MAX_REFUS):
        marquer_refus(conn, FICHE)
    n = conn.execute("SELECT traduction_tentatives FROM events_raw WHERE id=473").fetchone()[0]
    verifier(f"après {MAX_REFUS} refus, le compteur les a comptés", n == MAX_REFUS, str(n))

    rows = [dict(r) for r in conn.execute("SELECT * FROM events_raw")]
    verifier("la fiche est sortie de la file", garees(rows)[0] == [])

    # 4. matière INCHANGÉE → elle ne repart pas (sinon on ramène le martèlement)
    verifier("matière inchangée : aucune réouverture", _rearme_traductions(conn) == 0)

    # 3. LE CAS QUI DOIT PASSER : la matière change → réouverture SANS personne
    conn.execute("UPDATE events_raw SET description=? WHERE id=473",
                 ("Description réparée par autocomplete.",))
    conn.commit()
    verifier("matière changée : la fiche repart d'elle-même", _rearme_traductions(conn) == 1)
    rows = [dict(r) for r in conn.execute("SELECT * FROM events_raw")]
    verifier("et elle est de nouveau candidate", [r["id"] for r in garees(rows)[0]] == [473])
    conn.close()

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
