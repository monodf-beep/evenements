#!/usr/bin/env python3
"""Fixture : le portillon « juste temps » ne retient QUE les temps forts nommés
(Noël, Halloween — config/temps_forts.json) hors de leur fenêtre propre. Un
événement ordinaire, même très loin dans le temps, un grand festival à
billetterie (Musilac) : AUCUNE fenêtre, jamais retenu ici.

⚠️ CORRIGÉ le 2026-08-05, même jour : la première version imposait 90 jours à
TOUT événement daté — Franck l'a corrigé (« je n'ai pas demandé ça pour Nice
Jazz, Carnaval de Nice… ça peut être plus loin »). Ce test remplace l'ancien
qui validait le mauvais comportement.

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
from utils import saison as saison_mod  # noqa: E402

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
_ins(conn, 1, "Concert ordinaire dans 300 jours", 300)         # AUCUNE fenêtre : jamais retenu
_ins(conn, 2, "Marché de Noël du Borgo", 300)                  # Noël, 300j : HORS fenêtre (65j)
_ins(conn, 3, "Marché de Noël du Borgo, tout proche", 40)      # Noël, 40j : DANS la fenêtre
_ins(conn, 4, "Soirée Halloween au château", 90)                # Halloween, 90j : HORS (30j)
_ins(conn, 5, "Musilac 2027", 300,                              # grand festival, 300j : AUCUNE
     desc="Le grand festival Musilac revient sur les rives du lac.")
_ins(conn, 6, "Événement récurrent sans date unique", 0)
conn.execute("UPDATE events_raw SET date_event_start=NULL, date_event_end=NULL WHERE id=6")
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

print("──── dry-run : seuls les temps forts nommés hors fenêtre sont retenus ────")
rc = pub.main(["--dry-run", "--cap", "50"])
if rc != 0:
    echecs += 1
    print(f"ÉCHEC : code retour {rc}")

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
    fen = saison_mod.fenetre_publication_jours(ev)
    if fen is None:
        continue
    ecart = (pub.date.fromisoformat(debut[:10]) - pub.date.today()).days
    if ecart > fen:
        retenus_saison.append(ev["id"])

attendu = [2, 4]  # Noël trop tôt (id 2) et Halloween trop tôt (id 4) — les seuls
if sorted(retenus_saison) == sorted(attendu):
    print(f"OK    retenus pour la saison : {sorted(retenus_saison)} (attendu {sorted(attendu)})")
else:
    echecs += 1
    print(f"ÉCHEC : retenus {sorted(retenus_saison)}, attendu {sorted(attendu)}")

print("\n──── un événement ordinaire, même à 300 jours, n'a AUCUNE fenêtre ────")
fen1 = saison_mod.fenetre_publication_jours({"title": "Concert ordinaire", "description": ""})
if fen1 is None:
    print("OK    fenêtre = None (aucun plafond) pour un événement non-thématique")
else:
    echecs += 1
    print(f"ÉCHEC : fenêtre={fen1}, attendu None")

print("\n──── Musilac (grand festival à billetterie) n'a AUCUNE fenêtre non plus ────")
fen_musilac = saison_mod.fenetre_publication_jours(
    {"title": "Musilac 2027", "description": "Le grand festival Musilac revient."})
if fen_musilac is None:
    print("OK    fenêtre = None pour Musilac — Franck : « ça peut être plus loin »")
else:
    echecs += 1
    print(f"ÉCHEC : fenêtre={fen_musilac}, attendu None (Musilac ne doit plus être plafonné)")

print("\n──── vérif individuelle des fenêtres nommées ────")
cas = [
    ("Marché de Noël", "", 65),
    ("Soirée Halloween", "", 30),
]
for titre, desc, attendu_fenetre in cas:
    fen = saison_mod.fenetre_publication_jours({"title": titre, "description": desc})
    if fen == attendu_fenetre:
        print(f"OK    « {titre} » → fenêtre {fen}j")
    else:
        echecs += 1
        print(f"ÉCHEC : « {titre} » fenêtre {fen}j, attendu {attendu_fenetre}j")

print("\n──── --allow-early : plus rien n'est retenu pour la saison ────")
rc2 = pub.main(["--dry-run", "--cap", "50", "--allow-early"])
if rc2 == 0:
    print("OK    --allow-early n'a pas fait planter la sélection")
else:
    echecs += 1
    print(f"ÉCHEC : rc={rc2}")

print("\n──── la fiche récurrente/sans date n'est jamais retenue pour la saison ────")
if 6 not in retenus_saison:
    print("OK    fiche 6 (sans date) absente des retenues — règle 5 de CLAUDE.md")
else:
    echecs += 1
    print("ÉCHEC : fiche 6 retenue pour la saison alors qu'elle n'a pas de date")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
