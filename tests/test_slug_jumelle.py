#!/usr/bin/env python3
"""Fixture : l'adresse d'une traduction ne porte ni `-2`, ni la langue de l'original.

⚠️ Aucun réseau, aucun appel LLM, aucune base.

D'OÙ ÇA VIENT. Le 30/09/2026, Franck : « ça va pas du tout de mettre 2, 3 », puis deux
arbitrages — l'adresse italienne est tirée du TITRE ITALIEN, et les adresses déjà en
ligne sont renommées avec une 301. Mesuré la veille : les 103 jumelles italiennes à
venir portaient toutes un `-2`/`-3` et un slug français, parce que la traduction
reprenait le slug de l'original (« URL commune à la paire », 28/07) sur la foi d'un
commentaire qui affirmait que Polylang accepte deux fois le même slug. Faux ici.

CE QUE LA FIXTURE VÉRIFIE :

  1. LE TÉMOIN ROUGE : l'ancienne règle (le slug de l'original) redonne bien le slug
     français — celui que WordPress suffixait. Sinon cette fixture ne prouverait rien.
  2. Des titres italiens RÉELS (relevés sur le site le 30/09) donnent une adresse
     italienne, sans date, sans suffixe.
  3. LA COLLISION : un titre qui ne se traduit pas (« Orlando ») reçoit la ville.
  4. ⚠️ LES CAS QUI DOIVENT PASSER TELS QUELS : un titre traduit différent de l'original
     ne reçoit PAS de ville ; un titre entier qui finit par « di » le garde (seule une
     COUPE retire le mot-outil final) ; une ville déjà dans le titre n'est pas doublée.
  5. `renommer_slugs_jumelles.planifier` (pur) : ne retient que les jumelles
     italiennes non terminées à `-N`, résout une collision par la ville, met « à
     trancher » ce qu'elle ne résout pas, et ne donne jamais le même slug à deux fiches.
  6. Plus aucun chemin du dépôt ne recopie le slug de l'original sur la jumelle.

Lancer : .venv/bin/python -m tests.test_slug_jumelle
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.seo import a_suffixe_wp, slug_jumelle, slug_sans_date  # noqa: E402
from scripts.renommer_slugs_jumelles import planifier  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── 1. Témoin rouge : l'ancienne règle ────")
# Adresses RÉELLES des jumelles italiennes, relevées sur le site le 29/09 : le
# détecteur doit les voir, sinon le plan de renommage ne prouverait rien.
for reel in ("festival-photo-de-montmelian-9eme-edition-2", "orlando-2",
             "viens-avec-ton-doudou-lopera-de-nice-ouvre-ses-portes-aux-tout-petits-3",
             "lecomuseo-del-cossatese-e-delle-baragge-ouvre-gratuitement-2-2"):
    _check(f"slug réel repéré comme suffixé : {reel[:50]}", a_suffixe_wp(reel))
_check("et « it-3 » (Mille Storie) aussi", a_suffixe_wp("it-3"))
ancien = "festival-photo-de-montmelian-9eme-edition"
_check("la nouvelle règle ne redonne pas le slug de l'original",
       slug_jumelle("Festival Photo di Montmélian: cinque sguardi nelle strade", ancien,
                    "Montmélian") != ancien)

print("──── 2. Titres italiens réels (site, 30/09) ────")
REELS = [
    ("We Want Jazz 2026: sette concerti gratuiti in Valle d’Aosta",
     "we-want-jazz-sept-concerts-gratuits-en-vallee-daoste",
     "we-want-jazz-sette-concerti-gratuiti-in-valle-daosta"),
    ("Rowing Regatta a Torino: giovedì 1° ottobre la XXVIII edizione della sfida "
     "universitaria", "rowing-regatta-a-turin-1er-la-xxviiie-edition-du-duel-universitaire",
     "rowing-regatta-a-torino-la-xxviii-edizione-della-sfida-universitaria"),
    ("65ª Festa della Castagna di Fénis", "65e-fete-de-la-chataigne-de-fenis",
     "65-festa-della-castagna-di-fenis"),
    ("Il Salon de l’Étudiant a Nizza", "le-salon-de-letudiant-a-nice",
     "il-salon-de-letudiant-a-nizza"),
]
for titre, orig, attendu in REELS:
    obtenu = slug_jumelle(titre, orig, "")
    _check(f"« {titre[:50]} »", obtenu == attendu, f"→ {obtenu}")
    _check("   sans suffixe -N", not a_suffixe_wp(obtenu), obtenu)

print("──── 3. Collision : le titre ne se traduit pas ────")
_check("« Orlando » (original orlando) → orlando-nice",
       slug_jumelle("Orlando", "orlando", "Nice") == "orlando-nice")
_check("« Orlando » (original orlando-2) → la racine est reconnue malgré le -2",
       slug_jumelle("Orlando", "orlando-2", "Nizza") == "orlando-nizza")
_check("ville à plusieurs mots gardée ENTIÈRE malgré la coupe à 70",
       slug_jumelle("Chiara De Carlo et Luca Battagliotti en duo acoustique à Saint-Vincent "
                    "pour une longue soirée",
                    slug_sans_date("Chiara De Carlo et Luca Battagliotti en duo acoustique à "
                                   "Saint-Vincent pour une longue soirée"),
                    "Aoste").endswith("-aoste"))

print("──── 4. Ce qui doit PASSER sans retouche ────")
_check("titre traduit différent : PAS de ville ajoutée",
       slug_jumelle("Corri la ForTen, la corsa a piedi del Forte di Bard",
                    "corri-la-forten-la-course-a-pied-du-forte-di-bard", "Bard")
       == "corri-la-forten-la-corsa-a-piedi-del-forte-di-bard")
_check("titre ENTIER finissant par « di » : gardé (aucune coupe)",
       slug_sans_date("Le mille facce di") == "le-mille-facce-di")
_check("titre COUPÉ tombant sur « di » : retiré",
       not slug_sans_date("L’artista cinese Song Dong occupa l’intero MAO (Museo d’Arte "
                          "Orientale) di Torino fino a giugno").endswith("-di"))
_check("ville déjà dans le titre : pas doublée (l'appelant signalera la collision)",
       slug_jumelle("Nizza", "nizza", "Nizza") == "nizza")

print("──── 5. Le plan de renommage (pur) ────")
AUJ = "2026-09-30"
B = "https://agendasabauda.eu"
fiches = [
    {"id": 1, "url": f"{B}/evenement/orlando/", "titre": "Orlando", "ville": "Nice",
     "fin": "2026-10-06"},
    {"id": 2, "url": f"{B}/it/evenement/orlando-2/", "titre": "Orlando", "ville": "Nice",
     "fin": "2026-10-06"},
    # Deux événements distincts au MÊME titre italien (cas Ecomuseo, 30/09).
    {"id": 3, "url": f"{B}/it/evenement/ecomuseo-apre-2/", "titre": "Ecomuseo apre",
     "ville": "Cossato", "fin": "2026-10-04"},
    {"id": 4, "url": f"{B}/it/evenement/ecomuseo-apre-3/", "titre": "Ecomuseo apre",
     "ville": "Cossato", "fin": "2026-10-11"},
    # Collision que la ville ne résout pas : « Nizza » à Nizza, slug déjà pris.
    {"id": 5, "url": f"{B}/it/evenement/nizza/", "titre": "Nizza", "ville": "Nizza",
     "fin": "2026-10-10"},
    {"id": 6, "url": f"{B}/it/evenement/nice-2/", "titre": "Nizza", "ville": "Nizza",
     "fin": "2026-10-10"},
    # Terminée : hors périmètre (règle 5).
    {"id": 7, "url": f"{B}/it/evenement/vecchio-2/", "titre": "Vecchio evento",
     "ville": "", "fin": "2026-09-01"},
    # Française à -N : hors arbitrage, jamais touchée ici.
    {"id": 8, "url": f"{B}/evenement/fiera-2/", "titre": "Fiera", "ville": "",
     "fin": "2026-12-13"},
    # Italienne déjà propre : rien à faire.
    {"id": 9, "url": f"{B}/it/evenement/festa-pulita/", "titre": "Festa pulita",
     "ville": "", "fin": "2026-10-10"},
]
plan, a_trancher = planifier(fiches, AUJ)
par_id = {p["id"]: p["voulu"] for p in plan}
_check("Orlando IT → orlando-nice (le slug orlando est pris par la française)",
       par_id.get(2) == "orlando-nice", par_id)
_check("deux Ecomuseo au même titre : deux slugs DIFFÉRENTS, sans chiffre",
       par_id.get(3) and par_id.get(4) and par_id[3] != par_id[4]
       and not a_suffixe_wp(par_id[3]) and not a_suffixe_wp(par_id[4]), par_id)
_check("collision non résolue → à trancher, PAS renommée",
       [t["id"] for t in a_trancher] == [6] and 6 not in par_id, a_trancher)
_check("terminée, française, déjà propre : jamais dans le plan",
       not ({7, 8, 9, 1, 5} & set(par_id)), par_id)
_check("aucun slug voulu en double dans le plan",
       len(set(par_id.values())) == len(par_id))

print("──── 6. Plus aucun chemin ne recopie le slug de l'original ────")
te = (ROOT / "scripts" / "translate_events.py").read_text(encoding="utf-8")
lt = (ROOT / "scripts" / "link_translations_as.py").read_text(encoding="utf-8")
_check("translate_events passe par slug_jumelle",
       '"slug": slug_jumelle(' in te)
_check("   et plus par le slug de l'original seul",
       '"slug": _slug_of(ev.get("wp_permalink_as"))' not in te)
_check("link_translations_as n'appelle plus cs/v1/set-slug",
       "set-slug" not in lt and "_align_slug(" not in lt)

print()
print("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)")
sys.exit(1 if echecs else 0)
