#!/usr/bin/env python3
"""Fixture : les dates antérieures à leur propre collecte, et la correction sous poignée
de main. Base jetable — jamais data/events.db.

DEUX MOITIÉS, parce que le défaut a deux bouts :

  1. `audit_annee_date` VOIT-il la fiche datée l'an dernier, et surtout : laisse-t-il
     tranquille tout le reste ? C'est là que se joue l'exigence de la règle 3 — la
     fixture contient des cas qui doivent PASSER, choisis près de la frontière, dont
     celui à 55 jours (la grâce de `dates._year()` en vaut 60 : une date légitimement
     un peu passée doit franchir le portillon, sinon l'audit rend une liste de bruit
     et personne ne la lira, exactement comme les 25 « fautes » de temps du 06/08) ;

  2. `completer_verifie --depuis` sait-il CORRIGER une valeur fausse — et refuse-t-il de
     le faire quand la base ne porte plus ce que la correction croyait remplacer ? Un
     agent qui écrase à l'aveugle effacerait la correction faite à la main la veille,
     sans un mot.

Lancer : .venv/bin/python -m tests.test_annee_date
"""
import json
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import audit_annee_date, completer_verifie  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


AUJ = date(2026, 8, 11)          # le jour où l'agent a signalé les trois fiches
COLLECTE = AUJ.isoformat() + " 06:12:00"

tmp = Path(tempfile.mkdtemp(prefix="fixture-annee-"))
db = tmp / "events.db"
conn = sqlite3.connect(db)
init_db(conn)
# `multi_lieux` naît dans app/app.py, pas dans init_db : le recompte final de
# completer_verifie passe par la clause du back-office, qui la lit.
try:
    conn.execute("ALTER TABLE events_raw ADD COLUMN multi_lieux INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass
conn.execute("""CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, label TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT)""")

# ── Le jeu d'essai ───────────────────────────────────────────────────────────────────
# (id, titre, description, début, fin, source, statut, récurrent, collecte)
CAS = [
    # ── Ce qui DOIT être signalé ─────────────────────────────────────────────────────
    (4434, "Fête patronale de Bard",
     "Come ogni anno, la festa si tiene il 15 agosto 2024 in piazza.",
     "2024-08-15", "2024-08-15", "parsed", "pending", 0, COLLECTE),
    (4691, "Rencontres du cinéma de montagne",
     "L'édition s'est déroulée du 3 au 6 octobre 2024 au Palais des Congrès.",
     "2024-10-03", "2024-10-06", "page", "pending", 0, COLLECTE),
    (4440, "Concert au Théâtre de Verdure",
     "Programme complet en ligne.",                 # l'année n'est PAS dans le texte
     "2025-07-20", "2025-07-20", "page", "pending", 0, COLLECTE),

    # ── Ce qui doit PASSER : les cas près de la frontière ────────────────────────────
    # 55 jours de retard : DANS la grâce de dates._year(). Le signaler rendrait une file
    # pleine d'événements légitimement passés — le contraire de ce qu'on cherche.
    (100, "Festival de juin", "Belle édition.",
     (AUJ - timedelta(days=55)).isoformat(), (AUJ - timedelta(days=55)).isoformat(),
     "parsed", "pending", 0, COLLECTE),
    # Exposition EN COURS : début passé de six mois, mais la fin décide (règle 5).
    (101, "Exposition Manara", "Du 3 juin au 13 septembre.",
     "2026-02-03", "2026-09-13", "parsed", "pending", 0, COLLECTE),
    # À venir, le cas ordinaire.
    (102, "Foire de Saint-Ours", "Les 30 et 31 janvier 2027.",
     "2027-01-30", "2027-01-31", "parsed", "pending", 0, COLLECTE),
    # Récurrente : pas de date unique, donc pas de date fausse possible.
    (103, "Visites du château", "Toute l'année.",
     "2024-01-01", "2024-01-01", "parsed", "pending", 1, COLLECTE),
    # Déjà écartée : elle n'est plus dans aucune file, la signaler serait du bruit.
    (104, "Compte rendu 2024", "Retour sur l'édition 2024.",
     "2024-05-05", "2024-05-05", "parsed", "rejected", 0, COLLECTE),
    # Collectée EN 2024 : à l'époque, la date était devant elle. Ce n'est pas un défaut,
    # c'est une vieille fiche — et c'est le piège qu'une comparaison à AUJOURD'HUI (au
    # lieu de la COLLECTE) ferait tomber en masse.
    (105, "Ancienne fiche légitime", "Le 20 novembre 2024.",
     "2024-11-20", "2024-11-20", "parsed", "pending", 0, "2024-10-01 08:00:00"),
]
for eid, titre, desc, deb, fin, src, statut, rec, collecte in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, source_name, "
        " date_event_start, date_event_end, date_source, statut, recurring, scrape_date) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (eid, titre, desc, f"https://exemple.fr/{eid}", "Source officielle",
         deb, fin, src, statut, rec, collecte))
conn.commit()
conn.close()

audit_annee_date.DB_PATH = db


def _signalees(argv=None):
    """Les identifiants que l'audit affiche, relus dans sa propre sortie."""
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        audit_annee_date.main(argv or [])
    sortie = buf.getvalue()
    return {int(m) for m in __import__("re").findall(r"^  \[\s*(\d+)\]", sortie,
                                                     __import__("re").M)}, sortie


print("──── 1. l'audit voit les trois fiches, et elles seules ────")
vues, sortie = _signalees()
_check("4434 signalée (15 août 2024, collectée en 2026)", 4434 in vues, sorted(vues))
_check("4691 signalée (octobre 2024)", 4691 in vues, sorted(vues))
_check("4440 signalée (juillet 2025)", 4440 in vues, sorted(vues))
_check("55 jours de retard : PAS signalée — c'est la grâce de dates._year()",
       100 not in vues, sorted(vues))
_check("exposition en cours : PAS signalée, c'est la FIN qui décide (règle 5)",
       101 not in vues, sorted(vues))
_check("événement à venir : pas signalé", 102 not in vues, sorted(vues))
_check("fiche récurrente : hors sujet, pas signalée", 103 not in vues, sorted(vues))
_check("fiche déjà écartée : pas signalée", 104 not in vues, sorted(vues))
_check("fiche COLLECTÉE en 2024 pour une date de 2024 : pas signalée — la comparaison "
       "se fait à la collecte, pas à aujourd'hui", 105 not in vues, sorted(vues))
_check("exactement trois fiches", vues == {4434, 4691, 4440}, sorted(vues))

print("\n──── 2. la sortie porte de quoi trancher ────")
_check("le périmètre est écrit (nombre de fiches examinées)",
       "examinées" in sortie or "examinée" in sortie)
_check("la phrase d'où vient l'année est montrée (garde-fou de l'erreur 14)",
       "15 agosto 2024" in sortie, sortie[:400])
_check("quand l'année n'est PAS dans le texte, l'audit le DIT au lieu de se taire",
       "n'apparaît pas dans le texte collecté" in sortie)
_check("l'hypothèse de report est proposée, pas appliquée",
       "à VÉRIFIER" in sortie and "2026-08-15" in sortie)
_check("le mot « signalement » borne la portée du document",
       "SIGNALEMENT" in sortie)

print("\n──── 3. un zéro dit d'où il vient ────")
vide, sortie_vide = _signalees(["--jours", "5000"])
_check("aucune suspecte avec un seuil absurde", vide == set(), sorted(vide))
_check("et le zéro annonce quand même combien de fiches ont été examinées",
       "examinées" in sortie_vide, sortie_vide[:300])

# ── Deuxième moitié : la porte de correction ────────────────────────────────────────
completer_verifie.DB_PATH = db


def _lire(eid, col):
    c = sqlite3.connect(db)
    v = c.execute(f"SELECT {col} FROM events_raw WHERE id=?", (eid,)).fetchone()[0]
    c.close()
    return v


def _depuis(charge):
    p = tmp / "correction.json"
    p.write_text(json.dumps(charge), encoding="utf-8")
    completer_verifie._VALEURS.clear()
    completer_verifie._REMPLACEMENTS.clear()
    return str(p)


print("\n──── 4. corriger une année fausse, l'ancienne valeur déclarée ────")
fichier = _depuis({"4434": {"champs": {"date_event_start": "2026-08-15",
                                       "date_event_end": "2026-08-15"},
                            "remplace": {"date_event_start": "2024-08-15",
                                         "date_event_end": "2024-08-15"},
                            "source": "comune.bard.ao.it — la fête a lieu le 15 août 2026"}})
completer_verifie.main(["--depuis", fichier])
_check("le DRY-RUN n'écrit rien (règle 4)", _lire(4434, "date_event_start") == "2024-08-15",
       _lire(4434, "date_event_start"))

fichier = _depuis({"4434": {"champs": {"date_event_start": "2026-08-15",
                                       "date_event_end": "2026-08-15"},
                            "remplace": {"date_event_start": "2024-08-15",
                                         "date_event_end": "2024-08-15"},
                            "source": "comune.bard.ao.it — la fête a lieu le 15 août 2026"}})
completer_verifie.main(["--depuis", fichier, "--apply"])
_check("l'année est corrigée", _lire(4434, "date_event_start") == "2026-08-15",
       _lire(4434, "date_event_start"))
_check("la fin aussi", _lire(4434, "date_event_end") == "2026-08-15")

print("\n──── 5. le refus quand la base a changé entre-temps ────")
# Franck corrige à la main pendant que l'agent prépare sa proposition : c'est SA valeur
# qui gagne, parce qu'il a agi après.
c = sqlite3.connect(db)
c.execute("UPDATE events_raw SET date_event_start='2026-08-16' WHERE id=4691")
c.commit()
c.close()
fichier = _depuis({"4691": {"champs": {"date_event_start": "2026-10-03"},
                            "remplace": {"date_event_start": "2024-10-03"},
                            "source": "une page lue par l'agent"}})
completer_verifie.main(["--depuis", fichier, "--apply"])
_check("la correction est REFUSÉE : la base ne porte plus la valeur déclarée",
       _lire(4691, "date_event_start") == "2026-08-16",
       _lire(4691, "date_event_start"))

print("\n──── 6. sans clause « remplace », rien n'est écrasé (comportement d'origine) ────")
fichier = _depuis({"4440": {"champs": {"date_event_start": "2026-07-20"},
                            "source": "une page lue par l'agent"}})
completer_verifie.main(["--depuis", fichier, "--apply"])
_check("un champ rempli reste intact sans déclaration explicite",
       _lire(4440, "date_event_start") == "2025-07-20", _lire(4440, "date_event_start"))

print("\n──── 7. une clause « remplace » qui ne porte sur rien est refusée en bloc ────")
fichier = _depuis({"4440": {"champs": {"date_event_start": "2026-07-20"},
                            "remplace": {"lieu": "Théâtre de Verdure"},
                            "source": "une page lue par l'agent"}})
completer_verifie.main(["--depuis", fichier, "--apply"])
_check("l'entrée entière est ignorée, pas appliquée à moitié",
       _lire(4440, "date_event_start") == "2025-07-20", _lire(4440, "date_event_start"))

print("\n──── 8. un trou se comble toujours sans déclaration ────")
fichier = _depuis({"102": {"champs": {"lieu": "Bourg de Saint-Ours"},
                           "source": "regione.vda.it"}})
completer_verifie.main(["--depuis", fichier, "--apply"])
_check("le champ vide est rempli comme avant", _lire(102, "lieu") == "Bourg de Saint-Ours",
       _lire(102, "lieu"))

print(f"\n{'TOUT PASSE' if not echecs else str(echecs) + ' ÉCHEC(S)'}")
sys.exit(1 if echecs else 0)
