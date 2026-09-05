#!/usr/bin/env python3
"""LE PLAFOND API N'EST PAS UNE ERREUR DE FICHE — c'est l'arrêt de toute la chaîne LLM.

L'INCIDENT QUI A TOUT MONTRÉ (2026-08-04, 15h33). Premier appel LLM de l'après-midi :
« Error 400 — You have reached your specified API usage limits. You will regain access on
2026-09-01 at 00:00 UTC. » Le plafond de dépense de l'organisation était atteint, à
28 jours de l'échéance. L'inventaire des gardes, fait dans l'heure, a donné :

  • `evaluator`    → s'arrête à la PREMIÈRE erreur, un seul avertissement : PROPRE ;
  • `daily_batch`  → hérite de la garde d'enrich, une seule alerte Slack : PROPRE ;
  • `translate`    → `except` À L'INTÉRIEUR de la boucle, `continue` : il MARTÈLE.
    Prouvé dans les journaux : 13 occurrences le 30/07, 15 le 31/07 — une par fiche
    tentée, jusqu'au bout du cap ;
  • `dates`, `venues`, `visuals` → AUCUNE garde : 313, 152 et 180 occurrences dans les
    journaux de juillet, les jours où le plafond avait déjà été atteint.

ET LE MARTÈLEMENT N'EST PAS QUE DU BRUIT, c'est là le vrai dégât : `llm_dates` et
`llm_venue` avalent l'exception (« jamais bloquant »), rendent `llm_none`, et la boucle
écrit ce verdict EN BASE avec un horodatage frais. Chaque fiche tentée un jour de plafond
est donc parquée pour `*_COOLDOWN_DAYS` (7 jours) — non pas parce que sa page ne dit rien,
mais parce que la carte bancaire a dit stop. Un problème de facturation se transforme en
faux verdict éditorial, indiscernable des vrais.

LA RÈGLE QUE CE MODULE PERMET D'APPLIQUER : un plafond atteint doit ARRÊTER le lot en
cours (les appels suivants échoueraient tous pareil), le DIRE une seule fois, et surtout
NE RIEN ÉCRIRE en base pour les fiches non tentées — elles n'ont rien fait, leur tour
reviendra quand le plafond sera levé. Franck le lève en deux clics dans la console
Anthropic ; c'est un réglage, pas une panne.

Détection VOLONTAIREMENT en canard (status_code + texte) plutôt que par isinstance sur
les classes du SDK anthropic : les appelants attrapent des exceptions déjà enveloppées de
plusieurs façons, le SDK évolue, et un test qui exige la vraie classe serait intestable
sur fixture — or c'est précisément le genre de garde qu'il faut pouvoir tester sans
brûler un appel réel.
"""
from __future__ import annotations

# Fragments qui signent un refus de QUOTA/PLAFOND, par opposition à une erreur de requête
# ordinaire (JSON malformé, modèle inconnu…) qui, elle, est bien une erreur de fiche.
_SIGNATURES = ("usage limits", "credit balance", "billing", "spending limit")


class PlafondAPI(Exception):
    """Levée par les helpers LLM quand l'API refuse pour PLAFOND — jamais pour une fiche.

    Les helpers de ce dépôt promettent « jamais bloquant » : c'est la bonne promesse pour
    une erreur de FICHE (page illisible, JSON cassé), et la mauvaise pour un plafond, qui
    condamne tous les appels suivants du lot. Cette exception est le seul cas où un helper
    a le droit de remonter — et la boucle appelante doit s'arrêter, pas la rattraper."""


def est_plafond(exc: BaseException) -> bool:
    """True si l'exception est un refus de plafond/quota API, quelle que soit sa classe."""
    if isinstance(exc, PlafondAPI):
        return True
    code = getattr(exc, "status_code", None)
    texte = str(exc).lower()
    # 400 « usage limits » (plafond configuré), 402 (facturation) ; le 429 classique de
    # débit N'EST PAS un plafond — il passe en quelques secondes et mérite le retry
    # normal, pas un arrêt de lot.
    if code in (400, 402) and any(sig in texte for sig in _SIGNATURES):
        return True
    return code is None and any(sig in texte for sig in _SIGNATURES)
