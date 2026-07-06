"""Conseiller « Franck, voici ce que TU dois faire ».

Traduit l'état de la base en actions HUMAINES, en français direct. On n'affiche
QUE ce qui n'est pas automatique : une décision (valider), un manque à combler
(sourcer un gros événement, remplir un territoire vide), un complément (photo,
date), ou un clic de pipeline (évaluer, collecter). Tout le reste se fait seul.

Chaque message : {level, icon, title, detail, url, cta}. Les seuils sont des
constantes en tête, faciles à recalibrer.

Aucune dépendance Flask : connexion sqlite + date du jour.
"""
from __future__ import annotations
from datetime import date, timedelta

# --- Seuils (recalibrables) ---
HEADLINER_MIN = 3       # nb de têtes d'affiche (score ≥ 8) souhaité pour le week-end
HEADLINER_SCORE = 8
LOW_STOCK = 20          # en dessous : trop peu d'événements à venir
CATEGORY_MODULES = [    # modules « catégorie » de la home qui ne doivent pas rester vides
    ("Gastronomie & Sagre", "Sagres & gastronomie"),
    ("Concerts & Musique", "Concerts"),
    ("Expositions & Patrimoine", "Nouvelles expositions"),
]
TERRITORY_LABELS = {
    "Savoie": "Savoie", "Piemonte": "Piémont",
    "Vallee-Aoste": "Vallée d'Aoste", "Nice": "Nice",
}

_ACTIVE = "statut NOT IN ('rejected','merged') AND duplicate_of IS NULL"
_RETAINED = "statut IN ('evaluated','published_cs','published_sub') AND duplicate_of IS NULL"
_END = "COALESCE(NULLIF(date_event_end,''), NULLIF(date_event_start,''))"
_START = "COALESCE(NULLIF(date_event_start,''), NULLIF(date_event_end,''))"


def _weekend(today: date) -> tuple[str, str]:
    wd = today.weekday()
    fri = today + timedelta(days=(4 - wd)) if wd <= 4 else today - timedelta(days=(wd - 4))
    return fri.isoformat(), (fri + timedelta(days=2)).isoformat()


def advise(conn, today: date, thr: int = 7, territories: list[str] | None = None) -> list[dict]:
    """Renvoie la liste ordonnée (plus urgent d'abord) des actions humaines."""
    territories = territories or list(TERRITORY_LABELS)
    t = today.isoformat()
    fri, sun = _weekend(today)

    def n(sql, params=()):
        return conn.execute(sql, params).fetchone()[0]

    msgs: list[dict] = []

    # 1. À VALIDER — décisions sur du contenu prêt (candidats Cultura Sabauda).
    to_validate = n(
        f"SELECT COUNT(*) FROM events_raw WHERE statut='evaluated' AND llm_score >= ? "
        f"AND {_END} >= ? AND COALESCE(wp_post_id_cs,0)=0", (thr, t))
    if to_validate:
        msgs.append({
            "level": "valider", "icon": "🗓️",
            "title": f"Valide et publie {to_validate} événement(s).",
            "detail": "Ils sont notés ≥ 7 et à venir : à mettre en avant (Cultura Sabauda) ou à basculer en catalogue.",
            "url": "/validation", "cta": "Ouvrir le plan du week-end"})

    # 2. À SOURCER — il manque une tête d'affiche pour le carrousel du week-end.
    headliners = n(
        f"SELECT COUNT(*) FROM events_raw WHERE {_ACTIVE} AND {_START} <= ? AND {_END} >= ? "
        f"AND COALESCE(llm_score,0) >= ?", (sun, fri, HEADLINER_SCORE))
    if headliners < HEADLINER_MIN:
        msgs.append({
            "level": "sourcer", "icon": "⭐",
            "title": f"On a besoin d'un gros événement : {headliners} tête(s) d'affiche ce week-end.",
            "detail": f"Le carrousel « À la une » vise ≥ {HEADLINER_MIN} événements majeurs (score ≥ {HEADLINER_SCORE}). Trouve-en un et source-le.",
            "url": "/events?sort=score", "cta": "Voir les mieux notés"})

    # 3. À COMPLÉTER — photos manquantes sur des fiches retenues.
    nophoto = n(
        f"SELECT COUNT(*) FROM events_raw WHERE {_RETAINED} AND {_END} >= ? "
        "AND COALESCE(url_image,'')=''", (t,))
    if nophoto:
        msgs.append({
            "level": "completer", "icon": "🖼",
            "title": f"Choisis une photo pour {nophoto} fiche(s) retenue(s).",
            "detail": "Sans image, la fiche est faible (SEO + réseaux). Lance « Compléter les visuels » ou accepte la bannière territoire.",
            "url": "/events?img=0", "cta": "Voir les fiches sans photo"})

    # 4. À COMPLÉTER — événements retenus sans date (invisibles sur le site).
    undated = n(
        f"SELECT COUNT(*) FROM events_raw WHERE {_RETAINED} "
        "AND COALESCE(date_event_start,'')='' AND COALESCE(date_event_end,'')=''")
    if undated:
        msgs.append({
            "level": "completer", "icon": "📅",
            "title": f"Précise la date de {undated} événement(s) retenu(s).",
            "detail": "Sans date, ils n'apparaissent dans aucune période — donc invisibles sur la home et les hubs.",
            "url": "/events?dated=undated", "cta": "Voir les non datés"})

    # 5. À SOURCER — un territoire n'a rien à venir (la home montre les 4).
    for terr in territories:
        if n(f"SELECT COUNT(*) FROM events_raw WHERE {_ACTIVE} AND territoire = ? AND {_END} >= ?",
             (terr, t)) == 0:
            label = TERRITORY_LABELS.get(terr, terr)
            msgs.append({
                "level": "sourcer", "icon": "📍",
                "title": f"Aucun événement à venir en {label}.",
                "detail": "La home affiche les 4 territoires : un territoire vide se voit. Source au moins un événement.",
                "url": f"/events?territoire={terr}", "cta": f"Voir {label}"})

    # 6. À SOURCER — un module « catégorie » de la home est vide.
    for cat, label in CATEGORY_MODULES:
        if n(f"SELECT COUNT(*) FROM events_raw WHERE {_ACTIVE} AND llm_categorie = ? AND {_END} >= ?",
             (cat, t)) == 0:
            msgs.append({
                "level": "sourcer", "icon": "🧩",
                "title": f"Le module « {label} » de la home est vide.",
                "detail": f"Aucun événement « {cat} » à venir. Source-en, sinon la rubrique disparaît.",
                "url": "/events", "cta": "Événements"})

    # 7. À LANCER (1 clic) — des événements attendent l'évaluation.
    pending = n(f"SELECT COUNT(*) FROM events_raw WHERE statut='pending' AND {_END} >= ?", (t,))
    if pending:
        msgs.append({
            "level": "lancer", "icon": "🧠",
            "title": f"Lance l'évaluation : {pending} événement(s) en attente.",
            "detail": "Claude va les noter (0-10) et les router. Un clic depuis le tableau de bord.",
            "url": "/", "cta": "Aller au pipeline"})

    # 8. À LANCER (1 clic) — trop peu d'événements à venir.
    stock = n(f"SELECT COUNT(*) FROM events_raw WHERE {_ACTIVE} AND {_END} >= ?", (t,))
    if stock < LOW_STOCK:
        msgs.append({
            "level": "lancer", "icon": "📡",
            "title": f"Peu d'événements à venir ({stock}).",
            "detail": "Le fond de stock est bas — lance une collecte (scraping / newsletters) pour réalimenter.",
            "url": "/", "cta": "Aller au pipeline"})

    order = {"valider": 0, "sourcer": 1, "completer": 2, "lancer": 3}
    msgs.sort(key=lambda m: order.get(m["level"], 9))
    return msgs
