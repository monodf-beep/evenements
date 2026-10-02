#!/usr/bin/env python3
"""Fixture : l'intérêt « local » de la une, et l'audit qui le compare nom par nom.

⚠️ BASE JETABLE — jamais data/events.db. Aucun appel de modèle.

D'OÙ ÇA VIENT (2026-09-29). Franck : « à la une, si je suis en Savoie, c'est un événement
qui est à côté — pas forcément une histoire de trois heures de route ». La une notait
l'intérêt avec les critères de « Ça vaut le déplacement » ; Mariam à Bonlieu Scène
nationale y valait 3/10. `utils.une.UNE_FORMULE=locale` prend la note d'évaluation telle
quelle. Défaut inchangé tant que Franck n'a pas lu l'audit.

CE QU'ELLE SURVEILLE :
  1. le DÉFAUT est « combinee » (la meilleure des deux notes), choisi après lecture de
     l'audit nom par nom ; « deplacement » reste disponible et inchangé ;
  2. le cas Mariam (grande scène, organisateur institutionnel, sans ancrage local) :
     dehors en « deplacement », DEDANS en « locale » ;
  3. ⚠️ le cas qui doit RESTER DEHORS dans les deux formules : le pilates (évalué 4) ;
  4. ⚠️ le cas qui doit PASSER près de la frontière : évalué pile 6 → dedans ;
  5. jamais évalué → dehors (« pas mesuré » n'est pas « digne ») ;
  6. les AUTRES portillons tiennent en « locale » (sans image → dehors) ;
  7. l'audit nomme ce qui ENTRE, et ne touche pas à la formule en service.

Lancer : .venv/bin/python -m tests.test_une_formule_locale
"""
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TMP = Path(tempfile.mkdtemp())
os.environ["DB_PATH"] = str(TMP / "fixture.db")
os.environ.pop("UNE_FORMULE", None)

import utils.une as U  # noqa: E402

echecs = 0


def _check(nom, ok, detail=""):
    global echecs
    print(("  ✓ " if ok else "  ✗ ") + nom + ("" if ok else f"\n      → {detail}"))
    if not ok:
        echecs += 1


def _detail(lieu, orga, trad, ray, spec):
    return json.dumps({"notoriete_lieu": {"points": lieu},
                       "organisateur_moyens": {"points": orga},
                       "edition_tradition": {"points": trad},
                       "rayonnement": {"points": ray},
                       "specificite_territoriale": {"points": spec}})


J = (date.today() + timedelta(days=4)).isoformat()


def fiche(titre, llm, detail, image="https://ex/a.jpg", terr="Savoie"):
    return {"title": titre, "llm_score": llm, "llm_score_detail": detail,
            "enrich_status": "enriched", "url_image": image, "home_score": 8.1,
            "date_event_start": J, "date_event_end": J, "territoire": terr}


MARIAM = fiche("Mariam chante Amadou & Mariam", 7, _detail(3, 2, 0, 1, 1 - 1))
PILATES = fiche("Bien-être aux Charmettes : Pilates", 4, _detail(1, 1, 1, 0, 1))
PILE6 = fiche("Évalué pile 6", 6, _detail(2, 1, 1, 1, 1))
JAMAIS = fiche("Jamais évalué", None, None)
# Le cas qui a fait choisir « combinee » : un festival ANCRÉ, bien noté en déplacement
# (rayonnement 2, spécificité 1, tradition 1 → 8) mais évalué 4 au total. « locale » le
# faisait SORTIR (Festival des Jardins Alpestres, Musicastelle) ; il doit rester.
JARDINS = fiche("Festival des Jardins Alpestres", 4, _detail(0, 0, 1, 2, 1))
SANS_IMAGE = fiche("Grand concert sans image", 9, _detail(3, 2, 2, 2, 0), image="")


def dedans(ev):
    return U.une_etat(ev)[0] is not None


print("1. Le défaut, et l'ancienne formule")
_check("UNE_FORMULE vaut « combinee » sans variable d'environnement",
       U.UNE_FORMULE == "combinee", U.UNE_FORMULE)
U.UNE_FORMULE = "deplacement"
_check("ancienne formule : Mariam DEHORS (intérêt 3)", not dedans(MARIAM), U.une_etat(MARIAM))
_check("ancienne formule : Jardins DEDANS", dedans(JARDINS), U.une_etat(JARDINS))

print("\n2. Formule locale")
U.UNE_FORMULE = "locale"
_check("Mariam (grande scène, sans ancrage local) : DEDANS", dedans(MARIAM), U.une_etat(MARIAM))
_check("⚠️ pilates (évalué 4) : reste DEHORS", not dedans(PILATES), U.une_etat(PILATES))
_check("⚠️ évalué pile 6 : DEDANS (le cas qui doit passer)", dedans(PILE6), U.une_etat(PILE6))
_check("jamais évalué : DEHORS", not dedans(JAMAIS), U.une_etat(JAMAIS))
_check("évalué 9 mais sans image : DEHORS (les autres portillons tiennent)",
       not dedans(SANS_IMAGE), U.une_etat(SANS_IMAGE))
_check("formule locale seule : Jardins SORT (c'est pourquoi on ne l'a pas retenue)",
       not dedans(JARDINS), U.une_etat(JARDINS))

print("\n3. Formule combinée (en service)")
U.UNE_FORMULE = "combinee"
_check("Mariam : DEDANS", dedans(MARIAM), U.une_etat(MARIAM))
_check("⚠️ Jardins : RESTE DEDANS (le cas qui a décidé)", dedans(JARDINS), U.une_etat(JARDINS))
_check("⚠️ pilates : reste DEHORS", not dedans(PILATES), U.une_etat(PILATES))
_check("jamais évalué, ni détail ni note : DEHORS", not dedans(JAMAIS), U.une_etat(JAMAIS))

print("\n4. L'audit nomme ce qui entre, sans basculer la formule")
from scripts.scraper_events import init_db  # noqa: E402
conn = sqlite3.connect(TMP / "fixture.db")
init_db(conn)
cols = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
besoin = {"llm_score_detail": "TEXT", "enrich_status": "TEXT", "home_score": "REAL",
          "date_event_start": "TEXT", "date_event_end": "TEXT", "wp_post_id_as": "INTEGER",
          "recurring": "INTEGER DEFAULT 0", "duplicate_of": "INTEGER",
          "translation_of": "INTEGER", "translated_lang": "TEXT"}
for c, d in besoin.items():
    if c not in cols:
        conn.execute(f"ALTER TABLE events_raw ADD COLUMN {c} {d}")
for i, ev in enumerate((MARIAM, PILATES, PILE6), 1):
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, url_image, territoire, llm_score,"
        " llm_score_detail, enrich_status, home_score, date_event_start, date_event_end,"
        " wp_post_id_as, statut) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (i, ev["title"], f"https://ex/{i}", ev["url_image"], ev["territoire"], ev["llm_score"],
         ev["llm_score_detail"], "enriched", 8.1, J, J, 100 + i, "published_sub"))
conn.commit()
conn.close()

from scripts import audit_une  # noqa: E402
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    audit_une.main([])
sortie = buf.getvalue()
_check("Mariam listée « ➕ ENTRE »",
       any("ENTRE" in l and "Mariam" in l for l in sortie.splitlines()), sortie[-1500:])
_check("le pilates n'est listé nulle part comme entrant",
       not any("ENTRE" in l and "Pilates" in l for l in sortie.splitlines()))
_check("après l'audit, la formule en service est toujours « combinee »",
       U.UNE_FORMULE == "combinee", U.UNE_FORMULE)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
