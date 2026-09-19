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
