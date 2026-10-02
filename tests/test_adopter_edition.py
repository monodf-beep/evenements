#!/usr/bin/env python3
"""Fixture : l'adoption d'édition déplace UN post d'une fiche à l'autre, et refuse tout
ce qui n'est pas exactement ça.

D'OÙ ÇA VIENT — docs/EDITIONS_ANNUELLES.md (2026-09-15). Le risque de ce mécanisme est
celui du 2026-08-02 (fusion « Une semaine pas plus » / « Fête du lac ») transposé d'un
jour à un an : donner à une fiche le post d'un AUTRE événement. D'où plus de cas qui
doivent ÉCHOUER que de cas qui doivent passer.

LE CAS QUI DOIT PASSER est choisi à la frontière : une paire dont les titres différent
par l'année ET dont l'écart est de 300 jours tout juste (la borne basse d'appariement).

Base jetable (init_db, puis colonnes d'édition), aucun réseau : l'état WordPress est
INJECTÉ. Lancer : .venv/bin/python -m tests.test_adopter_edition
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.adopter_edition import verifier_paire, adopter, defaire  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


TODAY = "2026-09-15"
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("""CREATE TABLE events_raw(
    id INTEGER PRIMARY KEY, title TEXT, lieu TEXT, ville TEXT, recurring INTEGER,
    date_event_start TEXT, date_event_end TEXT, wp_post_id_as INTEGER, wp_permalink_as TEXT,
    duplicate_of INTEGER, edition_precedente INTEGER, edition_suivante INTEGER,
    edition_adoptee_le TEXT)""")
conn.executemany(
    "INSERT INTO events_raw(id,title,lieu,ville,recurring,date_event_start,date_event_end,"
    "wp_post_id_as,wp_permalink_as,duplicate_of) VALUES(?,?,?,?,?,?,?,?,?,?)", [
    (1, "Foire du Sanctuaire de Vicoforte 2025", "Santuario", "Vicoforte", 0,
        "2025-09-07", "2025-09-07", 2255, "https://x/evenement/foire-vicoforte/", None),
    (2, "Foire du Sanctuaire de Vicoforte 2026", "Santuario", "Vicoforte", 0,
        "2026-07-04", "2026-11-04", None, None, None),          # écart 300 j EXACT, à venir
    (3, "Foire du Sanctuaire de Vicoforte 2026 bis", "Santuario", "Vicoforte", 0,
        "2026-09-06", "2026-09-06", 9999, "https://x/evenement/foire-vicoforte-2/", None),  # a déjà un post
    (4, "Fête du Lac Annecy 2026", "Pâquier", "Annecy", 0,
        "2026-10-03", "2026-10-03", None, None, None),          # autre événement, À VENIR
        # (première version : 2026-08-01, donc PASSÉE au 15/09 — et --force refusait
        # encore, pour la règle 5. La fixture avait tort, le code non : corrigé ici, pas
        # dans le garde-fou.)
    (5, "Foire du Sanctuaire de Vicoforte 2026 passée", "Santuario", "Vicoforte", 0,
        "2026-09-06", "2026-09-06", None, None, None),          # déjà passée au 15/09
    (6, "Foire du Sanctuaire de Vicoforte 2025 corbeille", "Santuario", "Vicoforte", 0,
        "2025-09-07", "2025-09-07", 7610, "https://x/evenement/vicoforte-trash/", None),
])
conn.commit()
row = lambda i: dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (i,)).fetchone())

WP = {2255: "public", 9999: "public", 7610: "non_public"}
etat = lambda pid: WP.get(pid, "inexistant")

# ── LE CAS QUI DOIT PASSER, à la frontière (300 jours pile) ────────────────────────
r = verifier_paire(row(1), row(2), TODAY, etat)
verifier("paire canonique (même titre sans l'année, même lieu, 300 j, à venir) : ADOPTABLE",
         r == [], str(r))

# ── Ce qui doit ÉCHOUER ────────────────────────────────────────────────────────────
r = verifier_paire(row(1), row(3), TODAY, etat)
verifier("la nouvelle a DÉJÀ un post → refus, et le motif dit « 301 »",
         any("301" in x for x in r), str(r))
r = verifier_paire(row(1), row(4), TODAY, etat)
verifier("autre événement (Fête du Lac) → refus par les critères d'appariement",
         any("appariement" in x for x in r), str(r))
r = verifier_paire(row(1), row(5), TODAY, etat)
verifier("la nouvelle est déjà passée → refus (règle 5)",
         any("passée" in x for x in r), str(r))
r = verifier_paire(row(6), row(2), TODAY, etat)
verifier("le post de l'ancienne est en corbeille (état WP interrogé) → refus",
         any("non_public" in x for x in r), str(r))
r = verifier_paire(row(4), row(2), TODAY, etat)
verifier("l'ancienne n'a pas de post → refus « rien à adopter »",
         any("rien à adopter" in x for x in r), str(r))
r = verifier_paire(row(1), row(4), TODAY, etat, force=True)
verifier("--force lève SEULEMENT le critère d'appariement, pas les autres gardes",
         not any("appariement" in x for x in r) and r == [], str(r))

# ── L'écriture déplace le post et laisse la trace ; puis se défait ──────────────────
adopter(conn, row(1), row(2))
n, a = row(2), row(1)
verifier("après adoption : la nouvelle porte WP#2255 et le permalien",
         n["wp_post_id_as"] == 2255 and n["wp_permalink_as"].endswith("foire-vicoforte/"))
verifier("après adoption : l'ancienne n'a PLUS de post (pas de collision à la republication)",
         a["wp_post_id_as"] is None and a["wp_permalink_as"] is None)
verifier("la trace est posée des deux côtés",
         n["edition_precedente"] == 1 and a["edition_suivante"] == 2 and n["edition_adoptee_le"])
r = verifier_paire(row(1), row(2), TODAY, etat)
verifier("une paire déjà adoptée est refusée si on la représente (idempotence)",
         any("déjà" in x for x in r), str(r))

anc = defaire(conn, row(2))
n, a = row(2), row(1)
verifier("--defaire rend le post à l'ancienne et efface les trois colonnes",
         anc and a["wp_post_id_as"] == 2255 and n["wp_post_id_as"] is None
         and n["edition_precedente"] is None and a["edition_suivante"] is None)
verifier("--defaire sur une fiche qui n'a rien adopté → None, rien écrit",
         defaire(conn, row(4)) is None)

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
