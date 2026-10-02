#!/usr/bin/env python3
"""Fixture : l'audit d'exclusion doit voir les DEUX paniers (en ligne / en file).

⚠️ BASE JETABLE construite par `scripts.scraper_events.init_db` dans un répertoire
temporaire — JAMAIS `data/events.db`.

Reproduit la situation réelle du 2026-08-05 : « French Riviera Beauty » est en ligne
(fiche 2465, WP#6420) tandis que son doublon non apparié (fiche 3086) n'a aucun post
mais porte `statut='published_sub'` — donc le profil exact que `publish_batch_as`
sélectionne pour une CRÉATION. Le premier audit ne voyait que le panier « en ligne » :
il aurait laissé partir le salon B2B au lot suivant.

Le test doit prouver les DEUX SENS : les exclues partent (des deux paniers), et le
salon du livre comme le marché de Noël ne bougent pas d'un pouce.

Lancer : .venv/bin/python -m tests.test_audit_excluded_events
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
import scripts.audit_excluded_events as audit  # noqa: E402

audit.DB_PATH = tmp
conn = sqlite3.connect(tmp)
init_db(conn)

FICHES = [
    # (titre, description, url, statut, wp_post_id_as) — ce qui doit se passer
    ("Afterwork LifeSciences", "Networking sectoriel.", "https://a.fr/1",
     "published_sub", 1147),                       # EN LIGNE → corbeille
    ("French Riviera Beauty", "Salon beauté.",
     "https://us.list-manage.com/NEbt0b0Fxb4?e=06a93eea46", "published_sub", 6420),
    ("French riviera Beauty", "Salon beauté, doublon non apparié.",
     "https://a.fr/3086", "published_sub", None),  # EN FILE → rejet en base
    ("Salon du livre de Chambéry", "Dédicaces.", "https://a.fr/ok1",
     "published_sub", 5000),                       # intouchable
    ("Marché de Noël d'Annecy", "Vin chaud.", "https://a.fr/ok2", "evaluated", None),
    ("Vieil afterwork déjà rejeté", "Networking.", "https://a.fr/vieux", "rejected", None),
]
for titre, desc, url, statut, wp in FICHES:
    conn.execute("INSERT INTO events_raw (title, description, url_source, statut, "
                 "wp_post_id_as, date_event_start) VALUES (?,?,?,?,?,?)",
                 (titre, desc, url, statut, wp, "2026-11-01"))
conn.commit()
conn.close()

print("──── dry-run ────")
assert audit.main([]) == 0

print("\n──── apply (--db-only : pas d'appel WordPress sur fixture) ────")
assert audit.main(["--apply", "--db-only"]) == 0

conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
print("\n──── état final ────")
echecs = 0
ATTENDU = {
    "Afterwork LifeSciences": ("rejected", None),
    "French Riviera Beauty": ("rejected", None),
    "French riviera Beauty": ("rejected", None),
    "Salon du livre de Chambéry": ("published_sub", 5000),
    "Marché de Noël d'Annecy": ("evaluated", None),
    "Vieil afterwork déjà rejeté": ("rejected", None),
}
for r in conn.execute("SELECT title, statut, wp_post_id_as FROM events_raw"):
    attendu = ATTENDU[r["title"]]
    obtenu = (r["statut"], r["wp_post_id_as"])
    if obtenu != attendu:
        echecs += 1
        print(f"ÉCHEC {r['title']:32} obtenu={obtenu} attendu={attendu}")
    else:
        print(f"OK    {r['title']:32} {obtenu}")

print(f"\n{len(ATTENDU) - echecs}/{len(ATTENDU)} fiches dans l'état attendu.")
sys.exit(1 if echecs else 0)
