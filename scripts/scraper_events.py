#!/usr/bin/env python3
"""Collecte quotidienne des événements depuis les sources RSS.

Cron : 0 8 * * * (quotidien 8h)
"""
from __future__ import annotations
import sqlite3
import os
import re
import sys
from pathlib import Path
import feedparser
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from urllib.parse import urlparse

from utils.logger import get_logger
from utils.sources import (is_blocked_image, is_broad_source, is_out_of_scope,
                           is_radar_relevant, load_blocked_image_domains, load_broad_sources,
                           load_out_of_zone, load_perimeter_filter, load_radar_cultural_filter,
                           mentions_perimeter)


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except ValueError:
        return ""

log = get_logger("scraper_events")

SOURCES_FILE = ROOT / "config" / "sources.txt"
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def init_db(conn: sqlite3.Connection) -> None:
    # Concurrence : plusieurs process écrivent la même base (app gunicorn + scripts
    # du pipeline + auto-complétion). Sans réglage, SQLite verrouille toute la base
    # pendant une écriture et lève « database is locked » dès qu'un 2e écrivain se
    # présente. WAL = lecteurs concurrents + 1 écrivain ; busy_timeout = on ATTEND
    # (30 s) le verrou au lieu d'échouer aussitôt. WAL est persistant (posé une fois
    # sur le fichier) ; busy_timeout est par connexion → init_db le repose à chaque fois.
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.OperationalError:
        pass  # base momentanément verrouillée à l'ouverture — non bloquant
    conn.execute("""
    CREATE TABLE IF NOT EXISTS events_raw (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        title            TEXT NOT NULL,
        description      TEXT,
        date_start       TEXT,
        lieu             TEXT,
        ville            TEXT,
        territoire       TEXT,
        url_source       TEXT NOT NULL UNIQUE,
        url_image        TEXT,
        organisateur     TEXT,
        source_name      TEXT,
        scrape_date      TEXT DEFAULT (datetime('now')),
        llm_score        INTEGER,
        llm_categorie    TEXT,
        llm_justification TEXT,
        llm_evaluated_at TEXT,
        llm_model        TEXT,
        statut           TEXT DEFAULT 'pending',
        published_cs_date TEXT,
        wp_post_id_cs    INTEGER,
        source_type      TEXT DEFAULT 'institutionnel',
        duplicate_of     INTEGER
    )
    """)
    # Migrations : colonnes ajoutées après coup sur une base déjà existante.
    for col, decl in (("source_type", "TEXT DEFAULT 'institutionnel'"),
                      ("duplicate_of", "INTEGER"),
                      # Publication vers agendasabauda.eu (événement TEC) — distinct
                      # de wp_post_id_cs qui vise culturasabauda.eu (article).
                      ("wp_post_id_as", "INTEGER"),
                      ("published_as_date", "TEXT"),
                      # Enrichissement + rédaction (scripts/enrich.py)
                      ("enrich_status", "TEXT"),
                      ("enriched_at", "TEXT"),
                      ("enrich_model", "TEXT"),
                      ("enrich_data", "TEXT"),
                      ("article_title", "TEXT"),
                      ("article_md", "TEXT"),
                      # Score HOME (0-10) : qualité du RENDU après rédaction (panel lecteurs
                      # + source officielle + affiches). Distinct de llm_score (importance
                      # AVANT rédaction). Sert au tri des sections « À la une / En évidence »
                      # de la home (méta as_home_score côté WordPress).
                      ("home_score", "REAL"),
                      # Vraie date de l'événement extraite du texte (scripts/dates.py)
                      ("date_event_start", "TEXT"),
                      ("date_event_end", "TEXT"),
                      ("date_source", "TEXT"),
                      # Détail du score d'importance par critère (JSON, scripts/evaluator.py)
                      ("llm_score_detail", "TEXT"),
                      # Visuels (scripts/visuals.py) : crédit + provenance de l'image
                      # ('rss' | 'og' | 'commons' | 'banner').
                      ("image_credit", "TEXT"),
                      ("image_source", "TEXT"),
                      # SEO/GEO/AEO (utils/seo.py) : champs générés à la demande pour
                      # les événements phares (title/méta/réponse directe/FAQ).
                      ("seo_title", "TEXT"),
                      ("seo_meta", "TEXT"),
                      ("seo_answer", "TEXT"),
                      ("seo_faq", "TEXT"),
                      ("seo_keyphrase", "TEXT"),
                      ("seo_slug", "TEXT"),
                      ("seo_tags", "TEXT"),
                      ("seo_model", "TEXT"),
                      ("seo_at", "TEXT"),
                      # Extraction du lieu (scripts/venues.py) : provenance du lieu.
                      ("venue_source", "TEXT"),
                      # Agent d'auto-complétion + porte qualité (scripts/autocomplete.py) :
                      # dernier passage + dernier signal émis (anti-spam Slack).
                      ("autocomplete_at", "TEXT"),
                      ("autocomplete_state", "TEXT"),
                      # Cooldown des recherches WEB (lieu/date/image) : horodatage de la
                      # dernière tentative, pour ne pas re-payer chaque jour un cas
                      # introuvable — on ré-essaie après WEB_COOLDOWN_DAYS.
                      ("venue_web_at", "TEXT"),
                      ("date_web_at", "TEXT"),
                      ("image_web_at", "TEXT"),
                      # Cooldown de la recherche de la version PAYSAGE (multi-format).
                      ("image_wide_at", "TEXT"),
                      # Score ajusté À LA MAIN par Franck (prime sur llm_score à
                      # l'affichage) + horodatage. Nourrit la mémoire d'apprentissage
                      # (utils/score_memory.py) qui recalibre l'évaluateur.
                      ("user_score", "INTEGER"),
                      ("score_overridden_at", "TEXT"),
                      # Événement RÉCURRENT / permanent (activité réservable à l'année,
                      # programmation sans date unique). recurring=1 → la date est
                      # remplacée par une note « vérifiez les dates sur la source » et
                      # l'événement satisfait la porte qualité (cf. utils/completeness).
                      ("recurring", "INTEGER DEFAULT 0"),
                      ("recurring_note", "TEXT"),
                      # Point focal du recadrage 4:3 de la vignette (0..1), réglé à la
                      # main dans le back-office quand le cadrage auto coupe mal.
                      ("card_focal_x", "REAL"),
                      ("card_focal_y", "REAL"),
                      # Mode de vignette forcé à la main : '' (auto) | 'cover'
                      # (recadrer au point focal) | 'letterbox' (affiche entière sur
                      # fond flou — utile quand le titre de l'affiche est coupé).
                      ("card_mode", "TEXT"),
                      # URL PRÉCISE de la fiche événement sur agendasabauda.eu (le
                      # permalien WP, renvoyé par cs-publish.php à chaque publish/
                      # update). Sert à pointer un lien direct (ex. DM Instagram
                      # « commente et je t'envoie le lien ») au lieu de la page
                      # d'accueil — cette fiche porte déjà le bloc « Ajoute-le à ton
                      # agenda » (Google/Apple/Outlook), donc UN lien couvre les deux
                      # usages (lire l'article + l'ajouter à son agenda).
                      ("wp_permalink_as", "TEXT"),
                      # Mot-clé « commente XXX et je t'envoie le lien en DM » (automatisation
                      # commentaire → réponse privée Instagram). Auto-déduit du titre
                      # (utils.social.dm_keyword), modifiable à la main avant publication.
                      ("dm_keyword", "TEXT"),
                      # Copie de la photo ORIGINALE (non recadrée) hébergée dans notre propre
                      # médiathèque WordPress, posée au publish AS. Sert à /reseaux/publish :
                      # reprendre CETTE copie plutôt que retélécharger depuis le site source à
                      # chaque publication Instagram — certains sites source bloquent le
                      # téléchargement par un défi anti-robot (Cloudflare…), notre propre
                      # copie hébergée n'a jamais ce problème.
                      ("wp_raw_image_url_as", "TEXT"),
                      # Multi-format (haut de panier, score ≥ 7) : l'affiche officielle
                      # déclinée dans les DEUX orientations, chacune servie à l'emplacement
                      # où elle rend le mieux (scripts/images_wide, cf. docs/IMAGES.md) :
                      #  • url_image_wide     = version PAYSAGE → grand visuel 16:9 de la fiche ;
                      #  • url_image_portrait = version PORTRAIT (l'affiche) → carte 4:3 + réseaux.
                      # Vide → on retombe sur url_image. Cooldown commun : image_wide_at.
                      ("url_image_wide", "TEXT"),
                      ("url_image_portrait", "TEXT"),
                      # URL du SITE OFFICIEL de l'événement, mémorisée dès qu'une résolution
                      # a donné de la matière officielle (page presse). Réutilisée telle
                      # quelle aux runs suivants → déterministe, plus de recherche web à
                      # refaire, plus de variantes de domaine aléatoires.
                      ("url_officiel", "TEXT"),
                      # File « Cette semaine » (app./semaine) : suivi de relecture PAR
                      # FRANCK, distinct de la vérification automatique (agent vision).
                      # Comparaison au CONTENU actuel (pas juste "vu une fois") : dès que
                      # url_image ou le texte publié change, la tâche redevient à faire
                      # d'elle-même (le _url/_hash stocké ne correspond plus au contenu
                      # courant) — aucun code ailleurs n'a besoin d'invalider quoi que ce
                      # soit explicitement.
                      ("image_reviewed_at", "TEXT"),
                      ("image_reviewed_url", "TEXT"),
                      ("text_reviewed_at", "TEXT"),
                      ("text_reviewed_hash", "TEXT"),
                      # Finition Instagram MANUELLE (/reseaux/publish) : l'API Graph ne sait
                      # ni attacher une musique de la bibliothèque Instagram, ni poser un tag
                      # natif, ni laisser un brouillon éditable (tout appel API publie
                      # immédiatement et définitivement) — Franck choisit PAR publication de
                      # finir lui-même dans l'app plutôt que de passer par l'API. done_at à
                      # NULL tant que ce n'est pas fait -> alimente la file /semaine.
                      ("ig_manual_mode", "INTEGER DEFAULT 0"),
                      ("ig_manual_done_at", "TEXT"),
                      # Mise en avant home : override MANUEL du home_score calculé (panel +
                      # source officielle + affiches). '' (défaut) = auto, le score décide ·
                      # 'featured' = forcé en avant même si le score est moyen · 'excluded' =
                      # jamais mis en avant même bien noté. Poussé en méta WP as_home_override,
                      # à lire en PRIORITÉ par les requêtes JetEngine avant le tri as_home_score.
                      ("home_override", "TEXT"),
                      ("home_override_at", "TEXT"),
                      # Rang manuel PARMI les fiches 'featured' (home_override) : plus petit
                      # = plus haut. NULL = pas encore rangée (retombe en fin de liste). Réglé
                      # via les flèches ▲▼ du back-office (/set-home-order) — n'a de sens que
                      # comparé aux AUTRES fiches 'featured', poussé en méta WP as_home_order.
                      ("home_order", "INTEGER"),
                      # Heure de DÉBUT réelle (« HH:MM »), extraite déterministe (regex,
                      # scripts/dates.extract_time) — JAMAIS devinée par LLM, coût zéro.
                      # Vide = heure inconnue → l'événement reste publié en journée entière
                      # (comportement historique, cs-publish.php). Corrige le Schema.org
                      # Event qui affichait 00:00-23:59 même quand l'heure réelle (ex.
                      # « 21h30 ») était visible dans le texte mais jamais transmise à TEC.
                      ("time_start", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass  # colonne déjà présente
    conn.commit()


# --------------------------------------------------------------------------- #
# Cooldown des recherches WEB (lieu/date/image). Une recherche web qui a échoué
# ne réussira pas si on la relance tout de suite : on mémorise la tentative et on
# ne ré-essaie qu'après WEB_COOLDOWN_DAYS. Évite de re-payer chaque jour les cas
# introuvables ET fait tourner l'agent sur d'AUTRES événements. cf. venues_web /
# dates_web / images_web / autocomplete.
# --------------------------------------------------------------------------- #
WEB_COOLDOWN_DAYS = int(os.getenv("WEB_COOLDOWN_DAYS", "7"))


def web_cooldown_sql(col: str, days: int | None = None) -> str:
    """Fragment SQL (pour un WHERE) : True si jamais tenté ou tentative trop ancienne."""
    d = WEB_COOLDOWN_DAYS if days is None else days
    return f"({col} IS NULL OR {col} < datetime('now','-{int(d)} days'))"


def web_cooldown_ok(ev: dict, col: str, days: int | None = None) -> bool:
    """True si on peut (re)tenter une recherche web pour ce champ (côté Python)."""
    from datetime import datetime, timedelta
    d = WEB_COOLDOWN_DAYS if days is None else days
    ts = (ev.get(col) or "").strip()
    if not ts:
        return True
    try:
        last = datetime.fromisoformat(ts)
    except ValueError:
        return True
    return (datetime.now() - last) >= timedelta(days=d)


def mark_web_attempt(conn, col: str, event_id: int) -> None:
    """Horodate la tentative web (réussie OU non) pour armer le cooldown."""
    conn.execute(f"UPDATE events_raw SET {col}=datetime('now') WHERE id=?", (event_id,))
    conn.commit()


def load_sources() -> list[dict]:
    if not SOURCES_FILE.exists():
        log.warning("Fichier sources absent : %s", SOURCES_FILE)
        return []
    sources = []
    for line in SOURCES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ";" not in line:
            continue
        # Format : url;territoire;nom;tier[;lieu;ville]
        # lieu/ville OPTIONNELS : pour les sources « officielle » (un lieu précis),
        # le lieu = la source → on l'applique par défaut (voir scripts/venues.py,
        # passe 0). Les URL ne contiennent jamais de « ; » (query en &), split sûr.
        parts = [p.strip() for p in line.split(";")]
        if len(parts) >= 2:
            sources.append({
                "url": parts[0],
                "territoire": parts[1],
                "name": parts[2] if len(parts) > 2 and parts[2] else parts[0],
                # type : institutionnel (défaut) | radar (presse/Google News, détection seule)
                "type": (parts[3].lower() if len(parts) > 3 and parts[3] else "institutionnel"),
                # Lieu/ville par défaut de la source (vides si non renseignés).
                "lieu": parts[4] if len(parts) > 4 else "",
                "ville": parts[5] if len(parts) > 5 else "",
            })
    return sources


def extract_image(entry: dict) -> str:
    """Cherche une image dans les champs RSS standards."""
    # media:content
    if hasattr(entry, "media_content") and entry.media_content:
        url = entry.media_content[0].get("url", "")
        if url:
            return url
    # enclosures
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image"):
            return enc.get("href", "")
    # media:thumbnail
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    # fallback : première <img> trouvée dans le résumé / contenu HTML
    blob = entry.get("summary", "") or ""
    for c in getattr(entry, "content", []) or []:
        blob += c.get("value", "")
    match = re.search(r'<img[^>]+src=["\']?(https?://[^"\'>\s]+)', blob, re.I)
    if match:
        return match.group(1)
    return ""


def best_content(entry: dict) -> str:
    """Texte le plus complet disponible : content:encoded prioritaire sur le résumé."""
    parts = []
    for c in getattr(entry, "content", []) or []:
        v = c.get("value", "")
        if v:
            parts.append(v)
    full = max(parts, key=len) if parts else ""
    summary = entry.get("summary", "") or ""
    text = full if len(full) >= len(summary) else summary
    # Retire les artefacts de scraping (spacers Elementor, pied de flux RSS
    # « appeared first on / proviene da », boutons) — garde les faits.
    from utils.clean_text import strip_boilerplate
    return strip_boilerplate(text.strip())[:10000]


def scrape_source(source: dict, conn: sqlite3.Connection, blocked: set,
                  perimeter_re=None, broad: set | None = None, out_re=None,
                  radar_cultural_re=None) -> int:
    log.info("Scraping : %s", source["name"])
    try:
        feed = feedparser.parse(source["url"])
    except Exception as exc:
        log.warning("Échec scraping %s : %s", source["name"], exc)
        return 0
    # Source LARGE (couverture > périmètre) : on ne gardera que les événements
    # qui citent un lieu du périmètre (évite Avignon, Grenoble… via Le Dauphiné).
    is_large = is_broad_source(_domain(source["url"]), broad or set())
    inserted = skipped = skipped_topic = 0
    for entry in feed.entries:
        url = entry.get("link", "").strip()
        if not url:
            continue
        # Déduplication stricte par url_source
        exists = conn.execute(
            "SELECT id FROM events_raw WHERE url_source = ?", (url,)
        ).fetchone()
        if exists:
            continue
        title = entry.get("title", "").strip()
        content = best_content(entry)
        material = f"{title}\n{content}"
        # 1) Source LARGE : gardée seulement si elle cite un lieu du périmètre.
        if is_large and not mentions_perimeter(material, perimeter_re):
            skipped += 1
            continue
        # 2) TOUTE source : écartée si le texte cite un lieu clairement hors zone
        #    (Avignon, Lyon, Milano…) SANS aucun lieu couvert. Détection positive,
        #    indépendante du domaine — rattrape le radar mal rangé.
        if is_out_of_scope(material, out_re, perimeter_re):
            skipped += 1
            continue
        # 3) Source RADAR (presse généraliste) : gardée seulement si un marqueur
        #    culturel/touristique est présent (config/radar_cultural_exceptions.txt).
        #    Filtre POSITIF, pas une liste de mots hors-sujet à énumérer — le
        #    vocabulaire du fait-divers est trop varié pour être exhaustif, alors
        #    qu'un vrai signal culturel porte quasi toujours un mot du champ lexical.
        if source.get("type") == "radar" and not is_radar_relevant(material, radar_cultural_re):
            skipped_topic += 1
            continue
        image = extract_image(entry)
        if is_blocked_image(image, blocked):
            image = ""
        try:
            conn.execute("""
            INSERT INTO events_raw
                (title, description, date_start, territoire, url_source,
                 url_image, source_name, organisateur, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                content,
                entry.get("published", ""),
                source["territoire"],
                url,
                image,
                source["name"],
                (entry.get("author", "") or "").strip()[:200],
                source.get("type", "institutionnel"),
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # doublon race condition
    conn.commit()
    bits = []
    if skipped:
        bits.append(f"{skipped} hors périmètre écartés")
    if skipped_topic:
        bits.append(f"{skipped_topic} hors-sujet écartés (radar)")
    tail = f" ({', '.join(bits)})" if bits else ""
    log.info("%s : %d nouveaux événements%s", source["name"], inserted, tail)
    return inserted


def main() -> int:
    load_dotenv(ROOT / ".env")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    blocked = load_blocked_image_domains()
    perimeter_re = load_perimeter_filter()
    broad = load_broad_sources()
    out_re = load_out_of_zone()
    radar_cultural_re = load_radar_cultural_filter()
    sources = load_sources()
    if not sources:
        log.error("Aucune source configurée dans %s", SOURCES_FILE)
        return 1
    total = sum(scrape_source(s, conn, blocked, perimeter_re, broad, out_re,
                              radar_cultural_re) for s in sources)
    cleaned = clean_out_of_perimeter(conn, perimeter_re, broad, out_re)
    cleaned_topic = clean_radar_offtopic(conn, radar_cultural_re)
    conn.close()
    log.info("=== Scraping terminé : %d nouveaux événements "
             "(%d hors périmètre rejetés, %d hors-sujet radar rejetés) ===",
             total, cleaned, cleaned_topic)
    return 0


def clean_out_of_perimeter(conn: sqlite3.Connection, perimeter_re, broad: set,
                           out_re=None) -> int:
    """Rejette rétroactivement les événements 'pending' hors périmètre. Idempotent.
    Deux motifs, déterministes et gratuits :
      A) source LARGE ne citant AUCUN lieu couvert ;
      B) TOUTE source citant un lieu clairement hors zone SANS lieu couvert
         (rattrape le radar mal rangé, ex. « Festival d'Avignon » en Savoie).
    """
    if perimeter_re is None and out_re is None:
        return 0
    rows = conn.execute(
        "SELECT id, title, description, url_source FROM events_raw "
        "WHERE statut = 'pending' AND duplicate_of IS NULL").fetchall()
    n = 0
    for r in rows:
        material = f"{r[1]}\n{r[2] or ''}"
        broad_hit = (broad and is_broad_source(_domain(r[3]), broad)
                     and perimeter_re is not None
                     and not mentions_perimeter(material, perimeter_re))
        zone_hit = is_out_of_scope(material, out_re, perimeter_re)
        if broad_hit or zone_hit:
            motif = ("Hors zone (lieu hors périmètre cité, aucun lieu couvert)."
                     if zone_hit else
                     "Hors périmètre (source large, aucun lieu couvert cité).")
            conn.execute("UPDATE events_raw SET statut='rejected', llm_justification=? "
                         "WHERE id=?", (motif, r[0]))
            n += 1
    if n:
        conn.commit()
    return n


def clean_radar_offtopic(conn: sqlite3.Connection, radar_cultural_re) -> int:
    """Rejette rétroactivement les événements RADAR 'pending' sans marqueur culturel/
    touristique (config/radar_cultural_exceptions.txt) — même filtre POSITIF que
    scrape_source() étage 3, appliqué au stock déjà en base (rattrape un radar
    resserré après coup, ou une exécution avant l'ajout du filtre). Idempotent,
    scopé aux seules sources radar et au statut 'pending' (jamais un événement déjà
    évalué ou retenu par Franck)."""
    if radar_cultural_re is None:
        return 0
    rows = conn.execute(
        "SELECT id, title, description FROM events_raw "
        "WHERE statut = 'pending' AND source_type = 'radar' AND duplicate_of IS NULL").fetchall()
    n = 0
    for r in rows:
        material = f"{r[1]}\n{r[2] or ''}"
        if not is_radar_relevant(material, radar_cultural_re):
            conn.execute(
                "UPDATE events_raw SET statut='rejected', "
                "llm_justification='Radar hors-sujet (aucun marqueur culturel/touristique).' "
                "WHERE id=?", (r[0],))
            n += 1
    if n:
        conn.commit()
    return n


if __name__ == "__main__":
    raise SystemExit(main())
