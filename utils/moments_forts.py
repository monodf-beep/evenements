"""Les étiquettes des moments forts : à quel événement-parapluie une fiche appartient.

POURQUOI. La strate « moment fort » et sa page dédiée doivent lister les fiches D'UN
événement, pas celles d'un week-end. Mesuré le 2026-09-22 sur le rendu réel : une
sélection par date + territoire ramenait BeerCult, le Biella Sport Festival et une
exposition Kusama dans une strate qui promet « patrimoine ».

CE MODULE NE DÉCIDE PAS DU TERRITOIRE. Il reçoit le slug déjà normalisé par
`scripts.publisher_as._map_territoire`, qui est le seul endroit du dépôt qui sache
lire « Piemonte », « Piémont » et « Piedmont » comme une même chose. Deux détecteurs
pour la même chose, un seul juste : c'est la faute de fond du 2026-09-08, quatre bugs
dont le garde-fou existait déjà dans le module voisin.

CE QUI SE PASSE QUAND RIEN NE CORRESPOND : une liste VIDE, qui est exactement ce que
`publisher_as` envoyait jusqu'ici. La route maison `cs/v1` fait alors
`wp_set_object_terms(..., array(), 'post_tag', false)`, donc elle NETTOIE les
étiquettes de la fiche. Ce comportement-là ne change pas — on ne fait qu'ajouter le
cas où une fiche en mérite une.
"""
from __future__ import annotations

import json
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "config" / "moments_forts.json"

_cache: dict | None = None


def charger(chemin: Path | str | None = None) -> list[dict]:
    """Les moments déclarés. Un fichier absent ou illisible ne casse pas la publication.

    Un moment fort est un confort éditorial ; une étiquette manquante se rattrape avec
    un `--update`. Une publication qui échoue, non.
    """
    global _cache
    if chemin is None and _cache is not None:
        return _cache
    p = Path(chemin) if chemin else CONFIG
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        moments = [m for m in data.get("moments", []) if m.get("etiquette")]
    except Exception:
        moments = []
    if chemin is None:
        _cache = moments
    return moments


def _dans_la_fenetre(debut_fiche: str, debut: str, fin: str) -> bool:
    """La fiche COMMENCE pendant le moment.

    Volontairement pas un chevauchement : une exposition ouverte depuis juin et encore
    visible le 26 septembre n'appartient pas aux journées du patrimoine. Un
    chevauchement l'aurait attrapée, et c'est précisément le bruit qu'on cherche à
    écarter.

    Une fiche sans date n'est jamais attrapée : c'est une donnée manquante, pas un
    événement hors période (règle 5 du CLAUDE.md).
    """
    d = (debut_fiche or "")[:10]
    if len(d) != 10:
        return False
    return debut <= d <= fin


def etiquettes(territoire_slug: str, date_event_start: str, source_name: str,
               lang: str = "fr", moments: list[dict] | None = None) -> list[str]:
    """Les étiquettes d'une fiche, dans la LANGUE de la fiche, ordre des moments déclarés.

    Toutes les conditions DÉCLARÉES doivent être satisfaites. Une condition absente
    n'est pas vérifiée : un moment sans `sources` s'appuie sur la seule paire
    territoire + dates, ce qui ne convient qu'à un moment qui occupe vraiment tout son
    territoire à ses dates.

    LA LANGUE COMPTE. `post_tag` est une taxonomie traduite par Polylang sur ce site
    (mesuré le 22/09 : six paires `-it` déjà en ligne). Envoyer le libellé français à
    une fiche italienne aurait fabriqué un terme au slug suffixé, introuvable par le
    mu-plugin. Un moment qui ne déclare pas la langue demandée ne pose rien : mieux
    vaut pas d'étiquette qu'une étiquette que personne n'interroge.
    """
    out = []
    for m in (moments if moments is not None else charger()):
        terrs = m.get("territoires") or []
        if terrs and (territoire_slug or "") not in terrs:
            continue
        if m.get("debut") and m.get("fin"):
            if not _dans_la_fenetre(date_event_start, m["debut"], m["fin"]):
                continue
        sources = m.get("sources") or []
        if sources and (source_name or "") not in sources:
            continue
        nom = m["etiquette"].get(lang) if isinstance(m["etiquette"], dict) else m["etiquette"]
        if nom and nom not in out:
            out.append(nom)
    return out


def slug(moment: dict, lang: str = "fr") -> str:
    """Le slug attendu côté WordPress, pour le mu-plugin et la page dédiée.

    Il est DÉCLARÉ, pas dérivé du nom : WordPress le dériverait bien de la même
    façon aujourd'hui, mais une dérivation silencieuse est exactement le genre de
    chose qui diverge sans prévenir.
    """
    s = moment.get("slug")
    if isinstance(s, dict):
        return s.get(lang, "")
    return s or ""
