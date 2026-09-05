#!/usr/bin/env python3
"""Tarif, horaires, réservation, accessibilité — LUS sur la page officielle, sans LLM.

Franck, 2026-08-11 : « c'est toujours trop de tâches. Il faut que le script aille chercher
les informations dans les ressources officielles. »

Il a raison, et le dépôt ne le permettait pas : sur 81 colonnes, AUCUNE ne stocke un
tarif, un horaire d'ouverture, une condition d'accès. Ces faits n'existaient que dans le
texte de l'article, écrit par le modèle à partir de la matière qu'on lui donnait. S'ils
manquaient, la seule issue prévue était d'ouvrir une tâche pour un humain — d'où les
« Tarifs de la Fête du Fort du Mont », « Capacités d'accueil des sorties », « Langue de la
médiation (FR/IT/EN ?) » qui remplissaient l'écran.

Or ces informations sont presque toujours ÉCRITES sur la page de l'organisateur. Il
suffisait d'aller les lire. C'est ce que fait ce module, et il le fait sans modèle : un
prix, un horaire, un « sur réservation » sont des formes reconnaissables, en français
comme en italien.

CE QU'IL RAMÈNE, ET SOUS QUELLE FORME. Des EXTRAITS de la page, jamais une interprétation :
la phrase où le prix apparaît, telle quelle. Un humain (ou le rédacteur) voit le contexte
et juge. C'est délibéré — « 12 € » isolé peut être le tarif plein, le tarif réduit, le
prix d'un catalogue ou celui du parking. La phrase, elle, tranche.

CE QU'IL NE FAIT JAMAIS
  • il n'invente rien : pas de motif trouvé = clé absente, jamais « gratuit » par défaut.
    Un tarif faux sur le site est pire qu'un tarif absent ;
  • il ne conclut pas « gratuit » d'une absence de prix ;
  • il ne lit que la page OFFICIELLE (l'appelant s'en assure) : un tarif relevé sur un
    article de presse peut être celui d'une autre édition.
"""
from __future__ import annotations

import re
import unicodedata

# Une phrase, au sens large : on capture autour du motif pour donner le contexte.
_FENETRE = 130


def _texte_visible(html: str) -> str:
    """HTML → texte, scripts et styles retirés, espaces normalisés."""
    txt = re.sub(r"(?is)<(script|style|noscript|svg|head)\b[^>]*>.*?</\1>", " ", html or "")
    txt = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>", " · ", txt)
    txt = re.sub(r"<[^>]+>", " ", txt)
    for ent, car in (("&nbsp;", " "), ("&amp;", "&"), ("&#8364;", "€"), ("&euro;", "€"),
                     ("&quot;", '"'), ("&#039;", "'"), ("&rsquo;", "'")):
        txt = txt.replace(ent, car)
    return re.sub(r"\s+", " ", txt).strip()


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c)).lower()


# Chaque famille : (clé, motifs). Les motifs s'appliquent au texte NORMALISÉ (sans
# accents, minuscules) ; l'extrait rendu, lui, vient du texte D'ORIGINE, accents compris.
_FAMILLES = (
    ("tarif", (
        r"\d+[.,]?\d*\s*(?:€|eur\b|euros?\b)",
        r"\bgratuit\b", r"\bgratuite\b", r"\bentree libre\b", r"\bingresso libero\b",
        r"\bingresso gratuito\b", r"\bentrata libera\b", r"\bfree entry\b",
        r"\btarif", r"\bplein tarif\b", r"\btarif reduit\b", r"\bbiglietto\b",
        r"\bprezzo\b", r"\bintero\b.{0,20}\bridotto\b",
    )),
    ("horaires", (
        r"\b\d{1,2}\s*h\s*\d{0,2}\b", r"\b\d{1,2}[:.]\d{2}\b",
        r"\bouverture\b", r"\bouvert\b.{0,30}\bde\b", r"\borari\b", r"\bapertura\b",
        r"\bdalle\b.{0,10}\balle\b", r"\bde\b.{0,8}\ba\b.{0,8}\bheures?\b",
    )),
    ("reservation", (
        r"\breservation", r"\bsur reservation\b", r"\bprenotazione\b",
        r"\bsu prenotazione\b", r"\bbilletterie\b", r"\bbiglietteria\b",
        r"\binscription", r"\biscrizione\b", r"\bplaces limitees\b",
        r"\bposti limitati\b",
    )),
    ("accessibilite", (
        r"\bpmr\b", r"\baccessibilite\b", r"\bfauteuil roulant\b",
        r"\bmobilita ridotta\b", r"\baccessibile\b", r"\bhandicap\b",
    )),
    ("langue", (
        r"\ben francais et en italien\b", r"\bbilingue\b", r"\bbilingue?\b",
        r"\bin italiano\b", r"\ben francais\b", r"\baudioguide\b", r"\baudioguida\b",
        r"\btraduction simultanee\b", r"\bsottotitol", r"\bsous-titr",
    )),
)


def extraire(html: str, max_par_famille: int = 2) -> dict:
    """{famille: [extraits]} — uniquement ce que la page dit VRAIMENT.

    `max_par_famille` : deux extraits suffisent à trancher, au-delà on recopierait la
    page. Les doublons exacts sont écartés."""
    texte = _texte_visible(html)
    if not texte:
        return {}
    plat = _norm(texte)
    out: dict[str, list[str]] = {}
    for cle, motifs in _FAMILLES:
        vus: list[str] = []
        for motif in motifs:
            for m in re.finditer(motif, plat):
                debut = max(0, m.start() - _FENETRE // 2)
                fin = min(len(texte), m.end() + _FENETRE // 2)
                extrait = texte[debut:fin].strip()
                # Coupe aux bornes de mots pour ne pas rendre un fragment illisible.
                extrait = re.sub(r"^\S*\s|\s\S*$", " ", extrait).strip()
                if extrait and not any(extrait in v or v in extrait for v in vus):
                    vus.append(extrait)
                if len(vus) >= max_par_famille:
                    break
            if len(vus) >= max_par_famille:
                break
        if vus:
            out[cle] = vus
    return out
