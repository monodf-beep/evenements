#!/usr/bin/env python3
"""Fixture : une image déjà portée par plusieurs autres fiches est de l'habillage.

LE DIAGNOSTIC ÉTAIT ÉCRIT DEPUIS LE DÉBUT, en commentaire de
config/blocked_image_patterns.txt : « une image partagée par beaucoup d'événements SANS
RAPPORT = presque toujours de l'habillage ». Il y figurait comme requête à taper à la
main pour trouver de nouveaux motifs à ajouter au fichier ; personne ne l'avait branché
sur la chaîne elle-même.

Mesuré le 2026-09-21, sur les fiches publiées encore devant nous :

    7 fiches → Cover L-eta dell-acquario-particolare.png   (bandeau de la bibliothèque)
    2 fiches → visuels-lancement-de-saison-2026-2027.png   (Opéra de Nice)
    2 fiches → img_11.webp                                  (Musei Reali)
    2 fiches → 2006.aerea_.RG-Palazzo-Madama.jpg            (vue aérienne du palais)
    2 fiches → Palazzo-Mazzonis-esterno-3-2.jpg             (façade du MAO)
    2 fiches → 1629_701_CHY_110986_HD-1-1-.jpg              (photo de la ville de Chambéry)

Aucune des défenses posées le même jour ne les aurait arrêtées : ce ne sont ni des
vignettes de PDF, ni des images d'interface, et la page lue est bien celle de
l'événement. Seul leur PARTAGE les trahit.

Le seuil est 2 AUTRES fiches — la troisième déclenche le refus : deux fiches peuvent
légitimement partager une affiche (deux concerts d'un même festival), trois événements
sans rapport, non. Et les traductions ne comptent jamais : elles portent la même image
que leur original, et c'est voulu.

Aucun réseau, base jetable. Lancer : .venv/bin/python -m tests.test_image_partagee
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
from scripts.images_wide import deja_partagee, PARTAGE_MAX  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


BANDEAU = "https://biblio.it/uploads/Cover-L-eta-dell-acquario-particolare.png"
AFFICHE = "https://biblio.it/uploads/mani-in-opera.png"
AUTRE = "https://festival.fr/uploads/affiche-du-festival.jpg"

conn = sqlite3.connect(tmp)
init_db(conn)
# Sept fiches sans rapport portent le bandeau en paysage — le cas réel du 21/09.
for eid, titre in ((1, "Sportello digitale"), (2, "La mossa del lettore"),
                   (3, "Donne controcorrente"), (4, "Fili tra le pagine"),
                   (5, "Mille storie in biblioteca"), (6, "Mani in opera"),
                   (7, "Lavoriamo a maglia")):
    conn.execute("INSERT INTO events_raw (id,title,url_source,statut,url_image,url_image_wide) "
                 "VALUES (?,?,?, 'published_sub', ?, ?)",
                 (eid, titre, f"https://biblio.it/e/{eid}", AFFICHE if eid == 6 else "", BANDEAU))
# Deux fiches d'un même festival partagent légitimement son affiche.
for eid, titre in ((10, "Festival, concert d'ouverture"), (11, "Festival, concert de clôture")):
    conn.execute("INSERT INTO events_raw (id,title,url_source,statut,url_image) "
                 "VALUES (?,?,?, 'published_sub', ?)", (eid, titre, f"https://festival.fr/{eid}", AUTRE))
# Une traduction porte la même image que son original : elle ne doit JAMAIS compter.
conn.execute("INSERT INTO events_raw (id,title,url_source,statut,url_image) "
             "VALUES (20,'Festival, concerto di apertura','translated:10:it','published_sub',?)",
             (AUTRE,))
conn.commit()

print("──── le bandeau partagé est reconnu ────")
_check("vu par six autres fiches depuis la fiche 1", deja_partagee(conn, BANDEAU, 1) == 6,
       str(deja_partagee(conn, BANDEAU, 1)))
_check("… donc au-delà du seuil", deja_partagee(conn, BANDEAU, 1) >= PARTAGE_MAX)

print("\n──── le cas qui doit PASSER : deux fiches d'un même festival ────")
_check("une seule autre fiche porte l'affiche", deja_partagee(conn, AUTRE, 10) == 1,
       str(deja_partagee(conn, AUTRE, 10)))
_check("… donc sous le seuil, l'affiche reste acceptable",
       deja_partagee(conn, AUTRE, 10) < PARTAGE_MAX)

print("\n──── une traduction ne compte pas ────")
_check("la version italienne n'est pas comptée comme une fiche de plus",
       deja_partagee(conn, AUTRE, 11) == 1, str(deja_partagee(conn, AUTRE, 11)))

print("\n──── frontières ────")
_check("image que personne d'autre ne porte → 0", deja_partagee(conn, AFFICHE, 6) == 0)
_check("URL vide → 0, sans requête", deja_partagee(conn, "", 1) == 0)
conn.close()

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
