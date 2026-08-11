#!/usr/bin/env python3
"""Fixture : le contradicteur de LIEUX. Base jetable — jamais data/events.db.

CE QU'ELLE SURVEILLE, DANS CET ORDRE — et c'est l'inverse de l'ordre qu'on croit. Le
risque n'est pas de rater une ville fausse : c'est d'en inventer. Le contrôle ③
(« le nom du lieu nomme une autre commune ») est structurellement capable de crier sur des
fiches justes — le Café de Turin est à Nice depuis 1908 — donc la fixture contient
d'abord des cas qui DOIVENT PASSER, choisis près de la frontière.

C'est l'exigence de la règle 3, écrite après le portillon du 06/08 : « la fixture doit
contenir un cas qui doit PASSER, choisi près de la frontière. Celle du 06/08 n'avait que
des cas qui confirmaient le design : elle est passée au vert sur un portillon faux. »

  1. l'ABSENCE ne signale jamais — ville vide, lieu inconnu, commune hors listes ;
  2. les faux amis passent — « Aoste » vs « Aosta », « Bardonecchia » vs « Bard »,
     un nom ambigu (« Théâtre des Nus ») ;
  3. le PASSÉ est hors périmètre (règle 5) ;
  4. et seulement ensuite : les trois contradictions sont bien vues.

Lancer : .venv/bin/python -m tests.test_verifier_lieux
"""
import contextlib
import io
import json
import re
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import verifier_lieux  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402
from utils import lieux  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ── 1. Le cœur, sans base ────────────────────────────────────────────────────────────
print("──── 1. ce qui doit PASSER — d'abord, parce que c'est là qu'on se trompe ────")
_check("le lieu et la ville s'accordent → rien",
       lieux.confronte("Forte di Bard", "Bard")[0] == "")
_check("« Aoste » et « Aosta » sont la MÊME ville, pas une contradiction",
       lieux.canon("Aoste") == lieux.canon("Aosta"))
_check("ville vide → silence (l'absence ne contredit rien)",
       lieux.confronte("Forte di Bard", "")[0] == "")
_check("lieu vide → silence",
       lieux.confronte("", "Aoste")[0] == "")
_check("un lieu inconnu du registre et sans toponyme → silence",
       lieux.confronte("Salle des fêtes", "Chambéry")[0] == "")
# LA FRONTIÈRE : « Bardonecchia » contient les lettres de « Bard ». Une recherche par
# sous-chaîne signalerait toutes les fiches de Bardonecchia. La recherche est par MOTS.
_check("« Bardonecchia » ne contient PAS la commune de Bard",
       lieux.toponyme_du_lieu("Chiesa di Bardonecchia") != "Bard")
# LA FRONTIÈRE, DEUXIÈME : « Nus » est une vraie commune valdôtaine ET un mot courant.
_check("un nom ambigu (« Nus ») ne déclenche pas sur un nom de lieu",
       lieux.confronte("Théâtre des Nus", "Chambéry")[0] == "")
_check("le toponyme se tait si la ville n'est PAS une commune connue "
       "(on compare deux faits, pas un fait à une intuition)",
       lieux.confronte("Castello di Rivoli", "Ljubljana")[0] == "")
_check("un lieu dont le nom porte SA PROPRE ville → rien",
       lieux.confronte("Théâtre de Chambéry", "Chambéry")[0] == "")

print("\n──── 2. ce qui doit ÊTRE VU ────")
v, phrase, attendue = lieux.confronte("Forte di Bard", "Aosta")
_check("① le registre (docs/savoir) contredit la fiche", v == "registre", f"→ {v}")
_check("   et il dit quelle ville il attend", attendue == "Bard", f"→ {attendue!r}")
_check("   la phrase cite sa PROVENANCE — sinon on arbitre à l'aveugle",
       "note de savoir" in phrase, f"→ {phrase!r}")
_check("① vaut aussi pour les autres graphies déclarées dans la note",
       lieux.confronte("Fort de Bard", "Aoste")[0] == "registre")
_check("③ le nom du lieu nomme une autre commune connue",
       lieux.confronte("Castello di Rivoli", "Torino")[0] == "toponyme")
_check("   le registre PRIME sur le toponyme (il fait foi, le nom peut être un hommage)",
       lieux.confronte("Forte di Bard", "Aosta")[0] == "registre")

# ── 3. Sur base jetable ──────────────────────────────────────────────────────────────
print("\n──── 3. sur base — périmètre, désaccord interne, --apply ────")
tmp = Path(tempfile.mkdtemp(prefix="fixture-veriflieux-"))
db = tmp / "fixture.db"
conn = sqlite3.connect(db)
init_db(conn)

AVENIR = (date.today() + timedelta(days=40)).isoformat()
PASSE = (date.today() - timedelta(days=40)).isoformat()

CAS = [
    # id, titre, lieu, ville, début, fin, wp, statut
    (1, "Concert à la cour d'armes", "Forte di Bard", "Aosta", AVENIR, AVENIR, 8001,
     "pending"),                                                        # ① registre
    (2, "Exposition permanente", "Forte di Bard", "Bard", AVENIR, AVENIR, None,
     "pending"),                                                        # rien : d'accord
    # ② DÉSACCORD INTERNE : le même lieu, deux villes, chez nous. Aucune liste n'aide —
    # ce sont nos deux affirmations qui s'excluent.
    (3, "Bal du 15 août", "Salle polyvalente du Bourg", "Chambéry", AVENIR, AVENIR, None,
     "pending"),
    (4, "Loto de l'école", "Salle polyvalente du Bourg", "Annecy", AVENIR, AVENIR, None,
     "pending"),
    # PAS un désaccord : « Aoste » et « Aosta » sont la même ville (alias).
    (5, "Marché médiéval", "Place de la Cathédrale", "Aoste", AVENIR, AVENIR, None,
     "pending"),
    (6, "Foire de printemps", "Place de la Cathédrale", "Aosta", AVENIR, AVENIR, None,
     "pending"),
    (7, "Visite guidée", "Castello di Rivoli", "Torino", AVENIR, AVENIR, None,
     "pending"),                                                        # ③ toponyme
    (8, "Sortie au lac", "Base de loisirs", "", AVENIR, AVENIR, None, "pending"),  # muette
    # RÈGLE 5 : passé et rejeté sortent du périmètre, même contredits.
    (9, "Concert de mai", "Forte di Bard", "Aosta", PASSE, PASSE, None, "pending"),
    (10, "Déjà écartée", "Forte di Bard", "Aosta", AVENIR, AVENIR, None, "rejected"),
    # SANS DATE : ce n'est PAS du passé, c'est une donnée manquante — elle reste.
    (11, "Date à confirmer", "Forte di Bard", "Aosta", "", "", None, "pending"),
]
for eid, titre, lieu, ville, deb, fin, wp, statut in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, lieu, ville, url_source, source_name, "
        " date_event_start, date_event_end, statut, wp_post_id_as, venue_source) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (eid, titre, lieu, ville, f"https://exemple.fr/{eid}", "Source officielle",
         deb, fin, statut, wp, "page"))
conn.commit()
conn.close()
verifier_lieux.DB_PATH = db


def _sortie(argv=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        verifier_lieux.main(argv or [])
    s = buf.getvalue()
    return {int(m) for m in re.findall(r"^  \[\s*(\d+)\]", s, re.M)}, s


vus, sortie = _sortie()
_check("① la fiche contredite par le registre est signalée", 1 in vus, sortie[-1200:])
_check("la fiche d'accord ne l'est pas", 2 not in vus)
_check("③ le toponyme est signalé", 7 in vus)
_check("la muette n'est pas une tâche", 8 not in vus)
_check("le PASSÉ est hors périmètre (règle 5)", 9 not in vus)
_check("la rejetée aussi", 10 not in vus)
_check("SANS DATE n'est pas du passé : elle reste vue", 11 in vus)
_check("② le désaccord interne est nommé", "Salle polyvalente du Bourg" in sortie)
_check("   et il compte les fiches de chaque côté", re.search(
    r"Chamb[eé]ry\s+1 fiche", sortie) is not None, sortie[-1500:])
_check("« Aoste » / « Aosta » ne fabriquent PAS un désaccord",
       "Place de la Cathédrale" not in sortie)
_check("le périmètre est écrit à côté des chiffres (règle 6)",
       "avec un lieu ET une ville" in sortie)
_check("le nombre de lieux au registre est affiché — sinon un « 0 » ne dit pas s'il "
       "vient d'une base saine ou d'un registre vide",
       "lieux au registre" in sortie)
_check("sans --apply, rien n'est écrit", "DRY-RUN" in sortie)

avant = sqlite3.connect(db).execute("SELECT ville FROM events_raw WHERE id=1").fetchone()[0]
_check("   … et c'est vrai en base, pas seulement à l'écran", avant == "Aosta",
       f"→ {avant!r}")

_vus2, sortie2 = _sortie(["--apply"])
apres = sqlite3.connect(db).execute(
    "SELECT ville, venue_source FROM events_raw WHERE id=1").fetchone()
_check("--apply corrige la ville depuis le registre", apres[0] == "Bard", f"→ {apres!r}")
_check("   et marque la provenance, pour qu'on sache d'où vient la valeur",
       apres[1] == "registre", f"→ {apres!r}")
_check("   le bilan RECOMPTE en base au lieu d'annoncer la longueur d'une liste (règle 6)",
       "vérifiée(s) en base" in sortie2, sortie2[-800:])
# Le ③ n'est PAS touché par --apply : un hommage n'est pas une faute.
t7 = sqlite3.connect(db).execute("SELECT ville FROM events_raw WHERE id=7").fetchone()[0]
_check("--apply ne touche NI ② NI ③ — ils demandent un arbitrage humain", t7 == "Torino")

vus3, sortie3 = _sortie()
_check("après correction, la fiche 1 ne se signale plus", 1 not in vus3)

# ── 4. Le registre éteint le toponyme, et il CORRIGE ─────────────────────────────────
print("\n──── 4. le registre : un arbitrage qui éteint ET qui répare ────")
# Sans ce mécanisme, ③ crierait tous les jours sur le même établissement — « un refus qui
# se rejoue sur la MÊME entrée n'est pas un rouvreur » (règle 3).
_reg = tmp / "lieux_villes.json"
_reg.write_text(json.dumps({
    "Castello di Rivoli": {"ville": "Torino",
                           "motif": "cas de fixture : on suppose l'arbitrage rendu"}
}, ensure_ascii=False), encoding="utf-8")
_ancien = lieux.CONFIG
lieux.CONFIG = tmp
lieux._registre_cache = None
try:
    _check("un lieu consigné cesse de se signaler",
           lieux.confronte("Castello di Rivoli", "Torino")[0] == "")
    _check("   mais il signale toujours une AUTRE ville que celle consignée",
           lieux.confronte("Castello di Rivoli", "Cuneo")[0] == "registre")
finally:
    lieux.CONFIG = _ancien
    lieux._registre_cache = None

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
