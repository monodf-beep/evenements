#!/usr/bin/env python3
"""Fixture : le titre de section « Programme » de `build_post` (scripts/publisher.py)
suit la LANGUE de la fiche — jamais figé en français.

INCIDENT RÉEL, 2026-08-06 : une re-traduction italienne (WP#2174, « Fiera di
Sant'Orso ») a publié un article intégralement en italien SAUF ce titre de section,
resté « Programme ». `translate_article` (scripts/translate_events.py) traduit
chapo/corps/programme, mais jamais ce titre : il était codé en dur dans le rendu
(`build_post`), hors de toute portée du LLM — donc jamais traduit, quelle que soit
la qualité de la traduction elle-même.

Aucun réseau, fonction pure.

Lancer : .venv/bin/python -m tests.test_build_post_langue
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publisher import build_post  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


def _enrich_data(chapo, corps, programme):
    return json.dumps({"article": {"chapo": chapo, "corps": corps, "programme": programme}},
                      ensure_ascii=False)


# ── 1. Fiche française : "Programme" ────────────────────────────────────────────
ev_fr = {
    "title": "Fête du village",
    "article_title": "La fête du village revient cet été",
    "enrich_data": _enrich_data(
        "Un rendez-vous convivial pour toute la famille dans le centre du village.",
        "La commune organise sa traditionnelle fête estivale avec animations et "
        "restauration sur place pour tous les habitants du village et des environs.",
        ["10h : ouverture des stands", "20h : bal populaire"]),
}
_, html = build_post(ev_fr)
_check("fiche FR : titre de section 'Programme'", "<h3>Programme</h3>" in html, html[:200])
_check("fiche FR : pas de 'Programma'", "Programma" not in html)

# ── 2. Fiche italienne (traduction) : "Programma" ───────────────────────────────
ev_it = {
    "title": "Fiera di Sant'Orso 2026 in Valle d'Aosta",
    "article_title": "La Fiera di Sant'Orso si svolge il 30 e 31 gennaio ad Aosta",
    "translation_of": 473, "translated_lang": "it",
    "enrich_data": _enrich_data(
        "Un appuntamento artigianale nel centro storico di Aosta.",
        "Il comune organizza la tradizionale fiera invernale con botteghe di "
        "artigiani provenienti da tutta la Valle d'Aosta, animazioni e stand "
        "gastronomici per tutti gli abitanti e i visitatori della regione.",
        ["30 gennaio: apertura delle bancarelle", "31 gennaio: mercato diurno"]),
}
_, html = build_post(ev_it)
_check("fiche IT : titre de section 'Programma'", "<h3>Programma</h3>" in html, html[:200])
_check("fiche IT : pas de 'Programme' figé en français", "<h3>Programme</h3>" not in html)

# ── 3. Sans programme du tout : aucun des deux titres, comportement inchangé ────
ev_sans_prog = dict(ev_fr)
ev_sans_prog["enrich_data"] = _enrich_data(ev_fr and "Chapô.", "Corps de l'article.", [])
_, html = build_post(ev_sans_prog)
_check("sans programme : ni 'Programme' ni 'Programma'",
      "Programme" not in html and "Programma" not in html, html[:200])

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
