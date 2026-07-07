#!/usr/bin/env python3
"""Porte QUALITÉ : un événement est-il COMPLET (prêt pour le brouillon WordPress) ?

Règle éditoriale (validée avec Franck) : un événement ne part sur Agenda Sabauda
QUE s'il a TOUS ses champs obligatoires. Sinon il RESTE dans le dashboard, où
l'agent d'auto-complétion (scripts/autocomplete.py) va scraper / chercher pour le
compléter, puis renvoyer un signal « bon » (on pousse) ou « pas bon » (on informe
Franck via Slack).

Un seul endroit définit « complet » — importé par le dashboard (liste « À
compléter »), la publication en lot (garde-fou) et l'agent d'auto-complétion.
Aucune dépendance externe : pur calcul sur une ligne events_raw.
"""
from __future__ import annotations

# Champs OBLIGATOIRES (clé DB → libellé lisible pour le dashboard). Ordre = ordre
# d'affichage. « tout » selon Franck : date + lieu + ville + territoire + catégorie
# + image. L'image a un filet de sécurité (bannière territoire, cf. visuals.py) donc
# elle est toujours *remplissable* — mais on la veut PERTINENTE (cf. images_web.py).
MANDATORY: list[tuple[str, str]] = [
    ("date_event_start", "Date"),
    ("lieu",             "Lieu"),
    ("ville",            "Ville"),
    ("territoire",       "Territoire"),
    ("llm_categorie",    "Catégorie"),
    ("url_image",        "Image"),
]

# Statuts « retenus » : les seuls concernés par la porte qualité (le reste — rejeté,
# fusionné, en attente d'évaluation — n'a pas vocation à partir sur l'agenda).
RETAINED_STATUTS = ("evaluated", "published_cs", "published_sub")


def _empty(value) -> bool:
    return not str(value if value is not None else "").strip()


def missing_fields(event: dict) -> list[tuple[str, str]]:
    """Liste des (clé, libellé) obligatoires ENCORE vides pour cet événement."""
    return [(key, label) for key, label in MANDATORY if _empty(event.get(key))]


def missing_labels(event: dict) -> list[str]:
    """Juste les libellés manquants (pour un badge « manque : Lieu, Image »)."""
    return [label for _key, label in missing_fields(event)]


def is_complete(event: dict) -> bool:
    """True si TOUS les champs obligatoires sont remplis."""
    return not missing_fields(event)


def has_real_image(event: dict) -> bool:
    """True si l'image N'EST PAS la bannière de repli (donc une vraie photo du sujet).

    Sert à l'agent d'auto-complétion : une bannière territoire remplit l'obligation
    « image » mais reste générique — on préfère la remplacer par une photo vérifiée
    (og:image, Commons, ou recherche web) quand c'est possible.
    """
    if _empty(event.get("url_image")):
        return False
    return (event.get("image_source") or "") != "banner"


def completeness(event: dict) -> dict:
    """Vue complète pour le dashboard : {complete, missing, missing_labels, is_banner}."""
    miss = missing_fields(event)
    return {
        "complete":       not miss,
        "missing":        miss,
        "missing_labels": [label for _k, label in miss],
        "is_banner":      (event.get("image_source") or "") == "banner"
                          and not _empty(event.get("url_image")),
    }
