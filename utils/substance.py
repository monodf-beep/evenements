# Mesure de la substance d'une fiche : combien de mots PROPRES le lecteur reçoit-il ?
"""Compte les mots de l'article réellement publié, gabarit exclu.

POURQUOI. Le 2026-08-05, AdSense a refusé agendasabauda.eu pour « contenu à faible
valeur informative ». La mesure a montré que le problème n'était pas la longueur des
pages — elles rendent 700 à 2300 mots — mais la part PROPRE dans ce total : environ
250 mots à elle pour 1100 mots rendus sur la fiche médiane, le reste étant une
charpente identique sur 257 fiches. Et 59 fiches publiées portaient moins de cent mots
à elles.

CE QU'ON COMPTE, ET POURQUOI CE TEXTE-LÀ. On appelle `build_post()`, la fonction qui
produit le contenu envoyé à WordPress, et on compte ses mots après retrait des balises.
Compter la colonne `description` serait plus simple mais mesurerait la matière d'entrée,
pas ce que le lecteur reçoit : une fiche à la description longue mais dont l'agent n'a
rien tiré passerait le contrôle. `build_post` est pure (elle lit le dictionnaire et
retourne deux chaînes), donc l'appeler dans un portillon ne coûte ni appel réseau ni
écriture.

CE QU'ON NE COMPTE PAS. Ni le titre, ni le bloc pratique (Quand/Où/Tarif), ni le
programme en liste : ce sont des faits structurés, présents partout, et les additionner
donnerait un score que même une fiche vide atteindrait.
"""
from __future__ import annotations

import html
import re

# Plancher par défaut. En dessous, une fiche n'apporte rien qu'un annuaire ne donne
# déjà : elle coûte une URL indexable au site et n'offre rien au lecteur. Ce n'est PAS
# un objectif de qualité — 120 mots reste maigre — mais un plancher de décence, choisi
# pour arrêter l'indéfendable sans bloquer la moitié du flux. Réglable par
# PUBLISH_MIN_MOTS pour pouvoir le remonter au fur et à mesure que le stock s'améliore.
MIN_MOTS_DEFAUT = 120

# Bande de surveillance : au-dessus du plancher, mais toujours maigre. On ne bloque pas,
# on COMPTE, pour que la traîne reste sous les yeux au lieu de dormir en base.
BANDE_MAIGRE = 250

_BALISES = re.compile(r"<[^>]+>")
_ESPACES = re.compile(r"\s+")


def mots_de(html_ou_texte: str) -> int:
    """Nombre de mots d'un fragment HTML ou texte brut."""
    if not html_ou_texte:
        return 0
    txt = html.unescape(_BALISES.sub(" ", str(html_ou_texte)))
    return len([m for m in _ESPACES.sub(" ", txt).strip().split(" ") if m])


def mots_publies(event: dict, build_post) -> int:
    """Mots de l'article tel qu'il partira en ligne. `build_post` est injectée pour
    garder ce module sans dépendance vers le publisher (et testable seul)."""
    try:
        _titre, contenu = build_post(event)
    except Exception:
        # Un événement mal formé ne doit pas faire tomber le lot : on le compte à zéro,
        # ce qui le fait retenir par le portillon — le comportement prudent.
        return 0
    return mots_de(contenu)


def plancher() -> int:
    import os
    try:
        v = int(os.getenv("PUBLISH_MIN_MOTS", "").strip() or MIN_MOTS_DEFAUT)
    except ValueError:
        return MIN_MOTS_DEFAUT
    return max(0, v)
