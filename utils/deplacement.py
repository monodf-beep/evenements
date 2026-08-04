#!/usr/bin/env python3
"""Score « ÇA VAUT LE DÉPLACEMENT » (0-12) — DÉTERMINISTE, zéro appel LLM.

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

⚠️ À LIRE AVANT DE RETOUCHER À CE BARÈME — constat du 2026-08-04, en fin de journée.

**Côté WordPress, la section « Ça vaut le déplacement » de la home est du HTML STATIQUE.**
Pas de grille, pas de listing : un `<div>` en dur qui nomme deux événements figés, avec ce
commentaire dans le contenu des pages 928 et 1717 :

    <!-- CA VAUT LE DEPLACEMENT (transfrontalier) — PLACEHOLDER v1, statique.
         Mécanisme de données pas encore tranché avec Franck (sélection manuelle de
         2 événements "vedettes" vs champ auto). -->

Conséquence à regarder en face : **deux jours de travail sur ce score — pondération,
barrière de la langue, plancher à 10, rafraîchissement quotidien, 264 republications —
n'ont AUCUN effet sur ce que voit le visiteur dans cette section.** Le calcul est juste,
`cs_home_deplacement_pick()` sélectionne correctement, mais son résultat n'est branché sur
rien. Les « cartes rendues » qu'on croyait mesurer étaient des correspondances de slug
ailleurs dans la page.

Rien de ce qui précède n'est à jeter : la méta `as_deplacement_now` est publiée, juste, et
tenue à jour. Ce qui manque est une décision éditoriale que Franck n'a jamais eu à prendre
— sélection manuelle de deux vedettes, ou grille automatique sur le score. Tant qu'elle
n'est pas prise, **affiner ce barème n'améliore rien de visible**. Le mesurer d'abord,
c'est ce qu'on n'a pas fait.
"""
from __future__ import annotations
import json

# PONDÉRATION — adoptée le 2026-08-04 après simulation sur le stock réel.
#
# CE QU'ELLE REMPLACE, ET POURQUOI. La première version disait « poids 1 partout : simple,
# explicable, et suffisant ». C'était faux sur le fond, et la phrase rassurante a empêché
# de vérifier pendant deux jours : les poids étaient bien égaux, mais les MAXIMA ne
# l'étaient pas (3, 2, 2, 1). Mesure sur la base réelle : `notoriete_lieu` pesait **44 %**
# de tous les points distribués, contre 24 % au rayonnement et 13 % à la spécificité. Le
# critère qui note LA SALLE pesait donc plus lourd que les deux qui disent pourquoi on se
# déplacerait — « Visite guidée du Stade Allianz Riviera » obtenait 6/8 dont 3 pour le
# stade, au même rang qu'un festival international.
#
# LE PRINCIPE RETENU : ce qui fait qu'on FAIT LA ROUTE, c'est de ne pas pouvoir le voir
# ailleurs (spécificité), que ça dépasse le voisinage (rayonnement), et — sur un agenda
# transfrontalier — de pouvoir en profiter sans parler la langue. La salle compte encore
# (le Castello di Rivoli est une destination) mais ne peut plus porter une fiche à elle
# seule : plafonnée à 1 point, « lieu remarquable, oui ou non ».
#
# Échelle 0-12 et non 0-8 : le plancher a dû être re-décidé plutôt que reconduit par
# inertie — 6/8 vaut 75 %, 6/12 en vaut 50, et recopier le chiffre aurait doublé la
# permissivité sans que personne ne s'en aperçoive.
_PONDERATION = {
    "rayonnement":              (2, None),   # 0-2 ×2 → 0-4  (33 %)
    "specificite_territoriale": (3, None),   # 0-1 ×3 → 0-3  (25 %)
    "edition_tradition":        (1, None),   # 0-2 ×1 → 0-2  (17 %)
    "notoriete_lieu":           (1, 1),      # plafonné à 1  ( 8 %)
}
# `organisateur_moyens` reste VOLONTAIREMENT absent : le budget de l'organisateur n'entre
# pas dans la décision d'un visiteur de faire trois heures de route.
_CRITERES = tuple(_PONDERATION)
POIDS_LANGUE = 1                             # 0-2 ×1 → 0-2  (17 %)
MAX_SCORE = 12


def _score_criteres(llm_score_detail) -> int | None:
    """Part du score qui vient de `llm_score_detail` (JSON de scripts/evaluator.py), déjà
    pondérée. None si le détail est absent ou illisible — None ≠ 0 : « pas mesuré » n'est
    pas « nul », la section doit écarter les non-mesurés, pas les classer derniers.

    Accepte une chaîne JSON ou un dict déjà décodé."""
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
    for cle, (poids, plafond) in _PONDERATION.items():
        bloc = data.get(cle)
        pts = bloc.get("points") if isinstance(bloc, dict) else bloc
        if isinstance(pts, (int, float)):
            p = int(pts)
            total += (min(p, plafond) if plafond is not None else p) * poids
            trouve = True
    return total if trouve else None


def deplacement_score(event: dict) -> int | None:
    """Note intrinsèque 0-12 de l'ÉVÉNEMENT, ou None s'il n'a pas été évalué.

    Prend l'événement entier et non le seul `llm_score_detail` : la barrière de la langue
    se lit sur la catégorie et le titre, pas dans le détail du score. Signature changée le
    2026-08-04 — les appelants passent désormais la ligne complète."""
    base = _score_criteres(event.get("llm_score_detail"))
    if base is None:
        return None
    return base + accessibilite_langue(event) * POIDS_LANGUE


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
# intrinsèque (0-12). Une fiche médiocre qui ferme demain ne doit pas chasser une fiche
# remarquable ouverte encore un mois — d'où aussi le plancher ci-dessous.
# --------------------------------------------------------------------------- #

# En dessous de ce score intrinsèque, aucune urgence ne rattrape : la section s'appelle
# « ça vaut le déplacement », pas « ça ferme bientôt ».
#
# RELEVÉ DE 3 À 6 LE 2026-08-03, sur constat de Franck en regardant la home. Le 3 avait été
# posé au jugé, faute de connaître le stock, et il ne servait à rien : il suffisait de ne
# pas être NUL pour entrer. « Au diapason » entrait ainsi dans le vivier de la Savoie — pas
# parce qu'il vaut le déplacement, mais parce qu'il était le moins mauvais de sa colonne.
#
# PUIS PORTÉ À 10/12 LE 2026-08-04, avec la nouvelle pondération. Ce n'est PAS le même
# seuil transposé : 6/8 valait 75 %, 10/12 en vaut 83, et recopier « 6 » aurait doublé la
# permissivité (6/12 retenait 73 fiches contre 32 auparavant). Mesuré avant de trancher :
#   • 8/12  → 81 fiches, soit un tiers du catalogue vivant — confortable, mais peu sélectif
#             pour une section qui promet « ça vaut le déplacement » ;
#   • 10/12 → 31 fiches, et chaque territoire en garde au moins 4 ;
#   • 11/12 → 18 fiches, mais le vivier ITALIEN tombe à 4 pour 2 places : deux fins
#             d'événement et la section se vide. C'est le seuil de rupture.
# 10 est donc le point le plus exigeant qui tienne encore.
#
# CE QUE CE SEUIL COÛTE, ET POURQUOI C'EST ACCEPTÉ. La section affiche UN événement par
# territoire : un plancher haut peut donc laisser une carte VIDE plutôt que médiocre.
# Arbitrage de Franck, et il est cohérent avec le nom de la section — une carte vide ne
# ment pas, une carte faible si. `scripts/audit_deplacement.py` mesure, territoire par
# territoire, ce que chaque plancher laisse : c'est lui qui dira si 7 tient.
DEPLACEMENT_MIN = 10
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
    base = deplacement_score(event)
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


# --------------------------------------------------------------------------- #
# LA BARRIÈRE DE LA LANGUE — le critère qui manquait à un agenda TRANSFRONTALIER
#
# Constat de Franck, 2026-08-03 : « ça vaut le détour si c'est un spectacle où on doit
# comprendre ce qui est dit, c'est quand même compliqué de faire le déplacement. Par
# contre un salon, Terra Madre sur la gastronomie, la Fête du lac… »
#
# CE QUE LES QUATRE CRITÈRES NE DISENT PAS. `rayonnement` mesure que l'événement PORTE
# au-delà de la frontière ; il ne dit rien de ce qui décide vraiment pour un visiteur
# d'en face : pourra-t-il en profiter ? Une pièce de théâtre en italien rayonne autant
# qu'une foire gastronomique et vaut infiniment moins le déplacement à un francophone.
# Sur un agenda qui couvre deux pays et deux langues, c'est le point aveugle central.
#
# POURQUOI PAR CATÉGORIE, ET NON PAR UN NOUVEAU CRITÈRE DE L'ÉVALUATEUR. Ajouter une
# cinquième question au prompt LLM créerait un stock à deux vitesses : les fiches déjà
# évaluées ne l'auraient pas, seraient notées sur moins de points, et se retrouveraient
# systématiquement derrière les nouvelles. Il faudrait tout ré-évaluer — des centaines
# d'appels — pour un renseignement que la catégorie contient DÉJÀ. C'est le même
# raisonnement qui avait fait choisir `llm_score_detail` plutôt qu'une note de persona :
# rétroactif, gratuit, et auditable.
#
# LA NUANCE ASSUMÉE : la barrière est traitée comme SYMÉTRIQUE, alors qu'elle ne l'est
# pas — une conférence en français est accessible à un Savoyard et pas à un Turinois. La
# traiter par langue supposerait de connaître la langue PARLÉE sur place (que rien ne
# stocke) et de produire deux notes par fiche, une par version du site. C'est la
# simplification, elle est ici pour être vue, pas pour être oubliée.
#
# ⚠️ CECI NE CHASSE RIEN DU SITE. « Conférences & Rencontres » reste l'une des onze
# catégories, et une conférence de musée ou un café philo y gardent toute leur place
# (docs/CHARTE_EDITORIALE.md). Ce critère ne joue QUE sur le classement d'une section qui
# invite à faire de la route — pas sur ce qui est publié.
_LANGUE_PAR_CATEGORIE = {
    # 2 — rien à comprendre pour en profiter : ça se regarde, ça se goûte, ça se marche.
    "Gastronomie & Sagre":          2,
    "Marchés & Foires":             2,
    "Sport":                        2,
    "Expositions & Patrimoine":     2,
    "Fêtes & Traditions populaires": 2,
    # 1 — la langue aide sans commander. Un concert chanté se vit, un festival mélange
    # les formes, le jeune public passe par le jeu et l'image.
    "Concerts & Musique":           1,
    "Festivals":                    1,
    "Jeune public & Famille":       1,
    "Cinéma":                       1,   # VO sous-titrée, salles bilingues
    # 0 — il faut comprendre ce qui est dit, sinon on a fait la route pour rien.
    "Spectacle vivant":             0,
    "Conférences & Rencontres":     0,
}
LANGUE_MAX = 2
# Ce que vaut une catégorie inconnue ou absente. 1 et non 0 : une catégorie manquante est
# une donnée qui manque, pas une barrière constatée — la pénaliser au maximum reviendrait
# à punir la fiche pour un défaut de classement dont son événement n'est pas responsable.
LANGUE_DEFAUT = 1


# LA CATÉGORIE DIT LE SUJET, PAS LE FORMAT — et le critère faisait donc l'INVERSE de son
# intention sur toute une famille de fiches. Constaté à la première simulation, le
# 2026-08-04 : « Visite guidée du Stade Allianz Riviera » remontait 3e à Nice et « Visite
# au Château de Montrottier » 3e en Savoie, promues par un critère censé mesurer l'ABSENCE
# de barrière de langue. Toutes deux sont rangées en « Expositions & Patrimoine », notée 2.
#
# Or une exposition se REGARDE et une visite guidée s'ÉCOUTE : une heure de commentaire,
# en français ou en italien. Même étiquette, formats opposés. Une conférence tenue dans un
# musée aurait le même sort.
#
# Le titre, lui, dit le format — et ça se lit sans LLM. Ces marqueurs RAMÈNENT à 0, quelle
# que soit la catégorie. Volontairement peu nombreux et précis (« rencontre » seul serait
# trop large : « rencontres sportives ») : un faux 0 déclasserait injustement un bon
# événement, et une famille oubliée se rattrape en ajoutant une chaîne ici.
_FORMATS_PAROLE = (
    "visite guidée", "visite commentée", "visita guidata", "visita commentata",
    "conférence", "conferenza", "table ronde", "tavola rotonda",
    "débat", "dibattito", "café philo", "dédicace", "lecture publique",
    "présentation du livre", "presentazione del libro", "rencontre avec", "incontro con",
)
# CE QUI RESTE DEHORS, ET C'EST VOULU : « Visite au Château de Montrottier » ne dit pas si
# la visite est guidée ou libre. Un château se parcourt aussi seul, sans un mot — mettre
# tout ce qui commence par « visite » à 0 déclasserait des sorties parfaitement
# accessibles. On préfère donc un faux 2 à un faux 0, et cette famille-là restera mal
# classée tant que le titre ne dit rien. À rouvrir si Franck constate qu'elle remonte trop.


def accessibilite_langue(event: dict) -> int:
    """0-2 : dans quelle mesure on peut profiter de l'événement sans parler la langue.

    Deux sources, dans cet ordre : le TITRE quand il trahit un format de parole (une visite
    guidée reste de la parole, même rangée en « Expositions »), la CATÉGORIE sinon. Aucun
    appel LLM, donc rétroactif sur tout le stock déjà publié.

    Voir les deux commentaires ci-dessus : pourquoi la catégorie plutôt qu'un cinquième
    critère de l'évaluateur, et pourquoi elle ne suffit pas seule."""
    titre = f"{event.get('title') or ''} {event.get('article_title') or ''}".lower()
    if any(m in titre for m in _FORMATS_PAROLE):
        return 0
    return _LANGUE_PAR_CATEGORIE.get((event.get("llm_categorie") or "").strip(), LANGUE_DEFAUT)


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
    base = deplacement_score(event)
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
