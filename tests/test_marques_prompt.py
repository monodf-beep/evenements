#!/usr/bin/env python3
"""Fixture : la règle « marques et partenaires » est bien dans ce qui PART au rédacteur.

D'OÙ ÇA VIENT. Franck, 2026-09-04, sur /evenement/carmagnola-la-fiera-nazionale-del-peperone… :
« c'est quoi CUKI ? une marque non ? alors il faut pas la mettre. mais quand on parle de
Ferrari au forum de l'automobile c'est bien une marque aussi ». La règle retenue : une
marque reste si elle EST le sujet (ce que le visiteur vient voir), s'efface si c'est un
crédit de sponsoring recopié du communiqué. La fiche en ligne a été corrigée à la main le
jour même ; cette fixture garantit que les PROCHAINES fiches reçoivent la consigne.

CE QU'ELLE VÉRIFIE : le prompt RENDU (pas le fichier source — même leçon que
test_vocabulaire le 04/09 : un contrôle sur le source ne prouve rien sur ce qui part).
  1. la consigne est présente, avec les deux exemples qui la bornent (Ferrari gardé,
     CUKI omis) — sans le cas qui doit PASSER (Ferrari), on ne prouverait qu'une
     interdiction, et le rédacteur effacerait aussi les marques qui sont le sujet ;
  2. elle donne le GESTE (garder le fait, omettre le nom), pas seulement l'interdit ;
  3. le placeholder du vocabulaire est toujours rendu (l'insertion n'a pas cassé .format).

Lancer : .venv/bin/python -m tests.test_marques_prompt
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.vocabulaire import consigne_prompt          # noqa: E402
import scripts.enrich as _enrich                       # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


rendu = _enrich.ENRICH_PROMPT.format(
    title="t", dates="d", lieu="l", territoire="terr", organisateur="org",
    categorie="cat", material="mat", vocabulaire_interdit=consigne_prompt("fr"))

print("──── la règle « marques » est dans le prompt RENDU ────")
_check("la consigne MARQUES ET PARTENAIRES est présente", "MARQUES ET PARTENAIRES" in rendu)
_check("   le cas qui doit PASSER est nommé (Ferrari, la marque-sujet)", "Ferrari" in rendu)
_check("   le cas qui doit S'EFFACER est nommé (CUKI, le sponsor)", "CUKI" in rendu)
_check("   elle donne le geste, pas seulement l'interdit",
       "garde le FAIT" in rendu and "omets le NOM" in rendu)
_check("   et relie à une règle déjà en vigueur (sources radar jamais créditées)",
       "radar" in rendu.split("MARQUES ET PARTENAIRES")[1][:700])

print("\n──── l'insertion n'a rien cassé autour ────")
_check("le vocabulaire interdit est toujours rendu", "royaume de Sardaigne" in rendu)
_check("la géographie suit toujours", "Nomme toujours la géographie" in rendu)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
