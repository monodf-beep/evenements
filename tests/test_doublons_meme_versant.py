#!/usr/bin/env python3
"""Fixture : « liées par translation_of » ne veut pas dire « dans deux langues » (2026-09-21).

⚠️ BASE JETABLE (init_db sur un fichier temporaire). Aucun réseau, aucun appel LLM.

D'OÙ ÇA VIENT. Le 21/09, Franck signale des doublons visibles sur le hub. Le correctif du
matin en fait remonter trois de plus — mais huit paires que je voyais sur le SITE restaient
invisibles au rapport. Relevé sur la base de production, pour les huit (Orlando, James
Carter, les violoncelles de l'Opéra de Nice, We Want Jazz, Mostre : Diálogos, Gaza/Merz,
Sotto i portici, le Castello di Ivrea) :

    paire_de_traduction = True

Elles étaient donc écartées comme « paires FR/IT normales » — alors que LES DEUX PAGES
ÉTAIENT EN FRANÇAIS, côte à côte sur le hub. C'est la règle 1 de CLAUDE.md transposée à la
langue : **la base dit « traduction », seul WordPress dit de quel côté la page est rangée.**
Le lien Polylang peut exister alors que la traduction a été publiée du mauvais versant —
l'incident du 17/09 (« Open Factories 2026: le fabbriche di Torino aprono le porte » sur la
page d'accueil française) est exactement ça.

CE QUE LA FIXTURE VÉRIFIE :

  1. LE TÉMOIN ROUGE : sur la paire réelle Orlando, `paire_de_traduction` rend True. C'est
     ce True-là qui cachait le doublon ; sans ce témoin on ne saurait pas quoi est réparé.
  2. `paire_de_traduction_credible` rend False quand les deux permaliens sont du même côté,
     et la paire remonte comme suspecte.
  3. ⚠️ LES CAS FRONTIÈRE QUI DOIVENT PASSER :
       a. une VRAIE paire FR/IT (l'une sous /it/) reste écartée, et comptée écartée ;
       b. une paire dont un permalien est MUET (forme provisoire `?p=…`) reste écartée —
          on ne crie pas sur une donnée absente (règle 6) ;
       c. un doublon ordinaire, sans lien de traduction, n'est pas affecté.
  4. LE GESTE EST LE BON : le groupe dit « ne pas corbeiller », nomme le versant partagé,
     propose `audit_langue_polylang` puis `translate_events --retranslate`, et ses ids
     n'entrent PAS dans la commande `trash_by_ids` automatique. Corbeiller une de ces deux
     pages perdrait la version italienne au lieu de la remettre en place.
  5. Le compteur « LIÉES MAIS DU MÊME CÔTÉ » s'affiche avec ce qu'il compte.

Lancer : .venv/bin/python -m tests.test_doublons_meme_versant
"""
import contextlib
import io
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

from scripts.scraper_events import init_db          # noqa: E402
import scripts.dedupe as dd                          # noqa: E402
import scripts.verifier_doublons_publies as vd       # noqa: E402

vd.DB_PATH = tmp
dd.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


AUJ = date.today()
D = (AUJ + timedelta(days=8)).isoformat()
F = (AUJ + timedelta(days=15)).isoformat()
BASE = "https://agendasabauda.eu"


def fiche(i, titre, wp, permalien, translation_of=None, ville="Nice",
          lieu="Opéra Nice Côte d'Azur", debut=D, fin=F):
    return {"id": i, "title": titre, "territoire": "comte-de-nice", "ville": ville,
            "lieu": lieu, "date_event_start": debut, "date_event_end": fin,
            "translation_of": translation_of, "wp_post_id_as": wp,
            "wp_permalink_as": permalien, "url_source": f"https://src.example/{i}"}


# La paire réelle : deux pages FRANÇAISES, liées par translation_of (WP#745 / WP#2340).
ORL_A = fiche(528, "Orlando", 745, f"{BASE}/evenement/orlando-de-haendel-nouvelle-production/")
ORL_B = fiche(3547, "Orlando", 2340, f"{BASE}/evenement/orlando-de-haendel-a-lopera-de-nice/",
              translation_of=528)
# (a) une VRAIE paire FR/IT : l'italienne est servie sous /it/.
VRAI_FR = fiche(600, "Carmen à l'Opéra", 810, f"{BASE}/evenement/carmen-a-lopera/",
                lieu="Opéra de Nice")
VRAI_IT = fiche(601, "Carmen all'Opéra", 811, f"{BASE}/it/evenement/carmen-a-lopera-2/",
                translation_of=600, lieu="Opéra de Nice")
# (b) un permalien MUET : la forme provisoire, qui ne dit rien du versant.
MUET_A = fiche(700, "Tosca au Théâtre", 900, f"{BASE}/evenement/tosca-au-theatre/",
               lieu="Théâtre de Nice")
MUET_B = fiche(701, "Tosca au Théâtre", 901, f"{BASE}/?post_type=tribe_events&p=901",
               translation_of=700, lieu="Théâtre de Nice")

print("──── 1. témoin rouge : c'est ce True-là qui cachait le doublon ────")
_check("paire_de_traduction(Orlando) = True — la base dit « traduction »",
       dd.paire_de_traduction(ORL_A, ORL_B) is True)
_check("   et les deux pages sont pourtant du côté « fr » du site",
       dd._cote(ORL_A["wp_permalink_as"]) == "fr"
       and dd._cote(ORL_B["wp_permalink_as"]) == "fr")

print("\n──── 2. la garde consulte désormais le versant ────")
_check("paire_de_traduction_credible(Orlando) = False",
       dd.paire_de_traduction_credible(ORL_A, ORL_B) is False)
_check("cote_partage nomme le versant partagé", dd.cote_partage([ORL_A, ORL_B]) == "fr",
       dd.cote_partage([ORL_A, ORL_B]))

print("\n──── 3. cas frontière ────")
_check("(a) une VRAIE paire FR/IT reste crédible",
       dd.paire_de_traduction_credible(VRAI_FR, VRAI_IT) is True)
_check("    et cote_partage ne la nomme pas", dd.cote_partage([VRAI_FR, VRAI_IT]) == "")
_check("(b) un permalien MUET : on ne sait pas, donc on écarte encore",
       dd.paire_de_traduction_credible(MUET_A, MUET_B) is True,
       dd._cote(MUET_B["wp_permalink_as"]))
_check("(c) deux fiches SANS lien de traduction ne passent pas par cette garde",
       dd.paire_de_traduction_credible(ORL_A, VRAI_FR) is False
       and dd.cote_partage([ORL_A, VRAI_FR]) == "")

print("\n──── 4-5. le rapport : le bon geste, et le compteur ────")
conn = sqlite3.connect(tmp)
init_db(conn)
for f in (ORL_A, ORL_B, VRAI_FR, VRAI_IT, MUET_A, MUET_B):
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, territoire, ville, lieu, statut, "
        "wp_post_id_as, wp_permalink_as, translation_of, date_event_start, "
        "date_event_end, duplicate_of) VALUES (?,?,?,?,?,?,'published_sub',?,?,?,?,?,NULL)",
        (f["id"], f["title"], f["url_source"], f["territoire"], f["ville"], f["lieu"],
         f["wp_post_id_as"], f["wp_permalink_as"], f["translation_of"],
         f["date_event_start"], f["date_event_end"]))
conn.commit()
conn.close()

vd._etat = lambda wp_url, post_id: "public"       # AUCUN RÉSEAU
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = vd.main(["--en-ligne"])
out = buf.getvalue()

_check("rc=0 (lecture seule)", rc == 0)
_check("la paire Orlando remonte : [  528] et [ 3547] dans la sortie",
       "[  528]" in out and "[ 3547]" in out, out[:2000])
_check("le groupe dit que les deux pages sont du côté « fr »",
       "les DEUX pages sont du côté « fr »" in out, out)
_check("   et qu'il ne faut PAS corbeiller", "NE PAS corbeiller" in out, out)
_check("   et propose audit_langue_polylang", "audit_langue_polylang" in out, out)
_check("   et propose --retranslate", "--retranslate" in out, out)
_check("le compteur « LIÉES MAIS DU MÊME CÔTÉ » vaut 1",
       "LIÉES MAIS DU MÊME CÔTÉ : 1" in out, out[:1800])
_check("la VRAIE paire FR/IT ne remonte pas", "[  600]" not in out and "[  601]" not in out, out)
_check("la paire au permalien muet ne remonte pas",
       "[  700]" not in out and "[  701]" not in out, out)
# Le point le plus important : ces ids ne doivent PAS entrer dans la commande consolidée.
_check("et surtout : aucun de ces ids n'entre dans la commande trash_by_ids",
       not any(f"trash_by_ids" in ligne and ("528" in ligne or "3547" in ligne)
               for ligne in out.splitlines()), out[-1200:])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
