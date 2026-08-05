#!/usr/bin/env python3
"""Fixture : la connaissance locale n'arrive que sur les fiches qu'elle concerne.

Notes jetables dans un dossier temporaire, jamais docs/savoir/ du dépôt.

POURQUOI CE MODULE EXISTE (2026-08-05). AdSense a refusé le site pour « contenu à faible
valeur informative » : la part propre d'une fiche vaut environ 250 mots dans 1100
rendus. Le manque n'est pas une longueur, c'est un apport. Le savoir de Franck sur
l'espace sabaudo est le gisement ; ce module lui donne un endroit où se déposer une fois
et servir cinquante fiches.

LE CAS QUI COMPTE LE PLUS est le troisième : une note sur Bard ne doit JAMAIS remonter
sur une fiche de Chambéry. Un savoir mal ciblé est pire qu'un savoir absent — il ferait
écrire des contrevérités avec aplomb.

Lancer : .venv/bin/python -m tests.test_savoir
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import savoir  # noqa: E402

dossier = Path(tempfile.mkdtemp())
os.environ[savoir.SAVOIR_ENV] = str(dossier)


def note(nom: str, entete: str, texte: str) -> None:
    (dossier / f"{nom}.md").write_text(f"---\n{entete}\n---\n{texte}\n", encoding="utf-8")


note("forte-di-bard",
     "lieux: Forte di Bard, Fort de Bard\nvilles: Bard\nterritoires: vallee-d-aoste",
     "Forteresse des années 1830, ascenseurs panoramiques, concerts dans la cour d'armes.")
note("vallee-d-aoste",
     "territoires: vallee-d-aoste",
     "Region bilingue franco-italienne, la plus petite d'Italie.")
note("sagre-piemontaises",
     "territoires: piemont\ncategories: Fêtes & Traditions populaires",
     "Les sagre sont des fetes de village organisees autour d'un produit.")
# Sans en-tête : ne doit JAMAIS être sélectionnée, elle ne sait pas où elle s'applique.
(dossier / "orpheline.md").write_text("Du texte sans en-tete.\n", encoding="utf-8")
# En-tête présent mais vide : même traitement.
note("vide", "lieux:", "Texte sans cle exploitable.")

echecs = 0


def verifier(libelle, condition, detail=""):
    global echecs
    if condition:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f"\n      {detail}" if detail else ""))


print("──── lecture des notes ────")
dispo = savoir.notes_disponibles()
noms = sorted(n["nom"] for n in dispo)
verifier("les notes valides sont lues",
         noms == ["forte-di-bard", "sagre-piemontaises", "vallee-d-aoste"], f"lues = {noms}")
verifier("une note sans en-tête est ignorée", "orpheline" not in noms)
verifier("un en-tête sans valeur exploitable est ignoré", "vide" not in noms)

print("\n──── sélection contextuelle ────")
bard = {"lieu": "Forte di Bard", "ville": "Bard", "territoire": "vallee-d-aoste",
        "llm_categorie": "Concerts & Musique"}
sel = [n["nom"] for n in savoir.notes_pour(bard)]
verifier("la note du LIEU passe avant celle du territoire",
         sel and sel[0] == "forte-di-bard", f"selection = {sel}")
verifier("la note du territoire remonte aussi", "vallee-d-aoste" in sel)

chambery = {"lieu": "Le Phare", "ville": "Chambéry", "territoire": "savoie",
            "llm_categorie": "Concerts & Musique"}
sel_ch = [n["nom"] for n in savoir.notes_pour(chambery)]
verifier("AUCUNE note de Bard sur une fiche de Chambéry", sel_ch == [], f"selection = {sel_ch}")
verifier("et donc aucun bloc injecté", savoir.bloc_pour_prompt(chambery) == "")

sagra = {"lieu": "Borgata Roggia", "ville": "Bosconero", "territoire": "piemont",
         "llm_categorie": "Fêtes & Traditions populaires"}
verifier("territoire + catégorie sélectionnent la note piémontaise",
         [n["nom"] for n in savoir.notes_pour(sagra)] == ["sagre-piemontaises"])

print("\n──── accents et graphies ────")
accents = {"lieu": "", "ville": "", "territoire": "Vallée d'Aoste", "llm_categorie": ""}
verifier("« Vallée d'Aoste » reconnaît « vallee-d-aoste »",
         "vallee-d-aoste" in [n["nom"] for n in savoir.notes_pour(accents)])

print("\n──── le bloc de prompt ────")
bloc = savoir.bloc_pour_prompt(bard)
verifier("le bloc contient le texte de la note", "ascenseurs panoramiques" in bloc)
verifier("le bloc interdit explicitement la recopie", "ne PAS recopier" in bloc)
verifier("le bloc rappelle la primauté des faits vérifiés",
         "Ne contredis jamais les faits" in bloc)
os.environ["SAVOIR_MAX_CHARS"] = "80"
verifier("SAVOIR_MAX_CHARS tronque au lieu de faire exploser le contexte",
         len(savoir.bloc_pour_prompt(bard)) < 400)
os.environ.pop("SAVOIR_MAX_CHARS", None)

print("\n──── robustesse ────")
os.environ[savoir.SAVOIR_ENV] = str(dossier / "ce-dossier-n-existe-pas")
verifier("dossier absent → pas de note, pas d'exception", savoir.notes_disponibles() == [])
verifier("dossier absent → bloc vide", savoir.bloc_pour_prompt(bard) == "")
os.environ[savoir.SAVOIR_ENV] = str(dossier)
verifier("événement sans aucun champ → bloc vide", savoir.bloc_pour_prompt({}) == "")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
