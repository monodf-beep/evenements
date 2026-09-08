#!/usr/bin/env python3
"""Fixture : le bouton du back-office qui annule un événement (docs/EVENEMENTS_ANNULES.md,
canal 1 — /action/<id>/annuler et /action/<id>/annuler_off dans app/app.py).

⚠️ BASE JETABLE — jamais data/events.db (absent de cet environnement). AUCUN appel réseau :
`publish_to_as` est remplacé par un faux qui enregistre les appels et ne contacte jamais
WordPress. `DB_PATH` est fixé AVANT d'importer app.app : ses migrations de colonnes
tournent à l'import (comme translation_of/multi_lieux/worth_trip), il faut donc qu'elles
s'appliquent sur la base jetable, jamais sur une base de prod.

Ce que ce test vérifie :
  1. le préfixe posé est le bon selon la langue (FR « ANNULÉ — », IT « ANNULLATO — »),
     et la jumelle FR/IT (translation_of) bascule EN MÊME TEMPS (doc, § « effets de
     bord » : « les deux langues annulent ensemble ») ;
  2. la republication est déclenchée UNIQUEMENT quand `wp_post_id_as` est renseigné,
     avec skip_media=True (même motif que scripts/seo_batch.py : seul le titre change) ;
  3. `statut` ne bouge JAMAIS — CLAUDE.md : ne pas dépublier, ne pas corbeiller ;
  4. le geste est idempotent (recliquer n'empile pas les préfixes, ne republie pas
     pour rien) et réversible (annuler_off retire le préfixe, republie, jumelle incluse) ;
  5. un échec de republication (faux WordPress qui renvoie None) n'efface pas l'état
     déjà posé en base — CLAUDE.md règle 6 : le résultat prime, la base ne ment pas ;
  6. utils.deplacement.deplacement_now/deplacement_etat retirent l'annulé des vitrines.

Lancer : .venv/bin/python -m tests.test_action_annuler
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
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-jetable")

from scripts.scraper_events import init_db  # noqa: E402

# La base doit exister AVANT l'import d'app.app : ses migrations de colonnes
# (annule_le compris) tournent au chargement du module, sur DB_PATH.
_bootstrap = sqlite3.connect(tmp)
init_db(_bootstrap)
_bootstrap.close()

import app.app as appmod  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label}{' — ' + detail if detail else ''}")


# --------------------------------------------------------------------------- #
# Faux WordPress : enregistre les appels, ne contacte JAMAIS le réseau.
# --------------------------------------------------------------------------- #
appels = []          # [(event_id, title, skip_media)]
ids_en_echec = set()  # events pour lesquels le faux WP renvoie un échec


def fake_publish_to_as(event, skip_media=False):
    appels.append((event["id"], event["title"], skip_media))
    if event["id"] in ids_en_echec:
        return None, "", ""
    return 9000 + event["id"], f"https://agendasabauda.eu/e/{event['id']}", ""


appmod.publish_to_as = fake_publish_to_as

# --------------------------------------------------------------------------- #
# Fixture : une paire FR/IT publiée, une fiche seule publiée qui échoue au
# republish, une fiche NON publiée.
# --------------------------------------------------------------------------- #
conn = sqlite3.connect(tmp)
conn.execute(
    "INSERT INTO events_raw (id, title, description, url_source, territoire, statut, "
    "wp_post_id_as, translation_of, translated_lang) VALUES (?,?,?,?,?,?,?,?,?)",
    (10, "Festival des Nuits Alpines", "Un grand rendez-vous musical en Savoie chaque été.",
     "https://x.fr/10", "Savoie", "published_sub", 501, None, None))
conn.execute(
    "INSERT INTO events_raw (id, title, description, url_source, territoire, statut, "
    "wp_post_id_as, translation_of, translated_lang) VALUES (?,?,?,?,?,?,?,?,?)",
    (11, "Festival delle Notti Alpine", "Un grande appuntamento musicale in Savoia ogni estate.",
     "https://x.fr/11", "Savoie", "published_sub", 502, 10, "it"))
conn.execute(
    "INSERT INTO events_raw (id, title, description, url_source, territoire, statut, "
    "wp_post_id_as) VALUES (?,?,?,?,?,?,?)",
    (12, "Petite brocante du village", "Une brocante conviviale près de l'église.",
     "https://x.fr/12", "Savoie", "evaluated", None))
conn.execute(
    "INSERT INTO events_raw (id, title, description, url_source, territoire, statut, "
    "wp_post_id_as) VALUES (?,?,?,?,?,?,?)",
    (13, "Marché artisanal de printemps", "Un marché avec de nombreux exposants.",
     "https://x.fr/13", "Savoie", "published_sub", 503))
conn.commit()
conn.close()
ids_en_echec.add(13)


def _row(eid):
    c = sqlite3.connect(tmp); c.row_factory = sqlite3.Row
    r = dict(c.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())
    c.close()
    return r


client = appmod.app.test_client()
with client.session_transaction() as sess:
    sess["logged_in"] = True


def _post(eid, action):
    return client.post(f"/action/{eid}/{action}", data={"next": "/preview/%d" % eid})


# ══════════════ 1. Annulation d'une paire FR/IT publiée ══════════════
print("──── 1. /action/10/annuler — paire FR/IT publiée ────")
appels.clear()
resp = _post(10, "annuler")
_check("redirige (302)", resp.status_code in (301, 302), str(resp.status_code))

f10, f11 = _row(10), _row(11)
_check("préfixe FR posé sur l'original",
       f10["title"] == "ANNULÉ — Festival des Nuits Alpines", f10["title"])
_check("annule_le posé sur l'original", bool(f10["annule_le"]), str(f10["annule_le"]))
_check("statut INCHANGÉ (pas de dépublication)", f10["statut"] == "published_sub", f10["statut"])
_check("préfixe IT posé sur la jumelle (translated_lang=it)",
       f11["title"] == "ANNULLATO — Festival delle Notti Alpine", f11["title"])
_check("annule_le posé sur la jumelle", bool(f11["annule_le"]), str(f11["annule_le"]))
_check("statut de la jumelle INCHANGÉ", f11["statut"] == "published_sub", f11["statut"])

_check("republication déclenchée pour les DEUX fiches (wp_post_id_as renseigné)",
       {a[0] for a in appels} == {10, 11}, str(appels))
_check("republication en skip_media=True (seul le titre change)",
       all(a[2] is True for a in appels), str(appels))
_check("le titre ENVOYÉ à WordPress porte déjà le préfixe",
       any(a[0] == 10 and a[1].startswith("ANNULÉ — ") for a in appels), str(appels))

# ══════════════ 2. Idempotence : recliquer ne double pas le préfixe ══════════════
print("\n──── 2. re-clic sur /action/10/annuler — idempotent ────")
appels.clear()
_post(10, "annuler")
f10b = _row(10)
_check("titre INCHANGÉ (pas de double préfixe)",
       f10b["title"] == "ANNULÉ — Festival des Nuits Alpines", f10b["title"])
_check("aucune republication inutile", appels == [], str(appels))

# ══════════════ 3. Réversibilité : annuler_off retire le préfixe, republie ══════════════
print("\n──── 3. /action/10/annuler_off — réversible, jumelle incluse ────")
appels.clear()
_post(10, "annuler_off")
f10c, f11c = _row(10), _row(11)
_check("préfixe retiré sur l'original", f10c["title"] == "Festival des Nuits Alpines", f10c["title"])
_check("annule_le effacé sur l'original", f10c["annule_le"] is None, str(f10c["annule_le"]))
_check("préfixe retiré sur la jumelle", f11c["title"] == "Festival delle Notti Alpine", f11c["title"])
_check("annule_le effacé sur la jumelle", f11c["annule_le"] is None, str(f11c["annule_le"]))
_check("republication déclenchée pour les DEUX fiches (retour à la normale)",
       {a[0] for a in appels} == {10, 11}, str(appels))

print("\n──── 3bis. re-clic sur /action/10/annuler_off — idempotent, rien à défaire ────")
appels.clear()
_post(10, "annuler_off")
_check("aucune republication (déjà non annulée)", appels == [], str(appels))

# ══════════════ 4. Fiche NON publiée : base changée, AUCUN appel WordPress ══════════════
print("\n──── 4. /action/12/annuler — pas de wp_post_id_as ────")
appels.clear()
_post(12, "annuler")
f12 = _row(12)
_check("préfixe posé quand même (Franck peut savoir avant publication)",
       f12["title"].startswith(("ANNULÉ — ", "ANNULLATO — ")), f12["title"])
_check("aucun appel WordPress (rien à republier)", appels == [], str(appels))

# ══════════════ 5. Échec WordPress : la base garde son état, rien n'est perdu ══════════════
print("\n──── 5. /action/13/annuler — le faux WordPress échoue ────")
appels.clear()
_post(13, "annuler")
f13 = _row(13)
_check("le préfixe reste posé MALGRÉ l'échec de republication (règle 6 : le résultat "
       "en base ne ment pas, même si WordPress a échoué)",
       f13["title"].startswith(("ANNULÉ — ", "ANNULLATO — ")), f13["title"])
_check("annule_le posé malgré l'échec", bool(f13["annule_le"]), str(f13["annule_le"]))
_check("l'appel WordPress a bien été TENTÉ", {a[0] for a in appels} == {13}, str(appels))

# ══════════════ 6. Vitrines : deplacement_now/deplacement_etat écartent l'annulé ══════════════
print("\n──── 6. utils.deplacement — retrait des vitrines ────")
from utils.deplacement import deplacement_now, deplacement_etat  # noqa: E402
ev_annule = {"annule_le": "2026-08-05 10:00:00", "llm_score_detail": '{"rayonnement":{"points":2}}',
             "date_event_start": "2030-01-01"}
_check("deplacement_now → None pour un événement annulé",
       deplacement_now(ev_annule) is None, str(deplacement_now(ev_annule)))
base, now, motif = deplacement_etat(ev_annule)
_check("deplacement_etat → (None, None, motif explicite) pour un annulé",
       base is None and now is None and "annulé" in motif.lower(), f"{base},{now},{motif}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
