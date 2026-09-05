#!/usr/bin/env python3
"""Fixture : un plafond API pendant l'auto-complétion arrête le lot PROPREMENT.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau, aucune clé API.

TROUVÉ le 2026-08-05 en corrigeant scripts/visuals.py (portillon plafond) : les trois
passes de complete_event() (_fill_date, _fill_venue, _fill_image) appellent chacune un
helper qui RE-LÈVE PlafondAPI (dates.py, venues.py, et depuis le même jour
visuals.resolve_image) — mais rien, dans la boucle principale d'autocomplete.py,
n'attrapait cette exception. Un plafond aurait fait PLANTER tout le run (traceback
Python, aucun code retour exploitable) au lieu de s'arrêter proprement comme
dates.py/venues.py/translate_events.py/visuals.py savent déjà le faire.

Le test force un plafond sur la DEUXIÈME de trois fiches et vérifie :
  • la première fiche (traitée avant le plafond) est bien enregistrée ;
  • le run ne plante PAS (pas d'exception qui remonte à l'appelant) ;
  • le code retour est 3 (non nul, visible par le chien de garde) ;
  • la troisième fiche n'a REÇU AUCUNE écriture (elle n'a pas été tentée).

Lancer : .venv/bin/python -m tests.test_autocomplete_plafond
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
os.environ.pop("ANTHROPIC_API_KEY", None)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.autocomplete as ac  # noqa: E402
from utils.api_limite import PlafondAPI  # noqa: E402

ac.DB_PATH = tmp

conn = sqlite3.connect(tmp)
init_db(conn)
for i in range(1, 4):
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, ville, "
        "territoire, lieu, statut, llm_score, llm_categorie, date_event_start, "
        "date_event_end, url_image) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (i, f"Concert {i}", "d", f"https://a.fr/{i}", "Annecy", "Savoie", None,
         "evaluated", 8, "Musique", "2026-11-15", "2026-11-15", "https://a.fr/img.jpg"))
conn.commit()
conn.close()

appels = []


def _faux_complete_event(ev, *a, **k):
    appels.append(ev["id"])
    if ev["id"] == 2:
        raise PlafondAPI("plafond simulé")
    ev = dict(ev)
    ev["lieu"] = "Salle des fêtes"
    return ev


ac.complete_event = _faux_complete_event

rc = ac.main(["--cap", "10", "--no-web", "--no-banner", "--no-publish"])

echecs = 0
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

conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
lignes = {r["id"]: r["autocomplete_at"] for r in conn.execute(
    "SELECT id, autocomplete_at FROM events_raw")}
conn.close()
# La fiche 1 est passée AVANT le plafond : la boucle a eu le temps d'écrire son passage
# (complete_event() lui-même est mocké, donc `lieu` n'est pas réécrit ici — ce qu'on
# vérifie est le témoin que la boucle a bien continué son travail habituel, pas
# stoppé net dès le premier appel).
if lignes[1] is not None:
    print("OK    fiche 1 (traitée avant le plafond) marquée autocomplete_at")
else:
    echecs += 1
    print(f"ÉCHEC : fiche 1 sans trace de passage : {lignes}")
if lignes[3] is None:
    print("OK    fiche 3 (jamais tentée) n'a reçu aucune écriture")
else:
    echecs += 1
    print(f"ÉCHEC : fiche 3 a été touchée alors qu'elle n'a jamais été tentée : {lignes}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
