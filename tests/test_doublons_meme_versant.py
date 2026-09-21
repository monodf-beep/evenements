#!/usr/bin/env python3
"""Fixture : une paire de traduction servie d'UN SEUL côté du site (2026-09-21).

⚠️ BASE JETABLE (init_db sur un fichier temporaire). Aucun réseau, aucun appel LLM.

D'OÙ ÇA VIENT. Le 21/09, Franck signale des doublons sur le hub Vallée d'Aoste. Le
correctif du matin en fait remonter trois — mais huit paires visibles sur le SITE
restaient absentes du rapport. Relevé sur la base de production, pour les huit (Orlando,
James Carter, les violoncelles de l'Opéra de Nice, We Want Jazz, Mostre : Diálogos,
Gaza/Merz, Sotto i portici, le Castello di Ivrea) : `paire_de_traduction = True`.

Elles sont donc écartées À RAISON — ce sont bien des paires liées. Mais **les deux pages
sont servies du côté français**, donc le lecteur voit deux cartes françaises. Ce ne sont
pas des doublons de CONTENU : ce sont des traductions publiées du mauvais versant,
exactement l'incident du 17/09 (« Open Factories 2026: le fabbriche di Torino aprono le
porte » sur la page d'accueil française). Mesuré le 21/09 : **32 traductions** dans ce
cas, toutes listées par `scripts/audit_langue_polylang` — qui n'est dans aucun cron.

⚠️ CE QUE LA PREMIÈRE VERSION DE CE CORRECTIF A CASSÉ, et pourquoi cette fixture existe
sous cette forme. J'ai d'abord RÉ-ADMIS ces paires comme groupes suspects. Sur la base de
production, le rapport est passé de 5 groupes à 29, et surtout le groupe EVO — qui mêle
un VRAI doublon de contenu et une traduction égarée — est sorti de la commande de
corbeille avec le conseil « NE PAS corbeiller », faux pour lui. Une file qui reçoit ce
qui a déjà sa file. On COMPTE et on RENVOIE, on ne recopie pas.

CE QUE LA FIXTURE VÉRIFIE :

  1. LE TÉMOIN ROUGE : sur la paire réelle Orlando, `paire_de_traduction` rend True et les
     deux permaliens sont du côté « fr ». Sans ce témoin, on ne saurait pas ce qui est
     réparé.
  2. `cote_partage` nomme ce versant partagé.
  3. La paire reste ÉCARTÉE (son geste n'est pas la corbeille), mais le rapport la COMPTE
     et nomme le relevé qui la traite.
  4. ⚠️ LE CAS FRONTIÈRE QUI DOIT PASSER, celui que j'avais cassé : un groupe qui mêle un
     vrai doublon de contenu ET une traduction du mauvais versant (la forme d'EVO) reste
     un suspect, garde sa recommandation, et ses ids restent dans la commande
     `trash_by_ids`.
  5. Les autres frontières : une VRAIE paire FR/IT n'est pas comptée ; une paire dont un
     permalien est MUET (`?p=…`) n'est pas comptée — on ne crie pas sur une donnée
     absente (règle 6).

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
          lieu="Opéra Nice Côte d'Azur", debut=D, fin=F, article=""):
    return {"id": i, "title": titre, "territoire": "comte-de-nice", "ville": ville,
            "lieu": lieu, "date_event_start": debut, "date_event_end": fin,
            "translation_of": translation_of, "wp_post_id_as": wp,
            "wp_permalink_as": permalien, "url_source": f"https://src.example/{i}",
            "enrich_data": article}


# La paire réelle : deux pages FRANÇAISES, liées par translation_of (WP#745 / WP#2340).
ORL_A = fiche(528, "Orlando", 745, f"{BASE}/evenement/orlando-de-haendel-nouvelle-production/")
ORL_B = fiche(3547, "Orlando", 2340, f"{BASE}/evenement/orlando-de-haendel-a-lopera-de-nice/",
              translation_of=528)
# Une VRAIE paire FR/IT : l'italienne est servie sous /it/.
VRAI_FR = fiche(600, "Carmen à l'Opéra", 810, f"{BASE}/evenement/carmen-a-lopera/",
                lieu="Opéra de Nice")
VRAI_IT = fiche(601, "Carmen all'Opéra", 811, f"{BASE}/it/evenement/carmen-a-lopera-2/",
                translation_of=600, lieu="Opéra de Nice")
# Un permalien MUET : la forme provisoire, qui ne dit rien du versant.
MUET_A = fiche(700, "Tosca au Théâtre", 900, f"{BASE}/evenement/tosca-au-theatre/",
               lieu="Théâtre de Nice")
MUET_B = fiche(701, "Tosca au Théâtre", 901, f"{BASE}/?post_type=tribe_events&p=901",
               translation_of=700, lieu="Théâtre de Nice")
# LA FORME D'EVO : un vrai doublon de contenu, ET une traduction du mauvais versant
# dedans. Ids et numéros de post réels (WP#6433 / WP#7727 / WP#8954 / WP#9302).
ART = '{"article": {"corps": "%s"}}' % ("texte " * 60)
EVO_GARDE = fiche(3739, "EVO France 2026", 6433, f"{BASE}/evenement/evo-france-2026/",
                  lieu="Palais des Expositions", article=ART)
EVO_GARDE_IT = fiche(4792, "EVO France 2026", 7727, f"{BASE}/it/evenement/evo-france-2026-2/",
                     translation_of=3739, lieu="Palais des Expositions", article=ART)
EVO_DOUBLE = fiche(2466, "EVO 2026", 8954, f"{BASE}/evenement/evo-2026-a-nice/",
                   lieu="Palais des Expositions")
EVO_DOUBLE_IT = fiche(5521, "EVO 2026", 9302, f"{BASE}/evenement/evo-2026-a-nice-2/",
                      translation_of=2466, lieu="Palais des Expositions")

print("──── 1. témoin rouge : la base dit « traduction », le site dit « deux fois fr » ────")
_check("paire_de_traduction(Orlando) = True", dd.paire_de_traduction(ORL_A, ORL_B) is True)
_check("   et les deux permaliens sont du côté « fr »",
       dd._cote(ORL_A["wp_permalink_as"]) == "fr" and dd._cote(ORL_B["wp_permalink_as"]) == "fr")

print("\n──── 2. cote_partage nomme le versant ────")
_check("cote_partage(Orlando) = « fr »", dd.cote_partage([ORL_A, ORL_B]) == "fr",
       dd.cote_partage([ORL_A, ORL_B]))
_check("cote_partage d'une VRAIE paire FR/IT = ''", dd.cote_partage([VRAI_FR, VRAI_IT]) == "")
_check("cote_partage quand un permalien est MUET = ''", dd.cote_partage([MUET_A, MUET_B]) == "")
_check("cote_partage de deux fiches SANS lien de traduction = ''",
       dd.cote_partage([ORL_A, VRAI_FR]) == "")

print("\n──── 3-5. le rapport ────")
conn = sqlite3.connect(tmp)
init_db(conn)
for f in (ORL_A, ORL_B, VRAI_FR, VRAI_IT, MUET_A, MUET_B,
          EVO_GARDE, EVO_GARDE_IT, EVO_DOUBLE, EVO_DOUBLE_IT):
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, territoire, ville, lieu, statut, "
        "wp_post_id_as, wp_permalink_as, translation_of, date_event_start, "
        "date_event_end, enrich_data, duplicate_of) "
        "VALUES (?,?,?,?,?,?,'published_sub',?,?,?,?,?,?,NULL)",
        (f["id"], f["title"], f["url_source"], f["territoire"], f["ville"], f["lieu"],
         f["wp_post_id_as"], f["wp_permalink_as"], f["translation_of"],
         f["date_event_start"], f["date_event_end"], f["enrich_data"]))
conn.commit()
conn.close()

vd._etat = lambda wp_url, post_id: "public"       # AUCUN RÉSEAU
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = vd.main(["--en-ligne"])
out = buf.getvalue()
commande = [l for l in out.splitlines() if "trash_by_ids" in l]

_check("rc=0 (lecture seule)", rc == 0)
_check("la paire Orlando n'est PAS remise dans la file des doublons",
       "[  528]" not in out and "[ 3547]" not in out, out[:2200])
# Deux, et pas une : la traduction d'Orlando (3547) ET celle d'EVO 2026 (5521) sont
# toutes deux servies du côté français. Le compteur compte des FICHES, pas des groupes —
# c'est ce que dit son libellé, et c'est ce qui permet de le rapprocher des 32 mesurées
# par `audit_langue_polylang` sur la base de production.
_check("mais le compteur « TRADUCTIONS DU MÊME CÔTÉ » vaut 2 — elles ne sont plus muettes",
       "TRADUCTIONS DU MÊME CÔTÉ : 2" in out, out[:2200])
_check("   et le rapport nomme le relevé qui la traite",
       "audit_langue_polylang" in out, out[:2200])
_check("   et dit que ce ne sont pas des doublons de contenu",
       "pas des doublons de CONTENU" in out, out[:2200])

print("\n   ⚠️ le cas frontière que la première version avait cassé :")
_check("(EVO) le groupe mixte reste un SUSPECT",
       "[ 2466]" in out and "[ 3739]" in out, out)
_check("    il garde sa recommandation (← GARDER / ← retirer)",
       "← GARDER" in out and "← retirer" in out, out)
_check("    et ses ids restent dans la commande trash_by_ids",
       any("2466" in l and "5521" in l for l in commande), commande)
_check("    tandis qu'Orlando n'y entre pas",
       not any("528" in l.replace("5521", "") for l in commande), commande)

_check("la VRAIE paire FR/IT n'est ni comptée ni listée",
       "[  600]" not in out and "[  601]" not in out, out)
_check("la paire au permalien muet non plus",
       "[  700]" not in out and "[  701]" not in out, out)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
