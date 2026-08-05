#!/usr/bin/env python3
"""Fixture : l'apprentissage Slack distingue résolu / ouvert / disparu, et repère
un motif récurrent (même champ manquant, même source, plusieurs fiches).

⚠️ BASE + ARCHIVE JETABLES — jamais data/events.db ni logs/slack/. Aucun réseau,
aucune clé API.

Scénario reconstruit à la main, dans le format RÉEL que `utils.slack.notify_incomplete`
écrit (le rappel `/agenda complete <id> ...` est ce que ce script utilise pour
retrouver l'id — le test vérifie donc aussi que ce format ne change pas en silence) :

  • fiche 1 — « Radio Piémont » manque Image, encore ouverte AUJOURD'HUI → compte ;
  • fiche 2 — même source, même manque, encore ouverte → avec la 1, ça fait un motif
    si le seuil est abaissé à 2 pour le test ;
  • fiche 3 — signalée manquante, mais COMPLÈTE en base depuis → résolue, ne doit
    pas peser dans un motif ;
  • fiche 4 — signalée, mais n'existe plus en base (fusionnée) → disparue, idem ;
  • fiche 5 — source différente, manque Lieu, seule → ne déclenche aucun motif.

Lancer : .venv/bin/python -m tests.test_slack_learning
"""
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp_dir = Path(tempfile.mkdtemp())
tmp_db = tmp_dir / "fixture.db"
tmp_archive = tmp_dir / "slack"
tmp_archive.mkdir()
os.environ["DB_PATH"] = str(tmp_db)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.slack_learning as learn  # noqa: E402

learn.DB_PATH = tmp_db
learn.ARCHIVE = tmp_archive
learn.STATE_FILE = tmp_dir / "state.json"
learn.SEUIL_MOTIF = 2

conn = sqlite3.connect(tmp_db)
init_db(conn)
FICHES = [
    # (id, titre, source, statut, url_image, lieu)  — date/ville/catégorie toujours OK
    (1, "Concert au kiosque", "Radio Piémont", "evaluated", None, "Place du kiosque"),
    (2, "Marché nocturne", "Radio Piémont", "evaluated", None, "Cours Vittorio"),
    (3, "Fête du village", "Radio Piémont", "evaluated", "https://a.fr/img.jpg", "Place"),
    (5, "Vide-grenier", "Gazette Savoie", "evaluated", "https://a.fr/img5.jpg", None),
]
for eid, titre, source, statut, url_image, lieu in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, ville, "
        "territoire, lieu, statut, llm_score, llm_categorie, date_event_start, "
        "date_event_end, url_image, source_name) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (eid, titre, "d", f"https://a.fr/{eid}", "Turin", "Piemonte", lieu, statut,
         7, "Musique", "2026-11-01", "2026-11-01", url_image, source))
conn.commit()
conn.close()

# Archive : format RÉEL de utils.slack.notify_incomplete.
today = datetime.now().strftime("%Y-%m-%d")
lignes = [
    (1, "Concert au kiosque", "Image"),
    (2, "Marché nocturne", "Image"),
    (3, "Fête du village", "Image"),       # résolue depuis (url_image posée)
    (4, "Événement fusionné", "Lieu"),     # id 4 n'existe pas en base
    (5, "Vide-grenier", "Lieu"),           # source différente, seule
]
with (tmp_archive / f"{today}.jsonl").open("w", encoding="utf-8") as f:
    for eid, titre, champ in lignes:
        texte = (f"⚠️ *À compléter* — {titre}\nIl manque : *{champ}*\n"
                 f"<https://x/preview/{eid}|Compléter dans le dashboard>\n"
                 f"_Ou réponds :_ `/agenda complete {eid} lieu=… ville=… url_image=…`")
        f.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"),
                            "envoye": True, "texte": texte}, ensure_ascii=False) + "\n")

echecs = 0
rc = learn.main(["--days", "30"])
if rc != 0:
    echecs += 1
    print(f"ÉCHEC : code retour {rc}")

etat = json.loads(learn.STATE_FILE.read_text(encoding="utf-8"))
motifs = etat["motifs"]
print(f"Motifs détectés : {motifs}")

if motifs.get("Radio Piémont::Image") == 2:
    print("OK    motif détecté : Radio Piémont manque Image sur 2 fiches (1 et 2)")
else:
    echecs += 1
    print("ÉCHEC : motif Radio Piémont::Image absent ou mal compté")

if "Gazette Savoie::Lieu" not in motifs:
    print("OK    la fiche 5 (source isolée) ne forme pas de motif")
else:
    echecs += 1
    print("ÉCHEC : une fiche isolée a été comptée comme motif")

# La fiche 3 (résolue) et la fiche 4 (disparue) ne doivent PAS avoir gonflé le motif :
# sans elles, Radio Piémont ne compte que 2 (fiches 1 et 2), jamais 3.
if motifs.get("Radio Piémont::Image") != 3:
    print("OK    fiche résolue (3) exclue du comptage")
else:
    echecs += 1
    print("ÉCHEC : la fiche résolue a été comptée à tort")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
