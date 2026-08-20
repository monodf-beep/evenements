#!/usr/bin/env python3
"""Fixture : le banc de rotation doit savoir dire « FIGÉE », et savoir dire l'inverse.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau, aucun LLM.

D'OÙ ÇA VIENT. Franck, 2026-08-18 : « on a des événements trop loin dans le temps, il
faudrait bien sûr les notes mais aussi se préoccuper des dates, sinon on a des homepages
identiques sur 6 mois ! »

`utils/deplacement.py` rend éligible tout ce qui commence dans les `HORIZON_JOURS` = 183,
mais ne donne de bonus d'imminence que dans les 45 derniers jours (`_FENETRES`). Entre 46
et 183 jours, tout le monde est à bonus zéro : le classement se réduit au score
intrinsèque, qui ne bouge pas. Une fiche lointaine et bien notée occupe donc la case de
son territoire pendant des mois.

Le banc de `audit_deplacement` mesure ça. Cette fixture vérifie qu'il MESURE, au lieu de
confirmer l'intuition de celui qui l'a écrit :

  1. un territoire dont la tête ne change jamais est déclaré **FIGÉ** ;
  2. ⚠️ ET LE CAS QUI DOIT PASSER : un territoire où la tête change ne l'est PAS. Sans lui,
     le banc pourrait écrire « FIGÉE » partout et se donner raison — c'est le défaut du
     portillon du 2026-08-06, passé au vert sur un design faux ;
  3. le verdict dit son dénominateur (« sur N relevés »), jamais un mot seul ;
  4. et il nomme le mécanisme, pour que le lecteur sache QUOI corriger.

Lancer : .venv/bin/python -m tests.test_rotation_deplacement
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

from scripts.scraper_events import init_db        # noqa: E402
import scripts.audit_deplacement as ad            # noqa: E402

ad.DB_PATH = tmp
AUJ = date.today()


def _det(rayon, spec, edition, notoriete, orga=0):
    return json.dumps({"rayonnement": {"points": rayon},
                       "specificite_territoriale": {"points": spec},
                       "edition_tradition": {"points": edition},
                       "notoriete_lieu": {"points": notoriete},
                       "organisateur_moyens": {"points": orga}})


def _dans(n):
    return (AUJ + timedelta(days=n)).isoformat()


# PIEMONTE — une seule fiche très forte et LOINTAINE (150 j). Rien ne peut la déloger
# avant qu'elle n'entre dans la fenêtre des 45 jours : c'est le cas de la Saint-Ours.
# NICE — deux fiches de force COMPARABLE à des dates différentes : la plus proche doit
# passer devant quand son bonus s'allume, puis céder la place. C'est le cas qui doit
# montrer une rotation.
FICHES = [
    (1, "Fiera lontana e enorme", "Piemonte", _dans(150), _dans(150), _det(2, 1, 2, 3)),
    (2, "Petite fête piémontaise", "Piemonte", _dans(10), _dans(10), _det(0, 0, 0, 0)),
    (3, "Festival de Nice, automne", "Nice", _dans(100), _dans(100), _det(2, 1, 2, 1)),
    (4, "Festival de Nice, bientôt", "Nice", _dans(20), _dans(20), _det(2, 1, 2, 0)),
]

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, titre, terr, deb, fin, detail in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, wp_post_id_as, statut, "
        "llm_categorie, llm_score_detail, date_event_start, date_event_end, territoire, "
        "duplicate_of, translation_of, enrich_status) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL,?)",
        (eid, titre, f"https://a.fr/{eid}", 900 + eid, "published_sub",
         "Fêtes & Traditions populaires", detail, deb, fin, terr, "enriched"))
conn.commit(); conn.close()

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
    ad.main([])
sortie = buf.getvalue()
bloc = sortie[sortie.find("Est-ce que la rangée CHANGE"):]

print("──── le banc existe et se lit ────")
_check("il rejoue à plusieurs dates", "J+0" in bloc and "J+180" in bloc, bloc[:300])
_check("   territoire par territoire, comme la section les affiche",
       "| Piemonte |" in bloc and "| Nice |" in bloc, bloc[:600])

print("\n──── il sait dire FIGÉE ────")
ligne_p = [l for l in bloc.splitlines() if l.startswith("- **Piemonte**")]
_check("le territoire à fiche unique et lointaine est déclaré figé",
       ligne_p and "FIGÉE" in ligne_p[0], ligne_p)
_check("   et le verdict dit son dénominateur, pas seulement le mot",
       ligne_p and "sur 7 relevés" in ligne_p[0], ligne_p)

print("\n──── ⚠️ et il sait dire l'inverse — le cas qui doit passer ────")
ligne_n = [l for l in bloc.splitlines() if l.startswith("- **Nice**")]
_check("le territoire dont la tête change n'est PAS déclaré figé",
       ligne_n and "FIGÉE" not in ligne_n[0], ligne_n)
_check("   il compte combien de fiches différentes s'y succèdent",
       ligne_n and "fiches différentes" in ligne_n[0], ligne_n)

print("\n──── le verdict nomme le mécanisme, pour qu'on sache quoi corriger ────")
_check("il cite la fenêtre au-delà de laquelle le bonus ne joue plus",
       "derniers jours" in bloc and "purement intrinsèque" in bloc, bloc[-500:])
_check("   et compte les territoires concernés sur le total",
       "territoire(s) sur" in bloc, bloc[-500:])

print("\n──── le verdict qui part sur Slack ────")
# Franck est en congés sans accès au VPS : ce verdict est le SEUL chemin par lequel la
# mesure lui parvient. S'il partait vide, ou s'il partait pour de vrai depuis les tests,
# on ne le saurait qu'en le lisant sur son téléphone.
import utils.slack as slack_mod  # noqa: E402
envoyes: list[str] = []
slack_mod.notify = lambda text, blocks=None, urgent=False: envoyes.append(text) or True

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ad.main(["--slack"])

_check("un seul message est déposé, pas un par territoire", len(envoyes) == 1, envoyes)
msg = envoyes[0] if envoyes else ""
_check("il annonce combien de cases sont figées sur le total",
       "case(s) figée(s) sur" in msg, msg)
_check("le territoire figé est marqué en rouge, avec la fiche concernée",
       "🔴 Piemonte" in msg and "Fiera lontana" in msg, msg)
_check("⚠️ celui qui tourne n'est PAS marqué en rouge (le cas qui doit passer)",
       "🔴 Nice" not in msg and "Nice :" in msg, msg)
_check("   et il montre son mouvement, de J+0 à J+180",
       "→" in [l for l in msg.splitlines() if l.startswith("· Nice")][0], msg)
_check("le message tient sur un écran de téléphone (moins de 10 lignes)",
       len(msg.splitlines()) < 10, f"{len(msg.splitlines())} lignes")

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
