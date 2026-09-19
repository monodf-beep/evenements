#!/usr/bin/env python3
"""Fixture : le solde des vérifications doit être REJOUABLE. Base jetable.

LE DÉFAUT REPRODUIT ICI A ÉTÉ VU EN PRODUCTION le 2026-08-11 à 20h50, dans la sortie d'un
`--apply` que Franck venait de coller :

    [ 3995] À CORRIGER dans l'article en ligne — Organisateur : Pro Loco de Saint-…
            ✓ Organisateur : la Pro Loco de Saint-Rhémy-en-Bosses…
            ⚠ article EN LIGNE à corriger : Organisateur : Pro Loco…

Le script fermait sa PROPRE correction et en rouvrait une neuve. La correction posée au
premier run contient forcément le fragment cherché (« Stefania Marchiano ») ; le second run
la prend donc pour le doute d'origine. Chaque exécution ajoutait deux lignes à la table et
remettait à zéro l'ancienneté de la tâche — celle qui dit depuis combien de temps l'article
en ligne est faux.

C'est la faute que ce dépôt combat depuis le matin, commise par le script écrit pour la
combattre. Et comme les autres, elle était invisible dans le code : c'est la LISTE des onze
points fermés qui l'a montrée, trois d'entre eux portant un libellé rédigé trois heures plus
tôt par ce même script.

La fixture enchaîne donc DEUX `--apply`, comme on l'a fait pour `completer_verifie` après le
plantage de 18h58. Un script destiné à tourner plusieurs fois doit être testé plusieurs fois.

Lancer : .venv/bin/python -m tests.test_solder_rejouable
"""
import io
import contextlib
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import solder_verifications as S  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


tmp = Path(tempfile.mkdtemp(prefix="fixture-solder-"))
db = tmp / "events.db"
conn = sqlite3.connect(db)
init_db(conn)
for col, decl in (("date_event_start", "TEXT"), ("date_event_end", "TEXT"),
                  ("recurring", "INTEGER DEFAULT 0"), ("wp_post_id_as", "INTEGER")):
    try:
        conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
    except sqlite3.OperationalError:
        pass
conn.execute("""CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, label TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT)""")

AVENIR = (date.today() + timedelta(days=60)).isoformat()
# 3995 est EN LIGNE : son doute doit devenir une correction. 3594 ne l'est pas : son doute
# se ferme simplement, sans correction (l'article n'existe pas encore).
conn.execute("INSERT INTO events_raw (id, title, url_source, source_name, "
             " date_event_start, date_event_end, wp_post_id_as) VALUES (?,?,?,?,?,?,?)",
             (3995, "Percorso in Rosso", "https://exemple.fr/3995", "La Prima Linea",
              AVENIR, AVENIR, 6001))
conn.execute("INSERT INTO events_raw (id, title, url_source, source_name, "
             " date_event_start, date_event_end, wp_post_id_as) VALUES (?,?,?,?,?,?,?)",
             (3594, "Bal à la Citadelle", "https://exemple.fr/3594", "Villefranche",
              AVENIR, AVENIR, None))
conn.execute("INSERT INTO checks (event_id, label) VALUES (?,?)",
             (3995, "Stefania Marchiano : autrice de l'article ou organisatrice ?"))
conn.execute("INSERT INTO checks (event_id, label) VALUES (?,?)",
             (3594, "Nature exacte de LivePlay (DJ, orchestre, groupe ?) à confirmer"))
conn.commit()
conn.close()
S.DB_PATH = db


def _run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        S.main(list(argv))
    return buf.getvalue()


def _points(eid=None):
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    q = "SELECT label, status FROM checks"
    p = ()
    if eid:
        q += " WHERE event_id=?"
        p = (eid,)
    r = [(x["label"], x["status"]) for x in c.execute(q, p)]
    c.close()
    return r


print("──── 1. le dry-run n'écrit rien ────")
_run()
_check("les deux points sont encore ouverts",
       sum(1 for _l, s in _points() if s == "pending") == 2, _points())

print("\n──── 2. premier passage ────")
_run("--apply")
p3995, p3594 = _points(3995), _points(3594)
_check("le doute de 3995 est fermé",
       any(s == "done" and "Marchiano : autrice" in l for l, s in p3995), p3995)
_check("la réponse est inscrite en clair",
       any(l.startswith(S._PREFIXE_REPONSE) for l, _s in p3995), p3995)
_check("fiche EN LIGNE : une correction est ouverte à la place",
       sum(1 for l, s in p3995 if l.startswith(S._PREFIXE_CORRECTION)
           and s == "pending") == 1, p3995)
_check("fiche HORS LIGNE : aucune correction ouverte, l'article n'existe pas",
       not any(l.startswith(S._PREFIXE_CORRECTION) for l, _s in p3594), p3594)

avant = _points()

print("\n──── 3. SECOND passage : c'est ici que ça se jouait ────")
sortie = _run("--apply")
apres = _points()
_check("la correction n'est PAS refermée par le script qui l'a écrite",
       sum(1 for l, s in _points(3995)
           if l.startswith(S._PREFIXE_CORRECTION) and s == "pending") == 1, _points(3995))
_check("aucune correction en double",
       sum(1 for l, _s in _points(3995) if l.startswith(S._PREFIXE_CORRECTION)) == 1,
       _points(3995))
_check("aucune réponse en double",
       sum(1 for l, _s in _points(3995) if l.startswith(S._PREFIXE_REPONSE)) == 1,
       _points(3995))
_check("la table n'a pas grossi d'un pouce", len(apres) == len(avant),
       f"{len(avant)} → {len(apres)}")
_check("et le script le DIT au lieu de faire semblant d'avoir travaillé",
       "Aucun point en attente" in sortie, sortie[:200])

print("\n──── 4. troisième passage, par acquit de conscience ────")
_run("--apply")
_check("toujours rien de nouveau", len(_points()) == len(avant),
       f"{len(avant)} → {len(_points())}")

print("\n──── 5. le reconnaisseur de ses propres écritures ────")
_check("une correction est reconnue",
       S._est_de_moi(S._PREFIXE_CORRECTION + "Organisateur : Pro Loco, PAS X"))
_check("une réponse est reconnue", S._est_de_moi(S._PREFIXE_REPONSE + "quoi que ce soit"))
_check("un vrai doute ne l'est PAS — le cas près de la frontière",
       not S._est_de_moi("Stefania Marchiano : autrice ou organisatrice ?"))
_check("ni un doute qui parlerait de correction en cours de phrase",
       not S._est_de_moi("Faut-il corriger l'article en ligne ? à vérifier"))

print(f"\n{'TOUT PASSE' if not echecs else str(echecs) + ' ÉCHEC(S)'}")
sys.exit(1 if echecs else 0)
