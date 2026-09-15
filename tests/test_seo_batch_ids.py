#!/usr/bin/env python3
"""Fixture : `seo_batch --ids` cible exactement les fiches demandées, et RIEN d'autre.

D'OÙ ÇA VIENT — 2026-09-10. En dictant la marche à suivre du chantier « longueur », j'ai
écrit `seo_batch --redo --ids …` : l'option `--ids` N'EXISTAIT PAS. C'est la faute 12 du
08/09 sous une autre forme — une commande donnée sans vérifier qu'elle existe.

Elle manquait vraiment, et pas pour le confort : après une ré-écriture d'articles, la clé
doit être re-choisie sur LES MÊMES fiches (le corps a changé). `--redo --cap 10` reprend
la file entière dans SON ordre — on croit relancer les 10 qu'on vient de ré-écrire, on en
relance 10 autres, et les 10 vraies gardent une clé calculée sur un texte qui n'existe
plus.

LE CAS QUI DOIT PASSER est la sélection ORDINAIRE, sans `--ids` : c'est elle qui tourne
au cron tous les jours, et un ciblage ajouté ne doit rien lui retirer.

Base jetable, aucun réseau, aucun appel LLM.

Lancer : .venv/bin/python -m tests.test_seo_batch_ids
"""
import sqlite3
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.seo_batch import _select  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


TODAY = "2026-09-10"
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("""CREATE TABLE events_raw(
    id INTEGER PRIMARY KEY, title TEXT, statut TEXT, duplicate_of INTEGER,
    date_event_start TEXT, date_event_end TEXT, llm_score INTEGER,
    wp_post_id_as INTEGER, seo_at TEXT, seo_pushed_at TEXT, annule_le TEXT)""")
conn.executemany("INSERT INTO events_raw VALUES(?,?,?,?,?,?,?,?,?,?,?)", [
    # id, titre,      statut,     dup, début,        fin,          score, wp,  seo_at,  pushed, annulé
    (1, "à venir, en ligne, SEO fait", "evaluated", None, "2026-12-01", "2026-12-02", 8, 500, "2026-09-01", "2026-09-01", None),
    (2, "à venir, hors ligne, sans SEO", "evaluated", None, "2026-12-05", "2026-12-05", 9, None, None, None, None),
    (3, "PASSÉE",                    "evaluated", None, "2025-01-01", "2025-01-02", 9, 501, None, None, None),
    (4, "score faible, hors ligne",  "evaluated", None, "2026-12-09", "2026-12-09", 2, None, None, None, None),
    (5, "ANNULÉE",                   "evaluated", None, "2026-12-10", "2026-12-10", 9, 502, None, None, "2026-09-01"),
])
conn.commit()


def args(**kw):
    base = dict(ids=None, cap=30, min_score=7, redo=False, include_past=False)
    base.update(kw)
    return SimpleNamespace(**base)


# ── LE CAS QUI DOIT PASSER : la sélection ordinaire est intacte ────────────────────
ordinaire = [r["id"] for r in _select(conn, args(), TODAY)]
verifier("sans --ids : la file normale ne retient que le 2 (à venir, sans SEO, score ≥ 7)",
         ordinaire == [2], str(ordinaire))
verifier("sans --ids : la fiche PASSÉE reste écartée", 3 not in ordinaire)
verifier("sans --ids : la fiche ANNULÉE reste écartée", 5 not in ordinaire)
verifier("sans --ids : la fiche déjà pourvue d'un seo_at reste écartée", 1 not in ordinaire)

# ── Le ciblage : tous les filtres levés, l'ordre demandé respecté ──────────────────
cible = [r["id"] for r in _select(conn, args(ids=[3, 1, 5]), TODAY)]
verifier("--ids : rend EXACTEMENT les ids demandés, dans l'ordre donné",
         cible == [3, 1, 5], str(cible))
verifier("--ids : lève le filtre de date (la fiche passée est rendue)", 3 in cible)
verifier("--ids : lève le filtre seo_at (la fiche déjà faite est rendue)", 1 in cible)
verifier("--ids : lève le filtre d'annulation", 5 in cible)
verifier("--ids : lève le plancher de score",
         [r["id"] for r in _select(conn, args(ids=[4]), TODAY)] == [4])

# ── Un id inexistant ne doit pas faire tomber le lot, ni gonfler le compte ─────────
melange = [r["id"] for r in _select(conn, args(ids=[2, 99999]), TODAY)]
verifier("--ids : un id introuvable est ignoré, pas inventé, et le reste passe",
         melange == [2], str(melange))

# ── --ids vide ou absent = comportement ordinaire, jamais « tout » ─────────────────
verifier("--ids [] : retombe sur la file normale, pas sur la base entière",
         [r["id"] for r in _select(conn, args(ids=[]), TODAY)] == [2])

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
