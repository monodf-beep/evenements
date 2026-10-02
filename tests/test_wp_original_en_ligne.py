#!/usr/bin/env python3
"""Fixture : wp_original_est_en_ligne() ne dit jamais "oui" par erreur.

Aucun réseau réel : requests.get est monkey-patché. Fonction pure, aucune base.

POURQUOI (incident WP#7286, 2026-08-06). WP#6355 (français) était à la corbeille
depuis deux jours, en attente d'une décision, quand le run automatique du matin a
publié WP#7286, son jumeau italien — un original absent avec une traduction bien
visible. Cette fonction est le garde posé devant translate_events.py pour que ça ne
se reproduise pas : elle doit répondre False sur TOUT ce qui n'est pas un "publish"
confirmé, y compris les pannes, pour que le portillon retienne plutôt que laisse
passer par défaut (même asymétrie que les autres portillons de cette session).

Lancer : .venv/bin/python -m tests.test_wp_original_en_ligne
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["WP_AS_URL"] = "https://agendasabauda.example"
os.environ["WP_AS_USER"] = "agenda-bot"
os.environ["WP_AS_APP_PASSWORD"] = "xxxx"

import requests
import scripts.publisher_as as pub  # noqa: E402


class FausseReponse:
    def __init__(self, code, corps):
        self.status_code = code
        self._corps = corps

    def json(self):
        return self._corps


def reponse_fixe(code, corps):
    def _get(*a, **k):
        return FausseReponse(code, corps)
    return _get


def leve_erreur_reseau(*a, **k):
    raise requests.RequestException("panne simulee")


echecs = 0


def verifier(libelle, condition, detail=""):
    global echecs
    if condition:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f"\n      {detail}" if detail else ""))


print("──── cas nominal ────")
pub.requests.get = reponse_fixe(200, {"id": 6355, "status": "publish"})
verifier("publish confirmé -> True", pub.wp_original_est_en_ligne(6355) is True)

print("\n──── l'incident lui-même ────")
pub.requests.get = reponse_fixe(200, {"id": 6355, "status": "trash"})
verifier("statut trash -> False", pub.wp_original_est_en_ligne(6355) is False)

print("\n──── incertitude = False, jamais d'exception ────")
pub.requests.get = reponse_fixe(404, {})
verifier("404 -> False", pub.wp_original_est_en_ligne(6355) is False)

pub.requests.get = reponse_fixe(200, {"status": "draft"})
verifier("statut inattendu (draft) -> False", pub.wp_original_est_en_ligne(6355) is False)

pub.requests.get = leve_erreur_reseau
verifier("panne réseau -> False, pas d'exception", pub.wp_original_est_en_ligne(6355) is False)

print("\n──── entrées dégénérées ────")
verifier("id vide -> False sans appel réseau", pub.wp_original_est_en_ligne(None) is False)
verifier("id zéro -> False sans appel réseau", pub.wp_original_est_en_ligne(0) is False)

os.environ["WP_AS_URL"] = ""
verifier("WP_AS_URL absente -> False", pub.wp_original_est_en_ligne(6355) is False)
os.environ["WP_AS_URL"] = "https://agendasabauda.example"

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
