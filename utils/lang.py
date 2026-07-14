#!/usr/bin/env python3
"""Détection de langue FR / IT d'un événement — pour Polylang (agendasabauda.eu bilingue).

Le site est bilingue : chaque événement doit porter SA langue (Polylang) pour que le
sélecteur de langue, les archives et les hreflang soient corrects. Beaucoup de sources
valdôtaines publient la MÊME info en français ET en italien → on ne peut pas se fier au
seul territoire, il faut lire le texte.

Heuristique déterministe (aucun LLM, aucune dépendance) : on compte des MOTS-OUTILS
DISTINCTIFS propres à chaque langue (on ignore ceux qui se ressemblent, « de/la/…»),
avec le territoire comme départage quand le texte ne tranche pas. Défaut : « fr »
(langue par défaut du site).
"""
from __future__ import annotations

import re

# Mots-outils/marqueurs qui TRANCHENT (présents dans une langue, absents/rares dans
# l'autre). Volontairement disjoints : on écarte « de », « la », « in »… (communs).
_FR = frozenset((
    "le", "les", "des", "une", "est", "été", "à", "au", "aux", "dans", "pour",
    "avec", "cette", "ce", "vous", "nous", "du", "sur", "par", "ses", "leur",
    "leurs", "plus", "très", "où", "déjà", "fête", "juillet", "août", "gratuit",
    "entrée", "jour", "tous", "toute", "aussi", "depuis", "jusqu", "chaque",
    "sans", "sous", "année", "spectacle", "exposition", "rencontre", "atelier",
    "et", "ou", "aux", "dès", "être", "fêtes", "journée", "soirée", "billet",
))
_IT = frozenset((
    "il", "lo", "gli", "della", "dello", "degli", "delle", "dei", "del", "una",
    "questa", "questo", "città", "più", "è", "né", "gratuito", "ingresso", "con",
    "per", "nella", "nel", "sono", "anche", "tra", "dal", "dalla", "estate",
    "luglio", "agosto", "ogni", "presso", "fino", "durante", "edizione",
    "spettacolo", "mostra", "serata", "giochi", "al", "allo", "alla", "che",
    "dell", "all", "sull", "dai", "dagli", "artista", "concerti", "gratuiti",
    "mercoledì", "sabato", "domenica", "giovedì",
))

# Territoire → langue probable quand le texte ne tranche pas. La Vallée d'Aoste est
# officiellement bilingue → neutre (on s'en remet alors au texte / au défaut).
_TERRITORY_LANG = {
    "piemonte": "it", "piemont": "it", "piedmont": "it",
    "savoie": "fr", "haute-savoie": "fr",
    "nice": "fr", "alpes-maritimes": "fr",
}


def _score(text: str) -> tuple[int, int]:
    """(score FR, score IT) : nombre de marqueurs distinctifs rencontrés."""
    toks = re.findall(r"\w+", (text or "").lower(), re.UNICODE)
    fr = sum(1 for t in toks if t in _FR)
    it = sum(1 for t in toks if t in _IT)
    return fr, it


def detect_lang(title: str = "", description: str = "", territoire: str = "") -> str:
    """Renvoie 'fr' ou 'it'. Décision par le TEXTE (marqueurs distinctifs) ; à égalité
    ou quasi-égalité, on départage par le TERRITOIRE ; à défaut 'fr' (langue du site)."""
    fr, it = _score(f"{title} {title} {description}")   # le titre compte double
    # Marge nette dans le texte → on tranche directement.
    if abs(fr - it) >= 2:
        return "it" if it > fr else "fr"
    # Texte indécis : le territoire départage (VdA neutre → non listé).
    terr = (territoire or "").strip().lower()
    for key, lang in _TERRITORY_LANG.items():
        if key in terr:
            return lang
    # Dernier recours : le léger avantage texte, sinon 'fr'.
    return "it" if it > fr else "fr"
