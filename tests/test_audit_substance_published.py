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

# CE QUI SUIT VIENT D'UN VRAI DÉFAUT, VU DANS LA SORTIE ET NON DANS LE CODE (2026-08-13).
# Les deux lignes qui expliquent le panier 3 — « l'événement a eu lieu… ~34 $ pour rien »
# — s'imprimaient APRÈS le panier 4. Elles se lisaient donc comme si elles décrivaient
# les fiches sans article, c'est-à-dire l'inverse : celles-là, il FAUT les réparer. Rien
# dans le code ne le montrait ; il a fallu lire la sortie. La fixture surveille l'ORDRE.
_i3, _i4 = _sortie.find("3. MAIGRES MAIS PASSÉES"), _sortie.find("4. PUBLIÉES SANS ARTICLE")
_ieu = _sortie.find("L'événement a eu lieu")
_check("les paniers sortent dans l'ordre", -1 < _i3 < _i4, f"3={_i3} 4={_i4}")
_check("l'explication « l'événement a eu lieu » reste ATTACHÉE au panier 3",
       _i3 < _ieu < _i4, f"3={_i3} explication={_ieu} 4={_i4}")

# RÈGLE 6 : le périmètre à côté du nombre. Ce compteur-ci porte sur TOUTES les publiées,
# celui de `panel_rattrapage` sur les vivantes seulement — deux périmètres, et c'est le
# plus gros qu'on croira si personne ne l'écrit.
_check("le panier 4 écrit son périmètre à côté de son nombre",
       "toutes dates confondues" in _sortie and "sur les" in _sortie, _sortie[_i4:_i4 + 300])
_check("   et il dit combien il apporte de VRAIMENT nouveau, sans additionner les paniers",
       "qu'AUCUNE commande ne visait" in _sortie, _sortie[_i4:_i4 + 400])

# Le cas frontière du panier 4 : id 6 est LONGUE (elle passe le plancher grâce au repli)
# et non rédigée. Elle doit donc apparaître dans la liste propre au panier 4, et surtout
# PAS être recomptée avec les maigres du panier 1.
_buf = _io.StringIO()
with _ctx.redirect_stdout(_buf):
    audit.main(["--ids"])
_ids_out = _buf.getvalue()
_check("la fiche longue-mais-non-rédigée est listée à part",
       "AU-DESSUS du plancher" in _ids_out, _ids_out[-600:])
_check("   et elle n'est PAS recomptée avec les maigres du panier 1",
       "  [    1] " not in _ids_out.split("AU-DESSUS du plancher")[1],
       _ids_out.split("AU-DESSUS du plancher")[-1][:400])

# ── UNE TRADUCTION N'EST PAS UNE TÂCHE ───────────────────────────────────────────────
# `enrich` REFUSE toute fiche dont `translation_of` est renseigné : il écrit en français
# et écraserait la traduction. L'audit les mettait quand même dans sa commande — le
# lecteur croyait lancer huit réparations et en obtenait six, sans que rien ne le dise.
# Vu en production le 2026-08-13 sur la paire 4194/4195 (Chagall FR puis IT), les deux
# dans le panier 4 le même jour.
#
# LES DEUX CÔTÉS DE LA FRONTIÈRE, y compris celui qui doit PASSER : id 7 est la traduction
# (elle sort de la commande), id 8 est un original tout aussi long et non rédigé (il y
# reste). Une fixture qui n'aurait que le cas refusé prouverait seulement qu'on sait
# refuser.
_c = _sq.connect(tmp)
_c.execute("INSERT INTO events_raw (id, title, url_source, wp_post_id_as, enrich_data, "
           "translation_of, translated_lang) VALUES (?,?,?,?,?,?,?)",
           (7, "Chagall, versione italiana", "https://a.fr/7", 994, "", 6, "it"))
_c.execute("INSERT INTO events_raw (id, title, url_source, wp_post_id_as, enrich_data, "
           "translation_of) VALUES (?,?,?,?,?, NULL)",
           (8, "Un original tout aussi long et non rédigé", "https://a.fr/8", 993, ""))
_c.commit(); _c.close()

_buf = _io.StringIO()
with _ctx.redirect_stdout(_buf):
    audit.main([])
_t = _buf.getvalue()
_cmd = [l for l in _t.splitlines() if "scripts.enrich " in l]
_check("la traduction (id 7) ne figure dans AUCUNE commande enrich",
       all(" 7 " not in f"{l} " and not l.rstrip().endswith(" 7") for l in _cmd),
       "\n".join(_cmd))
_check("   mais l'original de même longueur (id 8) y est bien — sinon on aurait "
       "seulement appris à refuser",
       any(" 8" in l for l in _cmd), "\n".join(_cmd))
_check("   et l'écart est DIT", "traduction mise de côté" in _t, _t[-900:])

# ── LE GESTE N'EST PAS LE MÊME SELON L'ORIGINAL ──────────────────────────────────────
# Une traduction sans article a deux causes, et l'audit les confondait : il disait
# « réécrire l'original » dans les deux. Or si l'original A DÉJÀ son article, le
# réenrichir coûte 0,33 $ et ne répare rien côté italien — c'est `translate_article` qui
# a échoué, et `--retranslate` régénère le jumeau en place. Vu le 2026-08-13 sur 4195,
# dont l'original 3026 (Chagall FR) porte bien ses 223 mots.
#
# id 7 (déjà posé) traduit id 6, qui n'a PAS d'article  → enrich puis retranslate.
# id 9 traduit id 4, qui EN A un (posé plus haut)       → retranslate SEUL.
# id 10 traduit un id qui n'existe pas                  → on le dit, on ne devine pas.
_c = _sq.connect(tmp)
for eid, orig in ((9, 4), (10, 12345)):
    _c.execute("INSERT INTO events_raw (id, title, url_source, wp_post_id_as, enrich_data, "
               "translation_of, translated_lang) VALUES (?,?,?,?,?,?,?)",
               (eid, f"Jumelle {eid}", f"https://a.fr/{eid}", 990 - eid, "", orig, "it"))
_c.commit(); _c.close()

_buf = _io.StringIO()
with _ctx.redirect_stdout(_buf):
    audit.main([])
_g = _buf.getvalue()
_check("l'original QUI A DÉJÀ son article n'est pas renvoyé à enrich",
       "--retranslate" in _g and "9←4" in _g, _g[-1200:])
_check("   et la commande proposée pour lui est bien --retranslate, pas enrich",
       "scripts.translate_events --retranslate 4 --apply" in _g, _g[-1200:])
_check("l'original SANS article, lui, passe par enrich AVANT la re-traduction",
       "7←6" in _g and "n'a PAS d'article non plus" in _g, _g[-1200:])
_check("une liaison cassée est DITE, pas devinée",
       "original 12345 INTROUVABLE" in _g, _g[-1200:])
# La corbeille, elle, doit garder la traduction : dépublier l'original en laissant sa
# version italienne en ligne laisserait justement ce qu'on retire.
_trash = [l for l in _t.splitlines() if "trash_by_ids" in l]
_check("la commande de DÉPUBLICATION, elle, garde la traduction",
       any(" 7" in l for l in _trash), "\n".join(_trash))

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
