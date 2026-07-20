#!/usr/bin/env python3
"""Détecteur déterministe « ce n'est PAS un événement » — un article de presse.

Le site est un AGENDA : on ne veut que des sorties datées auxquelles le public peut
ASSISTER (concert, expo, sagra, marché, fête…). Or des sources de presse (Le Dauphiné,
La Stampa…) publient aussi des ARTICLES autour d'un événement — logistique (« où se
garer »), portraits (« ces X qui… »), comptes-rendus institutionnels (« le conseil s'est
réuni »). Le LLM d'évaluation s'accroche au gros mot-clé (« Tour de France ») et les note
haut à tort ; ensuite ils sont publiés, puis traduits → doublon de non-événements.

Ce filtre est un GARDE-FOU haute précision : il ne signale QUE des tournures quasi
certaines de presse/logistique/institutionnel, jamais un vrai événement. En cas de doute
il renvoie None (on laisse le LLM juger). Aucune dépendance, déterministe, gratuit.
"""
from __future__ import annotations

import re

# Motifs quasi certains de NON-événement (presse / logistique / institutionnel). Chacun
# est volontairement étroit pour ne pas attraper un vrai événement. Testé sur les cas
# réels : attrape « où circuler et stationner », « meilleurs spots pour assister »,
# « s'est réuni », « caravane publicitaire » ; laisse passer « voici le programme de la
# fête nationale », « Reconstitution historique », « Un salon de peinture »…
_NON_EVENT = [
    (re.compile(r"o[uù]\s+(?:circuler|se\s+garer|stationner|se\s+rendre)", re.I),
     "logistique (où circuler / se garer)"),
    (re.compile(r"\b(?:o[uù]|comment)\s+(?:se\s+garer|stationner)\b", re.I),
     "logistique (stationnement)"),
    (re.compile(r"\bplan\s+de\s+circulation\b|\binfos?\s+trafic\b"
                r"|\bfermetures?\s+de\s+routes?\b|\bd[ée]viations?\b"
                r"|\barr[êe]t[ée]s?\s+de\s+circulation\b", re.I),
     "voirie / mobilité"),
    (re.compile(r"meilleur\w*\s+(?:spots?|endroits?|coins?|places?|points?)\s+pour", re.I),
     "article « meilleurs endroits pour… »"),
    (re.compile(r"\bcaravane\s+publicitaire\b", re.I),
     "logistique Tour de France (caravane)"),
    (re.compile(r"s['’]est\s+r[ée]uni", re.I),
     "compte-rendu institutionnel (réunion)"),
    (re.compile(r"\bconseil\s+(?:municipal|d[ée]partemental|communautaire|m[ée]tropolitain)\b"
                r".{0,40}\b(?:vote|voté|budget|d[ée]lib[ée]r|subvention|s[ée]ance)", re.I),
     "compte-rendu institutionnel (conseil)"),
]


def non_event_reason(title: str = "", description: str = "") -> str | None:
    """Renvoie une raison courte si (title+description) ressemble à un ARTICLE de presse
    plutôt qu'à un événement ; None si rien de certain (→ on laisse le LLM juger)."""
    text = f"{title or ''} — {description or ''}"
    for rx, reason in _NON_EVENT:
        if rx.search(text):
            return reason
    return None


def looks_like_news_article(title: str = "", description: str = "") -> bool:
    return non_event_reason(title, description) is not None
