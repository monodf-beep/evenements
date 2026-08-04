#!/usr/bin/env python3
"""Publie un événement vers AGENDA SABAUDA (agendasabauda.eu) — événement TEC.

Cible DISTINCTE de scripts/publisher.py :
  - publisher.py     → culturasabauda.eu (article, bouton « Publier CS »).
  - publisher_as.py  → agendasabauda.eu  (événement The Events Calendar, bouton
                       « Agenda Sabauda »).

Tout le travail TEC se fait CÔTÉ SERVEUR dans le mu-plugin deploy/wordpress/
cs-publish.php (route REST cs/v1/event : tribe_create_event, lieu, catégorie
tribe_events_cat, taxonomie « territoire », méta « as_* », SEO Rank Math, image à
la une, auteur selon le score). Ici on construit un JSON propre et on l'envoie.
TOUJOURS status=draft côté serveur — jamais publish automatiquement.

Variables .env dédiées (ne PAS réutiliser celles de culturasabauda.eu) :
  WP_AS_URL=https://agendasabauda.eu
  WP_AS_USER=agenda-bot
  WP_AS_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
"""
from __future__ import annotations
import base64
import json
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
# On réutilise la mise en forme de l'article et le mapping de catégorie du
# publisher historique (mêmes règles éditoriales, y compris charte §8 sur le radar).
from scripts.dates import extract_time
from scripts.publisher import build_post, _map_category, _upload_featured_media
# Détection des logos/pictogrammes + bannières de repli par territoire × catégorie + filtres image.
from utils.sources import (is_logo_image, load_territory_images, load_territory_category_images,
                           pick_banner_image, is_blocked_image, load_blocked_image_domains)
# Score « ça vaut le déplacement » dérivé des critères d'importance de l'évaluateur.
from utils.deplacement import deplacement_score, deplacement_now

log = get_logger("publisher_as")

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}

# Valeurs de prix qui signifient « entrée libre » → badge as_gratuit=1.
_FREE = {"gratuit", "gratuite", "gratuit·e", "entrée libre", "entree libre",
         "libre", "free", "0", "0€", "0 €"}


def _headers(auth) -> dict:
    """Navigateur + auth de secours via l'en-tête X-CS-Auth (lu par cs-rest-auth.php)
    quand l'hébergeur supprime l'en-tête Authorization. L'auth Basic reste en place."""
    token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode("utf-8")).decode("ascii")
    return {**_UA, "X-CS-Auth": token}


def _is_free(prix: str) -> int:
    return 1 if (prix or "").strip().lower() in _FREE else 0


def _norm(s: str) -> str:
    """minuscule, sans accents, apostrophe normalisée — pour les correspondances."""
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("’", "'")


def _map_territoire(value: str) -> str:
    """Territoire interne → SLUG du terme « territoire » semé (parent des 4).

    Détection par MOT-CLÉ (robuste à toutes les variantes FR/IT : « Vallée d'Aoste »,
    « Valle d'Aosta », « Vallee-Aoste »… ; « Piémont »/« Piemonte »/« Piedmont » ; etc.).
    À défaut de reconnaissance, on renvoie la valeur brute.

    ⚠️ CES SLUGS DOIVENT SUIVRE `docs/NOMMAGE_TERRITOIRES.md` §1. Bug corrigé le
    2026-08-02 : les 4 termes ont été renommés côté WordPress le **2026-07-22**
    (`savoie-haute-savoie` → `savoie`, `nice-alpes-maritimes` → `comte-de-nice`) sans que
    cette fonction soit mise à jour. Conséquence pendant 10 jours : `cs_resolve_term()`
    (cs-publish.php) ne trouvait plus le terme, renvoyait 0 et n'assignait RIEN — en
    SILENCE, sans erreur ni log. Les fiches antérieures au renommage n'ont rien perdu
    (WordPress assigne par `term_id`, insensible au changement de slug), mais toute fiche
    créée depuis en Savoie ou dans le Comté de Nice s'est retrouvée sans taxonomie
    territoire : pas de visuel de repli (`fallback-{territoire}-{catégorie}.png`), absente
    des hubs territoire et des sections filtrées. Repéré via un export des fiches sans
    visuel de repli — 24 fiches, exclusivement Savoie et Nice, aucune Piémont ni Vallée
    d'Aoste (dont les slugs, eux, n'avaient pas changé).
    """
    v = _norm(value)
    if not v:
        return ""
    if "aost" in v:                                    # Vallée d'Aoste / Valle d'Aosta
        return "vallee-d-aoste"
    if "piemont" in v or "piedmont" in v:              # Piémont / Piemonte / Piedmont
        return "piemont"
    if "savoie" in v:                                  # Savoie / Haute-Savoie
        return "savoie"
    if "nice" in v or "maritime" in v or "azur" in v:  # Nice / Alpes-Maritimes / Côte d'Azur
        return "comte-de-nice"
    return (value or "").strip()


def _iso_dates(event: dict) -> tuple[str, str]:
    """(début, fin) en ISO AAAA-MM-JJ pour The Events Calendar.

    Priorité aux colonnes déjà normalisées (date_event_start/end). Si elles sont
    vides, on RÉ-EXTRAIT depuis le texte brut date_start via la logique française
    de scripts/dates.parse_dates — surtout NE PAS envoyer date_start tel quel :
    WordPress/PHP ne sait pas lire « 10 juin 2026 » et retombe sur la date du jour.
    """
    start = (event.get("date_event_start") or "").strip()
    end   = (event.get("date_event_end") or "").strip()
    if not start:
        raw = (event.get("date_start") or "").strip()
        if raw:
            try:
                from scripts.dates import parse_dates
                s, e, _ = parse_dates(raw)
                start = start or s
                end   = end or e
            except Exception as exc:  # ré-extraction non bloquante
                log.warning("Ré-extraction de date impossible (%s) : %s", raw, exc)
    if not start:
        log.warning("Événement sans date ISO exploitable : %s",
                    (event.get("title", "") or "")[:60])
    return start, end


def _is_logo(url) -> bool:
    """True si l'URL image est en réalité un logo/pictogramme/bannière générique
    (détecté par utils.sources.is_logo_image) — à écarter comme vignette."""
    url = (url or "").strip()
    return bool(url) and is_logo_image(url)


# Redirections de traçage des routeurs de newsletter. Une lettre d'information est un
# canal de DÉTECTION, comme la presse : le lien cliqué n'est pas une source, il expire,
# il trace, et le paramètre `e=` porte NOTRE identifiant d'abonné. Neuf fiches en ont
# porté un jusqu'au 2026-08-04, dont quatre avec le même `e=` en clair sur des pages
# publiques. Cf. docs/CONFORMITE.md §5.
_TRACKING_HOSTS = re.compile(
    r"(^|\.)(list-manage\.com|mailchi\.mp|musvc\d*\.net|sendinblue\.com|brevo\.com"
    r"|mailerlite\.com|sendgrid\.net|hubspotlinks\.com|mailjet\.com)$", re.I)
_TRACKING_PATH = re.compile(r"/e/tr\b|[?&](e|eid|subscriber)=", re.I)


def _is_tracking_url(url) -> bool:
    """True si l'URL est une redirection de routeur de newsletter, jamais publiable
    comme source officielle (docs/CONFORMITE.md §5)."""
    url = (url or "").strip()
    if not url:
        return False
    host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0].lower()
    return bool(_TRACKING_HOSTS.search(host) or _TRACKING_PATH.search(url))


def _source_publiable(event: dict, is_radar: bool) -> str:
    """URL de source officielle, ou chaîne vide. Le radar n'est jamais lié (charte §8),
    et une redirection de traçage n'est pas une source (CONFORMITE §5)."""
    if is_radar:
        return ""
    url = (event.get("url_source", "") or "").strip()
    if _is_tracking_url(url):
        log.warning("source de traçage écartée (id=%s) : %s",
                    event.get("id"), url[:80])
        return ""
    return url


def _banner(event: dict, banners: dict, cat_banners: dict | None = None) -> str:
    """Bannière de repli territoire × catégorie (vignette pertinente propre), ou
    la bannière générique du territoire si la catégorie est absente/inconnue."""
    return pick_banner_image(event.get("territoire", ""), event.get("llm_categorie", ""),
                             key=str(event.get("id", "")),
                             cat_images=cat_banners or {}, fallback_images=banners)


def _is_radar(event: dict) -> bool:
    return (event.get("source_type") == "radar"
            or "(radar)" in (event.get("source_name") or ""))


def _recover_image(event: dict) -> str:
    """Tente d'extraire une VRAIE affiche depuis la PAGE SOURCE de l'événement.

    Beaucoup d'images sont bloquées en téléchargement direct (hotlink/Cloudflare :
    ex. le média d'agendaculturel en 403) alors que la fiche organisateur, elle, est
    accessible et contient la photo. On la récupère via utils.images.fetch_content_image
    (og:image puis 1re photo de contenu, habillage écarté). On saute le radar (charte
    §8 : pas de reprise d'image de presse) et on rejette logo/domaine proscrit.
    Renvoie une URL exploitable ou ""."""
    src = (event.get("url_source") or "").strip()
    if not src or _is_radar(event):
        return ""
    try:
        from utils.images import fetch_content_image
        found = (fetch_content_image(src) or "").strip()
    except Exception as exc:                      # jamais bloquant
        log.warning("Récupération image depuis la source impossible : %s", exc)
        return ""
    if not found or _is_logo(found):
        return ""
    if is_blocked_image(found, load_blocked_image_domains()):
        return ""
    return found


def _lang(event: dict) -> str:
    """Langue Polylang de l'événement ('fr'|'it'). Forcée par event['force_lang'] si
    présent (cas des traductions : on ne devine pas, on impose), sinon détectée sur
    titre+description (départagée par le territoire)."""
    forced = str(event.get("force_lang") or "").strip().lower()
    if forced in ("fr", "it"):
        return forced
    from utils.lang import detect_lang
    return detect_lang(event.get("title", ""), event.get("description", ""),
                       event.get("territoire", ""))


def _focal(event: dict) -> tuple[float, float]:
    """Point focal (x, y) ∈ [0,1] pour le recadrage 4:3 de la vignette. Défaut = centre.
    Renseigné à la main dans le back-office (éditeur de point focal) via card_focal_x/y."""
    def _c(v, d=0.5):
        try:
            return min(max(float(v), 0.0), 1.0)
        except (TypeError, ValueError):
            return d
    return (_c(event.get("card_focal_x")), _c(event.get("card_focal_y")))


def _panel_meta(event: dict) -> dict:
    """Détail du panel de personas lecteurs (scripts.enrich.reader_panel), extrait de
    enrich_data pour l'exposer côté WP (as_panel_*) — mean/vmean/verdict tels quels,
    'aucune'/'appliquée'/'tentée' si le brouillon initial notait mieux (cf.
    scripts.enrich, bloc PANEL LECTEURS). Champs vides si jamais relu (court, ou
    enrichi avant l'arrivée du panel)."""
    try:
        data = json.loads(event.get("enrich_data") or "") or {}
    except (ValueError, TypeError):
        data = {}
    panel = data.get("reader_panel") or {}
    home = data.get("home") or {}
    return {
        "as_panel_mean":    panel.get("mean") if panel.get("mean") is not None else "",
        "as_panel_vmean":   panel.get("vmean") if panel.get("vmean") is not None else "",
        "as_panel_votes":   panel.get("votes") if panel.get("votes") is not None else "",
        "as_panel_verdict": panel.get("verdict") or "",
        "as_panel_revision": panel.get("revision") or "",
        "as_affiches":      home.get("affiches") or "",
        "as_placement":     home.get("placement") or "",
    }


def _build_payload(event: dict) -> dict:
    """Construit le JSON envoyé à cs/v1/event depuis une ligne events_raw."""
    title, content = build_post(event)

    # Le radar n'est jamais crédité ni lié (charte §8).
    is_radar = (event.get("source_type") == "radar"
                or "(radar)" in (event.get("source_name") or ""))
    prix = event.get("prix", "") or ""
    # None (non mesuré) → chaîne vide côté WP : « pas mesuré » ne doit pas se confondre
    # avec un vrai 0, sinon la section classerait les non-évalués comme « sans intérêt ».
    depl = deplacement_score(event)
    depl_now = deplacement_now(event)

    meta = {
        "as_score":                 event.get("llm_score", ""),
        # Score HOME (0-10) : qualité du rendu (panel + source officielle + affiches), pour le
        # tri des sections éditoriales de la home. Vide si non enrichi.
        "as_home_score":            event.get("home_score") if event.get("home_score") is not None else "",
        # Override MANUEL (back-office /set-home-override) : '' = auto (as_home_score
        # décide) · 'featured' = forcé en avant · 'excluded' = jamais mis en avant. À lire
        # en PRIORITÉ par les requêtes JetEngine de la home, avant le tri sur as_home_score.
        "as_home_override":         event.get("home_override") or "",
        # Rang manuel PARMI les fiches 'featured' (flèches ▲▼ back-office, /set-home-order).
        # N'a de sens que comparé aux AUTRES as_home_order='featured' — plus petit = plus haut.
        "as_home_order":            event.get("home_order") if event.get("home_order") is not None else "",
        # Statut RÉEL de rédaction ('enriched' ou vide) — sert de filtre d'ÉLIGIBILITÉ pour
        # l'allocateur home, EN AMONT du tri par as_home_score : une fiche jamais rédigée
        # (enrich_status vide) ne doit jamais apparaître en « À la une »/« En évidence », même
        # si la section manque de contenu bien noté ce jour-là (cf. discussion Franck
        # 2026-07-30 — le score seul ne suffisait pas à l'exclure, la home se remplissait
        # avec du contenu non rédigé faute de mieux).
        "as_enrich_status":         event.get("enrich_status") or "",
        # Score « ÇA VAUT LE DÉPLACEMENT » (0-12 depuis le 2026-08-04, vide si non mesuré) —
        # l'échelle a changé avec la pondération ; ce commentaire disait encore 0-8 et c'est
        # la revue qui l'a vu. Une échelle recopiée à la main dérive à la première refonte.
        # dérivé des critères
        # d'importance de scripts/evaluator.py (rayonnement transfrontalier + spécificité
        # territoriale + notoriété du lieu + tradition), cf. utils/deplacement.py pour le
        # détail du choix. Sert à TRIER la section home du même nom, qui triait jusqu'ici
        # par simple ordre chronologique, sans aucun critère de qualité (Franck 2026-08-01).
        # ⚠️ NE PAS trier cette section sur as_panel_vmean : cette note-là mesure la
        # richesse de l'ARTICLE, pas l'ampleur de l'événement (Musilac notait 1.0).
        "as_deplacement":           depl if depl is not None else "",
        # ⚠️ C'EST SUR CELUI-CI QUE LA SECTION DOIT TRIER (ajouté le 2026-08-03), pas sur
        # `as_deplacement` seul ni sur `as_score`. Constat de Franck en regardant la home :
        # elle affichait deux expositions de 365 et 199 jours, l'une ouverte depuis sept
        # mois, pendant que la Foire de la Saint-Ours n'apparaissait jamais.
        # Le score intrinsèque n'était pas en cause — le Castello di Rivoli mérite ses
        # points (grand musée, rayonnement international). Ce qu'AUCUN critère ne disait,
        # c'est qu'une exposition ouverte encore six mois est une raison de se déplacer UN
        # JOUR, quand une foire de trois jours est une raison de se déplacer MAINTENANT.
        # `as_deplacement_now` relève donc l'intrinsèque par le TEMPS QUI RESTE pour y
        # aller — ce qui fait aussi remonter une grande exposition dans sa dernière
        # semaine, et c'est voulu. Vide = la fiche n'a pas sa place dans la section
        # (non mesurée, sous le plancher de qualité, ou déjà passée).
        # `as_deplacement` reste publié à côté : c'est lui qui est auditable critère par
        # critère au back-office, et il ne bouge pas avec le calendrier.
        "as_deplacement_now":       depl_now if depl_now is not None else "",
        # Détail du score home (panel lecteurs + statut affiche) — cf. _panel_meta.
        **_panel_meta(event),
        "as_gratuit":               _is_free(prix),
        "as_tarif":                 "" if _is_free(prix) else prix,
        "as_horaire":               event.get("horaire", "") or "",
        "as_billetterie_url":       event.get("billetterie_url", "") or "",
        "as_source_officielle_url": _source_publiable(event, is_radar),
        "as_verifie_le":            date.today().isoformat(),
        "as_image_credit":          event.get("image_credit", "") or "",
        # Image ORIGINALE (non recadrée) : la vignette mise en avant est standardisée
        # en 4:3 pour la grille ; la FICHE, elle, affiche l'affiche entière via ce champ.
        # JAMAIS un logo/pictogramme (« voir l'affiche en grand » n'aurait aucun sens) :
        # dans ce cas on laisse vide → la fiche montrera la bannière de repli seule.
        "as_image_original":        "" if _is_logo(event.get("url_image")) else (event.get("url_image", "") or ""),
        # Lieu + ville en plat : la carte-événement JetEngine les lit directement
        # (le Venue TEC reste par ailleurs pour la carte/adresse).
        "as_lieu":                  (event.get("lieu") or "").strip(),
        "as_ville":                 (event.get("ville") or "").strip(),
    }

    start_iso, end_iso = _iso_dates(event)
    # Heure de DÉBUT réelle (« HH:MM ») si connue — sinon la fiche reste en journée
    # entière (comportement historique, cs-publish.php). Priorité à time_start (posé à
    # l'enrichissement, scripts/enrich.py) ; repli déterministe sur la description pour
    # les événements jamais enrichis (court, ou publiés avant ce champ).
    start_time = (event.get("time_start") or "").strip()
    if not re.fullmatch(r"[0-2]\d:[0-5]\d", start_time):
        start_time = extract_time(event.get("description") or "")
    payload = {
        "wp_post_id":  event.get("wp_post_id_as") or None,
        "title":       title,
        "content":     content,
        "start_date":  start_iso,
        "end_date":    end_iso,
        "start_time":  start_time,
        "category":    _map_category(event.get("llm_categorie")),
        "territoire":  _map_territoire(event.get("territoire", "")),
        # Langue Polylang (site bilingue FR/IT) : détectée sur le texte, départagée par
        # le territoire. Permet le sélecteur de langue, les archives et les hreflang.
        "language":    _lang(event),
        "score":       event.get("llm_score"),
        # On ne transmet pas un logo comme image : l'endpoint pourrait la re-télécharger
        # en repli. La vraie vignette part en featured_media_id (téléversée ci-dessous).
        "image_url":   "" if _is_logo(event.get("url_image")) else (event.get("url_image", "") or ""),
        "image_alt":   event.get("seo_keyphrase") or event.get("title", "") or "",
        # Site officiel de l'événement (champ natif TEC « EventURL ») = même valeur
        # que as_source_officielle_url. Jamais la source radar (charte §8), jamais une
        # redirection de traçage (CONFORMITE §5) : même filtre, même valeur.
        "website":     _source_publiable(event, is_radar),
        # Champs natifs TEC : organisateur + prix (si on a la donnée).
        "organizer":   (event.get("organisateur") or "").strip(),
        "cost":        (event.get("prix") or "").strip(),
        "meta":        meta,
    }

    # Traductions : forcer la CRÉATION d'une nouvelle fiche (jamais de dédoublonnage —
    # le titre en nom propre est souvent identique à l'original, cf. cs-publish.php).
    if event.get("force_create"):
        payload["force_create"] = True

    # Slug explicite (paires FR/IT) : sans ça, WordPress dérive le slug du TITRE — deux
    # titres dans deux langues donnent deux URLs sans rapport, impossible de retrouver la
    # paire à l'œil (retour Franck). Polylang autorise le MÊME slug dans les deux langues
    # (le préfixe /fr//it/ suffit à les distinguer) : on réutilise donc le slug de
    # l'original pour la fiche traduite.
    if (event.get("slug") or "").strip():
        payload["slug"] = event["slug"].strip()

    if (event.get("lieu") or "").strip():
        payload["venue"] = {"Venue": event["lieu"].strip(),
                            "City": (event.get("ville") or "").strip()}

    # Extrait : la réponse directe SEO si dispo, sinon le début de la description.
    excerpt = (event.get("seo_answer") or "").strip()
    if not excerpt:
        raw = re.sub(r"<[^>]+>", " ", event.get("description") or "")
        excerpt = re.sub(r"\s+", " ", raw).strip()[:200]
    if excerpt:
        payload["excerpt"] = excerpt

    # Étiquettes : VOLONTAIREMENT AUCUNE. Les tags auto (LLM libre) créaient du bruit
    # (doublons de catégorie/territoire, dates, combos jetables) = mauvais SEO. On
    # enverra `tags` seulement plus tard, depuis un VOCABULAIRE CONTRÔLÉ lié aux
    # sections du site. On envoie une liste VIDE pour que l'endpoint nettoie les tags
    # existants (les 69 déjà publiés) au prochain --update.
    payload["tags"] = []

    # SEO Yoast (uniquement si l'événement a été traité par l'étape SEO).
    if event.get("seo_at"):
        payload["seo"] = {
            "title":         event.get("seo_title", "") or "",
            "description":   event.get("seo_meta", "") or "",
            "focus_keyword": event.get("seo_keyphrase", "") or "",
        }

    return payload


def publish_to_as(event: dict, skip_media: bool = False) -> "tuple[int, str, str] | tuple[None, str, str]":
    """Publie/actualise l'événement en brouillon sur agendasabauda.eu (TEC).
    Retourne (wp_post_id, permalink, raw_image_url) ou (None, '', '') si échec.

    skip_media=True → mise à jour TEXTE SEUL : on ne retéléverse AUCUNE image. Utile
    pour une passe qui ne touche que le texte (ex. conformité éditoriale) — évite de
    marteler les sources/Wikimedia (429) et de dégrader une bonne photo en bannière.
    WordPress conserve alors l'image à la une existante (cs-publish ne la change que si
    on lui en fournit une).
    Le permalien est le LIEN PRÉCIS de la fiche (pas la home) — cs-publish.php le
    renvoie déjà à chaque appel, on le capture pour pouvoir pointer dessus ailleurs
    (ex. DM Instagram). raw_image_url : copie de la photo ORIGINALE (non recadrée)
    hébergée dans notre médiathèque WordPress — sert à republier sur Instagram sans
    retélécharger depuis le site source (parfois bloqué par un anti-robot)."""
    load_dotenv(ROOT / ".env")
    wp_url  = os.getenv("WP_AS_URL", "").rstrip("/")
    wp_user = os.getenv("WP_AS_USER", "")
    wp_pass = os.getenv("WP_AS_APP_PASSWORD", "")

    if not all([wp_url, wp_user, wp_pass]):
        log.error("Variables Agenda Sabauda manquantes "
                  "(WP_AS_URL, WP_AS_USER, WP_AS_APP_PASSWORD)")
        return None, "", ""

    auth = (wp_user, wp_pass)
    payload = _build_payload(event)

    # Image à la une : on TÉLÉVERSE côté Python (fiable — le backoffice accède déjà à
    # ces images) plutôt que de laisser WordPress aller chercher l'URL lui-même (souvent
    # bloqué : hotlink/UA/firewall). On transmet ensuite l'id du média à l'endpoint.
    url_image = (event.get("url_image") or "").strip()
    alt = event.get("seo_keyphrase") or event.get("title", "") or ""
    media_id = None
    hero_source = ""  # URL réellement retenue comme image à la une (pas la bannière
                      # générique) — sert au grand visuel de fiche ci-dessous.
    # Multi-format : la carte 4:3 (+ la copie réseaux) préfère l'affiche PORTRAIT dédiée
    # (url_image_portrait) quand elle existe ; le grand visuel 16:9 prend la version PAYSAGE
    # (url_image_wide). Vide → on retombe sur l'image principale. Cf. scripts/images_wide.
    card_source = (event.get("url_image_portrait") or "").strip() or url_image
    if not skip_media and url_image and not _is_logo(url_image):
        # Vraie affiche OU bannière de repli territoire×catégorie (image_source='banner',
        # posée par scripts/visuals.py à défaut de vraie photo — une de NOS images réelles,
        # jamais générée à la volée) : dans les deux cas, une vraie image existe → on la
        # TÉLÉVERSE en featured media. Point focal ET mode (auto/cover/letterbox) réglables
        # à la main au back-office (éditeur de cadrage) pour les vraies affiches ; centré
        # pour les bannières. RÉTABLI le 2026-07-31 (Franck : pas de repli généré côté
        # WordPress/snippet — seulement nos propres images, réellement téléversées).
        is_banner = event.get("image_source") == "banner"
        media_id, _ = _upload_featured_media(
            wp_url, auth, card_source, alt=alt,
            caption=event.get("image_credit", "") or "", title=event.get("title", ""),
            card=True,
            # Focal centré pour une bannière (générique, pas de sujet à cadrer) ou pour
            # l'affiche portrait DÉDIÉE (le focal réglé à la main vaut pour l'image
            # principale, pas pour cette autre image) ; sinon le focal manuel du back-office.
            focal=(0.5, 0.5) if (is_banner or card_source != url_image) else _focal(event),
            mode="cover" if is_banner else (event.get("card_mode") or "auto"))
        if media_id:
            hero_source = url_image
    # Repli 1 — PAGE SOURCE : l'affiche directe manque, a échoué (403/429), ou était un
    # logo → on tente d'extraire une vraie photo depuis la fiche organisateur (souvent
    # accessible même quand le média direct est bloqué). Mieux qu'une bannière générique.
    if not skip_media and not media_id:
        recovered = _recover_image(event)
        if recovered:
            log.info("Affiche récupérée depuis la page source (%s)", recovered)
            media_id, _ = _upload_featured_media(
                wp_url, auth, recovered, alt=alt,
                caption=event.get("image_credit", "") or "", title=event.get("title", ""),
                card=True, focal=_focal(event),
                mode=(event.get("card_mode") or "auto"))
            if media_id:
                hero_source = recovered
    # Repli 2 (bannière territoire × catégorie) : plus besoin d'un appel séparé à
    # _banner() ici — quand ni la vraie affiche ni la récupération page n'ont abouti,
    # `url_image` contient DÉJÀ la bannière de repli (posée en amont par
    # scripts/visuals.py, même fonction pick_banner_image), et le bloc ci-dessus l'a
    # donc déjà téléversée comme featured media. `_banner()` reste dispo pour un appel
    # direct ailleurs (ex. republication ciblée) mais n'est plus appelée dans ce flux.
    if media_id:
        payload["featured_media_id"] = media_id

    # Grand visuel de la FICHE (as_image_original) : MÊME point focal que la vignette de
    # grille, mais au format « héros » 16:9 (plus large) au lieu de 4:3 — évite de couper
    # un titre/visage composé sur le côté d'une affiche large (constaté en production :
    # « Jazz Art », titre tronqué par le recadrage centré par défaut du thème WordPress).
    # Remplace l'URL brute (non recadrée) envoyée par défaut dans _build_payload.
    if hero_source:
        # Multi-format : si une version PAYSAGE dédiée existe (url_image_wide), c'est ELLE
        # qui alimente le 16:9 (un portrait d'affiche y ferait de grosses bandes) ; sinon on
        # retombe sur l'affiche (letterbox). Le paysage est une AUTRE image que l'affiche →
        # point focal centré et cover (le focal réglé à la main vaut pour l'affiche portrait).
        wide_source = (event.get("url_image_wide") or "").strip()
        hero_img = wide_source or hero_source
        is_banner = event.get("image_source") == "banner"
        _, hero_url = _upload_featured_media(
            wp_url, auth, hero_img, alt=alt,
            caption=event.get("image_credit", "") or "",
            title=f"{event.get('title', '')} — fiche",
            card=True,
            focal=(0.5, 0.5) if (wide_source or is_banner) else _focal(event),
            mode="cover" if (wide_source or is_banner) else (event.get("card_mode") or "auto"),
            ratio=(16, 9))
        if hero_url:
            payload["meta"]["as_image_original"] = hero_url

    # Copie ORIGINALE (non recadrée, card=False) hébergée chez nous — réutilisée par
    # /reseaux/publish pour composer les visuels Instagram sans retélécharger depuis le
    # site source (certains bloquent le téléchargement par un défi anti-robot). Couvre
    # aussi le cas bannière (image_source='banner') : hero_source est posé dans ce cas
    # aussi désormais, donc la bannière de repli est dispo pour les réseaux également.
    raw_image_url = ""
    if hero_source:
        # Copie réseaux : l'affiche PORTRAIT dédiée si elle existe (les visuels Instagram
        # sont verticaux/carrés), sinon l'image principale.
        _, raw_image_url = _upload_featured_media(
            wp_url, auth, card_source, alt=alt,
            caption=event.get("image_credit", "") or "",
            title=f"{event.get('title', '')} — original", card=False)

    endpoint = f"{wp_url}/?rest_route=/cs/v1/event"

    # Diagnostic : ce qu'on envoie réellement (dates, lieu, taxonomies) — permet de
    # savoir si un champ manquant vient d'ici (payload) ou de l'endpoint (TEC).
    log.info("→ AS payload : start=%r end=%r venue=%r cat=%r terr=%r img=%s",
             payload.get("start_date"), payload.get("end_date"),
             payload.get("venue"), payload.get("category"),
             payload.get("territoire"), bool(payload.get("image_url")))

    try:
        resp = requests.post(endpoint, json=payload, auth=auth,
                             headers=_headers(auth), timeout=60)
        resp.raise_for_status()
        body = resp.json()
        post_id = body.get("id")
        permalink = body.get("url") or ""
        verb = "mis à jour" if body.get("updated") else "créé"
        log.info("Événement Agenda Sabauda %s id=%s : %s", verb, post_id,
                 (event.get("title", "") or "")[:60])
        return post_id, permalink, raw_image_url
    except requests.HTTPError as exc:
        log.error("Erreur Agenda Sabauda API (%s) : %s", exc.response.status_code,
                  exc.response.text[:300])
        return None, "", ""
    except (requests.RequestException, ValueError) as exc:
        log.error("Connexion Agenda Sabauda impossible : %s", exc)
        return None, "", ""
