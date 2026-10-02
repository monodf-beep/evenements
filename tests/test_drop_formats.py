#!/usr/bin/env python3
"""Fixture : le rouvreur des déclinaisons portrait ET paysage (images_wide).

2026-09-21, fiche « Charcot Antartica » (id 5261, WP#8289). Franck : « c'est souvent qu'on
a l'image de malraux au lieu de l'événement ». La fiche avait pourtant la BONNE photo dans
`url_image` (og:image de la page du spectacle) — mais `url_image_portrait` portait la
couverture de la brochure de saison 26-27, et `publisher_as` préfère le portrait pour la
vignette de carte. Le paysage, lui, portait le plan de la grande salle. Les deux venaient
du pied de page du site, qui affiche les couvertures de ses PDF sur toutes ses pages.

`--drop-portrait` existait ; `--drop-wide` n'existait pas. Une moitié de rouvreur laissait
le plan de salle en place comme grand visuel 16:9 — le cul-de-sac de la règle 3, à moitié
rouvert.

Vérifié ici, sur une base jetable et sans réseau (aucune fiche n'a de `wp_post_id_as`,
donc aucun push) :
  • le DRY-RUN n'écrit rien (règle 4) ;
  • `--apply` efface les deux colonnes demandées, et UNIQUEMENT elles ;
  • `url_image`, qui est juste, n'est jamais touchée — c'est elle que la carte reprend ;
  • le cas qui doit PASSER, près de la frontière : `--drop-portrait` seul ne touche pas au
    paysage (une affiche paysage légitime ne doit pas partir avec un portrait fautif).

Lancer : .venv/bin/python -m tests.test_drop_formats
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
import scripts.images_wide as iw  # noqa: E402

iw.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


BROCHURE = "https://cdn.malrauxchambery.fr/uploads/M-Brochure-26-27-WEB-pdf.jpg"
PLAN = "https://cdn.malrauxchambery.fr/uploads/Plan_grande_salle_malraux-pdf.jpg"
VRAIE = "https://cdn.malrauxchambery.fr/uploads/charcot-Antartica-Anne-Bouillot-WEB.jpg"

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, titre, portrait, wide in (
        (1, "Charcot Antarctica", BROCHURE, PLAN),
        (2, "Parfums de la Terre", BROCHURE, PLAN),
        (3, "Affiche paysage légitime", BROCHURE, "https://x.fr/uploads/affiche-paysage.jpg")):
    conn.execute("INSERT INTO events_raw (id,title,url_source,statut,url_image,"
                 "url_image_portrait,url_image_wide) VALUES (?,?,?, 'published_sub', ?,?,?)",
                 (eid, titre, f"https://x.fr/e/{eid}", VRAIE, portrait, wide))
conn.commit()
conn.close()


def _lire(eid):
    c = sqlite3.connect(tmp)
    c.row_factory = sqlite3.Row
    r = dict(c.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())
    c.close()
    return r


print("──── DRY-RUN : rien n'est écrit ────")
iw.main(["1", "--drop-portrait", "--drop-wide"])
r = _lire(1)
_check("le portrait fautif est toujours là après un dry-run", r["url_image_portrait"] == BROCHURE)
_check("le paysage fautif aussi", r["url_image_wide"] == PLAN)

print("\n──── --apply : les deux déclinaisons partent, l'image principale reste ────")
iw.main(["1", "2", "--drop-portrait", "--drop-wide", "--apply"])
for eid in (1, 2):
    r = _lire(eid)
    _check(f"[{eid}] portrait effacé", not (r["url_image_portrait"] or ""), str(r["url_image_portrait"]))
    _check(f"[{eid}] paysage effacé", not (r["url_image_wide"] or ""), str(r["url_image_wide"]))
    _check(f"[{eid}] url_image INTACTE — c'est elle que la carte reprend", r["url_image"] == VRAIE)

print("\n──── le cas qui doit PASSER : --drop-portrait seul ne touche pas au paysage ────")
iw.main(["3", "--drop-portrait", "--apply"])
r = _lire(3)
_check("portrait effacé", not (r["url_image_portrait"] or ""))
_check("l'affiche paysage légitime est conservée",
       r["url_image_wide"] == "https://x.fr/uploads/affiche-paysage.jpg", str(r["url_image_wide"]))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
