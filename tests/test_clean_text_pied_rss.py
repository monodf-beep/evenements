#!/usr/bin/env python3
"""Fixture : `utils.clean_text.strip_boilerplate` retire le pied de flux RSS FRANÇAIS.

D'OÙ ÇA VIENT — 2026-09-08, audit SEO. La meta description de trois fiches publiées
(lue dans le HTML servi à Google, pas en base) était le pied de flux de la source :

    « L'article Grand Bal du Comité des Fêtes est apparu en premier sur Mairie de
      Villefranche-sur-Mer . »

Le nettoyeur existait et visait ce pied depuis le premier jour — mais sa marque de début
disait « Cet article », et le pied WordPress français dit « L'article ». Treize fiches en
ligne le portaient. Les chaînes ci-dessous sont recopiées du site, pas construites.

LES CAS QUI DOIVENT PASSER (= ne pas être coupés) sont choisis près de la frontière :
« l'article » est un mot courant du français, et la marque seule ne doit jamais suffire.

Lancer : .venv/bin/python -m tests.test_clean_text_pied_rss
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.clean_text import strip_boilerplate  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# ── Recopiés du site le 2026-09-08 ─────────────────────────────────────────────────
GRAND_BAL = ("L’article Grand Bal du Comité des Fêtes est apparu en premier sur "
             "Mairie de Villefranche-sur-Mer .")
VOILES = ("Régates dans la rade du 15 au 20 septembre. L’article Les Voiles Maralpines "
          "est apparu en premier sur Mairie de Villefranche-sur-Mer .")
CARTER = ("Mardi 6 octobre | 20h30 Thonon | Théâtre M. Novarina L’article James carter "
          "est apparu en premier sur Maison des Arts du Léman .")

verifier("un pied seul devient une chaîne vide (rien à garder)",
         strip_boilerplate(GRAND_BAL) == "", repr(strip_boilerplate(GRAND_BAL)))
out = strip_boilerplate(VOILES)
verifier("les faits AVANT le pied sont gardés (dates des régates)",
         out == "Régates dans la rade du 15 au 20 septembre.", repr(out))
out = strip_boilerplate(CARTER)
verifier("horaire et lieu gardés, pied retiré (James Carter)",
         out.startswith("Mardi 6 octobre") and "apparu" not in out, repr(out))
verifier("l'apostrophe typographique (’) est reconnue comme l'apostrophe droite",
         "apparu" not in strip_boilerplate(GRAND_BAL.replace("’", "'")))

# ── LES CAS QUI DOIVENT PASSER ─────────────────────────────────────────────────────
REGLEMENT = ("L'article 5 du règlement précise que les enfants de moins de 12 ans "
             "entrent gratuitement. Ouverture des portes à 19h.")
verifier("« L'article 5 du règlement » en tête de texte n'est PAS un pied",
         strip_boilerplate(REGLEMENT) == REGLEMENT)

# La marque en début, le VRAI pied loin derrière : on coupe au pied, pas à la marque.
LOIN = ("L'article de presse qui suit a été publié par la mairie. Concert gratuit le "
        "12 juillet à 21h sur la place. Restauration sur place. "
        + " Bla bla." * 60
        + " L'article Concert d'été est apparu en premier sur Ville de Thonon .")
out = strip_boilerplate(LOIN)
verifier("une marque lointaine (> 400 car. avant le verbe) ne coupe pas le texte utile",
         out.startswith("L'article de presse") and "12 juillet" in out
         and "apparu" not in out, repr(out[-80:]))

IT = "Concerto in piazza. L'articolo Festa d'estate proviene da Comune di Aosta."
verifier("le pied italien reste couvert (non-régression)",
         strip_boilerplate(IT) == "Concerto in piazza.")

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
