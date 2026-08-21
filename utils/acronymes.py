#!/usr/bin/env python3
"""Développer les sigles à leur PREMIÈRE mention — « Théâtre national de Nice (TNN) ».

D'OÙ ÇA VIENT. Franck, 2026-08-18 : « les acronymes. Ex : TNN, personne ne comprend, alors
mettre théâtre national de Nice ou théâtre de Nice. Je ne sais pas s'il y en a d'autres,
mettre en place une règle. »

LA RÈGLE, en une phrase : le développement d'abord, le sigle entre parenthèses, et une
seule fois. « Théâtre national de Nice (TNN) », puis « le TNN » partout ensuite. Le lecteur
qui ne connaît pas comprend tout de suite ; celui qui connaît n'est pas ralenti par une
répétition.

⚠️ DEUX MÉCANISMES, ET IL NE FAUT PAS LES CONFONDRE :

  • CE FICHIER AGIT, et il n'agit QUE sur le dictionnaire `config/acronymes.json`. Rien
    n'est deviné. Un sigle absent du dictionnaire est laissé tel quel ;
  • `scripts/audit_acronymes.py` DÉCOUVRE des candidats à ajouter au dictionnaire. Sa
    sortie se LIT, elle ne s'applique pas.

La séparation n'est pas un raffinement, c'est ce qui empêche le désastre : un détecteur de
majuscules prendrait « ESTATE REALE 2026 », « NOTE D'ARTE », « TORINO RINASCIMENTALE » et
« XII Monterosa Classica » pour des sigles. Ce sont des titres en capitales et un chiffre
romain, tous relevés dans le corpus réel du 2026-08-17.

ET ON N'INVENTE JAMAIS UN DÉVELOPPEMENT. Un sigle mal développé est PIRE que le sigle seul :
il a l'air d'une information, donc personne ne le vérifie. C'est pourquoi le dictionnaire
sépare les sigles confirmés des candidats repérés.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "acronymes.json"


@lru_cache(maxsize=1)
def _table() -> dict[str, dict]:
    try:
        d = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in (d.get("sigles") or {}).items() if isinstance(v, dict)}


def sigles_connus() -> set[str]:
    return set(_table())


def developpement(sigle: str, langue: str = "fr") -> str:
    """Le développement dans cette langue, "" si le sigle est inconnu ou non traduit."""
    return (_table().get(sigle.upper(), {}).get(langue) or "").strip()


def _motif(sigle: str) -> re.Pattern:
    """Le sigle en MOT ENTIER. Sans les bornes, « MAO » se déclencherait dans « MAOÏSTE »,
    et « GAM » dans « GAMME » — trouvé en écrivant la fixture, pas en relisant le code."""
    return re.compile(rf"(?<![A-Za-zÀ-ÿ0-9]){re.escape(sigle)}(?![A-Za-zÀ-ÿ0-9])")


def deja_developpe(texte: str, sigle: str, langue: str = "fr") -> bool:
    """Vrai si le développement figure DÉJÀ quelque part dans le texte.

    Comparaison insensible à la casse et aux accents partiels : un rédacteur écrira
    « Théâtre National de Nice » ou « théâtre national de Nice » indifféremment, et
    redévelopper par-dessus produirait « Théâtre national de Nice (Théâtre national de
    Nice (TNN)) ». Vu en écrivant la fixture.
    """
    dev = developpement(sigle, langue)
    return bool(dev) and dev.lower() in (texte or "").lower()


def sigles_presents(texte: str) -> list[str]:
    """Les sigles CONNUS présents dans le texte, dans l'ordre d'apparition."""
    t = texte or ""
    trouves = [(m.start(), s) for s in sigles_connus()
               if (m := _motif(s).search(t)) is not None]
    return [s for _pos, s in sorted(trouves)]


def a_developper(texte: str, langue: str = "fr") -> list[str]:
    """Les sigles présents dont le développement MANQUE. C'est la file de travail."""
    return [s for s in sigles_presents(texte)
            if developpement(s, langue) and not deja_developpe(texte, s, langue)]


def developper(texte: str, langue: str = "fr") -> str:
    """Développe la PREMIÈRE mention de chaque sigle connu ; laisse les suivantes.

    Ne touche à rien si le développement est déjà là — sinon on l'empilerait à chaque
    passage, et une fiche republiée tous les jours finirait par ne plus contenir que ça.
    """
    out = texte or ""
    for sigle in sigles_presents(out):
        dev = developpement(sigle, langue)
        if not dev or deja_developpe(out, sigle, langue):
            continue
        out = _motif(sigle).sub(f"{dev} ({sigle})", out, count=1)
    return out


# ── DÉCOUVERTE — sert l'AUDIT, jamais l'action ───────────────────────────────────────
# Mots tout en capitales qui n'ont rien d'un sigle et qu'un détecteur naïf ramasserait.
# Relevés dans le corpus réel, pas imaginés.
_ROMAIN = re.compile(r"^[IVXLCDM]+$")
_PAS_DES_SIGLES = {
    "ESTATE", "REALE", "NOTE", "ARTE", "TORINO", "RINASCIMENTALE", "GAZA", "MUSEO",
    "UNA", "SERA", "AL", "DI", "LA", "LE", "DU", "ET", "OU", "EN", "PAR", "SUR",
    "STILL", "IMAGE", "FOTOGRAFIE", "JESSICA", "LANGE", "EVO", "TOUR",
}


def candidats(texte: str) -> list[str]:
    """Suites de 2 à 6 capitales qui RESSEMBLENT à un sigle, hors bruit connu.

    ⚠️ SORTIE À LIRE, JAMAIS À APPLIQUER. Elle sert à repérer ce qui mériterait d'entrer
    au dictionnaire ; c'est un œil humain qui tranche, parce que seul un œil sait que
    « ARCA » est peut-être un nom propre et non un sigle.
    """
    vus, out = set(), []
    for mot in re.findall(r"(?<![A-Za-zÀ-ÿ])([A-Z]{2,6})(?![a-zà-ÿ])", texte or ""):
        if mot in vus or mot in _PAS_DES_SIGLES or _ROMAIN.match(mot):
            continue
        vus.add(mot)
        out.append(mot)
    return out
