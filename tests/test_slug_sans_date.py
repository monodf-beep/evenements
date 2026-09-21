#!/usr/bin/env python3
"""Fixture : une URL ne porte JAMAIS de date (2026-09-21).

⚠️ Aucun réseau, aucun appel LLM, aucune base.

D'OÙ ÇA VIENT. Le 21/09, Franck, à propos d'une adresse d'événement annuel : « les url
doivent-elles comporter la date alors qu'on veut que le lien et l'événement soit mis à
jour d'une année sur l'autre ? », puis : « ne mets jamais les dates, mets dans la
doctrine qu'il ne faut jamais mettre les dates ». C'est le prolongement de sa décision
des 08-09/09 (docs/EDITIONS_ANNUELLES.md) : un événement annuel garde UNE adresse, mise
à jour d'édition en édition, pour capitaliser les backlinks. Une URL millésimée l'interdit.

CE QUI PRODUISAIT LA DATE, mesuré : `publisher_as` n'envoyait aucun slug pour une fiche
originale, donc WordPress dérivait le permalien du TITRE. Relevé le même jour par l'API :
27 des 188 fiches en ligne et non terminées portaient une année ou un mois dans leur URL.

CE QUE LA FIXTURE VÉRIFIE :

  1. LE TÉMOIN ROUGE : les slugs RÉELS relevés sur le site le 21/09 contiennent bien une
     date — sinon cette fixture ne prouverait rien.
  2. Les douze titres réels perdent leur date, et gardent tout le reste.
  3. ⚠️ LES CAS FRONTIÈRE QUI DOIVENT PASSER — ce qui RESSEMBLE à une date et n'en est
     pas : « 1 000 places », « 65e Fête de la Châtaigne », « Le Cercle des 4 saisons ».
  4. Aucun slug ne sort coupé au milieu d'un mot, ni terminé par un tiret ou un
     mot-outil : le filtrage passe AVANT la coupe à 70 caractères (les deux défauts
     étaient dans le premier dry-run du 21/09, et lus dedans).
  5. `publisher_as` pose ce slug à la CRÉATION seulement — une republication ne renomme
     pas une adresse déjà indexée.

Lancer : .venv/bin/python -m tests.test_slug_sans_date
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.seo import slug_sans_date  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


MOIS = ("janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout",
        "septembre", "octobre", "novembre", "decembre", "gennaio", "febbraio", "marzo",
        "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre",
        "dicembre")


def _porte_une_date(slug: str) -> bool:
    mots = slug.split("-")
    return any(re.fullmatch(r"(?:19|20)\d\d", m) or m in MOIS for m in mots)


# ════════════════════════════════════════════════════════════════════════════════════════
# 1. LE TÉMOIN ROUGE — les adresses telles qu'elles sont en ligne le 21/09
# ════════════════════════════════════════════════════════════════════════════════════════
print("──── 1. témoin rouge : ces adresses-là portent VRAIMENT une date ────")
EN_LIGNE = [
    "marche-au-fort-2026-les-saveurs-du-val-daoste-envahissent-bard",                 # WP#9523
    "la-foire-des-alpes-2026-reunit-les-elevages-de-vallee-daoste-a-saint-christophe",  # WP#9528
    "du-24-au-27-septembre-terra-madre-salone-del-gusto-apporte-la-biodiversite",     # WP#2190
    "musique-de-chambre-au-foyer-de-lopera-de-nice-une-serie-jusquen-juin-2027",      # WP#8617
    "la-saint-ours-2026-rendez-vous-en-vallee-d-aoste",                               # WP#772
]
for s in EN_LIGNE:
    _check(f"« {s[:56]}… » porte une date", _porte_une_date(s))

# ════════════════════════════════════════════════════════════════════════════════════════
# 2. LES TITRES RÉELS — ce que la règle en fait
# ════════════════════════════════════════════════════════════════════════════════════════
print("\n──── 2. les titres réels, débarrassés de leur date ────")
CAS = [
    ("Marché au Fort 2026 : les saveurs du Val d'Aoste envahissent Bard",
     "marche-au-fort-les-saveurs-du-val-daoste-envahissent-bard"),
    ("La Foire des Alpes 2026 réunit les élevages de Vallée d'Aoste à Saint-Christophe",
     "la-foire-des-alpes-reunit-les-elevages-de-vallee-daoste-a-saint"),
    ("Du 24 au 27 septembre, Terra Madre Salone del Gusto apporte la biodiversité au "
     "centre historique de Turin",
     "terra-madre-salone-del-gusto-apporte-la-biodiversite-au-centre"),
    ("Trois façades pour raconter les quartiers Aurora et Barriera, à Turin, "
     "dès le 25 septembre",
     "trois-facades-pour-raconter-les-quartiers-aurora-et-barriera-a-turin"),
    ("Musique de chambre au Foyer de l'Opéra de Nice : une série jusqu'en juin 2027",
     "musique-de-chambre-au-foyer-de-lopera-de-nice-une-serie"),
    ("SMILE : l'Orchestra Filarmonica di Torino ouvre sa saison le 20 octobre au "
     "Conservatorio Verdi",
     "smile-lorchestra-filarmonica-di-torino-ouvre-sa-saison"),
    ("Dal 3 al 6 dicembre torna in Valle d'Aosta il Grand Continent Summit",
     "torna-in-valle-daosta-il-grand-continent-summit"),
    ("La Fiera del Bue Grasso di Carrù revient le 17 décembre 2026",
     "la-fiera-del-bue-grasso-di-carru-revient"),
    ("La Saint-Ours 2026, rendez-vous en Vallée d'Aoste",
     "la-saint-ours-rendez-vous-en-vallee-daoste"),
    ("Lo Pan Ner", "lo-pan-ner"),
]
for titre, attendu in CAS:
    obtenu = slug_sans_date(titre)
    _check(f"« {titre[:52]}… »", obtenu == attendu, f"\n        obtenu   : {obtenu}"
                                                    f"\n        attendu  : {attendu}")

print("\n   et AUCUN des slugs produits ne porte encore une date :")
for titre, _ in CAS:
    _check(f"   « {slug_sans_date(titre)[:58]} »", not _porte_une_date(slug_sans_date(titre)))

# ════════════════════════════════════════════════════════════════════════════════════════
# 3. LES CAS FRONTIÈRE — ce qui RESSEMBLE à une date et n'en est pas
# ════════════════════════════════════════════════════════════════════════════════════════
print("\n──── 3. cas frontière : les nombres qui ne sont pas des dates ────")
_check("« 1 000 places supplémentaires » garde son millier",
       "1-000-places-supplementaires" in slug_sans_date(
           "EVO 2026 à Nice : trois jeux inédits et 1 000 places supplémentaires"),
       slug_sans_date("EVO 2026 à Nice : trois jeux inédits et 1 000 places supplémentaires"))
_check("« 65e Fête de la Châtaigne de Fénis » est intacte",
       slug_sans_date("65e Fête de la Châtaigne de Fénis") == "65e-fete-de-la-chataigne-de-fenis",
       slug_sans_date("65e Fête de la Châtaigne de Fénis"))
_check("« Huit violoncelles » n'a rien à perdre",
       slug_sans_date("Huit violoncelles en carte blanche à l'Opéra de Nice")
       == "huit-violoncelles-en-carte-blanche-a-lopera-de-nice")
_check("un quantième LOIN d'un mois reste : « les 24 heures du Mans »",
       slug_sans_date("Les 24 heures du Mans") == "les-24-heures-du-mans",
       slug_sans_date("Les 24 heures du Mans"))
_check("un titre qui n'est QUE sa date rend quand même une adresse",
       slug_sans_date("Le 17 décembre 2026") != "",
       slug_sans_date("Le 17 décembre 2026"))

# ════════════════════════════════════════════════════════════════════════════════════════
# 4. LA FORME DE L'ADRESSE — les deux défauts lus dans le premier dry-run
# ════════════════════════════════════════════════════════════════════════════════════════
print("\n──── 4. la forme : ni coupe au milieu d'un mot, ni tiret orphelin ────")
LONG = ("Du 24 au 27 septembre, Terra Madre Salone del Gusto apporte la biodiversité au "
        "centre historique de Turin avec des centaines de producteurs venus du monde entier")
s = slug_sans_date(LONG)
_check("l'adresse tient dans 70 caractères", len(s) <= 70, f"{len(s)} : {s}")
_check("   et ne se termine ni par un tiret ni par un mot tronqué",
       not s.endswith("-") and s.split("-")[-1] in LONG.lower()
       .replace("é", "e").replace("è", "e").replace("à", "a"), s)
_check("   et ne commence pas par un tiret", not s.startswith("-"), s)
_check("un titre vide rend une chaîne vide, sans lever", slug_sans_date("") == "")

# ════════════════════════════════════════════════════════════════════════════════════════
# 5. LE CÂBLAGE — posé à la création, jamais sur une adresse déjà indexée
# ════════════════════════════════════════════════════════════════════════════════════════
print("\n──── 5. publisher_as : slug à la création seulement ────")
src = (ROOT / "scripts" / "publisher_as.py").read_text(encoding="utf-8")
_check("publisher_as appelle slug_sans_date", "slug_sans_date" in src)
_check("   et seulement quand la fiche n'a pas encore de post WordPress",
       'elif not event.get("wp_post_id_as"):' in src)
_check("la consigne du prompt SEO n'autorise plus l'année « si récurrent »",
       "sans année si récurrent" not in (ROOT / "utils" / "seo.py").read_text(encoding="utf-8"))

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
