#!/usr/bin/env python3
"""Fixture : le relevé des traductions dont la langue serait DEVINÉE au lieu d'imposée.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau, aucun LLM.

D'OÙ ÇA VIENT (2026-08-17). `translate_events` publie une traduction avec `force_lang` :
la langue est imposée. `publish_batch_as --update` republie la même fiche depuis la base
SANS ce champ — `publisher_as._lang` retombe alors sur `detect_lang`, qui devine, et qui
départage par le TERRITOIRE quand le texte ne tranche pas. Une traduction française d'un
événement piémontais peut donc repartir en italien.

CE QUE LA FIXTURE SURVEILLE :
  1. une traduction dont le texte est franc n'apparaît PAS dans le relevé — sinon la file
     se remplit de fiches sur lesquelles il n'y a aucun geste à faire (règle 6) ;
  2. une traduction dont le texte ne tranche pas ET dont le territoire tire dans l'autre
     sens y apparaît, avec les deux langues côte à côte ;
  3. le zéro dit son dénominateur : « aucun écart sur N examinée(s) », jamais « 0 » seul ;
  4. et le relevé propose le geste qui RÉSOUT (`--retranslate`, qui repasse par
     `force_lang`), pas seulement le constat.

Lancer : .venv/bin/python -m tests.test_audit_langue_polylang
"""
import contextlib
import io
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
import scripts.audit_langue_polylang as al  # noqa: E402

al.DB_PATH = tmp
FUTUR = (date.today() + timedelta(days=20)).isoformat()

# (id, titre, description, territoire, translation_of, translated_lang)
FICHES = [
    # 1. L'ORIGINAL italien. N'a pas de `translated_lang` : hors périmètre du relevé,
    #    qui ne parle que des traductions.
    (1, "Concerto della Filarmonica della Scala", "Il concerto si tiene nella sala "
     "grande, con ingresso libero per tutti gli spettatori.", "Piemonte", None, None),
    # 2. ⚠️ LE CAS QUI DOIT PASSER : une traduction française FRANCHE. Son texte porte
    #    assez de marqueurs pour que la devinette tombe juste — elle n'a donc rien à
    #    faire dans la file. Sans ce cas, la fixture ne prouverait que notre capacité à
    #    signaler, et une file qui signale tout ne désigne plus rien.
    (2, "Concert de la Philharmonie de la Scala", "Le concert est donné dans la grande "
     "salle, avec une entrée libre pour tous les spectateurs.", "Piemonte", 1, "fr"),
    # 3. LE CAS QUI DOIT SORTIR : titre-programme sans phrase, aucun marqueur de langue.
    #    Le territoire italien départage seul et emporte la fiche du mauvais côté.
    (3, "Brahms / Chostakovitch", "Brahms, Chostakovitch.", "Piemonte", 1, "fr"),
]

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, titre, desc, terr, orig, lang in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, wp_post_id_as, "
        "statut, date_event_start, date_event_end, territoire, duplicate_of, "
        "translation_of, translated_lang, wp_permalink_as) "
        "VALUES (?,?,?,?,?,?,?,?,?,NULL,?,?,?)",
        (eid, titre, desc, f"https://a.fr/{eid}", 900 + eid, "published_sub",
         FUTUR, FUTUR, terr, orig, lang, f"https://agendasabauda.eu/e/{eid}"))
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


buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    al.main([])
sortie = buf.getvalue()

print("──── la file ne contient que ce sur quoi il y a un geste ────")
_check("la traduction au texte franc n'est PAS signalée (le cas qui doit passer)",
       "Concert de la Philharmonie" not in sortie, sortie)
_check("l'ORIGINAL n'est pas signalé non plus — il n'a pas de langue demandée",
       "Concerto della Filarmonica" not in sortie, sortie)

print("\n──── ce qui doit sortir, sort ────")
_check("la traduction que le territoire emporte est signalée",
       "Brahms / Chostakovitch" in sortie, sortie)
_check("   avec la langue VOULUE et la langue DEVINÉE côte à côte",
       "| fr | **it** |" in sortie, sortie[sortie.find("| Fiche"):][:400])
_check("   et l'adresse de la page, parce que seul WordPress dit l'état réel (règle 1)",
       "https://agendasabauda.eu/e/3" in sortie, sortie[-600:])

print("\n──── les nombres disent leur périmètre ────")
_check("le total examiné est affiché à côté du total publié",
       "EXAMINÉES ici" in sortie and "encore devant nous" in sortie, sortie[:600])
_check("le relevé compte 2 traductions, pas 3 fiches",
       "Traductions publiées   : 2" in sortie, sortie[:600])

print("\n──── le geste est au bout de la file ────")
_check("il propose --retranslate, qui repasse par force_lang",
       "--retranslate 1" in sortie, sortie[-500:])
_check("   et dit POURQUOI ça règle le problème",
       "IMPOSE la langue" in sortie, sortie[-400:])

print("\n──── un zéro doit dire son dénominateur ────")
# On rejoue sur une base où il n'y a QUE le cas franc : le relevé doit alors annoncer
# « aucun écart sur N examinée(s) », jamais un 0 nu. Un zéro sans dénominateur ressemble
# exactement à un monde où il n'y a rien à trouver (journal du 2026-08-11).
c = sqlite3.connect(tmp)
c.execute("DELETE FROM events_raw WHERE id=3")   # base JETABLE, pas data/events.db
c.commit(); c.close()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    al.main([])
vide = buf.getvalue()
_check("le zéro annonce combien de cas se sont présentés",
       "Aucun écart sur les 1 traduction(s) examinée(s)" in vide, vide[-400:])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
