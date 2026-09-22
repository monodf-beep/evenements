#!/usr/bin/env python3
"""Fixture : le compteur de pages ouvertes (utils.frequentation + l'onglet « Les pages »).

D'OÙ ÇA VIENT — Franck, 2026-09-22 : « s'il y a des choses qui ne servent plus, on les
enlève ». La première tentative de mesure a lu le journal nginx : il ne contenait AUCUNE
page du back-office et presque rien d'autre que des sondes `/.env` et `/wp-login.php`.
Un compteur posé dans l'application, lui, ne voit que des sessions connectées.

CE QU'ELLE EXIGE, et chaque point écarte un chiffre qui mentirait :

  • une page vue en étant CONNECTÉ compte ; la même en étant déconnecté, non — sinon
    un robot sur /login gonflerait la mesure, et c'est tout le défaut du journal nginx ;
  • un EXPORT (CSV) ne compte pas : ce n'est pas une page qu'on ouvre ;
  • une page HORS MENU ne compte pas : la question posée est « quelle ENTRÉE de menu
    supprimer », pas « quelles adresses existent » ;
  • une page JAMAIS ouverte doit APPARAÎTRE au tableau, à zéro. C'est le sens de la
    mesure : ce sont les zéros qu'on cherche, et une absence ne se remarque pas ;
  • la DATE DE DÉPART est rendue avec les chiffres — un zéro ne dit pas s'il vient d'un
    désintérêt ou d'une mesure branchée la veille.

Lancer : .venv/bin/python -m tests.test_frequentation
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp()) / "freq_essai.db"
os.environ["DB_PATH"] = str(TMP)
os.environ.setdefault("FLASK_SECRET_KEY", "fixture")

from scripts.scraper_events import init_db  # noqa: E402

conn = sqlite3.connect(TMP)
init_db(conn)
conn.execute("ALTER TABLE events_raw ADD COLUMN multi_lieux INTEGER DEFAULT 0")
conn.commit()
conn.close()

from app.app import app  # noqa: E402
from utils import frequentation as freq, menu  # noqa: E402

app.config["TESTING"] = True
echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


def lu(chemin):
    c = sqlite3.connect(TMP)
    try:
        freq.assure(c)
        r = c.execute("SELECT n FROM page_hits WHERE chemin=?", (chemin,)).fetchone()
        return r[0] if r else 0
    finally:
        c.close()


# --- Déconnecté : rien ne doit être compté ------------------------------------------
anonyme = app.test_client()
anonyme.get("/tableur")
anonyme.get("/systeme")
verifier("une visite NON connectée ne compte pas — c'est tout le défaut du journal nginx",
         lu("/tableur") == 0, str(lu("/tableur")))

# --- Connecté : on compte -----------------------------------------------------------
client = app.test_client()
with client.session_transaction() as sess:
    sess["logged_in"] = True

client.get("/tableur")
client.get("/tableur")
client.get("/systeme")
verifier("une page du menu ouverte deux fois compte deux fois", lu("/tableur") == 2,
         str(lu("/tableur")))
verifier("une autre page compte séparément", lu("/systeme") == 1, str(lu("/systeme")))

client.get("/tableur.csv")
verifier("un export CSV ne compte pas : ce n'est pas une page qu'on ouvre",
         lu("/tableur.csv") == 0, str(lu("/tableur.csv")))

client.get("/couts")           # redirection 302 vers /systeme?vue=couts
verifier("une redirection ne compte pas", lu("/couts") == 0, str(lu("/couts")))
verifier("et elle n'a pas non plus gonflé sa cible", lu("/systeme") == 1, str(lu("/systeme")))

client.get("/nexistepas")
verifier("une page inexistante ne crée pas de ligne", lu("/nexistepas") == 0)

# --- Le tableau : ce sont les ZÉROS qu'on cherche ------------------------------------
c = sqlite3.connect(TMP)
lignes = freq.par_page(c, list(menu.PAGES))
depuis = freq.depuis(c)
c.close()

verifier("le tableau porte TOUTES les pages du menu, ouvertes ou non",
         len(lignes) == len(menu.PAGES), f"{len(lignes)} / {len(menu.PAGES)}")
verifier("les jamais-ouvertes y figurent, à zéro",
         any(r["n"] == 0 for r in lignes))
verifier("et elles viennent EN TÊTE : c'est ce qu'on cherche",
         lignes[0]["n"] == 0, str(lignes[0]))
verifier("la plus ouverte est en queue",
         lignes[-1]["url"] == "/tableur" and lignes[-1]["n"] == 2, str(lignes[-1]))
verifier("chaque ligne dit ce qu'on fait sur la page",
         all(r["resume"].strip() for r in lignes))
verifier("la date de départ est disponible", len(depuis) == 10, depuis)

# --- Le rendu de l'onglet -------------------------------------------------------------
page = client.get("/systeme?vue=pages")
verifier("l'onglet « Les pages » répond", page.status_code == 200, str(page.status_code))
h = page.get_data(as_text=True)
verifier("il écrit DEPUIS QUAND il mesure, à côté des chiffres",
         "Mesuré depuis le" in h and depuis in h)
verifier("il prévient qu'un zéro jeune ne prouve rien",
         "ne veut rien dire tant que la mesure est jeune" in h)
verifier("et que les candidates ne sont pas une preuve",
         "pas la preuve qu'elles sont inutiles" in h)
verifier("les deux autres onglets répondent toujours",
         client.get("/systeme").status_code == 200
         and client.get("/systeme?vue=couts").status_code == 200)

# Un compteur ne doit jamais casser la page qu'il mesure.
c = sqlite3.connect(TMP)
c.execute("DROP TABLE page_hits")
c.commit()
c.close()
verifier("table effacée sous ses pieds : la page répond quand même",
         client.get("/systeme?vue=pages").status_code == 200)

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
