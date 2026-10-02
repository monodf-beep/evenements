#!/usr/bin/env python3
"""Fixture : la datation LLM n'a plus le droit d'inventer un quantième (`dates.py`).

LE DÉFAUT. Fiche 845, mesurée le 2026-08-13 : la description disait « se déroulera en juin
et juillet », rien d'autre. Le modèle a rendu 2026-06-01 → 2026-07-31 — le premier et le
dernier jour des deux mois. Personne n'a jamais écrit ces bornes ; la fiche est partie en
ligne avec elles.

CE QUE CETTE FIXTURE DOIT PROUVER, ET DANS LES DEUX SENS. Un portillon qui n'a que des cas
qui lui donnent raison ne prouve rien (CLAUDE.md règle 3, écrite après celui du 06/08 qui
est passé au vert en refusant des traductions correctes). Les cas qui doivent PASSER sont
donc choisis à la frontière exacte :

  • un événement qui va RÉELLEMENT du 1er au 31 août — même signature de dates, mais la
    matière écrit les quantièmes. Il doit passer ;
  • un quantième en toutes lettres (« dal primo agosto »), fréquent en italien ;
  • une plage qui n'est pas une borne de mois, quelle que soit la matière ;
  • une date ISO ou numérique dans la matière.

Lancer : .venv/bin/python -m tests.test_quantieme_invente
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.dates import _quantieme_invente  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── 1. CE QUI DOIT ÊTRE REFUSÉ ────")
_check("845 : « en juin et juillet » → 01/06-31/07 est une borne fabriquée",
       _quantieme_invente("2026-06-01", "2026-07-31",
                          "Le festival se déroulera en juin et juillet dans plusieurs "
                          "communes de la vallée."))
_check("un seul mois : « per tutto agosto » → 01/08-31/08 fabriqué",
       _quantieme_invente("2026-08-01", "2026-08-31",
                          "La mostra resta aperta per tutto agosto al museo civico."))
_check("février court : 01/02-28/02 sur une matière sans quantième",
       _quantieme_invente("2026-02-01", "2026-02-28",
                          "Programmazione di febbraio, tutti i weekend."))

print("\n──── 2. LES CAS QUI DOIVENT PASSER ────")
_check("un festival qui va VRAIMENT du 1er au 31 août — les quantièmes sont écrits",
       not _quantieme_invente("2026-08-01", "2026-08-31",
                              "Exposition ouverte du 1er août au 31 août 2026."))
_check("le quantième en toutes lettres : « dal primo agosto »",
       not _quantieme_invente("2026-08-01", "2026-08-31",
                              "Aperta dal primo agosto fino a fine mese."))
_check("une date ISO dans la matière suffit à prouver qu'on n'a rien inventé",
       not _quantieme_invente("2026-08-01", "2026-08-31",
                              "Période : 2026-08-01 → 2026-08-31, entrée libre."))
_check("une date numérique aussi (05/07/2026)",
       not _quantieme_invente("2026-07-01", "2026-07-31",
                              "Ouverture le 01/07/2026, clôture le 31/07/2026."))
_check("une plage ORDINAIRE n'est jamais concernée, même sans quantième lisible",
       not _quantieme_invente("2026-07-14", "2026-07-18",
                              "Le festival revient cet été à Saint-Julien."))
_check("un début au 1er mais une fin quelconque → pas la signature du défaut",
       not _quantieme_invente("2026-08-01", "2026-08-17", "Rien de lisible ici."))
_check("une fin au dernier jour mais un début quelconque → non plus",
       not _quantieme_invente("2026-08-12", "2026-08-31", "Rien de lisible ici."))
_check("un seul jour (début = fin) n'est pas une borne de mois",
       not _quantieme_invente("2026-08-01", "2026-08-01", "Soirée d'ouverture."))
_check("des dates illisibles ne font pas planter le portillon",
       not _quantieme_invente("pas-une-date", "", "n'importe quoi"))

print(f"\n{'TOUT PASSE' if not echecs else str(echecs) + ' ÉCHEC(S)'}")
sys.exit(1 if echecs else 0)
