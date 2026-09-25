#!/usr/bin/env python3
"""Fixture : une image partagée n'est pas l'identité d'un événement.

2026-09-23, pages /plaisirs-de-culture-vallee-d-aoste/ et /it/plaisirs-de-culture-valle-
d-aosta/ : 15 cartes d'un côté, 26 de l'autre, et PAS UNE fiche traduite. Le dédoublonnage
de translate_events (« même affiche = même événement bilingue ») prenait pour une jumelle
toute fiche de l'autre langue portant la même image — or l'affiche du festival était sur
19 fiches, et les visuels de secours sont partagés par construction. Le refus renvoyait
`skip` sans rien marquer : rejoué chaque jour, à l'identique (règle 3).

Ce qui doit rester vrai, près de la frontière : une VRAIE paire (une fiche française, sa
jumelle italienne native, même affiche propre) est toujours reconnue.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_traduction_affiche_partagee
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.translate_events import index_affiches, image_identifiante  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


FR = {"title": "Une visite guidée du château pour les familles",
      "description": "Le château ouvre ses portes aux enfants et aux parents pour une visite"}
IT = {"title": "Una visita guidata al castello per le famiglie",
      "description": "Il castello apre le sue porte ai bambini e ai genitori per una visita"}
AFFICHE = "https://valledaostaheritage.com/wp-content/uploads/2026/07/Plaisirs-de-Culture-2026.webp"
SECOURS = "https://agendasabauda.eu/wp-content/uploads/2026/07/fallback-vallee-d-aoste-expositions-patrimoine.png"
PAIRE = "https://opera-nice.org/affiche-orlando.jpg"


def r(base, img, src="og"):
    return {**base, "url_image": img, "image_source": src}


rows = ([r(IT, AFFICHE, "")] * 13 + [r(FR, AFFICHE, "")] * 6      # l'affiche du festival
        + [r(IT, SECOURS, "banner"), r(IT, SECOURS, "banner")]      # deux visuels de secours
        + [r(FR, PAIRE), r(IT, PAIRE)]                               # une vraie paire
        + [r(FR, "https://x.fr/seule.jpg")])                         # une affiche seule
idx = index_affiches(rows)

_check("l'affiche d'un festival sur 19 fiches n'identifie rien",
       not image_identifiante(AFFICHE, "", idx), str(idx.get("_partagees")))
_check("un visuel de secours n'identifie rien (même porté par une seule fiche)",
       not image_identifiante(SECOURS, "banner", idx)
       and not image_identifiante(SECOURS.replace("expositions", "concerts"), "", idx))
_check("… donc aucune fiche ne se croit déjà traduite à cause d'eux",
       AFFICHE not in idx["it"] and AFFICHE not in idx["fr"] and SECOURS not in idx["it"])
_check("FRONTIÈRE : la vraie paire FR/IT est toujours reconnue",
       image_identifiante(PAIRE, "og", idx) and PAIRE in idx["it"] and PAIRE in idx["fr"],
       str(idx))
_check("une affiche portée par une seule fiche reste une identité",
       image_identifiante("https://x.fr/seule.jpg", "og", idx) and "https://x.fr/seule.jpg" in idx["fr"])
_check("deux fiches de la MÊME langue sur une image : elle n'identifie plus rien",
       not image_identifiante(AFFICHE, "og", index_affiches([r(FR, AFFICHE), r(FR, AFFICHE)])))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
