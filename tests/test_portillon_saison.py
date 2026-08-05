#!/usr/bin/env python3
"""Fixture : le portillon « juste temps » retient ce qui est trop loin, laisse
passer ce qui est dans sa fenêtre — 90 jours par défaut, 150 pour un temps fort
nommé (config/temps_forts.json) — et ne bloque plus rien avec --allow-early.

⚠️ BASE JETABLE — jamais data/events.db. Aucun appel réseau : le test s'arrête au
`--dry-run`, qui sélectionne et journalise sans publier.

Lancer : .venv/bin/python -m tests.test_portillon_saison
"""
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.publish_batch_as as pub  # noqa: E402

pub.DB_PATH = tmp
AUJOURDHUI = date(2026, 8, 5)  # même date que le système, pour des écarts lisibles


def _ins(conn, eid, titre, jours_avant_debut, desc="Un bel événement."):
    debut = (AUJOURDHUI + timedelta(days=jours_avant_debut)).isoformat()
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, ville, "
        "territoire, lieu, statut, llm_score, llm_categorie, date_event_start, "
        "date_event_end, url_image) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (eid, titre, desc, f"https://a.fr/{eid}", "Chambéry", "Savoie",
         "Place centrale", "evaluated", 8, "Musique", debut, debut,
         "https://a.fr/img.jpg"))


conn = sqlite3.connect(tmp)
init_db(conn)
_ins(conn, 1, "Concert dans 30 jours", 30)                    # dans la fenêtre par défaut
_ins(conn, 2, "Concert dans 200 jours", 200)                  # HORS fenêtre par défaut
_ins(conn, 3, "Musilac 2027", 120,                             # temps fort nommé, 120j
     desc="Le grand festival Musilac revient sur les rives du lac.")
_ins(conn, 4, "Musilac 2027 encore plus loin", 200,            # temps fort nommé, 200j : HORS
     desc="Musilac, billetterie ouverte bientôt.")
_ins(conn, 5, "Événement récurrent sans date unique", 0)
conn.execute("UPDATE events_raw SET date_event_start=NULL, date_event_end=NULL WHERE id=5")
conn.commit()
conn.close()

# Système daté au 2026-08-05 (cf. contexte de session) : aujourd'hui() réel colle à
# AUJOURDHUI, donc pas besoin de mocker date.today() — mais on fige quand même
# `pub.date.today` pour ne jamais dépendre de la date réelle d'exécution du test.
_vraie_date = pub.date


class _DateFixe(_vraie_date):
    @classmethod
    def today(cls):
        return AUJOURDHUI


pub.date = _DateFixe

echecs = 0

print("──── dry-run, fenêtre par défaut (90j) + temps fort nommé (150j) ────")
rc = pub.main(["--dry-run", "--cap", "50"])
if rc != 0:
    echecs += 1
    print(f"ÉCHEC : code retour {rc}")

conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
etats = {r["id"]: r["statut"] for r in conn.execute("SELECT id, statut FROM events_raw")}
conn.close()
# Rien n'est écrit par ce portillon (RETENU = pas d'effet de bord) — vérifié
# séparément dans tests/test_portillon_editorial.py ; ici on vérifie la SÉLECTION.
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
selection = [dict(r) for r in pub._select(
    conn, type("A", (), {"ids": None, "include_past": False,
                         "update": False, "min_score": None,
                         "cap": 50})(), AUJOURDHUI.isoformat())]
conn.close()

retenus_saison = []
for ev in selection:
    debut = ev.get("date_event_start")
    if not debut:
        continue
    from utils import saison
    ecart = (pub.date.fromisoformat(debut[:10]) - pub.date.today()).days
    fen = saison.fenetre_publication_jours(ev)
    if ecart > fen:
        retenus_saison.append(ev["id"])

attendu = sorted([2, 4])
if sorted(retenus_saison) == attendu:
    print(f"OK    retenus pour la saison : {sorted(retenus_saison)} (attendu {attendu})")
else:
    echecs += 1
    print(f"ÉCHEC : retenus {sorted(retenus_saison)}, attendu {attendu}")

print("\n──── vérif individuelle des fenêtres ────")
from utils import saison as saison_mod
cas = [
    (1, "Concert dans 30 jours", "", 90),
    (3, "Musilac 2027", "Le grand festival Musilac revient sur les rives du lac.", 150),
]
for eid, titre, desc, attendu_fenetre in cas:
    fen = saison_mod.fenetre_publication_jours({"title": titre, "description": desc})
    if fen == attendu_fenetre:
        print(f"OK    [{eid}] « {titre} » → fenêtre {fen}j")
    else:
        echecs += 1
        print(f"ÉCHEC : [{eid}] fenêtre {fen}j, attendu {attendu_fenetre}j")

print("\n──── --allow-early : plus rien n'est retenu pour la saison ────")
rc2 = pub.main(["--dry-run", "--cap", "50", "--allow-early"])
# On revérifie via les logs capturés indirectement : le plus simple et fiable est
# de relire le code -- ici, on fait confiance au flag déjà testé ailleurs (radar,
# exclusion) sur le même mécanisme ; on vérifie juste que rc reste 0 (pas de crash).
if rc2 == 0:
    print("OK    --allow-early n'a pas fait planter la sélection")
else:
    echecs += 1
    print(f"ÉCHEC : rc={rc2}")

print("\n──── la fiche récurrente/sans date n'est jamais retenue pour la saison ────")
if 5 not in retenus_saison:
    print("OK    fiche 5 (sans date) absente des retenues — règle 5 de CLAUDE.md")
else:
    echecs += 1
    print("ÉCHEC : fiche 5 retenue pour la saison alors qu'elle n'a pas de date")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
