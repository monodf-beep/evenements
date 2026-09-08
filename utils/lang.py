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


# Part des mots du titre traduit déjà présents dans le titre SOURCE au-delà de laquelle
# on considère que le traducteur n'a pas réécrit le titre, il l'a RECOPIÉ. 0.8 laisse
# passer un mot changé sur cinq — au-dessus, ce n'est plus une traduction.
_SEUIL_COPIE = 0.8


def _tokens_titre(s: str) -> set[str]:
    return set(re.findall(r"\w+", _strip_accents(s or "").lower(), re.UNICODE))


def titre_semble_intraduit(titre: str, cible: str, titre_source: str = "") -> bool:
    """True si le titre traduit est en réalité une RECOPIE du titre source resté dans
    la mauvaise langue — pas simplement un titre qui contient un mot de l'autre langue.

    TROUVÉ le 2026-08-06 : WP#2174 « La Saint-Ours 2026 - Rendez Vous en Vallée
    d'Aoste » publié comme fiche ITALIENNE avec un titre resté MOT POUR MOT celui de
    l'original français, alors que sa description, elle, était de l'italien correct.
    `detect_lang(titre, description)` n'aurait RIEN vu : la description, plus longue,
    noie le signal du titre — d'où une fonction qui ne regarde que le titre.

    ⚠️ CORRIGÉ le 2026-08-08, sur un faux positif en production. La première version ne
    regardait QUE le titre produit et refusait dès qu'il portait un marqueur de la
    langue source. Elle a bloqué « La Rencontre Valdôtaine compie 50 anni » (fiche
    3588) : « compie 50 anni » est de l'italien correct, la traduction avait
    parfaitement fonctionné — c'est « Rencontre », NOM PROPRE de l'événement, qui
    déclenchait le marqueur. Or un nom propre français reste français dans la version
    italienne, c'est la règle, pas l'exception, en Vallée d'Aoste bilingue.

    Et le coût d'un faux refus n'est PAS « un jour de retard » comme le disait la
    version d'origine : le LLM reproduit un titre équivalent au run suivant, donc la
    fiche est refusée de nouveau, tous les jours, indéfiniment — un cul-de-sac sans
    rouvreur (règle 3 de CLAUDE.md), qui brûle en plus deux appels API par passage.
    C'est ce qui impose la PRÉCISION ici, pas la sensibilité.

    D'où le critère corrigé : on ne compare plus le titre à un dictionnaire, on le
    compare à SA SOURCE. Refus seulement si les DEUX conditions tiennent :
      1. le titre produit reprend ≥ 80 % des mots du titre source (il l'a recopié,
         pas réécrit) ;
      2. ET ce qui en résulte porte un marqueur de la langue SOURCE, dominant.
    La condition 2 seule laissait passer le cas Rencontre ; la condition 1 seule
    refuserait « Katy Perry » (identique des deux côtés, mais un nom propre n'a rien
    à traduire — d'où le score neutre (0,0) qui le sauve).

    `titre_source` absent : on ne peut rien conclure, on se tait (False)."""
    if not titre_source:
        return False
    toks = _tokens_titre(titre)
    if not toks:
        return False
    if len(toks & _tokens_titre(titre_source)) / len(toks) < _SEUIL_COPIE:
        return False                      # titre réellement réécrit : rien à signaler
    fr, it = _score(titre)
    autre, decompte_cible = (fr, it) if cible == "it" else (it, fr)
    return autre >= 1 and autre > decompte_cible


def _mots_nouveaux(titre: str, titre_source: str) -> str:
    """Les mots de `titre` ABSENTS de `titre_source` (comparaison accents/casse
    ignorés), avec leur graphie d'origine conservée — `_score` EST sensible aux
    accents (« très », « più », « è »…), donc on ne les retire pas ici."""
    src = _tokens_titre(titre_source)
    mots = re.findall(r"\w+", titre or "", re.UNICODE)
    return " ".join(m for m in mots if _strip_accents(m).lower() not in src)


def titre_reecrit_mauvaise_langue(titre: str, cible: str, titre_source: str = "") -> bool:
    """True si les mots que le "traducteur" a AJOUTÉS par rapport à la source (donc
    jamais hérités d'un nom propre repris tel quel) sont dominés par la langue
    SOURCE au lieu de la langue CIBLE — signe que le titre a été RÉÉCRIT, mais dans
    la mauvaise langue.

    TROUVÉ le 31/08, en audit de production (pas en fixture) : `titre_semble_intraduit`
    ci-dessus ne détecte que la RECOPIE quasi verbatim (≥ 80 % des mots du titre source
    repris tels quels). Il ne voit RIEN quand le modèle a vraiment réécrit le titre —
    nouvelle formulation, nouveaux mots — mais dans la langue source au lieu de la
    cible. Cas réel : fiche italienne #732, titre publié « Risò 2026 : le festival
    international du riz revient à Vercelli en septembre » contre une source FR « Riso
    2026 : les dates du Festival international du riz dévoilées » — recouvrement de
    mots à peine 50 %, sous le seuil de 80 % de `titre_semble_intraduit`, qui ne s'est
    donc jamais déclenché, alors que le titre produit est entièrement français.
    `utils.lang.detect_lang` appliqué aux 42 fiches italiennes publiées du site en a
    trouvé 16 dans ce cas (38 % du catalogue italien) — 13 corrigées manuellement le
    31/08, les 3 restantes (Ankama, pizza show a Vercelli, Orlando déjà couvert
    ailleurs) laissées intactes : ce sont des noms propres/graphies neutres, pas des
    titres non traduits (voir plus bas pourquoi ce gate-ci les laisse passer).

    Pourquoi juger seulement les mots NOUVEAUX, pas le titre entier : un titre
    correctement traduit garde souvent un NOM PROPRE dans la langue source — ex.
    « Ankama alla Cité Internationale du Cinéma d'Animation! », où « Cité
    Internationale du Cinéma d'Animation » est le nom réel du lieu, en français, et
    RESTE correct côté italien. Juger la langue du TITRE ENTIER refuserait ce cas à
    tort — exactement le bug du 2026-08-06 que `titre_semble_intraduit` a dû corriger
    le 2026-08-08 pour la RECOPIE. Ce gate-ci l'évite structurellement : sur ce titre,
    le seul mot absent de la source est « alla » — italien — donc rien n'est refusé.

    Fixture obligatoire (règle 3 de CLAUDE.md) : `tests/test_titre_intraduit.py`
    porte le cas Risò (doit REFUSER) et le cas Ankama (doit PASSER), les deux tirés de
    données réelles, pas inventés pour confirmer le design.

    Seuil `autre >= 2` (pas 1, contrairement à `titre_semble_intraduit`) : les mots
    nouveaux sont un sous-ensemble plus petit et plus bruité (parfois un seul mot,
    ambigu) — exiger deux marqueurs concordants réduit le risque qu'un mot neutre
    isolé déclenche un refus.

    `titre_source` absent, ou aucun mot nouveau (titre identique à la source — déjà
    couvert par `titre_semble_intraduit`) : on ne peut rien conclure, on se tait
    (False)."""
    if not titre_source:
        return False
    nouveaux = _mots_nouveaux(titre, titre_source)
    if not nouveaux.strip():
        return False
    fr, it = _score(nouveaux)
    autre, decompte_cible = (fr, it) if cible == "it" else (it, fr)
    return autre >= 2 and autre > decompte_cible


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
