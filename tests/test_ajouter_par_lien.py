#!/usr/bin/env python3
"""Fixture : un événement signalé par un lien entre dans la chaîne — et seulement lui.

Base jetable (scripts.scraper_events.init_db), aucun réseau : la lecture de page est
remplacée. Premier cas réel : le post Instagram de la Fiera del Marrone (26/09/2026).

CE QUE LA FIXTURE PROTÈGE :
  • qu'un réseau social ne soit JAMAIS accepté comme page officielle, ni une ligne sans
    titre ou au territoire inconnu — la ligne arrête tout au lieu d'être sautée ;
  • le cas qui doit PASSER près de la frontière : la même page déjà en base sous une
    autre graphie (http, sans www, barre finale) est reconnue, pas réinsérée ;
  • qu'une page muette n'entre pas vide, et qu'en simulation rien ne s'écrive ;
  • qu'un signalement passe devant un événement mieux noté dans la file de rédaction,
    mais pas une fiche ordinaire.

Lancer : .venv/bin/python -m tests.test_ajouter_par_lien
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp())
os.environ["DB_PATH"] = str(tmp / "fixture.db")

from scripts.scraper_events import init_db  # noqa: E402
from scripts import ajouter_par_lien as apl  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    print(("OK    " if ok else "ÉCHEC ") + libelle + ("" if ok else f" — {detail}"))
    echecs += 0 if ok else 1


def liste(*lignes) -> Path:
    f = tmp / f"l{len(list(tmp.iterdir()))}.tsv"
    f.write_text("# commentaire\n\n" + "\n".join("\t".join(l) for l in lignes) + "\n",
                 encoding="utf-8")
    return f


def refuse(lignes, motif) -> None:
    try:
        apl.lire_liste(liste(*lignes))
        verifier(f"refus : {motif}", False, "ligne acceptée")
    except SystemExit as e:
        verifier(f"refus : {motif}", True, str(e))


IG = "https://www.instagram.com/p/DdtgNflG8ny/"
refuse([(IG, "Piemonte", "Fiera", IG, "")], "Instagram comme page officielle")
refuse([("https://www.marrone.net/", "Piemont", "Fiera", IG, "")], "territoire inconnu")
refuse([("https://www.marrone.net/", "Piemonte", "", IG, "")], "titre vide")

conn = sqlite3.connect(os.environ["DB_PATH"])
conn.row_factory = sqlite3.Row
init_db(conn)
conn.execute("INSERT INTO events_raw (title, url_source, statut) VALUES "
             "('Fête déjà connue', 'http://fete.example.fr/programme', 'evaluated')")
conn.commit()

lignes = apl.lire_liste(liste(
    ("https://www.marrone.net/edizione-corrente/programma/", "Piemonte",
     "Fiera Nazionale del Marrone", IG, "Du 16 au 18 octobre 2026."),
    ("https://www.fete.example.fr/programme/", "Savoie", "Fête", IG, ""),
    ("https://muette.example.fr/", "Nice", "Page muette", IG, ""),
))
verifier("trois lignes valides lues", len(lignes) == 3, str(len(lignes)))

pages = {"https://www.marrone.net/edizione-corrente/programma/":
         "Fiera del Marrone 27ª edizione – dal 16 al 18 ottobre 2026"}
lire = lambda url: pages.get(url, "")  # noqa: E731

b = apl.ajouter(conn, lignes, apply=False, lire=lire)
n = conn.execute("SELECT COUNT(*) FROM events_raw").fetchone()[0]
verifier("simulation : rien d'écrit", n == 1, f"{n} lignes")

b = apl.ajouter(conn, lignes, apply=True, lire=lire)
verifier("bilan : 1 insérée, 1 déjà en base, 1 muette",
         (b["insere"], b["deja"], b["injoignable"]) == (1, 1, 1), str(b))
r = conn.execute("SELECT * FROM events_raw WHERE url_source LIKE '%marrone%'").fetchone()
verifier("titre = le nom donné, pas celui de la rubrique",
         r["title"] == "Fiera Nazionale del Marrone", r["title"])
verifier("page officielle en source ET en url_officiel",
         r["url_officiel"] == r["url_source"], r["url_officiel"])
verifier("le lien signalé est gardé, pas publié", r["source_name"] == f"signalement : {IG}",
         r["source_name"])
verifier("statut pending, territoire posé", (r["statut"], r["territoire"]) ==
         ("pending", "Piemonte"), f"{r['statut']} {r['territoire']}")
verifier("la note passe en tête de la description",
         r["description"].startswith("Du 16 au 18 octobre 2026."), r["description"][:60])

b = apl.ajouter(conn, lignes, apply=True, lire=lire)
verifier("idempotent : rien de réinséré au second passage", b["insere"] == 0, str(b))

# File de rédaction : le signalement noté 5 passe devant une fiche notée 9 ; une fiche
# ordinaire notée 5 reste derrière.
from scripts.enrich import select_events  # noqa: E402
conn.execute("UPDATE events_raw SET statut='published_sub', llm_score=5, "
             "date_event_start='2099-10-16' WHERE id=?", (r["id"],))
for titre, score in (("Ordinaire bien notée", 9), ("Ordinaire moyenne", 5)):
    conn.execute("INSERT INTO events_raw (title, url_source, statut, llm_score, "
                 "date_event_start) VALUES (?,?,'evaluated',?,'2099-10-16')",
                 (titre, "https://x.example.fr/" + str(score), score))
conn.commit()
ordre = [e["title"] for e in select_events(conn, [])]
verifier("signalement en tête de la file de rédaction",
         ordre[:3] == ["Fiera Nazionale del Marrone", "Ordinaire bien notée",
                       "Ordinaire moyenne"], str(ordre))

print(f"\n{'ÉCHEC' if echecs else 'OK'} — {echecs} échec(s)")
sys.exit(1 if echecs else 0)
