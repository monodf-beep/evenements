#!/usr/bin/env python3
"""Fixture : le tri des fiches sans date range, et ne décide pas.

79 fiches sans date au 2026-08-11, dont on a établi qu'elles n'en ont pas parce qu'il n'y
en a pas à trouver : des saisons, des programmes, des offres, quelques fiches vides. Le
tri sert à ce que Franck n'ouvre pas 79 pages pour s'en apercevoir.

Le danger de ce genre d'outil est nommé dans la charte : « Le partage se fait sur À QUI
ÇA S'ADRESSE, jamais sur le mot du titre. » Un tri par mots-clés qui se prendrait pour un
verdict trierait faux, et vite. La fixture vérifie donc DEUX choses de nature différente :
que le rangement est utile, ET qu'il n'écrit rien.

Les cas sont pris sur de vrais titres de la base (Serralunga, l'Offre VIP du Nice Jazz
Fest, Talent in Tech, la fiche 2676 au titre vide) et incluent des cas qui doivent
tomber dans « événement », c'est-à-dire ne PAS être attrapés — un tri qui range tout
quelque part ne prouve rien.

Lancer : .venv/bin/python -m tests.test_trier_sans_date
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
import scripts.trier_sans_date as tri  # noqa: E402

tri.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# (titre, groupe attendu, pourquoi ce cas est là)
CAS = [
    ("", "vide", "fiche 2676 : aucun titre, rien à publier"),
    # Passé de « saison » à « activité » lors de l'élargissement : des balades
    # accompagnées sont une activité qui se répète. Les deux paniers suggèrent la MÊME
    # sortie (« récurrent »), donc le classement exact importe moins que le fait qu'elle
    # ne reste pas dans « événement ».
    ("Serralunga: le passeggiate accompagnate del 2026", "activité",
     "des balades accompagnées : une activité qui se répète"),
    ("Stagione 2026 – 2027", "saison", "une saison entière"),
    ("Programme des ateliers du centre socioculturel", "saison", "programme d'ateliers"),
    ("Nice Jazz Fest 2026 - Offre VIP", "professionnel", "une offre commerciale"),
    ("Talent in Tech", "professionnel", "un événement professionnel"),
    # ── Ce qui doit RESTER dans « événement » : la frontière est là, pas ailleurs ──
    ("Per Olivia", "événement", "un vrai spectacle, simplement non daté"),
    ("I duellanti", "événement", "une rencontre littéraire"),
    ("Concert de Katy Perry", "événement", "aucun mot-indice"),
    # Piège volontaire : « salon du livre » EST dans le catalogue (charte, onze
    # catégories). Le tri ne doit pas l'attraper avec « salon des… ».
    ("Salon du livre de Chambéry", "événement",
     "un salon du livre reste dans le catalogue — le tri ne doit pas le confondre"),
    # Piège inverse : « Conférences & Rencontres » est une catégorie du site, une
    # conférence de musée n'est PAS un colloque professionnel.
    ("Conférence : l'art des jardins alpestres", "événement",
     "une conférence de musée n'est pas un colloque"),
    # ── Élargissement du 2026-08-11, sur les titres RÉELS de la production ──────
    # La première version rangeait 70 fiches sur 75 dans « événement » : elle ne triait
    # rien. Ces cas viennent tous de la liste affichée ce matin-là.
    ("Sere d'Estate alla Reggia di Venaria", "saison", "une série sur tout l'été"),
    ("AGOSTO AI MUSEI REALI DI TORINO", "saison", "un mois de programmation"),
    ("Armonie Reali. Musica nelle Residenze Sabaude", "saison", "un cycle de concerts"),
    ("Fénis: un été à vivre", "saison", "un programme d'été"),
    ("Mostra Internazionale della Ceramica", "exposition", "une exposition court des mois"),
    ("Due esposizioni di Barbara Tutino a Cogne", "exposition", "deux expositions"),
    ("Aperture serali della Basilica di Superga", "activité", "des ouvertures du soir"),
    ("Percorsi enogastronomici Casa Martini", "activité", "des parcours, pas une date"),
    ("Balade gourmande aux Charmettes", "activité", "une balade qui se répète"),
    # ── Et surtout : ce qui doit RESTER « événement » après l'élargissement ──────
    # C'est ici que se joue la valeur du tri. Ces cinq-là ONT une date dans le monde
    # réel — on ne l'a simplement pas extraite. Les ranger en « récurrent » masquerait
    # de vrais événements derrière un renvoi à la source.
    ("Journées européennes du Patrimoine", "événement", "un week-end précis de septembre"),
    ("Notte di San Lorenzo", "événement", "la nuit du 10 août, une date fixe"),
    ("Championnats d'Europe de VTT Trial", "événement", "une compétition datée"),
    ("Concerto della Filarmonica della Scala", "événement", "un concert, un soir"),
    ("Gran Balon", "événement", "une brocante à date fixe"),
    # ── Second élargissement, même matin, même méthode : lire la liste réelle ────
    ("Visite commentée : L'heure du thé aux Charmettes", "activité",
     "« commentée » manquait alors que « guidée » y était — même chose, autre mot"),
    ("Bien-être aux Charmettes : Pilates", "activité", "un cours qui revient"),
    ("Domenica al Museo", "activité", "un rendez-vous mensuel"),
    ("Cinema sotto le stelle e musica elettronica", "activité", "des séances d'été"),
    # Et la frontière, encore : un thé dansant et un festival ont une date.
    ("Thé dansant", "événement", "un après-midi précis, pas une activité permanente"),
    ("Torino Opera Festival", "événement", "un festival a des dates"),
]

conn = sqlite3.connect(tmp)
init_db(conn)
for i, (titre, _g, _p) in enumerate(CAS, start=1):
    conn.execute(
        "INSERT INTO events_raw (id,title,url_source,statut,date_event_start,llm_score) "
        "VALUES (?,?,?, 'evaluated', '', 7)", (i, titre, f"https://x/{i}"))
# Fiches qui ne doivent PAS entrer dans la file du tout.
conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start,recurring)"
             " VALUES (90,'Déjà récurrent','https://x/90','evaluated','',1)")
conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start) "
             "VALUES (91,'Datée','https://x/91','evaluated','2026-12-01')")
conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start) "
             "VALUES (92,'Rejetée','https://x/92','rejected','')")
conn.commit()
conn.close()

print("──── rangement ────")
for i, (titre, attendu, pourquoi) in enumerate(CAS, start=1):
    obtenu = tri._groupe({"title": titre})
    _check(f"{obtenu:14} ← « {(titre or '(vide)')[:44]:44} » ({pourquoi})",
           obtenu == attendu, f"attendu {attendu}")

# ── La file elle-même : qui n'y entre pas ──────────────────────────────────────
print("\n──── périmètre de la file ────")
import io                                                        # noqa: E402
import contextlib                                                # noqa: E402
sortie = io.StringIO()
with contextlib.redirect_stdout(sortie):
    code = tri.main([])
texte = sortie.getvalue()
_check("code retour 0", code == 0, str(code))
_check("un récurrent n'est pas dans la file", "Déjà récurrent" not in texte)
_check("une fiche datée n'est pas dans la file", "Datée" not in texte)
_check("une fiche rejetée n'est pas dans la file", "Rejetée" not in texte)
_check("l'avertissement sur le mot du titre est affiché",
       "À QUI ÇA S'ADRESSE" in texte, texte[:200])
_check("le script annonce n'avoir rien modifié", "RIEN N'A ÉTÉ MODIFIÉ" in texte)

# ── Et surtout : il n'écrit rien ────────────────────────────────────────────────
conn = sqlite3.connect(tmp)
inchange = conn.execute(
    "SELECT COUNT(*) FROM events_raw WHERE COALESCE(recurring,0)=1").fetchone()[0]
statuts = conn.execute(
    "SELECT COUNT(*) FROM events_raw WHERE statut='rejected'").fetchone()[0]
conn.close()
_check("aucune fiche n'a été marquée récurrente", inchange == 1, str(inchange))
_check("aucune fiche n'a été rejetée", statuts == 1, str(statuts))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
