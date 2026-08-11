#!/usr/bin/env python3
"""Fixture : le rouvreur des signatures, sur une base jetable — jamais data/events.db.

Ce que la fixture surveille, dans l'ordre d'importance :

  1. le DRY-RUN n'écrit rien (règle 4 de CLAUDE.md) ;
  2. rien n'est PERDU : la valeur retirée est retrouvable dans `organisateur_byline` ;
  3. une fiche EN LIGNE garde son point « À vérifier » OUVERT. C'est le point le plus
     facile à rater et le plus coûteux : vider la colonne ne réécrit pas l'article déjà
     publié, donc le site continue d'annoncer la journaliste comme organisatrice. Fermer
     la tâche là ferait exactement ce que la règle 1 interdit — conclure sur l'état du
     site depuis l'état de la base ;
  4. le périmètre par défaut laisse le PASSÉ tranquille, et `--tout` le rattrape.

Lancer : .venv/bin/python -m tests.test_purge_bylines
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import purge_bylines  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


tmp = Path(tempfile.mkdtemp(prefix="fixture-bylines-"))
db = tmp / "events.db"
conn = sqlite3.connect(db)
init_db(conn)
for col, decl in (("date_event_start", "TEXT"), ("date_event_end", "TEXT"),
                  ("recurring", "INTEGER DEFAULT 0"), ("translation_of", "INTEGER"),
                  ("wp_post_id_as", "INTEGER"), ("article_title", "TEXT"),
                  ("enrich_status", "TEXT")):
    try:
        conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
    except sqlite3.OperationalError:
        pass
conn.execute("""CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, label TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT)""")

# ── Le jeu d'essai : les vrais cas du 2026-08-11, plus les pièges ────────────────────
CAS = [
    # (id, titre, description, organisateur, fin, wp_id) — fin '9999' = très à venir
    (1, "La Foire de Saint-Ours 2027", "Un article d'Arabella Pezza pour la rubrique.",
     "Arabella Pezza", "2027-01-31", None),
    (2, "Percorso in Rosso", "Propos recueillis par Stefania Marchiano.",
     "Stefania Marchiano", "2027-08-13", 6001),           # EN LIGNE
    (3, "Marché au Fort", "Rassegna al Forte di Bard.", "Chambre valdôtaine",
     "2027-10-11", None),                                  # vrai organisateur
    (4, "Fête du village", "La fête est organisée par Denis Falconieri, président.",
     "Denis Falconieri", "2027-07-01", None),              # corroboré → à garder
    (5, "Concert d'archives", "Un article de Paolo Rossi.", "Paolo Rossi",
     "2020-01-01", None),                                  # PASSÉ
    (6, "Exposition en cours", "Article signé Marie Durand.", "Marie Durand",
     "2027-09-30", None),
]
for eid, titre, desc, orga, fin, wp in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, organisateur, "
        "source_name, date_event_end, wp_post_id_as, article_title) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (eid, titre, desc, f"https://exemple.fr/{eid}", orga, "Source officielle",
         fin, wp, titre))
conn.execute("INSERT INTO checks (event_id, label) VALUES (?,?)",
             (1, "Organisateur réel de la foire (Arabella Pezza semble être une journaliste)"))
conn.execute("INSERT INTO checks (event_id, label) VALUES (?,?)",
             (2, "Stefania Marchiano : autrice de l'article ou organisatrice ?"))
conn.execute("INSERT INTO checks (event_id, label) VALUES (?,?)",
             (4, "Fonction exacte de Denis Falconieri"))
conn.commit()
conn.close()

purge_bylines.DB = db


def _lire(eid, col="organisateur"):
    c = sqlite3.connect(db)
    v = c.execute(f"SELECT {col} FROM events_raw WHERE id=?", (eid,)).fetchone()[0]
    c.close()
    return v


def _statut_check(eid):
    c = sqlite3.connect(db)
    r = c.execute("SELECT status FROM checks WHERE event_id=?", (eid,)).fetchone()
    c.close()
    return r[0] if r else None


print("──── 1. simulation : rien ne bouge ────")
purge_bylines.main([])
_check("la fiche 1 garde sa valeur après un dry-run", _lire(1) == "Arabella Pezza",
       repr(_lire(1)))
_check("aucun point n'est fermé par un dry-run", _statut_check(1) == "pending")

print("\n──── 2. application ────")
purge_bylines.main(["--apply"])
_check("signature de presse retirée (fiche 1)", _lire(1) == "", repr(_lire(1)))
_check("rien n'est perdu : la valeur est en mémoire",
       _lire(1, "organisateur_byline") == "Arabella Pezza",
       repr(_lire(1, "organisateur_byline")))
_check("le vrai organisateur est intact (fiche 3)", _lire(3) == "Chambre valdôtaine",
       repr(_lire(3)))
_check("le nom CORROBORÉ est intact (fiche 4) — le cas près de la frontière",
       _lire(4) == "Denis Falconieri", repr(_lire(4)))
_check("le passé n'est pas touché par défaut (fiche 5)", _lire(5) == "Paolo Rossi",
       repr(_lire(5)))
_check("autre signature retirée (fiche 6)", _lire(6) == "", repr(_lire(6)))

print("\n──── 3. les points « À vérifier » ────")
_check("fiche HORS LIGNE : le point est fermé, il n'a plus d'objet",
       _statut_check(1) == "done", repr(_statut_check(1)))
_check("fiche EN LIGNE : le point reste OUVERT (l'article publié cite encore le nom)",
       _statut_check(2) == "pending", repr(_statut_check(2)))
_check("le point d'une fiche non modifiée reste ouvert",
       _statut_check(4) == "pending", repr(_statut_check(4)))

print("\n──── 4. --tout rattrape le passé ────")
purge_bylines.main(["--apply", "--tout"])
_check("le passé est corrigé quand on le demande explicitement", _lire(5) == "",
       repr(_lire(5)))
_check("et sa valeur est gardée aussi",
       _lire(5, "organisateur_byline") == "Paolo Rossi")

print("\n──── 5. idempotence ────")
avant = _lire(1, "organisateur_byline")
purge_bylines.main(["--apply", "--tout"])
_check("relancer n'écrase pas la mémoire avec du vide",
       _lire(1, "organisateur_byline") == avant, repr(_lire(1, "organisateur_byline")))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s). Base jetable : {tmp}")
sys.exit(1 if echecs else 0)
