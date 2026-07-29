#!/usr/bin/env python3
"""Détection de langue FR / IT d'un événement — pour Polylang (agendasabauda.eu bilingue).

Le site est bilingue : chaque événement doit porter SA langue (Polylang) pour que le
sélecteur de langue, les archives et les hreflang soient corrects. Beaucoup de sources
valdôtaines publient la MÊME info en français ET en italien → on ne peut pas se fier au
seul territoire, il faut lire le texte.

Heuristique déterministe (aucun LLM, aucune dépendance). Trois sources de signal :
  1. des MOTS-OUTILS DISTINCTIFS propres à chaque langue (on ignore « de/la/in… ») ;
  2. des MARQUEURS ORTHOGRAPHIQUES haute précision (suffixes -zione/-ità, élisions
     dell'/nell', « gli » pour l'IT ; qu'/j', -eaux/-eux, ç/œ pour le FR) ;
  3. le TERRITOIRE en départage quand le texte ne tranche pas (accents normalisés).

Le TITRE pèse fort (×3) : un événement porte presque toujours son titre dans SA langue,
et c'est justement là que des descriptions bilingues/bruitées faisaient basculer à tort
un titre italien vers le français. Défaut : « fr » (langue par défaut du site).
"""
from __future__ import annotations

import re
import unicodedata

# Mots-outils/marqueurs qui TRANCHENT (présents dans une langue, absents/rares dans
# l'autre). Volontairement disjoints : on écarte « de », « la », « in »… (communs).
_FR = frozenset((
    "le", "les", "des", "une", "est", "été", "à", "au", "aux", "dans", "pour",
    "avec", "cette", "ce", "vous", "nous", "du", "sur", "par", "ses", "leur",
    "leurs", "plus", "très", "où", "déjà", "fête", "juillet", "août", "gratuit",
    "entrée", "jour", "tous", "toute", "aussi", "depuis", "jusqu", "chaque",
    "sans", "sous", "année", "spectacle", "exposition", "rencontre", "atelier",
    "et", "ou", "dès", "être", "fêtes", "journée", "soirée", "billet",
    # renforts FR (haute précision vs IT)
    "vendredi", "samedi", "dimanche", "jeudi", "mardi", "mercredi", "lundi",
    "septembre", "octobre", "novembre", "décembre", "février", "événement",
    "musée", "château", "église", "découverte", "visite", "quand", "toujours",
    "salle", "théâtre", "conférence", "programme", "enfants", "quartier",
))
_IT = frozenset((
    "il", "lo", "gli", "della", "dello", "degli", "delle", "dei", "del", "una",
    "questa", "questo", "città", "più", "è", "né", "gratuito", "ingresso", "con",
    "per", "nella", "nel", "sono", "anche", "tra", "dal", "dalla", "estate",
    "luglio", "agosto", "ogni", "presso", "fino", "durante", "edizione",
    "spettacolo", "mostra", "serata", "giochi", "al", "allo", "alla", "che",
    "dell", "all", "sull", "dai", "dagli", "artista", "concerti", "gratuiti",
    "mercoledì", "sabato", "domenica", "giovedì",
    # renforts IT (haute précision vs FR)
    "venerdì", "lunedì", "martedì", "settembre", "ottobre", "novembre",
    "dicembre", "febbraio", "gennaio", "museo", "chiesa", "castello", "sagra",
    "trofeo", "spettacoli", "mostre", "evento", "eventi", "bambini", "sala",
    "teatro", "incontro", "laboratorio", "quando", "sempre", "danza", "una",
    "questa", "quest", "nostra", "nostro", "loro", "come", "dove", "grande",
))

# Marqueurs ORTHOGRAPHIQUES haute précision (regex sur texte minuscule). Chaque motif
# rencontré vaut un point. Choisis pour n'apparaître QUE dans une langue.
_IT_PAT = re.compile(
    r"\w+(?:zione|zioni|ità|mento|aggio|issim[oa]|tore|trice)\b"   # suffixes IT
    r"|\b(?:dell|nell|sull|dall|quest|sant|un|gli)'"               # élisions IT
    r"|\bgli\b|\bperch[eé]\b", re.UNICODE)
_FR_PAT = re.compile(
    r"\b(?:qu|j)'"                    # clitiques élidées FR (jamais en IT)
    r"|\w+(?:eaux|eux)\b"            # pluriels/adjectifs FR
    r"|[çœ]", re.UNICODE)

# Territoire → langue probable quand le texte ne tranche pas. La Vallée d'Aoste est
# officiellement bilingue → neutre (on s'en remet alors au texte / au défaut). Clés
# SANS accent : le territoire est normalisé (accents retirés) avant comparaison.
_TERRITORY_LANG = {
    "piemonte": "it", "piemont": "it", "piedmont": "it",
    "savoie": "fr", "haute savoie": "fr",
    "nice": "fr", "alpes maritimes": "fr",
}


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def _score(text: str) -> tuple[int, int]:
    """(score FR, score IT) : mots-outils distinctifs + marqueurs orthographiques."""
    low = (text or "").lower()
    toks = re.findall(r"\w+", low, re.UNICODE)
    fr = sum(1 for t in toks if t in _FR) + len(_FR_PAT.findall(low))
    it = sum(1 for t in toks if t in _IT) + len(_IT_PAT.findall(low))
    return fr, it


def detect_lang(title: str = "", description: str = "", territoire: str = "") -> str:
    """Renvoie 'fr' ou 'it'. Le TITRE (pesé ×3) prime : un titre nettement dans une
    langue l'emporte, même si la description bruite. À égalité, on regarde titre+desc,
    puis le TERRITOIRE (accents normalisés), enfin 'fr' (langue du site)."""
    t_fr, t_it = _score(title)
    # 1. Titre décisif : marge nette dans le seul titre → on tranche (protège d'une
    #    description bilingue/française collée à un titre italien, et inversement).
    if abs(t_fr - t_it) >= 2:
        return "it" if t_it > t_fr else "fr"
    # 2. Sinon on combine, titre pesé ×3.
    d_fr, d_it = _score(description)
    fr, it = t_fr * 3 + d_fr, t_it * 3 + d_it
    if abs(fr - it) >= 2:
        return "it" if it > fr else "fr"
    # 3. Texte indécis : le territoire départage (accents retirés ; VdA neutre).
    terr = re.sub(r"[^a-z0-9]+", " ", _strip_accents(territoire).lower()).strip()
    for key, lang in _TERRITORY_LANG.items():
        if key in terr:
            return lang
    # 4. Dernier recours : le léger avantage texte, sinon 'fr'.
    return "it" if it > fr else "fr"


def effective_lang(ev: dict) -> str:
    """Langue à utiliser pour DÉCIDER une traduction/un jumelage : l'ARTICLE déjà rédigé
    fait foi s'il existe, jamais le seul titre brut. `scripts.enrich` écrit TOUJOURS en
    français par défaut, indépendamment de la langue du titre scrapé (site français
    d'abord) — un événement au titre italien peut donc déjà porter un article français.
    Sans le vérifier, translate_events.py a pu traduire un article DÉJÀ français « vers »
    le français (constaté : id 4122, quasi-doublon de l'article français de id 2387),
    et link_translations_as a pu jumeler sur la foi du seul titre. Sans article, repli
    sur le titre/la description bruts (comportement historique)."""
    article_title = (ev.get("article_title") or "").strip()
    body = ""
    if ev.get("enrich_data"):
        import json
        try:
            art = (json.loads(ev["enrich_data"]) or {}).get("article") or {}
            body = f"{art.get('chapo', '')} {art.get('corps', '')}"[:500]
        except (ValueError, TypeError):
            pass
    if article_title or body:
        return detect_lang(article_title, body, ev.get("territoire", ""))
    return detect_lang(ev.get("title", ""), ev.get("description", ""), ev.get("territoire", ""))
