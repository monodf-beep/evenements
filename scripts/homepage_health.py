#!/usr/bin/env python3
"""Vérifie que les sections mises en avant de la home (agendasabauda.eu) NE SONT PAS VIDES.

Incident vécu (2026-07-31) : « À la une » affichait « Aucun événement pour le moment »
suite à un trou d'éligibilité (as_enrich_status non câblé) — découvert par hasard, en
lisant une capture d'écran envoyée par Franck. Rien ne surveillait ça en continu.

DÉTECTION PAR COMPTAGE DE LIENS (pas d'API dédiée côté WordPress) : on repère les
MARQUEURS STRUCTURELS que le gabarit pose dans le document — l'`id=` de chaque section,
et pour « Ça vaut le déplacement » la classe de ses cartes — puis on compte les fiches
DISTINCTES dans la fenêtre qui suit.

⚠️ PAS le titre affiché : le 2026-08-13 ce script a crié « quatre sections vides » sur
une home qui servait cinquante fiches, parce que « À la une » n'apparaît dans le HTML
que dans le blob de configuration Elementor, à 130 000 caractères des cartes, et que
« Ça vaut le déplacement » n'y figure nulle part. On ne peut pas déduire le HTML de ce
qu'on voit à l'écran — ni la casse, ni le texte lui-même. Zéro coût API, zéro JS exécuté (pas besoin : les cartes
sont dans le HTML servi, confirmé en pratique le 2026-08-01).

Usage (VPS, cron quotidien) :
    .venv/bin/python -m scripts.homepage_health
"""
from __future__ import annotations
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import slack
from utils import pipeline_status

log = get_logger("homepage_health")

# (titre affiché, seuil minimum de cartes en dessous duquel on alerte)
# ⚠️ La CASSE des titres affichés à l'écran vient du CSS (`text-transform: uppercase`),
# PAS du HTML : la home sert « Les 7 prochains jours » et « Nouveautés sur Agenda
# Sabauda ». Écrits ici en capitales (relevés sur la capture d'écran), ils ne
# matchaient RIEN — la section était comptée 0 et une alerte rouge serait partie sur
# Slack tous les jours à 13h pour une home parfaitement saine. Tout le matching est
# donc insensible à la casse (cf. re.IGNORECASE dans _section_counts) : on ne peut pas
# déduire le HTML de ce qu'on voit à l'écran.
# « Ça vaut le déplacement » ajoutée le 2026-08-04, LE JOUR où sa clé de tri a changé
# (mu-plugin cs-cvld-dynamique.php, hors dépôt — c'est bien pourquoi il faut la
# surveiller d'ici : ce fichier n'a ni revue ni historique, et s'il casse, il retombe sur
# un placeholder qui nomme un événement terminé le 24/07 et un post supprimé). Seuil à 2 :
# la section vise une carte par territoire (4), mais le vivier italien peut légitimement
# être plus maigre — sous 2, ce n'est plus une pénurie, c'est une panne.
# ══ ON N'ANCRE PLUS SUR LE TITRE AFFICHÉ ══════════════════════════════════════════════
#
# Le 2026-08-13 à 13h, ce script a crié « À la une : 0 carte · En évidence : 0 · Les 7
# prochains jours : 0 · Ça vaut le déplacement : 0 » sur une home qui servait CINQUANTE
# liens de fiches. Vérifié en téléchargeant la page : dix fiches sous « À la une », six
# sous le week-end, quatre sous le jour, trois sous « En évidence ».
#
# La cause : les titres cherchés n'existent PAS dans le HTML rendu. Leurs seules
# occurrences (« À la une » cinq fois, entre les positions 23 886 et 47 924) sont dans le
# blob de configuration Elementor en tête de page — à 130 000 caractères des cartes, donc
# hors de toute fenêtre. Et « Ça vaut le déplacement » n'y figurait pas du tout, alors
# que la section porte dix-neuf cartes.
#
# Le commentaire ci-dessus disait déjà « on ne peut pas déduire le HTML de ce qu'on voit
# à l'écran » — la leçon avait été tirée pour la CASSE des titres, et pas poussée jusqu'à
# sa conclusion : le titre lui-même peut n'être nulle part. On ancre donc sur les
# marqueurs STRUCTURELS du thème (`id=` des sections, classe des cartes), qui sont ce que
# le gabarit pose réellement dans le document.
#
# DEUX FAMILLES DE MARQUEURS, ET LES MÉLANGER CASSE LE COMPTAGE (constaté en corrigeant,
# le 2026-08-13) : une section ancrée par un `id=` occupe un bloc continu, tandis qu'une
# classe de CARTE (`cs-cvld-card`) apparaît dix-neuf fois éparpillées dans la page. Jeter
# les deux dans la même liste de bornes fragmentait les fenêtres des sections à `id` —
# « À la une » retombait de dix cartes à six, « Les 7 prochains jours » à zéro. On les
# traite donc séparément, chacune avec la méthode qui convient à sa forme.
#
# (libellé lisible, `id=` de la section, seuil d'alerte)
_SECTIONS = [("À la une", "ala-une", 1),
             ("Le week-end", "weekend", 1),
             ("Les 7 prochains jours", "jour", 1),
             ("En évidence", "evidence", 1),
             ("L'agenda à venir", "venir", 1)]
# Bornes SUPPLÉMENTAIRES : pas surveillées pour elles-mêmes, mais elles ferment la fenêtre
# de la section qui les précède. Sans elles, la dernière section surveillée avalerait
# toutes les cartes des rubriques par catégorie qui suivent.
_ANCRES_BORNES = ["evidence-bottom", "venir-bottom", "cat-concerts", "cat-expositions",
                  "cat-gastronomie"]
# « Ça vaut le déplacement » n'a pas d'`id` de section : elle se reconnaît à la classe de
# ses cartes. Seuil à 2 — la section vise une carte par territoire (4), mais le vivier
# italien peut légitimement être plus maigre ; sous 2, ce n'est plus une pénurie, c'est
# une panne du mu-plugin cs-cvld-dynamique.php (hors dépôt, sans revue ni historique).
_CARTES = [("Ça vaut le déplacement", "cs-cvld-card", 2)]
_PORTEE_CARTE = 3000   # caractères après une carte où chercher son lien de fiche
# Les sections sont espacées d'environ 13 000 à 26 000 caractères sur la home réelle
# (relevé du 2026-08-13). La fenêtre doit pouvoir couvrir la plus large, sinon la
# dernière section de la page serait tronquée et comptée basse ; les autres restent
# bornées par le marqueur suivant, qui arrive toujours avant.
_WINDOW = 40000


def _section_counts(html: str) -> dict[str, int | None]:
    """Titre → nombre de cartes de la section, ou None si le titre est INTROUVABLE.

    ⚠️ CE COMPTEUR ADDITIONNAIT LES OCCURRENCES, ET C'ÉTAIT FAUX (corrigé le 2026-08-13
    après une alerte rouge sur une home parfaitement saine). Un titre de section apparaît
    PLUSIEURS FOIS dans la page — dans le menu, dans un `aria-label`, dans une classe CSS,
    puis enfin sur la vraie section. Relevé sur la home du 13/08 : « À la une » cinq fois,
    « En évidence » trois fois. Comme chaque fenêtre est bornée à l'occurrence SUIVANTE,
    on regardait cinq fenêtres de quelques centaines de caractères, toutes vides — et on
    additionnait cinq zéros. La page servait cinquante liens de fiches.

    On prend donc le MAXIMUM sur les occurrences, pas la somme : la question posée est
    « existe-t-il un endroit de la page où cette section est peuplée ? ». Une occurrence
    de menu rend 0 et ne masque plus la vraie.

    Et un titre ABSENT n'est pas une section vide : `None` le distingue de `0`. « Ça vaut
    le déplacement » ne figurait plus du tout dans le HTML du 13/08 — annoncer « 0 carte »
    aurait envoyé chercher un vivier maigre là où c'est la section elle-même qui a
    disparu du thème. Deux problèmes, deux gestes.
    """
    counts: dict[str, int | None] = {lib: None for lib, _a, _s in _SECTIONS + _CARTES}

    # ① Sections ancrées par un `id=` : fenêtre bornée par l'ancre suivante, quelle
    #    qu'elle soit (surveillée ou simple borne).
    toutes = [(lib, anc) for lib, anc, _s in _SECTIONS] + \
             [(None, anc) for anc in _ANCRES_BORNES]
    positions = sorted((m.start(), lib) for lib, anc in toutes
                       for m in re.finditer(rf'id="{re.escape(anc)}"', html, re.IGNORECASE))
    for i, (pos, lib) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else pos + _WINDOW
        end = min(end, pos + _WINDOW)
        if lib is None:
            continue
        # Fiches DISTINCTES : une carte porte le même lien deux fois (l'image et le
        # titre), et compter les occurrences gonflerait chaque section du double.
        n = len(set(re.findall(r"/evenement/[a-z0-9-]+/", html[pos:end])))
        actuel = counts.get(lib)
        counts[lib] = n if actuel is None else max(actuel, n)

    # ② Sections reconnaissables à la CLASSE de leurs cartes : on réunit les fiches
    #    trouvées près de chaque carte. Pas de fenêtre unique — les cartes d'une même
    #    section peuvent être dispersées dans le document (constaté : de la position
    #    77 681 à 286 186 pour « Ça vaut le déplacement »).
    for lib, classe, _s in _CARTES:
        occ = [m.start() for m in re.finditer(re.escape(classe), html, re.IGNORECASE)]
        if not occ:
            continue                       # reste None : la classe a disparu du thème
        fiches: set[str] = set()
        for p in occ:
            fiches |= set(re.findall(r"/evenement/[a-z0-9-]+/", html[p:p + _PORTEE_CARTE]))
        counts[lib] = len(fiches)
    return counts


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    base = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
    try:
        resp = requests.get(base + "/", timeout=30,
                            headers={"User-Agent": "Mozilla/5.0 (homepage_health check)"})
        resp.raise_for_status()
        html = resp.text
    except requests.RequestException as exc:
        msg = f"🔴 *Home Agenda Sabauda injoignable* : {exc}"
        log.error(msg)
        slack.notify(msg)
        pipeline_status.record_run("homepage_health", error=1, summary=msg)
        return 1

    counts = _section_counts(html)
    empty, absentes = [], []
    for title, _marqueur, floor in _SECTIONS + _CARTES:
        n = counts.get(title)
        if n is None:
            log.warning("Section « %s » : TITRE INTROUVABLE dans la page", title)
            absentes.append(title)
        else:
            log.info("Section « %s » : %d carte(s) détectée(s)", title, n)
            if n < floor:
                empty.append((title, n))

    if empty or absentes:
        lines = ["🔴 *Home Agenda Sabauda* :"]
        if empty:
            lines.append("Section(s) vide(s) ou quasi :")
            lines += [f"• « {t} » : {n} carte(s)" for t, n in empty]
        if absentes:
            # DEUX PROBLÈMES, DEUX GESTES. Un titre absent du HTML n'est pas une section
            # vide : c'est le thème qui a changé, ou la section qui a été renommée. Dire
            # « 0 carte » enverrait chercher un vivier maigre là où il n'y a plus de
            # section du tout — et c'est le mu-plugin, hors dépôt, qu'il faut regarder.
            lines.append("Section(s) dont le TITRE n'existe plus dans la page — ce n'est "
                         "pas un vivier vide, c'est le thème ou le mu-plugin qui a changé :")
            lines += [f"• « {t} » introuvable" for t in absentes]
        lines.append(base + "/")
        msg = "\n".join(lines)
        log.warning(msg)
        slack.notify(msg)
        pipeline_status.record_run("homepage_health", warn=len(empty), summary=msg)
        return 1

    summary = "; ".join(f"{t}={counts.get(t)}" for t, _m, _s in _SECTIONS + _CARTES)
    log.info("Home OK : %s", summary)
    pipeline_status.record_run("homepage_health", ok=1, summary=summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
