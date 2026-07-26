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

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# Nom de la variable d'env. LISTE de chemins (fichiers ou dossiers) séparés par « : »,
# chargés DANS L'ORDRE — d'abord la voix commune, puis la surcharge du projet. Système
# EN COUCHES. Chaque chemin peut être un .md ou un dossier (ses .md sont concaténés).
# Ex. : OBSIDIAN_VOIX_PATH=/opt/obsidian/.../Voix commune (synthèse).md:/opt/obsidian/.../Charte Agenda Sabauda (surcharges).md
VOIX_ENV = "OBSIDIAN_VOIX_PATH"


def _spec() -> str:
    """Lit OBSIDIAN_VOIX_PATH à l'APPEL (pas à l'import) : robuste quel que soit l'ordre
    de chargement. Charge d'abord le .env du projet (idempotent, sans écraser l'env)."""
    load_dotenv(ROOT / ".env")
    return os.getenv(VOIX_ENV, "")


def _max_chars() -> int:
    return int(os.getenv("VOIX_MAX_CHARS", "6000"))


# Voix CANONIQUE versionnée dans le dépôt : sert de source par défaut ET de garde-fou
# (la voix est TOUJOURS vivante, même sans Obsidian). OBSIDIAN_VOIX_PATH la surcharge/
# complète (système en couches). C'est le même fichier qu'on peut ouvrir dans Obsidian.
_DEFAULT_VOIX = ROOT / "docs" / "voix" / "VOIX.md"


# Dossier de voix : atelier Obsidian synchronisé sur le VPS (VOIX_DIR), sinon docs/voix/
# du dépôt. Chaque .md = une voix sélectionnable au back-office.
def _voix_dir() -> "Path | None":
    d = os.getenv("VOIX_DIR", "").strip()
    p = Path(d) if d else (ROOT / "docs" / "voix")
    return p if p.is_dir() else None


def available_voix() -> list[dict]:
    """Toutes les voix SÉLECTIONNABLES : les .md du dossier de voix (Obsidian via VOIX_DIR,
    sinon docs/voix/), plus le filet docs/VOIX.md. Chaque entrée : name/title/chars/path."""
    out, seen = [], set()
    d = _voix_dir()
    folders = [d] if d else []
    for folder in folders:
        for f in sorted(folder.glob("*.md")):
            rp = str(f.resolve())
            if rp in seen:
                continue
            try:
                raw = _strip_obsidian(f.read_text(encoding="utf-8"))
            except OSError:
                continue
            seen.add(rp)
            out.append({"name": f.name, "title": _title_of(raw), "chars": len(raw), "path": str(f)})
    if _DEFAULT_VOIX.exists() and str(_DEFAULT_VOIX.resolve()) not in seen:
        try:
            raw = _strip_obsidian(_DEFAULT_VOIX.read_text(encoding="utf-8"))
            out.append({"name": _DEFAULT_VOIX.name, "title": _title_of(raw),
                        "chars": len(raw), "path": str(_DEFAULT_VOIX)})
        except OSError:
            pass
    return out


def _sources() -> list[str]:
    """Chemins de voix à charger, par priorité :
    1) OBSIDIAN_VOIX_PATH (override explicite, système EN COUCHES pour power users) ;
    2) la voix CHOISIE au back-office (settings.voix_active), résolue dans le dossier ;
    3) filet : docs/VOIX.md. La voix n'est donc jamais 'vide'."""
    spec = _spec().strip()
    if spec:
        return [s.strip() for s in spec.split(os.pathsep) if s.strip()]
    try:
        from utils import settings as _ps
        chosen = _ps.voix_active().strip()
    except Exception:
        chosen = ""
    if chosen:
        for v in available_voix():
            if v["name"] == chosen or Path(v["path"]).name == chosen:
                return [v["path"]]
    return [str(_DEFAULT_VOIX)]


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
    """Renvoie le texte NETTOYÉ de la voix éditoriale, ou "" si indisponible.

    Plusieurs chemins (séparés par « : ») sont chargés DANS L'ORDRE et concaténés :
    voix commune d'abord, surcharge projet ensuite. Un chemin manquant est ignoré."""
    layers = []
    for spec in _sources():
        try:
            txt = _strip_obsidian(_read_path(Path(spec)))
        except OSError:
            continue
        if txt:
            layers.append(txt)
    if not layers:
        return ""
    return "\n\n".join(layers)[:_max_chars()].strip()


def _title_of(text: str) -> str:
    """Titre lisible d'une note : 1er titre markdown, sinon 1re ligne non vide."""
    for line in (text or "").splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("# ").strip()[:90]
        if line:
            return line[:90]
    return ""


def _voix_files(p: Path) -> list:
    """Fichiers .md effectivement chargés pour un chemin (un dossier = ses .md triés)."""
    if p.is_dir():
        return sorted(p.glob("*.md"))
    return [p] if p.exists() else []


def voix_status() -> dict:
    """État de la voix pour le back-office : QUELLES voix sont chargées (nom + titre +
    taille), depuis quelle source, actif/absent. Permet de VOIR que c'est vivant et pas
    cassé, et EXACTEMENT quelle(s) voix est appliquée (plusieurs notes possibles)."""
    sources = []
    for s in _sources():
        p = Path(s)
        files = []
        for f in _voix_files(p):
            try:
                raw = _strip_obsidian(f.read_text(encoding="utf-8"))
            except OSError:
                continue
            files.append({"name": f.name, "title": _title_of(raw), "chars": len(raw)})
        sources.append({"path": s, "exists": p.exists(), "is_dir": p.is_dir(),
                        "files": files, "chars": sum(f["chars"] for f in files)})
    text = load_voix()
    try:
        from utils import settings as _ps
        chosen = _ps.voix_active()
    except Exception:
        chosen = ""
    d = _voix_dir()
    return {"sources": sources, "active": bool(text), "total_chars": len(text),
            "from_env": bool(_spec().strip()), "text": text,
            "available": available_voix(), "chosen": chosen,
            "voix_dir": str(d) if d else ""}


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
