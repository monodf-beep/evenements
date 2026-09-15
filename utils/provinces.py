#!/usr/bin/env python3
"""Le territoire éditorial n'est pas assez fin pour voir les manques de SOURCES.

D'OÙ ÇA VIENT — Franck, 2026-08-31 : « ce serait bien de trier les sources par province,
comme ça ça nous permet de voir les manques. » Deux des quatre territoires sont eux-mêmes
des agrégats : « Savoie » fusionne la Savoie (73) et la Haute-Savoie (74) ; « Piemonte »
fusionne les huit provinces du Piémont. La Vallée d'Aoste et le Comté de Nice sont chacun
une seule province — rien à découper.

C'est le défaut mesuré le 18/08 (audit_deplacement, GAP « intentions de recherche ») :
Torino sur-couverte, six autres provinces piémontaises à 0-1 événement, invisible tant que
le compteur reste au niveau « Piemonte ».

⚠️ CORRIGÉ LE JOUR MÊME DE SA CRÉATION (audit de simplification du 31/08). La première
version de ce module chargeait DEUX fichiers de communes écrits à la main
(`provinces_savoie.json`, 45 entrées) — à côté de `config/communes_savoie_dept.json`, qui
en portait déjà **552** avec leur département depuis le 24/08. Les deux copies avaient
divergé le jour même : dix « communes » de ma liste n'existaient pas dans l'autre, et pour
cause — Val Thorens et Les Menuires sont des stations de Saint-Martin-de-Belleville,
Cran-Gevrier et Annecy-le-Vieux ont fusionné dans Annecy en 2017. C'est mot pour mot
l'incident « Venise des Alpes » (cinq copies, aucune ne disant laquelle fait foi), rejoué
en une heure. Ce module LIT donc désormais les registres existants et n'en recopie aucun.

MÉTHODE DE RÉSOLUTION, dans l'ordre :
  1. la VILLE de la source (colonne dédiée de `config/sources.txt`) ;
  2. à défaut, une commune reconnue dans son NOM.
Une source vraiment régionale (« VisitPiemonte DMO », « Piemonte dal Vivo ») n'a À JUSTE
TITRE aucune province : on ne force JAMAIS une classification, ce serait fabriquer un
chiffre faux. `None` est une réponse, pas un échec."""
from __future__ import annotations

import json
from pathlib import Path

from utils.lieux import _ALIAS, plie  # LA normalisation du dépôt — pas une deuxième

ROOT = Path(__file__).resolve().parent.parent

# Provinces à un seul membre — la Vallée d'Aoste EST une province (pas de sous-division),
# le Comté de Nice n'est qu'un arrondissement. Rien à découper.
_TERRITOIRES_UNIPROVINCE = {
    "vallee aoste": "Vallée d'Aoste",
    "nice": "Comté de Nice",
}

# Le département fait la province, côté français. Deux lignes au lieu d'un second registre.
_DEPT_VERS_PROVINCE = {"73": "Savoie", "74": "Haute-Savoie"}


def _charge(nom: str):
    chemin = ROOT / "config" / nom
    if not chemin.exists():
        return {}
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def _table_savoie() -> dict[str, str]:
    """commune pliée → « Savoie » | « Haute-Savoie », depuis le registre des 552.

    Aucune liste écrite ici : `config/communes_savoie_dept.json` fait foi, et il est déjà
    celui que lit `utils.lieux.communes()`."""
    brut = _charge("communes_savoie_dept.json")
    return {plie(k): _DEPT_VERS_PROVINCE[v] for k, v in brut.items()
            if not k.startswith("_") and v in _DEPT_VERS_PROVINCE}


def _table_piemonte() -> dict[str, str]:
    """commune pliée → province piémontaise.

    Celle-ci, il FAUT l'écrire : `config/communes_italiennes.json` liste les communes du
    Piémont mais ne dit pas de quelle province chacune relève — c'est une information
    neuve, pas une recopie. `config/provinces_piemonte.json` ne porte donc QUE ça, et
    `tests/test_provinces.py` vérifie qu'il ne contredit pas le registre des communes."""
    brut = _charge("provinces_piemonte.json")
    table = {}
    for province, communes in brut.items():
        if province.startswith("_"):
            continue
        for commune in communes:
            table[plie(commune)] = province
    return table


def _avec_alias(table: dict[str, str]) -> dict[str, str]:
    """Ajoute les formes COURANTES connues du dépôt (utils.lieux._ALIAS).

    Le registre porte les noms LÉGAUX (« Chamonix-Mont-Blanc ») ; les sources écrivent la
    forme d'usage (« Chamonix »). Sans ce repli, brancher sur le registre officiel ferait
    PERDRE des communes que la liste écrite à la main connaissait — un progrès qui régresse
    n'en est pas un. Les alias vivent dans `utils.lieux`, pas ici : une seule table."""
    for alias, officiel in _ALIAS.items():
        if officiel in table and alias not in table:
            table[alias] = table[officiel]
    return table


_TABLES = {"savoie": _avec_alias(_table_savoie()),
           "piemonte": _avec_alias(_table_piemonte())}

# Le nom du DÉPARTEMENT employé comme nom de source (« Département de la Haute-Savoie »)
# doit se reconnaître, alors que ce n'est pas une commune et qu'il n'a donc rien à faire
# dans le registre. « Savoie » seul est volontairement ABSENT : il désigne aussi bien
# l'agence commune aux deux départements (« Savoie Mont Blanc »), et le reconnaître
# classerait à tort une source régionale.
_ALIAS_NOM = {"haute savoie": "Haute-Savoie"}


def provinces_savoie() -> tuple[str, ...]:
    """Les provinces du versant français, déduites du département — pas une liste écrite.

    Sert au dénominateur de `scripts.audit_sources_provinces` : sans lui, il recopierait
    ces noms une troisième fois."""
    return tuple(_DEPT_VERS_PROVINCE[k] for k in sorted(_DEPT_VERS_PROVINCE))


def province_de(territoire: str, ville: str = "", nom: str = "") -> str | None:
    """La province d'une source/newsletter, ou None si indéterminable.

    `territoire` : valeur canonique de config/sources.txt (Savoie | Piemonte |
    Vallee-Aoste | Nice). `ville` : la colonne dédiée, qui fait foi. `nom` : sondé en
    repli, à la recherche d'une commune connue."""
    t = plie(territoire)
    for prefixe, label in _TERRITOIRES_UNIPROVINCE.items():
        if prefixe in t:
            return label
    table = (_TABLES["savoie"] if "savoie" in t
             else _TABLES["piemonte"] if "piemont" in t else None)
    if table is None:
        return None
    if ville and plie(ville) in table:
        return table[plie(ville)]
    n = f" {plie(nom)} "
    if not n.strip():
        return None
    for alias, province in _ALIAS_NOM.items():
        if f" {alias} " in n:
            return province
    # La commune la PLUS LONGUE d'abord : « Casale Monferrato » avant « Casale », sinon un
    # préfixe court gagnerait au hasard de l'ordre du dictionnaire.
    for commune in sorted(table, key=len, reverse=True):
        if commune and f" {commune} " in n:
            return table[commune]
    return None
