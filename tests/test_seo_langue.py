#!/usr/bin/env python3
"""Fixture : `utils.seo.optimize_seo` rédige dans la langue de la fiche.

Jusqu'au 2026-09-09 le prompt disait « Produis, en français » en dur — d'où l'exclusion
des traductions dans seo_batch depuis le 02/08, et les points gris de Yoast sur toutes
les fiches italiennes. Aucun réseau : le client Anthropic est remplacé par un faux qui
CAPTURE le prompt envoyé.

Lancer : .venv/bin/python -m tests.test_seo_langue
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.seo import langue_seo, optimize_seo  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


class _Bloc:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FauxClient:
    def __init__(self):
        self.prompts = []
        self.messages = self

    def create(self, model, max_tokens, messages):
        self.prompts.append(messages[0]["content"])
        rep = {"seo_keyphrase": "k", "seo_title": "T — Agenda Sabauda", "seo_slug": "s",
               "seo_meta": "m", "seo_answer": "a", "seo_tags": [], "seo_faq": []}

        class R:
            content = [_Bloc(json.dumps(rep))]
        return R()


EV_FR = {"title": "Concert de musique classique à Annecy", "description": "Au bord du lac.",
         "territoire": "Savoie", "date_event_start": "2099-11-15"}
EV_IT = {**EV_FR, "title": "Concerto di musica classica ad Annecy", "translated_lang": "it"}

verifier("langue_seo : fiche française → fr", langue_seo(EV_FR) == "fr")
verifier("langue_seo : translated_lang='it' fait foi → it", langue_seo(EV_IT) == "it")

cl = _FauxClient()
r = optimize_seo(EV_FR, cl, "modele-factice")
verifier("FR : le prompt demande le français", "en français" in cl.prompts[-1], cl.prompts[-1][-300:])
verifier("FR : seo_lang='fr' dans le résultat", r and r.get("seo_lang") == "fr")

r = optimize_seo(EV_IT, cl, "modele-factice")
verifier("IT : le prompt demande l'italien", "en italien" in cl.prompts[-1], cl.prompts[-1][-300:])
verifier("IT : le prompt ne demande PLUS le français", "en français" not in cl.prompts[-1])
verifier("IT : seo_lang='it' dans le résultat", r and r.get("seo_lang") == "it")

r = optimize_seo(EV_FR, cl, "modele-factice", lang="it")
verifier("lang explicite l'emporte sur la fiche", "en italien" in cl.prompts[-1] and r["seo_lang"] == "it")

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
