#!/usr/bin/env python3
"""Fixture : la page /tableur et son export CSV (app.app).

D'OÙ ÇA VIENT — Franck, 2026-09-22 : « il faut un vrai tableur dans le backoffice ».
`tests/test_tableur.py` couvre le CALCUL (utils.tableur) ; celle-ci couvre le CHEMIN
COMPLET, parce que c'est là que se logent les fautes que la relecture ne voit pas :
une requête SQL qui ramène autre chose que ce qu'on croit, un export qui diverge de
l'écran, un BOM oublié qui fait lire « ChambÃ©ry » à Excel.

CE QU'ELLE EXIGE, et pourquoi :

  • le PÉRIMÈTRE par défaut écarte le passé (règle 5) — un tableur qui mélange passé et
    à-venir fabrique du travail au lieu d'en désigner ;
  • l'EXPORT montre exactement la même sélection que la PAGE. Deux chemins pour la même
    question finissent par diverger, et c'est le plus gros des deux qu'on croira ;
  • la SAISIE écrit vraiment en base — et une case laissée vide n'efface RIEN. C'est la
    promesse de /complete (« on n'efface rien par mégarde ») ; la vérifier ici évite de
    découvrir l'inverse sur une fiche en ligne.

BASE JETABLE, jamais data/events.db (CLAUDE.md). Cette fixture a d'ailleurs révélé que `init_db` ne créait
PAS `multi_lieux` — elle devait la poser elle-même pour tourner. Corrigé le 22/09 (voir
`tests/test_colonnes_declarees.py`), le contournement a donc disparu d'ici.

Lancer : .venv/bin/python -m tests.test_tableur_route
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp()) / "tableur_essai.db"
os.environ["DB_PATH"] = str(TMP)
os.environ.setdefault("FLASK_SECRET_KEY", "fixture")

from scripts.scraper_events import init_db  # noqa: E402

conn = sqlite3.connect(TMP)
init_db(conn)


def ins(**kw):
    kw.setdefault("statut", "evaluated")
    ks = ", ".join(kw)
    conn.execute(f"INSERT INTO events_raw ({ks}) VALUES ({', '.join('?' * len(kw))})",
                 tuple(kw.values()))


ins(title="Concert au château", url_source="https://a/1", date_event_start="2027-10-04",
    date_event_end="2027-10-04", lieu="Château", ville="Annecy", territoire="Savoie",
    llm_categorie="Concerts & Musique", url_image="https://i/1.jpg", llm_score=8)
# Score 0 volontaire : un zéro ne doit pas faire disparaître la fiche d'un comptage.
ins(title="Expo sans lieu — Chambéry", url_source="https://a/2",
    date_event_start="2027-11-02", date_event_end="2027-11-30", territoire="Savoie",
    llm_categorie="Expositions & Patrimoine", llm_score=0)
ins(title="Visites permanentes", url_source="https://a/3", recurring=1, lieu="Musée",
    ville="Aoste", territoire="Vallee-Aoste", llm_categorie="Expositions & Patrimoine")
ins(title="Festival itinérant", url_source="https://a/4", multi_lieux=1,
    date_event_start="2027-09-01", date_event_end="2027-09-09", territoire="Piemonte",
    llm_categorie="Festivals")
ins(title="Fête passée", url_source="https://a/5", date_event_start="2020-01-01",
    date_event_end="2020-01-02", lieu="X", ville="Y", territoire="Savoie",
    llm_categorie="Festivals", url_image="https://i/5.jpg")
conn.commit()
conn.close()

from app.app import app  # noqa: E402

app.config["TESTING"] = True
client = app.test_client()
with client.session_transaction() as sess:
    sess["logged_in"] = True

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


page = client.get("/tableur")
verifier("la page répond 200", page.status_code == 200, str(page.status_code))
h = page.get_data(as_text=True)
verifier("le périmètre est écrit à côté du nombre (règle 6)",
         "périmètre : à venir, en cours ou récurrents" in h)
verifier("la fiche PASSÉE est écartée par défaut (règle 5)", "Fête passée" not in h)
verifier("les quatre fiches encore devant nous sont là", h.count("/preview/") >= 4,
         str(h.count("/preview/")))
verifier("« sans objet » distingue le champ qui ne s'applique pas",
         h.count("sans objet") >= 3, str(h.count("sans objet")))
verifier("un taux affiche son dénominateur, jamais un pourcentage seul",
         "(3/4)" in h or "(2/3)" in h, "aucun couple (remplies/concernées)")

verifier("le passé revient quand on le demande explicitement",
         "Fête passée" in client.get("/tableur?vivant=0").get_data(as_text=True))
verifier("le tri « les plus vides d'abord » répond",
         client.get("/tableur?tri=trous").status_code == 200)
tout = client.get("/tableur?jeu=tout")
verifier("le jeu « tout » répond", tout.status_code == 200, str(tout.status_code))
verifier("et il montre plus de colonnes que le jeu par défaut",
         tout.get_data(as_text=True).count('<th scope="col">') > h.count('<th scope="col">'))
verifier("un jeu inconnu ne casse pas la page",
         client.get("/tableur?jeu=nimportequoi").status_code == 200)

saisie = client.get("/tableur?edit=1")
verifier("le mode saisie répond", saisie.status_code == 200, str(saisie.status_code))
verifier("et il poste sur /complete, la route de saisie qui existait déjà",
         'action="/complete/' in saisie.get_data(as_text=True))

# --- Le bandeau « où ça pêche » et le filtre qu'il pose -----------------------------
verifier("le bandeau annonce combien de fiches ont un trou", "Où ça pêche" in h)
verifier("et il propose au moins un chiffre cliquable", 'class="tb-chip' in h)
verifier("le chiffre mène au filtre « il manque ce champ »", "&vide=" in h)

import re as _re
taux_avant = _re.findall(r"\((\d+)/(\d+)\)", h)
filtre = client.get("/tableur?vide=url_image")
verifier("le filtre « il manque l'image » répond", filtre.status_code == 200,
         str(filtre.status_code))
hf = filtre.get_data(as_text=True)
verifier("il ne montre QUE les fiches sans image",
         "Concert au château" not in hf and "Expo sans lieu" in hf)
verifier("et il dit sur quoi il filtre", "enlever ce filtre" in hf)
# LE PIÈGE : calculé sur les lignes déjà filtrées, le taux de cette colonne tomberait à
# 0 % et le bandeau ne dirait plus rien. Il doit rester celui du périmètre entier.
verifier("les pourcentages NE BOUGENT PAS quand on clique un chiffre",
         _re.findall(r"\((\d+)/(\d+)\)", hf) == taux_avant,
         "le diagnostic se recalcule sur sa propre sélection")
verifier("un champ inconnu dans « vide » est ignoré, sans planter",
         client.get("/tableur?vide=nimportequoi").status_code == 200)

csv_ = client.get("/tableur.csv")
verifier("le CSV répond 200", csv_.status_code == 200, str(csv_.status_code))
txt = csv_.get_data(as_text=True)
verifier("il commence par le BOM UTF-8 (sinon Excel lit « ChambÃ©ry »)",
         txt.startswith("﻿"), repr(txt[:3]))
verifier("son en-tête porte les libellés, pas les noms de colonnes",
         "Titre (source)" in txt.split("\n")[0], txt.split("\n")[0][:80])
verifier("les accents sont intacts", "Chambéry" in txt)
verifier("il est proposé en téléchargement",
         "attachment" in csv_.headers.get("Content-Disposition", ""))
verifier("il montre EXACTEMENT la même sélection que la page",
         "Fête passée" not in txt, "l'export déborde du périmètre de la page")
csv_filtre = client.get("/tableur.csv?vide=url_image").get_data(as_text=True)
verifier("et l'export suit aussi le filtre « il manque ce champ »",
         "Concert au château" not in csv_filtre and "Expo sans lieu" in csv_filtre)

# La saisie écrit-elle, et n'efface-t-elle rien ?
r = client.post("/complete/2", data={"lieu": "Musée des Beaux-Arts", "next": "/tableur"})
verifier("la saisie redirige", r.status_code in (302, 303), str(r.status_code))
conn = sqlite3.connect(TMP)
lu = conn.execute("SELECT lieu, ville FROM events_raw WHERE id=2").fetchone()
conn.close()
verifier("le champ rempli est écrit en base", lu[0] == "Musée des Beaux-Arts", str(lu))
verifier("le champ laissé vide n'a RIEN effacé", not (lu[1] or ""), str(lu))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
