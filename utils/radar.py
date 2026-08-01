#!/usr/bin/env python3
"""Contrat « radar = DÉTECTION seule » — verrou de PUBLICATION.

POURQUOI CE MODULE EXISTE (le bug réel, pas la théorie)
-------------------------------------------------------
`config/sources.txt` déclare le tier radar depuis toujours, mot pour mot :

    radar = presse / Google News (DÉTECTION seule, jamais crédité/lié)

… mais RIEN n'appliquait la première moitié de la phrase. `source_type == 'radar'`
n'était testé que pour ne pas CRÉDITER ni LIER le journal (scripts/publisher_as.py
l.148-150 et 228-230, scripts/newsletter.py l.97-131, scripts/visuals.py l.56-57).
Autrement dit : une fiche née d'un article du Dauphiné était évaluée, rédigée et
PUBLIÉE comme un événement autonome — simplement sans lien vers le journal. Le
contrat protégeait le journal, pas l'agenda.

Cas réels partis en ligne : « Chambéry. Cirque, danse, théâtre, déambulations : ce
qu'il faut savoir » (WP#1097), « Annecy. Défilé, concert, feu d'artifice,
animations » (WP#1105), plus tout un fond de faits divers (collisions mortelles,
incendies, conseils municipaux filmés), de revues de presse et d'arrêtés municipaux.

L'INTENTION ÉDITORIALE, elle, est claire : un radar sert à DÉTECTER qu'un événement
existe, puis à aller chercher sa PAGE OFFICIELLE. Sans matière officielle atteinte,
il n'y a pas d'événement à publier — il n'y a qu'un article de presse recopié.

CE QUE CE MODULE NE FAIT PAS
----------------------------
Il ne lit PAS le contenu et ne juge PAS si le texte « ressemble » à un événement :
c'est le travail de `utils/eventness.py`, volontairement laissé en simple
AVERTISSEMENT au stade publication (cf. scripts/batch_report.py, arbitrage du
2026-08-02 : « Tour de l'Avenir 2026 - Strambino », course cycliste bien réelle et
déjà en ligne sous WP#6380, déclenche son motif « voirie / mobilité » — une course
annonce légitimement des fermetures de routes). Durcir un filtre de vocabulaire,
c'est arbitrer entre faux positifs et faux négatifs sur du texte.

Ici, on ne regarde que deux faits VÉRIFIABLES, jamais du vocabulaire :
  1. d'où vient la fiche (tier de la source, écrit à la collecte) ;
  2. a-t-on RÉUSSI à remonter à une page officielle (trace laissée par enrich.py) ?

Aucun faux positif de langue n'est donc possible : un vrai événement détecté par
radar PASSE dès que sa page officielle a été atteinte — ce que le pipeline sait
déjà faire (scripts/enrich.py, fetch_official_material → url_officiel).
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

_ROOT = Path(__file__).resolve().parent.parent
_SOURCES_FILE = _ROOT / "config" / "sources.txt"
_NON_INSTITUTIONAL_FILE = _ROOT / "config" / "non_institutional_sources.txt"

# Plateformes génériques : jamais la preuve d'une source officielle (une page
# Facebook d'événement n'est pas le site de l'organisateur). Volontairement RECOPIÉ
# de scripts/enrich.py:_NOT_OFFICIAL plutôt qu'importé : `scripts.enrich` tire
# anthropic + requests au chargement, et ce module doit rester importable par
# n'importe quel script d'audit en lecture seule, sans dépendance ni clé d'API.
_GENERIC_HOSTS = (
    "facebook.", "fb.me", "fb.com", "instagram.", "twitter.", "x.com", "youtube.",
    "youtu.be", "tiktok.", "linkedin.", "google.", "goo.gl", "wikipedia.", "billetweb.",
    "weezevent.", "fnac", "ticketmaster.", "digitick.", "eventbrite.", "helloasso.",
    "yurplan.", "shotgun.", "dice.fm", "tripadvisor.", "spotify.", "deezer.", "apple.",
    "agendaculturel.", "mapstr.", "waze.", "instagr.am", "bit.ly",
)

_radar_hosts_cache: "set | None" = None
_blocked_hosts_cache: "set | None" = None


def _host(url: str) -> str:
    try:
        return urlparse(url or "").netloc.lower().removeprefix("www.")
    except ValueError:
        return ""


def radar_hosts() -> set[str]:
    """Domaines des sources déclarées `radar` dans config/sources.txt.

    Lu du fichier, pas codé en dur : ajouter un flux radar suffit à l'étendre. Sert
    de filet à la question « la page dite officielle n'est-elle pas, en fait, le
    journal lui-même ? » — `scripts/enrich.py:_NOT_OFFICIAL` ne connaît PAS
    ledauphine.com ni nicerendezvous.com (il ne liste que les plateformes), donc
    rien n'empêchait structurellement de mémoriser un domaine de presse comme
    `url_officiel`."""
    global _radar_hosts_cache
    if _radar_hosts_cache is None:
        hosts: set[str] = set()
        if _SOURCES_FILE.exists():
            for raw in _SOURCES_FILE.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or ";" not in line:
                    continue
                parts = [p.strip() for p in line.split(";")]
                if len(parts) > 3 and parts[3].lower() == "radar":
                    h = _host(parts[0])
                    if h:
                        hosts.add(h)
        _radar_hosts_cache = hosts
    return _radar_hosts_cache


def _blocked_hosts() -> set[str]:
    """Domaines déjà déclarés « jamais crédités » (config/non_institutional_sources.txt,
    charte §8) : guides tiers, presse. Une page de ces domaines ne prouve rien."""
    global _blocked_hosts_cache
    if _blocked_hosts_cache is None:
        out: set[str] = set()
        if _NON_INSTITUTIONAL_FILE.exists():
            for raw in _NON_INSTITUTIONAL_FILE.read_text(encoding="utf-8").splitlines():
                line = raw.strip().lower()
                if line and not line.startswith("#"):
                    out.add(line.lstrip("."))
        _blocked_hosts_cache = out
    return _blocked_hosts_cache


def is_radar(event: dict) -> bool:
    """Fiche d'ORIGINE radar ? Même test que scripts/publisher_as.py:_is_radar (et que
    newsletter/visuals/purge_uncompletable) : le tier écrit à la collecte, plus le
    libellé « (radar) » du nom de source — certaines fiches anciennes n'ont que le
    second. Les traductions héritent des deux (scripts/translate_events.py l.476-486)."""
    return ((event.get("source_type") or "").strip().lower() == "radar"
            or "(radar)" in (event.get("source_name") or ""))


def _is_official_host(host: str) -> bool:
    """Un domaine peut-il servir de PREUVE de résolution officielle ?"""
    if not host:
        return False
    if any(g in host for g in _GENERIC_HOSTS):
        return False
    if any(host == r or host.endswith("." + r) for r in radar_hosts()):
        return False
    return not any(host == b or host.endswith("." + b) for b in _blocked_hosts())


def _enrich_data(event: dict) -> dict:
    raw = event.get("enrich_data")
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "") or {}
    except (TypeError, ValueError):
        return {}


def official_anchor(event: dict) -> str:
    """Preuve qu'on a bien remonté à une source officielle, ou "" si aucune.

    Les trois signaux sont TOUS produits par le résolveur DÉTERMINISTE de
    scripts/enrich.py (pages réellement téléchargées), jamais par le LLM :

      1. `url_officiel` — mémorisée par enrich.py l.1387-1405 quand la résolution a
         payé, ET seulement si les pages lues mentionnent vraiment le titre.
      2. `enrich_data.source.pages` — les URLs officielles effectivement lues au
         moment de la rédaction (enrich.py l.1496-1500).
      3. `enrich_data.source.officielle` — le booléen `has_official` d'enrich.py
         l.1383 : « [PAGE PRESSE/PROGRAMME » ou « [DOSSIER » présent dans la matière.

    On n'utilise VOLONTAIREMENT PAS `enrich_data.sources` (la bibliographie écrite
    par l'agent) : ce sont des URLs CITÉES, pas des URLs LUES. Les accepter
    reviendrait à laisser le LLM lever lui-même le verrou en nommant un site
    officiel qu'il n'a jamais ouvert — exactement le mode de défaillance que
    filter_official_sources() attrape déjà après coup (cas guidatorino.com).
    """
    u = (event.get("url_officiel") or "").strip()
    if u and _is_official_host(_host(u)):
        return u
    data = _enrich_data(event)
    src = data.get("source") or {}
    for page in (src.get("pages") or []):
        if isinstance(page, str) and _is_official_host(_host(page)):
            return page
    if src.get("officielle") is True:
        return "matière officielle lue (enrich_data.source.officielle)"
    return ""


def publication_block_reason(event: dict, parent: dict | None = None) -> str | None:
    """Raison de NE PAS publier cette fiche, ou None si elle peut partir.

    `parent` : pour une TRADUCTION (translation_of), la fiche fille hérite de
    source_type et de source_name mais PAS de `url_officiel`
    (scripts/translate_events.py l.476-486 ne copie pas la colonne). Sans cet
    argument, la traduction italienne d'un événement radar parfaitement résolu
    paraîtrait non résolue. On accepte donc l'ancre de l'original.
    """
    if not is_radar(event):
        return None
    if official_anchor(event):
        return None
    if parent and official_anchor(parent):
        return None
    src = (event.get("source_name") or "source radar").strip()
    return (f"origine RADAR ({src}) sans page officielle résolue — le radar sert à "
            f"DÉTECTER, pas à publier (config/sources.txt, tier radar)")
