#!/usr/bin/env python3
"""Le vocabulaire interdit — une seule source, et elle vit dans OBSIDIAN, pas ici.

D'OÙ ÇA VIENT. Franck, 2026-08-21, en lisant une page en ligne : « ne jamais mettre
"royaume de Sardaigne" mais mettre "les États de Savoie" ». Ce module a d'abord fait de
`config/vocabulaire_interdit.json` la référence, pour arrêter les cinq copies divergentes
(quatre prompts + la charte). Le 05/09/2026, en reconstituant la voix éditoriale, on a
trouvé que la note « Vocabulaire interdit » vivait DÉJÀ dans Obsidian
(`01-Commun/Vocabulaire interdit.md`, coffre `agenda-sabauda`) avec quatre règles que le
JSON du dépôt ne connaissait pas (« frontière », « langues régionales »,
« francoprovençal », « patois »), et que deux règles du JSON n'avaient jamais été
recopiées côté Obsidian (« royaume de Sardaigne », « Venise des Alpes ») — la dérive que
ce fichier existait pour éviter, simplement déplacée d'un cran.

**Franck, 05/09/2026 : « tout doit être dans Obsidian, les règles ne doivent pas vivre
dans GitHub. »** Ce module lit donc la note en direct sur le VPS, comme `utils/voix.py`
lit la voix éditoriale — MÊME PRINCIPE, appliqué ici au vocabulaire : tu édites la note
dans Obsidian, le prochain enrichissement/traduction en tient compte, sans synchronisation
ni copie à maintenir. `config/vocabulaire_interdit.json` n'existe plus dans ce dépôt.

DIFFÉRENCE ASSUMÉE AVEC `utils/voix.py` : la voix garde un filet versionné dans le dépôt
(« toujours vivante, même sans Obsidian »). Ici, NON — Franck a choisi explicitement, le
05/09, qu'une panne Obsidian laisse le pipeline tourner SANS AUCUN filtre plutôt que de
bloquer ou d'alerter : « continuer sans filtre, silencieusement ». `interdits()` renvoie
alors un tuple vide, exactement comme si aucune règle n'existait. C'est un choix assumé,
pas un oubli : la note elle-même dit « pas de blocage silencieux » pour une occurrence
TROUVÉE (on ne réécrit jamais tout seul) — ça ne concerne pas le cas où la note même est
injoignable, tranché séparément ici.

FORMAT LU. Un tableau Markdown à 3 colonnes (Terme interdit | Pourquoi | Alternative),
celui réellement en place dans la note au 05/09/2026 :

    | **« terme »**[, « variante », ...][ qualificatif] | motif | **remplacement**[ *(IT : remplacement_it)*] |

- Une cellule « Terme interdit » peut lister plusieurs formes entre guillemets français ;
  la première est la clé (`expression`), les suivantes des `variantes`. Un texte hors
  guillemets dans la même cellule (« pour Savoie + Piémont », « en H1 ») est un
  qualificatif informatif, ajouté au motif — il n'est PAS appliqué structurellement (pas
  de détection « seulement dans le H1 ») : la portée fine reste à l'œil humain, comme
  avant pour « transfrontalier ».
- Une cellule « Alternative » ENTIÈREMENT en gras (`**...**`), avec ou sans un
  `*(IT : ...)*` à la suite, est un remplacement DIRECT. Toute autre forme (« Reformuler
  (…) », « Nommer la langue ») est un CONSEIL, pas un remplacement mot à mot :
  `consigne_prompt()` le rend comme une consigne à suivre, `remplacement()` renvoie "".

DEUX TEMPS, ET ILS NE FONT PAS LE MÊME TRAVAIL (inchangé) :
  • `consigne_prompt()` empêche d'écrire l'expression DEMAIN ;
  • `scripts/audit_vocabulaire.py` la trouve dans ce qui est DÉJÀ publié.

ON NE REMPLACE JAMAIS AUTOMATIQUEMENT. Une expression interdite peut être le titre officiel
d'une exposition ou une citation — « Il Regno di Sardegna » sur l'affiche d'un musée n'est
pas notre prose. Le module SIGNALE ; c'est un œil qui tranche, la phrase sous les yeux.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

# Chemin de la note Obsidian sur le VPS, ex. :
#   OBSIDIAN_VOCAB_PATH=/opt/obsidian/config/main/01-Commun/Vocabulaire interdit.md
# Une seule note (pas de couches comme OBSIDIAN_VOIX_PATH) : le vocabulaire interdit n'a
# pas de surcharge par projet, c'est une règle du Commun.
VOCAB_ENV = "OBSIDIAN_VOCAB_PATH"

_RE_GUILLEMETS = re.compile(r"«\s*([^»]+?)\s*»")
_RE_GRAS_SEUL = re.compile(r"^\*\*(.+?)\*\*$")
_RE_IT = re.compile(r"\*?\(\s*IT\s*:\s*([^)]+?)\)\*?\s*$", re.IGNORECASE)


def _sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c)).lower()


def _spec() -> str:
    """Lit OBSIDIAN_VOCAB_PATH à l'APPEL, comme utils/voix.py — robuste quel que soit
    l'ordre de chargement, et sensible à une note éditée entre deux exécutions."""
    load_dotenv(ROOT / ".env")
    return os.getenv(VOCAB_ENV, "").strip()


def _strip_frontmatter(text: str) -> str:
    return re.sub(r"\A\s*---\n.*?\n---\n", "", text, flags=re.S)


def _demarquer(cellule: str) -> str:
    """Retire markdown superficiel (gras) d'une cellule, SANS toucher aux guillemets ni
    au contenu — sert pour le motif, jamais pour l'alternative (qui a besoin du gras
    pour distinguer remplacement direct et conseil)."""
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", cellule).strip()


def _parse_alternative(cellule: str) -> tuple[str, str, str]:
    """(remplacement_fr, remplacement_it, conseil). Les deux premiers sont vides si la
    cellule n'est pas un remplacement direct (pas entièrement en gras) — dans ce cas
    `conseil` porte le texte intégral, nettoyé du gras superficiel."""
    cellule = cellule.strip()
    it = ""
    m_it = _RE_IT.search(cellule)
    if m_it:
        it = _demarquer(m_it.group(1)).strip(" *")
        cellule = cellule[:m_it.start()].strip()
    m_direct = _RE_GRAS_SEUL.match(cellule)
    if m_direct:
        return m_direct.group(1).strip(), it, ""
    return "", it, _demarquer(cellule)


def _parse_terme(cellule: str) -> tuple[str, list[str], str]:
    """(expression, variantes, qualificatif). `expression` = la première forme entre
    guillemets ; `variantes` = les suivantes ; `qualificatif` = ce qui reste hors
    guillemets et hors gras (« pour Savoie + Piémont », « en H1 »)."""
    formes = [f.strip() for f in _RE_GUILLEMETS.findall(cellule)]
    reste = _RE_GUILLEMETS.sub("", cellule)
    # Le gras qui entourait le terme entre guillemets devient «**»+«**» une fois le terme
    # retiré (ex. "**« x »**" → "****") : de purs astérisques résiduels, jamais un vrai
    # gras à préserver ici — on les enlève avant _demarquer, sinon "****" (aucun caractère
    # entre les deux paires) ne matche pas le motif et le motif du terme affiche un
    # « (****) » vide dès qu'il n'y a aucun qualificatif hors guillemets.
    reste = reste.replace("*", "")
    reste = _demarquer(reste).strip(" ,.")
    if not formes:
        return "", [], reste
    return formes[0], formes[1:], reste


def _lignes_tableau(texte: str) -> list[list[str]]:
    """Cellules de chaque ligne DE DONNÉES d'un tableau Markdown à 3 colonnes minimum
    (ignore l'en-tête et la ligne de séparation ---|---|---)."""
    lignes = []
    vu_separateur = False
    for ligne in texte.splitlines():
        ligne = ligne.strip()
        if not ligne.startswith("|"):
            vu_separateur = False
            continue
        cellules = [c.strip() for c in ligne.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cellules if c):
            vu_separateur = True
            continue
        if vu_separateur and len(cellules) >= 3:
            lignes.append(cellules)
    return lignes


def _lire_note() -> str:
    chemin = _spec()
    if not chemin:
        return ""
    try:
        return Path(chemin).read_text(encoding="utf-8")
    except OSError:
        return ""


def interdits() -> tuple[dict, ...]:
    """Les règles telles qu'écrites DANS LA NOTE OBSIDIAN, à l'instant de l'appel. Pas de
    cache : une note éditée doit être vue au run suivant sans redémarrer quoi que ce
    soit. Note absente/injoignable/vide → () — le pipeline tourne sans filtre (choix de
    Franck, 05/09/2026), jamais une exception qui arrêterait la rédaction."""
    brut = _lire_note()
    if not brut:
        return ()
    brut = _strip_frontmatter(brut)
    out = []
    for cellules in _lignes_tableau(brut):
        expression, variantes, qualificatif = _parse_terme(cellules[0])
        if not expression:
            continue
        motif = _demarquer(cellules[1])
        if qualificatif:
            motif = f"{motif} ({qualificatif})" if motif else qualificatif
        rf, ri, conseil = _parse_alternative(cellules[2])
        out.append({"expression": expression, "variantes": variantes,
                    "remplacement_fr": rf, "remplacement_it": ri,
                    "_motif": motif, "_conseil": conseil})
    return tuple(out)


def _formes(entree: dict) -> list[str]:
    """L'expression et ses variantes, normalisées. La normalisation compte : « États »
    s'écrit aussi « Etats », et l'italien arrive par sa propre forme entre guillemets."""
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
    """Ce qu'il faut écrire à la place, "" si l'expression est à supprimer/reformuler
    librement (pas de remplacement direct — voir `_conseil` de `interdits()` pour le
    détail dans ce cas)."""
    for e in interdits():
        if e["expression"] == expression:
            return (e.get(f"remplacement_{langue}") or "").strip()
    return ""


def consigne_prompt(langue: str = "fr") -> str:
    """La consigne à insérer dans un prompt de rédaction. UNE seule source (la note
    Obsidian), quatre usages (les 4 prompts de rédaction).

    Rendue en une ligne par expression : avec le remplacement direct quand il existe
    (« ne dis pas X, dis Y » se suit mieux qu'une interdiction nue) ; avec le CONSEIL de
    la note quand l'alternative est une reformulation plutôt qu'un mot à mot ; en dernier
    recours une interdiction simple, pour ne jamais laisser le rédacteur sans consigne.
    """
    lignes = []
    for e in interdits():
        rempl = (e.get(f"remplacement_{langue}") or "").strip()
        conseil = (e.get("_conseil") or "").strip()
        if rempl:
            lignes.append(f'- Ne dis JAMAIS « {e["expression"]} » : écris « {rempl} ».')
        elif conseil:
            lignes.append(f'- N\'emploie JAMAIS « {e["expression"]} » : {conseil}')
        else:
            lignes.append(f'- N\'emploie JAMAIS « {e["expression"]} », ni ses variantes.')
    return "\n".join(lignes)
