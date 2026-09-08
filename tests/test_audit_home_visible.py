#!/usr/bin/env python3
"""Fixture : le relevé de ce qu'un visiteur voit à tort.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau.

D'OÙ ÇA VIENT. Capture d'écran de Franck, 2026-08-18 22h18 : « j'espère que c'est une
blague cette image ». Sur une seule vue de la page d'accueil, un événement daté du 09/07
— six semaines dans le passé — illustré par le bandeau de notre PROPRE observatoire
économique.

CE QUE LA FIXTURE SURVEILLE :
  1. un événement terminé est signalé ;
  2. ⚠️ mais une fiche SANS DATE ne l'est pas — c'est une donnée manquante, pas un
     événement fini (règle 5), et `dates.py` la remplira peut-être demain ;
  3. ni un RÉCURRENT, qui n'a pas de date unique et n'est donc jamais passé ;
  4. une image servie par une plateforme d'emailing est signalée AVEC le nom de l'hôte —
     un relevé qui dit « suspecte » sans dire pourquoi ne se vérifie pas ;
  5. ⚠️ et une vraie photo d'office de tourisme ne l'est PAS — le cas qui doit passer,
     sans lequel on ne prouverait que la capacité à crier ;
  6. le verdict Slack tient sur un écran de téléphone et dit qu'il lit la BASE, pas le
     site (règle 1).

Lancer : .venv/bin/python -m tests.test_audit_home_visible
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

from scripts.scraper_events import init_db          # noqa: E402
import scripts.audit_home_visible as ah             # noqa: E402

ah.DB_PATH = tmp
AUJ = date.today()
PASSE = (AUJ - timedelta(days=40)).isoformat()
FUTUR = (AUJ + timedelta(days=20)).isoformat()

# (id, wp, titre, début, fin, image, recurrence)
FICHES = [
    (1, 6501, "Musicanti Estivo: Giua", PASSE, PASSE,
     "https://mcusercontent.com/a5a9/images/57e13b2d-646c-58c8.jpg", 0),
    (2, 6502, "Festival à venir", FUTUR, FUTUR,
     "https://office-tourisme.fr/media/fete-du-lac.jpg", 0),
    (3, 6503, "Fiche sans date", "", "", "https://exemple.fr/p.jpg", 0),
    (4, 6504, "Visite tous les mardis", PASSE, PASSE,
     "https://exemple.fr/q.jpg", 1),
]

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, wp, titre, deb, fin, img, recur in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, wp_post_id_as, statut, "
        "date_event_start, date_event_end, url_image, recurring, duplicate_of) "
        "VALUES (?,?,?,?,?,?,?,?,?,NULL)",
        (eid, titre, f"https://a.fr/{eid}", wp, "published_sub", deb, fin, img, recur))
conn.commit(); conn.close()

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── l'hôte d'emailing est reconnu, et NOMMÉ ────")
_check("une image Mailchimp est reconnue",
       ah.image_de_newsletter("https://mcusercontent.com/a/b.jpg") == "mcusercontent.com")
_check("   le relevé rend l'HÔTE, pas un simple oui/non",
       isinstance(ah.image_de_newsletter("https://musvc6.net/x.jpg"), str)
       and ah.image_de_newsletter("https://musvc6.net/x.jpg") != "")
_check("⚠️ une vraie photo d'office de tourisme ne l'est PAS (le cas qui doit passer)",
       ah.image_de_newsletter("https://office-tourisme.fr/media/fete.jpg") == "")
_check("   ni une image du site de l'organisateur",
       ah.image_de_newsletter("https://www.fortedibard.it/wp-content/800x600.jpg") == "")

print("\n──── ce qui compte comme PASSÉ, et ce qui n'en est pas ────")
_check("un événement terminé est passé",
       ah.evenement_passe({"date_event_end": PASSE}, AUJ))
_check("⚠️ une fiche SANS DATE ne l'est pas — donnée manquante ≠ événement fini",
       not ah.evenement_passe({"date_event_start": "", "date_event_end": ""}, AUJ))
_check("⚠️ ni un RÉCURRENT, qui n'a pas de date unique",
       not ah.evenement_passe({"date_event_end": PASSE,
                               "recurring": 1}, AUJ))

print("\n──── ce que le relevé rend ────")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ah.main([])
sortie = buf.getvalue()

_check("il compte 1 événement terminé (ni le sans-date, ni le récurrent)",
       "l'événement est TERMINÉ    : 1" in sortie, sortie[:600])
_check("   et le nomme, avec sa date de fin",
       "Musicanti Estivo" in sortie and "WP#6501" in sortie, sortie)
_check("il compte 1 image d'emailing", "l'image vient d'un envoi   : 1" in sortie,
       sortie[:600])
_check("   avec le nom de l'hôte à côté", "[mcusercontent.com]" in sortie, sortie)
_check("il rappelle qu'il lit la BASE, pas le site (règle 1)",
       "pas une preuve de ce que le site affiche" in sortie, sortie[:900])

print("\n──── le verdict qui part sur le téléphone ────")
import utils.slack as slack_mod  # noqa: E402
envoyes: list[str] = []
slack_mod.notify = lambda text, blocks=None, urgent=False: envoyes.append(text) or True
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ah.main(["--slack"])
_check("un seul message", len(envoyes) == 1, envoyes)
msg = envoyes[0] if envoyes else ""
_check("il donne les deux comptes sur le total", "sur 4 fiches" in msg, msg)
_check("   et marque en rouge ce qui n'est pas à zéro", msg.count("🔴") == 2, msg)
_check("il tient sur un écran de téléphone", len(msg.splitlines()) <= 8,
       f"{len(msg.splitlines())} lignes")

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
