#!/usr/bin/env python3
"""Fixture : `scripts.audit_substance_published` classe les fiches PUBLIÉES en
« sous le plancher » / « bande maigre » / publiable, et repère celles jamais
enrichies — le cas Saint-Ours/WP#2174 trouvé le 2026-08-06 (article_title vide,
publiée quand même avec la seule description auto-générée).

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau : `build_post` est monkey-
patchée (comme tests/test_portillon_substance.py) sur le contenu factice `_html`.

Lancer : .venv/bin/python -m tests.test_audit_substance_published
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
import scripts.audit_substance_published as audit  # noqa: E402

audit.DB_PATH = tmp


def _article(mots: int) -> str:
    corps = " ".join(f"mot{i}" for i in range(mots))
    return f"<p>{corps}</p>"


def _build_post_factice(ev):
    return ev.get("title", ""), ev.get("_html", "")


audit.build_post = _build_post_factice

conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
init_db(conn)

# id, title, url_source, wp_post_id_as, article_title, mots
FICHES = [
    (1, "Saint-Ours 2026, jamais enrichie", "https://a.fr/1", 999, None, 40),
    (2, "Publiée avec article court", "https://a.fr/2", 998, "Article court", 60),
    (3, "Bande maigre, publiable", "https://a.fr/3", 997, "Article moyen", 180),
    (4, "Bien fournie", "https://a.fr/4", 996, "Bel article", 400),
    (5, "Maigre mais PAS publiée (wp_post_id_as vide)", "https://a.fr/5", None, None, 20),
]
for eid, title, url_source, wp_id, article_title, mots in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, wp_post_id_as, article_title, "
        "duplicate_of) VALUES (?,?,?,?,?, NULL)",
        (eid, title, url_source, wp_id, article_title))
conn.commit()
conn.close()

# `_html` n'est pas une colonne SQL — on l'ajoute après coup dans le dict que le script
# lit, en patchant `build_post` pour lire un mapping id → mots au lieu de la colonne.
_MOTS = {eid: mots for eid, *_r, mots in FICHES}


def _build_post_par_id(ev):
    return ev.get("title", ""), _article(_MOTS[ev["id"]])


audit.build_post = _build_post_par_id

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


rc = audit.main(["--ids"])
_check("rc=0 (lecture seule, jamais d'échec)", rc == 0)

# Ré-exécute la logique de comptage directement pour vérifier les paniers (le script
# imprime, il ne renvoie rien — on rejoue son calcul avec les mêmes fonctions).
import sqlite3 as _sq  # noqa: E402
conn = _sq.connect(tmp)
conn.row_factory = _sq.Row
rows = [dict(r) for r in conn.execute(
    "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 AND duplicate_of IS NULL")]
conn.close()

from utils import substance  # noqa: E402
plancher = substance.plancher()
sous_plancher = [ev for ev in rows if substance.mots_publies(ev, audit.build_post) < plancher]
bande_maigre = [ev for ev in rows
                if plancher <= substance.mots_publies(ev, audit.build_post) < substance.BANDE_MAIGRE]

ids_sous = sorted(ev["id"] for ev in sous_plancher)
ids_bande = sorted(ev["id"] for ev in bande_maigre)

_check("sous le plancher : id 1 et 2 (40 et 60 mots < 120), pas 5 (pas publiée)",
       ids_sous == [1, 2], str(ids_sous))
_check("bande maigre : id 3 (180 mots)", ids_bande == [3], str(ids_bande))
_check("id 4 (400 mots) n'est dans aucun des deux paniers",
       4 not in ids_sous and 4 not in ids_bande)

# ── PANIER 4 : PUBLIÉE SANS ARTICLE RÉDIGÉ ───────────────────────────────────────────
# LE CAS QUI COMPTE EST CELUI QUI PASSE TOUT LE RESTE. `publisher.build_post` a un repli
# « article non enrichi → description brute » : une fiche dont la source a écrit trois
# cents mots franchit le plancher de substance sans qu'une ligne soit de nous. Ce script
# mesurait une longueur, pas une provenance — il ne la voyait donc pas, et le panel de
# lecteurs non plus, puisqu'il lit enrich_data.
import json as _json  # noqa: E402
_c = _sq.connect(tmp)
_c.execute("INSERT INTO events_raw (id, title, url_source, wp_post_id_as, article_title, "
           "enrich_data, duplicate_of) VALUES (?,?,?,?,?,?, NULL)",
           (6, "Longue mais jamais rédigée", "https://a.fr/6", 995, None, ""))
_c.execute("UPDATE events_raw SET enrich_data=? WHERE id=?",
           (_json.dumps({"article": {"corps": "Un vrai article rédigé chez nous."}}), 4))
_c.commit(); _c.close()

_check("une fiche SANS corps rédigé est vue, même longue",
       audit._article_de({"enrich_data": ""}) == {})
_check("   et une fiche AVEC corps ne l'est pas",
       (audit._article_de({"enrich_data": _json.dumps(
           {"article": {"corps": "texte"}})}) or {}).get("corps") == "texte")
_check("un enrich_data ABÎMÉ ne fait pas tomber l'audit — il compte comme non rédigé",
       audit._article_de({"enrich_data": "{pas du json"}) == {})

import io as _io, contextlib as _ctx  # noqa: E402
_buf = _io.StringIO()
with _ctx.redirect_stdout(_buf):
    audit.main([])
_sortie = _buf.getvalue()
_check("le panier 4 est affiché", "PUBLIÉES SANS ARTICLE RÉDIGÉ" in _sortie, _sortie[-400:])
_check("   et il dit d'où vient le texte affiché à la place",
       "DESCRIPTION BRUTE" in _sortie)
_check("   et qu'elles échappent aussi au panel", "invisibles de nous" in _sortie)

jamais_enrichies = [ev["id"] for ev in sous_plancher if not (ev.get("article_title") or "").strip()]
_check("« jamais enrichie » repère bien id=1 (article_title vide), pas id=2",
       jamais_enrichies == [1], str(jamais_enrichies))

# ── Frontière passé / à-venir (ajoutée le 2026-08-11) ───────────────────────────
# Ce script annonçait « 108 fiches sous le plancher » sans distinguer le passé de
# l'à-venir, et ce chiffre a servi trois jours à décrire l'état du site. Il y en avait
# SEIZE encore devant nous. Réparer un article dont l'événement a eu lieu coûte 0,33 $
# et ne sert personne (règle 5). Les cas ci-dessous prennent les DEUX côtés de la
# frontière, y compris ceux qui doivent PASSER.
print("\n──── frontière passé / à-venir ────")
AUJ = "2026-08-11"
FRONTIERE = [
    ({"date_event_end": "2026-12-01"},                     True,  "à venir"),
    ({"date_event_end": "2026-05-30"},                     False, "terminé"),
    ({"date_event_end": AUJ},                              True,  "se termine aujourd'hui"),
    ({"date_event_start": "2026-06-01", "date_event_end": "2026-09-20"}, True,
     "en cours (mai→septembre) : c'est la FIN qui décide"),
    ({},                                                   True,
     "sans date : donnée manquante, pas événement fini"),
    ({"date_event_end": "2026-05-30", "recurring": 1},     True,
     "récurrent : pas de date unique, jamais passé"),
]
for ev, attendu, motif in FRONTIERE:
    _check(f"{'gardé ' if attendu else 'écarté'} — {motif}",
           audit.devant_nous(ev, AUJ) == attendu, str(ev))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
