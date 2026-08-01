#!/usr/bin/env python3
"""Score « ÇA VAUT LE DÉPLACEMENT » (0-8) — DÉTERMINISTE, zéro appel LLM.

Contexte (décision Franck, 2026-08-01) : la section home « Ça vaut le déplacement »
triait chronologiquement (les 8 prochains événements, sans critère de qualité). On a
d'abord envisagé de trier sur `vmean` (note des personas VISITEURS) — mauvaise piste,
constatée sur les données réelles : `vmean` mesure la RICHESSE DE L'ARTICLE, pas
l'ampleur de l'événement (Musilac, 110 000 festivaliers, notait 1.0 pendant qu'une
petite exposition notait 3.0, simplement parce que son article était maigre).

On a ensuite envisagé de demander au persona de juger l'événement « au-delà de
l'article ». Abandonné aussi : un persona ne SAIT rien (c'est un texte de quelques
lignes), c'est le modèle qui mobiliserait ses connaissances d'entraînement — donc une
note invérifiable, exposée aux confusions de nom.

La bonne source existait déjà : `scripts/evaluator.py` note l'IMPORTANCE de chaque
événement sur 5 critères observables, stockés en base (`llm_score_detail`), CHACUN
avec sa phrase de justification. Deux de ces critères sont littéralement la définition
de « ça vaut le déplacement » :
  - `rayonnement`              : international / transfrontalier FR-IT = 2, régional = 1, local = 0
  - `specificite_territoriale` : identitaire, propre au territoire = 1, générique = 0

Avantages sur les pistes abandonnées : rétroactif (marche sur les fiches déjà publiées,
sans repasser enrich.py), auditable (on peut lire POURQUOI chaque point a été donné),
et sans risque d'hallucination.

`organisateur_moyens` est VOLONTAIREMENT exclu : le budget de l'organisateur n'entre pas
dans la décision d'un visiteur de faire trois heures de route.
"""
from __future__ import annotations
import json

# Critères retenus et leur poids. Somme des maxima = 8.
# Poids 1 partout : simple, explicable, et suffisant pour discriminer sur les données
# réelles (Musilac 7/8, Arte Povera Turin 7/8, « L'été au centre socioculturel » 1/8).
# À pondérer seulement si un cas concret le réclame — pas d'avance.
_CRITERES = ("notoriete_lieu", "edition_tradition", "rayonnement", "specificite_territoriale")
MAX_SCORE = 8


def deplacement_score(llm_score_detail) -> int | None:
    """Score 0-8 depuis `llm_score_detail` (JSON de scripts/evaluator.py), ou None si le
    détail est absent/illisible — None ≠ 0 : « pas mesuré » n'est pas « nul », la section
    doit écarter les non-mesurés, pas les classer derniers.

    Accepte une chaîne JSON ou un dict déjà décodé.
    """
    data = llm_score_detail
    if isinstance(data, str):
        try:
            data = json.loads(data or "{}")
        except (ValueError, TypeError):
            return None
    if not isinstance(data, dict) or not data:
        return None

    total = 0
    trouve = False
    for cle in _CRITERES:
        bloc = data.get(cle)
        pts = bloc.get("points") if isinstance(bloc, dict) else bloc
        if isinstance(pts, (int, float)):
            total += int(pts)
            trouve = True
    return total if trouve else None


def deplacement_raisons(llm_score_detail) -> list[str]:
    """Les justifications écrites par l'évaluateur, critère par critère — pour afficher
    au back-office POURQUOI un événement est (ou n'est pas) « à déplacement ». C'est ce
    qui rend le score auditable, contrairement à une note de persona."""
    data = llm_score_detail
    if isinstance(data, str):
        try:
            data = json.loads(data or "{}")
        except (ValueError, TypeError):
            return []
    if not isinstance(data, dict):
        return []
    out = []
    for cle in _CRITERES:
        bloc = data.get(cle)
        if isinstance(bloc, dict) and bloc.get("note"):
            out.append(f"{cle} ({bloc.get('points', '?')}) : {bloc['note']}")
    return out
