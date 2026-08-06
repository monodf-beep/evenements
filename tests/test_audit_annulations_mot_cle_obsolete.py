#!/usr/bin/env python3
"""Fixture : une suspicion d'annulation se clôt toute seule si son marqueur a été
retiré de config/annulation_keywords.txt — mais une suspicion toujours valide n'est
JAMAIS touchée par cette voie.

⚠️ BASE JETABLE — jamais data/events.db.

POURQUOI (bilan du matin, 2026-08-06). « report » a été retiré de la liste des
marqueurs le 2026-08-06 : 92 alertes « annulation suspectée » en dix minutes, 0
confirmée par audit_annulations, toutes déclenchées par la clause météo « report en
cas de pluie », omniprésente dans les titres de presse d'événements en plein air. Le
canal Slack était noyé. Mais retirer le mot de la LISTE ne clôt pas les 92 suspicions
DÉJÀ posées en base — elles resteraient à bloquer des fusions pour un marqueur qui
n'existe plus. Ce test prouve la reconciliation : audit_annulations recalcule le
marqueur sur le TITRE ARCHIVÉ avec la liste ACTUELLE, et clôt ce qui ne matche plus.

Ce test lit le VRAI config/annulation_keywords.txt du dépôt (pas une liste de test) :
c'est la garantie que « report » y est bien absent et « annulé » toujours présent
au moment où ce test tourne, pas une hypothèse non vérifiée.

Lancer : .venv/bin/python -m tests.test_audit_annulations_mot_cle_obsolete
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
from scripts.dedupe import ensure_annulation_columns  # noqa: E402
import scripts.audit_annulations as audit  # noqa: E402
from utils.annulation import load_annulation_filter, marqueur_annulation  # noqa: E402

audit.DB_PATH = tmp

echecs = 0


def verifier(libelle, condition, detail=""):
    global echecs
    if condition:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f"\n      {detail}" if detail else ""))


print("──── précondition sur la vraie liste du dépôt ────")
regex = load_annulation_filter()
verifier("« report » n'est plus un marqueur",
         marqueur_annulation("Musical'été : un report en cas de pluie", regex) is None)
verifier("« annulé » l'est toujours",
         marqueur_annulation("Festival des Nuits Alpines annulé", regex) is not None)

conn = sqlite3.connect(tmp)
init_db(conn)
ensure_annulation_columns(conn)
FICHES = [
    # id, titre, statut, wp_post_id_as, visee_id, visee_etait_publiee, detectee
    # 1: la fiche VISÉE par les deux suspects — encore pending, jamais publiée,
    #    donc les résolutions 1-3 (visée absente/rejected/dépubliée) ne s'appliquent
    #    pas : seule la voie 4 (marqueur obsolète) peut clore le suspect 2.
    (1, "Festival des Nuits Alpines", "pending", None),
    # 2: suspect FAUX POSITIF — la clause météo qui a produit les 92 alertes.
    (2, "Musical'été : un report en cas de pluie", "pending", None),
    # 3: suspect TOUJOURS VALIDE — même situation, mot différent, ne doit PAS bouger.
    (3, "Festival des Nuits Alpines annulé", "pending", None),
]
for eid, titre, statut, wp in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, territoire, "
        "statut, wp_post_id_as) VALUES (?,?,?,?,?,?,?)",
        (eid, titre, "matière quelconque", f"https://x.fr/{eid}", "Savoie", statut, wp))
for suspect_id in (2, 3):
    conn.execute(
        "UPDATE events_raw SET annulation_detectee_at=?, annulation_source_url=?, "
        "annulation_fiche_visee_id=1, annulation_visee_etait_publiee=0 WHERE id=?",
        ("2026-08-04 14:01:00", f"https://x.fr/{suspect_id}", suspect_id))
conn.commit()
conn.close()


def _row(eid):
    c = sqlite3.connect(tmp); c.row_factory = sqlite3.Row
    r = dict(c.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())
    c.close()
    return r


print("\n──── avant l'audit : les deux suspicions sont actives ────")
verifier("suspect 2 (report) actif avant", bool(_row(2)["annulation_detectee_at"]))
verifier("suspect 3 (annulé) actif avant", bool(_row(3)["annulation_detectee_at"]))

print("\n──── l'audit tourne ────")
import io, logging
buf = io.StringIO()
h = logging.StreamHandler(buf)
h.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger("audit-annulations").addHandler(h)
rc = audit.main([])
sortie = buf.getvalue()

verifier("code de sortie 0", rc == 0)
verifier("le suspect « report » est clôturé automatiquement",
         not _row(2)["annulation_detectee_at"])
verifier("le suspect « annulé » reste actif, jamais touché par cette voie",
         bool(_row(3)["annulation_detectee_at"]))
verifier("le journal compte une clôture pour marqueur obsolète",
         "1 clôturée(s) (marqueur retiré de la liste)" in sortie, sortie)
verifier("le suspect encore valide apparaît en attente",
         "suspect [3]" in sortie, sortie)
verifier("le suspect clôturé n'apparaît plus en attente",
         "suspect [2]" not in sortie, sortie)

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
