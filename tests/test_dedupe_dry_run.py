#!/usr/bin/env python3
"""Fixture : `dedupe.py --dry-run` n'écrit RIEN, et dit la même chose que le vrai passage.

⚠️ BASE JETABLE (init_db sur un fichier temporaire). Aucun réseau.

D'OÙ ÇA VIENT. 04-05/09 : le dédoublonnage a raté un doublon en ligne (Salone Auto
Torino, deux fiches FR) et fusionné à tort ailleurs (Terra Madre absorbé par une expo de
jardins). Avant de toucher au critère, il fallait pouvoir LIRE ce qu'il fusionnerait —
or le script écrivait d'office, à rebours de la règle 4 du dépôt, et tout commit part en
production à 7h50 sans qu'un humain ait vu la liste. Ce mode est le préalable.

CE QU'ELLE VÉRIFIE :
  1. en --dry-run, la base est INTACTE après le passage (aucun statut 'merged', aucun
     duplicate_of) — c'est tout l'objet ;
  2. l'aperçu nomme le groupe, son gagnant et son perdant, avec les ids ;
  3. ⚠️ LE CAS QUI DOIT PASSER : sans --dry-run, le MÊME script, sur la MÊME base, fusionne
     bien le groupe annoncé. Sans ce contrôle, un dry-run qui n'annoncerait jamais rien
     passerait au vert ;
  4. la fiche sans rapport n'est touchée dans aucun des deux modes.

Lancer : .venv/bin/python -m tests.test_dedupe_dry_run
"""
import contextlib
import io
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db   # noqa: E402
import scripts.dedupe as dd                   # noqa: E402

dd.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


conn = sqlite3.connect(tmp)
init_db(conn)
# Deux titres qui partagent ≥ 3 mots significatifs (musilac, programmation, complète),
# même territoire, mêmes dates → same_story dit OUI. Le troisième n'a rien à voir.
fiches = [
    (1, "Festival Musilac 2026 : programmation complète dévoilée",
     "https://www.musilac.com/programmation", "Savoie"),
    (2, "Musilac 2026 dévoile sa programmation complète au bord du lac",
     "https://www.ledauphine.com/musilac-2026", "Savoie"),
    (3, "Concert de jazz au Brise Glace", "https://www.le-brise-glace.com/jazz", "Savoie"),
]
for i, titre, url, terr in fiches:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, territoire, statut, "
        "date_event_start, date_event_end, description) VALUES (?,?,?,?,'pending',"
        "'2026-07-10','2026-07-13','')", (i, titre, url, terr))
conn.commit(); conn.close()


def etat():
    c = sqlite3.connect(tmp)
    rows = c.execute("SELECT id, statut, duplicate_of FROM events_raw ORDER BY id").fetchall()
    c.close()
    return rows


print("──── --dry-run : n'écrit rien, mais dit tout ────")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = dd.main(["--dry-run"])
s = buf.getvalue()
_check("le script rend 0", rc == 0)
_check("la base est INTACTE (aucun 'merged', aucun duplicate_of)",
       all(st == "pending" and dup is None for _i, st, dup in etat()), etat())
_check("l'aperçu annonce 1 groupe", "1 groupe(s) de doublons" in s, s[:300])
_check("   il nomme un gagnant", "GAGNANT id=" in s, s)
_check("   et le perdant, avec les deux ids 1 et 2",
       "fusionné id=" in s and ("id=1" in s and "id=2" in s), s)
_check("   la fiche sans rapport (3) n'y figure pas", "id=3" not in s, s)

print("\n──── ⚠️ le cas qui doit passer : le VRAI passage fusionne bien ce qui était annoncé ────")
with contextlib.redirect_stdout(io.StringIO()):
    rc2 = dd.main([])
apres = {i: (st, dup) for i, st, dup in etat()}
merged = [i for i, (st, _d) in apres.items() if st == "merged"]
_check("exactement UNE fiche est passée 'merged'", len(merged) == 1, apres)
if merged:
    perdant = merged[0]
    gagnant = apres[perdant][1]
    _check("   elle pointe vers l'autre fiche du groupe (1 ou 2)",
           {perdant, gagnant} == {1, 2}, apres)
_check("   la fiche 3, sans rapport, est toujours 'pending'", apres[3] == ("pending", None), apres)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
