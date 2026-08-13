#!/usr/bin/env python3
"""Fixture : ce que `incoherence_description` a le droit de REFUSER.

D'OÙ ÇA VIENT — et c'est un portillon que j'ai livré, pas un qu'on m'a laissé.
`translate_events` bloquait la traduction sur DEUX signaux :

  ① « aucun mot commun entre la description et l'identité de la fiche » ;
  ② « la description nomme une autre commune et jamais la sienne ».

Le 2026-08-13, après neuf jours pendant lesquels trois fiches étaient écartées à
l'identique tous les matins, j'ai enfin LU ce que le portillon refusait. Deux sur trois
étaient des faux :

  · [4420] « Fiera Nazionale del Peperone di Carmagnola » — titre italien, description
    française (« la plus grande manifestation italienne dédiée aux poivrons, dix jours de
    saveurs, traditions et spectacles »). Description excellente. Aucun mot commun, parce
    que le site est BILINGUE ;
  · [3739] « EVO France 2026 » — description « deuxième édition européenne du plus grand
    tournoi de jeux de combat au monde ». Excellente aussi. Aucun mot commun, parce
    qu'une bonne description PARAPHRASE au lieu de répéter son titre.

Signal ① : zéro vrai positif, deux faux, en neuf jours de production. Il ne refuse plus
rien tout seul ; il reste dans les RAPPORTS, que Franck lit et juge.

C'est la leçon du dépôt appliquée à un détecteur : sur un texte écrit pour des humains,
on ne peut pas EXTRAIRE, seulement CONFIRMER à partir d'un fait déjà connu. « Aucun mot
commun » ne confirme rien — il constate un SILENCE, et un silence n'est pas une
contradiction.

⚠️ LA MOITIÉ QUI COMPTE DE CETTE FIXTURE, ce sont les cas qui doivent PASSER. Celle du
06/08 (portillon des titres) n'avait que des cas confirmant son design ; elle est passée
au vert sur un portillon faux.

Lancer : .venv/bin/python -m tests.test_coherence_bloquant
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.coherence import incoherence_description  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ── LES DEUX FAUX POSITIFS RÉELS, recopiés de la production ───────────────────────────
PEPERONE = {
    "id": 4420,
    "title": "Fiera Nazionale del Peperone di Carmagnola",
    "lieu": "Carmagnola", "ville": "Carmagnola",
    "description": ("La plus grande manifestation italienne dédiée aux poivrons, avec "
                    "dix jours de saveurs, traditions et spectacles. Chaque soir, des "
                    "concerts gratuits animent le centre historique, tandis que les "
                    "marchés de producteurs occupent les places du bourg. Les "
                    "dégustations proposent une centaine de recettes, du plat de rue "
                    "au menu gastronomique servi sous les arcades. L'entrée est libre "
                    "et le programme complet paraît au début de l'été."),
}
EVO = {
    "id": 3739,
    "title": "EVO France 2026",
    "lieu": "Palais des Expositions", "ville": "Nice",
    "description": ("Deuxième édition européenne du plus grand tournoi de jeux de combat "
                    "au monde. L'événement propose huit tournois principaux, des "
                    "qualifications ouvertes à tous, une zone de démonstration et un "
                    "espace consacré aux éditeurs indépendants. Les finales se jouent le "
                    "dimanche devant plusieurs milliers de spectateurs, et la "
                    "retransmission est suivie par une audience internationale."),
}

print("──── LES CAS QUI DOIVENT PASSER (ce sont eux qui prouvent quelque chose) ────")
_check("bilinguisme : titre italien, description française → PLUS de refus",
       incoherence_description(PEPERONE, bloquant=True) is None,
       str(incoherence_description(PEPERONE, bloquant=True)))
_check("paraphrase : la description ne répète pas le titre → PLUS de refus",
       incoherence_description(EVO, bloquant=True) is None,
       str(incoherence_description(EVO, bloquant=True)))
_check("   (et ces deux-là étaient bien refusées AVANT — sinon la fixture ne montre rien)",
       incoherence_description(PEPERONE) is not None
       and incoherence_description(EVO) is not None,
       f"{incoherence_description(PEPERONE)} | {incoherence_description(EVO)}")

# ── LE VRAI POSITIF HISTORIQUE, QUI DOIT TENIR ────────────────────────────────────────
# WP#6798 : la description d'une soirée d'Annecy a contaminé une fiche de Chambéry par
# une fusion à tort. C'est CE cas qui justifie qu'un portillon existe — et il vient du
# signal ②, qui nomme une contradiction vérifiable au lieu de constater une absence.
WP6798 = {
    "id": 6798,
    "title": "Une semaine pas plus",
    "lieu": "Le Malamute", "ville": "Chambéry",
    "description": ("La Fête du lac d'Annecy revient sur les rives du lac avec son "
                    "spectacle pyrotechnique tiré depuis des barges. Le public est "
                    "attendu sur les quais d'Annecy et dans les jardins de l'Europe, "
                    "où des gradins sont montés pour l'occasion."),
}

print("\n──── LE CAS QUI DOIT ENCORE ÊTRE REFUSÉ ────")
motif = incoherence_description(WP6798, bloquant=True)
_check("une description qui nomme une AUTRE commune et jamais la sienne reste bloquante",
       motif is not None, str(motif))
_check("   et le motif cite la commune fautive, pour qu'on puisse en juger",
       "annecy" in (motif or "").lower(), str(motif))

print("\n──── le signal ① n'est pas supprimé, il est DÉCLASSÉ ────")
_check("hors mode bloquant, il parle encore (pour les rapports que Franck lit)",
       incoherence_description(EVO) is not None)
_check("   et le mode bloquant est bien plus indulgent que le mode rapport",
       incoherence_description(EVO, bloquant=True) is None)

print("\n──── ce qui n'a jamais été un signal ────")
_check("description vide → aucun verdict (une absence n'est pas une contradiction)",
       incoherence_description({"title": "T", "ville": "Nice", "description": ""},
                               bloquant=True) is None)
_check("fiche sans ville → le signal ② ne peut pas se prononcer, et il se tait",
       incoherence_description({"title": "T", "ville": "", "lieu": "",
                                "description": "Une soirée à Annecy sur les quais."},
                               bloquant=True) is None)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
