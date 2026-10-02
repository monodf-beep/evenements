#!/usr/bin/env python3
"""Fixture : scripts/poser_images_manuelles.py pose la photo sur TOUT le groupe (original
+ traductions), vide les colonnes portrait/paysage, ne touche à rien d'autre, et n'écrit
RIEN sans --apply.

Cas qui doit PASSER près de la frontière : une liste donnant l'id WordPress de la
TRADUCTION (versant italien) doit atteindre aussi l'original et ses autres traductions.

Aucun réseau (la republication est interceptée). Lancer :
.venv/bin/python -m tests.test_poser_images_manuelles
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.poser_images_manuelles as pim  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


tmp = Path(tempfile.mkdtemp())
db = tmp / "events.db"
c = sqlite3.connect(db)
c.execute("CREATE TABLE events_raw (id INTEGER PRIMARY KEY, translation_of INT, "
          "duplicate_of INT, wp_post_id_as INT, statut TEXT, url_image TEXT, "
          "image_source TEXT, image_credit TEXT, url_image_portrait TEXT, url_image_wide TEXT)")
c.executemany("INSERT INTO events_raw VALUES (?,?,?,?,?,?,?,?,?,?)", [
    (1, None, None, 100, "published_sub", "https://x/fallback.png", "banner", "", "https://x/saison.jpg", "https://x/w.jpg"),
    (2, 1, None, 200, "published_sub", "https://x/fallback.png", "banner", "", "", ""),
    (3, None, None, 300, "published_sub", "https://x/autre.jpg", "og", "", "", ""),   # sans rapport
    (4, None, None, 0, "evaluated", "", "", "", "", ""),                             # pas en ligne
    (5, 4, None, 0, "evaluated", "", "", "", "", ""),
])
c.commit()
c.close()
pim.DB_PATH = db
appels = []
pim.subprocess.call = lambda cmd: appels.append(cmd) or 0

liste = tmp / "l.tsv"
liste.write_text("# commentaire\n200\thttps://musee/photo.jpg\tMusée\tce qu'on voit\n"
                 "999\thttps://musee/rien.jpg\tMusée\n", encoding="utf-8")

# ── Simulation : rien n'est écrit ────────────────────────────────────────────────
pim.main([str(liste)])
r = sqlite3.connect(db).execute("SELECT url_image FROM events_raw WHERE id=1").fetchone()[0]
_check("sans --apply : rien n'est écrit", r == "https://x/fallback.png", r)
_check("sans --apply : aucune republication", not appels)

# ── Application ─────────────────────────────────────────────────────────────────
pim.main([str(liste), "--apply"])
c = sqlite3.connect(db)
c.row_factory = sqlite3.Row
g = {r["id"]: dict(r) for r in c.execute("SELECT * FROM events_raw")}
_check("id de la TRADUCTION → l'original reçoit la photo",
       g[1]["url_image"] == "https://musee/photo.jpg" and g[1]["image_source"] == "manual")
_check("… et la traduction aussi", g[2]["url_image"] == "https://musee/photo.jpg")
_check("crédit posé", g[1]["image_credit"] == "Musée" and g[2]["image_credit"] == "Musée")
_check("portrait et paysage VIDÉS (sinon la vignette garde l'ancienne affiche)",
       g[1]["url_image_portrait"] == "" and g[1]["url_image_wide"] == "")
_check("une fiche sans rapport n'est pas touchée",
       g[3]["url_image"] == "https://x/autre.jpg" and g[3]["image_source"] == "og")
_check("republication des SEULES fiches en ligne du groupe",
       appels and appels[-1][-2:] == ["1", "2"], str(appels))

# ── Ligne mal formée : refus bruyant, pas un saut silencieux ────────────────────
mauvaise = tmp / "m.tsv"
mauvaise.write_text("abc\thttps://x\tc\n", encoding="utf-8")
try:
    pim.main([str(mauvaise)])
    _check("ligne mal formée refusée", False)
except SystemExit as e:
    _check("ligne mal formée refusée", "mal formée" in str(e))

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)")
    sys.exit(1)
print("Tout passe.")
