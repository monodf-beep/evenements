#!/usr/bin/env python3
"""Fixture : l'organisateur lu dans le JSON-LD d'une page officielle (utils.jsonld).

D'OÙ ÇA VIENT — mesure du 2026-09-22 sur la base de production :

    vivantes                                  340
    sans organisateur                         237
    sans url officielle                       212
    ni l'un ni l'autre                        148
    sans organisateur MAIS avec url officielle  89   ← celles-ci

Quatre-vingt-neuf fiches dont on a déjà la page officielle et dont on ne tirait pas
l'organisateur : `moisson_officielle` télécharge cette page tous les matins, et
`jsonld.champs()` ne lisait pas `organizer`. On jetait l'information.

POURQUOI CETTE FIXTURE EST SURTOUT UNE FIXTURE DE REFUS. Écrire un organisateur FAUX sur
89 fiches publiées serait pire que la case vide : une case vide se voit, une case fausse
se croit. Et beaucoup de pages déclarent dans `organizer` l'éditeur du site, le CMS ou le
thème. Le dépôt a déjà ce précédent — « l'organisateur annoncé semble être la
journaliste, pas l'organisatrice » (CLAUDE.md, règle 6).

Elle contient donc, comme l'exige la règle 3, DES CAS QUI DOIVENT PASSER choisis près de
la frontière : un nom court (« MJC »), un nom long mais légitime, un organisateur en
second après un CMS refusé. Un portillon qui ne teste que ce qu'il refuse passe au vert
sur un design faux.

Lancer : .venv/bin/python -m tests.test_jsonld_organisateur
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import jsonld  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


def page(organizer: str, reste: str = '"startDate":"2027-05-01",') -> str:
    return ('<html><head><script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Event","name":"Un concert",'
            + reste + '"organizer":' + organizer + '}</script></head><body></body></html>')


def orga(html: str) -> str:
    return jsonld.champs(html).get("organisateur", "")


# --- CE QUI DOIT PASSER (la moitié qui manque aux portillons ratés) ----------------
verifier("un objet Organization nommé",
         orga(page('{"@type":"Organization","name":"Ville de Menton"}')) == "Ville de Menton")
verifier("une simple chaîne",
         orga(page('"Association Les Amis du Fort"')) == "Association Les Amis du Fort")
verifier("un SIGLE court — cas frontière, la longueur minimale",
         orga(page('"MJC"')) == "MJC", orga(page('"MJC"')))
verifier("un nom long mais légitime passe (on refuse les PHRASES, pas les noms longs)",
         orga(page('"Communauté de communes du Pays du Mont-Blanc"'))
         == "Communauté de communes du Pays du Mont-Blanc")
verifier("dans une liste, le premier EXPLOITABLE, même en second",
         orga(page('[{"name":"Wix"},{"name":"Théâtre de Chambéry"}]')) == "Théâtre de Chambéry")
verifier("une Person nommée (un organisateur peut être une personne)",
         orga(page('{"@type":"Person","name":"Jean Moulin"}')) == "Jean Moulin")

# --- CE QUI DOIT ÊTRE REFUSÉ --------------------------------------------------------
for outil in ("WordPress", "Wix", "Eventbrite", "The Events Calendar", "Yoast",
              "webmaster", "Rédaction"):
    verifier(f"« {outil} » n'est pas un organisateur", orga(page(f'"{outil}"')) == "",
             orga(page(f'"{outil}"')))
verifier("la casse et le point final ne sauvent pas un refus",
         orga(page('"wordpress."')) == "")
verifier("une URL est une coordonnée, pas un nom", orga(page('"https://exemple.org"')) == "")
verifier("un courriel non plus", orga(page('"contact@mairie.fr"')) == "")
verifier("un @handle non plus", orga(page('"@theatre_chambery"')) == "")
verifier("une PHRASE est un descriptif, pas un organisme",
         orga(page('"' + "Un événement organisé dans le cadre de la saison culturelle "
                   "portée par les partenaires du territoire" + '"')) == "")
verifier("un nom d'un seul signe est refusé", orga(page('"X"')) == "")
verifier("une chaîne vide aussi", orga(page('""')) == "")
verifier("une liste entièrement refusée ne rend rien",
         orga(page('[{"name":"WordPress"},{"name":"Wix"}]')) == "")

# --- Ce que l'absence doit produire : une clé ABSENTE, jamais une valeur vide -------
verifier("pas d'organizer → la clé n'existe pas (on n'invente rien)",
         "organisateur" not in jsonld.champs(
             '<script type="application/ld+json">{"@type":"Event","name":"X",'
             '"startDate":"2027-05-01"}</script>'))
verifier("aucun JSON-LD du tout → aucun champ", jsonld.champs("<html></html>") == {})

# --- Le reste de `champs()` ne doit pas avoir bougé --------------------------------
complet = jsonld.champs(
    '<script type="application/ld+json">{"@type":"Event","name":"X",'
    '"startDate":"2027-05-01","endDate":"2027-05-03",'
    '"location":{"@type":"Place","name":"Le Manège",'
    '"address":{"addressLocality":"Chambéry"}},'
    '"image":"https://x/a.jpg","organizer":{"name":"Ville de Chambéry"}}</script>')
verifier("les dates sont toujours lues", complet.get("date_event_start") == "2027-05-01")
verifier("le lieu et la ville aussi",
         complet.get("lieu") == "Le Manège" and complet.get("ville") == "Chambéry")
verifier("l'image aussi", complet.get("url_image") == "https://x/a.jpg")
verifier("et l'organisateur s'ajoute sans rien déplacer",
         complet.get("organisateur") == "Ville de Chambéry")

# --- La moisson doit VISER le champ, sinon elle ne sélectionne pas les fiches -------
from scripts import moisson_officielle as moisson  # noqa: E402
verifier("« organisateur » figure dans les champs moissonnés",
         "organisateur" in moisson.CHAMPS, str(moisson.CHAMPS))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
