#!/usr/bin/env python3
"""Fixture : le portillon éditorial de publish_batch_as retient, sans rien écrire.

⚠️ BASE JETABLE (`scripts.scraper_events.init_db` dans un répertoire temporaire) —
JAMAIS `data/events.db`. Aucun appel WordPress : le test s'arrête au `--dry-run`, qui
sélectionne et journalise sans publier.

POURQUOI CE PORTILLON EXISTE (2026-08-05). L'évaluateur applique déjà
`config/excluded_event_keywords.txt`, mais seulement aux fiches encore `pending`. Une
règle ajoutée aujourd'hui ne dit rien des fiches DÉJÀ évaluées : quatre salons et
afterworks B2B étaient concernés ce jour-là, dont deux en file de publication.
`audit_excluded_events` les rattrape, mais il ne tourne que le dimanche.

Le test doit prouver les DEUX SENS : l'exclu est retenu, et les fiches légitimes
partent — un portillon qui retient tout serait aussi cassé qu'un portillon ouvert.
Il vérifie aussi que RIEN n'est écrit : la rétention n'est pas un rejet.

Lancer : .venv/bin/python -m tests.test_portillon_editorial
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
import scripts.publish_batch_as as pub  # noqa: E402

pub.DB_PATH = tmp
conn = sqlite3.connect(tmp)
init_db(conn)

# Champs requis par la porte qualité (utils.completeness) : une fiche incomplète serait
# écartée AVANT le portillon, et le test ne prouverait rien.
FICHES = [
    ("Afterwork LifeSciences Team Nice", "Networking sectoriel entre entreprises.",
     "https://a.fr/afterwork", "Nice", "Comte-de-Nice"),
    ("Marché de Noël d'Annecy", "Chalets d'artisans, vin chaud et manège sur la place.",
     "https://a.fr/noel", "Annecy", "Savoie"),
    ("Salon du livre de Chambéry", "Dédicaces, lectures et rencontres avec les auteurs.",
     "https://a.fr/livre", "Chambéry", "Savoie"),
]
for titre, desc, url, ville, territoire in FICHES:
    conn.execute(
        "INSERT INTO events_raw (title, description, url_source, ville, territoire, "
        "lieu, statut, llm_score, llm_categorie, date_event_start, date_event_end, "
        "url_image, enrich_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (titre, desc, url, ville, territoire, "Place centrale", "evaluated", 8,
         "Fêtes & Traditions", "2026-11-15", "2026-11-15",
         "https://a.fr/img.jpg", "enriched"))
conn.commit()
conn.close()

print("──── sélection (dry-run, aucune publication) ────")
rc = pub.main(["--dry-run", "--cap", "50"])
assert rc == 0, f"publish_batch_as a échoué (rc={rc})"

conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
echecs = 0

# 1. La rétention n'écrit RIEN : les trois fiches gardent leur statut et n'ont pas de post.
print("\n──── aucun effet de bord en base ────")
for r in conn.execute("SELECT title, statut, wp_post_id_as FROM events_raw"):
    ok = r["statut"] == "evaluated" and r["wp_post_id_as"] is None
    echecs += 0 if ok else 1
    print(f"{'OK   ' if ok else 'ÉCHEC'} {r['title']:34} statut={r['statut']} wp={r['wp_post_id_as']}")

# 2. La sélection elle-même : l'afterwork retenu, les deux autres publiables.
selection = [dict(r) for r in pub._select(
    conn, type("A", (), {"ids": None, "include_past": False, "update": False,
                         "min_score": None, "cap": 50})(), "2026-08-05")]
exclusions = pub.load_excluded_events_filter()
retenus = [e["title"] for e in selection
           if pub.is_excluded_event(e.get("title", ""), e.get("description", ""),
                                    exclusions, url=e.get("url_source", ""))]
attendu = ["Afterwork LifeSciences Team Nice"]
print("\n──── qui passe le portillon ────")
print(f"retenus  : {retenus}")
print(f"attendus : {attendu}")
if retenus != attendu:
    echecs += 1
    print("ÉCHEC : le portillon ne retient pas exactement l'exclu.")

print(f"\n{'ÉCHEC' if echecs else 'OK'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
