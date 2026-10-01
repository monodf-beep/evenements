#!/usr/bin/env python3
"""Fixture : « arrivé(s) sur le site » ne compte pas une fiche que le site a GELÉE.

INCIDENT RÉEL, 23 → 28/09 puis 01/10/2026. Le compteur du cron SEO se fonde sur
`published_as_date`, réécrit par toute publication réussie. Une fiche dont le gel n'était
pas encore connu d'ici partait en publication, le site la gelait (aucune méta Yoast
écrite) — et elle était comptée « arrivée » : 91 fiches sur quatre jours, 25 optimisées
pour 21 arrivées le 01/10. Le bilan disait « 25/25 » ; Yoast n'avait rien reçu.

Deux fiches en retard, publiées toutes deux avec succès :
  - id 1 : le site répond qu'elle est gelée → NE doit PAS être comptée arrivée, et le
           bilan doit la nommer à part ;
  - id 2 : le site ne la gèle pas → DOIT être comptée arrivée (le cas qui passe ; sans
           lui, un compteur qui ne compte plus rien serait aussi « juste »).

Aucun réseau : publish_batch_as.main est remplacé.
Lancer : .venv/bin/python -m tests.test_seo_arrivees_gel
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
import scripts.seo_batch as sb  # noqa: E402
import scripts.publish_batch_as  # noqa: E402,F401  (déclare le module avant de le remplacer)
from utils import slack, pipeline_status  # noqa: E402

sb.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    print(("OK    " if cond else "ÉCHEC ") + label, "" if cond else detail)
    if not cond:
        echecs += 1


AUJOURDHUI = "2026-10-01"
conn = sqlite3.connect(tmp)
init_db(conn)
for eid, titre, wp in ((1, "Gelée par le site", 900), (2, "Publiée normalement", 901)):
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, statut, llm_score, seo_at, "
        "published_as_date, wp_post_id_as, date_event_start, date_event_end) "
        "VALUES (?,?,?,'published_cs',8,'2026-10-01 10:30:00','2026-09-20 09:00:00',?,"
        "'2026-12-01','2026-12-01')", (eid, titre, f"https://x/{eid}", wp))
conn.commit()
sb._ensure_seo_pushed_col(conn)
# le rattrapage initial marque comme poussées les fiches publiées APRÈS leur SEO ; ici
# elles sont publiées avant : toutes deux restent en retard.
conn.close()

messages = []
slack.notify = lambda m, *a, **k: messages.append(m)
pipeline_status.record_run = lambda *a, **k: None
sb.date = type("D", (), {"today": staticmethod(lambda: type("d", (), {
    "isoformat": staticmethod(lambda: AUJOURDHUI)})())})
sb.os.environ["ANTHROPIC_API_KEY"] = ""


def _publie(argv):
    """Le site accepte les deux publications ; il gèle la 1 (et publish_batch_as recopie
    ce gel en base via _ranger_gel, ce que fait ici la mise à jour directe)."""
    ids = [int(a) for a in argv[argv.index("--ids") + 1:] if a.isdigit()]
    c = sqlite3.connect(tmp)
    for i in ids:
        c.execute("UPDATE events_raw SET published_as_date='2026-10-01 11:00:00' WHERE id=?", (i,))
        if i == 1:
            c.execute("UPDATE events_raw SET wp_gel_at='2026-09-30', wp_gel_champs='title,content,yoast' WHERE id=1")
    c.commit()
    c.close()
    return 0


sys.modules["scripts.publish_batch_as"].main = _publie
sb.main(["--cap", "0"])

bilan = next((m for m in messages if "SEO quotidien" in m), "")
_check("le bilan existe", bool(bilan), str(messages))
_check("une seule fiche est comptée arrivée (la non gelée)", "(1 arrivé(s) sur le site)" in bilan, bilan)
_check("la fiche gelée est nommée à part, avec son id", "GELÉE" in bilan and "1" in bilan.split("GELÉE")[-1], bilan)
c = sqlite3.connect(tmp)
_check("id 2 (arrivée) est marquée poussée",
       c.execute("SELECT seo_pushed_at FROM events_raw WHERE id=2").fetchone()[0] == "2026-10-01 10:30:00")
_check("id 1 (gelée) n'est PAS marquée poussée : Yoast n'a rien reçu",
       c.execute("SELECT seo_pushed_at FROM events_raw WHERE id=1").fetchone()[0] is None)
c.close()

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
