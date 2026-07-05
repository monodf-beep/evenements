"""Modules de la home publique (Agenda Sabauda) = requêtes déterministes.

Chaque rubrique de la home mobile est soit :
  - AUTO (date)     : fenêtre temporelle sur date_event_start/end (« Ce week-end », « Aujourd'hui ») ;
  - AUTO (catégorie): filtre sur llm_categorie (les 11 catégories = celles de l'évaluateur,
                      identiques aux catégories WordPress) — « Sagres », « Concerts », « Expositions » ;
  - AUTO (tout)     : tout l'agenda à venir ;
  - SEMI (best-of)  : le pipeline propose le top score de la période, Franck valide/réordonne ;
  - MANUEL          : éditorial (Curiosités, listicles) ;
  - EXTERNE         : widget tiers (Météo).

Ce module sert (a) à PRÉVISUALISER sur le dashboard ce que chaque rubrique contient
aujourd'hui (combien d'événements, un aperçu), (b) de spécification pour les
shortcodes/requêtes TEC quand on montera le WordPress (mêmes filtres).

Aucune dépendance à Flask : on prend une connexion sqlite + la date du jour.
"""
from __future__ import annotations
from datetime import date, timedelta

# Le fond commun : un événement « présentable » = actif, non-doublon.
_ACTIVE = "statut NOT IN ('rejected','merged') AND duplicate_of IS NULL"
# Fin effective (à défaut de fin, on retombe sur le début) → les événements
# d'un seul jour (end vide) sont bien pris en compte.
_END = "COALESCE(NULLIF(date_event_end,''), NULLIF(date_event_start,''))"
_START = "COALESCE(NULLIF(date_event_start,''), NULLIF(date_event_end,''))"


def _weekend(today: date) -> tuple[str, str]:
    """(vendredi, dimanche) ISO du week-end de la semaine courante (ven→dim)."""
    wd = today.weekday()  # lun=0 … dim=6
    friday = today + timedelta(days=(4 - wd)) if wd <= 4 else today - timedelta(days=(wd - 4))
    return friday.isoformat(), (friday + timedelta(days=2)).isoformat()


# Définition des modules, dans l'ordre de la home. `feed` pilote l'affichage
# (badge AUTO/SEMI/MANUEL) et le calcul du compte.
MODULES = [
    {"key": "hero",      "label": "Carrousel (À la une)", "feed": "bestof", "window": "weekend",
     "help": "Top score du week-end, proposé automatiquement — tu valides / réordonnes."},
    {"key": "weekend",   "label": "Ce week-end",          "feed": "date", "window": "weekend",
     "help": "Chevauche le week-end en cours. 100 % automatique (dates)."},
    {"key": "today",     "label": "Aujourd'hui",          "feed": "date", "window": "today",
     "help": "Chevauche aujourd'hui. 100 % automatique (dates)."},
    {"key": "sagres",    "label": "Sagres & gastronomie", "feed": "cat", "category": "Gastronomie & Sagre",
     "help": "Catégorie « Gastronomie & Sagre », à venir. Automatique."},
    {"key": "concerts",  "label": "Concerts",             "feed": "cat", "category": "Concerts & Musique",
     "help": "Catégorie « Concerts & Musique », à venir. Automatique."},
    {"key": "expos",     "label": "Nouvelles expositions", "feed": "cat", "category": "Expositions & Patrimoine",
     "help": "Catégorie « Expositions & Patrimoine », à venir. Automatique (les listicles restent manuels)."},
    {"key": "all",       "label": "Tout l'agenda",        "feed": "all",
     "help": "Tous les événements à venir. Automatique."},
    {"key": "musees",    "label": "Musées",               "feed": "semi", "category": "Expositions & Patrimoine",
     "help": "À terme = taxonomie Lieu (WordPress). Approché ici par la catégorie Expositions & Patrimoine."},
    {"key": "alentours", "label": "Aux alentours",        "feed": "manual",
     "help": "Proximité géographique = « 📍 Près de moi » opt-in (v2). Pas d'auto au lancement."},
    {"key": "curiosites", "label": "Curiosités",          "feed": "manual",
     "help": "Éditorial (dossiers) — pas de requête auto."},
    {"key": "meteo",     "label": "Météo",                "feed": "external",
     "help": "Widget externe — hors base."},
]

_AUTO_FEEDS = {"date", "cat", "all", "bestof"}


def _count_and_sample(conn, where: str, params: list, limit: int = 3):
    n = conn.execute(f"SELECT COUNT(*) n FROM events_raw WHERE {where}", params).fetchone()[0]
    order = ("COALESCE(llm_score,-1) DESC, "
             f"COALESCE(NULLIF(date_event_start,''),'9999') ASC, id DESC")
    rows = conn.execute(
        f"SELECT title, COALESCE(territoire,'—') territoire, llm_score "
        f"FROM events_raw WHERE {where} ORDER BY {order} LIMIT ?", params + [limit]).fetchall()
    sample = [{"title": (r[0] or "")[:70], "territoire": r[1], "score": r[2]} for r in rows]
    return n, sample


def preview(conn, today: date, thr: int = 7) -> list[dict]:
    """Pour chaque module : compte réel + petit aperçu (pour les modules AUTO/SEMI).

    `conn` : connexion sqlite (row factory quelconque). `thr` : seuil best-of."""
    fri, sun = _weekend(today)
    tstr = today.isoformat()
    out = []
    for m in MODULES:
        item = {**m, "count": None, "sample": []}
        feed = m["feed"]
        where, params = _ACTIVE, []
        if feed == "date" and m.get("window") == "weekend":
            where += f" AND {_START} <= ? AND {_END} >= ?"; params += [sun, fri]
        elif feed == "date" and m.get("window") == "today":
            where += f" AND {_START} <= ? AND {_END} >= ?"; params += [tstr, tstr]
        elif feed == "cat":
            where += f" AND llm_categorie = ? AND {_END} >= ?"; params += [m["category"], tstr]
        elif feed == "all":
            where += f" AND {_END} >= ?"; params += [tstr]
        elif feed == "bestof":  # top score du week-end
            where += f" AND {_START} <= ? AND {_END} >= ? AND COALESCE(llm_score,0) >= ?"
            params += [sun, fri, thr]
        elif feed == "semi" and m.get("category"):  # approximation par catégorie
            where += f" AND llm_categorie = ? AND {_END} >= ?"; params += [m["category"], tstr]
        else:  # manual / external : pas de requête
            out.append(item); continue
        item["count"], item["sample"] = _count_and_sample(conn, where, params)
        out.append(item)
    return out
