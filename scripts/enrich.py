#!/usr/bin/env python3
"""Enrichissement + rédaction des événements retenus (étapes 3 & 4 du pipeline).

À partir du SIGNAL d'un événement retenu (titre, date, lieu, entités) et de toute
la MATIÈRE disponible (sa description + celle des doublons fusionnés, même venus
d'un radar gratuit), un agent LLM :

1. RECHERCHE le contexte sur le web → privilégie le DOSSIER DE PRESSE (source primaire,
   voir scripts/press_kits.py) puis la source officielle libre (organisateur, lieu,
   agenda, billetterie) — voir CHARTE §5 ;
2. ENRICHIT selon la nature de l'événement (lieu, artiste, conférencier, plat…) ;
3. RÉDIGE un article (titre, chapô, corps, encadré pratique) selon CHARTE §4/§6/§7.

GARDE-FOUS (CHARTE §5/§7) :
- FAITS vs EXPRESSION : la presse (même payante) sert à récupérer des FAITS (dates,
  lieu, casting) — jamais son texte, qu'on ne recopie pas et qu'on ne crédite pas.
  L'expression et l'attribution vont à la source officielle/primaire.
- Ne JAMAIS inventer : une info non trouvée n'est pas écrite (sinon "confiance" basse).
- Coût maîtrisé : réservé aux événements retenus (score ≥ seuil), traité par petits
  lots, modèle configurable. PAS en cron par défaut — déclenché à la main (bouton).

LLM ? OUI — jugement éditorial + recherche + rédaction (langue). La sélection des
candidats et l'agrégation de la matière restent déterministes. Voir docs/LLM_OU_CODE.md.

SDK anthropic DIRECT + outil serveur de recherche web (web_search_20260209).
Usage :
    python scripts/enrich.py            # lot par défaut (ENRICH_BATCH)
    python scripts/enrich.py 12 15 18   # enrichit ces id précis (bouton « 1 événement »)
"""
from __future__ import annotations
import anthropic
import html as htmlmod
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# Charge le .env DÈS l'import : les réglages ENRICH_* (recherche web, thinking, seuils…)
# sont lus en globals ci-dessous, donc AVANT que main() n'appelle load_dotenv. Sans ça,
# une variable posée dans .env (ex. ENRICH_WEB_SEARCH=1) serait ignorée à l'import.
# load_dotenv n'écrase pas l'environnement déjà défini : un export shell garde la priorité.
load_dotenv(ROOT / ".env")
from utils.logger import get_logger
from utils import usage
from utils.images import fetch_og_image
from scripts.scraper_events import init_db

log = get_logger("enrich")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Modèle dédié à l'enrichissement (recherche web + rédaction). Sonnet 5 par défaut :
# bon rapport qualité/prix et compatible avec l'outil de recherche web dynamique.
DEFAULT_MODEL = "claude-sonnet-5"
# PLANCHER d'enrichissement : TOUT événement retenu (statut 'evaluated', non rejeté)
# au-dessus de ce score reçoit AU MOINS un article COURT (CHARTE §3 : score < 7 = vrai
# événement → catalogue, jamais la description brute). Les non-événements sont déjà
# écartés par le statut ('rejected'), pas par ce seuil. Court = pas de recherche web
# → coût faible ; le débit reste borné par ENRICH_BATCH. Relever ce seuil si on veut
# réserver la rédaction aux événements plus notables.
MIN_SCORE = int(os.getenv("ENRICH_MIN_SCORE", "1"))
# Seuil du LONG : au-dessus, article COMPLET (Cultura Sabauda, recherche web) ; entre
# MIN_SCORE et ici, article COURT (Agenda). CHARTE §3 (mise en avant vs catalogue).
LONG_MIN_SCORE = int(os.getenv("ENRICH_LONG_MIN_SCORE", "7"))
# Taille de lot : l'enrichissement (web + rédaction) coûte cher → petit lot.
BATCH_SIZE = int(os.getenv("ENRICH_BATCH", "10"))
# Plafond de recherches web par événement (outil serveur).
MAX_WEB_SEARCHES = int(os.getenv("ENRICH_MAX_SEARCHES", "3"))
# Budget de sortie de l'article JSON.
MAX_TOKENS = int(os.getenv("ENRICH_MAX_TOKENS", "12000"))
# Raisonnement étendu : COÛTEUX et LENT (runs de ~5 min, budget de tokens épuisé avant
# le JSON → stop_reason=max_tokens). Inutile pour « chercher + rédiger en JSON ».
# Désactivé par défaut ; ENRICH_THINKING=1 pour l'activer (articles plus fouillés, plus chers).
USE_THINKING = os.getenv("ENRICH_THINKING", "0").lower() in ("1", "true", "yes", "on")
# Outil de recherche web (serveur Anthropic) : à activer seulement s'il est disponible
# sur la clé. Par défaut OFF — on fournit nous-mêmes la PAGE OFFICIELLE comme matière
# (déterministe, fiable, moins cher). ENRICH_WEB_SEARCH=1 pour l'ajouter en bonus.
USE_WEB_SEARCH = os.getenv("ENRICH_WEB_SEARCH", "0").lower() in ("1", "true", "yes", "on")
# En-têtes de VRAI navigateur : beaucoup de sites (agrégateurs, sites de festivals)
# bloquent un User-Agent « …Bot » ou l'absence d'Accept/Accept-Language. On lit des pages
# PUBLIQUES (programme, presse) pour la rédaction éditoriale, sans franchir de mur d'accès.
_UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
               "image/webp,*/*;q=0.8"),
    "Accept-Language": "fr-FR,fr;q=0.9,it;q=0.8,en;q=0.7",
}

# Sentinel : échec d'APPEL API. L'événement n'est pas marqué → réenrichi plus tard.
API_ERROR = object()

WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": MAX_WEB_SEARCHES,
}

ENRICH_PROMPT = """Si une VOIX ÉDITORIALE est fournie ci-dessus, elle RÉGIT le ton, le
style et les interdits (connecteurs, mise en forme, marqueurs) : en cas de désaccord avec
ce qui suit, la voix prime. Ce prompt, lui, définit ta TÂCHE et le FORMAT de sortie.

Tu es l'agent éditorial d'Agenda Sabauda, l'agenda culturel bilingue FR/IT des territoires
sabauds : Savoie/Haute-Savoie, Piémont, Vallée d'Aoste, Nice/Alpes-Maritimes. Un lecteur
d'agenda veut SAVOIR CE QUI SE PASSE : quoi, quand, qui, comment y aller. Pas un essai de
magazine.

MISSION : RÉDIGE un PREVIEW d'événement, COURT et INFORMATIF, à partir de la MATIÈRE fournie
ci-dessous (page officielle, dossier de presse, flux). Appuie-toi EN PRIORITÉ sur la PAGE
OFFICIELLE et le DOSSIER DE PRESSE (sources primaires). N'affirme aucun fait qui n'y figure
pas ; en cas de doute, baisse la confiance.

STRUCTURE — PYRAMIDE INVERSÉE (l'info d'abord), JAMAIS l'escalier de magazine :
1. ACCROCHE : quoi, quand, où, la raison d'y aller (tête d'affiche, temps fort, nouveauté) ;
2. ESSENTIEL (le cœur) : la PROGRAMMATION CONCRÈTE, avec la substance PROPRE AU GENRE — pour
   un concert pop/variété, les têtes d'affiche ; pour un festival de musique CLASSIQUE, les
   œuvres, compositeurs, orchestres, solistes, chefs et lieux ; pour une expo, les artistes
   et œuvres ; pour un spectacle, la pièce et la troupe ; plus les temps forts et horaires.
   Ne plaque PAS une logique « têtes d'affiche » sur un genre qui n'en a pas. EXPLOITE
   TOUJOURS le programme présent dans la MATIÈRE (ne dis JAMAIS « à venir » si on l'a déjà) ;
   complète par recherche web. Si le programme de CETTE édition n'est pas encore annoncé,
   DONNE CELUI DE L'ÉDITION PRÉCÉDENTE (« en 2025 : … ») pour que le lecteur sache ce qu'est
   l'événement — un article « programmation à venir » n'apprend rien et est un ÉCHEC ;
3. IDENTITÉ (1-2 items) : ce qui FAIT cet événement (artistes/œuvres marquants, affluence,
   ce qui revient chaque année) ;
4. STOP. On reste sur CET événement. INTERDIT : le contexte historique/économique du lieu
   (le thermalisme d'Aix, l'économie du tourisme…), ce qui se passe ailleurs, toute montée
   vers une « question universelle ». Ça, c'est Cultura Sabauda ; ici on veut l'événement.
Longueur : COURT et dense — vise 150 à 300 mots. Utile et concret vaut mieux que long.

RÈGLE DE SUBSTANCE : avant de conclure, demande-toi « qu'est-ce que le lecteur APPREND ? ».
S'il n'apprend rien de concret (des NOMS, des temps forts, ce qui distingue l'événement),
l'article a échoué : va chercher la matière (programme fourni, édition précédente par
recherche web) au lieu de meubler avec des généralités.

INTERDIT ABSOLU — MÉTA-COMMENTAIRE SUR L'INFO MANQUANTE. N'écris JAMAIS que l'info te manque
(« à ce stade, la matière disponible ne précise ni les compositeurs, ni les tarifs… »,
« le programme n'est pas encore connu », « les détails restent à confirmer »). Tu écris ce
que tu SAIS, un point c'est tout — et tu te tais sur le reste. Un article qui parle de son
propre vide est le PIRE des échecs. Si après recherche tu n'as vraiment pas de programme
concret, cherche l'ÉDITION PRÉCÉDENTE ; si tu n'as toujours rien, écris court et factuel
sur ce qui est certain, sans jamais commenter ce qui manque. Les doutes vont dans le champ
« a_verifier » (back-office), JAMAIS dans le corps de l'article.

ENRICHISSEMENT (ce que tu vas chercher SELON la nature de l'événement) :
- Lieu (théâtre, musée, château, abbaye…) : histoire/identité, importance patrimoniale.
- Artiste / groupe : origine (local ? de territoires proches ? renommée), genre.
- Conférencier / auteur : qui c'est, pourquoi ça compte.
- Plat / produit (si intérêt culturel local) : origine, tradition, ce qu'il raconte.
- Œuvre / exposition : artiste, période, intérêt.
- Date / récurrence : rendez-vous historique ? édition anniversaire ?

FAITS STRUCTURÉS OBLIGATOIRES (CHARTE §5 bis) — dès que la MATIÈRE les contient, tu DOIS
les restituer, quel que soit le format d'article. Un programme / line-up / déroulé de
séances se rend TOUJOURS en LISTE (champ "programme"), jamais noyé en prose. Selon le type :
- Exposition : horaires d'ouverture (≠ la simple plage de dates !), tarif/gratuité, artistes.
- Concert / série : line-up + horaires, salle, billetterie.
- Spectacle : distribution/casting, durée, réservation.
- Festival / multi-jours : programme PAR JOUR (liste), line-up complet.
- Sagra / gastronomie : ce qu'on mange/boit, dates, prix.
- Marché : récurrence (« chaque 1er dimanche »), horaires, type d'exposants.
- Conférence : intervenant, sujet, LANGUE (FR/IT), inscription.
- Sport : distingue les DEUX publics — spectateurs (venir voir, souvent gratuit, horaire
  de passage) vs participants (inscription, tarif d'engagement, catégories). Ne les mélange pas.
- Cinéma : film(s) + horaires de séance, VO/VF (langue !), lieu, tarif ; plein air : gratuité + heure.
- Fêtes populaires : programme multi-jours (temps forts : défilé, feu d'artifice, bal), gratuité, récurrence.
Une info pratique que la matière contenait mais que tu as omise est une ERREUR, pas un résumé.

EXPLOITER LA PRESSE POUR LES FAITS (pas pour le texte) :
- Tu PEUX consulter la presse, y compris via des extraits de recherche, pour en tirer
  des FAITS : dates, lieu, programme, distribution/casting, tarifs. Les faits ne sont
  pas protégés — sers-t'en pour avoir le MAXIMUM de matière.
- Tu ne dois JAMAIS recopier l'EXPRESSION d'un article (phrases, formules, l'analyse
  ou l'avis d'un journaliste) : reformule tout dans tes propres mots.
- Ne cite PAS la presse comme source. Dans "sources", ne mets que des pages
  OFFICIELLES/LIBRES (organisateur, lieu, agenda officiel, billetterie), où les faits
  sont vérifiables. Si un fait ne vient que de la presse, tu peux l'utiliser mais
  baisse la "confiance".
- Le DOSSIER DE PRESSE fourni (s'il y en a un) est la matière PRIORITAIRE : c'est la
  source primaire, avec droits d'usage — appuie-toi dessus en premier.

GARDE-FOUS STRICTS :
- N'invente RIEN. Si une info n'est pas trouvée, ne l'écris pas. En cas de matière trop
  mince, mets "confiance": "faible" et reste factuel.
- Pas de superlatifs creux ("incontournable", "magique", "à ne pas manquer"), aucun
  dark pattern (urgence factice, clickbait).
- Nomme toujours la géographie : ville → province/département → territoire.
- CASSE : jamais de titre/nom TOUT EN CAPITALES, même si la source l'écrit ainsi
  ("COREOGRAFIE DEL POSSIBILE" → "Coreografie del Possibile"). Normalise en casse de
  phrase (initiale + noms propres, selon la langue FR/IT) ; garde les vrais sigles
  (FIAF, ONU) et la casse voulue d'une marque (iMac). Vaut pour le titre ET le corps.

SIGNAL :
Titre : {title}
Dates de l'événement : {dates}
Lieu / ville : {lieu}
Territoire : {territoire}
Organisateur : {organisateur}
Catégorie évaluée : {categorie}

MATIÈRE DISPONIBLE (déjà collectée, à vérifier/compléter par ta recherche) :
{material}

Termine ta réponse par un UNIQUE bloc JSON valide, sans rien après, de la forme :
{{
  "contexte_lieu": "<ce que la recherche apprend du lieu, ou ''>",
  "contexte_entites": "<artiste/conférencier/plat/œuvre : origine, renommée, intérêt, ou ''>",
  "angle": "<l'accroche : en une phrase, la raison d'aller à CET événement (tête d'affiche, temps fort, nouveauté) — jamais une montée vers l'universel>",
  "infos_pratiques": "<dates, lieu, accès, tarif/gratuité, lien officiel — factuel>",
  "sources": ["<url officielle/libre consultée>", "..."],
  "confiance": "<haute|moyenne|faible>",
  "a_verifier": ["<fait factuel PRÉCIS à contrôler humainement : nom peut-être mal orthographié, line-up ambigu (1 ou 2 artistes ?), date/horaire incertain, prix/gratuité non confirmé, affirmation absente de la matière. Court (max ~12 mots). Liste vide [] si tu es SÛR. Ne signale QUE de vrais doutes, jamais de remplissage : c'est un garde-fou HUMAIN, pas une formalité>"],
  "article": {{
    "titre": "<titre informatif et incarné, pas racoleur>",
    "chapo": "<1-2 phrases : l'essentiel + l'angle>",
    "corps": "<le PREVIEW de l'événement en PYRAMIDE INVERSÉE : accroche (quoi/quand/tête d'affiche), puis la PROGRAMMATION de cette édition (line-up, temps forts, horaires, nouveautés), puis au plus un rappel bref. On reste sur CET événement : AUCUN contexte historique/économique du lieu ou du territoire, AUCUNE montée vers l'universel, RIEN sur ce qui se passe ailleurs (ça, c'est Cultura Sabauda, pas ici). COURT : 150-300 mots ; au plus un ou deux sous-titres '## ' si vraiment nécessaire. Phrases COURTES (<20 mots), CONCRÈTES, de JOURNALISTE : on dit ce qui se passe, jamais ce que « ça raconte » (pas de « X n'est pas neutre », pas de fausse profondeur). GRAS UTILE : 3 à 5 expressions structurantes (tête d'affiche, temps fort, nouveauté), JAMAIS sur noms propres, lieux, dates ou chiffres. PAS de tiret cadratin (— ou –) : virgule, parenthèse, deux-points, point. Français soigné, aucun anglicisme (« programmes », pas « programs »). N'écris PAS l'encadré pratique (dates/lieu/tarif) dans le corps : le site l'affiche nativement>",
    "programme": ["<UNE entrée par ligne de programme : jour/heure + intitulé (concert, séance, temps fort…). LISTE, jamais de la prose. Vide [] si l'événement n'a pas de programme/line-up dans la matière>"],
    "encadre": "<encadré pratique : dates, lieu, accès, gratuité, lien officiel>"
  }}
}}"""


def gather_press_kits(conn: sqlite3.Connection, ev: dict) -> str:
    """Matière PRIORITAIRE : dossiers de presse (source primaire) EXPLICITEMENT rattachés
    à l'événement. Le rattachement (déterministe) est fait par scripts/press_kits.py ;
    ici on ne fait que lire. Vide si le canal presse n'a jamais tourné (table absente)."""
    try:
        rows = conn.execute(
            "SELECT subject, body_text, pdf_text, n_photos FROM press_kits "
            "WHERE matched_event_id = ?", (ev["id"],)).fetchall()
    except sqlite3.OperationalError:
        return ""
    chunks = []
    for r in rows:
        body = (r["body_text"] or "").strip()
        pdf = (r["pdf_text"] or "").strip()
        photos = f" [{r['n_photos']} photo(s) HD jointe(s)]" if r["n_photos"] else ""
        chunk = "\n".join(x for x in (body, pdf) if x)
        if chunk:
            chunks.append(f"« {r['subject']} »{photos}\n{chunk}")
    return "\n\n===\n\n".join(chunks)[:12000]


def _html_to_text(doc: str) -> str:
    """Retire scripts/styles/navigation, puis les balises, puis décode les entités."""
    doc = re.sub(r"(?is)<(script|style|nav|header|footer|noscript)[^>]*>.*?</\1>", " ", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    doc = htmlmod.unescape(doc)
    return re.sub(r"\s+", " ", doc).strip()


def _get_html(url: str, timeout: int = 8) -> str:
    """HTML brut d'une page publique (ou "" si inaccessible). Ne franchit aucun mur."""
    if not url or url.startswith("gmail:") or "news.google.com" in url:
        return ""
    try:
        r = requests.get(url, timeout=timeout, headers=_UA)
        if r.status_code != 200 or not r.text:
            return ""
        return r.text
    except Exception:
        return ""


def fetch_official_page(url: str, timeout: int = 8) -> str:
    """Récupère le TEXTE de la page officielle de l'événement (source primaire, libre).
    Déterministe : le code va chercher la matière, le LLM la rédige. Skip radar/Gmail."""
    doc = _get_html(url, timeout)
    return _html_to_text(doc)[:6000] if doc else ""


# Ancres/URL qui trahissent une page « presse / programmation / line-up / affiche » — FR+IT.
# On les suit depuis la page d'accueil : la SOURCE OFFICIELLE (site + dossier de presse) FAIT
# FOI, avant tout. Les pages « presse » (relations-presse, espace presse, dossier de presse)
# concentrent le programme réel ET les visuels HD (affiche portrait + paysage) : on les suit
# en PRIORITÉ (score doublé, voir _programme_links).
_PRESS_HINTS = (
    "presse", "press", "dossier", "communiqu", "media-kit", "mediakit", "presskit",
    "espace-pro", "cartella-stampa", "ufficio-stampa", "rassegna-stampa",
)
_PROG_HINTS = (
    "programm", "line-up", "lineup", "line_up", "affiche", "artist", "artisti",
    "concert", "spettacol", "spectacle", "cartellone", "edition", "édition",
    "au-programme", "en-scene", "en-scène", "invit", "guest", "intervenant",
    "au-menu", "temps-fort",
) + _PRESS_HINTS
# Ancres à IGNORER (bruit : billetterie, mentions, contact, cookies…).
_PROG_STOP = ("billet", "ticket", "cookie", "mentions", "contact", "privacy",
              "cgv", "newsletter", "login", "compte", "panier", "boutique", "impressum")


def _programme_links(html: str, base_url: str, limit: int = 3) -> list[str]:
    """Depuis le HTML d'accueil, renvoie jusqu'à `limit` URLs INTERNES qui ressemblent à
    des pages programmation/line-up (même domaine), triées par pertinence de l'ancre."""
    from urllib.parse import urljoin, urlparse
    base_host = urlparse(base_url).netloc.lower()
    if not base_host:
        return []
    scored: dict[str, int] = {}
    for m in re.finditer(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html):
        href, anchor = m.group(1), _html_to_text(m.group(2)).lower()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absu = urljoin(base_url, href)
        pu = urlparse(absu)
        if pu.scheme not in ("http", "https") or pu.netloc.lower() != base_host:
            continue
        hay = (pu.path + " " + anchor).lower()
        if any(s in hay for s in _PROG_STOP):
            continue
        score = sum(2 for h in _PROG_HINTS if h in anchor) + \
            sum(1 for h in _PROG_HINTS if h in pu.path.lower())
        # PRIORITÉ à la page presse : elle concentre programme + visuels HD officiels.
        if any(h in hay for h in _PRESS_HINTS):
            score += 5
        if score <= 0:
            continue
        clean = absu.split("#")[0]
        if clean.rstrip("/") == base_url.split("#")[0].rstrip("/"):
            continue  # pas la page d'accueil elle-même
        scored[clean] = max(scored.get(clean, 0), score)
    ordered = sorted(scored, key=lambda u: scored[u], reverse=True)
    return ordered[:limit]


# Domaines qui ne sont JAMAIS le site officiel d'un événement : réseaux sociaux,
# billetteries, agrégateurs, plateformes. On ne les prend pas pour « la source ».
_NOT_OFFICIAL = (
    "facebook.", "fb.me", "fb.com", "instagram.", "twitter.", "x.com", "youtube.",
    "youtu.be", "tiktok.", "linkedin.", "google.", "goo.gl", "wikipedia.", "billetweb.",
    "weezevent.", "fnac", "ticketmaster.", "digitick.", "eventbrite.", "helloasso.",
    "yurplan.", "shotgun.", "dice.fm", "tripadvisor.", "spotify.", "deezer.", "apple.",
    "agendaculturel.", "mapstr.", "waze.", "instagr.am", "bit.ly",
)
# Mots trop génériques pour discriminer un domaine officiel (on les garde mais ils pèsent
# comme les autres : c'est le CUMUL de correspondances qui distingue le bon domaine).
_TITLE_STOP = {"festival", "concert", "spectacle", "exposition", "salon", "foire", "fete",
               "fête", "edition", "édition", "saison", "rencontres", "journees", "journées"}


def _event_tokens(title: str) -> list[str]:
    """Mots significatifs du titre (>3 lettres) pour reconnaître le domaine officiel."""
    return [w for w in re.findall(r"[a-zà-ÿ0-9]+", (title or "").lower())
            if len(w) > 3 and w not in _TITLE_STOP]


def _find_official_site(html: str, base_url: str, title: str) -> str:
    """Depuis une page (souvent un AGRÉGATEUR), trouve le lien SORTANT vers le vrai site
    OFFICIEL de l'événement : un domaine externe dont le nom recoupe le titre, ou pointé par
    une ancre « site officiel ». "" si rien de fiable (on ne devine pas)."""
    from urllib.parse import urlparse
    base_host = urlparse(base_url).netloc.lower().lstrip("www.")
    toks = _event_tokens(title)
    best, best_score = "", 0
    for m in re.finditer(r'(?is)<a\b[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', html):
        href, anchor = m.group(1), _html_to_text(m.group(2)).lower()
        host = urlparse(href).netloc.lower()
        if not host or host.lstrip("www.") == base_host:
            continue                                   # lien interne à l'agrégateur
        if any(bad in host for bad in _NOT_OFFICIAL):
            continue                                   # réseau/billetterie/agrégateur
        score = sum(1 for t in toks if t in host)      # recoupement titre ↔ domaine
        if any(k in anchor for k in ("site officiel", "officiel", "site web",
                                     "site internet", "site du", "en savoir plus")):
            score += 3
        if score > best_score:
            best, best_score = f"{urlparse(href).scheme}://{host}/", score
    return best if best_score >= 2 else ""


def _deep_read(html: str, url: str, timeout: int, n_sub: int, tag: str) -> list[str]:
    """Suit les pages presse/programme d'un site et renvoie leurs textes balisés."""
    out = []
    for link in _programme_links(html, url, limit=n_sub):
        txt = _html_to_text(_get_html(link, timeout))[:5000]
        if txt:
            out.append(f"[PAGE PRESSE/PROGRAMME — {link}]\n{txt}")
            log.info("%s : page presse/programme lue (%s)", tag, link[:90])
    return out


def fetch_official_material(url: str, timeout: int = 8, title: str = "") -> str:
    """SOURCE OFFICIELLE = première source (règle Franck). Si `url` est un AGRÉGATEUR, on
    remonte au vrai site officiel de l'événement (lien sortant qui recoupe le titre), puis on
    lit sa page presse/programme (programme réel + visuels HD). Sinon on lit `url` en
    profondeur. Désactivable via ENRICH_SITE_DEEP=0."""
    html = _get_html(url, timeout)
    if not html:
        return ""
    landing = _html_to_text(html)[:6000]
    deep = os.getenv("ENRICH_SITE_DEEP", "1") == "1"
    try:
        n_sub = int(os.getenv("ENRICH_SITE_SUBPAGES", "3") or 3)
    except ValueError:
        n_sub = 3
    if not deep or n_sub <= 0:
        return landing
    blocks: list[str] = []
    # 1) Remonter au SITE OFFICIEL si la source est un agrégateur.
    official = _find_official_site(html, url, title)
    if official:
        ohtml = _get_html(official, timeout)
        if ohtml:
            otext = _html_to_text(ohtml)[:6000]
            if otext:
                blocks.append(f"[SITE OFFICIEL DE L'ÉVÉNEMENT — {official}]\n{otext}")
                log.info("site officiel trouvé via la source : %s", official[:90])
            blocks += _deep_read(ohtml, official, timeout, n_sub, "site officiel")
    # 2) La page source (agrégateur, ou site officiel direct) reste de la matière utile.
    if landing:
        blocks.append(f"[PAGE SOURCE — {url}]\n{landing}")
    # 3) Si la source EST le site officiel (aucun lien sortant retenu), lire ses sous-pages.
    if not official:
        blocks += _deep_read(html, url, timeout, n_sub, "site officiel")
    return "\n\n".join(blocks)


def gather_material(conn: sqlite3.Connection, ev: dict) -> str:
    """Agrège (déterministe) la matière, par ordre de priorité :
    1) dossiers de presse rattachés ; 2) PAGE OFFICIELLE récupérée en direct ;
    3) signaux flux/radar (description + doublons fusionnés). Le LLM rédige à partir
    de cette matière RÉELLE — il n'a pas à « connaître » l'événement."""
    parts = []
    own = (ev.get("description") or "").strip()
    if own:
        parts.append(own)
    for row in conn.execute(
        "SELECT description, source_name FROM events_raw WHERE duplicate_of = ?",
        (ev["id"],)
    ):
        d = (row["description"] or "").strip()
        if d and d not in parts:
            parts.append(d)
    from utils.clean_text import strip_boilerplate
    rss = re.sub(r"(?s)<[^>]+>", " ", "\n\n---\n\n".join(parts))
    rss = strip_boilerplate(rss)[:6000]   # retire spacers Elementor, pied RSS, boutons

    press = gather_press_kits(conn, ev)
    if press:
        press = re.sub(r"(?s)<[^>]+>", " ", press)
    page = fetch_official_material(ev.get("url_source", ""), title=ev.get("title", ""))

    sections = []
    if press:
        sections.append(f"[DOSSIER(S) DE PRESSE — source primaire, prioritaire]\n{press}")
    if page:
        sections.append(f"[SITE OFFICIEL DE L'ÉVÉNEMENT — accueil + programmation, lu en direct, source primaire]\n{page}")
    if rss:
        sections.append(f"[SIGNAUX FLUX / RADAR]\n{rss}")
    return "\n\n".join(sections) or "(aucune — titre seul)"


def _parse_day(s: str) -> "date | None":
    """Parse une date ISO tolérante (garde les 10 premiers caractères). None si illisible."""
    try:
        return date.fromisoformat((s or "").strip()[:10])
    except ValueError:
        return None


def _dates_hint(ev: dict) -> str:
    """Dates réelles de l'événement pour le prompt, AVEC LE STATUT calculé par rapport à
    AUJOURD'HUI (déterministe). Le modèle ne connaît pas la date du jour : sans ça, il
    annonce au futur (« à venir », « billetterie pas encore publiée ») un événement déjà
    commencé. On lui impose le cadre temporel."""
    s = (ev.get("date_event_start") or "").strip()
    e = (ev.get("date_event_end") or "").strip()
    today = datetime.now().date()
    ds, de = _parse_day(s), _parse_day(e)
    start_d, end_d = ds, (de or ds)
    plage = f"du {s} au {e}" if (s and e and s != e) else (s or (f"jusqu'au {e}" if e else ""))
    now_str = today.isoformat()
    if start_d and end_d:
        if today < start_d:
            return (f"{plage or s} — À VENIR (nous sommes le {now_str}). Écris au futur proche, "
                    "sans inventer d'infos non encore publiées.")
        if today > end_d:
            return (f"{plage or e} — DÉJÀ TERMINÉ (nous sommes le {now_str}). NE l'annonce PAS "
                    "comme à venir ; parle au passé, ou n'en fais pas la promotion.")
        return (f"{plage or e} — EN COURS aujourd'hui {now_str} (commencé le "
                f"{start_d.isoformat()}, se termine le {end_d.isoformat()}). Écris au PRÉSENT "
                "« en cours jusqu'au … » ; n'écris JAMAIS « à venir », « prochainement », ni "
                "que le programme ou la billetterie « n'est pas encore » publié : l'événement "
                "a commencé.")
    # Dates non exploitables : filet minimal.
    return plage or ev.get("date_start") or "à confirmer"


def _final_text(message) -> str:
    """Concatène les blocs texte de la réponse (en ignorant les blocs d'outil web)."""
    out = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            out.append(block.text)
    return "\n".join(out)


def _tier_model(ev: dict, mode: str) -> "tuple[bool, str]":
    """Décide le PALIER (court/long) et le MODÈLE pour un événement (CHARTE §3).

    - mode "auto" (défaut) : le SCORE décide — ≥ LONG_MIN_SCORE → LONG, sinon COURT ;
      "court"/"long" forcent ; "off" est géré en amont.
    - modèle : Haiku PARTOUT par défaut (économique). Pour donner aux PHARES un
      modèle supérieur : ENRICH_LONG_MODEL=claude-sonnet-5. ANTHROPIC_MODEL_ENRICH
      force un modèle unique pour tout (voir plus bas)."""
    from utils import settings as pipeline_settings
    score = int(ev.get("llm_score") or 0)
    if mode == "long":
        court = False
    elif mode == "court":
        court = True
    else:  # "auto"
        court = score < LONG_MIN_SCORE
    # Modèle : Haiku (éco) partout PAR DÉFAUT — on ne dépense pas tant que le prompt
    # renforcé (gras/structure) n'a pas été jugé insuffisant. Pour offrir aux PHARES
    # (long) un modèle supérieur : ENRICH_LONG_MODEL=claude-sonnet-5. ANTHROPIC_MODEL_ENRICH
    # force un modèle UNIQUE pour tout (test / contrôle de coût).
    forced = os.getenv("ANTHROPIC_MODEL_ENRICH", "").strip()
    long_model = os.getenv("ENRICH_LONG_MODEL", "").strip() or pipeline_settings.model_eco()
    model = forced or (pipeline_settings.model_eco() if court else long_model)
    return court, model


def enrich_event(ev: dict, material: str, client: anthropic.Anthropic, model: str,
                 court: bool, extra_task: str = "", allow_web: bool = True):
    """Un appel agentique (recherche web → rédaction). Gère pause_turn + API_ERROR.
    `court`/`model` sont décidés par l'appelant via _tier_model. `extra_task` : consigne
    supplémentaire ajoutée en fin de prompt (ex. retour de l'agent persona lecteur pour une
    révision). `allow_web` : autorise la recherche web (coupée quand on a déjà la matière
    officielle — la source officielle fait foi, le web n'est qu'un secours)."""
    from utils.voix import voix_block
    from utils import settings as pipeline_settings  # COURT_MAX_TOKENS (mode court)
    _court = court
    prompt = voix_block() + ENRICH_PROMPT.format(
        title=ev.get("title", ""),
        dates=_dates_hint(ev),
        lieu=ev.get("lieu") or ev.get("ville") or "—",
        territoire=ev.get("territoire", ""),
        organisateur=ev.get("organisateur") or ev.get("source_name") or "—",
        categorie=ev.get("llm_categorie") or "—",
        material=material,
    )
    if _court:
        prompt += ("\n\n[MODE COURT — petit événement] Encore plus BREF (~120-200 mots, 1-2 "
                   "paragraphes), SANS recherche web : appuie-toi uniquement sur les informations "
                   "ci-dessus. Va droit à l'essentiel — MAIS garde les FAITS STRUCTURÉS OBLIGATOIRES "
                   "(§5 bis) : le champ \"programme\" (liste : horaires, séances, line-up…), les tarifs "
                   "et la langue sont OBLIGATOIRES dès que la matière les contient.")
    if extra_task:
        prompt += "\n\n" + extra_task
    messages = [{"role": "user", "content": prompt}]
    try:
        # Boucle de l'outil serveur : on relance tant que le tour est « en pause ».
        # STREAMING : indispensable ici (recherche web + raisonnement = requêtes longues)
        # — évite les read-timeouts silencieux. On logge chaque tour pour la traçabilité.
        # Mode COURT (Agenda) : tokens réduits, PAS de recherche web ni thinking → bien
        # moins cher. Mode LONG (Cultura Sabauda) : plein (web + thinking + 8000 tokens).
        _max = pipeline_settings.COURT_MAX_TOKENS if _court else MAX_TOKENS
        web_on = USE_WEB_SEARCH and allow_web and not _court
        kwargs = dict(model=model, max_tokens=_max, messages=messages)
        if web_on:
            kwargs["tools"] = [WEB_SEARCH_TOOL]
        if USE_THINKING and not _court:
            kwargs["thinking"] = {"type": "adaptive"}
        for turn in range(1, (MAX_WEB_SEARCHES + 4) if web_on else 2):
            log.info("[%d] appel API tour %d… (web=%s, thinking=%s)",
                     ev["id"], turn, web_on, USE_THINKING)
            kwargs["messages"] = messages
            with client.messages.stream(**kwargs) as stream:
                message = stream.get_final_message()
            usage.record_message(model, message, label="enrichissement")
            out_tok = getattr(getattr(message, "usage", None), "output_tokens", "?")
            log.info("[%d] tour %d : stop_reason=%s, %s tokens sortie",
                     ev["id"], turn, message.stop_reason, out_tok)
            if message.stop_reason == "max_tokens":
                log.warning("[%d] réponse coupée (max_tokens=%d) — augmente ENRICH_MAX_TOKENS",
                            ev["id"], MAX_TOKENS)
            if message.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": message.content})
                continue
            break
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        usage.note_api_error(exc)
        log.error("[%d] Erreur API Anthropic : %s", ev["id"], exc)
        return API_ERROR
    except Exception as exc:  # tout autre échec (ne jamais rester silencieux)
        log.error("[%d] Échec enrichissement inattendu : %s", ev["id"], exc)
        return API_ERROR

    raw = _final_text(message)
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        log.warning("Pas de JSON pour '%s'", ev.get("title", "")[:50])
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError as exc:
        log.warning("JSON invalide pour '%s' : %s", ev.get("title", "")[:50], exc)
        return None


_CHECKS_DDL = """
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT
)"""


def _ensure_checks_table(conn: sqlite3.Connection) -> None:
    """Table des points « à vérifier » (garde-fou humain sur les faits). Idempotent."""
    conn.execute(_CHECKS_DDL)
    conn.commit()


def sync_checks(conn: sqlite3.Connection, event_id: int, labels) -> None:
    """Resynchronise les points EN ATTENTE d'un événement avec les doutes de l'agent.
    On retire les 'pending' existants (l'enrichissement fait foi) et on réinsère la
    nouvelle liste ; les points déjà 'done' (vérifiés par l'humain) sont conservés.
    Défensif : labels peut être None, une chaîne, ou une liste."""
    _ensure_checks_table(conn)
    if isinstance(labels, str):
        labels = [labels]
    clean = [str(x).strip() for x in labels if str(x).strip()] if isinstance(labels, list) else []
    conn.execute("DELETE FROM checks WHERE event_id=? AND status='pending'", (event_id,))
    for label in clean:
        conn.execute("INSERT INTO checks (event_id, label) VALUES (?, ?)", (event_id, label))


def build_article_md(data: dict) -> tuple[str, str]:
    """Assemble (titre, markdown) depuis le JSON de l'agent (déterministe)."""
    from utils.clean_text import polish_prose
    art = data.get("article") or {}
    titre = (art.get("titre") or "").strip()
    # Corps et chapô : nettoyage déterministe en CODE (tiret cadratin, gras sur chiffres)
    # car le modèle n'est pas fiable. Le rendu (build_post) l'applique aussi. Titres/
    # programme laissés intacts.
    chapo = polish_prose((art.get("chapo") or "").strip())
    corps = polish_prose((art.get("corps") or "").strip())
    encadre = (art.get("encadre") or "").strip()
    sources = [s for s in (data.get("sources") or []) if s]
    # Programme (CHARTE §5 bis) : faits structurés en LISTE, y compris en mode court.
    # Défensif : le champ peut être absent, None, vide, ou (erreur LLM) une chaîne.
    prog = art.get("programme")
    if isinstance(prog, str):
        prog = [prog]
    programme = [str(p).strip() for p in prog if str(p).strip()] if isinstance(prog, list) else []

    md = []
    if titre:
        md.append(f"# {titre}")
    if chapo:
        # PAS de gras forcé sur le chapô : l'accroche Agenda porte dates/noms/chiffres,
        # sur lesquels la charte interdit le gras. Le chapô se distingue par sa position.
        md.append(chapo)
    if corps:
        md.append(corps)
    if programme:
        md.append("## Programme\n\n" + "\n".join(f"- {p}" for p in programme))
    if encadre:
        md.append("## En pratique\n\n" + encadre)
    if sources:
        md.append("## Sources\n\n" + "\n".join(f"- {s}" for s in sources))
    return titre, "\n\n".join(md).strip()


def select_events(conn: sqlite3.Connection, ids: list[int],
                  dfrom: str = "", dto: str = "") -> list[sqlite3.Row]:
    if ids:
        qmarks = ",".join("?" * len(ids))
        return conn.execute(
            f"SELECT * FROM events_raw WHERE id IN ({qmarks})", ids).fetchall()
    # Événements retenus (≥ seuil), pas encore enrichis. Les doublons 'merged' sont
    # exclus : leur matière est déjà agrégée vers le gagnant.
    where = ["statut IN ('evaluated', 'published_sub')", "llm_score >= ?",
             "(enrich_status IS NULL OR enrich_status = '')", "(duplicate_of IS NULL)"]
    params: list = [MIN_SCORE]
    if dfrom and dto:  # circonscrit à la période de travail (chevauchement)
        where.append("COALESCE(date_event_start,'') <= ? AND COALESCE(date_event_end,'') >= ?")
        params += [dto, dfrom]
    return conn.execute(
        f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
        "ORDER BY llm_score DESC, scrape_date DESC LIMIT ?",
        (*params, BATCH_SIZE)).fetchall()


def reader_review(article: dict, ev: dict, client, model: str,
                  persona: dict | None = None, mode: str = "local") -> dict:
    """AGENT PERSONA LECTEUR : lit l'article dans la peau d'UN persona (docs/personas/) et
    renvoie son retour au rédacteur. `mode` : "local" (l'événement est dans SON territoire :
    accès, pertinence quotidienne) ou "visite" (l'événement est dans une aire adjacente : le
    persona juge si ça vaut un aller-retour / week-end). {} si l'appel échoue. Renvoie
    {"persona": ..., "role": "local"|"visite", "interet": 0-5, "manques": [...],
    "verdict": "ok"|"revise", "note": ...}."""
    import re as _re
    art = (article.get("article") or {}) if isinstance(article, dict) else {}
    corps = (art.get("corps") or "")[:3000]
    if not corps:
        return {}
    who = (persona or {}).get("text") or (
        "Tu es un LECTEUR de l'agenda culturel Agenda Sabauda (PAS un rédacteur), pressé et "
        "exigeant : tu veux apprendre quelque chose de concret sur CET événement.")
    pname = (persona or {}).get("title") or "Lecteur"
    mode_txt = (
        "L'événement est dans TON territoire : juge s'il te parle et si tu peux y aller "
        "(accès, distance depuis chez toi, prix quand c'est pertinent) — mais ne pénalise "
        "pas un événement RÉEL et proche juste parce qu'un détail pratique manque encore."
        if mode == "local" else
        "ATTENTION : cet événement n'est PAS chez toi, il est dans une aire VOISINE de la "
        "tienne. Tu ne juges donc PAS l'accès quotidien, mais la valeur de DÉPLACEMENT : "
        "est-ce un assez bon motif pour faire l'aller-retour ou un week-end depuis chez toi ? "
        "Qu'est-ce qui donnerait envie de faire la route ? Ne pénalise pas la simple distance "
        "(elle est admise, tu es prêt à te déplacer si ça vaut le coup) : juge si l'article te "
        "DONNE une vraie raison de venir.")
    prompt = (
        "Tu incarnes CE persona lecteur de l'agenda culturel Agenda Sabauda (tu n'es PAS un "
        "rédacteur, tu es ce lecteur précis, avec ses attentes et ses agacements) :\n"
        f"\"\"\"\n{who}\n\"\"\"\n\n"
        "Lis ce preview d'événement et réponds franchement, DE TON POINT DE VUE : est-ce que "
        "ça t'APPREND quelque chose d'utile et de concret sur CET événement, ou est-ce creux "
        "(« festival au bord du lac, programmation à venir ») ? Un bon preview te donne envie "
        "d'y aller ET t'apprend quelque chose.\n\n"
        "JUGE LA SUBSTANCE SELON LE TYPE D'ÉVÉNEMENT, pas selon un modèle unique : la « tête "
        "d'affiche » n'a de sens que pour un concert pop/variété. Pour un festival de musique "
        "CLASSIQUE, la substance ce sont les œuvres, compositeurs, orchestres, solistes, "
        "chefs, lieux ; pour une expo, les artistes et les œuvres ; pour un spectacle, la "
        "pièce et la troupe ; pour une fête, le programme et les temps forts. Ne réclame pas "
        "des noms « grand public » quand le genre n'en a pas : demande la substance de CE "
        "genre-là.\n"
        f"{mode_txt}\n\n"
        f"TITRE : {art.get('titre') or ev.get('title')}\n"
        f"CATÉGORIE : {ev.get('llm_categorie', '')}\n"
        f"ARTICLE :\n{corps}\n\n"
        'Réponds en JSON STRICT : {"interet": <0-5, 0=creux 5=riche>, '
        '"manques": ["<ce qui te manque VRAIMENT, selon TES attentes et le genre>"], '
        '"verdict": "ok"|"revise", "note": "<1 phrase de conseil au rédacteur>"}. '
        'verdict = "revise" seulement si l\'article est réellement creux pour TOI (interet <= 2) '
        "ou s'il lui manque une substance qui EXISTE et qu'il aurait dû donner."
    )
    try:
        msg = client.messages.create(model=model, max_tokens=400,
                                     messages=[{"role": "user", "content": prompt}])
    except Exception:  # noqa: BLE001 — non bloquant
        return {}
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text")
    m = _re.search(r"\{.*\}", raw, _re.S)
    if not m:
        return {}
    try:
        out = json.loads(m.group())
    except (ValueError, TypeError):
        return {}
    if not isinstance(out, dict):
        return {}
    out["persona"] = pname
    out["role"] = mode
    return out


def reader_panel(article: dict, ev: dict, client, model: str) -> dict:
    """Fait relire l'article par le panel de personas CIBLÉ SUR LE TERRITOIRE de l'événement
    (un événement de Menton est jugé par des lecteurs de Nice, pas de Maurienne — sinon la
    note mesure la distance, pas la qualité). Renvoie un verdict agrégé :
    {"reviews": [...], "verdict": "ok"|"revise", "mean": <float>}. Révision si la MAJORITÉ
    vote « revise ». {} si aucun persona (panel désactivé, non bloquant)."""
    territoire = ev.get("territoire", "")
    try:
        from utils import personas as personas_mod
        locaux = personas_mod.personas_for(territoire)
        visiteurs = personas_mod.personas_visiting(territoire)
    except Exception:  # noqa: BLE001 — non bloquant
        locaux, visiteurs = [], []
    if not locaux:
        return {}
    try:
        cap = int(os.getenv("ENRICH_READER_PERSONAS", "0") or 0)
    except ValueError:
        cap = 0
    if cap > 0:
        locaux = locaux[:cap]
    log.info("[%s] panel territoire=%s | locaux: %s | visiteurs: %s", ev.get("id"),
             territoire or "?",
             ", ".join(p["title"].split(",")[0] for p in locaux) or "—",
             ", ".join(p["title"].split(",")[0] for p in visiteurs) or "—")

    reviews = [r for r in (reader_review(article, ev, client, model, persona=p, mode="local")
                           for p in locaux) if r]
    visite_reviews = [r for r in (reader_review(article, ev, client, model, persona=p,
                                                 mode="visite") for p in visiteurs) if r]
    if not reviews:
        return {}
    # La NOTE et la décision de révision sont pilotées par les LOCAUX (le public premier) ;
    # les visiteurs sont un signal complémentaire (« ça vaut le déplacement ? »).
    votes = sum(1 for r in reviews if r.get("verdict") == "revise")
    scores = [r["interet"] for r in reviews if isinstance(r.get("interet"), (int, float))]
    mean = round(sum(scores) / len(scores), 1) if scores else None
    vscores = [r["interet"] for r in visite_reviews if isinstance(r.get("interet"), (int, float))]
    vmean = round(sum(vscores) / len(vscores), 1) if vscores else None
    # Révision déclenchée par la NOTE des locaux, pas un demi-vote : un article correct
    # (≥ seuil) ne doit pas subir une réécriture coûteuse. ENRICH_REVISE_UNDER (défaut 3).
    try:
        seuil = float(os.getenv("ENRICH_REVISE_UNDER", "3") or 3)
    except ValueError:
        seuil = 3.0
    verdict = "revise" if (mean is not None and mean < seuil) else "ok"
    return {"reviews": reviews, "visite_reviews": visite_reviews,
            "verdict": verdict, "mean": mean, "vmean": vmean, "votes": votes}


def revise_article(result: dict, panel: dict, ev: dict, material: str,
                   client, model: str, court: bool, allow_web: bool = True):
    """Réécrit l'article en tenant compte des retours DU PANEL de lecteurs. Renvoie le
    nouveau result, ou l'ancien si la révision échoue."""
    lignes = []
    for r in (panel.get("reviews") or []) + (panel.get("visite_reviews") or []):
        if r.get("verdict") != "revise":
            continue
        role = "visiteur" if r.get("role") == "visite" else "local"
        lignes.append("- %s (%s, intérêt %s) : %s%s" % (
            r.get("persona", "Lecteur"), role, r.get("interet"),
            r.get("note") or "—",
            (" — manque : " + ", ".join(r.get("manques") or [])) if r.get("manques") else ""))
    critique = "\n".join(lignes) or "Article jugé creux par le panel."
    extra = ("[RETOURS DE LECTEURS sur ton brouillon précédent — CORRIGE-LE]\n" + critique +
             "\nRends l'article plus SUBSTANTIEL et CONCRET, avec les éléments propres AU TYPE "
             "d'événement (classique : œuvres, compositeurs, orchestres, solistes, chefs, "
             "lieux ; pop : têtes d'affiche ; expo : artistes et œuvres ; spectacle : pièce et "
             "troupe), pris du programme fourni ou, à défaut, de l'ÉDITION PRÉCÉDENTE via "
             "recherche web. N'INVENTE RIEN : si une info (nom, tarif, horaire) n'est pas "
             "publiée, ne la fabrique pas — mais NE COMMENTE PAS non plus son absence "
             "(« à ce stade, la matière ne précise pas… » est INTERDIT). Écris seulement les "
             "faits certains, sans jamais parler de ce qui manque. Ne meuble pas : le lecteur "
             "doit APPRENDRE quelque chose de réel.")
    revised = enrich_event(ev, material, client, model, court, extra_task=extra,
                           allow_web=allow_web)
    return revised if (revised and revised is not API_ERROR) else result


def main(argv: list[str]) -> int:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY non définie")
        return 1
    # Réglages back-office : on/off + court/long, et profil de modèle.
    from utils import settings as pipeline_settings
    if not pipeline_settings.enrich_enabled():
        log.info("Enrichissement DÉSACTIVÉ (réglage back-office). Rien à faire.")
        return 0
    mode = pipeline_settings.enrich_mode()   # off/auto/court/long — le palier est décidé par événement
    ids = [int(a) for a in argv if a.isdigit()]
    dfrom = dto = ""
    if "--from" in argv:
        dfrom = argv[argv.index("--from") + 1] if argv.index("--from") + 1 < len(argv) else ""
    if "--to" in argv:
        dto = argv[argv.index("--to") + 1] if argv.index("--to") + 1 < len(argv) else ""
    # Timeout dur : une requête (même longue avec recherche web) ne doit jamais
    # pendre indéfiniment — au pire elle échoue proprement et c'est loggé.
    client = anthropic.Anthropic(api_key=api_key, timeout=180.0)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _ensure_checks_table(conn)

    events = select_events(conn, ids, dfrom, dto)
    log.info("ids à traiter : %s", [e["id"] for e in events])
    log.info("%d événement(s) à enrichir (mode=%s ; long→%s, court→%s ; plancher score ≥ %d)",
             len(events), mode, pipeline_settings.model_qualite(),
             pipeline_settings.model_eco(), MIN_SCORE)

    done = 0
    for event in events:
        ev = dict(event)
        # Vignette de secours : si le flux n'a pas d'image, prendre l'og:image de la
        # page officielle (déterministe). Sert à la fiche ET à l'image à la une WordPress.
        if not (ev.get("url_image") or "").strip():
            og = fetch_og_image(ev.get("url_source", ""))
            if og:
                conn.execute("UPDATE events_raw SET url_image=? WHERE id=?", (og, ev["id"]))
                conn.commit()
                ev["url_image"] = og
                log.info("[%d] image récupérée (og:image) : %s", ev["id"], og[:80])
        material = gather_material(conn, ev)
        court, model = _tier_model(ev, mode)   # palier + modèle PAR événement
        # La source officielle fait foi : si on a déjà la matière officielle (page presse/
        # programme ou dossier de presse), on COUPE la recherche web (redondante, lente,
        # coûteuse, source de troncature). Le web ne reste qu'un secours quand on n'a rien.
        has_official = ("[PAGE PRESSE/PROGRAMME" in material or "[DOSSIER" in material)
        allow_web = not has_official
        log.info("[%d] palier=%s modèle=%s (score=%s) | matière officielle=%s → web=%s",
                 ev["id"], "court" if court else "long", model, ev.get("llm_score"),
                 has_official, USE_WEB_SEARCH and allow_web and not court)
        result = enrich_event(ev, material, client, model, court, allow_web=allow_web)
        if result is API_ERROR:
            # Trace visible côté back-office (sinon l'utilisateur ne voit « rien »).
            conn.execute(
                "UPDATE events_raw SET enrich_status='api_error', "
                "enriched_at=datetime('now'), enrich_model=? WHERE id=?", (model, ev["id"]))
            conn.commit()
            log.warning("[%d] erreur API — marqué 'api_error', arrêt du lot", ev["id"])
            break
        if result is None:
            conn.execute(
                "UPDATE events_raw SET enrich_status='error', "
                "enriched_at=datetime('now'), enrich_model=? WHERE id=?",
                (model, ev["id"]))
            conn.commit()
            continue
        # PANEL LECTEURS : sur les articles développés (palier long), tout le panel de
        # personas (docs/personas/) relit le brouillon. Si la majorité le juge creux (pas de
        # têtes d'affiche, pas de temps forts), on demande UNE révision au rédacteur. Les
        # retours sont stockés pour le back-office. Non bloquant, long uniquement (le court
        # est un catalogue).
        if not court and os.getenv("ENRICH_READER_REVIEW", "1") == "1":
            review_model = pipeline_settings.model_eco()
            panel = reader_panel(result, ev, client, review_model)
            if panel.get("verdict") == "revise":
                log.info("[%d] panel lecteurs: moyenne=%s, %s vote(s) révision → révision",
                         ev["id"], panel.get("mean"), panel.get("votes"))
                result = revise_article(result, panel, ev, material, client, model, court,
                                        allow_web=allow_web)
                panel = reader_panel(result, ev, client, review_model) or panel
            if panel:
                result["reader_panel"] = panel
        title, md = build_article_md(result)
        conn.execute("""
        UPDATE events_raw SET
            enrich_status='enriched', enriched_at=datetime('now'), enrich_model=?,
            enrich_data=?, article_title=?, article_md=?
        WHERE id=?
        """, (model, json.dumps(result, ensure_ascii=False), title, md, ev["id"]))
        conn.commit()
        # File « À vérifier » : les doutes factuels signalés par l'agent sont poussés au
        # back-office (garde-fou humain). On resynchronise les points EN ATTENTE (les
        # points déjà « vérifiés » sont conservés).
        labels = result.get("a_verifier")
        sync_checks(conn, ev["id"], labels)
        conn.commit()
        done += 1
        log.info("[%d] enrichi (confiance=%s) | %d à vérifier | %s", ev["id"],
                 result.get("confiance", "?"), len(labels or []), ev.get("title", "")[:60])

    conn.close()
    log.info("=== Enrichissement terminé : %d/%d ===", done, len(events))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
