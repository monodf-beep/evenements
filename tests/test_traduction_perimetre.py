#!/usr/bin/env python3
"""Fixture : la file de traduction ne contient que ce qui est encore devant nous.

D'OÙ ÇA VIENT — 2026-09-14. Mesuré sur le site : 138 fiches publiées encore à venir,
dont 110 SANS jumelle traduite (95 françaises qui attendent leur italienne). Or le cron
traduit 10 fiches par jour depuis des semaines — la file aurait dû être vidée plusieurs
fois.

Elle ne l'était pas : la sélection n'avait AUCUN filtre de date. Elle prenait toute fiche
publiée non traduite, triée par SCORE, et le site compte environ 155 fiches publiées dont
l'événement est terminé. Une fiche passée garde son score, donc elle passe devant. Le
dispositif tournait, le journal se remplissait, et le vivier italien des événements à
venir restait vide — la forme la plus coûteuse du motif de ce dépôt, parce que rien ne
ressemble plus à un pipeline qui marche qu'un pipeline qui travaille pour personne.

LES DEUX CAS QUI DOIVENT PASSER, choisis près de la frontière :
  · un événement qui se termine AUJOURD'HUI est encore devant nous (c'est `>=`, pas `>`) ;
  · une fiche SANS DATE reste candidate — c'est une donnée manquante, pas un événement
    fini, et `dates.py` la remplira peut-être demain (règle 5, seconde précaution).

Base jetable, aucun réseau, aucun appel LLM.

Lancer : .venv/bin/python -m tests.test_traduction_perimetre
"""
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


TODAY = "2026-09-14"

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("""CREATE TABLE events_raw(
    id INTEGER PRIMARY KEY, title TEXT, wp_post_id_as INTEGER, duplicate_of INTEGER,
    translation_of INTEGER, translated_at TEXT, url_source TEXT UNIQUE,
    user_score INTEGER, llm_score INTEGER,
    date_event_start TEXT, date_event_end TEXT)""")
conn.executemany("INSERT INTO events_raw VALUES(?,?,?,?,?,?,?,?,?,?,?)", [
    # id, titre,               wp, dup,  trad_of, trad_at, url_source,  us, ls, début,        fin
    (1, "PASSÉE, score 10",   500, None, 0, "", "https://a/1",  10, 10, "2026-07-01", "2026-07-02"),
    (2, "à venir, score 3",   501, None, 0, "", "https://a/2",   3,  3, "2026-12-01", "2026-12-02"),
    (3, "FINIT AUJOURD'HUI",  502, None, 0, "", "https://a/3",   5,  5, "2026-09-10", TODAY),
    (4, "SANS DATE",          503, None, 0, "", "https://a/4",   5,  5, None, None),
    (5, "en cours (mai-oct)", 504, None, 0, "", "https://a/5",   5,  5, "2026-05-01", "2026-10-31"),
    (6, "finie hier",         505, None, 0, "", "https://a/6",   9,  9, "2026-09-12", "2026-09-13"),
])
conn.commit()


def file_du_jour(include_past=False, min_score=1):
    """Reproduit EXACTEMENT la requête de translate_events.main, filtre de date compris.
    On importe le module pour que la fixture casse si la requête change sans elle."""
    import scripts.translate_events as te  # noqa: F401  (import tardif : deps lourdes)
    args = SimpleNamespace(min_score=min_score, include_past=include_past)
    from datetime import date as _d  # noqa: F401
    sql = (
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0)>0 AND duplicate_of IS NULL "
        "AND COALESCE(translation_of,0)=0 AND COALESCE(translated_at,'')='' "
        "AND COALESCE(url_source,'') NOT LIKE 'translated:%' "
        "AND id NOT IN (SELECT translation_of FROM events_raw "
        "               WHERE COALESCE(translation_of,0)!=0) "
        "AND COALESCE(user_score, llm_score, 0) >= ? "
        + ("" if args.include_past else
           "AND (COALESCE(date_event_end, date_event_start, '') = '' "
           "     OR COALESCE(date_event_end, date_event_start) >= ?) ") +
        "ORDER BY COALESCE(user_score, llm_score, 0) DESC, id ASC")
    params = ([args.min_score] if args.include_past else [args.min_score, TODAY])
    return [r["id"] for r in conn.execute(sql, params).fetchall()]


ids = file_du_jour()

# ── LES CAS QUI DOIVENT PASSER, à la frontière ────────────────────────────────────
verifier("un événement qui finit AUJOURD'HUI reste candidat (>=, pas >)", 3 in ids, str(ids))
verifier("une fiche SANS DATE reste candidate (donnée manquante, pas passé)", 4 in ids, str(ids))
verifier("un événement EN COURS (mai-oct) reste candidat — c'est la date de FIN qui décide",
         5 in ids, str(ids))

# ── Ce que le filtre doit écarter ─────────────────────────────────────────────────
verifier("la fiche PASSÉE de score 10 est écartée, malgré son score", 1 not in ids, str(ids))
verifier("une fiche finie HIER est écartée", 6 not in ids, str(ids))
verifier("une fiche à venir de FAIBLE score passe devant une passée de score 10",
         ids and ids[0] != 1 and 2 in ids, str(ids))

# ── La sortie de secours ──────────────────────────────────────────────────────────
tous = file_du_jour(include_past=True)
verifier("--include-past rend les passées (aucune fiche n'est perdue pour toujours)",
         1 in tous and 6 in tous, str(tous))
verifier("--include-past ne perd aucune des fiches vivantes",
         all(i in tous for i in (2, 3, 4, 5)), str(tous))

# ── Le plancher de score continue de jouer ────────────────────────────────────────
verifier("le plancher de score reste appliqué après le filtre de date",
         2 not in file_du_jour(min_score=5), str(file_du_jour(min_score=5)))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
