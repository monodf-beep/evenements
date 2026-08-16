#!/usr/bin/env python3
"""Fixture : le tableau « d'où viennent les points » doit mesurer LA formule en vigueur.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau.

D'OÙ ÇA VIENT. Le 2026-08-16, `audit_deplacement` a rendu ceci :

    | notoriete_lieu | 144 | 46 % | 3 |
    > `notoriete_lieu` note LA SALLE, pas l'événement. S'il pèse le plus lourd, la note
    > récompense la réputation du lieu […]. C'est la PONDÉRATION qu'il faudrait revoir.

Faux, et dans le sens le plus coûteux : `_PONDERATION` PLAFONNE déjà `notoriete_lieu` à
1 point, précisément pour que la réputation de la salle n'écrase pas la raison de s'y
rendre. Le rapport réclamait un correctif DÉJÀ APPLIQUÉ — l'appliquer une seconde fois
aurait cassé un barème calibré sur des mesures.

La cause : le tableau additionnait les points BRUTS, sans poids ni plafond. Son
commentaire décrivait la formule d'avant la repondération du 2026-08-04 et n'a pas été
relu quand elle a changé. Douze jours pendant lesquels un rapport destiné à décider
mesurait autre chose que ce qu'il annonçait.

CE QUE LA FIXTURE SURVEILLE :
  1. le plafond de `notoriete_lieu` est APPLIQUÉ — une salle notée 3 ne pèse pas plus
     qu'une salle notée 1 ;
  2. les poids le sont aussi — `specificite_territoriale` compte ×3 ;
  3. `accessibilite_langue`, 2 points sur 12, apparaît dans le tableau ;
  4. et le total des contributions égale EXACTEMENT la somme des notes rendues par
     `deplacement_score` : c'est la seule vérification qui interdit au tableau de
     diverger à nouveau du calcul qu'il décrit.

Lancer : .venv/bin/python -m tests.test_audit_deplacement_ponderation
"""
import contextlib
import io
import json
import os
import re
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
import scripts.audit_deplacement as ad  # noqa: E402
from utils.deplacement import deplacement_score  # noqa: E402

ad.DB_PATH = tmp
FUTUR = (date.today() + timedelta(days=30)).isoformat()

# Deux fiches choisies pour que le plafond et les poids se VOIENT :
#   · A : salle très cotée (3) mais aucun rayonnement — le plafond doit l'écrêter à 1 ;
#   · B : rien côté salle, mais identitaire (×3) et transfrontalier (×2).
# Si le tableau additionnait le brut, A pèserait plus que B. Avec la vraie formule,
# c'est l'inverse — et c'est tout l'objet du barème.
FICHES = [
    (1, "Concert dans une grande salle", "Concerts & Musique",
     {"notoriete_lieu": {"points": 3}, "organisateur_moyens": {"points": 2},
      "edition_tradition": {"points": 0}, "rayonnement": {"points": 0},
      "specificite_territoriale": {"points": 0}}),
    (2, "Fête identitaire transfrontalière", "Fêtes & Traditions populaires",
     {"notoriete_lieu": {"points": 0}, "organisateur_moyens": {"points": 0},
      "edition_tradition": {"points": 0}, "rayonnement": {"points": 2},
      "specificite_territoriale": {"points": 1}}),
]

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, titre, cat, detail in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, wp_post_id_as, statut, "
        "llm_categorie, llm_score_detail, date_event_start, date_event_end, "
        "territoire, duplicate_of) VALUES (?,?,?,?,?,?,?,?,?,?, NULL)",
        (eid, titre, f"https://a.fr/{eid}", 900 + eid, "published_sub", cat,
         json.dumps(detail), FUTUR, FUTUR, "Savoie"))
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


buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ad.main([])
sortie = buf.getvalue()

lignes = {m.group(1): m for m in
          re.finditer(r"\| `([a-z_]+)` \| ×(\d+) \| ([0-9—]+) \| ([0-9—]+) \| \*\*(\d+)\*\*",
                      sortie)}

print("──── 1. le plafond de notoriete_lieu est appliqué ────")
_check("le tableau montre le plafond déclaré", "notoriete_lieu" in lignes
       and lignes["notoriete_lieu"].group(3) == "1",
       sortie[sortie.find("D'où viennent"):][:700])
if "notoriete_lieu" in lignes:
    brut, reel = lignes["notoriete_lieu"].group(4), lignes["notoriete_lieu"].group(5)
    _check(f"3 points bruts ne contribuent qu'à 1 (brut={brut}, réel={reel})",
           brut == "3" and reel == "1", f"{brut} / {reel}")

print("\n──── 2. les poids sont appliqués ────")
if "specificite_territoriale" in lignes:
    g = lignes["specificite_territoriale"]
    _check(f"1 point brut ×3 contribue 3 (brut={g.group(4)}, réel={g.group(5)})",
           g.group(4) == "1" and g.group(5) == "3", g.group(0))
if "rayonnement" in lignes:
    g = lignes["rayonnement"]
    _check(f"2 points bruts ×2 contribuent 4 (réel={g.group(5)})", g.group(5) == "4",
           g.group(0))

print("\n──── 3. l'accessibilité linguistique n'est plus invisible ────")
_check("elle a sa ligne dans le tableau", "accessibilite_langue" in sortie,
       sortie[sortie.find("D'où viennent"):][:800])

print("\n──── 4. le tableau ne peut plus diverger du calcul qu'il décrit ────")
# LA VÉRIFICATION QUI COMPTE. Sans elle, une prochaine repondération pourrait à nouveau
# laisser le rapport mesurer l'ancienne formule pendant douze jours.
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
rows = [dict(r) for r in conn.execute("SELECT * FROM events_raw")]
conn.close()
attendu = sum(deplacement_score(r) or 0 for r in rows)
# `lignes` capture AUSSI la ligne « accessibilite_langue » (ses colonnes vides matchent
# le motif) : l'additionner une seconde fois la compterait deux fois. Vu en écrivant
# cette fixture — 14 au lieu de 11 — et c'est bien elle qui avait tort, pas le script.
total_tableau = sum(int(m.group(5)) for m in lignes.values())
_check(f"somme des contributions = somme des notes ({total_tableau} = {attendu})",
       total_tableau == attendu, f"tableau={total_tableau} scores={attendu}")

print("\n──── 5. l'encadré ne réclame plus un correctif déjà appliqué ────")
_check("il ne dit plus « c'est la PONDÉRATION qu'il faudrait revoir »",
       "qu'il faudrait revoir" not in sortie, sortie[-900:])
_check("   et il explique que le plafond est VOULU",
       "plafonné à 1" in sortie, sortie[sortie.find("La colonne qui compte"):][:400])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
