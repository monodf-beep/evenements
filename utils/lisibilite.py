#!/usr/bin/env python3
"""Mesure DÉTERMINISTE de la lisibilité d'un article : longueur des phrases et voix passive.

D'OÙ ÇA VIENT — 2026-09-09, onglet « Lisibilité » de Yoast (capture de Franck sur WP#727) :
« 50 % des phrases contiennent plus de 20 mots ». Mesuré le jour même sur 143 fiches
publiées : phrase médiane de 22 mots, 57 % de phrases longues en médiane, 92 % des fiches
au-dessus du seuil. Or la règle existait déjà — docs/voix/VOIX.md l.18 « phrases courtes
(vise < 20 mots) », prompt de scripts/enrich.py « Phrases COURTES (<20 mots) » — sans que
rien ne la MESURE. Prescrite, jamais vérifiée : le même trou que le temps du récit avant
scripts/audit_temps_recit.

Ce module ne juge pas, il compte, avec les mêmes seuils que Yoast pour que le chiffre
d'ici et celui du back-office parlent de la même chose :
  • phrase LONGUE : plus de 20 mots (Yoast : au plus 25 % des phrases) ;
  • phrase PASSIVE : « être » conjugué + participe passé (Yoast : au plus 10 %), en
    EXCLUANT les verbes qui prennent « être » aux temps composés (« est allée »,
    « sont venus ») — sinon un déplacement compte comme un passif.

Aucun réseau, aucun LLM. Les mots de transition ne sont PAS mesurés ici : leur usage est
une décision de doctrine (VOIX.md l.34 les proscrit, Yoast les réclame), posée à Franck
dans docs/AUDIT_SEO_2026-09-09.md.
"""
from __future__ import annotations
import html
import re

SEUIL_MOTS_LONGUE = 20
# Yoast, en pourcentage des phrases.
YOAST_MAX_LONGUES = 25.0
YOAST_MAX_PASSIF = 10.0

_ETRE = r"(?:est|sont|était|étaient|sera|seront|a été|ont été|avait été|avaient été|fut|furent|soit|soient)"
_PP = r"[a-zà-öø-ÿ]+(?:é|ée|és|ées|i|is|it|ite|its|ites|u|us|ue|ues)\b"
# « s'est imposé », « s'est écrite » : PRONOMINAL, pas passif — le lookbehind écarte le
# « s' » (droit ou typographique) devant l'auxiliaire. Vu sur le réel le 09/09, trois fois
# dans les douze premiers refus : le code ne l'aurait pas montré, la liste l'a montré.
_RE_PASSIF = re.compile(
    rf"(?<![sS][’'])\b{_ETRE}\s+(?:déjà\s+|aussi\s+|également\s+|encore\s+|bien\s+)?({_PP})",
    re.IGNORECASE)
# Mots courants qui FINISSENT comme un participe sans en être un — « c'est jamais »,
# « est petit », « est longue ». Même leçon que ci-dessus, même source.
_PAS_PARTICIPE = {
    "jamais", "mais", "puis", "depuis", "tandis", "ainsi", "aussi", "parmi", "ici", "oui",
    "merci", "fois", "mois", "bois", "trois", "avis", "tapis", "colis", "gratis", "paris",
    "petit", "petite", "petits", "petites", "droit", "droite", "huit", "nuit", "fruit",
    "bruit", "endroit", "toit", "tout", "peu", "lieu", "jeu", "feu", "bleu", "milieu",
    "menu", "tissu", "rue", "vue", "statue", "avenue", "revue", "issue", "longue", "longues",
    "bienvenue", "inconnu", "inconnue", "inconnus", "inconnues", "nu", "tu", "vu",
}
# Participes des verbes conjugués avec « être » : mouvement, état, naissance. « est allée »
# n'est pas un passif, c'est un passé composé.
_NON_PASSIF = {
    "allé", "allée", "allés", "allées", "venu", "venue", "venus", "venues", "arrivé", "arrivée",
    "arrivés", "arrivées", "parti", "partie", "partis", "parties", "resté", "restée", "restés",
    "restées", "né", "née", "nés", "nées", "monté", "montée", "montés", "montées", "descendu",
    "descendue", "descendus", "descendues", "tombé", "tombée", "tombés", "tombées", "devenu",
    "devenue", "devenus", "devenues", "entré", "entrée", "entrés", "entrées", "sorti", "sortie",
    "sortis", "sorties", "revenu", "revenue", "revenus", "revenues", "retourné", "retournée",
    "passé", "passée", "passés", "passées", "mort", "morte", "morts", "mortes", "décédé",
    "décédée", "décédés", "décédées", "apparu", "apparue", "apparus", "apparues",
    # adjectifs fréquents en « est … » qui ne sont pas des passifs
    "ouvert", "ouverte", "ouverts", "ouvertes", "gratuit", "gratuite", "gratuits", "gratuites",
    "fini", "finie", "finis", "finies", "prévu", "prévue", "prévus", "prévues",
}


def texte_brut(s: str | None) -> str:
    """Texte visible d'un corps markdown-léger ou HTML : balises, gras, titres retirés."""
    t = s or ""
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"^#{1,6}\s+", "", t, flags=re.M)   # titres markdown
    t = t.replace("**", "").replace("__", "")
    return re.sub(r"\s+", " ", t).strip()


def phrases(texte: str) -> list[str]:
    """Découpe en phrases (fin de phrase suivie d'une majuscule ou d'une ouverture de
    citation). Les fragments de moins de 3 mots (titres de section, lignes de programme)
    ne sont pas des phrases et ne comptent pas."""
    t = texte_brut(texte)
    if not t:
        return []
    morceaux = re.split(r"(?<=[.!?…])\s+(?=[A-ZÀ-ÖØ-Þ«\"“(])", t)
    return [m.strip() for m in morceaux if len(m.split()) >= 3]


def est_longue(phrase: str) -> bool:
    return len(phrase.split()) > SEUIL_MOTS_LONGUE


def marque_passive(phrase: str) -> str:
    """Le fragment « être + participe » s'il y en a un, '' sinon."""
    for m in _RE_PASSIF.finditer(phrase):
        pp = m.group(1).lower()
        if pp not in _NON_PASSIF and pp not in _PAS_PARTICIPE:
            return m.group(0)
    return ""


def mesurer(texte: str) -> dict:
    """Compte sur un article. `phrases` = 0 signifie « pas de matière à mesurer », pas
    « rien à signaler » : l'appelant doit le dire (règle du zéro, CLAUDE.md)."""
    ph = phrases(texte)
    longues = [p for p in ph if est_longue(p)]
    passives = [(p, marque_passive(p)) for p in ph]
    passives = [(p, m) for p, m in passives if m]
    n = len(ph)
    return {
        "phrases": n,
        "mots": len(texte_brut(texte).split()),
        "longues": longues,
        "passives": passives,
        "pc_longues": (100.0 * len(longues) / n) if n else 0.0,
        "pc_passif": (100.0 * len(passives) / n) if n else 0.0,
        "mots_par_phrase": (sum(len(p.split()) for p in ph) / n) if n else 0.0,
    }
