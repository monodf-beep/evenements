#!/usr/bin/env python3
"""Fixture : `_lien_public` — l'adresse enregistrée est celle que le SITE sert.

INCIDENT RÉEL, 2026-10-01. `cs-publish.php` répond `get_permalink()` avant que Polylang
ait posé la langue : une traduction italienne était enregistrée SANS `/it/`. Les audits
« traductions du mauvais versant » et « doublons en ligne » lisaient cette colonne et
se sont trompés chaque matin (7 faux positifs sur 7 vérifiés par numéro).

La fixture exige les deux sens (CLAUDE.md, règle 3) :
  - le lien REST l'emporte quand il a un préfixe que la réponse de création n'avait pas ;
  - mais une lecture ratée, ou une forme provisoire `?p=`, ne DOIT PAS écraser un repli
    correct — sinon le correctif ferait pire que le défaut.

Aucun réseau : requests.get est remplacé.
Lancer : .venv/bin/python -m tests.test_lien_public
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402
import scripts.publisher_as as pa  # noqa: E402

echecs = 0


def _check(nom, ok, detail=""):
    global echecs
    print(("  ok   " if ok else "  ECHEC"), nom, "" if ok else f"-> {detail}")
    if not ok:
        echecs += 1


class _R:
    def __init__(self, code, data):
        self.status_code, self._d = code, data

    def json(self):
        if isinstance(self._d, Exception):
            raise self._d
        return self._d


def _avec(reponse):
    def faux(*a, **k):
        if isinstance(reponse, requests.RequestException):
            raise reponse
        return reponse
    pa.requests.get = faux


W, A = "https://agendasabauda.eu", ("u", "p")
SANS = "https://agendasabauda.eu/evenement/doudou/"
AVEC = "https://agendasabauda.eu/it/evenement/doudou/"

_avec(_R(200, {"link": AVEC}))
_check("le lien du site (avec /it/) remplace celui de la création",
       pa._lien_public(W, 12498, A, SANS) == AVEC)

# Cas près de la frontière : ce qui NE DOIT PAS remplacer un repli correct.
_avec(_R(200, {"link": "https://agendasabauda.eu/?post_type=tribe_events&p=12498"}))
_check("une forme provisoire ?p= n'écrase pas le repli",
       pa._lien_public(W, 12498, A, SANS) == SANS)
_avec(_R(401, {"code": "rest_forbidden"}))
_check("un post non public (401) garde le repli", pa._lien_public(W, 1, A, SANS) == SANS)
_avec(requests.ConnectionError("réseau"))
_check("une panne réseau garde le repli", pa._lien_public(W, 1, A, SANS) == SANS)
_avec(_R(200, ValueError("pas du json")))
_check("une réponse illisible garde le repli", pa._lien_public(W, 1, A, SANS) == SANS)
_avec(_R(200, {}))
_check("une réponse sans `link` garde le repli", pa._lien_public(W, 1, A, SANS) == SANS)
_check("sans numéro de post, aucun appel et repli", pa._lien_public(W, None, A, SANS) == SANS)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
