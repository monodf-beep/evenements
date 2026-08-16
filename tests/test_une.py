#!/usr/bin/env python3
"""Fixture : les règles de « À LA UNE ». Aucun réseau, aucune base.

D'OÙ ÇA VIENT. Capture d'écran de Franck, 2026-08-17 :

    À LA UNE
    · Bien-être aux Charmettes : pilates dans le jardin   (26/08, visuel générique)
    · Charlie Winston au Théâtre Novarina                 (22/09)
    · Tout est calme dans les hauteurs                    (24/09)

    « pilate en "à la une" ??? les 2 autres, ça fait des semaines qu'ils sont à la
      une […]. À la une il faut des règles pour que ça tourne et que ça joue son
      vrai rôle. »

La section triait sur `as_home_score` — panel + source officielle + visuels. Cette note
mesure LA QUALITÉ DU RENDU, pas l'intérêt, et elle est figée au jour de la rédaction :
un cours de pilates bien illustré bat un festival mal illustré, et rien ne sait qu'on est
à cinq semaines de la date.

LES TROIS CAS QUI COMPTENT, et ce sont les trois de la capture :

  1. le pilates DOIT sortir — par l'intérêt, pas par le rendu (le sien est bon) ;
  2. un concert à cinq semaines NE DOIT PAS être en une, et doit y entrer plus tard :
     c'est ça, « que ça tourne » ;
  3. une fiche sans image propre ne doit pas y être — sa carte afficherait le visuel
     générique du site, et une une qui montre un pictogramme ne montre rien.

⚠️ ET LE CAS QUI DOIT PASSER : un événement imminent, intéressant et bien rendu. Sans
lui, cette fixture ne prouverait que notre capacité à refuser — c'est le défaut du
portillon du 2026-08-06, passé au vert sur un design faux.

Lancer : .venv/bin/python -m tests.test_une
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.une import UNE_HORIZON_JOURS, interet, une_etat, une_now  # noqa: E402

AUJ = date(2026, 8, 17)
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


def _det(rayon=2, spec=1, edition=1, notoriete=2) -> str:
    return json.dumps({"rayonnement": {"points": rayon},
                       "specificite_territoriale": {"points": spec},
                       "edition_tradition": {"points": edition},
                       "notoriete_lieu": {"points": notoriete}})


def _f(**kw) -> dict:
    """Une fiche par défaut ÉLIGIBLE et intéressante : chaque cas ne change qu'une chose."""
    ev = {"enrich_status": "enriched", "home_score": 8.0,
          "enrich_data": json.dumps({"home": {"affiches": "deux"}}),
          "llm_score_detail": _det(),
          "date_event_start": "2026-08-22", "date_event_end": "2026-08-22"}
    ev.update(kw)
    return ev


print("──── LE CAS QUI DOIT PASSER ────")
n, m = une_etat(_f(), AUJ)
_check(f"un événement imminent, intéressant et bien rendu entre en une ({n})",
       n is not None and n > 0, m)
_check("   et son motif dit POURQUOI, pas seulement combien",
       "intérêt" in m and "imminence" in m, m)

print("\n──── 1. le pilates : bien rendu, sans intérêt ────")
pil = _f(llm_score_detail=_det(0, 0, 0, 1), date_event_start="2026-08-26",
         date_event_end="2026-08-26")
n, m = une_etat(pil, AUJ)
_check("il est écarté", n is None, str(n))
_check("   par l'INTÉRÊT, pas par le rendu — c'est la distinction du correctif",
       "intérêt sous le plancher" in m, m)
_check("   et son rendu était pourtant bon (8/10) : la preuve que le rendu ne classe plus",
       pil["home_score"] == 8.0)

print("\n──── 2. la rotation : cinq semaines, c'est trop loin pour une une ────")
concert = _f(date_event_start="2026-09-22", date_event_end="2026-09-22")
n_loin, m_loin = une_etat(concert, AUJ)
_check("à 36 jours, il n'est PAS en une", n_loin is None, str(n_loin))
_check("   et le motif nomme l'horizon", f"horizon {UNE_HORIZON_JOURS}" in m_loin, m_loin)
n_pres, m_pres = une_etat(concert, date(2026, 9, 5))
_check("à 17 jours, il Y ENTRE — la vitrine tourne d'elle-même", n_pres is not None, m_pres)
n_veille, _ = une_etat(concert, date(2026, 9, 18))
_check("   et il monte encore en approchant", (n_veille or 0) > (n_pres or 0),
       f"{n_pres} → {n_veille}")
_check("l'événement PASSÉ sort (règle 5)",
       une_now(concert, date(2026, 9, 23)) is None)

print("\n──── 3. pas d'image propre, pas de une ────")
n, m = une_etat(_f(enrich_data=json.dumps({"home": {"affiches": "aucune"}})), AUJ)
_check("écartée", n is None, str(n))
_check("   et le motif dit ce que le visiteur VERRAIT à la place",
       "visuel générique" in m, m)
_check("une photo officielle suffit, elle — on n'exige pas l'affiche",
       une_now(_f(enrich_data=json.dumps({"home": {"affiches": "photo officielle"}})),
               AUJ) is not None)

print("\n──── les portillons d'éligibilité ────")
_check("jamais rédigée → jamais en une (règle Franck du 2026-07-30)",
       une_now(_f(enrich_status=""), AUJ) is None)
_check("annulée → jamais en une, même parfaite",
       une_now(_f(annule_le="2026-08-10"), AUJ) is None)
_check("rendu insuffisant → écartée", une_now(_f(home_score=3.0), AUJ) is None)

print("\n──── ce qui ne se devine pas ────")
_check("non évaluée → None, pas 0 — on ne classe pas dernier ce qu'on n'a pas mesuré",
       interet({"llm_score_detail": ""}) is None)
_check("   et la fiche est écartée, pas mise en queue",
       une_now(_f(llm_score_detail=""), AUJ) is None)
n, m = une_etat(_f(date_event_start="", date_event_end=""), AUJ)
_check("sans date → gardée avec l'intérêt seul (donnée manquante ≠ événement fini)",
       n is not None and "aucun bonus" in m, f"{n} · {m}")
_check("un llm_score_detail ABÎMÉ ne fait pas tomber la vitrine",
       une_now(_f(llm_score_detail="{pas du json"), AUJ) is None)

print("\n──── la langue n'entre PAS dans la une ────")
# `deplacement_score` inclut `accessibilite_langue` : ce critère mesure la traversée d'une
# frontière. Sur la home FRANÇAISE, lue par un francophone, une pièce en français n'a
# aucune barrière — l'y appliquer déclasserait tout le théâtre pour une raison qui ne
# concerne pas ce lecteur-là.
theatre = _f(llm_categorie="Spectacle vivant")
_check("une pièce de théâtre n'est pas pénalisée en une",
       une_now(theatre, AUJ) is not None, str(une_etat(theatre, AUJ)))
_check("   et l'intérêt ne dépend pas de la catégorie",
       interet(theatre) == interet(_f(llm_categorie="Gastronomie & Sagre")))

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
