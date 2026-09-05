#!/usr/bin/env python3
"""Le JOUR DE LA SEMAINE écrit dans un texte — la donnée gratuite que la chaîne jetait.

Extrait de `scripts/verifier_dates.py` le 2026-08-11 pour servir aussi à la COLLECTE.
Franck : « je ne veux plus que les informations ne soient pas prises via les sources
officielles » et, plus tôt, « implacable au niveau de la collecte AVANT de passer par les
LLM ». Le contradicteur vérifie APRÈS publication ; ce module permet de vérifier AVANT.

CE QUE CE SIGNAL A DE PARTICULIER. Un texte français ou italien nomme presque toujours le
jour : « le vendredi 21 août », « sabato 7 maggio ». C'est écrit par quelqu'un qui savait
de quoi il parlait, ça ne coûte rien à lire, et **ça contraint l'année à une sur sept**.
Rien d'autre dans un texte d'annonce ne fait ça.

Trouvé en lisant l'extrait de la fiche 1069, en ligne le 2026-08-11 pour le 7 mai 2027 :
la page Paratissima disait « sabato 7 maggio » et « 4 anni fa ». Le 7 mai ne tombe un
samedi qu'en 2022. Le site annonçait pour dans un an une visite d'atelier vieille de
quatre.

CE QU'IL NE FAUT PAS EN FAIRE, et c'est aussi important. Ce n'est pas un oracle : la
SOURCE peut se tromper de jour. TorinoClick, l'agence de la Ville de Turin, a écrit « du
vendredi 24 au lundi 27 septembre » pour Terra Madre 2026, dont les vraies bornes sont un
jeudi et un dimanche. Le jour de semaine sert donc à DOUTER, jamais à choisir : s'en servir
pour élire une année aurait daté Terra Madre en 2027.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

# Lundi = 0, comme `date.weekday()`.
JOURS = {
    "lundi": 0, "lunedi": 0, "mardi": 1, "martedi": 1, "mercredi": 2, "mercoledi": 2,
    "jeudi": 3, "giovedi": 3, "vendredi": 4, "venerdi": 4, "samedi": 5, "sabato": 5,
    "dimanche": 6, "domenica": 6,
}
JOUR_RE = "|".join(JOURS)
NOM_DU_JOUR = {0: "lundi", 1: "mardi", 2: "mercredi", 3: "jeudi",
               4: "vendredi", 5: "samedi", 6: "dimanche"}

_MOIS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "decembre": 12,
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6,
    "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11,
    "dicembre": 12,
}
_MOIS_RE = "|".join(sorted(_MOIS, key=len, reverse=True))


def _sans_accents(s: str) -> str:
    n = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in n if unicodedata.category(c) != "Mn").lower()


def jours_nommes(texte: str) -> dict[tuple[int, int], set[int]]:
    """{(mois, quantième) : les jours de semaine annoncés pour cette date}.

    TOUTES LES MENTIONS, PAS LA DERNIÈRE. La première version écrasait la clé à chaque tour
    de boucle : un texte qui nomme deux fois le même quantième ne gardait que la SECONDE
    mention. C'est ce qui a produit le faux positif Terra Madre — l'article disait « da
    giovedì 24 a domenica 27 settembre », puis reparlait du 27 ailleurs. La bonne mention
    existait, elle était remplacée par l'autre, en silence.

    D'où l'ensemble : si le texte nomme NOTRE jour ne serait-ce qu'une fois, il nous
    confirme. Une source qui se contredit elle-même ne prouve rien contre nous."""
    t = _sans_accents(texte)
    trouves: dict[tuple[int, int], set[int]] = {}
    for j, d, mon in re.findall(rf"\b({JOUR_RE})\s+(\d{{1,2}})\s+({_MOIS_RE})", t):
        trouves.setdefault((_MOIS[mon], int(d)), set()).add(JOURS[j])
    return trouves


def contredit(texte: str, iso: str) -> str:
    """Le texte contredit-il cette date par le jour qu'il annonce ? "" si tout va bien.

    Renvoie une phrase lisible, pas un booléen : elle finira sous les yeux de quelqu'un qui
    doit trancher, et « le texte annonce un samedi, notre 07/05/2027 est un vendredi » se
    juge en une seconde là où « True » ne se juge pas du tout.

    NE SE PRONONCE QUE SI LE TEXTE NOMME LE JOUR **DE NOTRE DATE**. Sans ça on comparerait
    le samedi d'un autre événement au nôtre."""
    try:
        d = date.fromisoformat((iso or "")[:10])
    except ValueError:
        return ""
    annonces = jours_nommes(texte).get((d.month, d.day)) or set()
    if not annonces or d.weekday() in annonces:
        return ""
    dit = NOM_DU_JOUR[sorted(annonces)[0]]
    return (f"le texte annonce un {dit}, le {d.strftime('%d/%m/%Y')} est un "
            f"{NOM_DU_JOUR[d.weekday()]}")


def annees_possibles(mois: int, quantieme: int, jour_semaine: int,
                     autour: int, marge: int = 6) -> list[int]:
    """Les années où ce quantième tombe bien ce jour-là, dans une fenêtre autour de `autour`.

    Sert à LIRE un désaccord, jamais à choisir une année — voir l'avertissement en tête de
    module. Quand la seule année possible est loin derrière, ce n'est plus une faute d'un
    an : c'est une annonce ancienne, et le geste n'est pas de re-dater mais d'écarter."""
    out = []
    for a in range(autour - marge, autour + 3):
        try:
            if date(a, mois, quantieme).weekday() == jour_semaine:
                out.append(a)
        except ValueError:
            continue
    return out
