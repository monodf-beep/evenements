#!/usr/bin/env python3
"""Fixture : le site officiel d'un LIEU déjà résolu se réutilise, il ne se re-cherche pas.

Franck, 2026-09-08, après avoir vu la facture : « au lieu de couper il faut trouver la
solution ». Appliqué d'abord aux images (la page officielle se lit au lieu de se chercher),
puis ici. `enrich.resolve_official_site` coûte 0,22 $ l'appel — troisième poste de dépense
du pipeline — et repartait de zéro à chaque fiche. Mesuré le même jour sur les 272 fiches
publiées : 159 lieux distincts, 57 lieux portent plusieurs fiches, **98 fiches rejouent un
lieu déjà connu**, dont 26 pour le seul Forte di Bard.

`site_officiel_du_lieu` rend l'URL déjà mémorisée pour une AUTRE fiche du même lieu. Ce
n'est pas un verrou : l'appelant vérifie que la page parle bien de l'événement et retombe
sur la recherche payante sinon (testé dans les cas ci-dessous côté sélection seulement —
la vérification de pertinence vit dans fetch_official_material).

LES CAS QUI DOIVENT RENDRE VIDE comptent autant que les autres : un lieu qui porte DEUX
domaines (le Teatro Regio, et le Torino Film Festival qui s'y tient) ne peut pas décider.

Base SQLite jetable, aucun réseau, aucun appel API.
Lancer : .venv/bin/python -m tests.test_site_officiel_lieu
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.enrich import site_officiel_du_lieu  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE events_raw (id INTEGER PRIMARY KEY, lieu TEXT, ville TEXT, "
             "url_officiel TEXT, title TEXT)")
conn.executemany(
    "INSERT INTO events_raw (id, lieu, ville, url_officiel, title) VALUES (?,?,?,?,?)", [
        # Le cas massif : 26 fiches au Forte di Bard dans la vraie base.
        (1, "Forte di Bard", "Bard", "https://www.fortedibard.it/", "Niccolò Fabi"),
        (2, "Forte di Bard", "Bard", "https://www.fortedibard.it/", "Paolo Crepet"),
        (3, "Forte di Bard", "Bard", "https://fortedibard.it/", "Aldo Cazzullo"),
        # Deux domaines pour un même lieu : le théâtre, et le festival qui s'y tient.
        (4, "Teatro Regio", "Torino", "https://www.teatroregio.torino.it/", "Traviata"),
        (5, "Teatro Regio", "Torino", "https://www.torinofilmfest.org/", "44e TFF"),
        # Même nom de lieu, ville différente : ne doit PAS se mélanger.
        (6, "Théâtre municipal", "Annecy", "https://bonlieu-annecy.com/", "Danse"),
        (7, "Théâtre municipal", "Chambéry", "", "Concert"),
        # Un lieu connu, mais sans site officiel mémorisé.
        (8, "Salle des fêtes", "Bard", "", "Bal"),
    ])
conn.commit()


def ev(id_, lieu, ville):
    return {"id": id_, "lieu": lieu, "ville": ville}


print("──── le cas qui paie : un lieu déjà résolu ────")
_check("nouvelle fiche au Forte di Bard → site hérité, aucune recherche",
       site_officiel_du_lieu(conn, ev(99, "Forte di Bard", "Bard")) != "",
       site_officiel_du_lieu(conn, ev(99, "Forte di Bard", "Bard")))
_check("le domaine hérité est bien celui du lieu",
       "fortedibard.it" in site_officiel_du_lieu(conn, ev(99, "Forte di Bard", "Bard")))
_check("www et non-www comptent pour UN seul domaine (3 fiches, 2 écritures)",
       site_officiel_du_lieu(conn, ev(99, "Forte di Bard", "Bard")) != "")
_check("casse et espaces indifférents",
       site_officiel_du_lieu(conn, ev(99, "  forte di BARD ", "bard")) != "")

print("\n──── ce qui doit rendre VIDE (et retomber sur la résolution normale) ────")
_check("deux domaines pour un même lieu → on ne tranche pas",
       site_officiel_du_lieu(conn, ev(99, "Teatro Regio", "Torino")) == "",
       site_officiel_du_lieu(conn, ev(99, "Teatro Regio", "Torino")))
_check("même nom de lieu, autre ville → aucun héritage",
       site_officiel_du_lieu(conn, ev(99, "Théâtre municipal", "Chambéry")) == "")
_check("lieu connu mais sans site mémorisé → vide",
       site_officiel_du_lieu(conn, ev(99, "Salle des fêtes", "Bard")) == "")
_check("lieu inconnu → vide", site_officiel_du_lieu(conn, ev(99, "Cour du Château", "Aoste")) == "")
_check("lieu vide → vide", site_officiel_du_lieu(conn, ev(99, "", "Bard")) == "")
_check("lieu trop court pour identifier quoi que ce soit → vide",
       site_officiel_du_lieu(conn, ev(99, "Bar", "Bard")) == "")
_check("la fiche ne s'hérite pas d'elle-même",
       site_officiel_du_lieu(conn, ev(6, "Théâtre municipal", "Annecy")) == "",
       site_officiel_du_lieu(conn, ev(6, "Théâtre municipal", "Annecy")))

print("\n──── robustesse : ne jamais bloquer l'enrichissement ────")
vide = sqlite3.connect(":memory:")
_check("table absente → vide, aucune exception", site_officiel_du_lieu(vide, ev(1, "X Y Z", "A")) == "")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
