#!/usr/bin/env python3
"""Fixture : la TENDANCE des rapports WordPress (scripts/rapports_wordpress).

D'OÙ ÇA VIENT — Franck, 2026-08-17 : « J'aimerais que les messages slack d'erreur soient
de moins en moins. » Un rapport qui affiche « 18 points » ne dit pas s'il y en avait 25
hier ou 12 : sans comparaison, personne ne sait si le dispositif s'assainit, et une file
qui stagne finit par ne plus être lue du tout.

CE QUE LA FIXTURE ÉPROUVE, et pourquoi ces cas-là :

  • la BAISSE est nommée (c'est la demande, donc le cas qui doit passer) ;
  • la HAUSSE est nommée aussi, et en majuscules — un dispositif qui ne sait annoncer que
    les bonnes nouvelles ne sert à rien ;
  • le PREMIER RELEVÉ le dit au lieu de laisser croire à une baisse. C'est la leçon du
    2026-08-11 : « un zéro ne dit pas s'il vient d'un échec ou d'une absence de cas » ;
  • un nombre STABLE depuis cinq relevés déclenche la phrase qui compte vraiment — ce ne
    sont plus des alertes, c'est une décision en attente. Sans elle, la file se contente
    d'exister ;
  • une série TRONQUÉE à sa fenêtre (30 relevés) ne perd pas le jour courant.

Lancer : .venv/bin/python -m tests.test_tendance_wordpress
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.rapports_wordpress import (  # noqa: E402
    _HISTO_JOURS, cle_rapport, compter_points, tendance,
)

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


RAPPORT = (
    ":shield: *Garde-fous 2 : panel, formes, lieux*\n"
    "*verdict revise sans motif* : 8 -> 6373, 6433\n"
    "*corps finissant par une troncature d agregateur* : 1 -> 2317\n"
    "_Perimetre : evenements encore devant nous. 12 passe(s) ecarte(s)._"
)

# ── Ce qu'on compte, et ce qu'on ne compte pas ──────────────────────────────────
verifier("le titre sert de clé, sans emoji ni gras",
         cle_rapport(RAPPORT) == "garde-fous 2 : panel, formes, lieux",
         cle_rapport(RAPPORT))
verifier("deux points comptés : ni le titre, ni la mention de périmètre",
         compter_points(RAPPORT) == 2, str(compter_points(RAPPORT)))

# ── Premier relevé : ne pas faire passer une absence pour un progrès ────────────
h = {}
p = tendance("audit", 18, h, "2026-08-17")
verifier("le premier relevé s'annonce comme tel", "Premier relevé" in p, p)
verifier("il n'annonce aucune baisse", "baisse" not in p, p)
verifier("le jour est enregistré", h["audit"]["2026-08-17"] == 18)

# ── LE CAS QUI DOIT PASSER : une baisse réelle est nommée ───────────────────────
h = {"audit": {"2026-08-10": 38, "2026-08-16": 25}}
p = tendance("audit", 18, h, "2026-08-17")
verifier("une baisse est nommée « en baisse »", "en baisse" in p, p)
verifier("elle cite le relevé précédent", "25" in p and "2026-08-16" in p, p)
verifier("elle cite le début de la série", "38" in p, p)

# ── La hausse aussi, et elle ne se fait pas discrète ────────────────────────────
h = {"audit": {"2026-08-16": 12}}
p = tendance("audit", 20, h, "2026-08-17")
verifier("une hausse est nommée, en majuscules", "EN HAUSSE" in p, p)

# ── Ce qui ne bouge pas est le vrai sujet ───────────────────────────────────────
h = {"audit": {f"2026-08-{j:02d}": 9 for j in range(10, 17)}}
p = tendance("audit", 9, h, "2026-08-17")
verifier("un nombre inchangé est dit inchangé", "inchangé" in p, p)
verifier("cinq relevés identiques déclenchent « décision en attente »",
         "décision en attente" in p, p)

# …mais pas sur un zéro : rien à décider quand il n'y a rien.
h = {"audit": {f"2026-08-{j:02d}": 0 for j in range(10, 17)}}
p = tendance("audit", 0, h, "2026-08-17")
verifier("un zéro stable ne réclame aucune décision",
         "décision en attente" not in p, p)

# ── La fenêtre glissante ne mange pas le jour courant ───────────────────────────
h = {"audit": {f"2026-{(m // 30) + 1:02d}-{(m % 30) + 1:02d}": m for m in range(45)}}
tendance("audit", 7, h, "2026-12-31")
verifier(f"la série est bornée à {_HISTO_JOURS} relevés",
         len(h["audit"]) == _HISTO_JOURS, str(len(h["audit"])))
verifier("le relevé du jour survit à la troncature",
         h["audit"].get("2026-12-31") == 7)

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
