#!/usr/bin/env python3
"""Score « ÇA VAUT LE DÉPLACEMENT » (0-8) — DÉTERMINISTE, zéro appel LLM.

Contexte (décision Franck, 2026-08-01) : la section home « Ça vaut le déplacement »
triait chronologiquement (les 8 prochains événements, sans critère de qualité). On a
d'abord envisagé de trier sur `vmean` (note des personas VISITEURS) — mauvaise piste,
constatée sur les données réelles : `vmean` mesure la RICHESSE DE L'ARTICLE, pas
l'ampleur de l'événement (Musilac, 110 000 festivaliers, notait 1.0 pendant qu'une
petite exposition notait 3.0, simplement parce que son article était maigre).

On a ensuite envisagé de demander au persona de juger l'événement « au-delà de
l'article ». Abandonné aussi : un persona ne SAIT rien (c'est un texte de quelques
lignes), c'est le modèle qui mobiliserait ses connaissances d'entraînement — donc une
note invérifiable, exposée aux confusions de nom.

La bonne source existait déjà : `scripts/evaluator.py` note l'IMPORTANCE de chaque
événement sur 5 critères observables, stockés en base (`llm_score_detail`), CHACUN
avec sa phrase de justification. Deux de ces critères sont littéralement la définition
de « ça vaut le déplacement » :
  - `rayonnement`              : international / transfrontalier FR-IT = 2, régional = 1, local = 0
  - `specificite_territoriale` : identitaire, propre au territoire = 1, générique = 0

Avantages sur les pistes abandonnées : rétroactif (marche sur les fiches déjà publiées,
sans repasser enrich.py), auditable (on peut lire POURQUOI chaque point a été donné),
et sans risque d'hallucination.

`organisateur_moyens` est VOLONTAIREMENT exclu : le budget de l'organisateur n'entre pas
dans la décision d'un visiteur de faire trois heures de route.
"""
from __future__ import annotations
import json

# Critères retenus et leur poids. Somme des maxima = 8.
# Poids 1 partout : simple, explicable, et suffisant pour discriminer sur les données
# réelles (Musilac 7/8, Arte Povera Turin 7/8, « L'été au centre socioculturel » 1/8).
# À pondérer seulement si un cas concret le réclame — pas d'avance.
_CRITERES = ("notoriete_lieu", "edition_tradition", "rayonnement", "specificite_territoriale")
MAX_SCORE = 8


def deplacement_score(llm_score_detail) -> int | None:
    """Score 0-8 depuis `llm_score_detail` (JSON de scripts/evaluator.py), ou None si le
    détail est absent/illisible — None ≠ 0 : « pas mesuré » n'est pas « nul », la section
    doit écarter les non-mesurés, pas les classer derniers.

    Accepte une chaîne JSON ou un dict déjà décodé.
    """
    data = llm_score_detail
    if isinstance(data, str):
        try:
            data = json.loads(data or "{}")
        except (ValueError, TypeError):
            return None
    if not isinstance(data, dict) or not data:
        return None

    total = 0
    trouve = False
    for cle in _CRITERES:
        bloc = data.get(cle)
        pts = bloc.get("points") if isinstance(bloc, dict) else bloc
        if isinstance(pts, (int, float)):
            total += int(pts)
            trouve = True
    return total if trouve else None


# --------------------------------------------------------------------------- #
# RARETÉ ET IMMINENCE — ce que les cinq critères ne mesurent pas
#
# Constat de Franck, 2026-08-03, en regardant la home : la section affichait deux
# expositions durant 365 et 199 jours, dont l'une ouverte depuis sept mois. Le Castello
# di Rivoli les mérite pourtant — grand musée (notoriété 3) et rayonnement international
# (2) : le score fait exactement ce qu'on lui a demandé.
#
# LE MANQUE N'EST DONC PAS DANS LES CRITÈRES, il est dans ce qu'aucun ne dit : une
# exposition ouverte encore six mois est une raison de se déplacer UN JOUR ; une foire de
# trois jours qui a lieu une fois par an est une raison de se déplacer MAINTENANT. À
# critères égaux, le musée gagne toujours, et la Foire de la Saint-Ours n'apparaît jamais.
#
# LE SIGNAL RETENU EST LE TEMPS QUI RESTE POUR Y ALLER, et lui seul. Il traite les deux
# cas d'un coup, sans avoir à distinguer « exposition » de « festival » :
#   • un événement court dont la date approche → peu de jours restants → il monte ;
#   • une longue exposition qui vient d'ouvrir  → beaucoup de jours restants → elle attend ;
#   • une longue exposition qui FERME bientôt   → peu de jours restants → elle remonte, et
#     c'est juste : la dernière chance de la voir est une vraie raison de se déplacer.
#
# UN BONUS, PAS UNE REFONTE. L'urgence départage, elle ne remplace pas la qualité : le
# maximum du bonus (3) reste inférieur à l'écart entre un bon et un mauvais score
# intrinsèque (0-8). Une fiche médiocre qui ferme demain ne doit pas chasser une fiche
# remarquable ouverte encore un mois — d'où aussi le plancher ci-dessous.
# --------------------------------------------------------------------------- #

# En dessous de ce score intrinsèque, aucune urgence ne rattrape : la section s'appelle
# « ça vaut le déplacement », pas « ça ferme bientôt ».
#
# RELEVÉ DE 3 À 6 LE 2026-08-03, sur constat de Franck en regardant la home. Le 3 avait été
# posé au jugé, faute de connaître le stock, et il ne servait à rien : il suffisait de ne
# pas être NUL pour entrer. « Au diapason » occupait ainsi la carte Savoie — pas parce
# qu'il vaut le déplacement, mais parce qu'il était le moins mauvais de sa colonne.
#
# CE QUE CE SEUIL COÛTE, ET POURQUOI C'EST ACCEPTÉ. La section affiche UN événement par
# territoire : un plancher haut peut donc laisser une carte VIDE plutôt que médiocre.
# Arbitrage de Franck, et il est cohérent avec le nom de la section — une carte vide ne
# ment pas, une carte faible si. `scripts/audit_deplacement.py` mesure, territoire par
# territoire, ce que chaque plancher laisse : c'est lui qui dira si 7 tient.
DEPLACEMENT_MIN = 6
# Fenêtres (jours restants → points). Volontairement peu de paliers : trois marches
# lisibles valent mieux qu'une formule continue que personne ne saura expliquer.
_FENETRES = ((7, 3), (21, 2), (45, 1))
# Durée totale au-delà de laquelle on ne parle plus d'un « événement » mais d'une
# programmation continue. Sert au bonus de rareté, pas à exclure.
PONCTUEL_MAX_JOURS = 4

# HORIZON — décision de Franck le 2026-08-03, en regardant la home : la section affichait
# la Foire de Saint-Ours du 30 janvier 2027, à six mois de là. « Ça vaut le déplacement »
# est une invitation à y aller, pas un pense-bête pour l'an prochain : un événement qu'on
# ne peut pas décider d'aller voir n'a rien à faire dans une section qui pousse à décider.
#
# Six mois et non trois : Franck a tranché sur les données réelles (« 6 mois c'est bien, ça
# capture les meilleurs »). Les grandes manifestations s'annoncent longtemps à l'avance, et
# un horizon court les ferait disparaître précisément parce qu'elles sont importantes.
#
# CE N'EST PAS LA MÊME CHOSE QUE LE BONUS D'URGENCE, et c'est pour ça qu'il en fallait un
# deuxième : le bonus DÉPARTAGE (il donne des points à ce qui approche), il n'EXCLUT rien.
# À six mois, il vaut zéro — donc il laissait passer, sans rien dire, tout ce qui est
# lointain. La Saint-Ours 2027 entrait sur sa seule qualité intrinsèque.
#
# Compté depuis le DÉBUT, jamais depuis la fin : une exposition déjà ouverte se visite
# aujourd'hui, quelle que soit sa date de clôture. C'est la date à partir de laquelle on
# PEUT y aller qui compte.
HORIZON_JOURS = 183


def _jour(valeur) -> "date | None":
    from datetime import date as _d
    try:
        return _d.fromisoformat(str(valeur or "").strip()[:10])
    except ValueError:
        return None


def deplacement_now(event: dict, aujourdhui=None) -> int | None:
    """Score de tri de la section « Ça vaut le déplacement » : la qualité intrinsèque,
    relevée par l'urgence. 0-12, ou None si la fiche n'a pas sa place dans la section.

    None dans cinq cas, tous volontaires :
      • le détail d'évaluation manque (rien à mesurer) ;
      • le score intrinsèque est sous DEPLACEMENT_MIN (voir plus haut) ;
      • l'événement est TERMINÉ — règle 5 de CLAUDE.md, on ne travaille que sur ce qui
        est encore devant nous ;
      • l'événement commence au-delà de HORIZON_JOURS — trop loin pour qu'on décide d'y
        aller (cf. le commentaire de la constante) ;
      • …mais PAS quand la date manque : une fiche sans date n'est pas un événement
        terminé, c'est une donnée manquante, et un événement récurrent n'a par nature
        pas de date unique. Elle garde son score intrinsèque, sans bonus.
    """
    from datetime import date as _d
    base = deplacement_score(event.get("llm_score_detail"))
    if base is None or base < DEPLACEMENT_MIN:
        return None

    auj = aujourdhui or _d.today()
    debut, fin = _jour(event.get("date_event_start")), _jour(event.get("date_event_end"))
    derniere = fin or debut
    if derniere is None:
        return base                      # sans date : intrinsèque seul, jamais exclu
    if derniere < auj:
        return None                      # passé : hors sujet (règle 5)
    # HORIZON. Sur `debut` et non sur `derniere` : une exposition ouverte depuis mai et
    # fermant en septembre a un début DANS LE PASSÉ — elle se visite aujourd'hui, elle
    # reste. Seul ce qui n'a pas encore commencé peut être trop loin.
    if debut and (debut - auj).days > HORIZON_JOURS:
        return None

    restant = (derniere - auj).days
    bonus = next((pts for seuil, pts in _FENETRES if restant <= seuil), 0)

    # RARETÉ : un événement de quelques jours est, par nature, un déplacement — on y va
    # POUR LUI. Une programmation continue se visite en passant. Un seul point : c'est un
    # départage, pas un critère de plus.
    if debut and fin and (fin - debut).days <= PONCTUEL_MAX_JOURS:
        bonus += 1
    elif debut and not fin:
        bonus += 1                       # date unique = ponctuel par définition

    return base + bonus


def deplacement_etat(event: dict, aujourdhui=None) -> tuple[int | None, int | None, str]:
    """(note intrinsèque, note de tri, MOTIF) — pour l'afficher au back-office.

    Demande de Franck le 2026-08-03 : « c'est dommage de pas la voir dans le back-office ».
    Il avait raison sur le fond, et pas seulement pour le confort — cette note décide seule
    de la vitrine de la home, et jusqu'ici elle ne se lisait NULLE PART. Une note invisible
    ne se conteste pas : on ne peut que constater le résultat sur le site et deviner, ce
    qu'il a dû faire pour s'apercevoir que « au diapason » occupait la carte Savoie.

    Le motif est renvoyé plutôt que recalculé côté gabarit : la règle d'exclusion doit
    rester à un seul endroit, sinon l'affichage et le tri finiront par diverger, et c'est
    l'affichage qu'on croira."""
    from datetime import date as _d
    base = deplacement_score(event.get("llm_score_detail"))
    if base is None:
        return None, None, "pas évalué — la section écarte les non-mesurés, elle ne les classe pas derniers"
    if base < DEPLACEMENT_MIN:
        return base, None, f"sous le plancher ({base} < {DEPLACEMENT_MIN})"

    auj = aujourdhui or _d.today()
    debut, fin = _jour(event.get("date_event_start")), _jour(event.get("date_event_end"))
    derniere = fin or debut
    if derniere is None:
        return base, base, "sans date — score intrinsèque seul, jamais exclu"
    if derniere < auj:
        return base, None, "événement terminé"
    if debut and (debut - auj).days > HORIZON_JOURS:
        return base, None, (f"commence dans {(debut - auj).days} jours — au-delà de "
                            f"l'horizon de {HORIZON_JOURS}")
    now = deplacement_now(event, aujourdhui=auj)
    return base, now, f"dans la section · {base} intrinsèque + {(now or base) - base} d'urgence"


def deplacement_raisons(llm_score_detail) -> list[str]:
    """Les justifications écrites par l'évaluateur, critère par critère — pour afficher
    au back-office POURQUOI un événement est (ou n'est pas) « à déplacement ». C'est ce
    qui rend le score auditable, contrairement à une note de persona."""
    data = llm_score_detail
    if isinstance(data, str):
        try:
            data = json.loads(data or "{}")
        except (ValueError, TypeError):
            return []
    if not isinstance(data, dict):
        return []
    out = []
    for cle in _CRITERES:
        bloc = data.get(cle)
        if isinstance(bloc, dict) and bloc.get("note"):
            out.append(f"{cle} ({bloc.get('points', '?')}) : {bloc['note']}")
    return out
