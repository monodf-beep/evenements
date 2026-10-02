#!/usr/bin/env python3
"""Reconnaître un COMPTE RENDU là où on attendait une ANNONCE.

Franck, 2026-08-11, en lisant l'article de Stefano Mancuso au Fort de Bard : « il faut
toujours parler au futur puisqu'on propose des événements qui se passent dans le futur.
Là, c'est plutôt du journalisme qui pourrait se trouver dans Nos Alpes : on parle au
passé, l'événement est déjà passé, on dit ce qui s'est fait. Ce n'est pas du tout ce que
je veux pour Agenda Sabauda. »

L'article disait : « Le chercheur italien Stefano Mancuso EST INTERVENU jeudi 23 juillet
2026 au Fort de Bard […] Devant le public du Fort, IL A DÉFENDU l'idée que les végétaux
produisent et gèrent leur propre énergie […] IL A NOTAMMENT ÉVOQUÉ les réseaux
souterrains. »

La cause n'était pas le modèle : `scripts/enrich.py` lui ordonnait « parle au passé » dès
que l'événement était terminé, et sa sélection ne les excluait pas. Les deux sont
corrigés. Ce module sert à trouver ce qui a été publié AVANT la correction.

CE QU'IL CHERCHE : les formes du récit, pas le passé grammatical en général. Un article
d'annonce peut légitimement écrire « le festival, créé en 1998, revient » ou « Mancuso a
publié plusieurs ouvrages » — un passé qui parle du CONTEXTE, pas de l'événement annoncé.
Ce qui trahit le compte rendu, c'est un verbe de DÉROULÉ conjugué au passé : quelqu'un est
intervenu, a défendu, a présenté, le public a découvert.

CE QU'IL NE FAIT PAS : trancher. Il rend les extraits, comme utils/infos_pratiques.py rend
la phrase autour du tarif. Une expression relevée se juge en une seconde ; un score, non.
"""
from __future__ import annotations

import re
import unicodedata

# ─────────────────────────────────────────────────────────────────────────────────────
# LE FRANÇAIS FAIT ICI UNE DISTINCTION QUE MA PREMIÈRE VERSION IGNORAIT, et elle est
# décisive. Vérifié sur les 25 fiches que le détecteur avait signalées en production le
# 2026-08-11 : la plupart étaient de FAUSSES alertes.
#
#   « le sport inclusif EST PRÉSENTÉ comme la valeur centrale »   ← présent passif, correct
#   « le musée EST OUVERT tous les jours de 10h à 12h »           ← présent passif, correct
#   « le départ EST DONNÉ au barrage de Place Moulin »            ← présent passif, correct
#   « une galerie photographique À CIEL OUVERT »                  ← même pas un verbe
#
# « est + participe » d'un verbe TRANSITIF est un présent passif — la forme la plus
# naturelle qui soit pour annoncer. « est + participe » d'un verbe INTRANSITIF de
# mouvement ou d'état (intervenu, venu, reparti…) est, lui, un passé composé. Les deux
# s'écrivent pareil et ne disent pas du tout la même chose.
#
# D'où deux listes séparées, et la seconde est volontairement minuscule.
#
# Et « à ciel ouvert » : en retirant les accents pour comparer, « à » devient « a », donc
# la préposition passait pour l'auxiliaire avoir. Le texte est désormais normalisé SANS
# toucher au « à ». C'est le genre de faute qu'aucune relecture de code ne montre — il a
# fallu voir la liste des faux positifs sur des articles réels.
# ─────────────────────────────────────────────────────────────────────────────────────

# Avec AVOIR : passé composé sans ambiguïté possible.
_AVEC_AVOIR = (
    "defendu", "evoque", "evoquee", "evoques", "raconte", "explique", "expose",
    "accueilli", "reuni", "rassemble", "attire", "anime", "cloture", "inaugure",
    "joue", "interprete", "chante", "danse", "decouvert", "assiste", "participe",
    "afflue", "rempli", "conquis", "seduit", "devoile", "aborde", "livre",
    "partage", "conclu", "presente", "propose", "donne", "ouvert", "termine",
)
# Avec ÊTRE : uniquement les verbes intransitifs, pour lesquels « est + participe » EST un
# passé composé et jamais un passif. Liste courte et fermée, c'est ce qui la rend sûre.
_AVEC_ETRE = (
    "intervenu", "intervenue", "intervenus", "intervenues",
    "venu", "venue", "venus", "venues", "revenu", "revenue", "revenus",
    "arrive", "arrivee", "arrives", "arrivees", "reparti", "repartie", "repartis",
    "monte sur scene", "passe par",
)

_MOTIFS = (
    # « il a défendu », « le public a découvert », « ils ont accueilli »
    (rf"\b(?:a|ont)\b(?:\s+\w+){{0,2}}\s+(?:{'|'.join(_AVEC_AVOIR)})\b",
     "passé composé avec avoir"),
    # « est intervenu », « sont venus » — verbes intransitifs seulement.
    (rf"\b(?:est|sont)\b(?:\s+\w+){{0,2}}\s+(?:{'|'.join(_AVEC_ETRE)})\b",
     "passé composé avec être"),
    # Formules de compte rendu, sans ambiguïté possible sur un agenda.
    (r"\bdevant (?:le|un|son) public,", "« devant le public, … »"),
    (r"\bles (?:visiteurs|spectateurs|participants) ont (?:pu|decouvert|assiste)\b",
     "« les visiteurs ont pu… »"),
    (r"\bs'est (?:tenu|tenue|deroule|deroulee|acheve|achevee|conclu|conclue)\b",
     "« s'est tenu / déroulé »"),
    (r"\bse sont (?:tenus|tenues|deroules|deroulees|succede)\b", "« se sont tenus »"),
)


def _norm(s: str) -> str:
    """Minuscules sans accents — SAUF le « à », qu'on protège.

    Sans cette protection, « à » devient « a » et la préposition passe pour l'auxiliaire
    avoir : « une galerie photographique À CIEL OUVERT » et « le Grenier À IMAGES PROPOSE
    des ateliers » étaient signalés comme des comptes rendus le 2026-08-11. Deux textes
    parfaitement corrects, sur des fiches en ligne.

    C'est une faute qu'aucune relecture de code ne montre : il a fallu voir la liste des
    faux positifs sur de vrais articles."""
    # Le « à » n'est protégé que comme MOT ISOLÉ. Première version : un remplacement
    # global, qui transformait « déjà » en « dejà » — et « déjà » est justement l'un des
    # marqueurs de rétrospective les plus utiles. Un correctif qui casse le correctif
    # suivant, trouvé par la fixture dix minutes après.
    protege = re.sub(r"(?<![a-zà-ÿ])à(?![a-zà-ÿ])", "\x01", (s or "").lower())
    n = unicodedata.normalize("NFKD", protege)
    return "".join(c for c in n if not unicodedata.combining(c)).replace("\x01", "à")


# CE QUI RESTAIT APRÈS LA PREMIÈRE CORRECTION, et qui est la vraie difficulté du sujet.
# Sur les 13 dernières fiches signalées, DOUZE étaient encore légitimes :
#
#   « le musée y A OUVERT EN 1984 »                              ← histoire du lieu
#   « qui A TERMINÉ 5e de Nationale LA SAISON PRÉCÉDENTE »       ← édition d'avant
#   « qui A DÉJÀ SÉDUIT 50 000 visiteurs L'ANNÉE PRÉCÉDENTE »    ← fréquentation passée
#   « sa XXVIe édition, EN 2025, S'EST TENUE du 10 au 15 »       ← édition d'avant
#   « des artistes qui ONT EXPOSÉ AU FIL DES ANS »               ← historique
#
# Toutes portent un MARQUEUR DE RÉTROSPECTIVE : une année révolue, « précédente »,
# « déjà », « au fil des ans », « depuis ». Le passé y parle d'AVANT, pas de l'événement
# annoncé — et c'est justement le passé que la charte autorise.
#
# La seule vraie faute du lot n'en portait aucun : « L'inauguration, LE 13 JUIN 2026,
# A RÉUNI projection d'un film » — l'année est celle de l'événement, donc ça raconte
# bien ce qui vient de se passer.
#
# D'où l'ancre : une année ANTÉRIEURE à celle de l'événement disculpe, la sienne non.
# Même principe que partout ailleurs aujourd'hui — on ne juge pas une forme isolée, on la
# confronte à un fait qu'on connaît déjà.
_RETROSPECTIF = (
    r"\bprecedent", r"\bl'an dernier\b", r"\bderniere edition\b", r"\bdeja\b",
    r"\bau fil des ans\b", r"\bchaque edition\b", r"\bdepuis\b", r"\bjusqu'ici\b",
    r"\bdans les annees \d{4}", r"\bavant\b", r"\bhistorique\b", r"\bautrefois\b",
    r"\ba l'epoque\b", r"\bpar le passe\b", r"\bfonde en\b", r"\bcree en\b", r"\ba donne naissance\b",
    r"\bne dans les annees\b", r"\bpremiere edition\b", r"\bediteurs? precedent",
)


def _est_du_contexte(zone: str, annee_reference: int | None) -> bool:
    """La zone parle-t-elle d'AVANT ? Alors son passé est légitime dans une annonce."""
    if any(re.search(m, zone) for m in _RETROSPECTIF):
        return True
    if annee_reference:
        for m in re.finditer(r"\b(19|20)\d{2}\b", zone):
            if int(m.group(0)) < annee_reference:
                return True
    return False


def extraits_de_recit(texte: str, max_extraits: int = 3,
                      annee_reference: int | None = None) -> list[str]:
    """Les passages qui racontent au lieu d'annoncer. [] si l'article annonce bien.

    L'extrait rendu vient du texte D'ORIGINE (accents compris) : c'est lui qu'on relit
    pour juger, pas le motif qui l'a trouvé."""
    if not texte:
        return []
    plat = _norm(texte)
    vus: list[str] = []
    for motif, _libelle in _MOTIFS:
        for m in re.finditer(motif, plat):
            debut = max(0, m.start() - 45)
            fin = min(len(texte), m.end() + 45)
            # Un passé entouré d'un marqueur de rétrospective parle du CONTEXTE.
            if _est_du_contexte(plat[max(0, m.start() - 90):m.end() + 90], annee_reference):
                continue
            extrait = re.sub(r"\s+", " ", texte[debut:fin]).strip()
            extrait = re.sub(r"^\S*\s|\s\S*$", " ", extrait).strip()
            if extrait and not any(extrait in v or v in extrait for v in vus):
                vus.append(extrait)
            if len(vus) >= max_extraits:
                return vus
    return vus


def raconte(texte: str, annee_reference: int | None = None) -> bool:
    """Vrai si l'article a la forme d'un compte rendu."""
    return bool(extraits_de_recit(texte, max_extraits=1,
                                  annee_reference=annee_reference))
