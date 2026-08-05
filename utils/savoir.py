#!/usr/bin/env python3
"""Savoir local : ce que Franck sait de l'espace sabaudo, injecté SEULEMENT quand ça
concerne la fiche en cours.

POURQUOI. Le 2026-08-05, AdSense a refusé le site pour « contenu à faible valeur
informative ». La mesure a montré que la part propre d'une fiche vaut environ 250 mots
dans 1100 rendus. Le manque n'est pas une longueur, c'est un APPORT : « concert au Forte
di Bard, 21h, gratuit » ne vaut pas mieux qu'un annuaire. Le même, qui explique en trois
phrases pourquoi un fort militaire donne des concerts, devient irremplaçable.

Ce savoir existe déjà — dans la tête de Franck. Ce module lui donne un endroit où se
déposer UNE fois et servir cinquante fiches sur dix ans.

DIFFÉRENCE AVEC utils/voix.py, ET C'EST TOUTE LA RAISON D'ÊTRE DE CE MODULE. La voix
injecte un TON, le même partout. Le savoir est CONTEXTUEL : une note sur Bard n'a rien à
faire dans une fiche sur Chambéry, et tout injecter diluerait le prompt au lieu de
l'enrichir. On sélectionne donc par lieu, ville, territoire ou catégorie.

FORMAT D'UNE NOTE. Un fichier .md par sujet, avec un en-tête déclarant à quoi il
s'applique. Tout est optionnel : une note sans en-tête n'est jamais sélectionnée (elle
ne peut pas se tromper de fiche), une note avec `territoires:` s'applique à tout un
territoire.

    ---
    lieux: Forte di Bard, Fort de Bard
    villes: Bard
    territoires: vallee-d-aoste
    categories: Concerts & Musique
    ---
    Le Forte di Bard est une forteresse du XIXe reconstruite après que Napoléon
    l'eut rasée. Devenue musée en 2006, elle programme l'été des concerts dans la
    cour d'armes — l'acoustique y est celle d'un puits, et le public entre par la
    rampe à mulets. C'est le seul lieu de la vallée où l'on monte en ascenseur
    panoramique pour aller au concert.

CE QU'ON N'ÉCRIT PAS DEDANS. Ni la programmation (elle change), ni les horaires, ni les
tarifs : ce sont des faits que le pipeline va chercher à la source. Une note dit ce qui
NE CHANGE PAS et ce qu'un visiteur ne devinerait pas.

Non bloquant, comme voix.py : dossier absent, note illisible, en-tête vide — on renvoie
"" et le pipeline tourne normalement.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Dossiers de notes. SAVOIR_DIR peut en lister plusieurs (séparateur système), pour
# pointer l'atelier Obsidian synchronisé sur le VPS. Repli sur docs/savoir/ du dépôt,
# qui sert aussi d'exemple versionné.
SAVOIR_ENV = "SAVOIR_DIR"
_DEFAUT = ROOT / "docs" / "savoir"

# Plafond de sécurité : le savoir complète le prompt, il ne le remplace pas. Au-delà,
# on tronque proprement plutôt que de faire exploser la fenêtre de contexte.
MAX_CHARS_DEFAUT = 3000
# Nombre maximum de notes retenues pour une fiche. Trois sujets pertinents suffisent ;
# au-delà on dilue, et le rédacteur se met à broder au lieu d'ancrer.
MAX_NOTES = 3

_CHAMPS = ("lieux", "villes", "territoires", "categories")


def _plie(s: str) -> str:
    """Minuscules sans accents ni ponctuation : « Vallée d'Aoste » et « vallee-d-aoste »
    doivent se reconnaître."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _dossiers() -> list[Path]:
    d = os.getenv(SAVOIR_ENV, "").strip()
    if d:
        return [p for p in (Path(x.strip()) for x in d.split(os.pathsep) if x.strip())
                if p.is_dir()]
    return [_DEFAUT] if _DEFAUT.is_dir() else []


def _lire_note(chemin: Path) -> dict | None:
    """{'nom', 'cles': {champ: [valeurs pliées]}, 'texte'} ou None si inexploitable."""
    try:
        brut = chemin.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", brut, re.S)
    if not m:
        # Pas d'en-tête = aucune règle d'application. On ne devine PAS : une note qui ne
        # dit pas à quoi elle s'applique ne peut que se tromper de fiche.
        return None
    entete, texte = m.group(1), m.group(2).strip()
    cles = {}
    for ligne in entete.splitlines():
        if ":" not in ligne:
            continue
        champ, valeurs = ligne.split(":", 1)
        champ = champ.strip().lower()
        if champ not in _CHAMPS:
            continue
        cles[champ] = [_plie(v) for v in valeurs.split(",") if _plie(v)]
    if not any(cles.values()) or not texte:
        return None
    return {"nom": chemin.stem, "cles": cles, "texte": texte}


def notes_disponibles() -> list[dict]:
    out, vues = [], set()
    for dossier in _dossiers():
        for f in sorted(dossier.glob("*.md")):
            rp = str(f.resolve())
            if rp in vues:
                continue
            vues.add(rp)
            note = _lire_note(f)
            if note:
                out.append(note)
    return out


def _score(note: dict, champs_fiche: dict) -> int:
    """Plus le critère est précis, plus il pèse : un lieu nommé vaut mieux qu'un
    territoire entier. Une note qui ne correspond à rien vaut 0 et sera écartée."""
    poids = {"lieux": 8, "villes": 4, "categories": 2, "territoires": 1}
    total = 0
    for champ, valeurs in note["cles"].items():
        cible = champs_fiche.get(champ, "")
        if not cible or not valeurs:
            continue
        # Correspondance par inclusion : « Chiesa di San Maurizio, Brusson » contient
        # « brusson ». On exige au moins 3 caractères pour éviter les collisions bêtes.
        if any(v and len(v) >= 3 and (v in cible or cible in v) for v in valeurs):
            total += poids[champ]
    return total


def notes_pour(event: dict, notes: list[dict] | None = None) -> list[dict]:
    """Notes pertinentes pour cette fiche, les plus précises d'abord."""
    notes = notes_disponibles() if notes is None else notes
    champs = {
        "lieux": _plie(event.get("lieu", "")),
        "villes": _plie(event.get("ville", "")),
        "territoires": _plie(event.get("territoire", "")),
        "categories": _plie(event.get("llm_categorie", "")),
    }
    notes_scorees = [(_score(n, champs), n) for n in notes]
    retenues = sorted([(s, n) for s, n in notes_scorees if s > 0],
                      key=lambda x: (-x[0], x[1]["nom"]))
    return [n for _s, n in retenues[:MAX_NOTES]]


def bloc_pour_prompt(event: dict, notes: list[dict] | None = None) -> str:
    """Bloc à injecter dans le prompt du rédacteur, ou "" s'il n'y a rien à dire.

    Le libellé compte : on demande d'ANCRER, pas de recopier. Sans cette consigne, un
    modèle recopie la note mot pour mot et cinquante fiches se mettent à partager le
    même paragraphe — on aurait remplacé un gabarit par un autre.
    """
    retenues = notes_pour(event, notes)
    if not retenues:
        return ""
    max_chars = int(os.getenv("SAVOIR_MAX_CHARS", str(MAX_CHARS_DEFAUT)) or MAX_CHARS_DEFAUT)
    morceaux = []
    for n in retenues:
        morceaux.append(f"— {n['nom']} —\n{n['texte']}")
    corps = "\n\n".join(morceaux)[:max_chars]
    return (
        "CONNAISSANCE LOCALE (rédaction maison, à ne PAS recopier telle quelle).\n"
        "Sers-t'en pour ancrer l'article : ce que le lieu a de particulier, ce qu'un\n"
        "visiteur ne devinerait pas. Reformule, choisis ce qui sert CET événement, et\n"
        "ignore le reste. Ne contredis jamais les faits vérifiés à la source.\n\n"
        + corps
    )
