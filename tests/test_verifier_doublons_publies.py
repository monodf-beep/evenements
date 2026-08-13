#!/usr/bin/env python3
"""Fixture : le contradicteur « deux fiches EN LIGNE sur le même événement ».

⚠️ BASE JETABLE — jamais data/events.db.

CE QU'ELLE SURVEILLE, et pourquoi chaque cas est là :

  1. LE CAS QUI DOIT PASSER, choisi près de la frontière : deux fiches ITALIENNES au
     titre presque identique, publiées toutes les deux, NON liées par traduction. C'est
     la paire 4421/4584 (« Tour de l'Avenir 2026 - Strambino Lago Serrù » avec et sans
     tiret) vue en production le 2026-08-13. Sans elle, la fixture ne prouverait que
     notre capacité à refuser.

  2. LE FAUX POSITIF QUI COÛTERAIT LE PLUS CHER : une traduction dont le titre est resté
     en italien parce que le nom de l'événement EST italien. Fusionner ces deux-là
     détruirait le bilinguisme. C'est le piège de la fiche 3588, où un portillon a pris
     un NOM PROPRE pour la preuve d'une traduction ratée.

  3. LA FRONTIÈRE PASSÉ / À-VENIR (règle 5) : deux jumelles sur un événement terminé ne
     sont pas une tâche.

  4. LE ZÉRO QUI SE LIT (journal du 11 août) : quand il n'y a rien, la sortie doit dire
     combien de cas se sont présentés — sinon « aucun doublon » et « rien examiné » ont
     exactement la même tête.

Lancer : .venv/bin/python -m tests.test_verifier_doublons_publies
"""
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.verifier_doublons_publies as vd  # noqa: E402

vd.DB_PATH = tmp

AUJ = date.today()
FUTUR = (AUJ + timedelta(days=40)).isoformat()
PASSE = (AUJ - timedelta(days=40)).isoformat()

# id, titre, wp, début, fin, translation_of, territoire
FICHES = [
    # 1. le vrai doublon — deux pages italiennes, presque le même titre, non liées
    (10, "Tour de l'Avenir 2026 - Strambino Lago Serrù", 6380, FUTUR, FUTUR, None, "piemont"),
    (11, "Tour de l'Avenir 2026 - Strambino - Lago Serrù", 7113, FUTUR, FUTUR, None, "piemont"),
    # 2. la paire FR/IT légitime : le titre reste italien, c'est un NOM PROPRE
    (20, "Campionato Italiano Canoa Slalom e Kayak Cross", 4422, FUTUR, FUTUR, None, "piemont"),
    (21, "Campionato Italiano Canoa Slalom e Kayak Cross", 4696, FUTUR, FUTUR, 20, "piemont"),
    # 3. deux jumelles, mais l'événement a eu lieu
    (30, "Fiera del Bue grasso di Carrù edizione", 2283, PASSE, PASSE, None, "piemont"),
    (31, "Fiera del Bue grasso di Carrù edizione", 2284, PASSE, PASSE, None, "piemont"),
    # une fiche seule, pour que le périmètre ne soit pas fait que de paires
    (40, "Concerto della Filarmonica della Scala", 7490, FUTUR, FUTUR, None, "piemont"),
]

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, titre, wp, d, f, trad, terr in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, wp_post_id_as, date_event_start, "
        "date_event_end, translation_of, territoire, duplicate_of) VALUES (?,?,?,?,?,?,?,?, NULL)",
        (eid, titre, f"https://a.it/{eid}", wp, d, f, trad, terr))
conn.commit()
conn.close()

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


import io as _io, contextlib as _ctx  # noqa: E402

_buf = _io.StringIO()
with _ctx.redirect_stdout(_buf):
    rc = vd.main([])
sortie = _buf.getvalue()

_check("rc=0 (lecture seule, jamais d'échec)", rc == 0)

print("\n──── 1. le cas qui doit PASSER ────")


def _groupes_signales() -> set[tuple[int, ...]]:
    """Les groupes que le script retiendrait, sous forme de tuples d'ids triés."""
    c = vd._connect_ro(tmp)
    rows = [dict(r) for r in c.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL").fetchall()]
    c.close()
    suspects, _compte = vd.analyser(rows, AUJ.isoformat())
    return {tuple(sorted(e["id"] for e in g)) for g in suspects}


ids = _groupes_signales()
_check("la paire non liée (10, 11) est signalée", (10, 11) in ids, str(ids))

print("\n──── 2. le faux positif le plus coûteux ────")
_check("la paire FR/IT (20, 21) n'est PAS signalée — deux langues, pas deux doublons",
       (20, 21) not in ids, str(ids))
_check("   et elle est COMPTÉE comme écartée, pas silencieusement perdue",
       "écartés (paires FR/IT)  : 1" in sortie, sortie[:900])
_check("paire_de_traduction reconnaît la liaison dans les deux sens",
       vd.paire_de_traduction({"id": 20, "translation_of": None},
                              {"id": 21, "translation_of": 20})
       and vd.paire_de_traduction({"id": 21, "translation_of": 20},
                                  {"id": 20, "translation_of": None}))
_check("   et deux fiches traduisant le MÊME original aussi",
       vd.paire_de_traduction({"id": 22, "translation_of": 20},
                              {"id": 23, "translation_of": 20}))
_check("   mais deux fiches sans liaison ne sont jamais confondues avec une paire",
       not vd.paire_de_traduction({"id": 10, "translation_of": None},
                                  {"id": 11, "translation_of": None}))

print("\n──── 3. la frontière passé / à-venir (règle 5) ────")
_check("la paire d'un événement TERMINÉ n'est pas une tâche", (30, 31) not in ids, str(ids))

print("\n──── 4. le geste au bout de la ligne ────")
_check("la sortie dit quoi faire, et que le choix reste éditorial",
       "reste ÉDITORIAL" in sortie and "trash_by_ids" in sortie, sortie[-700:])
_check("   et elle prévoit le cas « deux éditions », pour ne pas fabriquer une fusion",
       "DEUX ÉDITIONS" in sortie, sortie[-700:])
_check("le permalien inconnu est DIT, jamais remplacé par /?p=<id> qui répond 404",
       "permalien inconnu" in sortie and "?p=" not in sortie, sortie[-900:])

# ── 5. LE CAS CHAGALL : DEUX PAIRES BILINGUES POUR UNE SEULE EXPOSITION ──────────────
# Relevé en production le 2026-08-13. Quatre pages en ligne : 3021 (it) ↔ 4194 (fr) d'un
# côté, 3026 (fr) ↔ 4195 (it) de l'autre. Chaque paire est correcte ; c'est l'exposition
# entière qui est en double. Retirer « la fiche 4194 » aurait laissé 3021 seule en
# italien, liée par Polylang à un post corbeillé — un site à moitié réparé, plus dur à
# diagnostiquer qu'avant. On raisonne par FAMILLE.
print("\n──── 5. deux paires bilingues pour un seul événement (cas Chagall) ────")
import json as _json  # noqa: E402

c = sqlite3.connect(tmp)
CHAGALL = [
    # id, titre, wp, translation_of, corps d'article, permalien
    (3021, "Marc Chagall. Tra poesia e spiritualità", 2017, None, "", ""),
    (4194, "Marc Chagall. Entre poésie et spiritualité", 3977, 3021, "", ""),
    (3026, "Marc Chagall. Entre poésie et spiritualité", 2020, None,
     "Le musée de Verceil réunit une centaine d'œuvres. " * 4,
     "https://agendasabauda.eu/evenement/marc-chagall-entre-poesie-et-spiritualite/"),
    (4195, "Marc Chagall. Tra poesia e spiritualità", 3981, 3026, "", ""),
]
for eid, titre, wp, trad, corps, perma in CHAGALL:
    ed = _json.dumps({"article": {"corps": corps}}) if corps else ""
    c.execute("INSERT INTO events_raw (id,title,url_source,wp_post_id_as,date_event_start,"
              "date_event_end,translation_of,territoire,enrich_data,wp_permalink_as,"
              "duplicate_of) VALUES (?,?,?,?,?,?,?,?,?,?,NULL)",
              (eid, titre, f"https://a.it/{eid}", wp, FUTUR, FUTUR, trad, "piemont",
               ed, perma))
c.commit(); c.close()

_buf = _io.StringIO()
with _ctx.redirect_stdout(_buf):
    vd.main([])
chag = _buf.getvalue()
_check("la famille qui porte l'article est proposée à la GARDE",
       "[ 3026]" in chag and "← GARDER" in chag, chag[chag.find("Chagall") - 200:][:600])
_check("   et son jumeau italien est gardé avec elle, pas séparé",
       chag.split("[ 4195]")[1][:40].strip().startswith("WP#3981")
       and "← retirer" not in chag.split("[ 4195]")[1][:80], chag)
_check("l'autre paire ENTIÈRE est proposée au retrait — 3021 ET 4194",
       "3021 4194" in chag or ("3021" in chag.split("trash_by_ids")[1][:40]
                               and "4194" in chag.split("trash_by_ids")[1][:40]),
       chag.split("trash_by_ids")[1][:120] if "trash_by_ids" in chag else chag[-500:])
# Le motif est celui du critère qui a VRAIMENT départagé — pas une formule fixe. Sur
# Chagall c'est l'article ; sur la paire « Tour de l'Avenir », où les deux familles sont
# également nues, c'est l'ancienneté, et c'est dit tel quel. Une fixture qui exigerait la
# même phrase partout obligerait le script à mentir sur son critère.
_check("le critère du choix est DIT, et c'est bien l'article qui départage Chagall",
       "porte 1 article(s) rédigé(s) chez nous contre 0" in chag,
       chag[chag.find("défaut proposé"):][:300])
_check("   et quand rien ne départage sauf l'âge, il le dit AUSSI, sans se draper "
       "dans un critère qu'il n'a pas utilisé",
       "la plus ancienne" in chag, chag[:800])
_check("le jumeau ABSENT du groupe est signalé comme tel — sinon on croit n'en "
       "retirer qu'une",
       "jumeau" in chag, chag[-900:])

print("\n──── 6. le zéro qui se lit ────")
# On vide la base des paires : il ne doit plus rien rester à signaler, et la sortie doit
# permettre de distinguer « rien trouvé » de « rien examiné ».
c = sqlite3.connect(tmp)
c.execute("UPDATE events_raw SET wp_post_id_as=NULL WHERE id IN (11, 31, 4194, 4195)")
c.commit(); c.close()
_buf = _io.StringIO()
with _ctx.redirect_stdout(_buf):
    vd.main([])
vide = _buf.getvalue()
_check("plus aucun suspect", "SUSPECTS                 : 0" in vide, vide[:800])
_check("   et le zéro dit combien de cas se sont présentés",
       "fiches examinées" in vide and "groupes formés" in vide, vide[-500:])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
