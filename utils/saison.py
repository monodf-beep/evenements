#!/usr/bin/env python3
"""Le juste temps — quand une fiche COMPLÈTE peut partir en publication.

Proposition de Franck (2026-08-04), validée le 2026-08-05 (fenêtre par défaut :
90 jours) : « on connaît déjà des événements de Noël mais ce n'est pas le moment
de les afficher. » Aucun garde-fou d'horizon n'existait à la publication —
`publish_batch_as` triait par date croissante mais sans borne haute, donc un
marché de Noël complet partait en ligne en août dès que la file des événements
plus proches était vide. Voir docs/TEMPS_FORTS.md pour la doctrine complète.

PRINCIPE : une fenêtre de PUBLICATION, jamais un état. Une fiche trop lointaine
reste dans son statut RETENU (evaluated/published_sub…) — rien n'est écrit, rien
n'est rejeté. Le calendrier la rouvre tout seul le lendemain en recomparant les
dates : aucun état terminal, aucun script de réouverture à brancher
(docs/ETATS_TERMINAUX.md — la réponse aux quatre questions est justement
« le calendrier »).
"""
from __future__ import annotations
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_TEMPS_FORTS_FILE = ROOT / "config" / "temps_forts.json"

# Fenêtre par défaut : validée par Franck le 2026-08-05 (proposition initiale de
# docs/TEMPS_FORTS.md — « assez pour préparer un week-end ou des vacances, assez
# court pour que l'agenda garde une saison »). Réglable par env var pour un test
# ponctuel sans toucher au code.
FENETRE_DEFAUT_JOURS = int(os.getenv("TEMPS_FORTS_FENETRE_DEFAUT", "90"))


def _charger_temps_forts(path: Path | None = None) -> list[dict]:
    p = path or _TEMPS_FORTS_FILE
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, TypeError):
        return []
    return data.get("temps_forts", []) if isinstance(data, dict) else []


def _strip_accents(text: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", text)
                  if unicodedata.category(c) != "Mn")


def temps_fort_concerne(event: dict, temps_forts: list[dict] | None = None) -> dict | None:
    """Le temps fort NOMMÉ dont un mot-clé apparaît dans le titre OU la description
    de `event`, sinon None. Renvoie l'entrée entière (nom, fenetre_jours…) — pas
    juste un booléen, pour que l'appelant puisse motiver sa décision."""
    temps_forts = temps_forts if temps_forts is not None else _charger_temps_forts()
    if not temps_forts:
        return None
    texte = _strip_accents(
        f"{event.get('title', '')} {event.get('description', '')}").lower()
    for tf in temps_forts:
        for mc in tf.get("mots_cles", []):
            if _strip_accents(mc).lower() in texte:
                return tf
    return None


def fenetre_publication_jours(event: dict, temps_forts: list[dict] | None = None) -> int:
    """Nombre de jours, avant le début de l'événement, où sa publication est
    autorisée. 90 par défaut ; plus pour un temps fort nommé (config/temps_forts.json)
    qui se réserve à l'avance (billetterie, hébergement)."""
    tf = temps_fort_concerne(event, temps_forts)
    return int(tf["fenetre_jours"]) if tf else FENETRE_DEFAUT_JOURS
