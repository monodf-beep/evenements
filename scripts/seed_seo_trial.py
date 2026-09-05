#!/usr/bin/env python3
"""Seed UNIQUE des trouvailles du premier essai SEO manuel (28-29/07/2026) : 3 pages
d'agendasabauda.eu (accueil, une fiche événement, une page territoire), audit technique +
schema par les agents seo-technical et seo-schema du skill claude-seo. L'agent seo-content
a planté en cours de route (rapport final tronqué, 25k tokens sans livrable exploitable) —
consigné dans seo_runs.notes comme donnée de fiabilité, pas ignoré.

À lancer UNE SEULE FOIS (idempotent par prudence : ne réinsère pas si déjà fait) :
    .venv/bin/python -m scripts.seed_seo_trial
"""
from __future__ import annotations
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.scraper_events import init_db

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

HOME = "https://agendasabauda.eu/"
EVENT = "https://agendasabauda.eu/evenement/aldo-cazzullo-en-scene-avec-francesco-le-premier-italien/"
TERR = "https://agendasabauda.eu/que-faire-dans-le-piemont/"

FINDINGS = [
    # --- Accueil (analyse manuelle préliminaire, avant les agents) ---
    (HOME, "on-page", "critical", "Aucune balise H1 sur la page d'accueil",
     "grep sur le HTML brut : 0 occurrence de <h1>. Signal de structure de base absent.",
     "Ajouter un H1 réel (ex. le nom du site + son objet), pas juste visuel.", "manuel (essai initial)"),
    (HOME, "on-page", "high", "Pas de meta description propre sur l'accueil",
     "Seules og:description/twitter:description existent ; aucune <meta name=\"description\">.",
     "Ajouter une meta description Yoast dédiée à la page d'accueil.", "manuel (essai initial)"),
    (HOME, "on-page", "medium", "Titre de l'accueil trop court et générique",
     "<title>Accueil - Agenda Sabauda</title> (25 caractères, cible 50-60) — incohérent avec l'og:title (\"Agenda Sabauda : quoi faire, où manger\").",
     "Aligner le <title> sur l'og:title, avec mots-clés (agenda culturel, Savoie, Piémont…).", "manuel (essai initial)"),

    # --- seo-technical (3 pages) ---
    (HOME, "technique", "critical",
     "Le sitemap référence les anciennes URLs /territoire/xxx/ qui redirigent en 301",
     "territoire-sitemap.xml liste 8 URLs (FR+IT) qui répondent toutes en 301 vers de nouveaux slugs (ex. /que-faire-dans-le-piemont/). Ce sont les pages piliers du site.",
     "Régénérer le sitemap Yoast avec les URLs finales ; vérifier les liens internes en dur pointant encore vers l'ancien slug.", "seo-technical"),
    (EVENT, "on-page", "high", "Fiche événement sans meta description propre (template)",
     "Aucune <meta name=\"description\"> sur la fiche testée — seule une og:description générique auto-générée par The Events Calendar. Problème systémique du template, pas juste l'accueil.",
     "Configurer un template Yoast pour le CPT tribe_events (ex. %%excerpt%% — %%title%%, le %%date%%).", "seo-technical"),
    (HOME, "technique", "high", "Aucun header de sécurité HTTP (HSTS, X-Frame-Options, CSP…)",
     "Confirmé sur 2 pages testées : ni Strict-Transport-Security, ni X-Content-Type-Options, ni X-Frame-Options, ni CSP, ni Referrer-Policy. Fuite d'info serveur (x-powered-by: PHP/8.0).",
     "Ajouter au minimum HSTS, X-Content-Type-Options: nosniff, Referrer-Policy (config Apache/.htaccess ou plugin).", "seo-technical"),
    (HOME, "technique", "medium", "hreflang fr/it sans x-default (systémique)",
     "Confirmé sur accueil, fiche événement et page territoire : hreflang fr (self) + it, jamais de x-default.",
     "Ajouter hreflang=\"x-default\" pointant vers la version FR dans la config Polylang/Yoast.", "seo-technical"),
    (HOME, "performance", "medium", "CSS/JS bloquants au chargement, sitewide",
     "Accueil : 20 CSS + 2 scripts jQuery sans async/defer. Fiche événement : 21 CSS + 7 scripts. Territoire : 12 CSS + 5 scripts. Risque LCP/INP sur tout le site, pas juste l'accueil.",
     "Différer les scripts jQuery non critiques, purger/combiner les CSS Elementor inutilisés par page.", "seo-technical"),
    (TERR, "schema", "info", "FAQPage présent mais sans effet SERP depuis mai 2026",
     "Schema FAQPage valide sur la page territoire, mais Google a retiré ce rich result pour la plupart des sites.",
     "Réévaluer l'intérêt de maintenir ce balisage (poids de page vs bénéfice nul côté SERP).", "seo-technical"),

    # --- seo-schema (3 pages) ---
    (HOME, "schema", "critical",
     "Aucune donnée structurée Event/ItemList sur les pages de listing",
     "37 liens /evenement/ uniques sur l'accueil, 32 sur la page territoire — aucun ItemList/Event dans le JSON-LD (seule la fiche individuelle en a). JSON-LD prêt à l'emploi fourni par l'agent (voir rapport complet).",
     "Générer un ItemList d'événements à venir (~10-20 items) en JSON-LD sur accueil + pages territoire, via la boucle Tribe Events déjà utilisée pour l'affichage.", "seo-schema"),
    (EVENT, "schema", "high", "startDate/endDate du schema Event ne reflètent pas l'heure réelle",
     "JSON-LD : startDate=2026-08-05T00:00:00, endDate=...T23:59:59 (plage 24h par défaut) alors que la page affiche \"mercredi 5 août 2026, à 21h30\".",
     "Corriger startDate à l'heure réelle (21h30) ; ne pas inventer 23:59:59 si l'heure de fin est inconnue.", "seo-schema"),
    (EVENT, "schema", "high", "Propriété offers (prix) absente du schema Event",
     "Prix visible sur la page (10€ + billetterie Ticketone/Midaticket) mais aucun objet Offer dans le JSON-LD.",
     "Ajouter offers (price, priceCurrency, url, availability) — propriété recommandée par Google pour les rich results Event.", "seo-schema"),
    (EVENT, "schema", "medium", "Texte publicitaire fuite dans les données structurées",
     "location.description et organizer.description contiennent littéralement « Publicité Annoncer sur Agenda Sabauda → » — probablement sur TOUS les événements du même lieu/organisateur (Forte di Bard / Amelio Ambrosi).",
     "Corriger le template The Events Calendar : le champ description de Place/Organizer ne doit contenir que du texte réel, ou être omis.", "seo-schema"),
    (EVENT, "schema", "medium", "Propriétés Schema.org émises en chaîne vide au lieu d'être omises",
     "location.url=\"\", location.telephone=\"\", organizer.url=\"\", organizer.email=\"\"… — une chaîne vide n'est pas une valeur URL/Text valide, généralement signalé par le Rich Results Test.",
     "Omettre la propriété plutôt que d'émettre une chaîne vide.", "seo-schema"),
    (EVENT, "schema", "medium", "organizer = une Personne au lieu de l'Organisation réelle",
     "organizer pointe vers Person \"Amelio Ambrosi\" (auteur WP) alors que le texte mentionne Forte di Bard / Aosta Classica comme organisateurs réels. Pas de performer pour Aldo Cazzullo.",
     "organizer → Organization (Forte di Bard/Aosta Classica) ; ajouter performer → Person (l'artiste).", "seo-schema"),
    (TERR, "schema", "medium", "Deux BreadcrumbList concurrentes sur la page territoire",
     "Un bloc (dans le @graph Yoast) a le ListItem position 2 SANS propriété item (URL manquante) ; un second bloc séparé (Polylang ?) est complet. Ambiguïté pour Google.",
     "Supprimer l'un des deux générateurs de BreadcrumbList.", "seo-schema"),
]


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS seo_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT DEFAULT (datetime('now')),
        scope TEXT, pages_count INTEGER, agents_used TEXT,
        tokens_used INTEGER, notes TEXT)""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS seo_findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER, page_url TEXT, category TEXT,
        severity TEXT NOT NULL DEFAULT 'medium', title TEXT NOT NULL,
        description TEXT, recommendation TEXT, source_agent TEXT,
        status TEXT NOT NULL DEFAULT 'todo',
        created_at TEXT DEFAULT (datetime('now')), resolved_at TEXT)""")
    conn.commit()

    already = conn.execute(
        "SELECT COUNT(*) n FROM seo_runs WHERE notes LIKE '%essai manuel 28-29/07/2026%'"
    ).fetchone()["n"]
    if already:
        print("Déjà seedé (trouvé une entrée seo_runs correspondante) — rien à faire.")
        conn.close()
        return 0

    cur = conn.execute(
        "INSERT INTO seo_runs (scope, pages_count, agents_used, tokens_used, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        ("Essai manuel 28-29/07/2026 — accueil + 1 fiche événement + 1 page territoire",
         3, "seo-technical, seo-content (échec), seo-schema", 85794,
         "seo-content a planté en cours d'exécution (25k tokens, rapport final tronqué, "
         "aucun livrable exploitable) — signal de fiabilité à traiter avant autonomie complète."))
    run_id = cur.lastrowid

    for page_url, category, severity, title, description, recommendation, source in FINDINGS:
        conn.execute(
            "INSERT INTO seo_findings (run_id, page_url, category, severity, title, "
            "description, recommendation, source_agent) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, page_url, category, severity, title, description, recommendation, source))
    conn.commit()
    n = conn.execute("SELECT COUNT(*) n FROM seo_findings WHERE run_id=?", (run_id,)).fetchone()["n"]
    conn.close()
    print(f"Seed terminé : run #{run_id}, {n} trouvaille(s) insérée(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
