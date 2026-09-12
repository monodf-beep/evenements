#!/usr/bin/env python3
"""Fixture : le DERNIER RECOURS (recherche web) de la date et du lieu s'arrête
proprement sous plafond API, au lieu de le ravaler comme une page muette.

TROUVÉ le 2026-08-05 en balayant les points d'appel LLM après l'incident du
2026-08-04 (utils/api_limite.py) : `dates.py`, `venues.py` et `visuals.py` avaient
déjà leur garde, mais leurs propres derniers recours — `scripts/dates_web.web_date`
et `scripts/venues_web.web_venue`, appelés à la fois par leur propre `main()` ET par
`scripts.autocomplete._fill_date`/`_fill_venue` — attrapaient TOUTE exception
(`except Exception`) et rendaient `("", "", "web_none")`, exactement le trou déjà
bouché ailleurs le 04. Sous plafond, `scripts.autocomplete`'s `except PlafondAPI`
(posé le même jour pour ce même risque) ne voyait donc jamais rien passer : le lot
continuait, fiche après fiche, à interroger une API qui refuse déjà.

⚠️ BASE JETABLE, aucun appel réseau : le client Anthropic est un faux objet qui lève
l'erreur de plafond réellement reçue le 2026-08-04 à 15h33.

Lancer : .venv/bin/python -m tests.test_web_fallback_plafond
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
os.environ["ANTHROPIC_API_KEY"] = "factice-jamais-appelee"

from scripts.scraper_events import init_db  # noqa: E402
import scripts.dates_web as dates_web  # noqa: E402
import scripts.venues_web as venues_web  # noqa: E402
from utils.api_limite import PlafondAPI  # noqa: E402

dates_web.DB_PATH = tmp
venues_web.DB_PATH = tmp


class ErreurPlafond(Exception):
    """Reproduit l'erreur réelle du 2026-08-04 15h33 (status_code + texte du SDK)."""
    status_code = 400

    def __str__(self):
        return ("Error code: 400 - You have reached your specified API usage limits. "
                "You will regain access on 2026-09-01 at 00:00 UTC.")


class ErreurReseau(Exception):
    status_code = 502

    def __str__(self):
        return "Bad gateway"


class FauxClient:
    def __init__(self, exc=None, reponse=None):
        self._exc = exc
        self._reponse = reponse
        self.appels = 0

    class _Bloc:
        def __init__(self, text):
            self.type = "text"
            self.text = text

    class _Messages:
        def __init__(self, parent):
            self._p = parent

        def create(self, **kw):
            self._p.appels += 1
            if self._p._exc:
                raise self._p._exc

            class _Msg:
                content = [FauxClient._Bloc(self._p._reponse)]
                usage = None
            return _Msg()

    @property
    def messages(self):
        return self._Messages(self)


def _base(nb=3):
    if tmp.exists():
        tmp.unlink()
    conn = sqlite3.connect(tmp)
    init_db(conn)
    for i in range(nb):
        conn.execute(
            "INSERT INTO events_raw (title, description, url_source, ville, territoire, "
            "statut, llm_score, date_event_start, date_event_end) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (f"Festival {i}", "Un événement culturel.", f"https://a.fr/{i}", "Annecy",
             "Savoie", "evaluated", 8, "2026-11-15" if i else "", "2026-11-15" if i else ""))
    conn.commit()
    conn.close()


echecs = 0

# ── 1. web_date / web_venue lèvent PlafondAPI au lieu de rendre 'web_none' ──────
print("──── web_date / web_venue sous plafond ────")
for label, fn, args in (
    ("web_date", dates_web.web_date, ({"title": "x"}, FauxClient(ErreurPlafond()), "2026-08-05")),
    ("web_venue", venues_web.web_venue, ({"title": "x"}, FauxClient(ErreurPlafond()))),
):
    try:
        fn(*args)
        print(f"ÉCHEC {label} : a rendu 'web_none' au lieu de lever PlafondAPI")
        echecs += 1
    except PlafondAPI:
        print(f"OK    {label} : PlafondAPI levée")

# Contre-épreuve : une panne réseau ORDINAIRE reste tolérée (comportement inchangé).
print("\n──── contre-épreuve : panne réseau ordinaire, toujours tolérée ────")
s, e, src = dates_web.web_date({"title": "x"}, FauxClient(ErreurReseau()), "2026-08-05")
if src == "web_none":
    print("OK    web_date : panne ordinaire → ('','','web_none'), pas d'exception")
else:
    print(f"ÉCHEC web_date panne ordinaire : {(s, e, src)}")
    echecs += 1
lieu, ville, src = venues_web.web_venue({"title": "x"}, FauxClient(ErreurReseau()))
if src == "web_none":
    print("OK    web_venue : panne ordinaire → ('','','web_none'), pas d'exception")
else:
    print(f"ÉCHEC web_venue panne ordinaire : {(lieu, ville, src)}")
    echecs += 1

# ── 2. Le lot complet (main()) : plafond au 1er appel → arrêt propre, rc=3 ──────
print("\n──── lot dates_web.main() / venues_web.main() sous plafond ────")
_base(3)
dates_web.web_date = lambda *a, **k: (_ for _ in ()).throw(PlafondAPI("plafond"))
rc = dates_web.main([])
if rc == 3:
    print("OK    dates_web.main() : code retour 3 sous plafond")
else:
    print(f"ÉCHEC dates_web.main() : rc={rc}, attendu 3")
    echecs += 1

_base(3)
# Toutes les fiches ont une date ('2026-11-15' sauf la première) — on ne veut tester
# QUE venues_web ici, donc on donne un lieu vide et une date à toutes pour la sélection.
conn = sqlite3.connect(tmp)
conn.execute("UPDATE events_raw SET date_event_start='2026-11-15', date_event_end='2026-11-15'")
conn.commit()
conn.close()
venues_web.web_venue = lambda *a, **k: (_ for _ in ()).throw(PlafondAPI("plafond"))
rc = venues_web.main([])
if rc == 3:
    print("OK    venues_web.main() : code retour 3 sous plafond")
else:
    print(f"ÉCHEC venues_web.main() : rc={rc}, attendu 3")
    echecs += 1

# ── 3. Contre-épreuve : sans plafond, le lot écrit toujours normalement ─────────
print("\n──── contre-épreuve : chaîne normale (main()) ────")
_base(3)
dates_web.web_date = lambda ev, client, today: ("2026-12-24", "2026-12-24", "web")
rc = dates_web.main([])
conn = sqlite3.connect(tmp)
n = conn.execute("SELECT COUNT(*) FROM events_raw WHERE date_source='web'").fetchone()[0]
conn.close()
if rc == 0 and n >= 1:
    print(f"OK    dates_web.main() : rc=0, {n} fiche(s) datée(s)")
else:
    print(f"ÉCHEC dates_web.main() contre-épreuve : rc={rc}, {n} datée(s)")
    echecs += 1

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
