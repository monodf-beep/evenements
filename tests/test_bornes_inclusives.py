#!/usr/bin/env python3
"""Fixture : la borne de fin est INCLUSIVE, et elle l'a toujours été.

POURQUOI CETTE FIXTURE EXISTE. Le brief du 2026-08-12 (`docs/GARDE_FOUS_DATES_LIEUX_SOURCES.md`,
cause commune n° 3) affirme que « la borne de fin est traitée comme exclusive, sur les deux
cas multi-jours vérifiés ». C'est faux, et c'est le grief le plus dangereux du lot : appliqué,
il aurait ajouté un jour à la fin de TOUTES les fiches multi-jours du corpus — plusieurs
centaines, dont des dizaines en ligne.

Le raisonnement du brief était pourtant solide en apparence : deux cas sur deux, la fiche
s'arrêtait un jour avant la page officielle. « Deux sur deux, ce n'est plus un accident. »
Sauf que les deux fiches n'ont jamais été datées depuis la page officielle :

  • 2289 « Guitare en scène » — la page dit « du 14 au 18 juillet », mais NOTRE matière est
    la description collectée sur 74.agendaculturel.fr, qui écrit « du 14 au 17 juillet ».
    `parse_dates` a lu 17 parce que l'agrégateur écrit 17 ;
  • 2265 « Festa di San Savino » — notre source n'est pas comune.ivrea.to.it mais une
    newsletter de Turismo Torino, et la fiche porte `date_source='page'`.

Le défaut réel n'est donc pas un décalage d'un jour dans le code : c'est qu'on date depuis
un agrégateur sans jamais confronter la page officielle. Le remède est le garde-fou (c)
— `utils/confronter.py` —, pas une addition d'un jour.

CE QUE CETTE FIXTURE PROTÈGE : que personne, en relisant le brief dans six mois, ne
« corrige » une borne qui est juste. Les deux textes officiels cités y figurent tels quels,
avec le résultat qu'ils DOIVENT produire.

Lancer : .venv/bin/python -m tests.test_bornes_inclusives
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.dates import parse_dates  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


REF = date(2026, 7, 20)   # date de collecte réelle des deux fiches citées


print("──── 1. les deux textes officiels du brief, mot pour mot ────")
# Ce sont les citations EXACTES de docs/GARDE_FOUS_DATES_LIEUX_SOURCES.md § 2289 et § 2265.
_check("« du 14 au 18 Juillet 2026 » → fin au 18, pas au 17",
       parse_dates("Festival Guitare en scène, du 14 au 18 Juillet 2026", REF)[:2]
       == ("2026-07-14", "2026-07-18"),
       parse_dates("Festival Guitare en scène, du 14 au 18 Juillet 2026", REF))
_check("« Dal 4 all'8 luglio 2026 » → fin au 8, pas au 7",
       parse_dates("Festa Patronale di San Savino. Dal 4 all'8 luglio 2026", REF)[:2]
       == ("2026-07-04", "2026-07-08"),
       parse_dates("Festa Patronale di San Savino. Dal 4 all'8 luglio 2026", REF))

print("\n──── 2. et la matière que le pipeline a RÉELLEMENT eue ────")
# La démonstration que le décalage vient de la source, pas du code : sur le texte de
# l'agrégateur, le même code rend 17 — fidèlement.
_check("sur le texte de l'agrégateur (« du 14 au 17 »), le code rend 17 : il transcrit",
       parse_dates("Le Festival Guitare en scène 2026 revient du 14 au 17 juillet "
                   "à Saint-Julien-en-Genevois.", REF)[:2]
       == ("2026-07-14", "2026-07-17"))

print("\n──── 3. l'inclusivité sur toutes les formes de plage ────")
_check("plage inter-mois FR « du 30 juin au 3 juillet 2026 »",
       parse_dates("du 30 juin au 3 juillet 2026", REF)[:2]
       == ("2026-06-30", "2026-07-03"))
_check("plage inter-mois IT « dal 30 giugno al 3 luglio 2026 »",
       parse_dates("dal 30 giugno al 3 luglio 2026", REF)[:2]
       == ("2026-06-30", "2026-07-03"))
_check("plage ISO explicite 2026-07-14 → 2026-07-18",
       parse_dates("Du 2026-07-14 au 2026-07-18", REF)[:2]
       == ("2026-07-14", "2026-07-18"))
_check("« 5 e 6 luglio » : deux jours, les DEUX comptent",
       parse_dates("Sagra: 5 e 6 luglio 2026", REF)[:2]
       == ("2026-07-05", "2026-07-06"))
_check("date simple : début = fin, la journée compte entière",
       parse_dates("Concert le 9 juillet 2026", REF)[:2]
       == ("2026-07-09", "2026-07-09"))
_check("« jusqu'au 30 août 2026 » : le 30 est DANS l'événement",
       parse_dates("Exposition jusqu'au 30 août 2026", REF)[1] == "2026-08-30")

print("\n──── 4. les cas-frontière, ceux qui doivent PASSER ────")
# CLAUDE.md règle 3 : « la fixture doit contenir un cas qui doit PASSER, choisi près de la
# frontière ». Une plage d'un seul jour et une plage à cheval sur un changement d'année sont
# exactement les endroits où un correctif « +1 jour » se serait vu en dernier.
_check("plage dégénérée « du 9 au 9 juillet » reste un seul jour",
       parse_dates("du 9 au 9 juillet 2026", REF)[:2]
       == ("2026-07-09", "2026-07-09"))
_check("plage à cheval sur l'année « du 28 décembre 2026 au 3 janvier 2027 »",
       parse_dates("du 28 décembre 2026 au 3 janvier 2027", REF)[:2]
       == ("2026-12-28", "2027-01-03"))
_check("dernier jour du mois : « du 29 au 31 juillet » ne déborde pas en août",
       parse_dates("du 29 au 31 juillet 2026", REF)[:2]
       == ("2026-07-29", "2026-07-31"))
_check("le 28 février d'une année bissextile n'avance pas au 29",
       parse_dates("du 26 au 28 février 2028", REF)[:2]
       == ("2028-02-26", "2028-02-28"))

print(f"\n{'TOUT PASSE' if not echecs else str(echecs) + ' ÉCHEC(S)'}")
sys.exit(1 if echecs else 0)
