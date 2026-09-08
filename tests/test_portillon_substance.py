#!/usr/bin/env python3
"""Fixture : le portillon de substance, et surtout ce qu'il ne doit PAS bloquer.

Aucun réseau, aucune base : `utils.substance` est pur, et `build_post` est injectée.

POURQUOI CE PORTILLON (2026-08-05). AdSense a refusé le site pour « contenu à faible
valeur informative ». La mesure a montré que la longueur RENDUE des pages était
correcte, 700 à 2300 mots, mais que la part propre valait environ 250 mots pour 1100
rendus : le reste est une charpente identique sur 257 fiches. Et 59 fiches publiées
portaient moins de cent mots à elles.

LE CAS QUI COMPTE LE PLUS est le quatrième : une fiche maigre DÉJÀ en ligne doit
pouvoir être republiée. Bloquer sa republication ne la retirerait pas du site, ça y
figerait une version plus ancienne — et empêcherait la seule manœuvre qui la répare,
enrichir puis republier. Le verrou radar porte déjà ce raisonnement, écrit noir sur
blanc dans publish_batch_as ; ce portillon le reprend, et ce test l'empêche de se perdre.

Lancer : .venv/bin/python -m tests.test_portillon_substance
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import substance  # noqa: E402


def build_post_factice(ev):
    """Imite scripts.publisher.build_post : (titre, contenu HTML)."""
    if ev.get("casse"):
        raise ValueError("evenement mal forme")
    return ev.get("title", ""), ev.get("_html", "")


def article(mots: int) -> str:
    """HTML réaliste : un chapô en gras, un corps, et un programme en liste."""
    corps = " ".join(f"mot{i}" for i in range(mots))
    return (f"<p><strong>Un chap&ocirc; qui compte</strong></p><p>{corps}</p>"
            "<h3>Programme</h3><ul><li>19h ouverture</li></ul>")


echecs = 0


def verifier(libelle, condition, detail=""):
    global echecs
    if condition:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f"\n      {detail}" if detail else ""))


print("──── comptage ────")
# 5 mots de chapô + N du corps + 3 du programme + 1 du titre h3.
n = substance.mots_publies({"_html": article(100)}, build_post_factice)
verifier("les mots du corps sont comptés", 100 <= n <= 115, f"obtenu {n}")
verifier("les entités HTML ne comptent pas comme des mots parasites",
         substance.mots_de("<p>caf&eacute; &amp; th&eacute;</p>") == 3,
         f"obtenu {substance.mots_de('<p>caf&eacute; &amp; th&eacute;</p>')}")
verifier("contenu vide = 0", substance.mots_publies({"_html": ""}, build_post_factice) == 0)
verifier("build_post qui lève = 0, donc la fiche est retenue (prudent)",
         substance.mots_publies({"casse": True}, build_post_factice) == 0)

print("\n──── plancher ────")
os.environ.pop("PUBLISH_MIN_MOTS", None)
verifier(f"défaut = {substance.MIN_MOTS_DEFAUT}", substance.plancher() == substance.MIN_MOTS_DEFAUT)
os.environ["PUBLISH_MIN_MOTS"] = "300"
verifier("réglable par PUBLISH_MIN_MOTS", substance.plancher() == 300)
os.environ["PUBLISH_MIN_MOTS"] = "pas un nombre"
verifier("valeur illisible → on retombe sur le défaut, pas d'exception",
         substance.plancher() == substance.MIN_MOTS_DEFAUT)
os.environ.pop("PUBLISH_MIN_MOTS", None)

print("\n──── la règle de rétention ────")
plancher = substance.plancher()


def retenue(ev):
    """Réplique la condition du portillon : maigre ET pas encore en ligne."""
    n = substance.mots_publies(ev, build_post_factice)
    return n < plancher and not (ev.get("wp_post_id_as") or 0)


verifier("création maigre → RETENUE",
         retenue({"id": 1, "_html": article(40)}) is True)
verifier("création fournie → passe",
         retenue({"id": 2, "_html": article(400)}) is False)
verifier("fiche maigre DÉJÀ EN LIGNE → passe (sinon on fige une version plus ancienne)",
         retenue({"id": 3, "_html": article(40), "wp_post_id_as": 6352}) is False)
verifier("wp_post_id_as à 0 vaut « pas en ligne »",
         retenue({"id": 4, "_html": article(40), "wp_post_id_as": 0}) is True)
verifier("wp_post_id_as à None vaut « pas en ligne »",
         retenue({"id": 5, "_html": article(40), "wp_post_id_as": None}) is True)

print("\n──── bande de surveillance ────")
verifier("la bande est au-dessus du plancher",
         substance.BANDE_MAIGRE > substance.MIN_MOTS_DEFAUT)
milieu = substance.mots_publies({"_html": article(200)}, build_post_factice)
verifier("une fiche de la bande n'est PAS retenue, seulement comptée",
         retenue({"id": 6, "_html": article(200)}) is False
         and plancher <= milieu < substance.BANDE_MAIGRE,
         f"mots = {milieu}, plancher = {plancher}, bande = {substance.BANDE_MAIGRE}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
