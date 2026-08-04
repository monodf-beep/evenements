#!/usr/bin/env python3
"""Vérifie que les sections mises en avant de la home (agendasabauda.eu) NE SONT PAS VIDES.

Incident vécu (2026-07-31) : « À la une » affichait « Aucun événement pour le moment »
suite à un trou d'éligibilité (as_enrich_status non câblé) — découvert par hasard, en
lisant une capture d'écran envoyée par Franck. Rien ne surveillait ça en continu.

DÉTECTION PAR COMPTAGE DE LIENS (pas d'API dédiée côté WordPress) : on cherche le titre
de section dans le HTML brut de la home, puis on compte les liens `/evenement/` dans la
fenêtre qui suit (jusqu'au prochain titre de section, ou une limite de caractères). C'est
fragile aux changements de thème (pas une vraie API), mais ça attrape exactement le cas
vécu ; à durcir si le thème change. Zéro coût API, zéro JS exécuté (pas besoin : les cartes
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
_SECTIONS = [("À la une", 1), ("En évidence", 1), ("Les 7 prochains jours", 1),
             ("Ça vaut le déplacement", 2)]
# Titres supplémentaires, PAS surveillés pour eux-mêmes, mais nécessaires pour borner la
# fenêtre d'une section surveillée qui les précède directement (sinon on compte les cartes
# de la section SUIVANTE par débordement — vécu : "LES 7 PROCHAINS JOURS" est directement
# suivie de "NOUVEAUTÉS SUR AGENDA SABAUDA", jamais vide, qui aurait masqué le trou).
_BOUNDARY_ONLY = ["Nouveautés sur Agenda Sabauda", "L'agenda à venir", "Et ailleurs"]
_WINDOW = 12000  # caractères scrutés après le titre, avant le titre de section suivant


def _section_counts(html: str) -> dict[str, int]:
    counts = {}
    all_titles = [t for t, _ in _SECTIONS] + _BOUNDARY_ONLY
    # positions de TOUS les titres connus (surveillés + bornes), pour borner chaque
    # fenêtre au prochain titre quel qu'il soit (évite de compter les cartes d'une AUTRE
    # section par débordement).
    positions = sorted(
        (m.start(), title) for title in all_titles
        for m in re.finditer(re.escape(title), html, re.IGNORECASE))
    watched = {t for t, _ in _SECTIONS}
    for i, (pos, title) in enumerate(positions):
        if title not in watched:
            continue
        end = positions[i + 1][0] if i + 1 < len(positions) else pos + _WINDOW
        end = min(end, pos + _WINDOW)
        window = html[pos:end]
        counts[title] = counts.get(title, 0) + len(re.findall(r"/evenement/[a-z0-9-]+/?", window))
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
    empty = []
    for title, floor in _SECTIONS:
        n = counts.get(title, 0)
        log.info("Section « %s » : %d carte(s) détectée(s)", title, n)
        if n < floor:
            empty.append((title, n))

    if empty:
        lines = [f"🔴 *Home Agenda Sabauda* — section(s) vide(s) ou quasi :"]
        lines += [f"• « {t} » : {n} carte(s)" for t, n in empty]
        lines.append(base + "/")
        msg = "\n".join(lines)
        log.warning(msg)
        slack.notify(msg)
        pipeline_status.record_run("homepage_health", warn=len(empty), summary=msg)
        return 1

    summary = "; ".join(f"{t}={counts.get(t, 0)}" for t, _ in _SECTIONS)
    log.info("Home OK : %s", summary)
    pipeline_status.record_run("homepage_health", ok=1, summary=summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
