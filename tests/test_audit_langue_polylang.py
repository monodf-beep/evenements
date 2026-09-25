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
    # 3. LE CAS QUI DOIT SORTIR : une traduction française dont l'adresse enregistrée
    #    est du versant ITALIEN — WordPress l'a rangée du mauvais côté à sa dernière
    #    publication. (Avant le 17/09 cette fiche sortait pour un autre motif : titre sans
    #    marqueur, territoire italien qui départage. Ce motif n'existe plus, _lang lit
    #    translated_lang. L'adresse, elle, reste une mesure.)
    (3, "Brahms / Chostakovitch", "Brahms, Chostakovitch.", "Piemonte", 1, "fr"),
    # 3 bis. L'INCIDENT DU 17/09, à l'envers : une traduction ITALIENNE dont l'adresse
    #    n'a PAS de préfixe /it/ — donc servie côté français (WP#9209). Avant, une adresse
    #    sans préfixe passait pour « muette » et ce cas ne sortait pas.
    (6, "Open Factories 2026: le fabbriche di Torino aprono le porte",
     "Tre giorni prima di Terra Madre, Torino apre ai visitatori i suoi laboratori.",
     "Piemonte", 1, "it"),
    # 4. LE CAS TROUVÉ EN PRODUCTION (fiche 3509) : une traduction en ligne dont
    #    l'ORIGINAL, lui, n'est pas publié — une fiche radar que `publish_batch_as`
    #    écarte à chaque passage. `--retranslate` partirait donc d'une fiche que la
    #    publication refuse : il ne faut pas la proposer, il faut le DIRE.
    (4, "MonumenTO, Torino Capitale", "MonumenTO, Torino Capitale.", "Piemonte", 5, "fr"),
    # 5. …et l'original en question, sans `wp_post_id_as` : jamais publié.
    (5, "MonumenTO — dépêche radar", "Dépêche.", "Piemonte", None, None),
]
# La fiche 5 n'a pas de page : c'est ce qui rend le geste impossible pour la 4.
SANS_PAGE = {5}
# Adresses : 2 et 6 sans préfixe (versant français), 3 et 4 avec /it/. La 2 est voulue
# fr → rien à dire ; la 6 est voulue it → écart ; 3 et 4 voulues fr → écart.
COTE_SERVI = {3: "it", 4: "it"}

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, titre, desc, terr, orig, lang in FICHES:
    prefixe = COTE_SERVI.get(eid, "")
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, wp_post_id_as, "
        "statut, date_event_start, date_event_end, territoire, duplicate_of, "
        "translation_of, translated_lang, wp_permalink_as) "
        "VALUES (?,?,?,?,?,?,?,?,?,NULL,?,?,?)",
        (eid, titre, desc, f"https://a.fr/{eid}",
         None if eid in SANS_PAGE else 900 + eid,
         "radar" if eid in SANS_PAGE else "published_sub",
         FUTUR, FUTUR, terr, orig, lang,
         f"https://agendasabauda.eu/{prefixe + '/' if prefixe else ''}e/{eid}"))
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
_check("la traduction rangée du mauvais versant est signalée",
       "Brahms / Chostakovitch" in sortie, sortie)
_check("   avec la langue VOULUE et la langue SERVIE côte à côte",
       "| 3 | fr | **it** |" in sortie, sortie[sortie.find("| Fiche"):][:500])
_check("l'incident du 17/09 : une traduction italienne servie sans préfixe /it/ sort aussi",
       "| 6 | it | **fr** |" in sortie, sortie[sortie.find("| Fiche"):][:600])
_check("   le compte des écarts est 3 (fiches 3, 4 et 6), pas 4 (la 2 est du bon côté)",
       "Du mauvais versant     : 3" in sortie, sortie[:700])
# ⚠️ L'ADRESSE DONNÉE DOIT ÊTRE CELLE QUI RÉPOND. Le 2026-08-17, ce relevé affichait le
# lien public ; Franck l'a ouvert et a vu « 404 Pagina non trovata » — la forme `?p=<id>`
# rend 404 pour TOUT tribe_events, en ligne ou non, et CLAUDE.md le documente depuis le
# 2026-08-02. Un relevé qui envoie vérifier au mauvais endroit est pire qu'un relevé
# muet : il fabrique une certitude fausse.
_check("   et l'adresse de vérification est l'API REST, pas le lien public",
       "/wp-json/wp/v2/tribe_events/903" in sortie,
       sortie[sortie.find("| Fiche"):][:600])
_check("   allégée pour être lisible dans un navigateur",
       "_fields=link,status,title" in sortie, sortie[sortie.find("| Fiche"):][:600])
_check("   et le relevé dit POURQUOI le lien public ne vaut rien ici",
       "répond 404 pour tout tribe_events" in sortie, sortie[:1800])

print("\n──── le témoin de code : _lang ne devine plus une traduction ────")
_check("aucune régression signalée : _lang rend translated_lang pour les 4 traductions",
       "RÉGRESSION DE CODE" not in sortie, sortie[:900])

print("\n──── les nombres disent leur périmètre ────")
_check("le total examiné est affiché à côté du total publié",
       "EXAMINÉES ici" in sortie and "encore devant nous" in sortie, sortie[:600])
_check("le relevé compte les 4 traductions, pas les 6 fiches",
       "Traductions publiées   : 4" in sortie, sortie[:600])

print("\n──── le geste n'est proposé que quand il existe ────")
_check("il propose --retranslate pour l'original qui EST en ligne",
       "--retranslate 1 --apply" in sortie, sortie[-900:])
_check("   et dit POURQUOI ça règle le problème",
       "IMPOSE la langue" in sortie, sortie[-900:])
_check("⚠️ il ne le propose PAS pour l'original qui n'est pas publié",
       "--retranslate 5" not in sortie and "1 5" not in sortie, sortie[-900:])
_check("   il dit à la place que c'est un arbitrage, avec le statut de l'original",
       "PAS de geste automatique" in sortie and "statut radar" in sortie,
       sortie[-700:])

print("\n──── un zéro doit dire son dénominateur ────")
# On rejoue sur une base où il n'y a QUE le cas franc : le relevé doit alors annoncer
# « aucun écart sur N examinée(s) », jamais un 0 nu. Un zéro sans dénominateur ressemble
# exactement à un monde où il n'y a rien à trouver (journal du 2026-08-11).
c = sqlite3.connect(tmp)
c.execute("DELETE FROM events_raw WHERE id IN (3,4,6)")  # base JETABLE, pas data/events.db
c.commit(); c.close()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    al.main([])
vide = buf.getvalue()
_check("le zéro annonce combien de cas se sont présentés",
       "Aucun écart sur les 1 traduction(s) examinée(s)" in vide, vide[-400:])

print("\n──── --slack : UNE ligne dans le bilan quotidien, et elle part même à zéro ────")
# BRANCHÉ LE 2026-09-21. Ce script portait depuis le 17/09 la phrase « un audit qui mesure
# un risque sans jamais tourner ne protège de rien » — et il n'était dans aucun cron. Le
# 21/09, mesuré : 32 traductions du mauvais versant, découvertes seulement parce que Franck
# a envoyé une capture du hub. La ligne de cron est désormais dans crontab.txt (9h55).
_envois = []
import utils.slack as _slk  # noqa: E402
_slk.notify = lambda texte, blocks=None, urgent=False: _envois.append(texte) or True

# (a) sur la base RÉDUITE de l'étape précédente : zéro écart, le message part quand même.
with contextlib.redirect_stdout(io.StringIO()):
    al.main(["--slack"])
_check("à zéro écart, UN message part quand même", len(_envois) == 1, _envois)
_check("   et il porte les DEUX nombres, pas un 0 nu",
       "0 sur 1 examinée(s)" in _envois[0], _envois)
_check("   et son périmètre est écrit à côté",
       "encore devant nous" in _envois[0], _envois)
_check("   et il ne propose aucun geste quand il n'y a rien à faire",
       "audit_langue_polylang`" not in _envois[0], _envois)

# (b) le cas franc remis : le message doit compter l'écart ET nommer le relevé.
c = sqlite3.connect(tmp)
c.execute("INSERT INTO events_raw (id, title, url_source, territoire, statut, "
          "wp_post_id_as, wp_permalink_as, translation_of, translated_lang, "
          "date_event_start, date_event_end) VALUES "
          "(7,'Open Factories 2026','https://src/7','piemont','published_sub',9209,"
          "'https://agendasabauda.eu/evenement/open-factories-2026/',1,'it',?,?)",
          (FUTUR, FUTUR))
c.commit(); c.close()
_envois.clear()
with contextlib.redirect_stdout(io.StringIO()):
    al.main(["--slack"])
_check("avec un écart, le message le compte", len(_envois) == 1
       and "1 sur 2 examinée(s)" in _envois[0], _envois)
_check("   il dit POURQUOI ça se voit (le lecteur croit à un doublon)",
       "doublons" in _envois[0], _envois)
_check("   et il nomme le relevé complet, sans recopier le tableau",
       "scripts.audit_langue_polylang" in _envois[0] and "|" not in _envois[0], _envois)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
