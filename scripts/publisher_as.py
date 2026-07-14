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
from scripts.publisher import build_post, _map_category, _upload_featured_media
# Détection des logos/pictogrammes + bannières de repli par territoire + filtres image.
from utils.sources import (is_logo_image, load_territory_images, pick_image,
                           is_blocked_image, load_blocked_image_domains)

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
    """
    v = _norm(value)
    if not v:
        return ""
    if "aost" in v:                                    # Vallée d'Aoste / Valle d'Aosta
        return "vallee-d-aoste"
    if "piemont" in v or "piedmont" in v:              # Piémont / Piemonte / Piedmont
        return "piemont"
    if "savoie" in v:                                  # Savoie / Haute-Savoie
        return "savoie-haute-savoie"
    if "nice" in v or "maritime" in v or "azur" in v:  # Nice / Alpes-Maritimes / Côte d'Azur
        return "nice-alpes-maritimes"
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


def _banner(event: dict, banners: dict) -> str:
    """Bannière de repli (vignette générique propre) pour le territoire, ou "".
    Déterministe par id → varie d'un événement à l'autre au sein d'un territoire."""
    return pick_image(event.get("territoire", ""), key=str(event.get("id", "")),
                      images=banners)


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
    """Langue Polylang de l'événement ('fr'|'it'), détectée sur titre+description."""
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


def _build_payload(event: dict) -> dict:
    """Construit le JSON envoyé à cs/v1/event depuis une ligne events_raw."""
    title, content = build_post(event)

    # Le radar n'est jamais crédité ni lié (charte §8).
    is_radar = (event.get("source_type") == "radar"
                or "(radar)" in (event.get("source_name") or ""))
    prix = event.get("prix", "") or ""

    meta = {
        "as_score":                 event.get("llm_score", ""),
        "as_gratuit":               _is_free(prix),
        "as_tarif":                 "" if _is_free(prix) else prix,
        "as_horaire":               event.get("horaire", "") or "",
        "as_billetterie_url":       event.get("billetterie_url", "") or "",
        "as_source_officielle_url": "" if is_radar else (event.get("url_source", "") or ""),
        "as_verifie_le":            date.today().isoformat(),
        "as_image_credit":          event.get("image_credit", "") or "",
        # Image ORIGINALE (non recadrée) : la vignette mise en avant est standardisée
        # en 4:3 pour la grille ; la FICHE, elle, affiche l'affiche entière via ce champ.
        # JAMAIS un logo/pictogramme (« voir l'affiche en grand » n'aurait aucun sens) :
        # dans ce cas on laisse vide → la fiche montrera la bannière territoire seule.
        "as_image_original":        "" if _is_logo(event.get("url_image")) else (event.get("url_image", "") or ""),
        # Lieu + ville en plat : la carte-événement JetEngine les lit directement
        # (le Venue TEC reste par ailleurs pour la carte/adresse).
        "as_lieu":                  (event.get("lieu") or "").strip(),
        "as_ville":                 (event.get("ville") or "").strip(),
    }

    start_iso, end_iso = _iso_dates(event)
    payload = {
        "wp_post_id":  event.get("wp_post_id_as") or None,
        "title":       title,
        "content":     content,
        "start_date":  start_iso,
        "end_date":    end_iso,
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
        # que as_source_officielle_url. Jamais la source radar (charte §8).
        "website":     "" if is_radar else (event.get("url_source", "") or ""),
        # Champs natifs TEC : organisateur + prix (si on a la donnée).
        "organizer":   (event.get("organisateur") or "").strip(),
        "cost":        (event.get("prix") or "").strip(),
        "meta":        meta,
    }

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


def publish_to_as(event: dict) -> int | None:
    """Publie/actualise l'événement en brouillon sur agendasabauda.eu (TEC).
    Retourne le wp_post_id (côté agenda) ou None."""
    load_dotenv(ROOT / ".env")
    wp_url  = os.getenv("WP_AS_URL", "").rstrip("/")
    wp_user = os.getenv("WP_AS_USER", "")
    wp_pass = os.getenv("WP_AS_APP_PASSWORD", "")

    if not all([wp_url, wp_user, wp_pass]):
        log.error("Variables Agenda Sabauda manquantes "
                  "(WP_AS_URL, WP_AS_USER, WP_AS_APP_PASSWORD)")
        return None

    auth = (wp_user, wp_pass)
    payload = _build_payload(event)

    # Image à la une : on TÉLÉVERSE côté Python (fiable — le backoffice accède déjà à
    # ces images) plutôt que de laisser WordPress aller chercher l'URL lui-même (souvent
    # bloqué : hotlink/UA/firewall). On transmet ensuite l'id du média à l'endpoint.
    url_image = (event.get("url_image") or "").strip()
    alt = event.get("seo_keyphrase") or event.get("title", "") or ""
    media_id = None
    if url_image and not _is_logo(url_image):
        # Vraie affiche → vignette standardisée 4:3. Point focal ET mode (auto/cover/
        # letterbox) réglables à la main au back-office (éditeur de cadrage).
        media_id = _upload_featured_media(
            wp_url, auth, url_image, alt=alt,
            caption=event.get("image_credit", "") or "",
            card=True, focal=_focal(event),
            mode=(event.get("card_mode") or "auto"))
    # Repli 1 — PAGE SOURCE : l'affiche directe manque, a échoué (403/429), ou était un
    # logo → on tente d'extraire une vraie photo depuis la fiche organisateur (souvent
    # accessible même quand le média direct est bloqué). Mieux qu'une bannière générique.
    if not media_id:
        recovered = _recover_image(event)
        if recovered:
            log.info("Affiche récupérée depuis la page source (%s)", recovered)
            media_id = _upload_featured_media(
                wp_url, auth, recovered, alt=alt,
                caption=event.get("image_credit", "") or "",
                card=True, focal=_focal(event),
                mode=(event.get("card_mode") or "auto"))
    # Repli 2 — BANNIÈRE TERRITOIRE quand tout le reste a échoué (logo écarté sans page
    # exploitable, image bloquée + page bloquée, aucune image). Comble les cartes vides.
    if not media_id:
        banner = _banner(event, load_territory_images())
        if banner:
            if _is_logo(url_image):
                log.info("Logo écarté au push (%s) → bannière territoire", url_image)
            elif url_image:
                log.info("Téléversement affiche échoué (%s) → bannière territoire", url_image)
            media_id = _upload_featured_media(
                wp_url, auth, banner, alt=alt, card=True, focal=(0.5, 0.5))
    if media_id:
        payload["featured_media_id"] = media_id

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
        verb = "mis à jour" if body.get("updated") else "créé"
        log.info("Événement Agenda Sabauda %s id=%s : %s", verb, post_id,
                 (event.get("title", "") or "")[:60])
        return post_id
    except requests.HTTPError as exc:
        log.error("Erreur Agenda Sabauda API (%s) : %s", exc.response.status_code,
                  exc.response.text[:300])
        return None
    except (requests.RequestException, ValueError) as exc:
        log.error("Connexion Agenda Sabauda impossible : %s", exc)
        return None
