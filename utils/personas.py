#!/usr/bin/env python3
"""Personas lecteurs : le PANEL qui relit un article après rédaction.

Chaque persona est une note markdown (dossier docs/personas/ du dépôt, ou un dossier
Obsidian pointé par PERSONAS_DIR). Le pipeline lit le dossier à chaque run : tu ajoutes,
retires ou édites un persona, le prochain enrichissement en tient compte — aucune synchro.

Même esprit que utils/voix.py : source de vérité versionnée dans le dépôt, surchargeable
par un atelier Obsidian. Non bloquant : si le dossier est vide/absent, load_personas()
renvoie [] et le pipeline tourne sans panel.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

# LISTE de dossiers séparés par os.pathsep (comme VOIX_DIR). Chaque .md = un persona.
PERSONAS_ENV = "PERSONAS_DIR"
_DEFAULT_DIR = ROOT / "docs" / "personas"
# Fichiers ignorés (méta, pas des personas).
_SKIP = {"readme.md"}


def _dirs() -> "list[Path]":
    """Dossiers de personas : PERSONAS_DIR (Obsidian) sinon docs/personas/ du dépôt."""
    load_dotenv(ROOT / ".env")
    spec = os.getenv(PERSONAS_ENV, "").strip()
    if spec:
        out = [p for p in (Path(s.strip()) for s in spec.split(os.pathsep) if s.strip())
               if p.is_dir()]
        if out:
            return out
    return [_DEFAULT_DIR] if _DEFAULT_DIR.is_dir() else []


def _strip_obsidian(text: str) -> str:
    """Retire frontmatter YAML, embeds et wikilinks Obsidian (comme utils/voix.py)."""
    text = re.sub(r"\A\s*---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"!\[\[[^\]]*\]\]", "", text)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"%%.*?%%", "", text, flags=re.S)
    return text.strip()


def _title_of(text: str) -> str:
    """1er titre markdown (# ...) nettoyé, sinon 1re ligne non vide."""
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            return line.lstrip("# ").strip()[:90]
        return line[:90]
    return ""


def load_personas() -> list[dict]:
    """Tous les personas SÉLECTIONNABLES, triés par nom de fichier (l'ordre 01-, 02-…
    pilote la priorité). Chaque entrée : name/title/text/path. [] si dossier vide."""
    out, seen = [], set()
    for folder in _dirs():
        for f in sorted(folder.glob("*.md")):
            if f.name.lower() in _SKIP:
                continue
            rp = str(f.resolve())
            if rp in seen:
                continue
            try:
                raw = _strip_obsidian(f.read_text(encoding="utf-8"))
            except OSError:
                continue
            if not raw:
                continue
            seen.add(rp)
            out.append({"name": f.name, "title": _title_of(raw),
                        "text": raw, "path": str(f)})
    return out


def personas_status() -> dict:
    """État du panel pour le back-office : quels personas sont chargés, depuis où."""
    dirs = _dirs()
    personas = load_personas()
    return {"personas": personas, "count": len(personas),
            "dirs": [str(d) for d in dirs],
            "dir": str(dirs[0]) if dirs else "",
            "from_env": bool(os.getenv(PERSONAS_ENV, "").strip())}
