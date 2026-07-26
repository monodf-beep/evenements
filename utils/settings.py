#!/usr/bin/env python3
"""Réglages du pipeline pilotés depuis le back-office (page /reglages).

Boutons, avec conséquences expliquées côté UI :
  • ai_profile  : « eco » (Haiku, ~3× moins cher) | « qualite » (Sonnet, meilleure rédaction)
  • enrich_mode : « off » (pas d'article, la fiche garde la description de la source)
                | « auto »  (le SCORE décide : ≥7 → long, sinon court — RECOMMANDÉ)
                | « court » (force l'article concis, sans recherche web — Agenda Sabauda)
                | « long »  (force l'article complet + recherche web — Cultura Sabauda, cher)
  • social_caption_auto  : réécriture LLM des légendes réseaux (voix Enrico) — off par
    défaut (bouton manuel « 🪄 Réécrire » dans /reseaux). Si ON, /reseaux réécrit tout
    seul les meilleurs événements de chaque territoire n'ayant pas encore de légende
    IA, plafonné à social_caption_limit PAR TERRITOIRE PAR LANGUE — jamais 100
    appels/jour, le volume reste celui de la cadence réseaux (quelques posts/semaine).

Persisté en JSON dans data/ (propre au VPS), lu à la fois par l'app (écrit) et par les
scripts du cron (évaluateur, enrichissement). Valeurs par défaut = les moins chères.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / "data" / "pipeline_settings.json"

_DEFAULTS = {"ai_profile": "eco", "enrich_mode": "auto",
             "social_caption_auto": False, "social_caption_limit": 3}
_PROFILES = ("eco", "qualite")
_ENRICH_MODES = ("off", "auto", "court", "long")
_MODEL_ECO = "claude-haiku-4-5"
_MODEL_QUAL = "claude-sonnet-5"
COURT_MAX_TOKENS = 1800
SOCIAL_CAPTION_LIMIT_MAX = 10  # garde-fou dur, même si quelqu'un tape un grand nombre


def load() -> dict:
    d = dict(_DEFAULTS)
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            if raw.get("ai_profile") in _PROFILES:
                d["ai_profile"] = raw["ai_profile"]
            if raw.get("enrich_mode") in _ENRICH_MODES:
                d["enrich_mode"] = raw["enrich_mode"]
            d["social_caption_auto"] = bool(raw.get("social_caption_auto", False))
            try:
                lim = int(raw.get("social_caption_limit", d["social_caption_limit"]))
                d["social_caption_limit"] = max(0, min(lim, SOCIAL_CAPTION_LIMIT_MAX))
            except (TypeError, ValueError):
                pass
    except (OSError, ValueError):
        pass
    return d


def save(patch: dict) -> dict:
    d = load()
    if patch.get("ai_profile") in _PROFILES:
        d["ai_profile"] = patch["ai_profile"]
    if patch.get("enrich_mode") in _ENRICH_MODES:
        d["enrich_mode"] = patch["enrich_mode"]
    if "social_caption_auto" in patch:
        d["social_caption_auto"] = bool(patch["social_caption_auto"])
    if "social_caption_limit" in patch:
        try:
            d["social_caption_limit"] = max(0, min(int(patch["social_caption_limit"]),
                                                    SOCIAL_CAPTION_LIMIT_MAX))
        except (TypeError, ValueError):
            pass
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass
    return d


def social_caption_auto() -> bool:
    return load()["social_caption_auto"]


def social_caption_limit() -> int:
    return load()["social_caption_limit"]


def ai_profile() -> str:
    return load()["ai_profile"]


def model() -> str:
    """Modèle à utiliser (évaluation + enrichissement) selon le profil."""
    return _MODEL_ECO if ai_profile() == "eco" else _MODEL_QUAL


def model_eco() -> str:
    """Modèle économique (Haiku) — articles COURTS / catalogue."""
    return _MODEL_ECO


def model_qualite() -> str:
    """Modèle qualité (Sonnet) — articles LONGS / phares (structure + gras)."""
    return _MODEL_QUAL


def enrich_mode() -> str:
    return load()["enrich_mode"]


def enrich_enabled() -> bool:
    return enrich_mode() != "off"
