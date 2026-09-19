"""Fixture pour `_heriter_source_traduction` (scripts/publish_batch_as.py).

Incident du 16/09, EN DEUX TEMPS — le deuxième est le plus instructif :

1. Une traduction dont `url_source` est le pseudo-marqueur `translated:<id>:<lang>`
   (jamais publiable) restait sans source officielle publiable, alors que l'original
   en a une vraie — cs-completude.php la démettait en brouillon pour de mauvaises
   raisons.
2. Ma PREMIÈRE version du correctif copiait `radar.official_anchor(parent)`, qui ne
   lit que `url_officiel` + `enrich_data.source`. Déployée, elle n'a RIEN changé pour
   Chopin/Egitto : leur statut de source officielle vient de `url_source` (tier
   « officielle » de sources.txt), pas de `url_officiel` — vide des deux côtés. Un
   test qui n'avait que le cas « l'original a bien url_officiel » serait passé au vert
   sur un correctif qui ne marchait pas en production. D'où le cas-témoin ci-dessous :
   EXACTEMENT cette configuration (url_officiel vide, url_source la vraie adresse),
   qui doit PASSER pour que le test ait un sens (règle 3 du dépôt).
"""
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publish_batch_as import _heriter_source_traduction

# Schéma minimal autonome : ce test n'exerce que les colonnes lues par
# `_heriter_source_traduction` / `_source_publiable` / `_is_radar`. Ce conteneur de
# développement n'a pas les dépendances de `scripts.scraper_events.init_db`
# (feedparser, etc.) — reconstruire ici évite de les installer à l'aveugle pour un
# test qui n'en a pas besoin. Toujours PAS sur data/events.db (règle du dépôt),
# toujours une base jetable, juste plus étroite.
_SCHEMA = """
CREATE TABLE events_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url_officiel TEXT DEFAULT '',
    url_source TEXT DEFAULT '',
    source_type TEXT DEFAULT '',
    source_name TEXT DEFAULT '',
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
    def test_cas_reel_chopin_url_officiel_vide_des_deux_cotes(self):
        """LE CAS-TÉMOIN, mesuré en production sur Chopin (id local 525/5586) :
        `url_officiel` est vide sur l'original ET la traduction ; la source
        officielle vit dans `url_source` de l'original. C'est le cas que la
        première version du correctif ratait entièrement — il DOIT passer."""
        conn = _conn()
        orig_id = _inserer(conn, title="Chopin", url_officiel="",
                            url_source="https://www.opera-nice.org/agenda/chopin/20260918-1800/")
        enfant = {"id": 5586, "title": "Chopin", "translation_of": orig_id,
                  "url_source": f"translated:{orig_id}:it", "url_officiel": ""}
        _heriter_source_traduction(enfant, conn)
        self.assertEqual(enfant["url_source"],
                          "https://www.opera-nice.org/agenda/chopin/20260918-1800/")

    def test_original_a_url_officiel_directe(self):
        """Cas plus simple : l'original a une vraie `url_officiel` — elle doit
        se retrouver dans `url_source` de la traduction (c'est ce champ-là que
        `_source_publiable` relit ensuite pour la traduction elle-même)."""
        conn = _conn()
        orig_id = _inserer(conn, title="X", url_officiel="https://officiel.example/")
        enfant = {"id": 1, "title": "X", "translation_of": orig_id,
                  "url_source": f"translated:{orig_id}:it", "url_officiel": ""}
        _heriter_source_traduction(enfant, conn)
        self.assertEqual(enfant["url_source"], "https://officiel.example/")

    def test_original_sans_aucune_source_ne_transmet_rien(self):
        """L'original n'a ni `url_officiel` ni `url_source` publiable (ex.
        `enrich_data.source.officielle` vrai mais aucune page conservée) — rien
        à copier, le pseudo-marqueur reste tel quel."""
        conn = _conn()
        orig_id = _inserer(conn, title="Une expo", url_officiel="", url_source="",
                            enrich_data='{"source": {"officielle": true, "pages": []}}')
        enfant = {"id": 998, "title": "Une expo", "translation_of": orig_id,
                  "url_source": f"translated:{orig_id}:it", "url_officiel": ""}
        _heriter_source_traduction(enfant, conn)
        self.assertEqual(enfant["url_source"], f"translated:{orig_id}:it")

    def test_pas_une_traduction_ne_fait_rien(self):
        conn = _conn()
        enfant = {"id": 1, "title": "X", "translation_of": None, "url_source": ""}
        _heriter_source_traduction(enfant, conn)
        self.assertEqual(enfant["url_source"], "")

    def test_traduction_a_deja_une_vraie_source_n_est_pas_ecrasee(self):
        conn = _conn()
        orig_id = _inserer(conn, title="X", url_officiel="https://original.example/")
        enfant = {"id": 2, "title": "X", "translation_of": orig_id,
                  "url_source": "https://deja-la.example/"}
        _heriter_source_traduction(enfant, conn)
        self.assertEqual(enfant["url_source"], "https://deja-la.example/")

    def test_original_introuvable_ne_casse_rien(self):
        conn = _conn()
        enfant = {"id": 3, "title": "X", "translation_of": 999999,
                  "url_source": "translated:999999:it"}
        _heriter_source_traduction(enfant, conn)
        self.assertEqual(enfant["url_source"], "translated:999999:it")


if __name__ == "__main__":
    unittest.main()
