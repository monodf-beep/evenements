#!/usr/bin/env python3
"""Fixture : --retranslate vise l'inverse de la langue ACTUELLE de l'original.

23/09/2026 : jumelles créées en français depuis des originaux italiens bruts ; les
originaux sont ensuite rédigés en français ; --retranslate relit translated_lang='fr' et
ré-écrit les jumelles en français. Résultat mesuré : 43 fiches valdôtaines sans jumelle,
une vingtaine d'événements en double côté français.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_retraduction_cible
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.translate_events import cible_retraduction  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


ART_FR = json.dumps({"article": {"titre": "Une visite guidée du château de Sarre",
                                 "chapo": "Le château ouvre ses portes aux familles pour une visite",
                                 "corps": "La visite commence dans la cour et se poursuit dans les salles."}})
ART_IT = json.dumps({"article": {"titre": "Una visita guidata al castello di Sarre",
                                 "chapo": "Il castello apre le sue porte alle famiglie per una visita",
                                 "corps": "La visita comincia nel cortile e prosegue nelle sale."}})
BRUT_IT = {"title": "Effimeri, Erranti e Vagabondi",
           "description": "Il castello apre le sue porte ai bambini e ai genitori per una visita"}

_check("le cas du 23/09 : original rédigé en FR, jumelle mémorisée 'fr' → on vise l'italien",
       cible_retraduction({**BRUT_IT, "enrich_data": ART_FR}, {"translated_lang": "fr"}) == "it")
_check("FRONTIÈRE : original rédigé en IT, jumelle 'fr' → on garde le français",
       cible_retraduction({**BRUT_IT, "enrich_data": ART_IT}, {"translated_lang": "fr"}) == "fr")
_check("FRONTIÈRE : original brut italien sans article → français",
       cible_retraduction(dict(BRUT_IT), {"translated_lang": ""}) == "fr")
_check("original rédigé en FR, jumelle 'it' (cas normal) → italien, inchangé",
       cible_retraduction({**BRUT_IT, "enrich_data": ART_FR}, {"translated_lang": "it"}) == "it")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
