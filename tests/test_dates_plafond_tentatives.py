#!/usr/bin/env python3
"""Fixture : cesser de re-tenter une datation impossible — SANS refabriquer une impasse.

MESURÉ le 2026-08-11 : 79 des 95 fiches incomplètes encore devant nous n'ont pas de date,
et toutes ont déjà reçu un verdict de dates.py. Le ré-armement automatique (ajouté après
l'incident des 823 fiches endormies) les re-tente tous les sept jours — indéfiniment, et
elles échouent à chaque fois. Le correctif d'hier avait supprimé un cul-de-sac ; il en
avait créé un à l'envers.

VÉRIFIÉ, PAS SUPPOSÉ : la page de « Per Olivia » (Teatro Stabile di Torino, fiche 2374) a
été récupérée à la main. Elle ne contient AUCUNE date — ni en texte, ni en JSON-LD, ni en
méta. Le spectacle appartient à la « Stagione 2026-2027 » et ses dates vivent dans la
billetterie. D'autres fiches n'ont même pas d'URL (« gmail:<id>#<n> »). Aucun modèle ne
fera apparaître ce qui n'est pas là.

D'où un plafond de tentatives — et la question que CLAUDE.md (règle 3) impose de traiter
AVANT de poser un état terminal : QUI LE ROUVRE ? Réponse ici, et c'est ce que la fixture
vérifie : **le changement de la matière**. Si le titre, la description ou l'URL changent,
un nouvel essai peut légitimement donner autre chose, donc le compteur repart à zéro, tout
seul, sans commande. Si rien ne change, re-tenter c'est repayer le même échec.

Cas choisis exprès des DEUX côtés de la frontière — un test qui ne cherche qu'à se donner
raison ne prouve rien (CLAUDE.md, règle 3) :
  • 2 échecs → doit encore être re-tentée (le plafond ne mord pas trop tôt) ;
  • 3 échecs, matière inchangée → ne doit PLUS être re-tentée ;
  • 3 échecs, matière CHANGÉE → doit être rouverte automatiquement ;
  • 3 échecs + --retry → doit être rouverte (la main de l'humain passe toujours) ;
  • déjà datée → n'est jamais concernée.

Aucun réseau : --no-fetch --no-llm.

Lancer : .venv/bin/python -m tests.test_dates_plafond_tentatives
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

from scripts.scraper_events import init_db  # noqa: E402
import scripts.dates as dates  # noqa: E402

dates.DB_PATH = tmp

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


VIEUX = "2026-01-01 00:00:00"          # bien au-delà du délai de carence
conn = sqlite3.connect(tmp)
init_db(conn)
dates.ensure_columns(conn)
dates._ensure_colonnes_tentatives(conn)

# (id, titre, tentatives, matière enregistrée alors, date déjà connue ?)
CAS = [
    (1, "Deux échecs seulement",        2, "empreinte-du-jour",  ""),
    (2, "Trois échecs, rien n'a bougé", 3, "empreinte-du-jour",  ""),
    (3, "Trois échecs, matière changée", 3, "AUTRE-empreinte",   ""),
    (4, "Déjà datée",                   3, "empreinte-du-jour",  "2026-12-01"),
]
for eid, titre, n, _emp, date_connue in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, statut, "
        "date_source, date_checked_at, date_tentatives, date_event_start) "
        "VALUES (?,?,?,?, 'evaluated', 'llm_none', ?, ?, ?)",
        (eid, titre, "Aucune date dans ce texte.", f"https://x/{eid}", VIEUX, n, date_connue))
conn.commit()
# L'empreinte réelle des fiches 1, 2 et 4 : celle de leur matière ACTUELLE (donc
# « inchangée depuis le dernier échec »). La 3 garde une empreinte étrangère → changée.
conn.row_factory = sqlite3.Row
for eid in (1, 2, 4):
    r = dict(conn.execute("SELECT id,title,description,url_source FROM events_raw "
                          "WHERE id=?", (eid,)).fetchone())
    conn.execute("UPDATE events_raw SET date_matiere=? WHERE id=?",
                 (dates._empreinte_matiere(r), eid))
conn.execute("UPDATE events_raw SET date_matiere='EMPREINTE-PERIMEE' WHERE id=3")
conn.commit()
conn.close()

# ── Run normal : le plafond s'applique, le rouvreur aussi ───────────────────────
print("──── run normal (--no-fetch --no-llm) ────")
dates.main(["--no-fetch", "--no-llm", "--no-republish"])

conn = sqlite3.connect(tmp)
etat = {r[0]: (r[1], r[2]) for r in conn.execute(
    "SELECT id, date_source, date_tentatives FROM events_raw")}
conn.close()

_check("2 échecs → re-tentée (date_source ré-armé à 'none')", etat[1][0] == "none",
       f"obtenu {etat[1]}")
_check("3 échecs, matière inchangée → PLUS re-tentée", etat[2][0] == "llm_none",
       f"obtenu {etat[2]}")
_check("3 échecs, matière CHANGÉE → rouverte toute seule", etat[3][0] == "none",
       f"obtenu {etat[3]}")
_check("… et son compteur est remis à zéro", etat[3][1] == 0, f"obtenu {etat[3]}")
_check("fiche déjà datée → jamais touchée", etat[4][0] == "llm_none", f"obtenu {etat[4]}")

# ── --retry : la main de l'humain passe outre le plafond ────────────────────────
print("\n──── --retry : le plafond ne bloque pas un geste explicite ────")
dates.main(["--no-fetch", "--no-llm", "--no-republish", "--retry"])
conn = sqlite3.connect(tmp)
apres = {r[0]: r[1] for r in conn.execute("SELECT id, date_source FROM events_raw")}
conn.close()
_check("la fiche plafonnée est ré-armée par --retry", apres[2] == "none",
       f"obtenu {apres[2]}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
