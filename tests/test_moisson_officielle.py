#!/usr/bin/env python3
"""Fixture : une page officielle lue UNE fois remplit tous les champs vides d'un coup —
et n'écrase jamais rien.

Franck, 2026-08-11 : « la complétion des informations grâce aux infos officielles devrait
se faire, alors qu'actuellement ce n'est pas le cas ». Trois crons savent lire une page
officielle et chacun n'y prend qu'un champ, chacun avec son propre délai de carence :
il suffit que l'horloge des dates soit fermée pour que le lieu et l'image, pourtant dans
la même page, ne soient pas récoltés. Constaté le soir même : « 0 page(s) à lire » côté
dates ET côté lieux, avec 79 fiches sans date et 31 sans lieu.

Ce que la fixture vérifie, en particulier ce qui doit NE PAS bouger :
  • les champs vides sont remplis depuis le JSON-LD et l'og:image ;
  • un champ DÉJÀ renseigné n'est jamais écrasé — c'est la leçon du 2026-08-09, quand le
    pipeline a remplacé une vraie photo posée à la main par une image de repli ;
  • une page muette ne pose AUCUN verdict : la fiche reste candidate pour dates.py, on
    ne lui consomme pas un délai de carence pour un essai qui n'a rien coûté ;
  • une fiche sans page téléchargeable (« gmail:… ») est ignorée, pas tentée ;
  • le passé est écarté (règle 5) ;
  • en simulation, RIEN n'est écrit.

Aucun réseau : le téléchargement est monkey-patché.

Lancer : .venv/bin/python -m tests.test_moisson_officielle
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
import scripts.moisson_officielle as mo  # noqa: E402

mo.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


PAGE_RICHE = '''<html><head>
<meta property="og:image" content="https://officiel.fr/affiche.jpg">
<script type="application/ld+json">{"@type":"Event","name":"Concert",
"startDate":"2026-12-05","endDate":"2026-12-06",
"location":{"@type":"Place","name":"Théâtre Charles Dullin",
"address":{"addressLocality":"Chambéry"}}}</script>
</head><body>Concert</body></html>'''
PAGE_MUETTE = "<html><head><title>Rien</title></head><body>Aucune donnée.</body></html>"


class _Rep:
    def __init__(self, text):
        self.text = text


AUJOURDHUI = "2026-08-11"
PAGES = {
    "https://officiel.fr/riche": PAGE_RICHE,
    "https://officiel.fr/muette": PAGE_MUETTE,
    "https://officiel.fr/deja": PAGE_RICHE,
    "https://officiel.fr/riche2": PAGE_RICHE,
}
mo._robust_get = lambda url: _Rep(PAGES[url]) if url in PAGES else None
mo.fetch_og_image = lambda url, timeout=8: (
    "https://officiel.fr/affiche.jpg" if PAGES.get(url) == PAGE_RICHE else "")

conn = sqlite3.connect(tmp)
init_db(conn)
# (id, url_source, date_start, lieu, ville, image, date_end)
CAS = [
    (1, "https://officiel.fr/riche",  "", "", "", "", "2026-12-31"),
    (2, "https://officiel.fr/muette", "", "", "", "", "2026-12-31"),
    (3, "https://officiel.fr/deja",   "2026-11-11", "Ma salle", "Ma ville",
     "https://vraie-photo-posee-a-la-main.jpg", "2026-11-11"),
    (4, "gmail:abc#1",                "", "", "", "", "2026-12-31"),
    (5, "https://officiel.fr/riche2", "", "", "", "", "2026-05-01"),   # PASSÉE
]
for eid, url, ds, lieu, ville, img, fin in CAS:
    conn.execute(
        "INSERT INTO events_raw (id,title,url_source,statut,date_event_start,lieu,ville,"
        "url_image,date_event_end) VALUES (?,?,?, 'evaluated', ?,?,?,?,?)",
        (eid, f"Fiche {eid}", url, ds, lieu, ville, img, fin))
conn.commit()

print("──── sélection ────")
conn.row_factory = sqlite3.Row
cibles = {e["id"] for e in mo._a_moissonner(conn, AUJOURDHUI, 50)}
_check("la fiche incomplète avec page est retenue", 1 in cibles, str(sorted(cibles)))
_check("la fiche « gmail: » est ignorée (rien à télécharger)", 4 not in cibles,
       str(sorted(cibles)))
_check("la fiche PASSÉE est écartée (règle 5)", 5 not in cibles, str(sorted(cibles)))
_check("la fiche complète n'est pas retenue", 3 not in cibles, str(sorted(cibles)))
conn.close()

print("\n──── simulation : rien n'est écrit ────")
mo.main([])
conn = sqlite3.connect(tmp)
avant = conn.execute("SELECT date_event_start, lieu FROM events_raw WHERE id=1").fetchone()
conn.close()
_check("la fiche 1 est toujours vide après simulation", avant == ("", ""), str(avant))

print("\n──── --apply : la page riche remplit tout d'un coup ────")
mo.main(["--apply"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
f1 = dict(conn.execute("SELECT * FROM events_raw WHERE id=1").fetchone())
f2 = dict(conn.execute("SELECT * FROM events_raw WHERE id=2").fetchone())
f3 = dict(conn.execute("SELECT * FROM events_raw WHERE id=3").fetchone())
conn.close()

_check("date de début récoltée", f1["date_event_start"] == "2026-12-05", str(f1["date_event_start"]))
# La fin SUIT le début : la fiche portait « 2026-12-31 » (une borne venue d'ailleurs),
# et comme le début vient d'être posé depuis cette page, la fin est reprise avec lui.
# Garder les deux bornes de sources différentes fabriquerait un intervalle faux.
_check("date de fin récoltée, et elle suit son début",
       f1["date_event_end"] == "2026-12-06", str(f1["date_event_end"]))
_check("lieu récolté", f1["lieu"] == "Théâtre Charles Dullin", str(f1["lieu"]))
_check("ville récoltée", f1["ville"] == "Chambéry", str(f1["ville"]))
_check("image récoltée", f1["url_image"] == "https://officiel.fr/affiche.jpg",
       str(f1["url_image"]))
_check("date_source='page' posée quand on a TROUVÉ", f1["date_source"] == "page",
       str(f1["date_source"]))

# Le cas qui compte le plus : ne rien trouver ne doit RIEN fermer.
_check("page muette : aucun verdict de date posé (la fiche reste candidate)",
       not (f2["date_source"] or ""), repr(f2["date_source"]))
_check("page muette : aucun verdict de lieu posé",
       not (f2["venue_source"] or ""), repr(f2["venue_source"]))

# Et celui qui a déjà coûté cher en production : ne JAMAIS écraser.
_check("la vraie photo posée à la main n'est PAS écrasée",
       f3["url_image"] == "https://vraie-photo-posee-a-la-main.jpg", str(f3["url_image"]))
_check("le lieu saisi à la main n'est PAS écrasé", f3["lieu"] == "Ma salle", str(f3["lieu"]))
_check("la date saisie à la main n'est PAS écrasée",
       f3["date_event_start"] == "2026-11-11", str(f3["date_event_start"]))

# ── La bannière est une place vide, la vraie photo ne l'est pas ─────────────────
# Mesuré le 2026-08-11 avec --diagnostic : 36 des 53 pages « muettes » portaient un
# og:image que la moisson n'a PAS pris, parce qu'elle ne regardait que « url_image est
# vide ». La veille, un run sans-API avait posé une bannière générique sur 40 fiches :
# le pis-aller bloquait l'accès à la vraie affiche.
print("\n──── bannière : une place vide, pas une image ────")
conn = sqlite3.connect(tmp)
conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start,lieu,"
             "ville,url_image,image_source,date_event_end) VALUES "
             "(6,'Sur bannière','https://officiel.fr/banniere','evaluated','2026-12-01',"
             "'Salle','Ville','https://banniere-generique.png','banner','2026-12-01')")
conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start,lieu,"
             "ville,url_image,image_source,date_event_end) VALUES "
             "(7,'Vraie photo','https://officiel.fr/photo','evaluated','2026-12-01',"
             "'Salle','Ville','https://sa-vraie-affiche.jpg','og','2026-12-01')")
conn.commit()
PAGES["https://officiel.fr/banniere"] = PAGE_RICHE
PAGES["https://officiel.fr/photo"] = PAGE_RICHE

conn.row_factory = sqlite3.Row
cibles2 = {e["id"] for e in mo._a_moissonner(conn, AUJOURDHUI, 50)}
_check("la fiche sur BANNIÈRE est reprise (il lui manque une vraie affiche)",
       6 in cibles2, str(sorted(cibles2)))
_check("la fiche à VRAIE photo n'est pas reprise", 7 not in cibles2, str(sorted(cibles2)))
conn.close()

mo.main(["--apply", "6", "7"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
f6 = dict(conn.execute("SELECT * FROM events_raw WHERE id=6").fetchone())
f7 = dict(conn.execute("SELECT * FROM events_raw WHERE id=7").fetchone())
conn.close()
_check("la bannière est remplacée par l'og:image de la page officielle",
       f6["url_image"] == "https://officiel.fr/affiche.jpg", str(f6["url_image"]))
_check("… et sa provenance suit (plus jamais reprise pour ce motif)",
       f6["image_source"] == "og", str(f6["image_source"]))
_check("la vraie photo existante n'est PAS remplacée",
       f7["url_image"] == "https://sa-vraie-affiche.jpg", str(f7["url_image"]))

# ── Aucune récolte sur un domaine de presse ────────────────────────────────────
# Franck, 2026-08-11, en lisant la sortie : « il semble encore y avoir du radar ! » —
# la moisson proposait l'og:image de guidatorino.com, quotidianopiemontese.it et
# aostaoggi.it. Le contrat radar dit « DÉTECTER, jamais créditer ni lier », et une photo
# de presse appartient au journal. On ne prend RIEN de ces pages, pas même la date : un
# article « que faire ce week-end » parle de dix événements, et la date qu'on y lirait
# risque d'être celle d'un autre (c'est ainsi que WP#6798 a porté la date d'un voisin).
print("\n──── presse : rien n'est récolté ────")
PRESSE = [
    (10, "https://www.guidatorino.com/evenement-x"),
    (11, "https://www.quotidianopiemontese.it/evenement-y"),
    (12, "https://www.aostaoggi.it/evenement-z"),
]
conn = sqlite3.connect(tmp)
for eid, url in PRESSE:
    PAGES[url] = PAGE_RICHE          # la page EST riche : seul le domaine la disqualifie
    conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start,"
                 "lieu,ville,url_image,date_event_end) VALUES (?,?,?, 'evaluated', "
                 "'','','','', '2026-12-31')", (eid, f"Presse {eid}", url))
conn.commit()
conn.row_factory = sqlite3.Row
cibles3 = {e["id"] for e in mo._a_moissonner(conn, AUJOURDHUI, 50)}
for eid, url in PRESSE:
    _check(f"écarté — {url.split('/')[2]}", eid not in cibles3, str(sorted(cibles3)))
_check("une page officielle riche reste, elle, récoltable",
       any(mo._url_telechargeable(dict(r)) for r in
           conn.execute("SELECT * FROM events_raw WHERE id=1")))
conn.close()

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
