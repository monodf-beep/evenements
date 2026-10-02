#!/usr/bin/env python3
"""Fixture : une traduction tronquée (max_tokens) est retentée UNE FOIS avec un
budget plus large avant d'abandonner — au lieu de redevenir un cul-de-sac
silencieux qui échoue pour la même raison technique chaque jour.

Incident réel du 2026-08-05 (VPS, en production) : la fiche 4161 (« Le avventure
di Pinocchio ») échouait deux jours de suite pour exactement le même motif
(max_tokens), avec une description de 1213 caractères seulement — bien sous la
limite de 2000 imposée à l'entrée. Le titre source déjà en italien gonflait
probablement la sortie attendue au-delà des 4000 tokens d'alors. Sans second
essai, aucune fiche dans ce cas ne pouvait jamais aboutir : elle se
resélectionne (translated_at reste vide, c'est voulu) et retombe sur le même mur.

⚠️ Aucun réseau : client.messages.create est un faux objet qui renvoie des
réponses scriptées.

Lancer : .venv/bin/python -m tests.test_translate_retry_tokens
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.translate_events as te  # noqa: E402


class _Bloc:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Reponse:
    def __init__(self, stop_reason, texte_json=""):
        self.stop_reason = stop_reason
        self.content = [_Bloc(texte_json)] if texte_json else []


class _ClientScripte:
    """Renvoie les réponses de `script`, dans l'ordre, un appel = une réponse."""
    def __init__(self, script):
        self.script = list(script)
        self.appels = []

    class _Messages:
        def __init__(self, parent):
            self._p = parent

        def create(self, **kw):
            self._p.appels.append(kw.get("max_tokens"))
            return self._p.script.pop(0)

    @property
    def messages(self):
        return self._Messages(self)


echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


ok_json = json.dumps({"title": "Le avventure di Pinocchio", "description": "Une belle histoire."})

print("──── premier essai tronqué, second réussit avec un budget plus large ────")
client = _ClientScripte([
    _Reponse("max_tokens"),           # 1er essai (4000) : tronqué
    _Reponse("end_turn", ok_json),    # 2e essai (7000) : réussit
])
res = te.translate_title_desc(client, "modele-test", "Le avventure di Pinocchio",
                              "Une belle histoire.", "it")
_check("résultat obtenu au 2e essai", res == {"title": "Le avventure di Pinocchio",
                                              "description": "Une belle histoire."}, str(res))
_check("budgets essayés : 4000 puis 7000", client.appels == [4000, 7000], str(client.appels))

print("\n──── premier essai réussit directement : pas de second appel ────")
client2 = _ClientScripte([_Reponse("end_turn", ok_json)])
res2 = te.translate_title_desc(client2, "modele-test", "Titre", "Desc", "fr")
_check("résultat obtenu au 1er essai", res2 is not None)
_check("un seul appel effectué (pas de retry inutile)", client2.appels == [4000], str(client2.appels))

print("\n──── les DEUX essais tronquent : abandon propre, pas de 3e appel ────")
client3 = _ClientScripte([_Reponse("max_tokens"), _Reponse("max_tokens")])
res3 = te.translate_title_desc(client3, "modele-test", "Titre", "Desc", "fr")
_check("None renvoyé (abandon pour aujourd'hui)", res3 is None)
_check("exactement deux essais, jamais un troisième", client3.appels == [4000, 7000], str(client3.appels))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
