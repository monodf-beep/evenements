#!/usr/bin/env python3
"""Test du verrou « radar = DÉTECTION seule » (utils/radar.py).

⚠️ TEST SUR FIXTURE, PAS SUR LA BASE. `data/events.db` est hors dépôt Git (.gitignore)
et absent de cet environnement : les cas ci-dessous sont RECONSTRUITS à la main à
partir de fiches réellement observées (titres et numéros WP cités dans l'audit du
2026-08-02). Les champs reproduisent ce que le pipeline écrit vraiment :
`source_type`/`source_name` par scripts/scraper_events.py l.395-405, `url_officiel`
et `enrich_data.source` par scripts/enrich.py l.1387-1405 et l.1496-1500.

Ce que le test doit prouver, DANS LES DEUX SENS :
  • il BLOQUE les fiches de presse (faits divers du Dauphiné, comptes-rendus,
    revues de presse) qui sont parties en ligne comme des événements ;
  • il LAISSE PASSER un vrai événement détecté par radar puis résolu vers sa page
    officielle — sinon la règle tuerait l'utilité même du radar.

Lancer : .venv/bin/python -m tests.test_radar_gate   (ou python3 tests/test_radar_gate.py)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import radar  # noqa: E402


def _ev(**kw) -> dict:
    base = {"id": 0, "title": "", "source_type": "institutionnel", "source_name": "",
            "url_source": "", "url_officiel": "", "enrich_data": "", "translation_of": 0,
            "wp_post_id_as": 0}
    base.update(kw)
    return base


def _enrich(officielle: bool, pages: list[str] | None = None,
            sources: list[str] | None = None) -> str:
    """Reproduit le JSON écrit par enrich.py (clé `source`, plus la bibliographie
    `sources` rédigée par l'agent — volontairement ignorée par le verrou)."""
    return json.dumps({"source": {"officielle": officielle, "pages": pages or [],
                                  "web": False, "dossier": "absent"},
                       "sources": sources or []}, ensure_ascii=False)


# ─────────────────────────── CAS À BLOQUER (presse pure) ────────────────────────────
A_BLOQUER = [
    # Les deux fiches nommément citées dans l'audit : partie en ligne sous WP#1097 et
    # WP#1105. Titres d'articles du Dauphiné, aucune page officielle jamais résolue.
    _ev(id=1097, title="Chambéry. Cirque, danse, théâtre, déambulations : ce qu'il faut savoir",
        source_type="radar", source_name="Le Dauphiné - Savoie (édition locale)",
        url_source="https://www.ledauphine.com/culture-loisirs/2026/07/12/chambery-cirque-danse"),
    _ev(id=1105, title="Annecy. Défilé, concert, feu d'artifice, animations",
        source_type="radar", source_name="Le Dauphiné - Haute-Savoie (édition locale)",
        url_source="https://www.ledauphine.com/culture-loisirs/2026/07/13/annecy-defile-concert"),
    # Faits divers de l'édition locale ENTIÈRE (le flux n'est pas une rubrique culture).
    _ev(id=2001, title="Deux morts dans une collision frontale sur la RD1090",
        source_type="radar", source_name="Le Dauphiné - Savoie (édition locale)",
        url_source="https://www.ledauphine.com/faits-divers/2026/07/20/collision"),
    _ev(id=2002, title="Un incendie ravage un hangar agricole à Ugine",
        source_type="radar", source_name="Le Dauphiné - Savoie (édition locale)"),
    _ev(id=2003, title="Ugine : arrêté municipal réglementant le stationnement en centre-ville",
        source_type="radar", source_name="Le Dauphiné - Savoie (édition locale)"),
    # Revue de presse / actualité institutionnelle, détectées par Google News.
    _ev(id=2004, title="Rassegna stampa: il calendario della settimana",
        source_type="radar", source_name="Google News - Cultura Torino/Piemonte (radar)",
        url_source="https://news.google.com/rss/articles/CBMi..."),
    _ev(id=2005, title="Interreg ALCOTRA : signature d'une convention transfrontalière",
        source_type="radar", source_name="Google News - Culture Savoie/Haute-Savoie (radar)"),
    # Fiche radar ENRICHIE mais dont la résolution a échoué : enrich a écrit
    # `officielle: false` et aucune page. C'est le cas le plus courant.
    _ev(id=2006, title="Turin : la semaine culturelle en dix rendez-vous",
        source_type="radar", source_name="GuidaTorino (guide)",
        url_source="https://www.guidatorino.com/eventi-torino-weekend/",
        enrich_data=_enrich(False, [])),
    # PIÈGE 1 : le LLM cite un site officiel dans sa bibliographie, mais aucune page
    # n'a été LUE. Le verrou ne doit pas se laisser ouvrir par une URL non vérifiée.
    _ev(id=2007, title="Aoste : le programme de l'été", source_type="radar",
        source_name="Gazzetta Matin - Appuntamenti (agenda)",
        enrich_data=_enrich(False, [], sources=["https://www.comune.aosta.it/eventi"])),
    # PIÈGE 2 : « url_officiel » qui pointe en fait sur le journal lui-même.
    _ev(id=2008, title="Nice : trois expositions à voir ce week-end", source_type="radar",
        source_name="NiceRendezVous - Culture (guide)",
        url_officiel="https://www.nicerendezvous.com/"),
    # PIÈGE 3 : « url_officiel » sur une plateforme générique (page Facebook).
    _ev(id=2009, title="Chambéry : la fête de la musique en centre-ville", source_type="radar",
        source_name="Le Dauphiné - Savoie (édition locale)",
        url_officiel="https://www.facebook.com/events/123456789/"),
    # Fiche ancienne sans source_type mais dont le nom porte « (radar) » — seul signal
    # disponible sur une partie du stock (même test que publisher_as._is_radar).
    _ev(id=2010, title="Exposition photo à Annecy", source_type="",
        source_name="Google News - Culture Savoie/Haute-Savoie (radar)"),
]

# ──────────────────── CAS À LAISSER PASSER (le radar a fait son travail) ────────────
A_PASSER = [
    # LE CAS QUI JUSTIFIE LA RÈGLE TELLE QUELLE : vrai événement DÉTECTÉ par un radar,
    # puis RÉSOLU vers la page officielle de l'organisateur → publiable.
    _ev(id=3001, title="Musilac 2026 — Aix-les-Bains", source_type="radar",
        source_name="Le Dauphiné - Savoie (édition locale)",
        url_source="https://www.ledauphine.com/culture-loisirs/2026/05/02/musilac-2026",
        url_officiel="https://www.musilac.com/",
        enrich_data=_enrich(True, ["https://www.musilac.com/",
                                   "https://www.musilac.com/presse/"])),
    # Résolution tracée uniquement dans enrich_data (fiche enrichie avant que
    # url_officiel ne soit mémorisée systématiquement).
    _ev(id=3002, title="Castello di Rivoli — mostra 2026", source_type="radar",
        source_name="Quotidiano Piemontese - Eventi (agenda)",
        enrich_data=_enrich(True, ["https://www.castellodirivoli.org/mostre/"])),
    # `officielle: true` sans liste de pages (matière officielle lue via dossier de presse).
    _ev(id=3003, title="Festival del Cinema — Aosta", source_type="radar",
        source_name="Aostaoggi - Eventi (agenda)", enrich_data=_enrich(True, [])),
    # TRADUCTION italienne d'une fiche radar résolue : elle hérite de source_type mais
    # PAS de url_officiel (translate_events l.476-486) → on juge sur l'original.
    _ev(id=3004, title="Musilac 2026 — Aix-les-Bains", source_type="radar",
        source_name="Le Dauphiné - Savoie (édition locale)", translation_of=3001),
    # NON-RADAR : le verrou ne doit jamais toucher une source officielle, même sans
    # url_officiel (le flux du lieu EST la source officielle).
    _ev(id=3005, title="Saison 2026-2027 de l'Espace Malraux", source_type="officielle",
        source_name="Malraux scène nationale Chambéry"),
    _ev(id=3006, title="Fête de la Saint-Vincent", source_type="tourisme",
        source_name="Office de Tourisme du Lac d'Annecy"),
    # Contre-épreuve du calibrage d'utils/eventness : « Tour de l'Avenir 2026 -
    # Strambino » (WP#6380, en ligne, vrai événement) déclenche le motif « voirie /
    # mobilité » d'eventness. Le verrou radar, lui, ne lit PAS le texte : cette fiche
    # vient d'une source officielle, donc elle passe. C'est précisément pour ça que la
    # règle porte sur la PROVENANCE et pas sur le vocabulaire.
    _ev(id=6380, title="Tour de l'Avenir 2026 - Strambino : plan de circulation et "
                       "fermetures de routes", source_type="institution",
        source_name="Comune di Strambino"),
]


def main() -> int:
    parent_index = {e["id"]: e for e in A_PASSER + A_BLOQUER}
    echecs = []
    print("=" * 78)
    print("VERROU RADAR — test sur FIXTURE (data/events.db absent du dépôt)")
    print("=" * 78)

    print("\n### Doivent être BLOQUÉS (presse / non résolus)")
    for ev in A_BLOQUER:
        parent = parent_index.get(ev.get("translation_of") or 0)
        reason = radar.publication_block_reason(ev, parent)
        ok = reason is not None
        print(f"  {'OK  ' if ok else 'RATÉ'} [{ev['id']}] {(ev['title'] or '')[:56]:56} "
              f"→ {'RETENU' if ok else 'PUBLIÉ (!)'}")
        if not ok:
            echecs.append(("devrait être bloqué", ev))

    print("\n### Doivent PASSER (radar résolu, ou source non-radar)")
    for ev in A_PASSER:
        parent = parent_index.get(ev.get("translation_of") or 0)
        reason = radar.publication_block_reason(ev, parent)
        ok = reason is None
        ancre = radar.official_anchor(ev) or (radar.official_anchor(parent) if parent else "")
        print(f"  {'OK  ' if ok else 'RATÉ'} [{ev['id']}] {(ev['title'] or '')[:56]:56} "
              f"→ {'publiable' if ok else 'BLOQUÉ (!)'}"
              + (f"  · ancre : {ancre[:48]}" if ok and ancre else ""))
        if not ok:
            echecs.append(("devrait passer", ev))

    print("\n### Domaines radar lus depuis config/sources.txt")
    print("  " + ", ".join(sorted(radar.radar_hosts())))

    print()
    if echecs:
        print(f"ÉCHEC : {len(echecs)} cas incorrect(s)")
        for quoi, ev in echecs:
            print(f"  - [{ev['id']}] {quoi} : {ev['title'][:60]}")
        return 1
    print(f"SUCCÈS : {len(A_BLOQUER)} bloqué(s), {len(A_PASSER)} laissé(s) passer, 0 erreur.")
    return 0


def test_verrou_radar() -> None:
    """Point d'entrée pytest (la suite du dépôt tourne sous pytest) — même contenu que
    le script autonome, qui reste lançable sans pytest sur le VPS."""
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
