#!/usr/bin/env python3
"""Fixture : une traduction montre la même image que son original.

2026-09-21, fiche « Orlando » (Opéra Nice Côte d'Azur). La version française portait
l'affiche du spectacle — l'og:image de `opera-nice.org/agenda/orlando/`. L'italienne
portait un scan du LIVRET IMPRIMÉ du XVIIIe siècle trouvé sur Wikimedia Commons : deux
colonnes de texte en italien et en anglais, illisibles en vignette. Même événement, deux
images.

L'enchaînement, reconstitué : `translate_events` copie bien `url_image` à la CRÉATION de
la traduction ; si l'original n'a alors qu'une bannière, la traduction hérite de la
bannière, `visuals` la reprend plus tard comme fiche à compléter — et là `url_source` vaut
`translated:<id>:<lang>`, il n'y a aucune page à lire, la chaîne saute donc directement à
l'étage Commons. Quand l'original reçoit enfin sa vraie affiche, rien ne réaligne la
traduction.

L'héritage se fait donc à la PUBLICATION, au même endroit que celui de la source
(`_heriter_source_traduction`, incident du 16/09), et seulement vers le HAUT : ce qui est
vérifié ici, c'est autant ce qu'il copie que ce qu'il refuse de copier.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_heriter_image_traduction
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
from scripts.publish_batch_as import _heriter_image_traduction  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


AFFICHE = "https://www.opera-nice.org/wp-content/uploads/2026/05/30-06-10-orlando.jpg"
LIVRET = "https://upload.wikimedia.org/wikipedia/commons/1/1c/Orlando_Argomento.jpg"
BANNIERE = "https://agendasabauda.eu/fallback-comte-de-nice-spectacle-vivant.png"
MAIN = "https://x.fr/photo-choisie-a-la-main.jpg"

conn = sqlite3.connect(tmp)
init_db(conn)


def _ajoute(eid, titre, img, source, parent=None):
    conn.execute("INSERT INTO events_raw (id,title,url_source,statut,url_image,image_source,"
                 "image_credit,translation_of) VALUES (?,?,?, 'published_sub', ?,?,'',?)",
                 (eid, titre, f"translated:{parent}:it" if parent else f"https://x.fr/e/{eid}",
                  img, source, parent))


_ajoute(1, "Orlando", AFFICHE, "og")
_ajoute(2, "Orlando (it)", LIVRET, "commons", parent=1)
_ajoute(3, "Concert", BANNIERE, "banner")
_ajoute(4, "Concerto (it)", MAIN, "manual", parent=3)
_ajoute(5, "Expo", AFFICHE, "og")
_ajoute(6, "Mostra (it)", BANNIERE, "banner", parent=5)
_ajoute(7, "Sans parent", LIVRET, "commons")
conn.commit()


def _relire(eid):
    r = conn.execute("SELECT url_image, image_source FROM events_raw WHERE id=?", (eid,)).fetchone()
    return {"url_image": r[0], "image_source": r[1]}


conn.row_factory = sqlite3.Row


def _charger(eid):
    return dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())


print("──── le cas Orlando : commons (2) cède à og (4) ────")
ev = _charger(2)
_heriter_image_traduction(ev, conn)
_check("la traduction reprend l'affiche de l'original", ev["url_image"] == AFFICHE, ev["url_image"])
_check("… et la base aussi, pas seulement l'objet en mémoire",
       _relire(2)["url_image"] == AFFICHE, str(_relire(2)))
_check("… avec la provenance de l'original", ev["image_source"] == "og", ev["image_source"])

print("\n──── ce qu'il doit REFUSER de copier ────")
ev4 = _charger(4)
_heriter_image_traduction(ev4, conn)
_check("une image posée À LA MAIN sur la traduction n'est jamais écrasée par une bannière",
       ev4["url_image"] == MAIN and _relire(4)["url_image"] == MAIN, ev4["url_image"])

print("\n──── et ce qu'il doit copier, près de la frontière ────")
ev6 = _charger(6)
_heriter_image_traduction(ev6, conn)
_check("une bannière (1) cède à la vraie affiche de l'original (4)",
       ev6["url_image"] == AFFICHE and _relire(6)["url_image"] == AFFICHE, ev6["url_image"])

print("\n──── une fiche sans parent n'est pas touchée ────")
ev7 = _charger(7)
_heriter_image_traduction(ev7, conn)
_check("rien ne bouge", ev7["url_image"] == LIVRET and _relire(7)["url_image"] == LIVRET)

conn.close()
print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
