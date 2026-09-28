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

# Tout ALTER TABLE du dépôt. TROIS FORMES à reconnaître, et c'est le point qui a failli
# tout faire rater :
#   1. littérale          →  ADD COLUMN multi_lieux TEXT
#   2. variable de module →  ADD COLUMN {_COL_INFOS}   (moisson_officielle)
#   3. variable de BOUCLE →  ADD COLUMN {col}          (la migration d'init_db elle-même)
# La première version ne lisait que la forme 1. Elle a donc laissé filer
# `infos_pratiques`, posée en forme 2, LE JOUR MÊME où on l'écrivait. Une fois corrigée
# pour la forme 2, elle criait au loup sur onze boucles parfaitement saines.
#
# D'où le passage à l'AST plutôt qu'à une nième expression régulière : on cherche les
# f-strings qui portent l'ordre SQL, et on résout le nom là où il est réellement défini
# — affectation de module, ou littéraux de l'itérable de la boucle englobante. Empiler
# des regex pour rattraper chaque forme d'écriture, c'est fabriquer le détecteur borgne
# que cette fixture est censée remplacer.
import ast as _ast

_ORDRE = "ALTER TABLE events_raw ADD COLUMN "


def _noms_de_colonnes(arbre, texte):
    """{colonne: 'littéral'|'variable'} pour un fichier, ou lève ce qu'elle ne sait pas lire."""
    trouves, illisibles = set(), []

    def _fstring_ajoute(noeud):
        """Le nœud est-il une f-string portant l'ordre, et quelle variable suit ?"""
        if not isinstance(noeud, _ast.JoinedStr):
            return None
        for i, part in enumerate(noeud.values):
            if (isinstance(part, _ast.Constant) and isinstance(part.value, str)
                    and part.value.rstrip().endswith(_ORDRE.strip())):
                suite = noeud.values[i + 1] if i + 1 < len(noeud.values) else None
                if isinstance(suite, _ast.FormattedValue) and isinstance(suite.value, _ast.Name):
                    return suite.value.id
        return None

    # Les affectations de module : _COL_INFOS = "infos_pratiques".
    constantes = {n.targets[0].id: n.value.value
                  for n in _ast.walk(arbre)
                  if isinstance(n, _ast.Assign) and len(n.targets) == 1
                  and isinstance(n.targets[0], _ast.Name)
                  and isinstance(n.value, _ast.Constant)
                  and isinstance(n.value.value, str)}

    # Les boucles : for col, decl in ((...),(...)) — on prend les littéraux de l'itérable.
    boucles = []
    for n in _ast.walk(arbre):
        if isinstance(n, _ast.For):
            noms = [x.id for x in _ast.walk(n.target) if isinstance(x, _ast.Name)]
            littéraux = [c.value for c in _ast.walk(n.iter)
                         if isinstance(c, _ast.Constant) and isinstance(c.value, str)]
            boucles.append((noms, littéraux, n))

    for noeud in _ast.walk(arbre):
        var = _fstring_ajoute(noeud)
        if var is None:
            continue
        if var in constantes:
            trouves.add(constantes[var])
            continue
        # Cherche la boucle la plus proche qui lie cette variable.
        depuis_boucle = None
        for noms, littéraux, boucle in boucles:
            if var in noms and any(n is noeud for n in _ast.walk(boucle)):
                depuis_boucle = littéraux
                break
        if depuis_boucle is None:
            illisibles.append(var)
        else:
            # Les littéraux d'une migration alternent nom et déclaration SQL : on ne
            # garde que ce qui ressemble à un nom de colonne.
            trouves |= {l for l in depuis_boucle
                        if l and l.islower() and " " not in l and not l.isupper()}

    for m in __import__("re").finditer(
            _ORDRE.replace(" ", r"\s") + r"([a-z_][a-z0-9_]*)", texte):
        trouves.add(m.group(1))
    return trouves, illisibles


ajoutees, non_resolus = {}, []
for py in list(ROOT.glob("scripts/*.py")) + list(ROOT.glob("app/*.py")) + \
        list(ROOT.glob("utils/*.py")):
    texte = py.read_text(encoding="utf-8")
    if _ORDRE not in texte:
        continue
    noms, illisibles = _noms_de_colonnes(_ast.parse(texte), texte)
    for n in noms:
        ajoutees.setdefault(n, []).append(py.name)
    non_resolus += [f"{py.name}:{{{v}}}" for v in illisibles]

verifier("aucun ADD COLUMN ne reste illisible pour cette fixture",
         not non_resolus,
         "nom de colonne non résolu : " + ", ".join(non_resolus))

verifier("des ALTER TABLE existent bien dans le dépôt (sinon la fixture ne prouve rien)",
         len(ajoutees) >= 5, str(len(ajoutees)))

orphelines = sorted(c for c in ajoutees if c not in colonnes)
verifier("toute colonne ajoutée ailleurs existe aussi sur une base neuve",
         not orphelines,
         "; ".join(f"{c} (ajoutée par {', '.join(ajoutees[c])})" for c in orphelines))

# Les six du rattrapage, nommées : si l'une repart, on veut savoir laquelle.
for col in ("multi_lieux", "mail_corps", "organisateur_byline", "seo_pushed_at",
            "unmerge_data", "worth_trip", "annule_le", "wp_deleted_at",
            # Posée via une f-string, donc invisible à la première version d'ici.
            "infos_pratiques"):
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
