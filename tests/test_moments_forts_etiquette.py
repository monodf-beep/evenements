#!/usr/bin/env python3
"""Fixture : l'étiquette des moments forts (utils/moments_forts.py).

POURQUOI. C'est ce marqueur qui décide de ce qu'une strate de home et une page dédiée
montrent. Mesuré le 2026-09-22 sur le rendu réel du mu-plugin, SANS marqueur : la
sélection par date + territoire ramenait BeerCult, le Biella Sport Festival et une
exposition Kusama sous un titre « patrimoine ». Une règle fausse ici ne se voit pas
dans le code, elle se voit en ligne.

Chaque volet porte sa CONTRE-ÉPREUVE, et elles ne sont pas décoratives : un test qui
ne cherche qu'à se donner raison ne prouve rien (CLAUDE.md, règle 3).

  1. LE CAS QUI DOIT PASSER, choisi aux deux bornes de la fenêtre.
  2. LA SOURCE. Une fiche du bon territoire, aux bonnes dates, mais d'une autre source
     ne doit RIEN recevoir — c'est exactement le cas BeerCult.
  3. LES BORNES. La veille et le lendemain sont dehors ; une fiche SANS date aussi,
     parce qu'une donnée manquante n'est pas un événement hors période (règle 5).
  4. LA LANGUE. `post_tag` est traduite par Polylang sur ce site (six paires `-it`
     mesurées en ligne le 22/09) : la fiche italienne doit recevoir le libellé italien,
     pas le français.
  5. LE DÉFAUT. Aucun moment déclaré, ou fichier illisible → liste VIDE, donc le
     nettoyage des étiquettes que publisher_as faisait déjà continue de se faire.

Lancer : .venv/bin/python -m tests.test_moments_forts_etiquette
"""
import json
import sys
import tempfile
from pathlib import Path

from utils.moments_forts import charger, etiquettes, slug
# Le nom est IMPORTÉ du script, pas retapé : c'est lui qui l'écrit en base, et une
# apostrophe typographique d'un côté et droite de l'autre suffirait à ne plus rien
# étiqueter, en silence.
from scripts.moisson_plaisirs_culture import SOURCE_NAME as PLAISIRS

ROOT = Path(__file__).resolve().parent.parent
GEP = "Ministero della Cultura — GEP"

echecs = 0


def echec(m):
    global echecs
    echecs += 1
    print("ECHEC : " + m)


def verifie(attendu, obtenu, quoi):
    if obtenu == attendu:
        print("  ok  %s → %s" % (quoi, obtenu or "[]"))
    else:
        echec("%s : attendu %s, obtenu %s" % (quoi, attendu, obtenu))


def test_config_reelle():
    moments = charger()
    if not moments:
        echec("config/moments_forts.json ne déclare aucun moment")
        return
    m = moments[0]
    for lang in ("fr", "it"):
        if not slug(m, lang):
            echec("le moment « %s » n'a pas de slug en %s" % (m.get("etiquette"), lang))
    # Le slug ne doit pas porter d'année : une adresse d'édition annuelle ne se millésime
    # pas (docs/EDITIONS_ANNUELLES.md), et l'étiquette sert de clé à la page dédiée.
    for lang in ("fr", "it"):
        s = slug(m, lang)
        if any(a in s for a in ("2025", "2026", "2027")):
            echec("le slug « %s » porte une année : la page dédiée changerait d'adresse "
                  "chaque septembre" % s)
    print("  ok  config réelle : slugs %s / %s, sans millésime"
          % (slug(m, "fr"), slug(m, "it")))


def test_regles():
    m = charger()
    if not m:
        return
    mo = m[0]
    fr = mo["etiquette"]["fr"]
    it = mo["etiquette"]["it"]

    # 1. LE CAS QUI DOIT PASSER, aux DEUX bornes de la fenêtre.
    verifie([fr], etiquettes("piemont", mo["debut"], GEP, "fr", m), "borne basse (%s)" % mo["debut"])
    verifie([fr], etiquettes("piemont", mo["fin"], GEP, "fr", m), "borne haute (%s)" % mo["fin"])
    verifie([fr], etiquettes("vallee-d-aoste", "2026-09-26", GEP, "fr", m), "second territoire")

    # 1 bis. LE VOLET VALDÔTAIN (22/09/2026) : la Vallée d'Aoste n'est pas au programme
    #    du ministère, elle a sa propre source. Une fiche du 20/09 moissonnée par
    #    scripts/moisson_plaisirs_culture.py doit recevoir l'étiquette, en français et en
    #    italien — et la même fiche venue d'une AUTRE source, non (contre-épreuve : c'est
    #    bien la source qui décide, pas le couple territoire + dates).
    if PLAISIRS not in (mo.get("sources") or []):
        echec("« %s » (SOURCE_NAME de moisson_plaisirs_culture) absent des sources du "
              "moment : ses fiches ne seraient jamais étiquetées" % PLAISIRS)
    verifie([fr], etiquettes("vallee-d-aoste", "2026-09-20", PLAISIRS, "fr", m),
            "Vallée d'Aoste, 20/09, Plaisirs de Culture")
    verifie([it], etiquettes("vallee-d-aoste", "2026-09-20", PLAISIRS, "it", m),
            "Vallée d'Aoste, 20/09, Plaisirs de Culture, fiche italienne")
    verifie([], etiquettes("vallee-d-aoste", "2026-09-20", "Forte di Bard - Eventi", "fr", m),
            "Vallée d'Aoste, 20/09, AUTRE source")
    verifie([], etiquettes("vallee-d-aoste", "2026-09-28", PLAISIRS, "fr", m),
            "Plaisirs de Culture, le lendemain de la fenêtre")

    # 2. LA SOURCE — le cas BeerCult, mesuré en ligne.
    verifie([], etiquettes("piemont", "2026-09-26", "beercult.it", "fr", m),
            "bon territoire, bonnes dates, AUTRE source")

    # 3. LES BORNES et la fiche sans date.
    verifie([], etiquettes("piemont", "2026-09-18", GEP, "fr", m), "la veille de la fenêtre")
    verifie([], etiquettes("piemont", "2026-09-28", GEP, "fr", m), "le lendemain de la fenêtre")
    verifie([], etiquettes("piemont", "", GEP, "fr", m), "fiche sans date")
    verifie([], etiquettes("savoie", "2026-09-26", GEP, "fr", m), "hors territoire")

    # 4. LA LANGUE.
    verifie([it], etiquettes("piemont", "2026-09-26", GEP, "it", m), "fiche italienne")
    if fr == it:
        echec("les deux langues rendent le même libellé : Polylang en ferait un terme suffixé")

    # 5. LE DÉFAUT — et c'est lui qui garantit que le nettoyage existant ne change pas.
    verifie([], etiquettes("piemont", "2026-09-26", GEP, "fr", []), "aucun moment déclaré")
    with tempfile.TemporaryDirectory() as d:
        casse = Path(d) / "casse.json"
        casse.write_text("{ ceci n'est pas du JSON", encoding="utf-8")
        verifie([], etiquettes("piemont", "2026-09-26", GEP, "fr", charger(casse)),
                "config illisible")

    # 6. UN MOMENT SANS SOURCE s'appuie sur territoire + dates seuls. Volontaire, et
    #    c'est pour ça que le fichier de config le dit : ne déclarer un moment sans
    #    source que s'il occupe vraiment tout son territoire à ses dates (Noël).
    noel = [{"etiquette": {"fr": "Noël"}, "slug": {"fr": "noel"},
             "debut": "2026-12-01", "fin": "2026-12-25", "territoires": ["savoie"]}]
    verifie(["Noël"], etiquettes("savoie", "2026-12-10", "n-importe-quelle-source", "fr", noel),
            "moment sans source déclarée")
    verifie([], etiquettes("piemont", "2026-12-10", "x", "fr", noel),
            "moment sans source, mauvais territoire")


def test_branchement():
    """publisher_as doit VRAIMENT appeler ce module — et avec la langue de la fiche.

    Sans ce volet, on pourrait avoir un module parfait que personne n'appelle : c'est
    la règle 1 transposée au code (un fichier livré ne prouve pas qu'il tourne).
    """
    src = (ROOT / "scripts" / "publisher_as.py").read_text(encoding="utf-8")
    if 'payload["tags"] = []' in src:
        echec("publisher_as envoie encore une liste vide en dur")
    if "etiquettes_moments(" not in src:
        echec("publisher_as n'appelle pas utils.moments_forts")
    elif "_lang(event)" not in src.split("etiquettes_moments(")[1][:400]:
        echec("publisher_as appelle le module sans lui passer la langue de la fiche")
    else:
        print("  ok  publisher_as appelle le module, avec la langue")


if __name__ == "__main__":
    print("— la configuration livrée")
    test_config_reelle()
    print("— les règles")
    test_regles()
    print("— le branchement")
    test_branchement()
    print(("%d echec(s)" % echecs) if echecs else "tout est vert")
    sys.exit(1 if echecs else 0)
