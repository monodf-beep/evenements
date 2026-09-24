#!/usr/bin/env python3
"""Fixture : l'extrait d'une fiche vient de son ARTICLE (langue de la page), pas de la
description brute de la source.

Incident du 24/09/2026 (capture du flux RSS par Franck) : la page française de Palazzo
Carignano résumée en italien, « Palazzo Carignano, Torino — In occasione delle
Giornate… ». 94 fiches à venir dans ce cas ce jour-là. Rouge sur la version d'avant :
l'extrait valait le début de la description.

Cas qui doivent PASSER intacts : une réponse SEO (`seo_answer`) reste prioritaire ; une
fiche SANS article garde le repli sur la description ; un chapeau trop court (< 60
caractères) laisse la main au paragraphe suivant.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_extrait_langue_article
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scripts.publisher_as as pa  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    print(("OK    " if cond else "ÉCHEC ") + label + ("" if cond else f"  → {detail}"))
    echecs += 0 if cond else 1


DESC_IT = ("Palazzo Carignano, Torino — In occasione delle Giornate europee del patrimonio, "
           "gli Appartamenti dei Principi di Savoia-Carignano aprono in serata.")
CHAPO_FR = ("Le 26 septembre 2026, les Appartements des Princes de Palazzo Carignano, à Turin, "
            "ouvrent exceptionnellement en soirée, avec des visites guidées chaque heure.")
BASE = {"id": 1, "title": "Palazzo Carignano", "description": DESC_IT, "lang": "fr",
        "force_lang": "fr", "categorie": "", "ville": "Torino", "lieu": "Palazzo Carignano",
        "date_event_start": "2026-09-26", "url_source": "https://example.org/x"}


def extrait(**champs):
    ev = dict(BASE, **champs)
    try:
        return pa._build_payload(ev, skip_media=True).get("excerpt", "")
    except TypeError:
        return pa._build_payload(ev).get("excerpt", "")


article = json.dumps({"article": {"titre": "Palazzo Carignano ouvert en soirée",
                                  "chapo": CHAPO_FR, "corps": "Un corps en français. " * 10}})
e = extrait(enrich_data=article)
_check("fiche rédigée en français, description italienne : l'extrait est le chapeau français",
       e.startswith("Le 26 septembre 2026"), e[:90])
_check("… et ne contient rien de la description italienne", "In occasione" not in e, e[:90])
_check("… coupé proprement (≤ 201 caractères)", len(e) <= 201, len(e))

_check("seo_answer reste prioritaire",
       extrait(enrich_data=article, seo_answer="Réponse SEO en français.") == "Réponse SEO en français.")
_check("sans article, repli sur la description (comportement d'avant)",
       extrait(enrich_data="").startswith("Palazzo Carignano, Torino"))

court = json.dumps({"article": {"titre": "T", "chapo": "Trop court.",
                                "corps": "Un premier paragraphe du corps, écrit en français et assez long pour servir."}})
_check("chapeau trop court : le paragraphe suivant sert d'extrait",
       extrait(enrich_data=court).startswith("Un premier paragraphe"), extrait(enrich_data=court)[:80])

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)")
    sys.exit(1)
print("Tout passe.")
