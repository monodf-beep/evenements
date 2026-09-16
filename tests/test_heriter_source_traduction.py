"""Fixture pour `_heriter_source_traduction` (scripts/publish_batch_as.py).

Incident du 16/09 : une traduction dont `url_source` est le pseudo-marqueur
`translated:<id>:<lang>` (jamais publiable) restait sans `url_officiel`, donc
sans source officielle publiable — cs-completude.php la démettait en brouillon
alors que l'ORIGINAL avait une vraie source. Le cas-témoin choisi près de la
frontière (règle 3 du dépôt) : une traduction dont l'original n'a PAS de
`url_officiel` mais une matière « officielle lue » — ce signal-là ne doit
JAMAIS être copié comme URL (ce n'est pas une adresse), et c'est le cas qui
aurait cassé une version naïve de ce correctif.
"""
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publish_batch_as import _heriter_source_traduction

# Schéma minimal autonome : ce test n'exerce que les colonnes lues par
# `_heriter_source_traduction` / `radar.official_anchor`. Ce conteneur de
# développement n'a pas les dépendances de `scripts.scraper_events.init_db`
# (feedparser, etc.) — reconstruire ici évite de les installer à l'aveugle
# pour un test qui n'en a pas besoin. Toujours PAS sur data/events.db (règle
# du dépôt), toujours une base jetable, juste plus étroite.
_SCHEMA = """
CREATE TABLE events_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url_officiel TEXT DEFAULT '',
    url_source TEXT DEFAULT '',
    translation_of INTEGER,
    enrich_data TEXT
)
"""


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def _inserer(conn, **champs):
    cols = ", ".join(champs.keys())
    ph = ", ".join("?" * len(champs))
    cur = conn.execute(f"INSERT INTO events_raw ({cols}) VALUES ({ph})", tuple(champs.values()))
    return cur.lastrowid


class TestHeriterSourceTraduction(unittest.TestCase):
    def test_traduction_recupere_url_officiel_de_l_original(self):
        """Cas nominal (Chopin/Egitto, mesuré en production) : l'original a une
        vraie URL officielle, la traduction ne l'a pas encore — elle doit
        l'hériter."""
        conn = _conn()
        orig_id = _inserer(conn, title="Chopin", url_officiel="https://www.opera-nice.org/agenda/chopin/")
        enfant = {"id": 999, "title": "Chopin", "translation_of": orig_id,
                  "url_source": f"translated:{orig_id}:it", "url_officiel": ""}
        _heriter_source_traduction(enfant, conn)
        self.assertEqual(enfant["url_officiel"], "https://www.opera-nice.org/agenda/chopin/")

    def test_cas_frontiere_matiere_officielle_sans_url_n_est_pas_copiee(self):
        """PRÈS DE LA FRONTIÈRE : l'original n'a pas de `url_officiel` mais son
        `enrich_data.source.officielle` est vrai — `official_anchor` renvoie
        alors la PHRASE « matière officielle lue (…) », pas une URL. Une version
        naïve du correctif (copier `official_anchor(parent)` sans vérifier le
        schéma http(s)) écrirait cette phrase dans `url_officiel` et casserait
        `_source_publiable`. Ce cas DOIT passer sans rien copier."""
        conn = _conn()
        orig_id = _inserer(
            conn, title="Une expo", url_officiel="",
            enrich_data='{"source": {"officielle": true, "pages": []}}')
        enfant = {"id": 998, "title": "Une expo", "translation_of": orig_id,
                  "url_source": f"translated:{orig_id}:it", "url_officiel": ""}
        _heriter_source_traduction(enfant, conn)
        self.assertEqual(enfant["url_officiel"], "")

    def test_pas_une_traduction_ne_fait_rien(self):
        conn = _conn()
        enfant = {"id": 1, "title": "X", "translation_of": None, "url_officiel": ""}
        _heriter_source_traduction(enfant, conn)
        self.assertEqual(enfant["url_officiel"], "")

    def test_traduction_a_deja_sa_propre_ancre_n_est_pas_ecrasee(self):
        conn = _conn()
        orig_id = _inserer(conn, title="X", url_officiel="https://original.example/")
        enfant = {"id": 2, "title": "X", "translation_of": orig_id,
                  "url_officiel": "https://deja-la.example/"}
        _heriter_source_traduction(enfant, conn)
        self.assertEqual(enfant["url_officiel"], "https://deja-la.example/")

    def test_original_introuvable_ne_casse_rien(self):
        conn = _conn()
        enfant = {"id": 3, "title": "X", "translation_of": 999999, "url_officiel": ""}
        _heriter_source_traduction(enfant, conn)
        self.assertEqual(enfant["url_officiel"], "")


if __name__ == "__main__":
    unittest.main()
