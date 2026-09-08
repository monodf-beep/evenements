#!/usr/bin/env python3
"""Fixture : `_retranslate_one` republie TEXTE SEUL (skip_media=True) — une
re-traduction ne doit jamais toucher à l'image.

INCIDENT RÉEL, 2026-08-06 : `--retranslate --apply 473` a republié la fiche 3483
avec `url_image` toujours en base (la bannière de repli), écrasant une vraie photo
que Franck venait de poser à la main côté WordPress — jamais remontée dans
`events_raw.url_image`. `publish_to_as(upd)` était appelé SANS `skip_media`, donc
avec son défaut `False` : il retéléversait l'image à chaque re-traduction, alors
que seul le texte (titre/description/article) doit changer.

⚠️ Aucun réseau : translate_title_desc et publish_to_as sont monkey-patchées.

Lancer : .venv/bin/python -m tests.test_retranslate_skip_media
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.translate_events as te  # noqa: E402

te.DB_PATH = tmp

conn = sqlite3.connect(tmp)
init_db(conn)
conn.execute(
    "INSERT INTO events_raw (id, title, description, url_source, url_image, "
    "territoire, statut, date_event_start, date_event_end) VALUES "
    "(473, 'La Foire de Saint-Ours 2027', 'Un rendez-vous artisanal à Aoste.', "
    "'https://a.fr/473', 'https://a.fr/vraie-photo.jpg', 'Vallee-Aoste', "
    "'evaluated', '2027-01-30', '2027-01-31')")
conn.execute(
    "INSERT INTO events_raw (id, title, description, url_source, url_image, "
    "translation_of, translated_lang, wp_post_id_as, territoire, statut, "
    "date_event_start, date_event_end) VALUES "
    "(3483, 'La Fiera di Sant''Orso 2027', 'Un appuntamento artigianale ad Aosta.', "
    "'translated:473:it', 'https://a.fr/vieille-banniere-fallback.png', 473, 'it', "
    "2174, 'Vallee-Aoste', 'evaluated', '2027-01-30', '2027-01-31')")
conn.commit()
conn.close()

appels_publish = []
te.publish_to_as = lambda ev, **kw: (appels_publish.append(kw) or (2174, "https://x/", "https://x/img.jpg"))
te.translate_title_desc = lambda *a, **k: {
    "title": "Fiera di Sant'Orso 2026 in Valle d'Aosta",
    "description": "Un evento culturale ad Aosta, con artigianato locale.",
}


class _Args:
    apply = True
    model = "modele-test"


tw = {"id": 3483, "translation_of": 473, "translated_lang": "it"}
resultat = te._retranslate_one(tw, _Args(), client=object(), voix="")

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


_check("résultat = 'done'", resultat == "done", f"obtenu {resultat!r}")
_check("publish_to_as appelé une fois", len(appels_publish) == 1, str(appels_publish))
if appels_publish:
    _check("skip_media=True passé à publish_to_as",
          appels_publish[0].get("skip_media") is True, str(appels_publish[0]))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
