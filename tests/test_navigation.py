#!/usr/bin/env python3
"""Fixture : le menu rendu et la palette « Aller à… » (base.html + utils.menu).

D'OÙ ÇA VIENT — Franck, 2026-09-22 : « rends le back-office le plus simple possible […]
utilise tes skills UI et UX pour que ce soit facile de navigation ».

`tests/test_menu.py` vérifie la CARTE (les pages existent, les routes aussi).
Celle-ci vérifie le RENDU : ce que le menu montre vraiment, et ce que la palette permet.
Les deux sont nécessaires — une carte juste rendue par un gabarit fautif donne un menu
faux, et c'est invisible à la relecture.

CE QU'ELLE EXIGE, et pourquoi chaque point a coûté quelque chose ailleurs :

  • AUCUNE page de la carte ne disparaît du rendu. Le regroupement + le repli sont
    précisément la mécanique qui fait perdre une page de vue ;
  • un groupe REPLIÉ affiche quand même son total : sinon le repli cache du travail en
    attente, et la simplification se paye en oublis ;
  • la page courante porte `aria-current="page"` ET son groupe est ouvert — sans quoi on
    ne sait plus où on est, ce qui est le contraire d'une navigation facile ;
  • le lien d'évitement existe : c'est la première chose qu'attend un clavier, et il
    manquait ;
  • la palette liste TOUTES les pages, avec une cible de recherche sans accents.

Lancer : .venv/bin/python -m tests.test_navigation
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp()) / "nav_essai.db"
os.environ["DB_PATH"] = str(TMP)
os.environ.setdefault("FLASK_SECRET_KEY", "fixture")

from scripts.scraper_events import init_db  # noqa: E402

conn = sqlite3.connect(TMP)
init_db(conn)
conn.commit()
conn.close()

from app.app import app  # noqa: E402
from utils import menu  # noqa: E402

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
verifier("une page rend bien", page.status_code == 200, str(page.status_code))
h = page.get_data(as_text=True)

# --- Rien ne se perd dans le regroupement -----------------------------------------
absentes = [p["libelle"] for p in menu.PAGES if f'href="{p["url"]}"' not in h]
verifier("toutes les pages de la carte sont dans le menu rendu",
         not absentes, "absentes : " + ", ".join(absentes))
verifier("les trois écrans épinglés sont au premier niveau",
         h.count('class="nav-main') == len(menu.EPINGLEES),
         str(h.count('class="nav-main')))
verifier("les groupes sont rendus en repliables",
         h.count("<details ") >= len(menu.GROUPES), str(h.count("<details ")))

# --- On sait toujours où on est ----------------------------------------------------
verifier("la page courante est marquée pour les lecteurs d'écran",
         'aria-current="page"' in h)
verifier("et elle est marquée visuellement", 'class="nav-main on"' in h)

sys_page = client.get("/systeme").get_data(as_text=True)
verifier("une page d'un groupe replié ouvre SON groupe", "<details open>" in sys_page)
verifier("et le groupe ouvert est le bon",
         sys_page.index("<details open>") > 0 and
         'href="/systeme" class="on"' in sys_page.replace('\n', ' '),
         "la page active du groupe n'est pas allumée")

# --- Le repli ne cache pas le travail ----------------------------------------------
verifier("chaque page à pastille porte son compteur dans le gabarit",
         'nav[p.badge]' not in h, "expression Jinja non évaluée : le menu rend du code")
verifier("le total d'un groupe est calculé, pas laissé en expression",
         "_tot.v" not in h)

# --- Accessibilité -----------------------------------------------------------------
verifier("le lien d'évitement existe", 'class="skip" href="#contenu"' in h)
verifier("et sa cible aussi", 'id="contenu"' in h)
verifier("le bouton de palette s'annonce au clavier",
         'aria-label="Aller à une page' in h)
verifier("la palette est un dialogue déclaré",
         'role="dialog"' in h and 'aria-modal="true"' in h)
verifier("sa liste est une liste d'options",
         'role="listbox"' in h and h.count('role="option"') == len(menu.PAGES),
         str(h.count('role="option"')))
verifier("les raccourcis sont dits, pas seulement dessinés",
         "Flèches haut et bas" in h)
verifier("la palette est masquée tant que rien ne l'ouvre",
         '<div class="palette" id="palette" hidden>' in h)

# --- La recherche ------------------------------------------------------------------
verifier("chaque option porte sa cible de recherche",
         h.count("data-cible=") == len(menu.PAGES), str(h.count("data-cible=")))
verifier("les cibles sont aplaties (sans accents)",
         'data-cible="etat du systeme' in h.lower(),
         "« État du système » n'est pas aplati")

# --- Le ménage du 22/09 -------------------------------------------------------------
verifier("« Coûts par date » n'est plus une entrée de menu",
         'href="/couts"' not in h)
verifier("mais l'adresse vit encore et redirige",
         client.get("/couts").status_code in (301, 302),
         str(client.get("/couts").status_code))
verifier("et elle mène bien à l'onglet des coûts",
         "vue=couts" in (client.get("/couts").headers.get("Location") or ""))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
