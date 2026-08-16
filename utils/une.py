#!/usr/bin/env python3
"""Score de la section « À LA UNE » — l'INTÉRÊT de l'événement, relevé par l'imminence.

D'OÙ ÇA VIENT. Constat de Franck le 2026-08-17, capture d'écran à l'appui :

    À LA UNE
    · Bien-être aux Charmettes : pilates dans le jardin   (26/08, visuel générique)
    · Charlie Winston au Théâtre Novarina                 (22/09)
    · Tout est calme dans les hauteurs                    (24/09)

    « pilate en "à la une" ??? les 2 autres, ça fait des semaines qu'ils sont à la
      une, c'est des événements fin septembre. À la une il faut des règles pour que
      ça tourne et que ça joue son vrai rôle. »

DEUX DÉFAUTS, ET UNE SEULE CAUSE. La section triait sur `as_home_score`, qui vaut
« panel de lecteurs (0-6) + source officielle (2,5) + visuels (1,5) ». Cette note mesure
LA QUALITÉ DU RENDU — peut-on montrer cette fiche proprement ? — et pas du tout l'intérêt
de l'événement. D'où :

  · un cours de pilates bien rédigé, sourcé et illustré bat mécaniquement un festival mal
    illustré. Le score fait exactement ce qu'on lui a demandé ;
  · elle est calculée UNE FOIS à la rédaction et ne bouge plus jamais : rien ne sait qu'on
    est à cinq semaines de la date, donc rien ne tourne.

C'EST UN PROBLÈME DÉJÀ RÉSOLU AILLEURS DANS CE DÉPÔT. Le 2026-08-01, Franck faisait le
même constat sur « Ça vaut le déplacement » : deux expositions de 365 et 199 jours
occupaient la vitrine pendant que la Foire de la Saint-Ours n'apparaissait jamais. La
réponse a été `deplacement_now` — l'intrinsèque relevé par le temps qui reste. « À la
une » n'avait jamais reçu ce traitement. On ne réinvente donc rien : on rebranche.

LA RÉPARTITION DES RÔLES, et c'est tout le correctif :

    `as_home_score`  → ÉLIGIBILITÉ.  Peut-on la montrer ? (rédigée, sourcée, illustrée)
    `interet()`      → CLASSEMENT.   Est-ce que ça mérite la une ?
    imminence        → ROTATION.     Est-ce que c'est pour bientôt ?

Le rendu FILTRE, il ne classe plus. C'est l'inversion qui règle les deux plaintes d'un
coup : le pilates sort par le classement, les concerts de fin septembre tournent par
l'imminence.

⚠️ POURQUOI PAS `deplacement_score` TEL QUEL. Il inclut `accessibilite_langue`, et ce
critère mesure LA TRAVERSÉE D'UNE FRONTIÈRE — « pourra-t-il en profiter ? » se demande
d'un visiteur d'en face. Pour la une de la home FRANÇAISE, lue par un francophone, une
pièce en français n'a aucune barrière de langue : l'y appliquer déclasserait tout le
théâtre de la vitrine, pour une raison qui ne concerne pas ce lecteur-là. On prend donc
les quatre critères d'importance SEULS (`_score_criteres`, 0-10 pondérés), et la langue
reste où elle sert.
"""
from __future__ import annotations

import os
from datetime import date as _date

from utils.deplacement import (_score_criteres, _jour, _FENETRES, PONCTUEL_MAX_JOURS)

# Plancher d'INTÉRÊT (sur 10 pondérés : rayonnement ×2, spécificité ×3, tradition ×1,
# notoriété plafonnée à 1). En dessous, la fiche n'a rien à faire en une, même parfaitement
# rendue — c'est très exactement le cas du cours de pilates.
#
# ⚠️ VALEUR PROVISOIRE, À MESURER AVANT D'Y CROIRE. Le seuil de « Ça vaut le déplacement »
# a été posé au jugé à 3 le 2026-08-01, « faute de connaître le stock » : il ne servait à
# rien, il suffisait de ne pas être nul pour entrer. Il a fallu compter ce que chaque
# plancher laissait par territoire pour arriver à 10/12. La même mesure est due ici :
# `scripts/audit_une.py` l'affiche. 6/10 est un point de départ, pas une décision.
UNE_INTERET_MIN = int(os.getenv("UNE_INTERET_MIN", "6"))
# Plancher de RENDU (as_home_score, 0-10). Une fiche qu'on ne peut pas montrer proprement
# n'est pas une une, quel que soit son intérêt.
UNE_RENDU_MIN = float(os.getenv("UNE_RENDU_MIN", "6"))
# HORIZON PROPRE À LA UNE, et c'est LUI qui fait tourner la vitrine.
#
# « Ça vaut le déplacement » regarde à 183 jours : on peut décider six mois à l'avance
# d'aller à la Saint-Ours. Une UNE, non — elle dit ce qui se passe MAINTENANT. Avec
# l'horizon long, un concert du 22 septembre entre dès la mi-août et occupe la vitrine
# cinq semaines durant : c'est exactement ce que Franck a constaté.
#
# À 30 jours, chaque semaine fait ENTRER de nouveaux événements et en fait SORTIR
# d'autres, sans qu'aucun état ne soit mémorisé nulle part. La rotation est une
# conséquence du calendrier, pas un compteur à tenir — donc rien à réparer le jour où
# elle se grippe.
UNE_HORIZON_JOURS = int(os.getenv("UNE_HORIZON_JOURS", "30"))

MAX_INTERET = 10
MAX_BONUS = max(p for _s, p in _FENETRES) + 1      # fenêtre la plus proche + ponctuel
MAX_UNE = MAX_INTERET + MAX_BONUS


def interet(event: dict) -> int | None:
    """L'INTÉRÊT de l'événement, 0-10, ou None s'il n'a pas été évalué.

    None ≠ 0 : « pas mesuré » n'est pas « sans intérêt ». Une fiche non évaluée est écartée
    de la vitrine, pas classée dernière — même règle que `deplacement_score`, et pour la
    même raison : classer un inconnu au plus bas, c'est affirmer quelque chose qu'on ne
    sait pas.
    """
    return _score_criteres(event.get("llm_score_detail"))


def _visuel(event: dict) -> str:
    """Ce que la rédaction a trouvé comme image : 'deux' | 'une' | 'photo officielle' |
    'aucune'. Lu dans `enrich_data`, jamais recalculé — c'est `enrich.py` qui a comparé
    le domaine de l'image aux domaines officiels, et refaire ce calcul ici finirait par
    diverger du sien."""
    import json
    try:
        data = json.loads(event.get("enrich_data") or "{}")
    except (ValueError, TypeError):
        return "aucune"
    return str(((data.get("home") or {}).get("affiches") or "aucune"))


def une_etat(event: dict, aujourdhui=None) -> tuple[int | None, str]:
    """(score de tri, MOTIF) — le motif est rendu pour être AFFICHÉ, jamais deviné.

    La note de déplacement a mis trois jours à devenir lisible faute d'exposer son motif
    (« c'est dommage de pas la voir dans le back-office », 2026-08-03) : une note invisible
    ne se conteste pas, on ne peut que constater le résultat sur le site et deviner. On
    rend donc la raison dès le premier jour.
    """
    if event.get("annule_le"):
        return None, "annulé — une vitrine ne recommande pas ce qui n'aura pas lieu"

    # ── ÉLIGIBILITÉ : peut-on la MONTRER ? ────────────────────────────────────────────
    # Règle posée par Franck le 2026-07-30 : la home se remplissait de contenu non rédigé
    # faute de mieux. Le score seul ne suffisait pas à l'exclure — il faut un portillon.
    if (event.get("enrich_status") or "") != "enriched":
        return None, "jamais rédigée — la une ne se remplit pas faute de mieux"
    visuel = _visuel(event)
    if visuel == "aucune":
        # C'est le cas du pilates : sa carte affiche le visuel GÉNÉRIQUE du site (une
        # silhouette de Chambéry), pas une image de l'événement. Une une sans image propre
        # est une une qui ment sur ce qu'elle montre.
        return None, "aucune image propre — la carte afficherait le visuel générique"
    rendu = event.get("home_score")
    if rendu is None:
        return None, "score de rendu non calculé"
    if float(rendu) < UNE_RENDU_MIN:
        return None, f"rendu insuffisant ({rendu} < {UNE_RENDU_MIN})"

    # ── CLASSEMENT : est-ce que ça MÉRITE la une ? ────────────────────────────────────
    base = interet(event)
    if base is None:
        return None, "pas évaluée — écartée, pas classée dernière"
    if base < UNE_INTERET_MIN:
        return None, (f"intérêt sous le plancher ({base} < {UNE_INTERET_MIN}) — bien "
                      f"rendue ne veut pas dire digne de la une")

    # ── ROTATION : est-ce que c'est pour BIENTÔT ? ────────────────────────────────────
    auj = aujourdhui or _date.today()
    debut, fin = _jour(event.get("date_event_start")), _jour(event.get("date_event_end"))
    derniere = fin or debut
    if derniere is None:
        # Sans date (récurrent, ou en attente de dates.py) : intérêt seul, jamais exclu —
        # une donnée manquante n'est pas un événement terminé (règle 5).
        return base, "sans date — intérêt seul, aucun bonus d'imminence"
    if derniere < auj:
        return None, "événement terminé (règle 5)"
    if debut and (debut - auj).days > UNE_HORIZON_JOURS:
        return None, (f"commence dans {(debut - auj).days} jours — la une parle du mois "
                      f"qui vient, pas de la saison (horizon {UNE_HORIZON_JOURS} j)")

    restant = (derniere - auj).days
    bonus = next((pts for seuil, pts in _FENETRES if restant <= seuil), 0)
    if debut and fin and (fin - debut).days <= PONCTUEL_MAX_JOURS:
        bonus += 1
    elif debut and not fin:
        bonus += 1
    motif = (f"intérêt {base}/10" +
             (f" + {bonus} d'imminence ({restant} j restant)" if bonus else
              f" · aucun bonus — encore {restant} jours, la une n'est pas pour maintenant"))
    return base + bonus, motif


def une_now(event: dict, aujourdhui=None) -> int | None:
    """Le seul chiffre que WordPress doit trier. None = la fiche n'a pas sa place en une."""
    return une_etat(event, aujourdhui)[0]
