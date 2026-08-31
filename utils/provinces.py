#!/usr/bin/env python3
"""Le territoire éditorial n'est pas assez fin pour voir les manques de SOURCES.

D'OÙ ÇA VIENT — Franck, 2026-08-31 : « ce serait bien de trier les sources par province,
comme ça ça nous permet de voir les manques. » Deux des quatre territoires sont eux-mêmes
des agrégats administratifs : « Savoie » fusionne Savoie (73) et Haute-Savoie (74) ;
« Piemonte » fusionne les huit provinces du Piémont. La Vallée d'Aoste et le Comté de
Nice sont chacun une seule province — rien à découper.

C'est exactement le défaut mesuré le 18/08 (audit_deplacement, GAP « intentions de
recherche ») : Torino sur-couverte, six autres provinces piémontaises à 0-1 événement,
invisible tant que le compteur reste au niveau « Piemonte ».

MÉTHODE DE RÉSOLUTION, dans l'ordre :
  1. la VILLE de la source (config/sources.txt colonne 6, ou territoire du newsletter
     s'il porte une ville identifiable dans son nom) — comparée à un registre de
     communes connues (config/provinces_savoie.json, config/provinces_piemonte.json),
     même normalisation que config/communes_comte_de_nice.json ;
  2. à défaut, le NOM de la source — une source régionale sans ville dédiée
     (« VisitPiemonte DMO », « Piemonte dal Vivo ») n'a À JUSTE TITRE aucune province :
     on ne force JAMAIS une classification sur une source qui couvre toute la région,
     ce serait fabriquer un chiffre faux (règle 6 — ne jamais inventer un dénominateur).

Renvoie `None` quand rien ne permet de trancher : un manque de connaissance affiché
comme tel vaut mieux qu'une province inventée."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Provinces à un seul membre — la Vallée d'Aoste EST une province (pas de sous-division
# administrative), le Comté de Nice n'est qu'un seul arrondissement. Rien à découper.
_TERRITOIRES_UNIPROVINCE = {
    "vallee-aoste": "Vallée d'Aoste",
    "nice": "Comté de Nice",
}


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _charger(nom_fichier: str) -> dict[str, str]:
    """commune normalisée → province, à partir d'un config/provinces_*.json."""
    chemin = ROOT / "config" / nom_fichier
    if not chemin.exists():
        return {}
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    table = {}
    for province, communes in brut.items():
        if province.startswith("_"):
            continue
        for commune in communes:
            table[_norm(commune)] = province
    return table


_TABLES = {
    "savoie": _charger("provinces_savoie.json"),
    "piemonte": _charger("provinces_piemonte.json"),
}


def province_de(territoire: str, ville: str = "", nom: str = "") -> str | None:
    """La province d'une source/newsletter, ou None si indéterminable.

    `territoire` : la valeur canonique de config/sources.txt (Savoie|Piemonte|
    Vallee-Aoste|Nice — comparé insensible à la casse/accents).
    `ville` : colonne dédiée si présente (source de vérité) ;
    `nom` : nom de la source, sondé en repli (« Reggia di Venaria » → Venaria Reale
    n'est PAS le nom, donc ça échoue ; « Comune di Cossato » → Cossato, ça marche).
    """
    t = _norm(territoire)
    for prefixe, label in _TERRITOIRES_UNIPROVINCE.items():
        if t.startswith(prefixe.replace("-", " ")) or prefixe in t:
            return label
    table = _TABLES.get("savoie") if "savoie" in t else (
        _TABLES.get("piemonte") if "piemont" in t else None)
    if table is None:
        return None
    if ville and _norm(ville) in table:
        return table[_norm(ville)]
    # Repli sur le nom : on cherche une commune CONNUE comme sous-chaîne du nom
    # normalisé, la plus LONGUE d'abord (« Casale Monferrato » avant « Casale » s'il
    # existait un doublon) pour ne pas se faire piéger par un préfixe trop court.
    n = _norm(nom)
    if n:
        for commune in sorted(table, key=len, reverse=True):
            if commune and re.search(rf"\b{re.escape(commune)}\b", n):
                return table[commune]
    return None
