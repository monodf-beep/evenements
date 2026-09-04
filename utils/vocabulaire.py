#!/usr/bin/env python3
"""Le vocabulaire interdit — une seule source, deux usages.

D'OÙ ÇA VIENT. Franck, 2026-08-21, en lisant une page en ligne : « ne jamais mettre
"royaume de Sardaigne" mais mettre "les États de Savoie" ».

CE QUE CE FICHIER CHANGE. La même consigne existait déjà pour « Venise des Alpes »,
recopiée dans QUATRE prompts (`enrich`, `translate_events`, `conform_articles`,
`utils/social`) et dans la charte. Cinq copies, aucune ne disant laquelle fait foi — et
elles divergeront. `config/vocabulaire_interdit.json` devient la référence ; les prompts
citent cette liste au lieu de la répéter.

DEUX TEMPS, ET ILS NE FONT PAS LE MÊME TRAVAIL :

  • `consigne_prompt()` empêche d'écrire l'expression DEMAIN ;
  • `scripts/audit_vocabulaire.py` la trouve dans ce qui est DÉJÀ publié.

Un prompt ne corrige pas le passé. « Venise des Alpes » figurait dans les quatre prompts
et a quand même été écrit, généré, publié, puis trouvé en ligne le 2026-08-18.

ON NE REMPLACE JAMAIS AUTOMATIQUEMENT. Une expression interdite peut être le titre officiel
d'une exposition ou une citation — « Il Regno di Sardegna » sur l'affiche d'un musée n'est
pas notre prose. Le module SIGNALE ; c'est un œil qui tranche, la phrase sous les yeux.
"""
from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "vocabulaire_interdit.json"


def _sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c)).lower()


@lru_cache(maxsize=1)
def interdits() -> tuple[dict, ...]:
    try:
        d = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    return tuple(e for e in (d.get("interdits") or []) if e.get("expression"))


def _formes(entree: dict) -> list[str]:
    """L'expression et ses variantes, normalisées. La normalisation compte : « États »
    s'écrit aussi « Etats », et « Regno di Sardegna » arrive en italien."""
    return [_sans_accents(f) for f in
            [entree["expression"], *(entree.get("variantes") or [])] if f]


def trouver(texte: str) -> list[tuple[str, str]]:
    """[(expression interdite, extrait de la phrase où elle apparaît)] — jamais un booléen.

    L'EXTRAIT EST OBLIGATOIRE. Un relevé qui dit « expression interdite trouvée » sans
    montrer la phrase ne se vérifie pas : impossible de distinguer notre prose du titre
    officiel d'une exposition. C'est la même exigence que pour les dates contredites.
    """
    plat = _sans_accents(texte or "")
    out: list[tuple[str, str]] = []
    for entree in interdits():
        for forme in _formes(entree):
            i = plat.find(forme)
            if i < 0:
                continue
            deb = max(0, plat.rfind(".", 0, i) + 1)
            fin = plat.find(".", i + len(forme))
            fin = len(texte) if fin < 0 else fin + 1
            out.append((entree["expression"], (texte or "")[deb:fin].strip()[:220]))
            break          # une seule fois par expression : on signale, on ne compte pas
    return out


def remplacement(expression: str, langue: str = "fr") -> str:
    """Ce qu'il faut écrire à la place, "" si l'expression est simplement à supprimer."""
    for e in interdits():
        if e["expression"] == expression:
            return (e.get(f"remplacement_{langue}") or "").strip()
    return ""


def consigne_prompt(langue: str = "fr") -> str:
    """La consigne à insérer dans un prompt de rédaction. UNE seule source, quatre usages.

    Rendue en une ligne par expression, avec le remplacement quand il existe : « ne dis pas
    X, dis Y » se suit mieux que « n'emploie pas X », qui laisse le rédacteur sans solution
    et donc libre d'improviser.
    """
    lignes = []
    for e in interdits():
        rempl = (e.get(f"remplacement_{langue}") or "").strip()
        if rempl:
            lignes.append(f'- Ne dis JAMAIS « {e["expression"]} » : écris « {rempl} ».')
        else:
            lignes.append(f'- N\'emploie JAMAIS « {e["expression"]} », ni ses variantes.')
    return "\n".join(lignes)
