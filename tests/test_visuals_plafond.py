#!/usr/bin/env python3
"""Fixture : un plafond API n'écrit AUCUN visuel — ni pour la fiche en cours, ni pour
les suivantes.

⚠️ BASE JETABLE (`scripts.scraper_events.init_db` dans un répertoire temporaire) —
JAMAIS `data/events.db`. Aucun appel réseau : le client Anthropic est un faux objet
qui lève l'erreur de plafond réellement reçue le 2026-08-04 à 15h33.

POURQUOI CE CAS EST PIRE QUE LES AUTRES. `dates.py` et `venues.py` écrivaient, un jour
de plafond, un verdict `llm_none` horodaté : la fiche dormait 7 jours, puis repartait.
Ici, la chaîne retombe sur la BANNIÈRE territoire et l'écrit dans `url_image` — or
`visuals.select_events` ne sélectionne que les fiches dont `url_image` est VIDE. La
bannière posée par manque de crédit n'aurait donc jamais été remplacée : le faux
verdict n'expire pas, il est définitif. `utils.image_verify.verify_relevance` aggravait
le tout en renvoyant `True` (« panne technique, on ne bloque pas ») — soit une image
ACCEPTÉE sans que personne ne l'ait regardée.

Le test prouve les DEUX SENS : rien n'est écrit sous plafond, et une panne technique
ORDINAIRE (timeout réseau) laisse bien la chaîne se replier sur la bannière — sinon la
correction aurait simplement remplacé un défaut par un autre.

Lancer : .venv/bin/python -m tests.test_visuals_plafond
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
os.environ["ANTHROPIC_API_KEY"] = "factice-jamais-appelee"

from scripts.scraper_events import init_db  # noqa: E402
import scripts.visuals as visuals  # noqa: E402
from utils.api_limite import PlafondAPI  # noqa: E402

visuals.DB_PATH = tmp


class ErreurPlafond(Exception):
    """Reproduit l'erreur réelle du 2026-08-04 15h33 (status_code + texte du SDK)."""
    status_code = 400

    def __str__(self):
        return ("Error code: 400 - You have reached your specified API usage limits. "
                "You will regain access on 2026-09-01 at 00:00 UTC.")


class ErreurReseau(Exception):
    status_code = 502

    def __str__(self):
        return "Bad gateway"


def _base(nb=4):
    if tmp.exists():
        tmp.unlink()
    conn = sqlite3.connect(tmp)
    init_db(conn)
    for i in range(nb):
        conn.execute(
            "INSERT INTO events_raw (title, description, url_source, ville, territoire, "
            "lieu, statut, llm_score, llm_categorie, date_event_start, date_event_end) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (f"Concert {i}", "Un concert dans la vallée.", f"https://a.fr/{i}", "Annecy",
             "Savoie", "Salle des fêtes", "evaluated", 8, "Musique",
             "2026-11-15", "2026-11-15"))
    conn.commit()
    conn.close()


def _images_posees() -> list:
    conn = sqlite3.connect(tmp)
    conn.row_factory = sqlite3.Row
    out = [(r["id"], r["url_image"], r["image_source"])
           for r in conn.execute("SELECT id, url_image, image_source FROM events_raw")]
    conn.close()
    return out


echecs = 0

# ── 1. Le helper lève bien PlafondAPI au lieu de renvoyer True ──────────────────
print("──── verify_relevance sous plafond ────")
from utils import image_verify  # noqa: E402


class FauxClient:
    def __init__(self, exc):
        self._exc = exc
        self.appels = 0

    class _Messages:
        def __init__(self, parent):
            self._p = parent

        def create(self, **kw):
            self._p.appels += 1
            raise self._p._exc

    @property
    def messages(self):
        return self._Messages(self)


faux_png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
try:
    image_verify.verify_relevance(faux_png, "image/png", {"title": "x"},
                                  FauxClient(ErreurPlafond()), "m")
    print("ÉCHEC : verify_relevance a renvoyé au lieu de lever PlafondAPI")
    echecs += 1
except PlafondAPI:
    print("OK    PlafondAPI levée — l'image n'est plus acceptée sans être regardée")

ok, fx, fy = image_verify.verify_relevance(faux_png, "image/png", {"title": "x"},
                                           FauxClient(ErreurReseau()), "m")
if (ok, fx, fy) == (True, 0.5, 0.5):
    print("OK    panne réseau ordinaire : tolérance conservée (True, 0.5, 0.5)")
else:
    print(f"ÉCHEC : panne réseau devrait rester tolérée, obtenu {(ok, fx, fy)}")
    echecs += 1

# ── 2. Le lot complet : plafond au premier appel → aucune écriture ──────────────
print("\n──── lot visuals.main() sous plafond ────")
_base(4)
visuals.resolve_image = lambda *a, **k: (_ for _ in ()).throw(PlafondAPI("plafond"))
rc = visuals.main([])
posees = [(i, u, s) for i, u, s in _images_posees() if u]
if rc == 3:
    print("OK    code retour 3 (non nul) — le chien de garde peut le voir")
else:
    print(f"ÉCHEC : code retour {rc}, attendu 3")
    echecs += 1
if not posees:
    print("OK    aucune image écrite (0 fiche sur 4) — aucune bannière définitive")
else:
    print(f"ÉCHEC : {len(posees)} image(s) écrite(s) malgré le plafond : {posees}")
    echecs += 1

# ── 3. Contre-épreuve : sans plafond, le lot écrit bien ses visuels ─────────────
print("\n──── contre-épreuve : chaîne normale ────")
_base(4)
visuals.resolve_image = lambda ev, *a, **k: (
    "https://exemple.fr/banniere.jpg", "", "banner", 0.5, 0.5)
rc = visuals.main([])
posees = [(i, u, s) for i, u, s in _images_posees() if u]
if rc == 0 and len(posees) == 4:
    print("OK    4 visuels posés, code retour 0 — la correction n'a rien cassé")
else:
    print(f"ÉCHEC : rc={rc}, {len(posees)} image(s) posée(s), attendu rc=0 et 4")
    echecs += 1

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
