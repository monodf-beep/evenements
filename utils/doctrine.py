#!/usr/bin/env python3
"""Doctrine d'affichage — choix DÉLIBÉRÉS que le site ne montre pas, à ne jamais
signaler comme un manque (config/doctrine_affichage.md).

Née d'un cas concret (Franck, 2026-08-05) : un persona qui lit le site sans
référence écrite compare ce qu'il voit à son intuition — « il manque le prix » —
alors que l'absence de prix est un choix, pas un oubli. Même principe que chaque
garde-fou qui a tenu cette session (config/excluded_event_keywords.txt,
communes_comte_de_nice.json) : comparer à un FICHIER ÉCRIT, jamais à une
impression. Voir docs/PANEL_SITE_COORDINATEUR.md pour le mécanisme complet.
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_DOCTRINE_FILE = ROOT / "config" / "doctrine_affichage.md"


def load_doctrine(path: Path | None = None) -> list[dict]:
    """Chaque entrée : {"titre": ..., "texte": ...} — une section `## Titre` du
    fichier. [] si le fichier est absent (le panel tourne quand même, sans filet)."""
    p = path or _DOCTRINE_FILE
    if not p.exists():
        return []
    brut = p.read_text(encoding="utf-8")
    sections = re.split(r"(?m)^##\s+", brut)[1:]  # [0] = préambule avant le 1er ##
    out = []
    for sec in sections:
        lignes = sec.splitlines()
        titre = lignes[0].strip() if lignes else ""
        texte = "\n".join(lignes[1:]).strip()
        if titre:
            out.append({"titre": titre, "texte": texte})
    return out


def doctrine_pour_prompt(doctrine: list[dict] | None = None) -> str:
    """Bloc de texte à injecter dans le prompt d'un persona qui lit le site —
    liste courte, en langage courant, pas de jargon de fichier de config."""
    doctrine = doctrine if doctrine is not None else load_doctrine()
    if not doctrine:
        return ""
    lignes = [f"- {d['titre']}" + (f" — {d['texte']}" if d["texte"] else "")
             for d in doctrine]
    return ("CHOIX DÉLIBÉRÉS DU SITE — ne les signale JAMAIS comme un manque, "
            "ce sont des décisions, pas des oublis :\n" + "\n".join(lignes))


_STOP = {"pas", "de", "des", "du", "les", "des", "sur", "dans", "pour", "avec",
        "site", "affiche", "affichage", "jamais", "aucune", "aucun", "nulle", "part"}


def contredit_doctrine(trouvaille: str, doctrine: list[dict] | None = None) -> dict | None:
    """La trouvaille d'un persona contredit-elle une entrée de la doctrine ?

    Correspondance SOUPLE (un seul mot-clé significatif du TITRE suffit — pas une
    correspondance exacte de phrase, un persona paraphrase) sur le titre de
    l'entrée, pas la justification (trop générique pour être un signal fiable).
    C'est le second filet, gratuit et déterministe, pour le cas où le premier
    filtre — la doctrine injectée dans le prompt du persona — n'aurait pas suffi.
    Biaisé vers la PRÉCISION plutôt que le rappel : un faux négatif laisse passer
    une trouvaille que Franck écartera d'un coup d'œil ; un faux positif effacerait
    une trouvaille peut-être valide — le pire des deux erreurs ici. Renvoie
    l'entrée de doctrine contredite, ou None."""
    doctrine = doctrine if doctrine is not None else load_doctrine()
    if not doctrine or not trouvaille:
        return None
    texte = trouvaille.lower()
    for d in doctrine:
        mots = [m for m in re.findall(r"[^\W\d_]{4,}", d["titre"].lower()) if m not in _STOP]
        if mots and any(m in texte for m in mots):
            return d
    return None
