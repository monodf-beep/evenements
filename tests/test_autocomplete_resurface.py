#!/usr/bin/env python3
"""Fixture : une fiche bloquée sur le MÊME manque doit reparaître sur Slack.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau, aucune clé API : le test
force `--no-web --no-banner --no-publish` et vérifie seulement le mécanisme de
notification, pas la résolution elle-même.

LE BUG TROUVÉ LE 2026-08-05 : l'anti-spam d'origine ne notifiait QUE si l'état
Slack changeait (`state != prev`). Une fiche dont le lieu reste introuvable
produit le MÊME état ("missing:Lieu") à chaque passage — donc UNE SEULE
notification, jamais revue, alors qu'autocomplete continue de la retenter tous
les jours en silence. C'est l'incident « LES 7 PROCHAINS JOURS : 0 carte » sous
une autre forme : un signal émis une fois, jamais relu.

Simule trois passages sur la MÊME fiche, sans jamais la compléter :
  jour 0 → notifiée (premier signal, état inédit) ;
  jour 1 → PAS notifiée (même état, moins de RESURFACE_DAYS depuis) ;
  jour 0 + RESURFACE_DAYS → RE-notifiée (ressurfaçage), avec la date d'origine.

Lancer : .venv/bin/python -m tests.test_autocomplete_resurface
"""
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)
os.environ.pop("ANTHROPIC_API_KEY", None)  # déterministe seulement

from scripts.scraper_events import init_db  # noqa: E402
import scripts.autocomplete as ac  # noqa: E402

ac.DB_PATH = tmp
ac.RESURFACE_DAYS = 3

envoyes = []
ac.slack.notify_incomplete = lambda ev, labels, note="": envoyes.append(
    (ev["id"], tuple(labels), note)) or True
ac.slack.notify_ready = lambda *a, **k: envoyes.append(("ready",)) or True

conn = sqlite3.connect(tmp)
init_db(conn)
conn.execute(
    "INSERT INTO events_raw (title, description, url_source, ville, territoire, "
    "lieu, statut, llm_score, llm_categorie, date_event_start, date_event_end, "
    "url_image) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
    ("Concert introuvable", "Un concert dont le lieu ne sera jamais trouvé.",
     "https://a.fr/x", "Annecy", "Savoie", None, "evaluated", 8, "Musique",
     "2026-11-15", "2026-11-15", "https://a.fr/img.jpg"))
conn.commit()
conn.close()


def _run():
    return ac.main(["--cap", "10", "--no-web", "--no-banner", "--no-publish"])


def _row():
    conn = sqlite3.connect(tmp)
    conn.row_factory = sqlite3.Row
    r = dict(conn.execute("SELECT * FROM events_raw WHERE id=1").fetchone())
    conn.close()
    return r


def _reculer(champ: str, jours: int) -> None:
    """Recule artificiellement une date en base — simule le passage du temps."""
    conn = sqlite3.connect(tmp)
    valeur = conn.execute(f"SELECT {champ} FROM events_raw WHERE id=1").fetchone()[0]
    nouvelle = (datetime.fromisoformat(valeur) - timedelta(days=jours)).isoformat(timespec="seconds")
    conn.execute(f"UPDATE events_raw SET {champ}=? WHERE id=1", (nouvelle,))
    conn.commit()
    conn.close()


echecs = 0

print("──── jour 0 : premier passage, état inédit ────")
_run()
if len(envoyes) == 1 and envoyes[0][0] == 1 and "Lieu" in envoyes[0][1]:
    print(f"OK    notifié : {envoyes[0]}")
else:
    echecs += 1
    print(f"ÉCHEC : {envoyes}")

print("\n──── jour 1 : même état, pas de nouvelle notification ────")
envoyes.clear()
_run()
if not envoyes:
    print("OK    silence (anti-spam normal)")
else:
    echecs += 1
    print(f"ÉCHEC : notifié alors que rien n'a changé : {envoyes}")

print(f"\n──── jour {ac.RESURFACE_DAYS} : ressurfaçage attendu ────")
_reculer("autocomplete_notified_at", ac.RESURFACE_DAYS)
_reculer("autocomplete_state_since", ac.RESURFACE_DAYS)
envoyes.clear()
_run()
if len(envoyes) == 1 and envoyes[0][0] == 1 and envoyes[0][2].startswith("Bloqué depuis"):
    print(f"OK    re-notifié avec la date d'origine : {envoyes[0][2]}")
else:
    echecs += 1
    print(f"ÉCHEC : {envoyes}")

row = _row()
print(f"\nautocomplete_state_since inchangé depuis le premier passage : "
     f"{row['autocomplete_state_since']}")

print("\n──── contre-épreuve : un VRAI changement notifie tout de suite ────")
# On aggrave le manque (ville aussi vide) plutôt que de compléter : une fiche
# complétée SORT de la sélection avant même d'atteindre la notification (ligne
# `incomplete = [r for r in rows if not comp.is_complete(r)]`) — pas le mécanisme
# testé ici. Un manque DIFFÉRENT, lui, reste dans la boucle : c'est le bon test.
conn = sqlite3.connect(tmp)
conn.execute("UPDATE events_raw SET ville='' WHERE id=1")
conn.commit()
conn.close()
envoyes.clear()
_run()
if len(envoyes) == 1 and envoyes[0][0] == 1 and set(envoyes[0][1]) == {"Lieu", "Ville"} \
        and envoyes[0][2] == "":
    print(f"OK    nouveau manque → notifié immédiatement, sans attendre RESURFACE_DAYS : "
         f"{envoyes[0]}")
else:
    echecs += 1
    print(f"ÉCHEC : {envoyes}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
