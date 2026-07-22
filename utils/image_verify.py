#!/usr/bin/env python3
"""RÈGLES + AGENT de vérification des images d'événements — un seul endroit.

Deux défenses complémentaires contre les visuels hors-sujet (bandeaux, pubs,
sliders, images sans rapport) :

  1. RÈGLES déterministes (gratuites, toujours actives) — looks_parasitic() :
     rejette une URL qui correspond à un motif d'habillage connu
     (config/blocked_image_patterns.txt). Rapide, extensible sans code.

  2. AGENT vision (payant, ciblé) — verify_relevance() : un LLM regarde l'image et
     dit si elle correspond VRAIMENT à l'événement. C'est le vrai garde-fou de
     pertinence — le seul capable de dire « ce ruban vert est une campagne don
     d'organes, pas une reconstitution historique ».

Utilisé par la chaîne de résolution (scripts.visuals.resolve_image) et par l'agent
web de dernier recours (scripts.images_web) — plus de logique de vérification
dupliquée.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_PATTERNS_FILE = ROOT / "config" / "blocked_image_patterns.txt"
_OK_MIME = ("image/jpeg", "image/png", "image/webp", "image/gif")

_patterns_cache: "list[str] | None" = None


def load_blocked_patterns() -> list[str]:
    """Motifs d'URL parasites (config/blocked_image_patterns.txt), en minuscules."""
    global _patterns_cache
    if _patterns_cache is None:
        pats: list[str] = []
        try:
            for line in _PATTERNS_FILE.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s and not s.startswith("#"):
                    pats.append(s.lower())
        except OSError:
            pass
        _patterns_cache = pats
    return _patterns_cache


def looks_parasitic(url: str, patterns: "list[str] | None" = None) -> bool:
    """Vrai si l'URL correspond à un motif d'habillage/parasite connu (déterministe)."""
    if not url:
        return False
    low = url.lower()
    for p in (patterns if patterns is not None else load_blocked_patterns()):
        if p in low:
            return True
    return False


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", text or "")).strip()


def verify_relevance(img_bytes: bytes, mime: str, event: dict, client, model: str,
                     subject: str = "") -> bool:
    """AGENT VISION : l'image correspond-elle vraiment à l'événement ? True/False.

    Refuse explicitement les bandeaux/pubs/logos/captures/affiches-tout-texte et les
    images sans rapport. Tolérant en cas d'échec technique (renvoie True) SEULEMENT si
    l'appel plante — l'appelant décide alors ; ici on préfère ne pas bloquer sur une
    panne réseau. Un refus DE CONTENU (l'image ne colle pas) renvoie bien False."""
    if not img_bytes or mime not in _OK_MIME or client is None:
        return True  # rien à vérifier / pas de client → on laisse passer (règles déjà filtrées)
    b64 = base64.standard_b64encode(img_bytes).decode("ascii")
    prompt = (
        "Voici une image candidate pour illustrer un ÉVÉNEMENT CULTUREL sur un média "
        "public. Dis si elle est PERTINENTE et publiable pour CET événement précis.\n"
        f"Titre : {_clean(event.get('article_title') or event.get('title'))}\n"
        f"Lieu / ville : {_clean(event.get('lieu'))} {_clean(event.get('ville'))}\n"
        f"Catégorie : {event.get('llm_categorie') or ''}\n"
        + (f"Sujet attendu : {subject}\n" if subject else "")
        + "\nREFUSE (ok=false) si l'image est : un bandeau ou une bannière de campagne "
        "(don d'organes, sécurité routière, climat…), une publicité, un logo, une "
        "capture d'écran, une affiche pleine de texte illisible, un visuel d'habillage "
        "de site (slider, en-tête), une image de très mauvaise qualité, ou tout "
        "simplement SANS RAPPORT avec l'événement. ACCEPTE (ok=true) une vraie photo "
        "du lieu, de l'artiste, du thème, ou une affiche propre et lisible de "
        "l'événement.\n"
        'Réponds en JSON STRICT : {"ok": true|false, "raison": "…"}'
    )
    try:
        msg = client.messages.create(
            model=model, max_tokens=150,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                {"type": "text", "text": prompt}]}])
    except Exception:
        return True  # panne technique : ne bloque pas (les règles déterministes ont déjà filtré)
    try:
        from utils import usage
        usage.record_message(model, msg, label="image_verify")
    except Exception:
        pass
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text").strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return True
    try:
        data = json.loads(m.group())
    except (ValueError, TypeError):
        return True
    return bool(data.get("ok"))
