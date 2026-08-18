#!/usr/bin/env python3
"""La MÉMOIRE des recherches : ce qui a déjà été tenté sur une fiche, et par quel angle.

D'OÙ ÇA VIENT — Franck, 2026-08-18 : « toutes les sources donnent les informations. Toutes
les informations, on les trouve. C'est juste que des fois c'est mal cherché, c'est mal
trouvé. Et donc il faut relancer sur des événements spécifiques. J'aimerais que tu sois
autonome dessus. »

LE CONSTAT QUI MANQUAIT. `lister_a_completer` rend chaque matin la même liste : numéro, ce
qui manque, titre, adresse. Sans mémoire. Une fiche qui a résisté hier est présentée à
l'identique aujourd'hui — donc l'agent quotidien ouvre la même page, qui se tait toujours,
et repart. Vingt créneaux par run consommés à refaire ce qui a déjà échoué, pendant que
d'autres fiches attendent. C'est la règle 3 dans sa forme la plus coûteuse : non pas un
état terminal sans rouvreur, mais un rouvreur qui rejoue exactement la tentative ratée.

CE QUE CE MODULE APPORTE — deux choses, et la seconde compte plus que la première :

  1. il ENREGISTRE chaque tentative : quelle fiche, quel champ manquant, quel ANGLE, et ce
     que ça a donné (trouvé / la source est muette / la page est inaccessible) ;
  2. il désigne le PROCHAIN ANGLE, différent de tous ceux déjà essayés. C'est ce qui rend
     la relance légitime au sens de CLAUDE.md : « écrire pourquoi le prochain passage
     donnerait un AUTRE résultat ». Ici la réponse n'est pas « le LLM est stochastique »,
     c'est « on n'a pas encore regardé là ».

L'ÉCHELLE DES ANGLES vient de l'expérience du 2026-08-11, pas d'une théorie : sur les neuf
fiches de la file ce soir-là, SEPT ont été résolues non par l'adresse enregistrée mais par
une recherche web sur le titre. L'ordre va donc du moins cher au plus cher, et du plus
fiable au moins fiable :

    page_fiche        la page qu'on a déjà en base
    site_organisateur le site de celui qui organise (fait foi)
    commune_ot        mairie, office de tourisme, salle
    recherche_nom     recherche web sur le TITRE de l'événement
    fiche_soeur       la traduction, un doublon, une édition précédente
    reseaux           page Facebook/Instagram de l'organisateur (dernier recours)

QUAND TOUS LES ANGLES SONT ÉPUISÉS, la fiche sort de la file — avec son motif, comptée, et
un rouvreur : `EPUISEMENT_JOURS` plus tard elle repasse, parce qu'une source PUBLIE parfois
tard (un office de tourisme met son programme en ligne trois semaines avant). Ce délai est
le seul moyen honnête de distinguer « la source ne le dira jamais » de « la source ne le
dit pas ENCORE ». Sans cette sortie, la file accumule des silences de source — les 315
« tarifs non publiés » du 2026-08-11, que ni Franck ni un modèle ne peuvent trouver.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

# Du moins cher au plus cher. L'ordre EST la stratégie de relance.
ANGLES: tuple[str, ...] = (
    "page_fiche",
    "site_organisateur",
    "commune_ot",
    "recherche_nom",
    "fiche_soeur",
    "reseaux",
)

RESULTATS: tuple[str, ...] = ("trouve", "muet", "inaccessible")

# Une source peut publier plus tard : on rouvre après ce délai, une seule fois par cycle.
EPUISEMENT_JOURS = 30


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tentatives_completion (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id   INTEGER NOT NULL,
            champ      TEXT    NOT NULL,
            angle      TEXT    NOT NULL,
            resultat   TEXT    NOT NULL,
            note       TEXT,
            at         TEXT    NOT NULL
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tentatives_event "
                 "ON tentatives_completion(event_id, champ)")
    conn.commit()


def enregistrer(conn: sqlite3.Connection, event_id: int, champ: str, angle: str,
                resultat: str, note: str = "", maintenant: datetime | None = None) -> None:
    """Note une tentative. `note` sert à écrire CE QU'ON A LU — « la page ne donne que la
    date, aucun lieu » vaut mieux que « muet », pour celui qui reprendra la fiche."""
    if angle not in ANGLES:
        raise ValueError(f"angle inconnu : {angle} (attendus : {', '.join(ANGLES)})")
    if resultat not in RESULTATS:
        raise ValueError(f"résultat inconnu : {resultat} (attendus : {', '.join(RESULTATS)})")
    _ensure(conn)
    conn.execute("INSERT INTO tentatives_completion (event_id, champ, angle, resultat, "
                 "note, at) VALUES (?,?,?,?,?,?)",
                 (int(event_id), champ, angle, resultat, note[:400],
                  (maintenant or datetime.now()).isoformat(timespec="seconds")))
    conn.commit()


def deja_tentes(conn: sqlite3.Connection, event_id: int, champ: str) -> list[dict]:
    """Les tentatives déjà faites sur ce couple (fiche, champ), de la plus ancienne à la
    plus récente. C'est ce que l'agent doit LIRE avant de chercher."""
    _ensure(conn)
    return [dict(r) for r in conn.execute(
        "SELECT angle, resultat, note, at FROM tentatives_completion "
        "WHERE event_id=? AND champ=? ORDER BY at ASC", (int(event_id), champ))]


def prochain_angle(tentatives: list[dict]) -> str | None:
    """Le premier angle JAMAIS essayé, ou None si tous l'ont été.

    On ne re-propose pas un angle déjà tenté, même ancien : re-lire une page qui se taisait
    hier, c'est la tentative que ce module existe pour empêcher. Le retour en arrière se
    fait par `a_rouvrir` (le délai), pas en boucle.
    """
    faits = {t.get("angle") for t in tentatives}
    for angle in ANGLES:
        if angle not in faits:
            return angle
    return None


def epuisee(tentatives: list[dict]) -> bool:
    """Tous les angles essayés, aucun n'a trouvé."""
    if any(t.get("resultat") == "trouve" for t in tentatives):
        return False
    return prochain_angle(tentatives) is None


def a_rouvrir(tentatives: list[dict], maintenant: datetime | None = None) -> bool:
    """C'EST LE ROUVREUR. Une fiche épuisée redevient candidate après EPUISEMENT_JOURS :
    une source publie parfois tard, et c'est le seul moyen de distinguer « ne le dira
    jamais » de « ne le dit pas encore ». Sans humain, sans commande."""
    if not epuisee(tentatives):
        return False
    dernier = max((t.get("at") or "") for t in tentatives)
    try:
        quand = datetime.fromisoformat(dernier)
    except (ValueError, TypeError):
        return False
    return (maintenant or datetime.now()) - quand >= timedelta(days=EPUISEMENT_JOURS)


def resume(tentatives: list[dict]) -> str:
    """Une ligne lisible pour la file : ce qui a été tenté, et ce qui vient après.

    Écrite pour être LUE par l'agent quotidien au moment de choisir sa fiche — donc elle
    dit l'angle suivant en clair, jamais un code."""
    if not tentatives:
        return "jamais cherché → commencer par : page_fiche"
    faits = ", ".join(f"{t['angle']}={t['resultat']}" for t in tentatives)
    suivant = prochain_angle(tentatives)
    if suivant:
        return f"déjà tenté : {faits} → PROCHAIN ANGLE : {suivant}"
    return (f"déjà tenté : {faits} → TOUS LES ANGLES ÉPUISÉS "
            f"(la source ne publie pas cette information ; nouvelle chance dans "
            f"{EPUISEMENT_JOURS} jours)")
