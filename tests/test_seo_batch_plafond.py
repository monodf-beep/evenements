#!/usr/bin/env python3
"""Fixture : un plafond API pendant le SEO en lot arrête proprement, au lieu de
marteler une erreur par fiche.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau, aucune clé API.

TROUVÉ EN PRODUCTION le 2026-08-05 (VPS, crédit insuffisant) : 16 erreurs
identiques « Your credit balance is too low », dont 10 martelées par seo_batch en
13 secondes — une par fiche, exactement le cap. Même trou que translate_events.py
avant sa garde du matin même : `utils.seo.optimize_seo` laisse VOLONTAIREMENT
remonter les exceptions API (sa docstring : sa seconde appelante, une route
Flask, les gère elle-même) — mais la boucle de seo_batch.py les attrapait toutes
avec un `except Exception` générique, "jamais bloquant", continuant à essayer
chaque fiche suivante pour rien.

Le test force un plafond sur la DEUXIÈME de trois fiches et vérifie :
  • la première fiche (traitée avant le plafond) est bien enregistrée ;
  • le run ne plante PAS et ne martèle PAS (la 3e fiche n'est jamais tentée) ;
  • le code retour est 3 (non nul, visible par le chien de garde) ;
  • une panne ORDINAIRE (pas un plafond) reste tolérée par fiche, sans arrêter le lot.

Lancer : .venv/bin/python -m tests.test_seo_batch_plafond
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
import scripts.seo_batch as seo_batch  # noqa: E402

seo_batch.DB_PATH = tmp


class ErreurPlafond(Exception):
    status_code = 400

    def __str__(self):
        return "Error code: 400 - Your credit balance is too low to access the Anthropic API."


class ErreurOrdinaire(Exception):
    def __str__(self):
        return "JSON invalide renvoyé par le modèle."


def _base():
    if tmp.exists():
        tmp.unlink()
    conn = sqlite3.connect(tmp)
    init_db(conn)
    for i in range(1, 4):
        conn.execute(
            "INSERT INTO events_raw (id, title, description, url_source, ville, "
            "territoire, lieu, statut, llm_score, llm_categorie, date_event_start, "
            "date_event_end) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (i, f"Concert {i}", "d", f"https://a.fr/{i}", "Annecy", "Savoie",
             "Salle", "evaluated", 8, "Musique", "2026-11-15", "2026-11-15"))
    conn.commit()
    conn.close()


def _seo_at_poses():
    conn = sqlite3.connect(tmp)
    n = conn.execute("SELECT COUNT(*) FROM events_raw WHERE seo_at IS NOT NULL").fetchone()[0]
    conn.close()
    return n


echecs = 0

print("──── plafond sur la 2e fiche : arrêt net ────")
_base()
appels = []


def _faux_optimize(ev, client, model):
    appels.append(ev["id"])
    if ev["id"] == 2:
        raise ErreurPlafond()
    return {"seo_title": "t", "seo_meta": "m", "seo_answer": "a", "seo_faq": [],
           "seo_keyphrase": "k", "seo_slug": "s", "seo_tags": []}


seo_batch.seo_mod.optimize_seo = _faux_optimize
rc = seo_batch.main(["--cap", "10", "--delay", "0"])

if appels == [1, 2]:
    print(f"OK    arrêt net après la fiche en plafond : appels={appels} (fiche 3 jamais tentée)")
else:
    echecs += 1
    print(f"ÉCHEC : appels={appels}, attendu [1, 2]")

if rc == 3:
    print("OK    code retour 3 (non nul, visible par le chien de garde)")
else:
    echecs += 1
    print(f"ÉCHEC : code retour {rc}, attendu 3")

if _seo_at_poses() == 1:
    print("OK    une seule fiche a reçu un SEO (celle traitée avant le plafond)")
else:
    echecs += 1
    print(f"ÉCHEC : {_seo_at_poses()} fiche(s) avec seo_at, attendu 1")

print("\n──── contre-épreuve : une panne ORDINAIRE ne stoppe pas le lot ────")
_base()
appels.clear()


def _faux_optimize_ordinaire(ev, client, model):
    appels.append(ev["id"])
    if ev["id"] == 2:
        raise ErreurOrdinaire()
    return {"seo_title": "t", "seo_meta": "m", "seo_answer": "a", "seo_faq": [],
           "seo_keyphrase": "k", "seo_slug": "s", "seo_tags": []}


seo_batch.seo_mod.optimize_seo = _faux_optimize_ordinaire
rc2 = seo_batch.main(["--cap", "10", "--delay", "0"])

if appels == [1, 2, 3]:
    print(f"OK    les trois fiches tentées malgré la panne sur la 2e : {appels}")
else:
    echecs += 1
    print(f"ÉCHEC : appels={appels}, attendu [1, 2, 3]")

if rc2 == 1:  # 1 échec (fiche 2), pas de plafond → code existant préservé
    print("OK    code retour 1 (échec de fiche ordinaire, pas un plafond) — comportement inchangé")
else:
    echecs += 1
    print(f"ÉCHEC : code retour {rc2}, attendu 1")

if _seo_at_poses() == 2:
    print("OK    deux fiches sur trois ont reçu un SEO (1 et 3, la 2 a juste échoué)")
else:
    echecs += 1
    print(f"ÉCHEC : {_seo_at_poses()} fiche(s) avec seo_at, attendu 2")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
