#!/usr/bin/env python3
"""Fixture : toute colonne ajoutée quelque part est-elle déclarée dans init_db ?

D'OÙ ÇA VIENT — 2026-09-22. En montant une fixture du back-office, `multi_lieux`
manquait à une base neuve. Elle n'était créée que par un `ALTER TABLE` isolé dans
`scripts/completer_depuis_mail.py`, alors qu'`app/app.py` l'interroge SANS CONDITION
(`incomplete_clause`) : la route /a-completer plantait sur une base fraîche. Rien
n'était cassé en production — le cron de 8h48 pose la colonne depuis longtemps — mais
toute fixture partait d'une base que la production n'a pas, ce qui les rend toutes
suspectes.

En comptant, il y en avait SIX dans ce cas. Et la leçon était DÉJÀ écrite dans
`init_db`, pour `annule_le` et `wp_deleted_at` : « une colonne créée par un seul module
casse tous les autres sur une base neuve ». Elle n'avait pas tenu, parce qu'elle
n'était qu'un commentaire. Cette fixture est ce qui la fait tenir.

CE QU'ELLE VÉRIFIE : toute colonne de `events_raw` ajoutée par un `ALTER TABLE` où que
ce soit dans le dépôt existe aussi sur une base créée par `init_db` seul. Les ALTER
d'origine peuvent rester — ils deviennent des no-op — mais ils ne font plus foi.

Lancer : .venv/bin/python -m tests.test_colonnes_declarees
"""
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# Une base NEUVE, telle que le CLAUDE.md prescrit d'en construire pour une fixture.
chemin = Path(tempfile.mkdtemp()) / "neuve.db"
conn = sqlite3.connect(chemin)
init_db(conn)
colonnes = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}

# Tout ALTER TABLE du dépôt, littéral ou construit avec une f-string sur une liste.
ajoutees = {}
for py in list(ROOT.glob("scripts/*.py")) + list(ROOT.glob("app/*.py")) + \
        list(ROOT.glob("utils/*.py")):
    texte = py.read_text(encoding="utf-8")
    for m in re.finditer(
            r"ALTER TABLE events_raw ADD COLUMN ([a-z_][a-z0-9_]*)", texte):
        ajoutees.setdefault(m.group(1), []).append(py.name)

verifier("des ALTER TABLE existent bien dans le dépôt (sinon la fixture ne prouve rien)",
         len(ajoutees) >= 5, str(len(ajoutees)))

orphelines = sorted(c for c in ajoutees if c not in colonnes)
verifier("toute colonne ajoutée ailleurs existe aussi sur une base neuve",
         not orphelines,
         "; ".join(f"{c} (ajoutée par {', '.join(ajoutees[c])})" for c in orphelines))

# Les six du rattrapage, nommées : si l'une repart, on veut savoir laquelle.
for col in ("multi_lieux", "mail_corps", "organisateur_byline", "seo_pushed_at",
            "unmerge_data", "worth_trip", "annule_le", "wp_deleted_at"):
    verifier(f"« {col} » est déclarée dans init_db", col in colonnes)

# Le cas fondateur, de bout en bout : la requête qui plantait doit passer.
verifier("la clause de la file « À compléter » s'exécute sur une base neuve",
         conn.execute("SELECT COUNT(*) FROM events_raw WHERE "
                      "(COALESCE(lieu,'')='' AND COALESCE(multi_lieux,0)=0)"
                      ).fetchone()[0] == 0)

# Idempotence : init_db doit pouvoir repasser sur une base déjà migrée.
init_db(conn)
apres = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
verifier("un second passage d'init_db ne casse rien et n'ajoute rien",
         apres == colonnes, str(sorted(apres ^ colonnes)))
conn.close()

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
