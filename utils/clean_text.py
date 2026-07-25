#!/usr/bin/env python3
"""Nettoyage déterministe des DESCRIPTIONS scrappées : retire les artefacts de
page-builder et les pieds de flux RSS qui polluent les fiches (mais GARDE les faits :
horaires, tarifs, dates). Appliqué à l'ingestion (scraper) et avant l'enrichissement.

Familles d'artefacts visées (constatées en prod) :
- Directives Elementor : « Spacer Y –> Altezza = 6 = 24px ».
- Pied de flux RSS multilingue : « The post … appeared first on … » /
  « L'articolo … è apparso su / proviene da … » / « Cet article … est apparu en premier sur … ».
- Libellés d'interface isolés : « Action Link/Pulsante », « Vai alle Impostazioni »,
  « Prenota Subito », « Book now »…
"""
from __future__ import annotations
import re

_FOOTER_MARK = re.compile(r"(?is)(the post|l'?articolo|cet article)\b")
_FOOTER_VERB = re.compile(r"(?i)appeared first on|è apparso|proviene da|apparu en premier sur")

# « Spacer Y –> Altezza = 6 = 24px » et variantes (tirets/flèches divers, casse libre).
_SPACER = re.compile(r"(?i)spacer\s*y\s*[–\-—>\s]*altezza\s*=\s*\d+\s*=\s*\d+\s*px")

# Libellés d'UI récurrents (boutons/nav) — retirés seulement en tant que fragments isolés.
_UI_BITS = re.compile(
    r"(?i)\b(action\s*link\s*/?\s*pulsante|vai alle impostazioni|"
    r"prenota subito|prenota ora|book now|réserver maintenant|scopri di più)\b")


def strip_boilerplate(text: str) -> str:
    """Retire les artefacts de scraping d'une description, en préservant les faits."""
    if not text:
        return text
    t = text
    # Pied RSS : on coupe à partir du DERNIER « The post / L'articolo / Cet article »
    # SUIVI d'un verbe de pied (« appeared first on », « proviene da »…) → évite de
    # tronquer un « l'articolo 5 » légitime en début de texte.
    cut = None
    for m in _FOOTER_MARK.finditer(t):
        if _FOOTER_VERB.search(t[m.start():m.start() + 400]):
            cut = m.start()
    if cut is not None:
        t = t[:cut]
    t = _SPACER.sub(" ", t)
    t = _UI_BITS.sub(" ", t)
    # Normalisation des blancs (sans écraser les sauts de paragraphe utiles).
    t = re.sub(r"[ \t ]{2,}", " ", t)
    t = re.sub(r"\n[ \t]*\n\s*", "\n\n", t)
    return t.strip()
