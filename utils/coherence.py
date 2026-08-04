#!/usr/bin/env python3
"""LA DESCRIPTION PARLE-T-ELLE DE CETTE FICHE ? — contrôle déterministe, zéro appel LLM.

POURQUOI CE MODULE EXISTE. Arbitrage de Franck, 2026-08-04 : « je veux qu'il puisse juger
la description, et ce, partout. On ne doit pas faire des choses automatiques pour faire
des choses automatiques sans réfléchir. »

Il répondait à une proposition de ma part qui était mauvaise : j'avais présenté la
relecture humaine quotidienne de deux permaliens comme « la seule protection » contre une
description polluée. C'était faire compenser à un humain un contrôle qu'on pouvait écrire —
exactement ce que `docs/ETATS_TERMINAUX.md` interdit ailleurs (« un humain qui tape une
commande n'est pas une réponse »).

CE QUI REND LE CONTRÔLE POSSIBLE, et qu'on n'avait pas vu pendant trois jours : la
contradiction de WP#6798 était visible SANS INTELLIGENCE ARTIFICIELLE. La fiche disait
« Une semaine pas plus · La Comédie des Alpes · Chambéry » et sa description disait
« Fête du lac 2026 : les spectateurs qui n'habitent pas Annecy paieront plus cher ». Aucun
mot commun, et une autre commune nommée. Il n'y avait rien à comprendre — seulement à
comparer.

LES DEUX SIGNAUX, et pourquoi ceux-là :

  ① AUCUN MOT COMMUN entre la description et l'identité propre de la fiche (titre + lieu +
    ville). Universel : il ne dépend d'aucune liste, marche dans les deux langues et sur
    les quatre territoires. C'est le signal qui attrape WP#6798.

  ② UNE AUTRE COMMUNE NOMMÉE, et pas la sienne. Décisif quand il tombe, mais il ne couvre
    que la Savoie/Haute-Savoie et le Comté de Nice — seuls territoires dont on possède la
    liste des communes. Il complète ①, il ne le remplace pas.

CE QU'IL NE FAIT PAS, ET C'EST VOULU. Il ne juge pas la QUALITÉ d'une description, ni sa
véracité : seulement si elle parle de la même chose que le reste de la fiche. Une
description médiocre mais cohérente passe — ce module n'est pas un critique littéraire,
et lui demander de l'être en ferait un générateur de faux positifs.

Il ne BLOQUE rien non plus par lui-même : il rend un motif ou None, et chaque appelant
décide. Poser un blocage uniforme sans mesurer d'abord combien de fiches il attrape, ce
serait précisément « faire de l'automatique sans réfléchir » — et fabriquer un état
terminal de plus.
"""
from __future__ import annotations
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Longueur minimale du texte VISIBLE en dessous de laquelle on ne conclut rien. Une
# description de deux lignes peut légitimement ne reprendre aucun mot du titre ; c'est sur
# un texte fourni que l'absence totale de recoupement devient anormale. Le signal ① est
# une absence — et une absence ne prouve quelque chose que s'il y avait la place d'être
# présent.
MIN_TEXTE_VISIBLE = 200


def _sans_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _texte_visible(html: str | None) -> str:
    """Texte débarrassé des balises et des URLs — mêmes précautions que dedupe._text_len.

    Les URLs sont retirées AVANT tout comptage : un item Google News n'est qu'un lien dont
    l'adresse encodée pèse des centaines de caractères, et c'est ce volume creux qui a
    fabriqué WP#6798 en gagnant un arbitrage de longueur."""
    s = re.sub(r"<[^>]+>", " ", html or "")
    s = re.sub(r"https?://\S+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _mots(s: str, mini: int = 4) -> set[str]:
    """Mots significatifs. Seuil à 4 lettres et non 3 : « lac », « art », « ville »
    reviennent partout et créeraient de faux recoupements rassurants."""
    return {t for t in re.findall(r"[a-z0-9]+", _sans_accents(s)) if len(t) >= mini}


def _charger_communes() -> dict[str, str]:
    """Commune normalisée → territoire. Deux territoires seulement : ce sont les seuls dont
    on possède la liste (`config/communes_*.json`). Le Piémont et la Vallée d'Aoste n'en
    ont pas — le signal ② est donc muet pour eux, et c'est dit plutôt que masqué."""
    out: dict[str, str] = {}
    try:
        d = json.loads((ROOT / "config" / "communes_savoie_dept.json").read_text())
        for c in d:
            if not str(c).startswith("_"):
                out[_sans_accents(str(c).replace("-", " "))] = "Savoie"
    except (OSError, ValueError):
        pass
    try:
        d = json.loads((ROOT / "config" / "communes_comte_de_nice.json").read_text())
        for cle in ("arrondissement_de_nice", "arrondissement_de_grasse"):
            for c in d.get(cle) or []:
                out.setdefault(_sans_accents(str(c).replace("-", " ")), "Nice")
    except (OSError, ValueError):
        pass
    return out


_COMMUNES: dict[str, str] | None = None


def _communes() -> dict[str, str]:
    global _COMMUNES
    if _COMMUNES is None:
        _COMMUNES = _charger_communes()
    return _COMMUNES


def incoherence_description(event: dict) -> str | None:
    """Motif si la description ne parle manifestement pas de cette fiche, sinon None.

    None ≠ « description correcte » : ça veut dire « rien de contradictoire détecté ». La
    nuance compte, c'est elle qui empêche de prendre ce contrôle pour une garantie."""
    texte = _texte_visible(event.get("description"))
    if len(texte) < MIN_TEXTE_VISIBLE:
        return None

    ville = (event.get("ville") or "").strip()
    ancrage = " ".join(str(event.get(k) or "") for k in ("title", "lieu", "ville"))
    mots_ancrage, mots_texte = _mots(ancrage), _mots(texte)

    # ② D'ABORD : il est plus précis, donc son motif est plus utile quand les deux tombent.
    mienne = _sans_accents(ville.replace("-", " "))
    autres = {c for c in _communes() if c in _sans_accents(texte) and c != mienne}
    # Une commune n'est nommée que si elle apparaît comme un MOT entier : « Nice » ne doit
    # pas se déclencher sur « Nicermes », ni « Bex » sur « annexe ».
    autres = {c for c in autres
              if re.search(rf"\b{re.escape(c)}\b", _sans_accents(texte))}
    if autres and ville and mienne not in _sans_accents(texte):
        return (f"la description nomme {', '.join(sorted(autres)[:3])} et jamais "
                f"« {ville} », qui est la ville de la fiche")

    # ① ENSUITE : universel, mais plus grossier.
    if mots_ancrage and not (mots_ancrage & mots_texte):
        return ("aucun mot commun entre la description et l'identité de la fiche "
                "(titre, lieu, ville)")
    return None
