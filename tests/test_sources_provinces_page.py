#!/usr/bin/env python3
"""Fixture : la page back-office « Sources par province » se rend réellement.

Aucun réseau, aucune vraie base — `_sources_provinces_data()` ne lit QUE les fichiers de
config (sources.txt, newsletters.txt), la page ne dépend donc d'aucune connexion.

D'OÙ ÇA VIENT — Franck, 2026-08-31 : « dans le back-office, ce serait bien de les trier
par province, ça nous permet de voir les manques. » Rendre le template une fois ici,
pour de vrai (pas juste vérifier que le fichier existe), attrape ce qu'une lecture ne
verrait pas : une variable Jinja qui ne correspond à rien, un accès à un champ absent.

Lancer : .venv/bin/python -m tests.test_sources_provinces_page
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


from app.app import app, _sources_provinces_data  # noqa: E402

with app.test_request_context():
    from flask import render_template

    data = _sources_provinces_data()
    verifier("les quatre territoires sont là", len(data["territoires"]) == 4,
             [t["nom"] for t in data["territoires"]])
    verifier("Piemonte a bien ses 8 provinces",
             any(t["nom"] == "Piemonte" and len(t["rows"]) == 8
                 for t in data["territoires"]))
    verifier("Savoie a bien ses 2 provinces (73/74)",
             any(t["nom"] == "Savoie" and len(t["rows"]) == 2
                 for t in data["territoires"]))
    verifier("Vallee-Aoste et Nice n'en ont qu'UNE chacune",
             all(len(t["rows"]) == 1 for t in data["territoires"]
                 if t["nom"] in ("Vallee-Aoste", "Nice")))

    html = render_template("sources_provinces.html", active="sources_provinces", **data)
    verifier("le rendu produit une vraie page (pas vide)", len(html) > 2000, len(html))
    verifier("le lien de nav pointe vers la bonne route",
             '/sources-provinces' in (ROOT / "app" / "templates" / "base.html")
             .read_text(encoding="utf-8"))
    verifier("le manque réel (Novara) apparaît dans la page rendue", "Novara" in html)
    verifier("les zéros sont mis en évidence visuellement (fond rouge)",
             "#fdeaea" in html)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
