#!/usr/bin/env python3
"""Fixture : la langue d'un article RÉDIGÉ se lit sur son corps, pas sur son titre.

Incident du 23/09/2026, Plaisirs de Culture en Vallée d'Aoste. Trois originaux (5935,
5958, 5973) portent un titre italien — le NOM de l'événement, gardé par la rédaction —
sur un corps entièrement français. `effective_lang` rendait `it` (le titre tranchait
seul dès deux mots-outils d'avance) : l'original partait sous l'étiquette italienne
avec un texte français, et `--retranslate` écrivait la jumelle… en français.

Textes réels, relevés sur le site le 23/09 (WP#11800, WP#11790, WP#11842).

Cas qui DOIVENT passer en `it`, près de la frontière : un corps italien qui cite des
noms propres français (« Plaisirs de Culture en Vallée d'Aoste », « Fondation Grand
Paradis ») — ceux-là ne doivent pas renverser le verdict dans l'autre sens.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_langue_corps_decide
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.lang import effective_lang  # noqa: E402

echecs = 0


def _check(label, obtenu, attendu):
    global echecs
    if obtenu == attendu:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} : {obtenu!r}, attendu {attendu!r}")


def _ev(titre, chapo, corps="", territoire="Vallée d'Aoste"):
    return {"article_title": titre, "territoire": territoire,
            "enrich_data": json.dumps({"article": {"titre": titre, "chapo": chapo,
                                                   "corps": corps}})}


FR_MANZETTI = ("Le samedi 26 septembre 2026, la Sala Museale Manzetti, au Centro "
               "Saint-Bénin à Aoste (Vallée d'Aoste), propose une visite spéciale pour "
               "les familles autour de l'inventeur valdôtain, avec la présentation de son "
               "automate et de ses recherches sur la transmission de la voix. La visite "
               "est gratuite et dure une heure.")
IT_INTROD = ("La storia del Castello di Introd è scandita da un ciclo continuo di "
             "distruzione e rinascita. Segnato da due devastanti incendi, questo luogo "
             "solleva interrogativi universali sul rapporto tra autenticità e memoria. "
             "Plaisirs de Culture en Vallée d'Aoste 2026. A cura di: Fondation Grand "
             "Paradis.")
IT_GAMBA = ("Un'occasione di incontro con due degli artisti che partecipano alla "
            "collettiva Sotto il cielo di stelle. Il curatore del progetto dialoga con "
            "Daniela Pellegrini e Marco Nereo Rotelli nella sede del Museo Gamba. "
            "Plaisirs de Culture en Vallée d'Aoste 2026.")

# ── L'incident : titre italien, corps français → fr ────────────────────────────────
_check("5958 : « Dall'automa al telefono » sur corps français → fr",
       effective_lang(_ev("Dall'automa al telefono: il genio di Innocenzo Manzetti",
                          FR_MANZETTI)), "fr")
_check("5935 : « La chiave della rinascita… » sur corps français → fr",
       effective_lang(_ev("La chiave della rinascita di un tesoro del 1462",
                          "Du 19 au 27 septembre, Gignod ouvre les portes de son grenier "
                          "du XVe siècle, restauré et transformé en séchoir pour les "
                          "plantes. La visite commence dans le pré, où le guide raconte "
                          "la découverte du grenier et de sa clé.")), "fr")

# ── Frontière, dans l'autre sens : corps italien truffé de noms propres français ────
_check("corps italien + « Plaisirs de Culture en Vallée d'Aoste » → it",
       effective_lang(_ev("Il Castello di Introd e l'armonia della trasformazione",
                          IT_INTROD)), "it")
_check("corps italien sous un titre français → it (le corps est ce qu'on lit)",
       effective_lang(_ev("Sous le ciel étoilé avec les artistes", IT_GAMBA)), "it")

# ── Corps indécis : on retombe sur le jugement d'ensemble, titre compris ────────────
_check("corps trop court pour trancher → le titre décide (it)",
       effective_lang(_ev("Il castello e la storia della valle", "Castello Gamba, 18.00.")),
       "it")
_check("sans article du tout → titre/description bruts, comme avant",
       effective_lang({"title": "La festa della castagna", "description": "",
                       "territoire": "Piemonte"}), "it")

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)")
    sys.exit(1)
print("Tout passe.")
