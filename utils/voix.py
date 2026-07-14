#!/usr/bin/env python3
"""Voix éditoriale : injecte le TON JOURNALISTIQUE (défini dans Obsidian) dans les prompts.

Source de vérité UNIQUE = une note Obsidian, sur le VPS, pointée par la variable
d'environnement OBSIDIAN_VOIX_PATH. Le pipeline la lit à chaque run : tu édites la note
dans Obsidian, le prochain enrichissement/newsletter en tient compte — aucune synchro.

On l'applique aux textes LONGS (article enrichi, newsletter, réponse directe SEO) où le
ton se voit ; pas à la description factuelle de 2 phrases (on ne brode pas sur les faits).

Non bloquant : si la note est absente/illisible, voix_block() renvoie "" et le pipeline
tourne normalement. Aucune dépendance externe.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# Chemin de la note (ou du dossier) portant la voix, dans le vault Obsidian sur le VPS.
# Ex. : OBSIDIAN_VOIX_PATH=/root/obsidian/Cultura Sabauda/Voix journaliste.md
VOIX_PATH = os.getenv("OBSIDIAN_VOIX_PATH", "")
# Garde-fou : on n'injecte pas un pavé illimité dans chaque prompt.
MAX_CHARS = int(os.getenv("VOIX_MAX_CHARS", "4000"))


def _strip_obsidian(text: str) -> str:
    """Retire la syntaxe Obsidian pour ne garder que le texte utile pour le LLM."""
    # Frontmatter YAML en tête (--- ... ---).
    text = re.sub(r"\A\s*---\n.*?\n---\n", "", text, flags=re.S)
    # Embeds ![[...]] → rien ; wikilinks [[cible|alias]] → alias, [[cible]] → cible.
    text = re.sub(r"!\[\[[^\]]*\]\]", "", text)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    # Tags #ainsi en début de ligne ou isolés (on garde le # dans les titres markdown).
    text = re.sub(r"(?<!\w)#(?![# ])[\w/-]+", "", text)
    # Commentaires Obsidian %% ... %%.
    text = re.sub(r"%%.*?%%", "", text, flags=re.S)
    return text.strip()


def _read_path(p: Path) -> str:
    """Lit une note, ou concatène les .md d'un dossier (ordre alphabétique)."""
    if p.is_dir():
        parts = []
        for f in sorted(p.glob("*.md")):
            try:
                parts.append(f.read_text(encoding="utf-8"))
            except OSError:
                continue
        return "\n\n".join(parts)
    return p.read_text(encoding="utf-8")


def load_voix() -> str:
    """Renvoie le texte NETTOYÉ de la voix éditoriale, ou "" si indisponible."""
    if not VOIX_PATH:
        return ""
    try:
        raw = _read_path(Path(VOIX_PATH))
    except OSError:
        return ""
    return _strip_obsidian(raw)[:MAX_CHARS].strip()


def voix_block(prefix: str = "") -> str:
    """Bloc prêt à PRÉPOSER à un prompt de rédaction. "" si aucune voix définie.

    `prefix` : phrase d'accroche optionnelle avant la charte (sinon défaut)."""
    voix = load_voix()
    if not voix:
        return ""
    intro = prefix or (
        "VOIX ÉDITORIALE À RESPECTER (charte du journaliste Cultura Sabauda). "
        "Applique ce ton et ces règles de style, SANS jamais altérer les faits "
        "(dates, lieux, prix, noms restent exacts) :")
    return f"{intro}\n\"\"\"\n{voix}\n\"\"\"\n\n"
