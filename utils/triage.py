#!/usr/bin/env python3
"""TRIAGE des fiches « À compléter » qui bloquent.

Constat (validé avec Franck) : la file « À compléter » stagne parce qu'elle mélange
5 causes de blocage TRÈS différentes, dont 3 ont déjà une solution dans le back-office
— il suffit de l'appliquer :

  • date manquante + langage « permanent »  → case RÉCURRENT (date remplacée par une
    note renvoyant à la source). La fiche redevient complétable.
  • lieu/ville manquants + langage « itinérant » → case MULTI-LIEUX (festival diffus,
    programme sur plusieurs communes). Lieu/ville ne sont plus exigés.
  • source morte / périmé                    → REJETER (rien à sauver honnêtement).
  • ambiguïté / conflit dans la source        → un humain tranche.

Ce module NE complète rien tout seul et n'invente aucune donnée : il DÉTECTE la
catégorie probable à partir du texte, pour proposer la bonne action en 1 clic. La
détection du lien mort (test HTTP) est faite ailleurs (elle demande le réseau).

Pur calcul sur une ligne events_raw + utils.completeness → testable sans base.
"""
from __future__ import annotations

import unicodedata

from utils import completeness as comp

# Libellés lisibles par clé obligatoire (repris de completeness.MANDATORY).
_LABEL = dict(comp.MANDATORY)

# Indices « activité permanente / récurrente » (FR + IT), sans accents, en minuscules.
RECURRING_HINTS = (
    "toute l annee", "toute lannee", "a l annee", "toute la saison", "toute la journee",
    "en permanence", "permanent", "permanente", "en continu", "en continu",
    "tous les jours", "chaque jour", "ouvert tous les jours", "7j/7", "7 j sur 7",
    "sur reservation", "sur rendez-vous", "sur rdv", "visite libre", "visites guidees",
    "exposition permanente", "collection permanente", "toute l anno",
    # Italien
    "tutto l anno", "tutti i giorni", "su prenotazione", "sempre aperto",
    "ingresso libero tutti", "aperto tutto",
)

# Indices « itinérant / multi-lieux » (FR + IT).
MULTI_HINTS = (
    "itinerant", "itinerante", "plusieurs communes", "plusieurs lieux",
    "plusieurs villes", "plusieurs sites", "divers lieux", "differents lieux",
    "en plusieurs lieux", "dans plusieurs", "un peu partout", "multi-sites",
    "multisite", "hors les murs", "dans toute la vallee", "dans toute la ville",
    "sur tout le territoire", "de village en village", "plusieurs villages",
    # Italien
    "vari luoghi", "diverse localita", "in tutta la valle", "piu comuni",
    "diversi comuni", "itinerante tra",
)


def _norm(text: str) -> str:
    """Minuscule + sans accents (comparaison robuste des indices)."""
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _text(event: dict) -> str:
    return _norm(f"{event.get('title', '')} {event.get('description', '')}")


def _has(text: str, hints) -> bool:
    return any(h in text for h in hints)


def classify(event: dict) -> dict:
    """Analyse une fiche incomplète et propose des relaxations éditoriales.

    Renvoie un dict prêt pour le template :
      missing            libellés obligatoires encore vides
      suggest_recurring  la date manque ET le texte parle de permanence
      suggest_multi      lieu/ville manquent ET le texte parle d'itinérance
      residual           libellés qui resteront manquants MÊME après les relaxations
                         (→ vraie donnée à trouver, ou fiche à rejeter)
      primary            'recurring' | 'multi_lieux' | 'both' | 'manual'
      resolved_by_flags  True si appliquer les cases suffit à compléter la fiche
    """
    missing = comp.missing_fields(event)
    keys = {k for k, _ in missing}
    text = _text(event)

    suggest_recurring = "date_event_start" in keys and _has(text, RECURRING_HINTS)
    suggest_multi = bool(keys & {"lieu", "ville"}) and _has(text, MULTI_HINTS)

    residual_keys = set(keys)
    if suggest_recurring:
        residual_keys.discard("date_event_start")
    if suggest_multi:
        residual_keys.discard("lieu")
        residual_keys.discard("ville")

    if suggest_recurring and suggest_multi:
        primary = "both"
    elif suggest_recurring:
        primary = "recurring"
    elif suggest_multi:
        primary = "multi_lieux"
    else:
        primary = "manual"

    return {
        "missing": [lbl for _k, lbl in missing],
        "suggest_recurring": suggest_recurring,
        "suggest_multi": suggest_multi,
        "residual": [_LABEL.get(k, k) for k in residual_keys],
        "primary": primary,
        "resolved_by_flags": (not residual_keys) and (suggest_recurring or suggest_multi),
    }
