#!/usr/bin/env python3
"""Détection déterministe d'un marqueur d'annulation/report dans un TITRE.

Canal 2 de docs/EVENEMENTS_ANNULES.md (proposition validée par Franck le
2026-08-05, mécanique « alerte seulement, un humain confirme ») : quand un
festival est annulé, la presse écrit « Festival X annulé » — cet article partage
ses mots avec la fiche du festival, donc `scripts.dedupe` va les apparier. Sans
ce module, il les FUSIONNERAIT (le mécanisme WP#6798, en pire : la dépêche
d'annulation deviendrait matière de la fiche encore publiée). Ici, on détecte le
marqueur AVANT la fusion pour la bloquer et alerter — jamais pour poser tout seul
un bandeau « annulé » sur la foi d'un seul titre de presse.

Zéro LLM, gratuit : mêmes mécaniques que `utils.sources.load_excluded_events_filter`
(config/annulation_keywords.txt, une expression par ligne, accents/casse ignorés).
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_KEYWORDS_FILE = ROOT / "config" / "annulation_keywords.txt"

from utils.sources import _strip_accents  # noqa: E402 — même normalisation partout


def _load_keywords(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [_strip_accents(line.strip()).lower()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")]


def _compile(words: list[str]):
    if not words:
        return None
    parts = sorted((re.escape(w) for w in words), key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(parts) + r")\b")


def load_annulation_filter(path: Path | None = None):
    """Regex des marqueurs d'annulation (config/annulation_keywords.txt)."""
    return _compile(_load_keywords(path or _KEYWORDS_FILE))


def marqueur_annulation(titre: str, regex=None) -> str | None:
    """Le marqueur trouvé dans le TITRE (jamais la description : un article dont
    le corps mentionne une annulation passée, ancienne ou d'un AUTRE événement,
    ne doit pas déclencher — le titre, lui, est ce que la presse choisit de dire
    de CET article-ci). None si aucun marqueur.

    Renvoie le texte exact matché (utile pour le message Slack), pas juste un
    booléen — « repéré sur "annullato" » est plus vérifiable que « repéré »."""
    if regex is None:
        regex = load_annulation_filter()
    if regex is None:
        return None
    m = regex.search(_strip_accents(titre or "").lower())
    return m.group(0) if m else None


# ══ MARQUEUR SUR UNE PAGE ENTIÈRE (canal 3) ══════════════════════════════════════════
#
# Un TITRE qui dit « annullato » parle de l'événement ; une PAGE entière dit beaucoup
# d'autres choses. Mesuré du 19/09 au 01/10 : `audit_annulations` a rendu 6 suspicions,
# 6 faux positifs, 0 annulation réelle — et chaque faux positif était une phrase qui ne
# vise pas l'événement :
#   • les conditions de vente de la billetterie (« ART. 4 ANNULLAMENTO ORDINE »), présentes
#     sur TOUTE page du site de la Fondazione Merz — 4 fois ;
#   • la clause météo conditionnelle (« sarà rinviata in caso di forte maltempo »), qui
#     est une promesse, pas un fait — 3 fois ;
#   • l'édition précédente (« dopo l'annullamento dell'edizione 2025, … torna »).
# On juge donc l'occurrence dans sa FENÊTRE, pas le mot nu. Les cas qui doivent RESTER
# signalés sont près de la frontière et tenus en fixture : « rinviato causa maltempo »
# (un report réel, dont la cause est la météo) et « rinviato al 2027 » (une année, mais
# celle d'après).
_FENETRE = 90
_CGV_ARTICLE = re.compile(r"\bart\.?\s*\d+\s*[-–:.)]?\s*$")   # « ART. 4 » juste avant le mot
_CGV = re.compile(
    r"annullamento\s+(?:dell['’]\s*)?ordin[ei]"           # « annullamento (dell') ordine »
    r"|diritto\s+di\s+recesso|condizioni\s+(?:generali\s+)?di\s+vendita"
    r"|conditions\s+g[ée]n[ée]rales\s+de\s+vente")
_METEO_CONDITIONNELLE = re.compile(
    r"\bin\s+caso\s+di\s+(?:forte\s+|brutto\s+|cattivo\s+)?(?:maltempo|pioggia|meteo|"
    r"condizioni\s+meteo)|\bse\s+(?:il\s+tempo|piove)|\bsalvo\s+maltempo"
    r"|\ben\s+cas\s+de\s+(?:mauvais\s+temps|pluie|intemp[ée]ries)|\bsi\s+(?:le\s+temps|il\s+pleut)")
_ANNEE = re.compile(r"\b(20\d\d)\b")


def marqueur_annulation_page(texte: str, annee_evenement: int | None, regex=None) -> str | None:
    """Le premier marqueur d'une PAGE qui vise vraiment l'événement, sinon None.

    Écarte une occurrence quand sa fenêtre (±90 caractères) est : une condition de vente,
    une clause météo CONDITIONNELLE, ou l'annulation d'une édition antérieure à
    `annee_evenement` (année lue dans la fenêtre, strictement inférieure). Sans année
    d'événement connue, ce dernier filtre ne s'applique pas — on ne devine pas."""
    if regex is None:
        regex = load_annulation_filter()
    if regex is None:
        return None
    t = _strip_accents(texte or "").lower()
    for m in regex.finditer(t):
        avant = t[max(0, m.start() - _FENETRE):m.start()]
        fenetre = t[max(0, m.start() - _FENETRE):m.end() + _FENETRE]
        if _CGV_ARTICLE.search(avant) or _CGV.search(fenetre):
            continue
        if _METEO_CONDITIONNELLE.search(fenetre):
            continue
        if annee_evenement:
            annees = [int(a) for a in _ANNEE.findall(fenetre)]
            if annees and max(annees) < annee_evenement:
                continue
        return m.group(0)
    return None
