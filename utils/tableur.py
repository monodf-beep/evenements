#!/usr/bin/env python3
"""Le TABLEUR du back-office : toutes les colonnes, toutes les fiches, et les TROUS.

Franck, 2026-09-22 : « il faut un vrai tableur dans le backoffice ».

POURQUOI IL N'Y EN AVAIT PAS. `/events` montre huit colonnes fixes (photo, titre, date,
territoire, source, statut, score, actions) choisies pour AGIR sur une fiche à la fois.
C'est une file de travail, pas une vue d'ensemble : on n'y voit pas les quatre-vingts
autres colonnes, on ne peut pas trier sur l'une d'elles, et surtout **on ne voit pas ce
qui manque**. Or la question posée ce jour-là était exactement celle-là : « un tableau qui
reprendrait toutes les informations, et nous dire est-ce qu'il manque ».

CE QUE CE MODULE FAIT, ET CE QU'IL NE FAIT PAS. Du calcul pur sur des lignes
`events_raw` déjà lues — aucun accès base, aucun réseau, aucun Flask. Il dit quelles
colonnes afficher, dans quel ordre, avec quel libellé, et combien de fiches ont
réellement quelque chose dedans. La route et le gabarit vivent dans `app/`.

TROIS PRÉCAUTIONS, APPRISES AILLEURS DANS CE DÉPÔT

1. **Le catalogue ne fait pas foi, la base fait foi.** `colonnes_visibles()` prend la
   liste RÉELLE des colonnes (PRAGMA table_info) et n'affiche que l'intersection. Une
   colonne renommée disparaît au lieu de faire planter la page ; une colonne ajoutée par
   une migration et oubliée ici réapparaît dans le groupe « Autres » au lieu d'être
   invisible. Un tableur qui cache une colonne existante ment sur son sujet.

2. **Un taux de remplissage porte son PÉRIMÈTRE** (règle 6 du CLAUDE.md). `taux()` rend
   toujours le couple (remplies, total) et jamais un pourcentage seul : « 82 % » sans
   dénominateur ni filtre est exactement le genre de chiffre qui a produit les « 793
   points à vérifier » du 11/08.

3. **Une case vide n'est pas une faute.** Trois cas se ressemblent à l'écran et ne
   demandent pas le même geste : la donnée EXISTE sur la source et personne ne l'a lue
   (à remplir), la source ne la publie PAS (rien à faire, ne jamais mettre en file), ou
   le champ ne s'applique pas à cette fiche (un récurrent n'a pas de date, un multi-lieux
   n'a pas de lieu — cf. `utils.completeness`). Le tableur distingue le troisième cas
   (« sans objet ») des deux autres ; séparer les deux premiers demande de lire la page,
   et c'est un autre chantier.
"""
from __future__ import annotations

# Champs modifiables À LA MAIN depuis le back-office. SOURCE UNIQUE : `app/app.py`
# importe cette liste pour sa route /complete plutôt que d'en tenir une seconde — deux
# listes pour la même chose divergent, et c'est la racine de quatre fautes du 08/09.
EDITABLES: tuple[str, ...] = (
    "date_event_start", "date_event_end", "lieu", "ville",
    "territoire", "llm_categorie", "url_officiel",
    # Affiches manuelles : sites JS/gated où l'extraction auto échoue.
    "url_image", "url_image_portrait", "url_image_wide",
)

# Catalogue : (colonne, libellé, groupe). L'ORDRE est l'ordre d'affichage.
CATALOGUE: tuple[tuple[str, str, str], ...] = (
    ("id",                 "#",                  "Identité"),
    ("title",              "Titre (source)",     "Identité"),
    ("article_title",      "Titre (rédigé)",     "Identité"),
    ("organisateur",       "Organisateur",       "Identité"),
    ("source_name",        "Source",             "Identité"),
    ("source_type",        "Type de source",     "Identité"),
    ("url_source",         "URL source",         "Identité"),
    ("url_officiel",       "URL officielle",     "Identité"),

    ("date_event_start",   "Début",              "Dates"),
    ("date_event_end",     "Fin",                "Dates"),
    ("date_source",        "Provenance date",    "Dates"),
    ("recurring",          "Récurrent",          "Dates"),
    ("recurring_note",     "Note récurrence",    "Dates"),

    ("lieu",               "Lieu",               "Lieu"),
    ("ville",              "Ville",              "Lieu"),
    ("territoire",         "Territoire",         "Lieu"),
    ("multi_lieux",        "Multi-lieux",        "Lieu"),
    ("venue_source",       "Provenance lieu",    "Lieu"),

    ("ip_tarif",           "Tarif",              "Infos pratiques"),
    ("ip_horaires",        "Horaires",           "Infos pratiques"),
    ("ip_reservation",     "Réservation",        "Infos pratiques"),
    ("ip_accessibilite",   "Accessibilité",      "Infos pratiques"),
    ("ip_langue",          "Langue parlée",      "Infos pratiques"),

    ("llm_categorie",      "Catégorie",          "Éditorial"),
    ("llm_score",          "Score",              "Éditorial"),
    ("user_score",         "Score Franck",       "Éditorial"),
    ("home_score",         "Score home",         "Éditorial"),
    ("statut",             "Statut",             "Éditorial"),
    ("enrich_status",      "Rédaction",          "Éditorial"),
    ("llm_justification",  "Justification",      "Éditorial"),

    ("url_image",          "Image",              "Images"),
    ("url_image_portrait", "Image portrait",     "Images"),
    ("url_image_wide",     "Image paysage",      "Images"),
    ("image_source",       "Provenance image",   "Images"),
    ("image_credit",       "Crédit image",       "Images"),

    ("seo_title",          "Titre SEO",          "SEO"),
    ("seo_meta",           "Méta description",   "SEO"),
    ("seo_keyphrase",      "Requête cible",      "SEO"),
    ("seo_slug",           "Slug",               "SEO"),

    ("wp_post_id_as",      "WP Agenda",          "Publication"),
    ("published_as_date",  "Publié le",          "Publication"),
    ("wp_post_id_cs",      "WP Cultura",         "Publication"),
    ("translated_lang",    "Langue",             "Publication"),
)

GROUPES: tuple[str, ...] = ("Identité", "Dates", "Lieu", "Infos pratiques",
                            "Éditorial", "Images", "SEO", "Publication", "Autres")

# Jeux de colonnes prêts à l'emploi. Le premier est le défaut.
JEUX: dict[str, tuple[str, ...]] = {
    "completion": ("id", "title", "date_event_start", "date_event_end", "lieu",
                   "ville", "territoire", "llm_categorie", "url_image",
                   "organisateur", "url_officiel"),
    "editorial":  ("id", "title", "llm_categorie", "llm_score", "user_score",
                   "home_score", "statut", "enrich_status", "date_event_start"),
    "publication": ("id", "title", "statut", "wp_post_id_as", "published_as_date",
                    "translated_lang", "date_event_start", "date_event_end"),
    "seo":        ("id", "title", "seo_title", "seo_meta", "seo_keyphrase",
                   "seo_slug", "wp_post_id_as"),
    "pratique":   ("id", "title", "date_event_start", "lieu", "ville", "ip_tarif",
                   "ip_horaires", "ip_reservation", "ip_accessibilite", "url_officiel"),
}
JEU_LIBELLES: dict[str, str] = {
    "completion":  "Complétude",
    "editorial":   "Éditorial",
    "publication": "Publication",
    "seo":         "SEO",
    "pratique":    "Infos pratiques",
    "tout":        "Tout",
}

# ─────────────────────────────────────────────────────────────────────────────
# LES INFOS PRATIQUES SONT DÉJÀ LÀ, et ce fichier a affirmé le contraire.
#
# Le 22/09, ce module annonçait « aucune colonne ne stocke un tarif », en citant la
# docstring d'`utils/infos_pratiques.py`. Elle était vraie le jour où elle a été
# écrite ; `scripts/moisson_officielle.py` a créé la colonne `infos_pratiques`
# depuis, et la remplit tous les jours à 8h52. J'ai pris un COMMENTAIRE pour un
# FAIT au lieu d'interroger le schéma — la racine du CLAUDE.md, une fois de plus.
#
# La colonne contient du JSON : {famille: [extraits de la page]}. Illisible dans une
# cellule, et surtout inutilisable pour compter les trous. On la DÉPLIE donc en
# colonnes virtuelles, une par famille, avant tout le reste : le comptage, le tri par
# trous, le filtre « il manque X » et l'export fonctionnent alors sans rien savoir de
# leur origine. Une valeur dépliée est un EXTRAIT de la page, jamais une
# interprétation — c'est la promesse d'infos_pratiques et elle ne change pas ici.
# ─────────────────────────────────────────────────────────────────────────────
COL_INFOS = "infos_pratiques"

DERIVEES: tuple[tuple[str, str, str], ...] = (
    ("ip_tarif",         "Tarif",          "tarif"),
    ("ip_horaires",      "Horaires",       "horaires"),
    ("ip_reservation",   "Réservation",    "reservation"),
    ("ip_accessibilite", "Accessibilité",  "accessibilite"),
    ("ip_langue",        "Langue",         "langue"),
)


def deplier_infos(ligne: dict) -> dict:
    """Ajoute les colonnes virtuelles `ip_*` à une ligne, depuis le JSON de la base.

    Modifie et rend la ligne. Appelée une fois, à la lecture : tout le reste du module
    voit alors des colonnes ordinaires. Un JSON illisible ne fait rien planter — il
    laisse simplement les colonnes vides, ce qui est la vérité (on n'a rien pu lire).
    """
    import json
    brut = ligne.get(COL_INFOS)
    donnees = {}
    if brut:
        try:
            lu = json.loads(brut)
            if isinstance(lu, dict):
                donnees = lu
        except (ValueError, TypeError):
            donnees = {}
    for cle, _, famille in DERIVEES:
        extraits = donnees.get(famille) or []
        ligne[cle] = (extraits[0] if isinstance(extraits, list) and extraits else "")
    return ligne

# Colonnes trop longues pour une cellule : on tronque à l'affichage (jamais à l'export).
_LONGUES = {"llm_justification", "seo_meta", "url_source", "url_officiel",
            "url_image", "url_image_portrait", "url_image_wide", "recurring_note"} | {
            c for c, _, _ in DERIVEES}
_TRONQUE = 60

# Colonnes booléennes stockées en 0/1 : « oui » vaut mieux que « 1 » pour un lecteur.
_BOOLEENNES = {"recurring", "multi_lieux"}


def colonnes_visibles(colonnes_en_base) -> list[tuple[str, str, str]]:
    """Catalogue RESTREINT à ce qui existe vraiment, plus le reste de la base.

    `colonnes_en_base` : les noms rendus par PRAGMA table_info(events_raw). Une colonne
    du catalogue absente de la base est écartée (migration pas encore passée) ; une
    colonne de la base absente du catalogue est ajoutée dans « Autres », pour qu'un
    champ ajouté demain soit visible sans toucher à ce fichier.
    """
    presentes = set(colonnes_en_base)
    # Les colonnes virtuelles existent si et seulement si leur SOURCE existe : sans la
    # colonne `infos_pratiques` en base, il n'y a rien à déplier, et les afficher vides
    # ferait croire à un manque de données là où c'est la colonne qui manque.
    if COL_INFOS in presentes:
        presentes |= {c for c, _, _ in DERIVEES}
    connues = set()
    out: list[tuple[str, str, str]] = []
    for col, libelle, groupe in CATALOGUE:
        connues.add(col)
        if col in presentes:
            out.append((col, libelle, groupe))
    for col in colonnes_en_base:
        if col not in connues and col != COL_INFOS:
            out.append((col, col, "Autres"))
    return out


def jeu(nom: str, visibles: list[tuple[str, str, str]]) -> list[str]:
    """Colonnes d'un jeu nommé, restreintes à celles qui existent. 'tout' = tout."""
    dispo = [c for c, _, _ in visibles]
    if nom == "tout":
        return dispo
    return [c for c in JEUX.get(nom, JEUX["completion"]) if c in dispo]


def sans_objet(ligne: dict, col: str) -> bool:
    """Ce champ NE S'APPLIQUE PAS à cette fiche — ce n'est donc pas un trou.

    Miroir de `utils.completeness` : un récurrent n'a pas de date (une note la remplace),
    un multi-lieux n'a ni lieu ni ville (festival itinérant). Confondre « sans objet » et
    « manquant » gonfle le compte des trous et fabrique du travail qui n'existe pas.
    """
    if col in ("date_event_start", "date_event_end"):
        return bool(ligne.get("recurring"))
    if col in ("lieu", "ville"):
        return bool(ligne.get("multi_lieux"))
    return False


def est_vide(ligne: dict, col: str) -> bool:
    """Case vide : ni None, ni chaîne blanche. Un 0 numérique N'EST PAS vide."""
    v = ligne.get(col)
    if v is None:
        return True
    return not str(v).strip()


def trous(ligne: dict, colonnes: list[str]) -> int:
    """Nombre de cases réellement manquantes (« sans objet » exclu)."""
    return sum(1 for c in colonnes if est_vide(ligne, c) and not sans_objet(ligne, c))


def taux(lignes: list[dict], colonnes: list[str]) -> dict[str, tuple[int, int]]:
    """Par colonne : (remplies, concernées). JAMAIS un pourcentage seul — règle 6.

    « Concernées » exclut les fiches pour lesquelles le champ est sans objet : mesurer le
    remplissage de `lieu` sur des festivals itinérants qui n'en ont pas par construction
    donnerait un taux faux et enverrait chercher ce qui n'existe pas.
    """
    out: dict[str, tuple[int, int]] = {}
    for c in colonnes:
        concernees = [l for l in lignes if not sans_objet(l, c)]
        remplies = sum(1 for l in concernees if not est_vide(l, c))
        out[c] = (remplies, len(concernees))
    return out


def pourcent(remplies: int, total: int) -> str:
    """« 82 % » ou « — » si aucun cas ne s'est présenté.

    Un zéro ne dit pas s'il vient d'un échec ou d'une absence de cas (CLAUDE.md) : sans
    dénominateur, on n'affiche pas de pourcentage du tout.
    """
    return f"{round(100 * remplies / total)} %" if total else "—"


def affiche(ligne: dict, col: str) -> str:
    """Valeur pour une CELLULE : booléens en clair, longues tronquées. Jamais pour l'export."""
    if sans_objet(ligne, col):
        return "sans objet"
    v = ligne.get(col)
    if v is None or not str(v).strip():
        return ""
    if col in _BOOLEENNES:
        return "oui" if str(v).strip() not in ("0", "") else "non"
    s = str(v).strip()
    if col in _LONGUES and len(s) > _TRONQUE:
        return s[:_TRONQUE - 1] + "…"
    return s


def exporte(ligne: dict, col: str) -> str:
    """Valeur pour le CSV : brute et entière. Un export tronqué n'est pas un export."""
    v = ligne.get(col)
    return "" if v is None else str(v)


def fiches_trouees(lignes: list[dict], colonnes: list[str]) -> int:
    """Combien de fiches ont AU MOINS une case manquante parmi les colonnes affichées."""
    return sum(1 for l in lignes if trous(l, colonnes))


def ou_ca_peche(taux_par_colonne: dict[str, tuple[int, int]],
                combien: int = 4) -> list[tuple[str, int, int, float]]:
    """Les colonnes où il manque le plus de choses. (colonne, manquantes, concernées, %).

    Franck, 2026-09-22 : « mets juste des petits chiffres au début en disant où ça pêche ».

    CLASSÉ PAR NOMBRE DE MANQUES, pas par pourcentage. Les deux sont défendables et ils
    ne désignent pas la même chose : un pourcentage met en tête une colonne vide à 0 %
    sur un seul cas concerné, un décompte met en tête le plus gros tas. C'est le tas
    qu'on veut — la question au bout du chiffre est « par où je commence », pas « quelle
    colonne est la plus vide dans l'absolu ».

    DEUX EXCLUSIONS, et chacune évite un faux signalement :
      • une colonne PLEINE n'est pas un problème, donc elle ne figure pas ;
      • une colonne dont AUCUN cas ne s'est présenté non plus — un zéro ne dit pas s'il
        vient d'un échec ou d'une absence de cas, et on ne bâtit pas une alerte dessus.
    """
    out = []
    for col, (remplies, concernees) in taux_par_colonne.items():
        if not concernees:
            continue
        manquantes = concernees - remplies
        if manquantes > 0:
            out.append((col, manquantes, concernees, 100.0 * remplies / concernees))
    out.sort(key=lambda t: (-t[1], t[3]))
    return out[:combien]
