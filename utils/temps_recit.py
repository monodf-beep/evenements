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

# Verbes de DÉROULÉ au passé composé : l'auxiliaire, puis le participe. On borne l'écart
# entre les deux (« il a notamment évoqué », « il s'est longuement exprimé ») sans laisser
# la fenêtre traverser une phrase entière.
_PARTICIPES = (
    "intervenu", "intervenue", "intervenus", "presente", "presentee", "presentes",
    "defendu", "evoque", "evoquee", "evoques", "raconte", "explique", "expose",
    "accueilli", "reuni", "rassemble", "attire", "propose", "anime", "ouvert",
    "cloture", "inaugure", "donne", "joue", "interprete", "chante", "danse",
    "decouvert", "assiste", "participe", "afflue", "rempli", "conquis", "seduit",
    "devoile", "abordé", "aborde", "livre", "partage", "conclu", "termine",
)
# PAS de plus-que-parfait ni d'imparfait dans les auxiliaires. « Elle AVAIT présenté
# L'Île des esclaves la saison précédente » est du CONTEXTE parfaitement légitime dans une
# annonce : ça parle de l'édition d'avant, pas de celle qu'on annonce. Le cas a été
# attrapé par la fixture avant que le détecteur ne parte — c'est exactement ce que la
# règle 3 attend d'un cas « qui doit PASSER, choisi près de la frontière ».
_AUX = r"\b(?:a|ont|est|sont|s'est|se sont)\b"

_MOTIFS = (
    # « il a défendu », « le public a découvert », « elle est intervenue »
    (rf"{_AUX}(?:\s+\w+){{0,2}}\s+(?:{'|'.join(_PARTICIPES)})\b", "verbe de déroulé au passé"),
    # Formules de compte rendu, sans ambiguïté possible sur un agenda.
    (r"\bdevant (?:le|un|son|le nombreux) public\b", "« devant le public »"),
    (r"\bles (?:visiteurs|spectateurs|participants) ont\b", "« les visiteurs ont… »"),
    (r"\bs'est (?:tenu|tenue|deroule|deroulee|acheve|achevee|conclu|conclue)\b",
     "« s'est tenu / déroulé »"),
    (r"\bse sont (?:tenus|tenues|deroules|deroulees|succede)\b", "« se sont tenus »"),
    (r"\bl'an dernier, (?:il|elle|le|la)\b", "retour sur l'édition précédente"),
    (r"\b(?:cette annee|cette edition) (?:a|aura) (?:attire|reuni|rassemble)\b",
     "bilan de fréquentation"),
)


def _norm(s: str) -> str:
    n = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in n if not unicodedata.combining(c))


def extraits_de_recit(texte: str, max_extraits: int = 3) -> list[str]:
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
            extrait = re.sub(r"\s+", " ", texte[debut:fin]).strip()
            extrait = re.sub(r"^\S*\s|\s\S*$", " ", extrait).strip()
            if extrait and not any(extrait in v or v in extrait for v in vus):
                vus.append(extrait)
            if len(vus) >= max_extraits:
                return vus
    return vus


def raconte(texte: str) -> bool:
    """Vrai si l'article a la forme d'un compte rendu."""
    return bool(extraits_de_recit(texte, max_extraits=1))
