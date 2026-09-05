#!/usr/bin/env python3
"""Fixture : le détail des coûts API — par étape, et ce qui fait vraiment la facture.

Franck, 2026-08-11 : « il faudrait que tu expliques le détail des coûts ». Le tableau de
bord montrait 218 $ répartis sur trois modèles, ce qui ne se pilote pas : savoir qu'on
dépense sur claude-sonnet-5 ne dit pas s'il faut réduire la rédaction, la traduction ou la
datation.

CE QUE LA FIXTURE SURVEILLE, et pourquoi c'est le nerf de l'affaire :

  1. l'agrégat PAR ÉTAPE existe et additionne juste — chaque appel porte son étiquette
     depuis le début, elle n'était simplement jamais lue ;
  2. une étiquette VIDE ne disparaît pas : un poste de dépense invisible ne sera jamais
     réduit ;
  3. `part_entree` dit la vérité contre-intuitive de cette facture — l'entrée coûte cinq
     fois moins cher au jeton que la sortie et pèse pourtant les deux tiers, parce qu'on en
     envoie dix fois plus ;
  4. et rien de tout ça ne recalcule le coût : le total reste celui qui a été additionné
     appel par appel au moment de l'appel. On décompose, on ne réestime pas — sinon deux
     chiffres portant le même nom finiraient par diverger.

Lancer : .venv/bin/python -m tests.test_couts_detail
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import usage  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


tmp = Path(tempfile.mkdtemp(prefix="fixture-couts-"))
usage.USAGE_FILE = tmp / "api_usage.jsonl"

# Trois étapes, des volumes très différents — le cas réel : la rédaction envoie beaucoup,
# l'évaluation peu mais souvent.
LIGNES = [
    ("claude-sonnet-5", 20000, 2000, "rédaction"),
    ("claude-sonnet-5", 20000, 2000, "rédaction"),
    ("claude-sonnet-5", 4000, 1500, "traduction"),
    ("claude-haiku-4-5", 800, 100, "évaluation"),
    ("claude-haiku-4-5", 800, 100, "évaluation"),
    ("claude-haiku-4-5", 800, 100, ""),          # étiquette VIDE, volontairement
]
for model, i, o, label in LIGNES:
    usage.record(model, i, o, label=label)

s = usage.summarize()
tot = s["total"]
lab = tot["by_label"]

print("──── 1. l'agrégat par étape ────")
_check("les trois étapes sont là, plus le non-étiqueté",
       set(lab) == {"rédaction", "traduction", "évaluation", "(non étiqueté)"}, sorted(lab))
_check("une étiquette VIDE devient « (non étiqueté) », elle ne disparaît pas",
       lab["(non étiqueté)"]["calls"] == 1, lab.get("(non étiqueté)"))
_check("les appels sont bien comptés par étape",
       lab["rédaction"]["calls"] == 2 and lab["évaluation"]["calls"] == 2, lab)
_check("l'entrée est additionnée par étape",
       lab["rédaction"]["in"] == 40000, lab["rédaction"])
_check("la somme des étapes fait le total, au centime",
       abs(sum(d["cost"] for d in lab.values()) - tot["cost"]) < 1e-6,
       (sum(d["cost"] for d in lab.values()), tot["cost"]))
_check("les appels aussi", sum(d["calls"] for d in lab.values()) == tot["calls"])

print("\n──── 2. par semaine, le détail suit ────")
sem = list(s["weeks"].values())[0]
_check("chaque semaine porte son propre détail par étape", "by_label" in sem, sem.keys())

print("\n──── 3. l'explication, c'est-à-dire le levier ────")
e = usage.explique(tot)
_check("le nombre d'appels est repris tel quel", e["appels"] == 6, e)
_check("le coût par appel est le total divisé par les appels",
       abs(e["cout_par_appel"] - tot["cost"] / 6) < 1e-9, e)
_check("l'entrée par appel est donnée", e["entree_par_appel"] == round(46400 / 6), e)
_check("le rapport entrée/sortie est donné", e["ratio"] == round(46400 / 5800, 1), e)
_check("la part de l'entrée dans la facture est un pourcentage plausible",
       0 < e["part_entree"] < 100, e["part_entree"])
# LE POINT LE PLUS IMPORTANT : on DÉCOMPOSE, on ne RÉESTIME pas. Deux chiffres portant le
# même nom et calculés deux fois finissent toujours par diverger — c'est la faute du
# 2026-08-11 (« 1611 datés » comptés sur une liste d'étiquettes au lieu de la donnée).
_check("le coût affiché reste CELUI QUI A ÉTÉ ADDITIONNÉ appel par appel",
       e["cout"] == tot["cost"], (e["cout"], tot["cost"]))

print("\n──── 3 bis. la fenêtre de dates ────")
# « mets la possibilité de voir par date, comme ça je pourrai comparer les coûts ».
# Comparer suppose de découper — et un cumul depuis toujours ne dit pas si une correction
# d'hier a servi.
import json as _json
brut = [_json.loads(l) for l in usage.USAGE_FILE.read_text(encoding="utf-8").splitlines()]
jour = brut[0]["ts"][:10]
_check("le journal est agrégé PAR JOUR", jour in usage.summarize()["jours"],
       list(usage.summarize()["jours"]))
_check("une fenêtre qui contient tout rend le total complet",
       usage.summarize(jour, jour)["total"]["calls"] == 6,
       usage.summarize(jour, jour)["total"]["calls"])
_check("une fenêtre HORS période rend zéro appel, pas une erreur",
       usage.summarize("2020-01-01", "2020-01-02")["total"]["calls"] == 0)
_check("et son détail par étape est vide, pas absent",
       usage.summarize("2020-01-01", "2020-01-02")["total"]["by_label"] == {})
_check("chaque jour porte son poste dominant",
       "rédaction" in usage.summarize()["jours"][jour]["by_label"],
       usage.summarize()["jours"][jour]["by_label"])
_check("les jours sont rendus du plus RÉCENT au plus ancien",
       list(usage.summarize()["jours"]) == sorted(usage.summarize()["jours"], reverse=True))

print("\n──── 4. le cas vide ne fabrique pas de faux zéro ────")
usage.USAGE_FILE = tmp / "vide.jsonl"
v = usage.summarize()["total"]
ev = usage.explique(v)
_check("aucun appel : la part d'entrée vaut None, pas 0 %", ev["part_entree"] is None, ev)
_check("et le coût par appel ne divise pas par zéro", ev["cout_par_appel"] == 0.0, ev)

print(f"\n{'TOUT PASSE' if not echecs else str(echecs) + ' ÉCHEC(S)'}")
sys.exit(1 if echecs else 0)
