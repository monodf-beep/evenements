#!/usr/bin/env python3
"""Lecture COMPLÈTE des données structurées d'une page — JSON-LD d'abord, microdata ensuite.

Franck, 2026-08-11 : « j'aimerais qu'on soit implacable au niveau automatisation de la
collecte des informations officielles AVANT de passer par les LLM pour interpréter ».

Ce que faisait le dépôt jusqu'ici tenait en deux expressions régulières :
`"startDate"\\s*:\\s*"(\\d{4}-\\d{2}-\\d{2})` et `<time datetime=`. C'est-à-dire qu'on
cherchait une chaîne de caractères dans du HTML, au lieu de LIRE le document que le site
publie précisément pour être lu par des machines. Tout ce qui s'écarte de cette forme
exacte était invisible :

  • un bloc `@graph` (la forme que produisent Yoast et Rank Math, donc l'immense majorité
    des sites WordPress — et une bonne part de nos sources) ;
  • un tableau de plusieurs objets dans un même `<script>` ;
  • des guillemets échappés (`\\"startDate\\"`), courants quand le JSON-LD est injecté
    par un builder de page ;
  • `startDate` niché dans un `subEvent` ou un `eventSchedule` ;
  • les microdata `itemprop="startDate"`, que schema.org autorise tout autant.

⚠️ ET SURTOUT, CE QUE J'AI AFFIRMÉ SANS LE PROUVER. Le premier diagnostic comptait la
présence d'un bloc `application/ld+json` sur 29 pages muettes, et j'en ai conclu devant
Franck que « ces pages décrivent l'organisation, pas l'événement, il n'y a pas de
gisement ». Or le marqueur que j'avais écrit ne testait PAS cela : il disait qu'un bloc
existait, jamais ce qu'il contenait. `types_presents()` répond à la vraie question.

Aucune dépendance : le dépôt n'embarque pas de parseur HTML, et en ajouter un pour ça
serait disproportionné. On isole les blocs par expression régulière — c'est le SEUL usage
légitime d'une regex ici — puis on parse le JSON avec le module standard.
"""
from __future__ import annotations

import json
import re

_BLOC = re.compile(
    r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S)

# Types schema.org qui décrivent un ÉVÉNEMENT. Liste large : schema.org en dérive une
# vingtaine, et une exposition peut être annoncée en « ExhibitionEvent » comme en
# « Event » tout court.
TYPES_EVENEMENT = frozenset((
    "event", "exhibitionevent", "musicevent", "theaterevent", "screeningevent",
    "festival", "socialevent", "educationevent", "foodevent", "danceevent",
    "literaryevent", "visualartsevent", "comedyevent", "sportsevent",
    "childrensevent", "businessevent", "courseinstance", "publicationevent",
))


def _charge(brut: str):
    """JSON d'un bloc, avec deux rattrapages courants. None si illisible."""
    txt = (brut or "").strip()
    if not txt:
        return None
    for tentative in (txt,
                      # Guillemets échappés : le bloc a été injecté dans une chaîne.
                      txt.replace('\\"', '"'),
                      # Commentaires HTML enveloppants (vieux thèmes).
                      txt.replace("<!--", "").replace("-->", "")):
        try:
            return json.loads(tentative)
        except (ValueError, TypeError):
            continue
    return None


def _aplatir(noeud, sortie: list) -> None:
    """Tous les dictionnaires de l'arbre, @graph et tableaux compris.

    On descend PARTOUT plutôt que de suivre les seuls chemins connus : un Event peut être
    dans `@graph`, dans `subEvent`, dans `about`, dans `mainEntity`… Énumérer ces chemins,
    c'est se condamner à en découvrir un nouveau chaque mois."""
    if isinstance(noeud, dict):
        sortie.append(noeud)
        for valeur in noeud.values():
            _aplatir(valeur, sortie)
    elif isinstance(noeud, list):
        for element in noeud:
            _aplatir(element, sortie)


def noeuds(html: str) -> list[dict]:
    """Tous les objets JSON-LD de la page, à plat."""
    out: list[dict] = []
    for brut in _BLOC.findall(html or ""):
        data = _charge(brut)
        if data is not None:
            _aplatir(data, out)
    return out


def _types(noeud: dict) -> list[str]:
    t = noeud.get("@type") or noeud.get("type") or []
    if isinstance(t, str):
        t = [t]
    return [str(x).strip().lower() for x in t if x]


def types_presents(html: str) -> list[str]:
    """Les @type réellement déclarés par la page — la question à laquelle le premier
    diagnostic ne répondait pas. Trié, sans doublon."""
    vus = set()
    for n in noeuds(html):
        vus.update(_types(n))
    return sorted(vus)


def evenements(html: str) -> list[dict]:
    """Les nœuds qui décrivent un événement."""
    return [n for n in noeuds(html) if any(t in TYPES_EVENEMENT for t in _types(n))]


def _texte(valeur) -> str:
    """Une valeur schema.org peut être une chaîne, un objet {name}, ou une liste."""
    if isinstance(valeur, str):
        return valeur.strip()
    if isinstance(valeur, dict):
        for cle in ("name", "@id", "url", "contentUrl"):
            v = valeur.get(cle)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""
    if isinstance(valeur, list):
        for v in valeur:
            t = _texte(v)
            if t:
                return t
    return ""


_ISO = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _date(valeur) -> str:
    m = _ISO.search(_texte(valeur))
    return m.group(1) if m else ""


def champs(html: str) -> dict:
    """Ce que la page déclare sur son événement : debut, fin, lieu, ville, image,
    description. Champs absents = clés absentes, jamais de valeur inventée.

    Quand plusieurs événements sont déclarés (page de programme), on prend le PREMIER qui
    porte une date : une page qui liste dix concerts n'est pas une fiche, et prendre la
    date d'un autre est précisément l'accident de WP#6798. En cas de doute, on préfère
    ne rien rendre — c'est le sens du « implacable » : implacable à COLLECTER ce qui est
    déclaré, pas à deviner ce qui ne l'est pas."""
    evts = evenements(html)
    if not evts:
        return {}
    # Un même événement est souvent décrit deux fois (Yoast + le thème) : on ne compte
    # comme « plusieurs événements » que des noms distincts.
    noms = {(_texte(e.get("name")) or "").lower() for e in evts}
    noms.discard("")
    avec_date = [e for e in evts if _date(e.get("startDate"))]
    if len(noms) > 1 and len(avec_date) > 1:
        return {}          # page de programme : ambigu, on ne prend rien
    src = avec_date[0] if avec_date else evts[0]

    out: dict = {}
    debut, fin = _date(src.get("startDate")), _date(src.get("endDate"))
    if debut:
        out["date_event_start"] = debut
        out["date_event_end"] = fin or debut
    lieu = src.get("location")
    nom_lieu = _texte(lieu)
    if nom_lieu:
        out["lieu"] = nom_lieu
    if isinstance(lieu, dict):
        adr = lieu.get("address")
        ville = ""
        if isinstance(adr, dict):
            ville = _texte(adr.get("addressLocality"))
        elif isinstance(adr, str):
            ville = ""     # adresse en une seule chaîne : la ville n'en est pas isolable
        if ville:
            out["ville"] = ville
    img = _texte(src.get("image"))
    if img.startswith(("http://", "https://")):
        out["url_image"] = img
    return out


# ── Microdata : la seconde forme que schema.org autorise ────────────────────────
_ITEMPROP = r'itemprop\s*=\s*["\']{prop}["\']'


def _microdata_valeur(html: str, prop: str) -> str:
    """Valeur d'un itemprop : attribut `content`/`datetime`, sinon texte de la balise."""
    for motif in (
        r'<[^>]+' + _ITEMPROP.format(prop=prop) + r'[^>]*\scontent\s*=\s*["\']([^"\']+)',
        r'<[^>]+\scontent\s*=\s*["\']([^"\']+)["\'][^>]*' + _ITEMPROP.format(prop=prop),
        r'<[^>]+' + _ITEMPROP.format(prop=prop) + r'[^>]*\sdatetime\s*=\s*["\']([^"\']+)',
        r'<[^>]+' + _ITEMPROP.format(prop=prop) + r'[^>]*>([^<]{2,120})<',
    ):
        m = re.search(motif, html or "", re.I)
        if m:
            return m.group(1).strip()
    return ""


def champs_microdata(html: str) -> dict:
    """Mêmes champs, lus en microdata. Complément du JSON-LD, jamais son remplaçant :
    on ne s'en sert que si le JSON-LD n'a rien donné."""
    out: dict = {}
    debut = _date(_microdata_valeur(html, "startDate"))
    if debut:
        out["date_event_start"] = debut
        out["date_event_end"] = _date(_microdata_valeur(html, "endDate")) or debut
    lieu = _microdata_valeur(html, "location") or _microdata_valeur(html, "name")
    # `name` seul est trop ambigu (c'est souvent le titre de l'événement) : on ne le
    # retient que s'il vient d'un itemprop="location" explicite.
    if _microdata_valeur(html, "location"):
        out["lieu"] = _microdata_valeur(html, "location")
    ville = _microdata_valeur(html, "addressLocality")
    if ville:
        out["ville"] = ville
    return out
