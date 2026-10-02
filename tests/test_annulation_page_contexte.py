#!/usr/bin/env python3
"""Fixture : un marqueur d'annulation sur une PAGE se juge dans sa fenêtre.

INCIDENT RÉEL, 19/09 → 01/10/2026 : `audit_annulations` a rendu 6 suspicions, 6 faux
positifs, 0 annulation réelle. Les phrases sont recopiées des pages en cause :
CGV de la billetterie Merz (5694, 5127, 5756, 5981, 6294), « rinviata in caso di forte
maltempo » (5036, 6142, 6209), « Dopo l'annullamento dell'edizione 2025 » (6212).

Deux moitiés, et la seconde est celle qui compte (CLAUDE.md, règle 3 : le 06/08 une
fixture qui ne confirmait que le design est passée au vert sur un portillon faux) :
  A. ce qui doit être ÉCARTÉ — les phrases réelles ci-dessus ;
  B. ce qui doit RESTER signalé, choisi près de la frontière : un report réel dont la
     cause est la météo, un report vers l'année d'après, une annulation avec
     remboursement, et une phrase de CGV qui n'est PAS celle de la boutique.

Lancer : .venv/bin/python -m tests.test_annulation_page_contexte
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.annulation import marqueur_annulation_page as m  # noqa: E402

echecs = 0


def _check(nom, ok, detail=""):
    global echecs
    print(("  ok   " if ok else "  ECHEC"), nom, "" if ok else f"-> {detail}")
    if not ok:
        echecs += 1


print("A. à écarter")
_check("CGV Merz : « ART. 4 ANNULLAMENTO ORDINE »",
       m("Condizioni di vendita\nART. 4 ANNULLAMENTO ORDINE\nL'ordine può essere annullato", 2026) is None)
_check("CGV : « annullamento dell'ordine » sans numéro d'article",
       m("Il cliente può chiedere l'annullamento dell'ordine entro 24 ore.", 2026) is None)
_check("météo conditionnelle : « sarà rinviata in caso di forte maltempo »",
       m("La caccia al tesoro sabato 3 ottobre. In caso di forte maltempo l'escursione sarà rinviata.", 2026) is None)
_check("édition passée : « Dopo l'annullamento dell'edizione 2025 »",
       m("Dopo l'annullamento dell'edizione 2025, la Rowing Regatta è pronta a tornare", 2026) is None)

print("B. à garder (près de la frontière)")
_check("report réel dû à la météo : « rinviato causa maltempo »",
       m("Il concerto di sabato è rinviato causa maltempo.", 2026) == "rinviato")
_check("annulation réelle avec remboursement",
       m("Lo spettacolo è stato annullato. Rimborso dei biglietti presso la biglietteria.", 2026) == "annullato")
_check("report vers l'année d'après : « rinviato al 2027 »",
       m("L'evento è rinviato al 2027.", 2026) == "rinviato")
_check("sans année d'événement connue, le filtre d'année ne s'applique pas",
       m("Dopo l'annullamento dell'edizione 2025, la manifestazione è annullata.", None) == "annullamento")
_check("« art. » dans une autre phrase ne protège pas une vraie annulation",
       m("Come da art. 4 del regolamento comunale. Il festival è annullato.", 2026) == "annullato")
_check("annulation française nue", m("Le festival est annulé.", 2026) == "annule")
_check("un mot sans fenêtre suspecte ne casse pas le texte vide", m("", 2026) is None)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
