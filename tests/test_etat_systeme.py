#!/usr/bin/env python3
"""Fixture : l'état du système. Base jetable — jamais data/events.db.

UNE PAGE DE TABLEAU DE BORD EST L'ENDROIT OÙ LES COMPTEURS MENTENT. Le 2026-08-11, trois
d'entre eux ont menti dans la même journée — aucun sur ses données, tous sur leur
PÉRIMÈTRE. La fixture surveille donc d'abord les dénominateurs, ensuite seulement les
numérateurs :

  1. le PASSÉ ne compte nulle part (règle 5), mais une fiche RÉCURRENTE ou SANS DATE compte
     — elle n'est pas terminée, elle est incomplète ;
  2. les TRADUCTIONS ne comptent pas dans les étages amont : ce sont des copies, et les
     inclure doublerait tout le haut de la chaîne ;
  3. un étage sans aucun cas rend `pct = None`, pas `0` — « rien à faire » et « tout a
     échoué » s'affichent pareil et n'appellent pas du tout le même geste ;
  4. le goulot désigné est le PREMIER qui décroche, pas le pire : un étage ne peut pas
     faire mieux que celui qui le précède.

Lancer : .venv/bin/python -m tests.test_etat_systeme
"""
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import etat_systeme as es  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


AUJ = date(2026, 8, 11)
DEMAIN = (AUJ + timedelta(days=30)).isoformat()
HIER = (AUJ - timedelta(days=30)).isoformat()
COLLECTE = AUJ.isoformat() + " 06:00:00"

tmp = Path(tempfile.mkdtemp(prefix="fixture-systeme-"))
db = tmp / "events.db"
conn = sqlite3.connect(db)
init_db(conn)
for col, decl in (("multi_lieux", "INTEGER DEFAULT 0"),
                  ("translation_of", "INTEGER"), ("translated_lang", "TEXT")):
    try:
        conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
    except sqlite3.OperationalError:
        pass


def ajoute(eid, **kw):
    champs = {"id": eid, "title": f"Fiche {eid}", "url_source": f"https://ex.fr/{eid}",
              "source_name": "Source", "statut": "evaluated", "scrape_date": COLLECTE,
              "date_event_start": DEMAIN, "date_event_end": DEMAIN}
    champs.update(kw)
    cols = ", ".join(champs)
    conn.execute(f"INSERT INTO events_raw ({cols}) "
                 f"VALUES ({', '.join('?' * len(champs))})", tuple(champs.values()))


# 1-4 : la chaîne complète, publiées, dont deux traduites et une référencée.
for eid in (1, 2, 3, 4):
    ajoute(eid, llm_score=7, lieu="Salle", ville="Aoste", url_image="http://i/1.jpg",
           article_md="# Article", wp_post_id_as=1000 + eid,
           seo_title="t" if eid == 1 else "", seo_meta="m" if eid == 1 else "")
# Les traductions de 1 et 2 — elles ne doivent PAS gonfler les étages amont.
ajoute(51, translation_of=1, translated_lang="it", llm_score=7, lieu="Salle",
       ville="Aoste", url_image="http://i/1.jpg", article_md="# Articolo",
       wp_post_id_as=2001, url_source="translated:1:it")
ajoute(52, translation_of=2, translated_lang="it", url_source="translated:2:it")
# 5 : rédigée mais PAS publiée.
ajoute(5, llm_score=6, lieu="Salle", ville="Aoste", url_image="http://i/5.jpg",
       article_md="# Article")
# 6 : complète mais pas rédigée.
ajoute(6, llm_score=5, lieu="Salle", ville="Aoste", url_image="http://i/6.jpg")
# 7 : sans image. 8 : sans lieu. 9 : SANS DATE (incomplète, pas passée).
ajoute(7, llm_score=5, lieu="Salle", ville="Aoste")
ajoute(8, llm_score=5, url_image="http://i/8.jpg")
ajoute(9, llm_score=4, lieu="Salle", ville="Aoste", url_image="http://i/9.jpg",
       date_event_start="", date_event_end="")
# 10 : RÉCURRENTE, sans date — elle compte comme datée.
ajoute(10, llm_score=4, lieu="Salle", ville="Aoste", url_image="http://i/10.jpg",
       recurring=1, date_event_start="", date_event_end="")
# 11 : PASSÉE — hors périmètre partout.
ajoute(11, llm_score=3, date_event_start=HIER, date_event_end=HIER)
# 12 : ÉCARTÉE — hors périmètre partout.
ajoute(12, statut="rejected", llm_score=3)
# 13 : jamais évaluée.
ajoute(13, llm_score=None)
conn.commit()

etgs = es.etages(conn, AUJ.isoformat())
par_cle = {e["cle"]: e for e in etgs}

print("──── 1. les dénominateurs, c'est-à-dire QUI est compté ────")
# Actifs à venir, hors traductions : 1..10 + 13 = 11. (11 est passée, 12 écartée.)
_check("« évalués » porte sur les actifs à venir, traductions exclues",
       par_cle["evalue"]["total"] == 11, par_cle["evalue"]["total"])
_check("le PASSÉ ne compte nulle part", par_cle["date"]["total"] < 12,
       par_cle["date"]["total"])
_check("l'ÉCARTÉE ne compte nulle part",
       all(e["total"] <= 11 for e in etgs), [(e["cle"], e["total"]) for e in etgs])
_check("« traduits » se mesure sur les PUBLIÉS, pas sur tout le stock",
       par_cle["traduit"]["total"] == 4, par_cle["traduit"]["total"])
_check("« SEO » aussi", par_cle["seo"]["total"] == 4, par_cle["seo"]["total"])
_check("« publiés » se mesure sur les RÉDIGÉS (5 rédigées, 4 publiées)",
       par_cle["publie"]["total"] == 5 and par_cle["publie"]["fait"] == 4,
       (par_cle["publie"]["total"], par_cle["publie"]["fait"]))
_check("chaque étage écrit son périmètre EN FRANÇAIS",
       all(len(e["perimetre"]) > 10 for e in etgs))

print("\n──── 2. les numérateurs ────")
_check("une fiche RÉCURRENTE compte comme datée — elle n'a pas de date à trouver",
       par_cle["date"]["fait"] == 10, par_cle["date"]["fait"])
_check("une fiche SANS DATE n'est pas « passée » : elle manque, et elle compte",
       par_cle["date"]["reste"] == 1, par_cle["date"]["reste"])
_check("« traduits » : 2 sur 4 publiées", par_cle["traduit"]["fait"] == 2,
       par_cle["traduit"]["fait"])
_check("« SEO » : 1 sur 4 — il faut titre ET description",
       par_cle["seo"]["fait"] == 1, par_cle["seo"]["fait"])
_check("les traductions ne gonflent pas le haut de la chaîne",
       par_cle["evalue"]["total"] == 11, par_cle["evalue"]["total"])

print("\n──── 3. zéro cas ≠ zéro pour cent ────")
vide = sqlite3.connect(":memory:")
init_db(vide)
for e in es.etages(vide, AUJ.isoformat()):
    if e["total"] == 0 and e["pct"] is not None:
        _check(f"étage « {e['nom'] } » : base vide → pct doit valoir None", False, e["pct"])
        break
else:
    _check("sur une base vide, aucun étage n'affiche « 0 % » — tous disent « aucun cas »",
           True)
_check("et aucun goulot n'est désigné quand il n'y a rien à faire",
       es.goulot(es.etages(vide, AUJ.isoformat())) is None)
vide.close()

print("\n──── 4. le goulot : le PREMIER qui décroche, pas le pire ────")
g = es.goulot(etgs)
_check("un goulot est désigné", g is not None)
_check("c'est le premier étage sous 90 %, pas le plus bas en pourcentage",
       g["cle"] == next(e["cle"] for e in etgs if e["pct"] is not None
                        and e["pct"] < 90 and e["reste"]),
       g["cle"] if g else None)
_check("il porte son reste et son lien, donc un geste au bout",
       g["reste"] > 0 and g["lien"].startswith("/"))

print("\n──── 5. le régime dit le MOUVEMENT, que les pourcentages ne montrent pas ────")
f = es.flux(conn, AUJ.isoformat())
_check("les collectes de la semaine sont comptées", f["collectes"] >= 13, f)
_check("les écartées aussi", f["ecartes"] >= 1, f)
_check("le nombre de sources actives est donné", f["sources"] >= 1, f)

conn.close()
print(f"\n{'TOUT PASSE' if not echecs else str(echecs) + ' ÉCHEC(S)'}")
sys.exit(1 if echecs else 0)
