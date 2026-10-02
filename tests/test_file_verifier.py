#!/usr/bin/env python3
"""Fixture : la file « À vérifier » ne doit montrer que ce qui est encore devant nous.

INCIDENT RÉEL, 2026-08-10. Franck, capture d'écran du back-office à l'appui : « j'ai
l'impression d'avoir beaucoup d'événements non complets, et qu'on arrive pas à rattraper
le coup. dans le backoffice on a énorme de tâches, que je ne peux pas assumer ! » —
793 points en attente sur 211 fiches.

La requête n'avait AUCUN filtre : tous les points 'pending' depuis le premier jour. Les
trois premières fiches affichées à l'écran étaient un festival du 30 mai, des ateliers de
juillet-août, et une saison finie le 20 septembre. Vérifier le tarif d'un festival de mai
au mois d'août ne sert personne — c'est la règle 5 de CLAUDE.md, mot pour mot : « un
audit, un rapport ou une liste de correctifs qui mélange passé et à-venir FABRIQUE du
travail au lieu d'en désigner ». C'est ce qui rendait la file inassumable.

Ce que la fixture vérifie, et les frontières choisies exprès :
  • un événement À VENIR reste (évidemment) ;
  • un événement PASSÉ sort ;
  • une fiche SANS DATE reste : c'est une donnée manquante, pas un événement terminé —
    dates.py la remplira peut-être demain (règle 5, première précaution) ;
  • un RÉCURRENT dont la date est passée reste : il n'a pas de date unique, il n'est
    jamais « passé » ;
  • une fiche REJETÉE ou FUSIONNÉE sort, même à venir : plus personne ne la publiera ;
  • la pastille du menu compte EXACTEMENT la même chose que la page — sinon elle annonce
    793 quand l'écran en montre 40, et c'est la pastille qu'on croit.

Aucun réseau, aucune écriture ailleurs qu'en base jetable.

Lancer : .venv/bin/python -m tests.test_file_verifier
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
os.environ.setdefault("ADMIN_PASSWORD", "test")

from scripts.scraper_events import init_db  # noqa: E402
from app.app import _CHECKS_VIVANTS  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


AUJOURDHUI = "2026-08-10"
conn = sqlite3.connect(tmp)
init_db(conn)
conn.execute("CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY AUTOINCREMENT, "
             "event_id INTEGER NOT NULL, label TEXT NOT NULL, "
             "status TEXT NOT NULL DEFAULT 'pending', created_at TEXT, resolved_at TEXT)")

# (id, titre, date_event_end, statut, duplicate_of, recurring, doit_rester)
CAS = [
    (1, "Festival de décembre",        "2026-12-01", "evaluated", None, 0, True),
    (2, "Festival des jardins (30 mai)", "2026-05-30", "evaluated", None, 0, False),
    (3, "Fiche sans date",             None,         "evaluated", None, 0, True),
    (4, "Visite permanente du musée",  "2026-05-30", "evaluated", None, 1, True),
    (5, "Rejetée mais à venir",        "2026-12-01", "rejected",  None, 0, False),
    (6, "Fusionnée mais à venir",      "2026-12-01", "merged",    None, 0, False),
    (7, "Doublon mais à venir",        "2026-12-01", "evaluated", 1,    0, False),
    # Frontière exacte : un événement qui se termine AUJOURD'HUI est encore en cours.
    (8, "Se termine aujourd'hui",      AUJOURDHUI,   "evaluated", None, 0, True),
]
for eid, titre, fin, statut, dup, rec, _ in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, date_event_end, statut, "
        "duplicate_of, recurring) VALUES (?,?,?,?,?,?,?)",
        (eid, titre, f"https://x/{eid}", fin, statut, dup, rec))
    conn.execute("INSERT INTO checks (event_id, label, status) VALUES (?,?, 'pending')",
                 (eid, f"tarif de « {titre} »"))
conn.commit()

print("──── périmètre de la file ────")
q = (f"SELECT e.id FROM checks c JOIN events_raw e ON e.id=c.event_id "
     f"WHERE {_CHECKS_VIVANTS}")
gardes = {r[0] for r in conn.execute(q, (AUJOURDHUI,))}
for eid, titre, _f, _s, _d, _r, attendu in CAS:
    _check(f"{'gardé ' if attendu else 'écarté'} — {titre}",
           (eid in gardes) == attendu, f"gardés={sorted(gardes)}")

# ── La pastille du menu compte la même chose que la page ────────────────────────
print("\n──── pastille du menu = contenu de la page ────")
pastille = conn.execute(
    f"SELECT COUNT(*) FROM checks c JOIN events_raw e ON e.id=c.event_id "
    f"WHERE {_CHECKS_VIVANTS}", (AUJOURDHUI,)).fetchone()[0]
_check("la pastille annonce le nombre réellement affiché",
       pastille == len(gardes), f"pastille={pastille}, page={len(gardes)}")

# ── Rien n'est supprimé : les points écartés restent en base ────────────────────
print("\n──── rien n'est supprimé ni soldé d'office ────")
total = conn.execute("SELECT COUNT(*) FROM checks WHERE status='pending'").fetchone()[0]
_check("les points écartés restent 'pending' en base (ils reviendraient)",
       total == len(CAS), f"total={total}")
_check("l'écart est affichable (total - affichés)", total - len(gardes) == 4,
       f"{total} - {len(gardes)}")
conn.close()

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
