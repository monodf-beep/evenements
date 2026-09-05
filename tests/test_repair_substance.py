#!/usr/bin/env python3
"""Fixture : qui entre dans la file de réparation des fiches maigres, et qui n'y entre pas.

108 fiches publiées sont sous le plancher de substance, dont 99 sans le moindre article
(mesuré le 2026-08-09). Le commit qui a posé le portillon annonçait « enrichissement ou
dépublication, décision par décision » — et neuf jours plus tard aucune décision n'avait
été prise, parce qu'il y en a cent huit à prendre.

Réparer coûte ~0,33 $ l'unité (mesuré : 121,13 $ pour 369 enrichissements sur 14 jours).
Le périmètre n'est donc pas un détail d'affichage, c'est ce qui décide de la dépense. Les
cas ci-dessous sont pris DES DEUX CÔTÉS de chaque frontière — un test qui ne retient que
des cas confirmant le design ne prouve rien (CLAUDE.md, règle 3).

Lancer : .venv/bin/python -m tests.test_repair_substance
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

from scripts.scraper_events import init_db  # noqa: E402
import scripts.repair_substance as rs  # noqa: E402

rs.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


AUJOURDHUI = "2026-08-11"
LONG = "Un très bel événement culturel de la Vallée d'Aoste. " * 40   # bien au-dessus
ART = '{"article":{"chapo":"%s","corps":"%s"}}'

conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row      # _candidates lit les colonnes par nom
init_db(conn)
# (id, wp_post_id_as, titre, article_title, enrich_data, fin, statut, translation_of,
#  recurring, doit_être_candidate, motif)
CAS = [
    (1, 771, "Maigre, jamais enrichie", "", "", "2026-12-01", "published_cs", 0, 0, True,
     "le cas type : en ligne, à venir, aucun article"),
    (2, 772, "Maigre, déjà rédigée", "Titre", ART % ("court", "trop court"),
     "2026-12-01", "published_cs", 0, 0, True,
     "candidate, mais rangée à part : la matière manque, pas la rédaction"),
    (3, 773, "Assez fournie", "Titre", ART % (LONG, LONG), "2026-12-01", "published_cs",
     0, 0, False, "au-dessus du plancher — rien à réparer"),
    (4, 774, "Maigre mais PASSÉE", "", "", "2026-05-01", "published_cs", 0, 0, False,
     "règle 5 : l'événement a eu lieu, la réparer ne sert personne"),
    (5, None, "Maigre, PAS en ligne", "", "", "2026-12-01", "evaluated", 0, 0, False,
     "invisible du public : le portillon de publication la traitera"),
    (6, 776, "Maigre TRADUCTION", "", "", "2026-12-01", "published_cs", 1, 0, False,
     "enrich écrit en français : on répare l'original, jamais la jumelle"),
    (7, 777, "Maigre RÉCURRENTE, date passée", "", "", "2026-05-01", "published_cs", 0, 1,
     True, "un récurrent n'est JAMAIS passé — il n'a pas de date unique"),
    (8, 778, "Maigre mais REJETÉE", "", "", "2026-12-01", "rejected", 0, 0, False,
     "plus personne ne la publiera"),
]
for eid, wp, titre, at, ed, fin, statut, tof, rec, _a, _m in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, wp_post_id_as, title, article_title, enrich_data, "
        "date_event_end, statut, translation_of, recurring, url_source, description) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (eid, wp, titre, at, ed, fin, statut, tof, rec, f"https://x/{eid}", "desc"))
conn.commit()

print("──── périmètre de la réparation ────")
candidates = {e["id"] for e in rs._candidates(conn, AUJOURDHUI)}
for eid, _w, titre, _at, _ed, _f, _s, _t, _r, attendu, motif in CAS:
    _check(f"{'retenue' if attendu else 'écartée'} — {titre[:34]:34} ({motif})",
           (eid in candidates) == attendu, f"candidates={sorted(candidates)}")

# ── L'ordre : les fiches jamais enrichies d'abord ───────────────────────────────
print("\n──── ordre de traitement ────")
ordre = [e["id"] for e in rs._candidates(conn, AUJOURDHUI)]
_check("les jamais enrichies passent avant celles qui ont déjà un article",
       ordre.index(1) < ordre.index(2) and ordre.index(7) < ordre.index(2), str(ordre))
conn.close()

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
