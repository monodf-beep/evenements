#!/usr/bin/env python3
"""Fixture : le banc de rotation doit savoir dire « FIGÉE », et savoir dire l'inverse.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau, aucun LLM.

D'OÙ ÇA VIENT. Franck, 2026-08-18 : « on a des événements trop loin dans le temps, il
faudrait bien sûr les notes mais aussi se préoccuper des dates, sinon on a des homepages
identiques sur 6 mois ! »

`utils/deplacement.py` rend éligible tout ce qui commence dans les `HORIZON_JOURS` = 183.
CE QUI SUIT DÉCRIT L'ÉTAT D'AVANT LE 05/09 : le bonus d'imminence ne jouait alors que
dans les 45 derniers jours (`_FENETRES`) ; entre 46 et 183 jours, tout le monde était à
bonus zéro, le classement se réduisait au score intrinsèque, figé, et une fiche
lointaine bien notée occupait la case de son territoire pendant des mois — exactement ce
que cette fixture a servi à mesurer et confirmer le 05/09 (Piémont : 12 semaines
d'affilée ; Vallée d'Aoste : 21). `utils.deplacement._bonus_lointain` referme ce trou
depuis, testé par `tests/test_gradient_deplacement.py` — cette fixture-ci continue de
vérifier que le BANC DE MESURE dit vrai, gradient ou pas.

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
# CORRIGÉ le 05/09, en même temps que le gradient (`utils.deplacement._bonus_lointain`) :
# le verdict n'affirme plus « au-delà, le classement est purement intrinsèque » — c'est
# devenu FAUX depuis que le bonus s'étend jusqu'à l'horizon. Il nomme désormais le
# gradient et rappelle qu'une case peut rester figée À RAISON (une seule fiche dans la
# colonne, comme Piemonte ici — 150 jours, sans concurrente).
_check("il cite le gradient d'imminence, pas l'ancienne fenêtre à 45 jours",
       "gradient d'imminence" in bloc, bloc[-500:])
_check("   et distingue une case figée À RAISON d'un défaut du mécanisme",
       "à raison" in bloc, bloc[-500:])
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

print("\n──── la question HEBDOMADAIRE de Franck, pas les jalons épars ────")
# Franck, 2026-08-24 : « chaque semaine, je vais aller voir [...] qu'est-ce que je vais
# faire ce week-end ». Les jalons ci-dessus (0,15,30,60,90,120,180) peuvent sauter
# par-dessus une longue série immobile sans jamais le montrer — d'où ce second relevé,
# UN point par semaine sur tout l'horizon.
bloc_hebdo = sortie[sortie.find("Si je reviens chaque semaine"):]
_check("le bloc hebdomadaire existe", bloc_hebdo != "", sortie[-200:])
_check("Piemonte, réellement figée, affiche une longue série immobile",
       "**Piemonte** : jusqu'à **" in bloc_hebdo, bloc_hebdo[:500])

import re as _re  # noqa: E402
m_piem = _re.search(r"\*\*Piemonte\*\* : jusqu'à \*\*(\d+) semaines", bloc_hebdo)
m_nice = _re.search(r"\*\*Nice\*\* : jusqu'à \*\*(\d+) semaines", bloc_hebdo)
_check("   avec un nombre de semaines assez grand pour être un problème réel (≥15)",
       m_piem is not None and int(m_piem.group(1)) >= 15, bloc_hebdo)
_check("   et ZÉRO changement sur tout l'horizon — elle est FIGÉE au sens fort",
       "Piemonte** : jusqu'à **" in bloc_hebdo
       and "et 0 changement(s)" in bloc_hebdo.split("Piemonte")[1][:120],
       bloc_hebdo)

# ⚠️ LE CAS QUI DOIT PASSER, ET IL EST INSTRUCTIF : le relevé SPARSE plus haut dit déjà
# que Nice « tourne » (2 fiches différentes sur 7 jalons). La question hebdomadaire montre
# une réalité plus dure — Nice reste PARFOIS immobile plusieurs semaines d'affilée elle
# aussi, juste moins longtemps que Piemonte. Sans cette comparaison, on pourrait croire
# qu'un territoire qui « tourne » au sens sparse n'a plus de problème hebdomadaire.
_ligne_nice = bloc_hebdo.split("**Nice**")[1].splitlines()[0] if "**Nice**" in bloc_hebdo else ""
_m_chg_nice = _re.search(r"et (\d+) changement", _ligne_nice)
_check("Nice a AU MOINS un changement (contrairement à Piemonte)",
       _m_chg_nice is not None and int(_m_chg_nice.group(1)) >= 1, _ligne_nice)
_check("   et sa PIRE série immobile est plus courte que celle de Piemonte — "
       "c'est la comparaison qui compte, pas un seuil absolu",
       m_piem and m_nice and int(m_nice.group(1)) < int(m_piem.group(1)),
       f"Nice={m_nice.group(1) if m_nice else '?'} Piemonte={m_piem.group(1) if m_piem else '?'}")

_check("le relevé explique QUEL chiffre compte pour un rendez-vous hebdomadaire",
       "PIRE série immobile" in bloc_hebdo, bloc_hebdo[-400:])

print("\n──── le pire cas hebdomadaire part aussi sur Slack ────")
envoyes2: list[str] = []
slack_mod.notify = lambda text, blocks=None, urgent=False: envoyes2.append(text) or True
buf3 = io.StringIO()
with contextlib.redirect_stdout(buf3):
    ad.main(["--slack"])
msg3 = envoyes2[0] if envoyes2 else ""
_check("le message Slack cite le pire cas hebdomadaire, pas seulement le relevé sparse",
       "Pire cas hebdomadaire" in msg3 and "Piemonte" in msg3, msg3)
_check("   avec le nombre de semaines et la fiche en cause",
       "semaines**" in msg3 and "Fiera lontana" in msg3, msg3)
_check("   et le message tient toujours sur un écran de téléphone",
       len(msg3.splitlines()) <= 8, f"{len(msg3.splitlines())} lignes : {msg3}")

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
