#!/usr/bin/env python3
"""Réglages du pipeline pilotés depuis le back-office (page /reglages).

Deux boutons, avec conséquences expliquées côté UI :
  • ai_profile  : « eco » (Haiku, ~3× moins cher) | « qualite » (Sonnet, meilleure rédaction)
  • enrich_mode : « off » (pas d'article, la fiche garde la description de la source)
                | « court » (article concis, sans recherche web — pour Agenda Sabauda)
                | « long »  (article complet + recherche web — pour Cultura Sabauda, cher)

Persisté en JSON dans data/ (propre au VPS), lu à la fois par l'app (écrit) et par les
scripts du cron (évaluateur, enrichissement). Valeurs par défaut = les moins chères.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / "data" / "pipeline_settings.json"

_DEFAULTS = {"ai_profile": "eco", "enrich_mode": "court"}
_PROFILES = ("eco", "qualite")
_ENRICH_MODES = ("off", "court", "long")
_MODEL_ECO = "claude-haiku-4-5"
_MODEL_QUAL = "claude-sonnet-5"
COURT_MAX_TOKENS = 1800


def load() -> dict:
    d = dict(_DEFAULTS)
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            if raw.get("ai_profile") in _PROFILES:
                d["ai_profile"] = raw["ai_profile"]
            if raw.get("enrich_mode") in _ENRICH_MODES:
                d["enrich_mode"] = raw["enrich_mode"]
    except (OSError, ValueError):
        pass
    return d


def save(patch: dict) -> dict:
    d = load()
    if patch.get("ai_profile") in _PROFILES:
        d["ai_profile"] = patch["ai_profile"]
    if patch.get("enrich_mode") in _ENRICH_MODES:
        d["enrich_mode"] = patch["enrich_mode"]
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass
    return d


def ai_profile() -> str:
    return load()["ai_profile"]


def model() -> str:
    """Modèle à utiliser (évaluation + enrichissement) selon le profil."""
    return _MODEL_ECO if ai_profile() == "eco" else _MODEL_QUAL


def enrich_mode() -> str:
    return load()["enrich_mode"]


def enrich_enabled() -> bool:
    return enrich_mode() != "off"
