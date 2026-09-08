#!/usr/bin/env python3
"""Fixture : le rouvreur du portillon « description incohérente ».

⚠️ BASE JETABLE — jamais data/events.db. AUCUN RÉSEAU : `recuperer_description` est
remplacée par une table id → texte.

D'OÙ ÇA VIENT. `translate_events` écarte une fiche dont la description « parle
manifestement d'autre chose », et son commentaire renvoie vers
`repair_polluted_descriptions` comme rouvreur. Or ce script sélectionnait sur
`motif_pollution` — « description SANS SUBSTANCE ». Une description longue, riche, mais
qui raconte un autre événement passait donc au travers : le rouvreur documenté ne
répondait pas à la question posée par le portillon. Résultat mesuré en production :
[4420] [3739] [4576] écartées à l'identique tous les jours du 2026-08-05 au 2026-08-13.
Neuf jours, zéro reprise. Règle 3.

CE QUE LA FIXTURE SURVEILLE :

  1. l'ancien chemin marche toujours — une description polluée reste réparée par la
     règle de longueur. Un correctif qui casse ce qu'il complète n'est pas un correctif ;
  2. LE CAS QUI DOIT PASSER, choisi au plus près de la frontière : une fiche incohérente
     dont la vraie page donne une description JUSTE mais PLUS COURTE. Sous l'ancienne
     règle (« strictement plus long »), elle était refusée — c'est-à-dire que le rouvreur
     aurait pu voir la fiche et la laisser coincée quand même ;
  3. le refus qui doit tenir : si la page re-téléchargée est elle AUSSI incohérente, on
     ne touche à rien. On n'a pas trouvé mieux, on a trouvé autre chose ;
  4. les vrais culs-de-sac (page non re-téléchargeable) sont NOMMÉS avec le geste, pas
     comptés en silence avec les items radar — sinon on recrée le silence qu'on répare,
     en croyant l'avoir refermé ;
  5. une fiche saine n'est jamais candidate.

Lancer : .venv/bin/python -m tests.test_repair_incoherentes
"""
import io
import contextlib
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
import scripts.repair_polluted_descriptions as rp  # noqa: E402
from utils.coherence import incoherence_description, MIN_TEXTE_VISIBLE  # noqa: E402

rp.DB_PATH = tmp

# Un texte long ET substantiel qui parle d'ANNECY, posé sur une fiche de Chambéry :
# c'est la signature de WP#6798, où la description d'un autre événement a contaminé une
# fiche par une fusion à tort. Il dépasse MIN_TEXTE_VISIBLE, donc `motif_pollution` ne
# voit rien : il a de la substance, elle est simplement étrangère à la fiche.
DESC_ETRANGERE = ("La Fête du lac d'Annecy revient cette année encore sur les rives du "
                  "lac, avec un spectacle pyrotechnique de grande ampleur tiré depuis "
                  "des barges installées au large. Le public est attendu nombreux sur "
                  "les quais et dans les jardins de l'Europe, où des gradins sont montés "
                  "pour l'occasion. La billetterie ouvre au printemps et les places "
                  "numérotées partent traditionnellement en quelques jours. " * 2)
assert len(DESC_ETRANGERE) > MIN_TEXTE_VISIBLE

# La VRAIE description, juste, mais PLUS COURTE que l'étrangère : c'est tout l'enjeu.
DESC_JUSTE_COURTE = ("Le Malamute reçoit le théâtre de Chambéry pour une soirée de "
                     "lectures publiques dans la salle voûtée.")

FICHES = [
    # id, titre, lieu, ville, description, url_source, source_type
    (1, "Polluée par un blob Google News", "Salle X", "Chambéry",
     '<a href="https://news.google.com/rss/articles/CBMi' + "A" * 400 + '">lien</a>',
     "https://exemple.fr/1", "site"),
    (2, "Soirée lectures", "Le Malamute", "Chambéry",
     DESC_ETRANGERE, "https://exemple.fr/2", "site"),
    (3, "Soirée lectures bis", "Le Malamute", "Chambéry",
     DESC_ETRANGERE, "https://exemple.fr/3", "site"),
    (4, "Venue d'un mail, sans page", "Le Malamute", "Chambéry",
     DESC_ETRANGERE, "gmail:abc123", "site"),
    (5, "Fiche parfaitement saine", "Le Malamute", "Chambéry",
     "Le Malamute accueille à Chambéry une soirée de lectures publiques. " * 6,
     "https://exemple.fr/5", "site"),
]

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, titre, lieu, ville, desc, url, stype in FICHES:
    conn.execute("INSERT INTO events_raw (id, title, lieu, ville, description, url_source, "
                 "source_type, duplicate_of) VALUES (?,?,?,?,?,?,?, NULL)",
                 (eid, titre, lieu, ville, desc, url, stype))
conn.commit()
conn.close()

# Ce que « la vraie page » renvoie, par identifiant d'URL. Aucun réseau.
PAGES = {
    "https://exemple.fr/1": "Une vraie description de la soirée au Malamute à Chambéry, "
                            "assez fournie pour battre le blob en texte visible. " * 4,
    "https://exemple.fr/2": DESC_JUSTE_COURTE,      # juste, mais PLUS COURTE
    "https://exemple.fr/3": DESC_ETRANGERE,          # la page parle encore d'ailleurs
    "https://exemple.fr/5": "peu importe, elle ne doit pas être candidate",
}
rp.recuperer_description = lambda url, timeout=8: (PAGES.get(url, ""), "fixture")

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── 0. la matière de la fixture est bien ce qu'on croit ────")
_ligne2 = dict(zip(("id", "title", "lieu", "ville", "description"), FICHES[1][:5]))
_check("la description étrangère EST jugée incohérente par le portillon",
       incoherence_description(_ligne2) is not None)
_check("   et elle n'est PAS vue comme « sans substance » — c'est tout le trou",
       not rp.motif_pollution(DESC_ETRANGERE))
_check("la vraie description, elle, est cohérente",
       incoherence_description({**_ligne2, "description": DESC_JUSTE_COURTE}) is None)
_check("   et elle est PLUS COURTE que l'étrangère — le cas frontière",
       len(DESC_JUSTE_COURTE) < len(DESC_ETRANGERE))

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = rp.main(["--apply", "--delay", "0"])
sortie = buf.getvalue()
_check("rc=0", rc == 0, sortie[-400:])

conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
apres = {r["id"]: r["description"] for r in conn.execute(
    "SELECT id, description FROM events_raw")}
conn.close()

print("\n──── 1. l'ancien chemin marche toujours ────")
_check("la fiche polluée (1) est réparée par la règle de longueur",
       "news.google.com" not in (apres[1] or "") and len(apres[1] or "") > 100,
       (apres[1] or "")[:80])

print("\n──── 2. LE CAS QUI DOIT PASSER : juste mais plus court ────")
_check("la fiche 2 est réparée, alors que la nouvelle description est PLUS COURTE",
       (apres[2] or "").startswith("Le Malamute reçoit"), (apres[2] or "")[:80])
_check("   (sous l'ancienne règle « strictement plus long », elle serait restée coincée)",
       len(DESC_JUSTE_COURTE) < len(DESC_ETRANGERE))

print("\n──── 3. le refus qui doit tenir ────")
_check("la fiche 3 n'est PAS touchée — la page parle encore d'autre chose",
       apres[3] == DESC_ETRANGERE, (apres[3] or "")[:60])

print("\n──── 4. le vrai cul-de-sac est NOMMÉ, pas compté en silence ────")
_check("la fiche 4 (gmail:, non re-téléchargeable) apparaît comme SANS RECOURS",
       "SANS RECOURS" in sortie and "[4]" in sortie, sortie[:1200])
_check("   et le geste est écrit à côté", "écarter la\n     fiche" in sortie or
       "écarter la fiche" in sortie.replace("\n     ", " "), sortie[:1500])
_check("   elle n'est PAS confondue avec les items radar, qui eux sont normaux",
       "écartée(s) volontairement" in sortie)
_check("   et sa description n'a pas bougé", apres[4] == DESC_ETRANGERE)

print("\n──── 5. une fiche saine n'est jamais candidate ────")
_check("la fiche 5 est intacte", apres[5] == FICHES[4][4], (apres[5] or "")[:60])

print("\n──── 6. le compte distingue les deux causes ────")
_check("la sortie sépare « sans substance » et « parlent d'autre chose »",
       "SANS SUBSTANCE" in sortie and "PARLENT D'AUTRE CHOSE" in sortie, sortie[:900])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
