#!/usr/bin/env python3
"""Périmètre géographique — décision sur le champ `ville`.

RÈGLE (charte §2, arbitrage Franck du 2026-08-02) : le quatrième territoire est le
**Comté de Nice**, c'est-à-dire l'**arrondissement de Nice**, PAS le département des
Alpes-Maritimes. Les 62 communes de l'**arrondissement de Grasse** — Cannes, Antibes,
Grasse, Cagnes-sur-Mer, Vence, Saint-Paul-de-Vence, Mandelieu-la-Napoule,
Mouans-Sartoux, Saint-Laurent-du-Var… — sont **hors périmètre** : « on ne devrait pas
avoir d'événements sur ces territoires pour le moment ». Ce n'est pas « sans
étiquette », c'est « pas dans le catalogue ».

Ce module ne contient QUE l'adaptation au champ `ville` de la base. La liste des
communes et la comparaison exacte restent chez `utils.sources` (lecture de
`config/communes_comte_de_nice.json` : 101 communes pour Nice + 62 pour Grasse = 163,
le compte exact du département, donc listes complètes et disjointes).

Pourquoi un module à part : `scripts/purge_out_of_zone.py` se revendique « gratuit,
sans LLM » et `scripts/count_grasse.py` est en lecture seule ; leur faire importer
`scripts.evaluator` leur imposerait la dépendance `anthropic`. Trois appelants, une
seule définition.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.sources import est_arrondissement_grasse


def ville_hors_perimetre(ville: str) -> bool:
    """Vrai si la `ville` d'une fiche est une commune de l'ARRONDISSEMENT DE GRASSE.

    On délègue entièrement à `utils.sources.est_arrondissement_grasse()`. Seule
    tolérance ajoutée ici : `ville` arrive parfois sous la forme « Cannes, France »
    ou « Antibes (06) » selon la source (JSON-LD `addressLocality` ou extraction LLM,
    cf. scripts/venues.py) — on retente alors sur le premier segment.

    JAMAIS de recherche dans du texte libre : uniquement le champ `ville`, où la
    comparaison est exacte. Cherchés dans une description, ces noms produiraient des
    faux positifs (« Vence » ⊂ « Provence », « Grasse » ⊂ « grasse matinée »,
    « Cannes » ⊂ « cannes à pêche », « Biot » et « Opio » trop courts) — c'est
    exactement la mise en garde que porte `config/out_of_zone.txt`.

    Ville vide → False : on n'exclut jamais sur une absence d'information.

    FORMES ENRICHIES (corrigé le 2026-08-03) : la comparaison exigeait le nom EXACT,
    si bien que « Antibes Juan-les-Pins » (nom d'usage), « Cannes-la-Bocca » (quartier)
    et « Nice Cedex 1 » (mention postale) passaient tous les trois au travers.
    `utils.sources._cherche_commune()` essaie désormais le nom complet puis des
    préfixes de MOTS décroissants — jamais de sous-chaîne, pour ne pas confondre
    « Saint-Paul-de-Vence » avec « Vence », commune distincte qui y est contenue.
    Vérifié sur 16 formes réelles : 0 erreur.

    LIMITE RESTANTE : un homonyme lointain dont le nom commence comme une commune
    d'ici serait rattaché à tort — mais à l'arrondissement de Grasse, donc écarté, et
    il était de toute façon hors périmètre. L'erreur va dans le sens prudent. Le filet
    de sécurité pour tout le reste est l'ÉTAPE 0 du prompt de scripts/evaluator.py,
    qui juge sur le texte et connaît la liste des communes de Grasse.
    """
    ville = (ville or "").strip()
    if not ville:
        return False
    if est_arrondissement_grasse(ville):
        return True
    tete = re.split(r"[,(/]", ville, maxsplit=1)[0].strip()
    return bool(tete) and tete != ville and est_arrondissement_grasse(tete)
