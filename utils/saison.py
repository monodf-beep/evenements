#!/usr/bin/env python3
"""Le juste temps — quand une fiche COMPLÈTE peut partir en publication.

Franck (2026-08-04) : « on connaît déjà des événements de Noël mais ce n'est pas
le moment de les afficher. » Voir docs/TEMPS_FORTS.md pour la doctrine complète.

CORRIGÉ le 2026-08-05, même jour — première version fausse. J'avais transformé
« Noël ne doit pas s'afficher en août » en une fenêtre GÉNÉRALE de 90 jours
s'appliquant à TOUT événement daté. Faux : le problème n'est pas la distance dans
le temps, c'est le DÉCALAGE THÉMATIQUE — un marché de Noël en pleine canicule
jure, un concert de mars annoncé en septembre ne jure de rien. Franck : « je n'ai
pas demandé les 90 jours pour Nice Jazz, Carnaval de Nice… ça peut être plus
loin » — ces grands rendez-vous n'ont besoin d'AUCUNE fenêtre, pas d'une plus
large, la réservation anticipée leur sert.

PRINCIPE CORRIGÉ : AUCUN plafond par défaut. SEULS les temps forts thématiques
NOMMÉS (config/temps_forts.json — Noël, Halloween pour l'instant, les deux seuls
exemples confirmés par Franck) ont une fenêtre, propre à chacun. Tout le reste se
publie dès que prêt, comme avant le 2026-08-04.

MÊME DOCTRINE D'ÉTAT que la version précédente : une fenêtre de PUBLICATION,
jamais un état. Une fiche hors fenêtre reste dans son statut RETENU — rien n'est
écrit, rien n'est rejeté. Le calendrier la rouvre tout seul en approchant
(docs/ETATS_TERMINAUX.md — qui rouvre : le calendrier).
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_TEMPS_FORTS_FILE = ROOT / "config" / "temps_forts.json"


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


def fenetre_publication_jours(event: dict, temps_forts: list[dict] | None = None) -> int | None:
    """Nombre de jours, avant le début de l'événement, où sa publication est
    autorisée — SEULEMENT si l'événement correspond à un temps fort thématique
    NOMMÉ (config/temps_forts.json). None = AUCUNE fenêtre, publiable dès que
    prêt (le cas de la grande majorité des événements, y compris les grands
    festivals à billetterie : Musilac, Nice Jazz, Carnaval de Nice n'ont pas de
    problème de décalage saisonnier, ils n'ont donc pas d'entrée ici)."""
    tf = temps_fort_concerne(event, temps_forts)
    return int(tf["fenetre_jours"]) if tf else None
