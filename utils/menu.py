#!/usr/bin/env python3
"""La carte du back-office : quelles pages existent, où elles vivent, comment on les trouve.

Franck, 2026-09-22 : « rends le back-office le plus simple possible ».

LE PROBLÈME MESURÉ CE JOUR-LÀ : 28 entrées de menu pour UNE personne, réparties en
quatre blocs, dont la liste ne vivait qu'en dur dans `base.html`. Deux conséquences :

  • on ne pouvait pas répondre à « qu'est-ce qui ne sert plus ? » sans relire un gabarit ;
  • rien ne reliait le menu aux ROUTES. Une page pouvait disparaître du menu sans
    disparaître du code, ou l'inverse — c'est la mécanique exacte des scripts orphelins
    du 18/08, transposée à l'interface.

Ce module est donc la carte, et `tests/test_menu.py` la confronte aux routes réelles de
`app/app.py` : toute page servie doit être ICI, ou déclarée HORS_MENU avec sa raison.
Pas de troisième cas — c'est ce qui empêche une page de devenir invisible par accident.

CE QU'IL NE FAIT PAS. Il ne dit pas ce qui SERT : ça, seuls les journaux d'accès du
serveur le disent, et personne ne les avait regardés. Une page rangée ici n'est pas une
page utile ; elle est seulement une page qu'on sait nommer.

TROIS ÉCRANS RESTENT AU PREMIER NIVEAU, le reste se replie. Le choix vient de ce que
Franck ouvre tous les jours, pas de l'ordre du code : ce qui l'attend aujourd'hui, la
file de travail, et l'état de la complétude.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
# Les groupes, dans l'ordre d'affichage. Le sous-titre sert à la palette (⌘K) et
# aux infobulles : un intitulé de deux mots ne suffit jamais à situer une page.
# --------------------------------------------------------------------------- #
GROUPES: tuple[tuple[str, str, str], ...] = (
    ("traiter",  "À traiter",  "Ce qui attend une décision de ta part"),
    ("diffuser", "Diffuser",   "Ce qui sort : infolettre, réseaux, publicité"),
    ("analyser", "Analyser",   "Comprendre ce que le site couvre et ce qu'il coûte"),
    ("reglages", "Réglages",   "Le ton, les règles, le fonctionnement"),
)

# Les trois écrans qui ne se replient jamais.
EPINGLEES: tuple[str, ...] = ("dash", "semaine", "tableur")


def _p(actif, url, libelle, groupe, icone, resume, badge="", site="", mots=""):
    return {"actif": actif, "url": url, "libelle": libelle, "groupe": groupe,
            "icone": icone, "resume": resume, "badge": badge, "site": site,
            "mots": mots}


# --------------------------------------------------------------------------- #
# Les pages. `actif` est le jeton que la page passe à `active=` dans son
# render_template — c'est lui qui allume l'entrée, et le test le vérifie.
# `resume` dit ce qu'on y FAIT, à l'infinitif : « Couverture » ne se comprend
# pas tout seul, « voir quels territoires sont sous-servis » si.
# --------------------------------------------------------------------------- #
PAGES: tuple[dict, ...] = (
    _p("dash", "/", "Aujourd'hui", "traiter", "🏠",
       "Ce qu'il y a à faire maintenant", badge="todo",
       mots="accueil tableau de bord dashboard"),
    _p("semaine", "/semaine", "Cette semaine", "traiter", "🗓️",
       "Une tâche, une décision : valider une photo, relire un texte",
       mots="file travail taches a faire"),
    _p("tableur", "/tableur", "Tableur", "traiter", "🧮",
       "Toutes les colonnes et ce qui manque, avec export",
       mots="tableau colonnes complétude trous csv excel manquant"),

    _p("tocomplete", "/a-completer", "À compléter", "traiter", "🛠️",
       "Les fiches retenues à qui il manque un champ obligatoire",
       badge="tocomplete", site="as", mots="incomplet manque date lieu image"),
    _p("triage", "/triage", "Triage", "traiter", "🧭",
       "Débloquer en une case : récurrent, multi-lieux, ou à la main",
       site="as", mots="debloquer bloque recurrent itinerant"),
    _p("verifier", "/verifier", "À vérifier", "traiter", "⚠️",
       "Les faits que le pipeline juge incertains", badge="verifier",
       mots="controle doute incertain"),
    _p("audit_visuel", "/audit-visuel", "Audit visuel", "traiter", "🖼️",
       "Planche contact : juger les photos d'un coup d'œil", badge="audit",
       mots="images photos vignettes affiches planche contact"),
    _p("validation", "/validation", "À valider", "traiter", "✅",
       "File Cultura Sabauda : les articles longs à arbitrer",
       badge="validate", site="cs", mots="cultura sabauda article long"),
    _p("events", "/events", "Tous les événements", "traiter", "📥",
       "Tout ce qui a été collecté, avec les actions de publication",
       mots="liste catalogue publier statut rejeter"),

    _p("newsletter", "/newsletter", "Newsletter", "diffuser", "📧",
       "Préparer et envoyer l'infolettre", mots="infolettre brevo mail envoi"),
    _p("reseaux", "/reseaux", "Réseaux sociaux", "diffuser", "📣",
       "Légendes et publication Instagram, Facebook, Threads",
       mots="instagram facebook threads social legende"),
    _p("regie", "/regie", "Régie pub", "diffuser", "💶",
       "Les campagnes publicitaires en cours", badge="regie",
       mots="publicite annonceur campagne"),
    _p("partenariat", "/partenariat", "Partenariat / widget", "diffuser", "🤝",
       "Le widget à intégrer chez un partenaire", mots="embed widget integration"),

    _p("pilotage", "/pilotage", "Pilotage", "analyser", "🧭",
       "Santé éditoriale : ce que le site couvre et ce qui manque",
       mots="sante editoriale kpi"),
    _p("couverture", "/couverture", "Couverture", "analyser", "📊",
       "Par section, territoire et langue : où sont les trous",
       mots="territoire langue section manques"),
    _p("couverture_geo", "/couverture-geo", "Couverture géo", "analyser", "🗺️",
       "Quelle commune mérite sa page", mots="carte commune ville geographie"),
    _p("calendrier_categories", "/calendrier-categories", "Calendrier des catégories",
       "analyser", "📅", "Ce qui est publié et encore devant nous, par catégorie",
       mots="categorie jour agenda visibilite"),
    _p("sources_provinces", "/sources-provinces", "Sources par province", "analyser", "📡",
       "Quelles provinces n'ont aucune source", mots="flux rss province moisson"),
    _p("seo", "/seo", "SEO", "analyser", "🔍",
       "Titres, métas et position dans Google", badge="seo",
       mots="google referencement meta titre yoast"),
    _p("systeme", "/systeme", "État du système", "analyser", "📈",
       "Les crons, les erreurs, et ce que l'API coûte",
       mots="cron sante panne watchdog couts api tokens depense facture budget"),
    _p("wireframe", "/wireframe-home", "Wireframe home", "analyser", "🏠",
       "Le plan de la page d'accueil et de ses encarts",
       mots="maquette accueil sections plan"),

    _p("process", "/process", "Fonctionnement", "reglages", "🔄",
       "Comment la chaîne marche, de la moisson à la publication",
       mots="aide documentation chaine pipeline explication"),
    _p("pipeline", "/pipeline", "Pipeline auto", "reglages", "⚙️",
       "Ce qui tourne tout seul, et à quelle heure", mots="cron automatique horaire"),
    _p("voix", "/voix", "Voix éditoriale", "reglages", "🗣️",
       "Le ton de la maison, lu dans Obsidian", mots="ton style obsidian redaction"),
    _p("personas", "/personas", "Personas lecteurs", "reglages", "👓",
       "Le panel qui relit les articles", mots="panel relecture lecteurs"),
    _p("doctrine", "/doctrine", "Doctrine", "reglages", "📚",
       "Les règles d'écriture, pour les agents", mots="regles claude vocabulaire charte"),
    _p("cowork", "/cowork", "Cowork", "reglages", "🤖",
       "Le journal des sessions Claude", mots="claude session journal"),
    _p("reglages", "/reglages", "Réglages", "reglages", "⚙️",
       "Modèle, profil, plafonds de dépense", mots="parametres modele budget profil"),
)

# --------------------------------------------------------------------------- #
# Routes de PAGE servies VOLONTAIREMENT hors du menu, avec leur raison. Toute page
# doit être ici ou dans PAGES — c'est ce que la fixture vérifie. Les ACTIONS (POST
# seul : bascule, écriture, point d'entrée Slack) n'y figurent pas : ce ne sont pas
# des destinations, et les lister ici ferait croire à des pages cachées.
# --------------------------------------------------------------------------- #
HORS_MENU: dict[str, str] = {
    "/login": "écran d'entrée",
    "/logout": "action, pas une page",
    "/preview": "s'ouvre depuis une fiche, jamais depuis le menu",
    "/tableur.csv": "export du tableur",
    "/doctrine.txt": "servie aux agents, avec jeton",
    "/site-dedie": "étude ponctuelle, atteinte par lien direct",
    # Mesuré le 22/09 : cette route N'EST PLUS UNE PAGE, c'est une redirection vers
    # /systeme?vue=couts. La fusion date du 11/08 — Franck venait de dire « il y a trop
    # trop trop de pages » — mais le menu a continué d'afficher une entrée séparée, donc
    # le nombre de pages n'a jamais baissé DE SON POINT DE VUE. L'adresse survit (un
    # favori ne doit pas casser) ; l'entrée de menu, non.
    "/couts": "redirige vers l'onglet Coûts de « État du système » (fusionné le 11/08)",
}


def groupes_avec_pages() -> list[tuple[str, str, str, list[dict]]]:
    """(cle, libellé, sous-titre, pages) — dans l'ordre, épinglées exclues."""
    out = []
    for cle, libelle, resume in GROUPES:
        pages = [p for p in PAGES if p["groupe"] == cle and p["actif"] not in EPINGLEES]
        out.append((cle, libelle, resume, pages))
    return out


def epinglees() -> list[dict]:
    """Les écrans du premier niveau, dans l'ordre de EPINGLEES."""
    par_actif = {p["actif"]: p for p in PAGES}
    return [par_actif[a] for a in EPINGLEES if a in par_actif]


def groupe_de(actif: str) -> str:
    """Le groupe d'une page, pour savoir lequel ouvrir. '' si épinglée ou inconnue."""
    for p in PAGES:
        if p["actif"] == actif and p["actif"] not in EPINGLEES:
            return p["groupe"]
    return ""


def index_recherche() -> list[dict]:
    """Ce que la palette (⌘K) indexe : une entrée par page, avec de quoi la trouver.

    `cible` concatène tout ce sur quoi on peut taper — libellé, résumé, groupe, mots
    supplémentaires — en minuscules et SANS ACCENTS. Chercher « completude » doit
    trouver « Complétude » : un opérateur pressé ne tape pas les accents, et une
    recherche qui échoue là-dessus passe pour une page absente.
    """
    import unicodedata

    def _plat(s: str) -> str:
        s = unicodedata.normalize("NFD", s or "")
        return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()

    libelles = {cle: lib for cle, lib, _ in GROUPES}
    out = []
    for p in PAGES:
        cible = " ".join((p["libelle"], p["resume"], p["mots"],
                          libelles.get(p["groupe"], ""), p["url"]))
        out.append({"url": p["url"], "libelle": p["libelle"], "resume": p["resume"],
                    "icone": p["icone"], "groupe": libelles.get(p["groupe"], ""),
                    "cible": _plat(cible)})
    return out
