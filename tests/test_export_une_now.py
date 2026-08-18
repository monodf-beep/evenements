#!/usr/bin/env python3
"""Fixture : l'export qui contourne le tuyau bloqué doit dire vrai, et ne marquer qu'après.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau.

D'OÙ ÇA VIENT (2026-08-18). Le VPS ne joint plus le site ; `publish_batch_as` est le seul
chemin par lequel `as_une_now` atteint WordPress. `export_une_now` sépare le CALCUL (local,
qui marche) du TRANSPORT (bloqué) pour qu'un autre canal écrive les valeurs.

CE QUE LA FIXTURE SURVEILLE :
  1. les valeurs exportées sont EXACTEMENT celles que `publisher_as` aurait posées —
     sinon on écrirait à la main un classement différent de celui du pipeline, et les deux
     se contrediraient au retour du réseau ;
  2. une fiche hors une est exportée VIDE, pas absente : « pas sa place » n'est pas
     « jamais calculée », et c'est la distinction qui permet de tout marquer ensuite ;
  3. ⚠️ SANS `--marquer`, RIEN n'est écrit en base. C'est la garantie qui compte : marquer,
     c'est écrire « WordPress a cette valeur », et le faire sans preuve fabriquerait
     précisément le mensonge que la règle 1 interdit ;
  4. avec `--marquer`, la base porte les mêmes valeurs — donc le rafraîchisseur ne
     republiera pas tout le catalogue au retour du réseau.

Lancer : .venv/bin/python -m tests.test_export_une_now
"""
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db      # noqa: E402
import scripts.export_une_now as ex             # noqa: E402
from utils.une import une_now                   # noqa: E402

ex.DB_PATH = tmp
AUJ = date.today()
DANS_8_J = (AUJ + timedelta(days=8)).isoformat()
PASSE = (AUJ - timedelta(days=5)).isoformat()

DETAIL = json.dumps({"rayonnement": {"points": 2}, "specificite_territoriale": {"points": 1},
                     "edition_tradition": {"points": 2}, "notoriete_lieu": {"points": 3}})
ARTICLE = json.dumps({"article": {"chapo": "Le grand rendez-vous revient.",
                                  "corps": "Une journée entière de spectacles."},
                      "home": {"affiches": "deux"}})

# (id, wp_post_id, titre, début, fin)
FICHES = [
    (1, 6380, "Tour de l'Avenir", DANS_8_J, DANS_8_J),   # en une → 13
    (2, 6381, "Fête déjà passée", PASSE, PASSE),         # hors une → ""
]

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, wp, titre, deb, fin in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, wp_post_id_as, statut, "
        "llm_categorie, llm_score_detail, date_event_start, date_event_end, territoire, "
        "duplicate_of, enrich_status, home_score, url_image, enrich_data, article_title) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,NULL,?,?,?,?,?)",
        (eid, titre, f"https://a.fr/{eid}", wp, "published_sub", "Festivals", DETAIL,
         deb, fin, "Piemonte", "enriched", 8.0, f"https://exemple.fr/p/{eid}.jpg",
         ARTICLE, titre))
conn.commit(); conn.close()

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


def _json_de(sortie: str) -> dict:
    for ligne in sortie.splitlines():
        if ligne.startswith("{"):
            return json.loads(ligne)
    return {}


print("──── l'export dit ce que le pipeline aurait posé ────")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ex.main([])
sortie = buf.getvalue()
donnees = _json_de(sortie)

conn = sqlite3.connect(tmp); conn.row_factory = sqlite3.Row
lignes = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM events_raw")}
conn.close()

_check(f"la fiche en une est exportée à sa valeur ({donnees.get('6380')})",
       donnees.get("6380") == str(une_now(lignes[1], AUJ)), donnees)
_check("   et c'est bien 13, la valeur vérifiée en production",
       donnees.get("6380") == "13", donnees)
_check("la fiche hors une est exportée VIDE, pas absente",
       "6381" in donnees and donnees["6381"] == "", donnees)
_check("l'export annonce son périmètre et son dénominateur",
       "Fiches liées à un post WordPress : 2" in sortie
       and "place en une aujourd'hui" in sortie, sortie[:400])
_check("   et montre les plus hautes, pour reconnaître le résultat sur le site",
       "WP#6380" in sortie, sortie[:600])

print("\n──── l'empreinte rend le transport vérifiable sans faire confiance ────")
# D'OÙ ÇA VIENT : le 2026-08-18, ce JSON a traversé une conversation et UNE entrée vide
# s'est perdue à la recopie. Le compte l'a attrapée — mais un compte juste avec une VALEUR
# modifiée serait passé. L'empreinte couvre les deux, et se recalcule côté destinataire :
# le contrôle ne dépend donc plus de qui transporte.
import hashlib  # noqa: E402
attendue = hashlib.sha256(
    json.dumps(donnees, separators=(",", ":"), sort_keys=True).encode("utf-8")
).hexdigest()[:12]
_check("la sortie porte une empreinte du JSON",
       f"sha256(12) = {attendue}" in sortie,
       sortie[sortie.find("CONTRÔLE"):][:300])
_check("   et le compte d'entrées à côté d'elle", "entrées = 2 · non vides = 1" in sortie,
       sortie[sortie.find("CONTRÔLE"):][:300])
_check("   avec la commande pour la recalculer de l'autre côté",
       "hash('sha256'" in sortie, sortie[sortie.find("CONTRÔLE"):][:300])
# ⚠️ ET SURTOUT : l'empreinte doit CHANGER si une seule entrée bouge. Sans ce contrôle-ci,
# on aurait pu poser une constante et croire le transport vérifié.
autre = dict(donnees); autre["6381"] = "4"
bougee = hashlib.sha256(
    json.dumps(autre, separators=(",", ":"), sort_keys=True).encode("utf-8")
).hexdigest()[:12]
_check("une seule valeur modifiée change l'empreinte", bougee != attendue,
       f"{attendue} vs {bougee}")

print("\n──── ⚠️ sans --marquer, la base ne bouge pas ────")
conn = sqlite3.connect(tmp)
cols = [c[1] for c in conn.execute("PRAGMA table_info(events_raw)")]
vals = ([r[0] for r in conn.execute("SELECT une_now_publie FROM events_raw")]
        if "une_now_publie" in cols else [])
conn.close()
_check("aucune valeur de suivi n'a été écrite — l'export est en lecture seule",
       all(v is None for v in vals), vals)
_check("   et la sortie rappelle que le marquage vient APRÈS la confirmation",
       "APRÈS sa confirmation seulement" in sortie, sortie[-300:])

print("\n──── avec --marquer, la base porte les mêmes valeurs ────")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ex.main(["--apply"])
marque = buf.getvalue()

conn = sqlite3.connect(tmp); conn.row_factory = sqlite3.Row
apres = {r["wp_post_id_as"]: r["une_now_publie"] for r in
         conn.execute("SELECT wp_post_id_as, une_now_publie FROM events_raw")}
conn.close()
_check("la fiche en une est marquée à 13", apres.get(6380) == "13", apres)
_check("la fiche hors une est marquée VIDE (pas NULL) — sinon elle serait republiée",
       apres.get(6381) == "", apres)
_check("le bilan RECOMPTE en base au lieu d'annoncer une longueur de liste",
       "2 fiche(s) marquées sur 2 (recompté en base)" in marque, marque)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
