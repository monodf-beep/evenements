#!/usr/bin/env python3
"""Séparer un DOUTE d'une information ABSENTE — deux choses que la file « À vérifier »
confondait, et c'est ce qui la rendait ingérable.

Franck, 2026-08-11, capture d'écran à l'appui : « 548 tâches ! c'est ingérable. Soit
c'est pas assez regroupé et du coup ça fait peur, soit la collecte n'est pas bonne, soit
les 2. » 454 points sur 118 événements, soit quatre par fiche, mécaniquement.

Les quatre premiers de l'écran disent tout :
    « Tarifs de la Fête du Fort du Mont, de la visite gourmande et du festiv'arts »
    « Contenu précis (genre, horaires) du festiv'arts de Conflans »
    « Programme détaillé des ateliers (titres, horaires, jours précis) »
    « Capacités d'accueil des sorties (lacs, grotte) »

Aucun de ces points n'est vérifiable. Ce ne sont pas des faits douteux : ce sont des
informations que la source ne publie pas. Franck ne peut pas davantage que le modèle
connaître la capacité d'accueil d'une sortie au lac — il faudrait téléphoner à
l'organisateur. Une file remplie de ça n'est pas un garde-fou, c'est un inventaire des
silences de la source.

LA DISTINCTION QUI COMPTE
  • DOUTE — l'article AFFIRME quelque chose dont on n'est pas sûr : un nom peut-être mal
    orthographié, « une seule date trouvée », un tarif annoncé mais non confirmé. Là, il
    y a un risque de publier un fait FAUX, et un humain peut trancher. C'est le
    garde-fou, et il doit rester visible.
  • ABSENCE — l'article ne dit RIEN de ce point. Aucun risque : un article qui n'affirme
    pas ne se trompe pas. Il n'y a rien à vérifier, seulement quelque chose qu'on
    n'écrira pas.

RIEN N'EST SUPPRIMÉ : les absences restent en base et sont comptées à l'écran. Si la
distinction s'avère mauvaise, elle se défait d'un paramètre.

⚠️ C'EST UNE HEURISTIQUE SUR LA FORMULATION, et il faut le dire. Elle repose sur les
marqueurs de doute que le modèle emploie quand il doute vraiment. Un doute rédigé sans
marqueur sera classé « absence » à tort — d'où le compteur visible et l'option de tout
afficher. Le correctif de fond est en amont, dans le prompt d'enrichissement, qui
demandait explicitement de signaler toute « affirmation absente de la matière » : cette
phrase INVITAIT à produire l'inventaire qu'on constate.
"""
from __future__ import annotations

import re
import unicodedata

# ── L'ABSENCE L'EMPORTE SUR LE DOUTE ────────────────────────────────────────────
# Deuxième passe, le 2026-08-11 : après le premier tri il restait 138 points, et Franck —
# « on a encore trop de tâches !!! ». En lisant l'écran, la faute était la mienne : j'avais
# rangé « non confirmé » parmi les marqueurs de DOUTE. Or le modèle l'emploie pour dire
# « la source ne le dit pas », ce qui est exactement une ABSENCE :
#     « Gratuité de l'accès non confirmée explicitement par la matière »
#     « Lieu exact de la rencontre (salle, foyer ?) non précisé dans la matière »
#     « Date et horaire précis de la rencontre non confirmés »
# Aucun de ces trois-là n'est vérifiable, et le second passait même grâce à son point
# d'interrogation. « Non confirmé » ne dit pas qu'on doute d'un fait écrit : il dit qu'on
# n'a pas trouvé le fait. Ces formules sont donc testées EN PREMIER et l'emportent.
_ABSENCE = (
    r"\bnon confirme", r"\bpas confirme", r"\bnon precise", r"\bpas precise",
    r"\bnon explicite", r"\bnon mentionne", r"\bpas mentionne", r"\bnon indique",
    r"\bnon detaille", r"\bnon publie", r"\bnon communique", r"\bnon renseigne",
    r"\babsente? de la matiere\b", r"\bmanque dans la matiere\b",
    r"\bpas (?:d[eu']|de la |des )?(?:tarif|horaire|programme|detail)",
    # TROISIÈME PASSE, même jour. Le point d'interrogation laissait encore passer une
    # famille entière : les questions qui RÉCLAMENT DU CONTENU. « Contenu précis de
    # l'exposition Chine : artefacts, maquettes, films ? », « quelles œuvres exactement
    # de Brahms ? », « Thèmes concrets des ateliers (nature, histoire, archéologie ?) ».
    # Ce sont des absences déguisées en questions : la source ne détaille pas, et aucun
    # humain ne peut « vérifier » un détail qui n'existe nulle part.
    # Ce qui les distingue d'un vrai doute : elles demandent CE QU'IL Y A, jamais si ce
    # qui est écrit est JUSTE.
    r"\bcontenu precis", r"\bcomposition precise", r"\bthemes? concrets?",
    r"\bdetails? (?:de|du|des|precis)", r"\bprogramme detaille",
    r"\bquelles? (?:oeuvres?|pieces?|activites?|animations?)",
    r"\by a-t-il d'autres\b", r"\bnombre et niveau\b",
    r"\bnationalites precises", r"\bcapacites? d'accueil",
    r"\bages? recommandes?", r"\bdurees? des\b",
)

# Marqueurs employés quand on doute d'un fait QU'ON ÉCRIT — c'est-à-dire quand l'article
# AFFIRME quelque chose qui pourrait être faux. Ce qui les distingue des formules
# ci-dessus : ils signalent une CONTRADICTION, une CONFUSION ou une AMBIGUÏTÉ, jamais un
# silence. Choisis sur les points réels de la production, pas imaginés.
_DOUTE = (
    r"\bpeut-etre\b", r"\bpeut etre\b",
    r"\bincertain", r"\bdouteu", r"\bambigu",
    r"\bune seule date\b", r"\bseule date trouvee\b",
    r"\bcontradict", r"\bdivergen", r"\bincoheren",
    r"\bmal orthographi", r"\borthographe\b",
    r"\b1 ou 2\b", r"\bou bien\b",
    r"\bsemble\b", r"\bsupposé", r"\bsuppose\b",
    r"\bconfusion\b", r"\bconfondu", r"\bne correspond pas\b",
    r"\bdeux (?:dates|lieux|titres|noms)\b",
)


def _norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "")
                if not unicodedata.combining(c))
    return s.lower()


def est_doute(label: str) -> bool:
    """True si le point signale un fait AFFIRMÉ dont on doute (à garder sous les yeux),
    False si c'est une information simplement absente de la source (rien à vérifier).

    L'ABSENCE est testée d'abord et l'emporte : « lieu exact (salle, foyer ?) non précisé
    dans la matière » contient un point d'interrogation, mais dit surtout que la source
    se tait. Un silence bien formulé reste un silence."""
    bas = _norm(label)
    if any(re.search(m, bas) for m in _ABSENCE):
        return False
    if "?" in (label or ""):
        # Une VRAIE question posée à l'humain (« 1 ou 2 artistes ? ») est un doute — mais
        # seulement si aucune formule d'absence ne l'a déjà disqualifiée ci-dessus.
        return True
    return any(re.search(m, bas) for m in _DOUTE)


def repartition(labels) -> tuple[list, list]:
    """(doutes, absences) — pour compter les deux sans en perdre aucun."""
    doutes, absences = [], []
    for lab in labels or []:
        (doutes if est_doute(lab if isinstance(lab, str) else lab.get("label", ""))
         else absences).append(lab)
    return doutes, absences
