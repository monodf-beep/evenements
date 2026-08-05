#!/usr/bin/env python3
"""Fixture : l'apprentissage Slack distingue résolu / ouvert / disparu, groupe un
motif récurrent sur le bon AXE (source ou territoire selon le champ), et compare
au passage précédent pour ne signaler que ce qui est nouveau.

⚠️ BASE + ARCHIVE JETABLES — jamais data/events.db ni logs/slack/. Aucun réseau,
aucune clé API.

Scénario reconstruit à la main, dans le format RÉEL que `utils.slack.notify_incomplete`
écrit (le rappel `/agenda complete <id> ...` est ce que ce script utilise pour
retrouver l'id — le test vérifie donc aussi que ce format ne change pas en silence) :

  • fiches 1, 2 — source « Radio Piémont », territoire Piemonte, manquent Image ;
  • fiche 3 — même source, même manque, mais COMPLÈTE en base depuis → résolue ;
  • fiche 4 — signalée, mais n'existe plus en base (fusionnée) → disparue ;
  • fiche 5 — source « Gazette Savoie », TERRITOIRE PIEMONTE AUSSI, manque Image →
    doit rejoindre le motif de 1/2 (Image se groupe par TERRITOIRE, pas par source :
    autocomplete retente déjà la bannière chaque jour, ce qui manque encore est une
    bannière absente de config/territory_category_images.txt, pas une source fautive) ;
  • fiche 6 — MÊME source « Radio Piémont » que 1/2, mais territoire Nice, manque
    Image → NE DOIT PAS rejoindre le motif Piemonte (axe différent) ;
  • fiche 7 — source « Gazette Savoie », manque Lieu (pas Image) → Lieu se groupe par
    SOURCE : seule sur sa source, ne forme aucun motif à elle seule.

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
    # (id, titre, source, territoire, url_image, lieu)
    (1, "Concert au kiosque", "Radio Piémont", "Piemonte", None, "Place du kiosque"),
    (2, "Marché nocturne", "Radio Piémont", "Piemonte", None, "Cours Vittorio"),
    (3, "Fête du village", "Radio Piémont", "Piemonte", "https://a.fr/img.jpg", "Place"),
    (5, "Vide-grenier piémontais", "Gazette Savoie", "Piemonte", None, "Place du marché"),
    (6, "Concert niçois", "Radio Piémont", "Nice", None, "Cours Saleya"),
    (7, "Brocante savoyarde", "Gazette Savoie", "Savoie", "https://a.fr/img7.jpg", None),
]
for eid, titre, source, territoire, url_image, lieu in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, ville, "
        "territoire, lieu, statut, llm_score, llm_categorie, date_event_start, "
        "date_event_end, url_image, source_name) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (eid, titre, "d", f"https://a.fr/{eid}", "Ville", territoire, lieu, "evaluated",
         7, "Musique", "2026-11-01", "2026-11-01", url_image, source))
conn.commit()
conn.close()

# Archive : format RÉEL de utils.slack.notify_incomplete.
today = datetime.now().strftime("%Y-%m-%d")
lignes = [
    (1, "Concert au kiosque", "Image"),
    (2, "Marché nocturne", "Image"),
    (3, "Fête du village", "Image"),           # résolue depuis (url_image posée)
    (4, "Événement fusionné", "Lieu"),         # id 4 n'existe pas en base
    (5, "Vide-grenier piémontais", "Image"),   # autre source, même territoire
    (6, "Concert niçois", "Image"),            # même source, autre territoire
    (7, "Brocante savoyarde", "Lieu"),         # champ différent, seule sur sa source
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

if motifs.get("territoire=Piemonte::Image") == 3:
    print("OK    Image groupée par TERRITOIRE : 1, 2 (Radio Piémont) et 5 (Gazette "
         "Savoie) forment un seul motif de 3 fiches, malgré deux sources différentes")
else:
    echecs += 1
    print(f"ÉCHEC : attendu territoire=Piemonte::Image=3, obtenu "
         f"{motifs.get('territoire=Piemonte::Image')}")

if "territoire=Nice::Image" not in motifs and "source=Radio Piémont::Image" not in motifs:
    print("OK    la fiche 6 (même source, autre territoire) ne rejoint PAS le motif "
         "Piemonte et ne forme pas de motif seule")
else:
    echecs += 1
    print("ÉCHEC : la fiche 6 a été mal classée")

if "source=Gazette Savoie::Lieu" not in motifs:
    print("OK    la fiche 7 (Lieu, seule sur sa source) ne forme aucun motif")
else:
    echecs += 1
    print("ÉCHEC : une fiche isolée sur son axe a été comptée comme motif")

# Second passage : mêmes messages, aucun nouveau motif attendu (comparaison cumulative).
rc2 = learn.main(["--days", "30"])
etat2 = json.loads(learn.STATE_FILE.read_text(encoding="utf-8"))
if etat2["motifs"] == motifs and rc2 == 0:
    print("OK    second passage stable : mêmes motifs, rien de « nouveau » à répéter")
else:
    echecs += 1
    print(f"ÉCHEC : le second passage diverge : {etat2['motifs']}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
