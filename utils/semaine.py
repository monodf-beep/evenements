#!/usr/bin/env python3
"""File de travail « Cette semaine » — logique PARTAGÉE entre la page backoffice
(app.py::semaine()) et le rappel Slack (scripts/semaine_reminder.py). Un seul
endroit pour la liste des tâches : le compteur envoyé sur Slack doit toujours
correspondre exactement à ce que la page affiche, jamais une copie qui dérive.

Pas d'import de app.py ici (coûteux : démarre une app Flask + migrations au
chargement du module) — ce module ne dépend que de sqlite3 + utils/scripts.
"""
from __future__ import annotations

import hashlib

from scripts.publisher import build_post
from utils import completeness as comp
from utils import organizers


def text_hash(event: dict) -> str:
    _, content = build_post(event)
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def tasks(conn) -> list[dict]:
    """Photo à valider + texte à relire, pour chaque événement retenu, + un candidat
    de handle Instagram organisateur à confirmer/refuser, + une finition Instagram
    manuelle en attente — triés par date d'événement la plus proche (le plus urgent
    à relire en premier). Les candidats organisateur n'ont pas de date propre : ils
    passent en tête (traités vite, ils débloquent des mentions pour PLUSIEURS
    événements futurs d'un coup)."""
    q = (f"SELECT * FROM events_raw WHERE statut IN "
         f"({','.join('?' * len(comp.RETAINED_STATUTS))}) AND duplicate_of IS NULL "
         "ORDER BY COALESCE(NULLIF(date_event_start,''),'9999-12-31') ASC")
    rows = [dict(r) for r in conn.execute(q, comp.RETAINED_STATUTS).fetchall()]
    out = [{"kind": "organisateur", "row": row} for row in organizers.pending_candidates(conn)]
    for e in rows:
        if comp.has_real_image(e) and (e.get("image_reviewed_url") or "") != (e.get("url_image") or ""):
            out.append({"kind": "photo", "event": e})
        if (e.get("text_reviewed_hash") or "") != text_hash(e):
            out.append({"kind": "texte", "event": e})
        # Finition Instagram manuelle (choisie sur /reseaux/publish) : reste dans la
        # file tant que Franck n'a pas cliqué « C'est posté » — pas de comparaison au
        # contenu (rien à comparer, la case n'est pas ré-évaluée automatiquement).
        if e.get("ig_manual_mode") and not e.get("ig_manual_done_at"):
            out.append({"kind": "instagram-manuel", "event": e})
    return out
