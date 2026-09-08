#!/usr/bin/env python3
"""Fixture : la suspicion d'annulation bloque la fusion, alerte une fois, et se
résout selon que la fiche visée était publiée ou non au moment du signal.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau : slack.notify est mocké
pour ne rien poster, seulement compter les appels.

DEUX SCÉNARIOS, parce que crontab.txt le prouve : le dedupe quotidien tourne SANS
--rescan (`30 8 * * * ... dedupe.py`), donc il ne compare que des fiches encore
'pending' entre elles — le cas courant (scénario A) est une fiche PAS ENCORE
publiée. Le cas d'une fiche déjà en ligne (scénario B) n'arrive qu'avec --rescan.
Un premier jet de ce test ne testait QUE le scénario B, absent du cron réel — il
aurait validé un mécanisme qui ne se déclenche jamais en production.

  A. Deux fiches 'pending' (le cas quotidien réel) — fusion bloquée, une alerte,
     PAS de résolution automatique (rien ne prouve qu'un humain a vérifié une
     fiche qui n'a jamais été publiée) → résolution MANUELLE (--resolu) ;
  B. Fiche visée déjà PUBLIÉE (--rescan) — même blocage, mais résolution
     AUTOMATIQUE dès que la fiche est dépubliée (wp_post_id_as vidé).

Lancer : .venv/bin/python -m tests.test_annulation
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
import scripts.dedupe as dedupe  # noqa: E402
import scripts.audit_annulations as audit  # noqa: E402

dedupe.DB_PATH = tmp
audit.DB_PATH = tmp

alertes = []
dedupe.slack.notify = lambda text, blocks=None: alertes.append(text) or True

conn = sqlite3.connect(tmp)
init_db(conn)
FICHES = [
    # id, titre, statut, source_type, wp_post_id_as
    (1, "Festival des Nuits Alpines", "pending", "officielle", None),
    (2, "Festival des Nuits Alpines annulé", "pending", "radar", None),
    (3, "Marché de Noël du Borgo", "published_sub", "officielle", 700),
    (4, "Marché de Noël du Borgo annullato", "pending", "radar", None),
]
for eid, titre, statut, source_type, wp in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, territoire, "
        "statut, source_type, wp_post_id_as) VALUES (?,?,?,?,?,?,?,?)",
        (eid, titre, "matière quelconque", f"https://x.fr/{eid}", "Savoie", statut,
         source_type, wp))
conn.commit()
conn.close()

echecs = 0

def _row(eid):
    conn = sqlite3.connect(tmp); conn.row_factory = sqlite3.Row
    r = dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())
    conn.close()
    return r

# ══════════════ SCÉNARIO A — cron réel, deux fiches pending ══════════════
print("──── A. passage 1 (cron réel, sans --rescan) : blocage + alerte ────")
rc = dedupe.main([])
f1, f2 = _row(1), _row(2)
if rc == 0 and f1["statut"] == "pending" and f2["statut"] == "pending":
    print("OK    aucune fusion : les deux fiches gardent leur statut")
else:
    echecs += 1
    print(f"ÉCHEC : f1={f1['statut']} f2={f2['statut']}")

if len(alertes) == 1 and "annulation" in alertes[0].lower():
    print(f"OK    une alerte envoyée : {alertes[0][:70]}...")
else:
    echecs += 1
    print(f"ÉCHEC : {len(alertes)} alerte(s) : {alertes}")

if f2.get("annulation_fiche_visee_id") == 1 and f2.get("annulation_visee_etait_publiee") == 0:
    print("OK    fiche visée = 1, marquée « n'était pas publiée » au moment du signal")
else:
    echecs += 1
    print(f"ÉCHEC : visee_id={f2.get('annulation_fiche_visee_id')} "
         f"etait_publiee={f2.get('annulation_visee_etait_publiee')}")

print("\n──── A. passage 2 : pas de re-fusion, pas de re-alerte ────")
alertes.clear()
dedupe.main([])
f1b = _row(1)
if not alertes and f1b["statut"] == "pending":
    print("OK    silence, toujours bloqué")
else:
    echecs += 1
    print(f"ÉCHEC : alertes={alertes} f1={f1b['statut']}")

print("\n──── A. audit : suspicion EN ATTENTE (jamais publiée → pas de résolution auto) ────")
en_attente_avant = sum(1 for r in [_row(2)] if r.get("annulation_detectee_at"))
audit.main([])
r2 = _row(2)
if r2.get("annulation_detectee_at"):
    print("OK    toujours active après l'audit (lecture seule, aucune résolution auto)")
else:
    echecs += 1
    print("ÉCHEC : la suspicion a disparu toute seule (elle ne devrait pas)")

print("\n──── A. --resolu : clôture manuelle ────")
audit.main(["--resolu", "2"])
r2 = _row(2)
if not r2.get("annulation_detectee_at"):
    print("OK    suspicion clôturée manuellement")
else:
    echecs += 1
    print(f"ÉCHEC : toujours active : {r2.get('annulation_detectee_at')}")

# ══════════════ SCÉNARIO B — fiche visée déjà publiée (--rescan) ══════════════
print("\n──── B. passage 1 (--rescan) : fiche visée déjà publiée ────")
alertes.clear()
rc_b = dedupe.main(["--rescan"])
f3, f4 = _row(3), _row(4)
if f3["statut"] == "published_sub" and f4.get("annulation_visee_etait_publiee") == 1:
    print("OK    fiche 3 intacte, suspicion marquée « était publiée »")
else:
    echecs += 1
    print(f"ÉCHEC : f3={f3['statut']} etait_publiee={f4.get('annulation_visee_etait_publiee')}")

print("\n──── B. la fiche visée est dépubliée (Franck) → résolution AUTOMATIQUE ────")
# Note attendue : la suspicion 2↔1 a été RE-détectée par le --rescan de tout à
# l'heure (le --resolu manuel avait effacé le signal, mais la paire existe
# toujours en base) — avec annulation_visee_etait_publiee=0 puisque la fiche 1
# n'a jamais été publiée. Elle reste donc « en attente », c'est le comportement
# attendu : seule la suspicion 4↔3 doit se résoudre automatiquement ici.
conn = sqlite3.connect(tmp)
conn.execute("UPDATE events_raw SET wp_post_id_as=NULL WHERE id=3")
conn.commit()
conn.close()
import io, logging
buf = io.StringIO()
h = logging.StreamHandler(buf); h.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger("audit-annulations").addHandler(h)
audit.main([])
sortie = buf.getvalue()
lignes_suspect = [l for l in sortie.splitlines() if "suspect [" in l]
if ("1 résolue(s) automatiquement" in sortie and "1 encore EN ATTENTE" in sortie
        and len(lignes_suspect) == 1 and "suspect [2]" in lignes_suspect[0]
        and "suspect [4]" not in sortie):
    print("OK    1 résolue automatiquement (fiche 3 dépubliée, suspect 4 disparaît "
         "de la liste), 1 encore en attente (suspect 2, fiche 1 jamais publiée) :")
    print(f"      {lignes_suspect}")
else:
    echecs += 1
    print(f"ÉCHEC :\n{sortie}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
