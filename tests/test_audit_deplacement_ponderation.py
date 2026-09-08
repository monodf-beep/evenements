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
     diverger à nouveau du calcul qu'il décrit ;
  5. le relevé « ce que la barrière de la langue écarterait de la traduction » LISTE les
     fiches notées 0 au lieu de les compter. Ajouté le 2026-08-16, quand Franck a
     objecté « si je suis un touriste, j'aimerais avoir la traduction » : le seul motif
     défendable de ne pas traduire est la langue, et avant d'en faire une règle il faut
     LIRE ce qu'elle refuse. C'est la consigne de CLAUDE.md que trois portillons du
     2026-08-13 avaient sautée.

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


# Trois fiches de plus, une par valeur d'accessibilité linguistique — dont le cas
# frontière : « Visite guidée » est classé 0 par le titre (un format de PAROLE), même
# rangé en Expositions. C'est peut-être un faux positif (une visite guidée peut être
# bilingue) : la fixture ne tranche pas, elle vérifie qu'il est AFFICHÉ pour qu'un œil
# tranche.
_c = sqlite3.connect(tmp)
for eid, titre, cat in ((3, "Fiera del Peperone", "Gastronomie & Sagre"),
                        (4, "Brahms / Chostakovitch", "Concerts & Musique"),
                        (5, "Café philo : habiter la montagne", "Conférences & Rencontres"),
                        (6, "Visite guidée du théâtre", "Expositions & Patrimoine")):
    _c.execute("INSERT INTO events_raw (id, title, url_source, wp_post_id_as, statut, "
               "llm_categorie, llm_score_detail, date_event_start, date_event_end, "
               "territoire, duplicate_of) VALUES (?,?,?,?,?,?,?,?,?,?, NULL)",
               (eid, titre, f"https://a.fr/{eid}", 900 + eid, "published_sub", cat,
                json.dumps(FICHES[1][3]), FUTUR, FUTUR, "Savoie"))
_c.commit(); _c.close()

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
# On vérifie le RAPPORT (réel = brut × poids), jamais des totaux absolus : ceux-ci
# dépendent du nombre de fiches de la fixture, et deux assertions sont tombées le
# 2026-08-16 pour cette seule raison quand on en a ajouté quatre. Un test qui casse
# parce qu'on enrichit son jeu de données n'apprend rien à personne.
for crit in ("specificite_territoriale", "rayonnement"):
    if crit in lignes:
        g = lignes[crit]
        poids, brut, reel = int(g.group(2)), int(g.group(4)), int(g.group(5))
        _check(f"`{crit}` : {brut} bruts ×{poids} = {reel}", reel == brut * poids,
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

print("\n──── 6. ce que la barrière de la langue écarterait ────")
_check("le relevé existe", "barrière de la langue écarterait" in sortie, sortie[-400:])
_check("   il écrit son PÉRIMÈTRE, et dit qu'il n'est PAS celui de la traduction",
       "PAS la file de traduction" in sortie, sortie[sortie.find("barrière de la"):][:400])
_check("les fiches à 0 sont LISTÉES, pas seulement comptées",
       "Café philo : habiter la montagne" in sortie
       and "notées 0 — À LIRE UNE PAR UNE" in sortie,
       sortie[sortie.find("notées 0"):][:500])
_check("   avec leur catégorie, qui est le motif du verdict",
       "_Conférences & Rencontres_" in sortie, sortie[sortie.find("notées 0"):][:500])
# LE CAS FRONTIÈRE, et c'est lui qui justifie de LIRE plutôt que de compter : le titre
# « Visite guidée » vaut 0 même sur une fiche rangée en Expositions. Une visite guidée
# bilingue serait donc écartée à tort — invisible dans un total, évidente dans la liste.
_check("le cas frontière (visite guidée rangée en Expositions) est visible",
       "Visite guidée du théâtre" in sortie.split("notées 0")[-1],
       sortie.split("notées 0")[-1][:500])
_check("celles qu'on traduirait ne sont PAS listées — la file ne contient que "
       "ce qu'un œil doit trancher",
       "Fiera del Peperone" not in sortie.split("notées 0")[-1],
       sortie.split("notées 0")[-1][:500])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
