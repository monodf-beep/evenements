#!/usr/bin/env python3
"""Fixture : TOUT appel à `publish_to_as` publie la source de l'original sur une
traduction — pas seulement celui de `publish_batch_as`.

Incident du 23-24/09/2026 : `refresh_deplacement` (10h55) republiait les jumelles
italiennes des Giornate avec `as_source_officielle_url` VIDE — il appelle publish_to_as
directement, et l'héritage ne vivait que dans publish_batch_as. 21 pages italiennes à
venir en noindex et hors sitemap (cs-completude).

Rouge sur la version d'avant (vérifié : `heriter_source_traduction` n'existait pas dans
publisher_as, et `_build_payload` recevait `translated:1:it`).

Cas qui doivent PASSER près de la frontière : une traduction qui a SA PROPRE source http
la garde (celle de l'original ne l'écrase pas) ; un original non traduit est intact ; une
base illisible ne bloque pas la publication. Et l'événement de l'APPELANT n'est pas
modifié (certains le réécrivent en base, où `translated:` est l'ancre UNIQUE de la paire).

Aucun réseau. Lancer : .venv/bin/python -m tests.test_source_traduction_tous_chemins
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp())
db = tmp / "events.db"
os.environ["DB_PATH"] = str(db)
for k in ("WP_AS_URL", "WP_AS_USER", "WP_AS_APP_PASSWORD"):
    os.environ.setdefault(k, "x")

import scripts.publisher_as as pa  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    print(("OK    " if cond else "ÉCHEC ") + label + ("" if cond else f"  {detail}"))
    echecs += 0 if cond else 1


c = sqlite3.connect(db)
c.execute("CREATE TABLE events_raw (id INTEGER PRIMARY KEY, title TEXT, url_officiel TEXT "
          "DEFAULT '', url_source TEXT DEFAULT '', source_type TEXT DEFAULT '', source_name "
          "TEXT DEFAULT '', translation_of INT, enrich_data TEXT)")
c.execute("INSERT INTO events_raw (id, title, url_source) VALUES "
          "(1, 'Aperitivo in vigna', 'https://cultura.gov.it/evento/aperitivo-in-vigna-GEP2026')")
c.commit()
c.close()

vus = []


class _Stop(Exception):
    pass


def _capture(event, **kw):
    vus.append(dict(event))
    raise _Stop


pa._build_payload = _capture


def _publier(ev):
    try:
        pa.publish_to_as(ev, skip_media=True)
    except _Stop:
        pass
    return vus[-1]


# ── Le chemin de refresh_deplacement : appel direct, traduction au marqueur ─────
jumelle = {"id": 2, "title": "Aperitivo", "translation_of": 1, "url_source": "translated:1:it"}
envoye = _publier(jumelle)
_check("appel direct : la traduction part avec la source de l'original",
       envoye.get("url_source") == "https://cultura.gov.it/evento/aperitivo-in-vigna-GEP2026",
       envoye.get("url_source"))
_check("… et la méta calculée n'est plus vide",
       pa._source_publiable(envoye, pa._is_radar(envoye)).startswith("https://cultura.gov.it"))
_check("l'événement de l'appelant n'est PAS modifié", jumelle["url_source"] == "translated:1:it")

# ── Frontière : ce qui doit passer intact ────────────────────────────────────────
propre = {"id": 3, "translation_of": 1, "url_source": "https://autre.example/page"}
_check("une traduction qui a sa propre source http la garde",
       _publier(propre)["url_source"] == "https://autre.example/page")
original = {"id": 1, "url_source": "https://cultura.gov.it/x"}
_check("un original n'est pas touché", _publier(original)["url_source"] == "https://cultura.gov.it/x")

# ── Base illisible : la publication continue, comme avant ────────────────────────
os.environ["DB_PATH"] = str(tmp / "absente" / "events.db")
e = _publier({"id": 4, "translation_of": 1, "url_source": "translated:1:it"})
_check("base illisible : pas d'exception, fiche laissée telle quelle",
       e["url_source"] == "translated:1:it")

# ── publish_batch_as délègue au même calcul (un seul calcul, pas deux) ───────────
import scripts.publish_batch_as as pb  # noqa: E402
_check("publish_batch_as utilise le calcul de publisher_as",
       pb.heriter_source_traduction is pa.heriter_source_traduction)

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)")
    sys.exit(1)
print("Tout passe.")
