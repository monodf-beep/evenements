#!/usr/bin/env python3
"""Fixture : le contradicteur de LIENS. Base jetable, réseau simulé — jamais l'un ni
l'autre en vrai.

CE QU'ELLE SURVEILLE EN PREMIER, ET C'EST L'INVERSE DE L'INTUITION. Le danger n'est pas de
rater un lien mort : c'est d'en déclarer un qui marche. Un 403 renvoyé à NOTRE serveur
n'empêche personne d'ouvrir la page — `agendaculturel.fr` refuse ce serveur sur ses quatre
sous-domaines et porte 338 fiches. Si le contrôle comptait ces refus comme des liens
morts, il rendrait une file de plusieurs centaines de lignes dont aucune n'aurait de
geste au bout : très exactement la file de 454 « points à contrôler » du 2026-08-11, dont
315 n'étaient pas des faits douteux.

  1. 403 / 401 / 429 → JAMAIS une tâche, mais COMPTÉ ;
  2. 5xx et injoignable → pareil : une panne revient toute seule ;
  3. l'absence de lien ne signale rien ;
  4. le passé est hors périmètre (règle 5), le sans-date y reste ;
  5. et seulement ensuite : le 404 est bien vu, et les fiches qui le partagent aussi.

Lancer : .venv/bin/python -m tests.test_verifier_liens
"""
import contextlib
import io
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import verifier_liens  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ── 1. La classification, sans réseau ────────────────────────────────────────────────
print("──── 1. ce qui n'est PAS un lien mort — d'abord ────")


class _Rep:
    def __init__(self, code):
        self.status_code = code


def _repond(code):
    verifier_liens.requests.get = lambda *a, **k: _Rep(code)
    return verifier_liens.etat("https://exemple.fr/x")


_vrai_get = verifier_liens.requests.get
try:
    for code in (401, 403, 429):
        v, c = _repond(code)
        _check(f"{code} → « refus », pas « disparue » (c'est NOUS qu'on écarte)",
               v == "refus", f"→ {v}")
    for code in (500, 502, 503):
        v, c = _repond(code)
        _check(f"{code} → « panne » : ça revient tout seul", v == "panne", f"→ {v}")
    for code in (200, 301, 302):
        v, c = _repond(code)
        _check(f"{code} → vivant", v == "vivant", f"→ {v}")

    print("\n──── 2. ce qui EST un lien mort ────")
    for code in (404, 410):
        v, c = _repond(code)
        _check(f"{code} → DISPARUE, et c'est la seule famille qui fasse une tâche",
               v == "disparue", f"→ {v}")

    # UNE PANNE RÉSEAU N'EST PAS UNE PAGE MORTE. Sans ce cas, une coupure DNS de trois
    # minutes ferait apparaître tout le site comme cassé.
    def _explose(*a, **k):
        raise verifier_liens.requests.RequestException("DNS")
    verifier_liens.requests.get = _explose
    v, c = verifier_liens.etat("https://exemple.fr/x")
    _check("une erreur réseau → « injoignable », jamais « disparue »",
           v == "injoignable" and c is None, f"→ {v}")
finally:
    verifier_liens.requests.get = _vrai_get

# ── 3. Sur base jetable, avec un réseau simulé ───────────────────────────────────────
print("\n──── 3. sur base — périmètre, regroupement, comptage ────")
tmp = Path(tempfile.mkdtemp(prefix="fixture-verifliens-"))
db = tmp / "fixture.db"
conn = sqlite3.connect(db)
init_db(conn)

AVENIR = (date.today() + timedelta(days=30)).isoformat()
PASSE = (date.today() - timedelta(days=30)).isoformat()

MORT = "https://opera-nice.org/spectacle-retire"
VIVANT = "https://villefranche-sur-mer.fr/agenda"
REFUS = "https://ville-bloquee.fr/agenda"

CAS = [
    # id, titre, url_officiel, début, fin, wp, statut
    (1, "Récital lyrique", MORT, AVENIR, AVENIR, 9001, "pending"),
    (2, "Autre soirée à l'opéra", MORT, AVENIR, AVENIR, 9002, "pending"),  # MÊME url
    (3, "Fête des pêcheurs", VIVANT, AVENIR, AVENIR, 9003, "pending"),
    (4, "Concert bloqué", REFUS, AVENIR, AVENIR, 9004, "pending"),
    (5, "Sans lien", "", AVENIR, AVENIR, 9005, "pending"),
    # RÈGLE 5 : le passé sort, même avec un lien mort.
    (6, "Concert de mai", MORT, PASSE, PASSE, 9006, "pending"),
    # SANS DATE : donnée manquante, pas événement terminé — elle reste.
    (7, "Date à confirmer", MORT, "", "", 9007, "pending"),
    # NON PUBLIÉE : personne ne peut cliquer ce lien, hors périmètre par défaut.
    (8, "Brouillon", MORT, AVENIR, AVENIR, None, "pending"),
]
# LE MONTAGE DEMANDE DEUX PRÉCAUTIONS, et les deux viennent du code réel.
#
# 1. `url_source` porte une contrainte d'UNICITÉ en base : impossible d'y mettre deux
#    fois la même adresse pour tester deux fiches qui partagent un lien.
# 2. La publication ne lit pas `url_officiel` mais `publisher_as._source_publiable()`,
#    qui retient l'ancre officielle et, à défaut, retombe sur `url_source`.
#
# On donne donc à chaque fiche une `url_source` unique sur un hôte que
# `radar._is_official_host` REFUSE (un agrégateur) : elle ne peut jamais l'emporter, et
# l'adresse testée est bien celle qu'on a voulu poser dans `url_officiel`.
for eid, titre, url, deb, fin, wp, statut in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_officiel, url_source, source_name, "
        " date_event_start, date_event_end, statut, wp_post_id_as) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (eid, titre, url, f"https://agendaculturel.fr/fixture-{eid}",
         "Source officielle", deb, fin, statut, wp))
conn.commit()
conn.close()
verifier_liens.DB_PATH = db

_REPONSES = {MORT: 404, VIVANT: 200, REFUS: 403}


def _faux_get(url, **k):
    return _Rep(_REPONSES.get(url, 200))


verifier_liens.requests.get = _faux_get


def _sortie(argv=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        verifier_liens.main(argv or [])
    return buf.getvalue()


s = _sortie()
_check("le lien mort est listé", MORT in s)
_check("les DEUX fiches qui le partagent sont nommées", "[    1]" in s and "[    2]" in s)
_check("une seule requête pour cette adresse (regroupée par URL)",
       s.count(MORT) <= 2, "l'URL apparaît trop de fois : le regroupement a sauté")
_check("le 403 n'est PAS présenté comme un lien mort", REFUS not in s.split("═══ 1")[-1]
       if "═══ 1" in s else REFUS not in s.split("morte(s)")[-1])
_check("   mais il est COMPTÉ — sinon on le découvre des semaines plus tard",
       "refus (401/403/429)" in s)
_check("le lien vivant ne remonte pas", VIVANT not in s.split("morte(s)")[-1])
_check("le PASSÉ est hors périmètre (règle 5)", "[    6]" not in s)
_check("SANS DATE n'est pas du passé : la fiche reste vue", "[    7]" in s)
_check("une fiche non publiée est hors périmètre par défaut", "[    8]" not in s)
_check("… et --tout la fait entrer", "[    8]" in _sortie(["--tout"]))
_check("le périmètre est écrit à côté des chiffres (règle 6)",
       "adresse(s) distincte(s)" in s)
_check("les fiches SANS lien sont comptées — sinon « 0 lien mort » se lirait\n       « tous nos liens sont bons »", "AUCUN lien officiel" in s)
# LA VRAIE ADRESSE PUBLIÉE, pas la colonne qu'on croit. Contrôle ajouté après
# avoir constaté que la première version lisait `url_officiel` seule.
_check("l'adresse testée est celle que la PUBLICATION calcule",
       verifier_liens.lien_publie({"url_officiel": "", "url_source": MORT,
                                   "source_type": "", "source_name": "Mairie"})
       == MORT)
_check("   et le radar ne publie jamais son article de presse (charte §8)",
       verifier_liens.lien_publie({"url_officiel": "", "url_source": MORT,
                                   "source_type": "radar", "source_name": "X"})
       == "")
_check("le geste est nommé, pas seulement le problème", "completer_verifie" in s)

# LE PLAFOND DOIT SE DIRE. Un « --cap » silencieux ferait lire la sortie comme une
# couverture complète alors qu'elle en couvre une partie.
s_cap = _sortie(["--cap", "1"])
_check("un plafond atteint est ANNONCÉ, jamais silencieux",
       "au-delà du plafond" in s_cap, s_cap[:400])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
