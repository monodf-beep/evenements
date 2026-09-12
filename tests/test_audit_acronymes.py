#!/usr/bin/env python3
"""Fixture : le relevé des sigles distingue une FILE d'une LISTE À LIRE.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau.

D'OÙ ÇA VIENT. Franck, 2026-08-18 : « je ne sais pas s'il y en a d'autres, mettre en place
une règle. » La règle agit sur le dictionnaire ; ce relevé répond au « combien ».

CE QUE LA FIXTURE SURVEILLE :
  1. un sigle CONNU non développé est une file — chaque ligne a un geste au bout ;
  2. ⚠️ une suite de capitales INCONNUE va dans les candidats, PAS dans la file : personne
     ne peut la développer sans vérifier à la source, et certaines n'en sont pas ;
  3. ⚠️ un sigle DÉJÀ développé ne figure nulle part — le cas qui doit passer ;
  4. le périmètre est celui de la règle 5 : une fiche dont l'événement a eu lieu n'est pas
     examinée, développer un sigle pour personne n'a pas de sens ;
  5. et le zéro dit ses deux causes possibles — tout est développé, OU le dictionnaire est
     encore court. Un zéro qui ne dit pas ça se lit « rien à faire » à tort.

Lancer : .venv/bin/python -m tests.test_audit_acronymes
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
import scripts.audit_acronymes as aa            # noqa: E402

aa.DB_PATH = tmp
FUTUR = (date.today() + timedelta(days=20)).isoformat()
PASSE = (date.today() - timedelta(days=40)).isoformat()


def _art(chapo):
    return json.dumps({"article": {"chapo": chapo, "corps": ""}})


# (id, wp, article_title, chapo, début, fin)
FICHES = [
    (1, 7001, "Le TNN en tournée dans la Métropole", "Trois soirées.", FUTUR, FUTUR),
    (2, 7002, "Le Théâtre national de Nice (TNN) ouvre sa saison", "Dix créations.",
     FUTUR, FUTUR),
    (3, 7003, "Le CRR de Chambéry en concert", "Avec l'ADAC.", FUTUR, FUTUR),
    (4, 7004, "Le TNN en juillet", "Passé.", PASSE, PASSE),
]

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, wp, titre, chapo, deb, fin in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, article_title, enrich_data, url_source, "
        "wp_post_id_as, statut, date_event_start, date_event_end, duplicate_of) "
        "VALUES (?,?,?,?,?,?,?,?,?,NULL)",
        (eid, titre, titre, _art(chapo), f"https://a.fr/{eid}", wp, "published_sub",
         deb, fin))
conn.commit(); conn.close()

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    aa.main([])
s = buf.getvalue()
file_bloc = s[s.find("## À DÉVELOPPER"):s.find("## CANDIDATS")]
cand_bloc = s[s.find("## CANDIDATS"):]

print("──── la FILE : des sigles connus, avec un geste au bout ────")
_check("le TNN non développé y est", "**TNN**" in file_bloc and "WP#7001" in file_bloc,
       file_bloc[:400])
_check("   avec l'endroit où il se trouve (titre ou corps)", "(titre)" in file_bloc,
       file_bloc[:400])

print("\n──── ⚠️ ce qui NE doit PAS y être ────")
_check("le TNN DÉJÀ développé n'est pas dans la file (le cas qui doit passer)",
       "WP#7002" not in file_bloc, file_bloc)
_check("⚠️ un sigle inconnu (CRR) n'est PAS dans la file — on ne peut pas le développer",
       "WP#7003" not in file_bloc, file_bloc)
_check("la fiche PASSÉE n'est pas examinée (règle 5)", "WP#7004" not in file_bloc,
       file_bloc)
_check("   et le périmètre est écrit à côté du nombre",
       "encore devant nous    : 3" in s, s[:500])

print("\n──── la LISTE À LIRE : les candidats ────")
_check("CRR et ADAC y sont proposés", "**CRR**" in cand_bloc and "**ADAC**" in cand_bloc,
       cand_bloc[:500])
_check("   avec le nombre de mentions et un exemple",
       "| Mentions | Vu dans |" in cand_bloc, cand_bloc[:300])
_check("un sigle DÉJÀ au dictionnaire n'y est pas reproposé",
       "**TNN**" not in cand_bloc, cand_bloc[:500])
_check("⚠️ et le relevé dit que ce n'est PAS une file de travail",
       "N'EST PAS UNE FILE DE TRAVAIL" in cand_bloc, cand_bloc[:400])
_check("   en disant pourquoi : il faut vérifier à la source",
       "vérifier à la source" in cand_bloc, cand_bloc[:500])

print("\n──── le verdict envoyé sur le téléphone ────")
import utils.slack as slack_mod  # noqa: E402
envoyes: list[str] = []
slack_mod.notify = lambda text, blocks=None, urgent=False: envoyes.append(text) or True
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    aa.main(["--slack"])
msg = envoyes[0] if envoyes else ""
_check("un seul message", len(envoyes) == 1, envoyes)
_check("il donne les deux comptes séparément",
       "mention(s) d'un sigle CONNU" in msg and "pas encore au dictionnaire" in msg, msg)
_check("   et rappelle que les candidates se LISENT", "se LISENT" in msg, msg)
_check("il tient sur un écran de téléphone", len(msg.splitlines()) <= 6,
       f"{len(msg.splitlines())} lignes")

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
