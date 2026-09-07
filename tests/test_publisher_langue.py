#!/usr/bin/env python3
"""Fixture : l'étiquette Polylang posée à la PUBLICATION suit l'article rédigé, pas le
titre brut de la source.

INCIDENT RÉEL, 2026-09-07. Franck : « des fois on traduit depuis ici mais on ne fait pas
appel à Polylang qui doit tout gérer, c'est peut-être la double gestion qui entraîne des
pages en it et fr ». Mesuré sur le site : 15 des 126 fiches publiées encore devant nous
étaient étiquetées `it` avec un article FRANÇAIS, dont 11 sans jumelle française —
affichées en français sur le site italien, jamais traduites puisque crues italiennes.

Cause, lue dans le code : `publisher_as._lang` détectait la langue sur le titre et la
description BRUTS de la source (italiens pour un événement piémontais), alors que
`enrich` écrit toujours en français d'abord et que `translate_events` décide, lui, sur
l'article (`utils.lang.effective_lang`). Deux sources de vérité ; la mauvaise publiait.

Le cas qui DOIT PASSER près de la frontière : un article vraiment italien sous un titre
italien reste `it` — la correction ne francise pas tout.

Aucun réseau, fonction pure. Lancer : .venv/bin/python -m tests.test_publisher_langue
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publisher_as import _lang  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


def _ev(title, description, chapo=None, corps=None, article_title=None, **extra):
    ev = {"title": title, "description": description, "territoire": "Piemonte"}
    if chapo or corps:
        ev["enrich_data"] = json.dumps({"article": {"chapo": chapo or "", "corps": corps or ""}},
                                       ensure_ascii=False)
    if article_title:
        ev["article_title"] = article_title
    ev.update(extra)
    return ev


TITRE_IT = "Egitto. Sulle tracce degli dei — mostra al Palazzo Mathis"
DESC_IT = ("Una mostra unica che presenta pezzi inediti del Museo Egizio di Torino, con un "
           "percorso espositivo dedicato all'Egitto antico e alle divinità egizie.")
CHAPO_FR = ("Exposition unique présentant des pièces inédites du Musée égyptien de Turin, "
            "offrant un parcours consacré à l'Égypte ancienne et aux divinités égyptiennes.")
CORPS_FR = ("Le parcours s'organise autour des grandes divinités du panthéon. Les visiteurs "
            "découvrent des pièces qui n'avaient jamais quitté les réserves du musée, dans "
            "une scénographie pensée pour les familles et les scolaires.")
CHAPO_IT = ("Una mostra unica che presenta pezzi inediti del Museo Egizio di Torino, con un "
            "percorso dedicato all'Egitto antico e alle divinità del pantheon.")
CORPS_IT = ("Il percorso si organizza intorno alle grandi divinità. I visitatori scoprono "
            "pezzi che non avevano mai lasciato i depositi del museo, in un allestimento "
            "pensato per le famiglie e le scuole.")

print("──── le cas de l'incident : titre italien, article français ────")
_check("titre IT + article FR → étiquette fr (l'article fait foi)",
       _lang(_ev(TITRE_IT, DESC_IT, CHAPO_FR, CORPS_FR,
                 article_title="Le panthéon égyptien au Palazzo Mathis")) == "fr")

print("\n──── ce qui doit PASSER près de la frontière ────")
_check("titre IT + article IT → reste it (on ne francise pas tout)",
       _lang(_ev(TITRE_IT, DESC_IT, CHAPO_IT, CORPS_IT,
                 article_title="Egitto. Sulle tracce degli dei al Palazzo Mathis")) == "it")
_check("force_lang='it' l'emporte sur un article français (cas des traductions)",
       _lang(_ev(TITRE_IT, DESC_IT, CHAPO_FR, CORPS_FR, force_lang="it")) == "it")
_check("sans article : repli sur le titre brut (comportement historique)",
       _lang(_ev(TITRE_IT, DESC_IT)) == "it")
_check("sans article, titre français → fr",
       _lang(_ev("Le panthéon égyptien s'expose à Bra", "Une exposition consacrée aux dieux "
                 "de l'Égypte ancienne, avec des pièces du musée de Turin.")) == "fr")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
