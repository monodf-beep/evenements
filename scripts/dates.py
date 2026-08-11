#!/usr/bin/env python3
"""Extraction de la VRAIE date d'un événement (déterministe, sans LLM).

Le flux RSS ne donne que sa date de PUBLICATION (`entry.published`) — pas la date de
l'événement. Or on veut pouvoir circonscrire le travail (évaluation/rédaction) à une
PÉRIODE (« ce week-end », « week-end prochain »). Il faut donc extraire la période
réelle depuis le TEXTE (titre + description), en FR et IT.

LLM ? NON — parsing structuré à fort volume = code (voir docs/LLM_OU_CODE.md). On
gère les cas courants d'une programmation culturelle :
  - « le 5 juillet », « 5 juillet 2026 », « du 5 au 8 juillet », « du 30 juin au 3 juillet »
  - « dal 5 all'8 luglio », « dal 30 giugno al 3 luglio », « 5-8 luglio »
  - « jusqu'au 30 août » / « fino al 30 agosto » (fin seule → en cours jusqu'à…)
  - ISO 2026-07-05, dates numériques 05/07/2026, 05.07.2026 (jj/mm/aaaa, format européen)

Trois passes, du plus sûr/gratuit au dernier recours :
  1. TEXTE (titre + description) — regex FR/IT, gratuit et instantané ;
  2. PAGE structurée — JSON-LD schema.org Event + <time datetime> (déterministe) ;
  3. LLM — jugement de langue sur la prose de la page, quand 1 et 2 échouent
     (beaucoup de sites, surtout IT, ne donnent la date qu'en toutes lettres).
     Économique, borné, idempotent ; désactivable par DATES_LLM=0.

Sortie stockée : date_event_start / date_event_end (ISO AAAA-MM-JJ) + date_source
+ date_checked_at (DATE de la dernière tentative).

AUCUN ÉCHEC N'EST DÉFINITIF (depuis le 2026-08-03). Une fiche restée non datable est
automatiquement re-tentée après DATE_COOLDOWN_DAYS (défaut 7). Avant, la sortie de
l'impasse exigeait qu'un humain tape `--retry` en ayant deviné qu'il fallait le faire.
L'enjeu est lourd : sans date, publish_batch_as REFUSE la création — une fiche non
datable bloquée à vie est une fiche perdue, pas une fiche imparfaite.
('parsed' | 'page' | 'llm' | 'none' | 'nodate' | 'llm_none'). Les non-datés vont
dans le bac « date à confirmer ». Cron : après dedupe, avant l'évaluation.
"""
from __future__ import annotations
import argparse
import html as htmlmod
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import slack
from utils.annulation import marqueur_annulation
from scripts.scraper_events import init_db
from dotenv import load_dotenv

log = get_logger("dates")
# Logger dédié au canal 3 (docs/EVENEMENTS_ANNULES.md), partagé avec venues.py : les deux
# modules appellent `signale_annulation_page` ci-dessous, et un message « [id] annulation
# suspectée » doit se retrouver sous une même étiquette qu'on relise depuis dates.py ou
# depuis venues.py — pas étiqueté « dates » quand c'est venues.py qui a fait l'appel.
_log_annulation = get_logger("annulation")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
# Récupération de la date sur la PAGE de l'événement (2ᵉ passe, déterministe).
FETCH_CAP = int(os.getenv("DATES_FETCH_CAP", "200"))   # pages fetchées par run (max)
FETCH_TIMEOUT = int(os.getenv("DATES_FETCH_TIMEOUT", "10"))
# UA de NAVIGATEUR : beaucoup de sites (WAF/CDN) renvoient 403/404 à un robot déclaré.
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
       "Accept-Language": "fr,it;q=0.8,en;q=0.6"}


def _swap_www(url: str) -> str:
    """Bascule www ↔ non-www dans l'hôte (redirections mal configurées → 404)."""
    from urllib.parse import urlsplit, urlunsplit
    p = urlsplit(url)
    host = p.netloc[4:] if p.netloc.startswith("www.") else "www." + p.netloc
    return urlunsplit((p.scheme, host, p.path, p.query, p.fragment))


_SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>")


def _sans_script(html: str) -> str:
    """HTML débarrassé des balises <script>/<style>/<noscript> — sert au canal 3
    (marqueur d'annulation, voir `signale_annulation_page` plus bas) : sans ce
    nettoyage, le simple mot « report » planqué dans un identifiant d'analytics ou
    de bandeau cookies (fréquent sur ces pages) suffirait à déclencher une fausse
    alerte. Plus léger que `fetch_page_text` : pas de fenêtrage ni de troncature,
    la détection doit voir TOUTE la page, pas seulement la zone utile à la date."""
    return _SCRIPT_STYLE_RE.sub(" ", html or "")


def signale_annulation_page(conn: sqlite3.Connection, event: dict, texte: str,
                            regex=None, source: str = "") -> str | None:
    """Canal 3 (docs/EVENEMENTS_ANNULES.md) : un marqueur d'annulation/report posé
    directement sur la PROPRE page source d'un événement déjà en base — pas dans un
    article tiers apparié par la dédup (canal 2, `scripts.dedupe._porte_annulation`).

    Appelée par `main()` ici et dans `scripts/venues.py`, juste après une relecture
    de page qui a effectivement récupéré du texte (`fetch_event_dates`/
    `fetch_page_text` côté dates, `fetch_event_venue`/`fetch_page_text` côté venues)
    — « second filet, même bac » (docs/EVENEMENTS_ANNULES.md).

    DIFFÉRENCE avec le canal 2 : là-bas, la fiche VISÉE (le festival) et la fiche
    qui PORTE le marqueur (l'article d'annulation) sont deux fiches distinctes. Ici
    c'est LA MÊME fiche — sa propre page dit qu'elle est annulée/reportée. On
    réutilise donc EXACTEMENT les mêmes colonnes que le canal 2
    (`scripts.dedupe.ensure_annulation_columns`, jamais un schéma parallèle) en
    posant `annulation_fiche_visee_id` = son propre id et
    `annulation_visee_etait_publiee` = son propre `wp_post_id_as` au moment du
    signal. Résultat : `scripts.audit_annulations` n'a besoin d'AUCUNE modification
    — sa requête relit la fiche visée par id, qu'elle soit une autre fiche (canal 2)
    ou elle-même (canal 3), et ses deux rouvreurs (automatique si elle était publiée
    et ne l'est plus, manuel sinon via `--resolu`) s'appliquent identiquement.

    PAS DE SPAM : si `annulation_detectee_at` est déjà posé, on se tait — la
    suspicion reste active, `scripts.audit_annulations` continue de la recompter.
    NE BLOQUE RIEN D'AUTRE : appelée en plus du traitement normal de date/lieu,
    jamais à la place — le signal est un AJOUT (arbitrage du 2026-08-05 : alerte
    Slack seulement, jamais de bandeau ni de dépublication automatique, un humain
    confirme). Renvoie le marqueur trouvé (pour le log de l'appelant), ou None."""
    if event.get("annulation_detectee_at"):
        return None
    marqueur = marqueur_annulation(texte, regex)
    if not marqueur:
        return None
    conn.execute(
        "UPDATE events_raw SET annulation_detectee_at=datetime('now'), "
        "annulation_source_url=?, annulation_fiche_visee_id=?, "
        "annulation_visee_etait_publiee=?, annulation_marqueur=? WHERE id=?",
        (event.get("url_source", ""), event["id"],
         1 if event.get("wp_post_id_as") else 0, marqueur, event["id"]))
    conn.commit()
    slack.notify(
        f"🔴 *Annulation suspectée* — « {(event.get('title') or '')[:80]} »\n"
        f"Marqueur « {marqueur} » repéré sur SA PROPRE page source"
        + (f" ({source})" if source else "") + ".\n"
        f"URL : {event.get('url_source', '?')}\n"
        f"Rien n'est bloqué : la date/le lieu continuent d'être tenus à jour "
        f"normalement — à confirmer toi-même. Une fois vérifié : "
        f"`.venv/bin/python -m scripts.audit_annulations --resolu {event['id']}` "
        f"(docs/EVENEMENTS_ANNULES.md).")
    _log_annulation.warning(
        "[%s] annulation suspectée sur sa PROPRE page (marqueur « %s », %s) — "
        "alerte envoyée, traitement normal non bloqué", event["id"], marqueur,
        source or "page")
    return marqueur


def _robust_get(url: str):
    """GET avec UA navigateur ; si échec/non-200, retente l'hôte www↔non-www.
    Renvoie une réponse 200 non vide, ou None."""
    tried = []
    for u in (url, _swap_www(url)):
        if u in tried:
            continue
        tried.append(u)
        try:
            r = requests.get(u, timeout=FETCH_TIMEOUT, headers=_UA, allow_redirects=True)
            if r.status_code == 200 and r.text:
                return r
        except requests.RequestException:
            continue
    return None
# 3ᵉ passe : datation LLM (jugement de langue) sur les non-datés que le regex et le
# JSON-LD n'ont pas su lire — beaucoup de pages (surtout IT) donnent la date en prose.
# Économique et borné. Actif si une clé Anthropic est présente (désactivable : DATES_LLM=0).
DATES_LLM = os.getenv("DATES_LLM", "1") not in ("0", "false", "False", "")
DATES_LLM_CAP = int(os.getenv("DATES_LLM_CAP", "150"))
DATES_LLM_MODEL = os.getenv("DATES_LLM_MODEL") or os.getenv("ANTHROPIC_MODEL_EXTRACT",
                                                            "claude-haiku-4-5-20251001")

_MONTHS = {
    # français
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
    # italien
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6,
    "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))


def _strip(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def _iso(y: int, m: int, d: int) -> str | None:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def _year(day: int, month: int, ref: date) -> int:
    """Année sous-entendue (année absente du texte). On suppose un événement « à venir » :
    on garde l'année courante tant que la date n'est pas trop dans le passé (grâce de
    60 j pour les événements en cours / qui viennent de commencer) ; au-delà = l'an prochain.
    Ex. (réf. 1er juillet) : « 30 juin » → cette année ; « 5 janvier » → l'an prochain."""
    y = ref.year
    cand = _iso(y, month, day)
    if cand and (ref - date.fromisoformat(cand)).days > 60:
        y += 1
    return y


def parse_dates(text: str, ref: date | None = None) -> tuple[str, str, str]:
    """(date_start_iso, date_end_iso, source). source = 'parsed' | 'none'."""
    ref = ref or date.today()
    t = _strip(text)
    M = _MONTHS

    # 1) ISO explicite (éventuellement en plage)
    iso = re.findall(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if iso:
        starts = [f"{y}-{m}-{d}" for y, m, d in iso]
        starts = [s for s in starts if _iso(*map(int, s.split("-")))]
        if starts:
            return (min(starts), max(starts), "parsed")

    # 2) Plage même mois : « du 5 au 8 juillet », « dal 5 al 8 luglio », « 5 e 6 luglio »,
    #    « sabato 5 e domenica 6 luglio » (un mot — ex. jour de semaine — toléré après le lien)
    m = re.search(rf"(?:du|dal|dall'|dall’|da)?\s*(?<!\d)(\d{{1,2}})(?!\d)\s*(?:au|al|all'|all’|et|e|&|[-–—à])\s*"
                  rf"(?:[a-zà-ÿ]+\s+)?(?<!\d)(\d{{1,2}})(?!\d)\s+({_MONTH_RE})\.?\s*(\d{{4}})?", t)
    if m:
        d1, d2, mon, yr = int(m[1]), int(m[2]), M[m[3]], m[4]
        y = int(yr) if yr else _year(min(d1, d2), mon, ref)
        s, e = _iso(y, mon, d1), _iso(y, mon, d2)
        if s and e:
            return (min(s, e), max(s, e), "parsed")

    # 3) Plage inter-mois « du 30 juin au 3 juillet [2026] » / « dal 30 giugno al 3 luglio »
    m = re.search(rf"(?:du|dal|dall'|dall’|da)\s*(\d{{1,2}})\s+({_MONTH_RE})\.?\s*(\d{{4}})?\s*"
                  rf"(?:au|al|all'|all’)\s*(\d{{1,2}})\s+({_MONTH_RE})\.?\s*(\d{{4}})?", t)
    if m:
        d1, mon1, y1, d2, mon2, y2 = int(m[1]), M[m[2]], m[3], int(m[4]), M[m[5]], m[6]
        # Année : si UNE SEULE borne la porte (« du 2 mars au 27 avril 2025 »), on la
        # PROPAGE à l'autre au lieu de la deviner — sinon _year() peut inventer une
        # année délirante pour la borne nue (ex. « 2 mars » → 2027) et créer une plage
        # de deux ans à l'envers. On recule/avance d'un an si l'ordre des mois l'impose.
        if y1 and y2:
            yy1, yy2 = int(y1), int(y2)
        elif y2 and not y1:            # année seulement sur la fin → la propager au début
            yy2 = int(y2)
            yy1 = yy2 if mon1 <= mon2 else yy2 - 1
        elif y1 and not y2:            # année seulement sur le début → la propager à la fin
            yy1 = int(y1)
            yy2 = yy1 if mon2 >= mon1 else yy1 + 1
        else:                          # aucune année → inférence + cohérence des mois
            yy1 = _year(d1, mon1, ref)
            yy2 = yy1 if mon2 >= mon1 else yy1 + 1
        s, e = _iso(yy1, mon1, d1), _iso(yy2, mon2, d2)
        if s and e:
            return (min(s, e), max(s, e), "parsed")

    # 4) Fin seule « jusqu'au 30 août » / « fino al 30 agosto » → en cours jusqu'à…
    m = re.search(rf"(?:jusqu['’ ]?au|fino all?['’ ]?|sino al)\s*(\d{{1,2}})\s+"
                  rf"({_MONTH_RE})\.?\s*(\d{{4}})?", t)
    if m:
        d2, mon, yr = int(m[1]), M[m[2]], m[3]
        y = int(yr) if yr else _year(d2, mon, ref)
        e = _iso(y, mon, d2)
        if e:
            return ("", e, "parsed")  # début inconnu = en cours

    # 5) Date simple « [le] 5 juillet [2026] » / « 5 luglio »
    m = re.search(rf"\b(\d{{1,2}})\s+({_MONTH_RE})\.?\s*(\d{{4}})?", t)
    if m:
        d1, mon, yr = int(m[1]), M[m[2]], m[3]
        y = int(yr) if yr else _year(d1, mon, ref)
        s = _iso(y, mon, d1)
        if s:
            return (s, s, "parsed")

    # 6) Numérique jj/mm/aaaa ou jj.mm.aaaa (format européen)
    m = re.search(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b", t)
    if m:
        d1, mon, y = int(m[1]), int(m[2]), int(m[3])
        s = _iso(y, mon, d1)
        if s:
            return (s, s, "parsed")

    return ("", "", "none")


# Heure : UNIQUEMENT des motifs avec un mot-clé de contexte sans ambiguïté (« à »/« dès »
# français, « ore » italien). Pas de motif « nu » (« 21h30 » seul) : sur un site culturel,
# une durée s'écrit pareil (« Zootopie 2, 1h45 », « un film de 2h30 ») — même philosophie
# que parse_dates : gratuit, sans LLM, ZÉRO tentative de deviner sur du texte ambigu.
_TIME_RE = re.compile(
    r"\bore\s+(?P<h1>[01]?\d|2[0-3])(?:[:.hH](?P<m1>[0-5]\d))?\b"    # italien : « ore 21 », « ore 21:30 »
    r"|\b(?:à|dès)\s+(?P<h2>[01]?\d|2[0-3])[hH](?P<m2>[0-5]\d)?\b",  # français : « à 21h30 », « dès 20h »
    re.IGNORECASE)

# « à » est ambigu quand il CLÔT une plage (« ouvert de 9h à 18h » → 18h est la fermeture,
# pas un début) : on écarte un match « à » précédé de près par un autre « Xh ».
_RANGE_BEFORE = re.compile(r"[01]?\d[hH]\d{0,2}\s*(?:-|–|—)?\s*$")


def extract_time(text: str) -> str:
    """Heure de DÉBUT réelle « HH:MM », ou "" si rien de fiable. Déterministe, gratuit.
    Prend le PREMIER motif fiable trouvé (l'heure de début est presque toujours
    mentionnée avant une éventuelle heure de fin dans un texte français/italien)."""
    t = _strip(text) if text else ""
    for m in _TIME_RE.finditer(t):
        if m.group("h2") is not None and _RANGE_BEFORE.search(t[max(0, m.start() - 12):m.start()]):
            continue  # « de 9h à 18h » : 18h ferme une plage, pas une heure de début
        h = m.group("h1") if m.group("h1") is not None else m.group("h2")
        mn = m.group("m1") or m.group("m2") or "00"
        return f"{int(h):02d}:{mn}"
    return ""


def dates_from_page(html: str) -> tuple[str, str, str]:
    """Extrait une date depuis le HTML d'une page d'événement, du plus FIABLE au moins :
    1) JSON-LD schema.org Event (startDate/endDate) — le standard des sites d'événements ;
    2) balises <time datetime="…"> ;
    3) meta (article:published_time n'est PAS la date d'événement → ignoré).
    Ne devine JAMAIS depuis le texte libre de la page (trop de faux positifs).

    ⚠️ ÉLARGI le 2026-08-11 (« implacable au niveau de la collecte AVANT de passer par
    les LLM », Franck). L'étage 1 ci-dessous cherchait la CHAÎNE `"startDate":"…"` dans
    le HTML : il ratait donc le bloc `@graph` de Yoast et Rank Math — la forme de la
    majorité des sites WordPress —, les tableaux de plusieurs objets, les guillemets
    échappés, et les types dérivés comme ExhibitionEvent. utils/jsonld.py PARSE les blocs
    au lieu d'y chercher un motif ; il passe en tête, et les deux étages historiques
    restent derrière lui comme filets."""
    # 0) JSON-LD réellement parsé (@graph, tableaux, sous-objets, microdata).
    from utils import jsonld as _jsonld
    _c = _jsonld.champs(html)
    if _c.get("date_event_start"):
        return (_c["date_event_start"],
                _c.get("date_event_end") or _c["date_event_start"], "page")
    # 1) JSON-LD "startDate": "2026-07-05" (ou avec heure "2026-07-05T21:00")
    ms = re.search(r'"startDate"\s*:\s*"(\d{4}-\d{2}-\d{2})', html)
    if ms:
        me = re.search(r'"endDate"\s*:\s*"(\d{4}-\d{2}-\d{2})', html)
        s = ms.group(1)
        e = me.group(1) if me else s
        if _iso(*map(int, s.split("-"))):
            return (min(s, e), max(s, e), "page")
    # 2) <time datetime="2026-07-05">
    times = re.findall(r'<time[^>]+datetime=["\'](\d{4}-\d{2}-\d{2})', html, re.I)
    times = [t for t in times if _iso(*map(int, t.split("-")))]
    if times:
        return (min(times), max(times), "page")
    # 3) Microdata itemprop — l'autre forme que schema.org autorise, tout aussi valable
    #    et jusqu'ici totalement ignorée.
    _m = _jsonld.champs_microdata(html)
    if _m.get("date_event_start"):
        return (_m["date_event_start"],
                _m.get("date_event_end") or _m["date_event_start"], "page")
    return ("", "", "")


def fetch_event_dates(url: str, _capture: dict | None = None) -> tuple[str, str, str]:
    """Télécharge la page et en extrait la date (JSON-LD/<time>). ('','','nodate') si rien.

    `_capture` (optionnel) : si fourni, reçoit sous la clé "text" le texte de la
    page RÉELLEMENT téléchargée (script/style retirés, cf. `_sans_script`) — sert au
    canal 3 (`signale_annulation_page`) sans forcer un second téléchargement de la
    même page. Purement additif : les appelants existants qui ignorent ce paramètre
    (ex. `scripts/autocomplete.py`) gardent exactement le même comportement."""
    if not url or url.startswith("gmail:") or "news.google.com" in url:
        return ("", "", "nodate")
    r = _robust_get(url)
    if r is None:
        return ("", "", "nodate")
    if _capture is not None:
        _capture["text"] = _sans_script(r.text)
    s, e, src = dates_from_page(r.text)
    return (s, e, "page") if src == "page" else ("", "", "nodate")


def fetch_page_text(url: str, title: str = "") -> str:
    """Texte visible d'une page (pour la datation LLM). '' si inaccessible/hors périmètre.

    Se CENTRE sur le contenu de l'événement au lieu de prendre bêtement les premiers
    caractères : sur une page d'institution, un énorme menu précède le contenu (la
    date de l'événement peut être à 70 000 caractères du début). On privilégie la
    balise <article>, sinon on fenêtre autour de la mention LA PLUS PROFONDE du titre
    (le fil d'Ariane en haut n'est pas le contenu). Sans ce recentrage, le LLM ne
    voit que du menu et rate la date pourtant présente."""
    if not url or url.startswith("gmail:") or "news.google.com" in url:
        return ""
    r = _robust_get(url)
    if r is None:
        return ""
    doc = re.sub(r"(?is)<(script|style|noscript|svg|form)\b[^>]*>.*?</\1>", " ", r.text)

    region = ""
    if title:
        # Fenêtre autour du TITRE-TITRE de l'événement : le <h1>/<h2> dont le texte
        # correspond au titre marque le début du contenu (l'intro datée suit juste
        # après). On matche le HEADING, pas une mention quelconque — sinon on tombe
        # sur un lien de partage en pied de page qui pointe un événement voisin
        # (cas Fondazione Merz : la date d'à-côté serait captée à tort).
        toks = {t.lower() for t in re.findall(r"[^\W\d_]{4,}", title, re.U)}
        best_pos, best_score = -1, 0
        if toks:
            for m in re.finditer(r"(?is)<h[12]\b[^>]*>(.*?)</h[12]>", doc):
                htext = re.sub(r"<[^>]+>", " ", m.group(1)).lower()
                score = sum(1 for t in toks if t in htext)
                if score > best_score:
                    best_score, best_pos = score, m.start()
        if best_pos >= 0:
            region = doc[max(0, best_pos - 300):best_pos + 10000]
    if not region:
        articles = re.findall(r"(?is)<article\b.*?</article>", doc)
        if articles:
            region = max(articles, key=len)  # le plus gros <article> = le contenu
    doc = region or doc

    doc = re.sub(r"(?is)<(nav|header|footer|aside)\b[^>]*>.*?</\1>", " ", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    return re.sub(r"\s+", " ", htmlmod.unescape(doc)).strip()[:6000]


def llm_dates(material: str, ref: date, client, model: str,
              title: str = "", context: str = "") -> tuple[str, str, str]:
    """Le LLM lit la matière et rend la période de l'ÉVÉNEMENT. ('','','llm_none') si rien.

    Jugement de langue (FR/IT), pas de parsing structuré : on ne l'utilise qu'en
    dernier recours, quand regex + JSON-LD ont échoué (voir docs/LLM_OU_CODE.md).

    `title`/`context` ANCRENT la recherche : une page d'institution liste souvent
    PLUSIEURS événements (avec chacun sa date). Sans savoir lequel nous intéresse,
    le LLM ne peut pas trancher. On lui donne donc le titre (et lieu/ville) de
    l'événement cible pour qu'il repère SA date, pas celle d'un voisin.
    """
    material = (material or "").strip()
    if not material:
        return ("", "", "llm_none")
    cible = ""
    if title:
        cible = (f"ÉVÉNEMENT CIBLE : « {title} »"
                 + (f" ({context})" if context else "") + "\n"
                 "Le texte ci-dessous peut décrire PLUSIEURS événements ; ne renvoie "
                 "que la date de CET événement précis. Si sa date n'y figure pas "
                 "(même si d'autres dates sont présentes), found=false.\n\n")
    prompt = (
        "Tu extrais la DATE de déroulement d'un événement culturel à partir du texte "
        "fourni (français ou italien). Ignore les dates de publication, d'inscription "
        "ou de vernissage isolé : ce qui compte, c'est QUAND l'événement a lieu.\n"
        f"Date du jour (pour déduire l'année si absente) : {ref.isoformat()}.\n"
        "Règles : une seule date → start = end ; une plage → les deux ; une fin seule "
        "(« jusqu'au… ») → start vide, end rempli ; si aucune date de l'événement cible "
        "n'est trouvable, found=false.\n\n"
        f"{cible}"
        f"TEXTE :\n{material[:4000]}\n\n"
        'Réponds en JSON STRICT et rien d\'autre : '
        '{"start": "AAAA-MM-JJ" ou "", "end": "AAAA-MM-JJ" ou "", "found": true|false}'
    )
    try:
        msg = client.messages.create(
            model=model, max_tokens=150,
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:
        # PLAFOND API ≠ échec de fiche (2026-08-04). « Jamais bloquant » est la bonne
        # promesse pour une page illisible, la mauvaise pour un plafond de dépense : tous
        # les appels suivants échoueront pareil, et surtout rendre 'llm_none' ferait
        # écrire un verdict horodaté en base — la fiche serait parquée DATE_COOLDOWN_DAYS
        # pour un problème de facturation. 313 occurrences dans le journal du 08/07, une
        # par fiche, chacune consommant son cooldown à tort. On REMONTE, la boucle décide.
        from utils.api_limite import PlafondAPI, est_plafond
        if est_plafond(exc):
            raise PlafondAPI(str(exc)) from exc
        log.warning("Datation LLM échouée : %s", exc)
        return ("", "", "llm_none")
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text").strip()
    # MESURÉ (2026-08-11) : ce poste n'était pas compté du tout. Franck, 2026-08-10 :
    # « je consomme beaucoup trop de token API pour le résultat médiocre » — on ne peut
    # ni le lui confirmer ni le lui infirmer tant que la moitié des appels sont
    # invisibles. Voir scripts/audit_couts.py pour la répartition par poste.
    from utils import usage
    usage.record_message(model, msg, label="datation")
    blob = raw[raw.find("{"):raw.rfind("}") + 1] if "{" in raw else ""
    try:
        data = json.loads(blob or raw)
    except (ValueError, TypeError):
        return ("", "", "llm_none")
    if not data.get("found"):
        return ("", "", "llm_none")
    s, e = (data.get("start") or "").strip(), (data.get("end") or "").strip()
    # Validation stricte : on n'accepte que des dates ISO réelles.
    s = s if (re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) and _iso(*map(int, s.split("-")))) else ""
    e = e if (re.fullmatch(r"\d{4}-\d{2}-\d{2}", e) and _iso(*map(int, e.split("-")))) else ""
    if s and e:
        return (min(s, e), max(s, e), "llm")
    if s or e:
        return (s, e or s, "llm") if s else ("", e, "llm")
    return ("", "", "llm_none")


# Délai avant de re-tenter une fiche restée NON DATABLE. Même convention et même valeur
# par défaut que WEB_COOLDOWN_DAYS (scraper_events), VENUE_COOLDOWN_DAYS (venues) et
# ENRICH_RETRY_DAYS (enrich) — quatre délais différents pour la même idée seraient un
# piège de réglage.
DATE_COOLDOWN_DAYS = int(os.getenv("DATE_COOLDOWN_DAYS",
                                   os.getenv("WEB_COOLDOWN_DAYS", "7")))
# Nombre d'échecs après lequel on cesse de re-tenter TANT QUE LA MATIÈRE NE CHANGE PAS.
# Trois, parce qu'un échec peut venir d'une page momentanément injoignable ou d'un
# plafond API, deux peuvent être une coïncidence — trois sur trois semaines, non.
DATE_MAX_TENTATIVES = int(os.getenv("DATE_MAX_TENTATIVES", "3"))


def _empreinte_matiere(ev: dict) -> str:
    """Résumé stable de ce sur quoi la datation a travaillé. Si ce résumé change, un
    nouvel essai peut légitimement donner un AUTRE résultat — c'est ce qui autorise à
    rouvrir. S'il ne change pas, re-tenter, c'est repayer le même échec (CLAUDE.md,
    règle 3 : « écrire pourquoi le prochain passage donnerait un AUTRE résultat »)."""
    import hashlib
    brut = "|".join(str(ev.get(c) or "") for c in ("title", "description", "url_source"))
    return hashlib.sha1(brut.encode("utf-8", "replace")).hexdigest()[:16]


def _ensure_colonnes_tentatives(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
    for col, decl in (("date_tentatives", "INTEGER DEFAULT 0"), ("date_matiere", "TEXT")):
        if col not in cols:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
    conn.commit()


def _rearme_matiere_changee(conn: sqlite3.Connection) -> int:
    """Remet à zéro le compteur des fiches dont la matière a changé depuis le dernier
    échec. C'EST LE ROUVREUR : il ne dépend d'aucune commande ni d'aucun humain. Une page
    mise à jour, une description réparée, un doublon fusionné qui apporte du texte — et la
    fiche redevient candidate d'elle-même, dès le lendemain."""
    lignes = conn.execute(
        "SELECT id, title, description, url_source, date_matiere FROM events_raw "
        "WHERE COALESCE(date_tentatives,0) >= ? AND COALESCE(date_event_start,'')='' "
        "  AND statut != 'merged'", (DATE_MAX_TENTATIVES,)).fetchall()
    rouverts = [r["id"] for r in lignes
                if r["date_matiere"] and _empreinte_matiere(dict(r)) != r["date_matiere"]]
    if rouverts:
        ph = ",".join("?" * len(rouverts))
        conn.execute(f"UPDATE events_raw SET date_tentatives=0, date_source='none' "
                     f"WHERE id IN ({ph})", rouverts)
        conn.commit()
        log.info("Ré-ouverture : %d fiche(s) dont la matière a changé depuis leur dernier "
                 "échec de datation — elles repassent : %s", len(rouverts),
                 " ".join(str(i) for i in rouverts[:12]))
    return len(rouverts)


def ensure_columns(conn: sqlite3.Connection) -> None:
    # `date_checked_at` (ajoutée le 2026-08-03) : DATE de la dernière tentative, là où
    # `date_source` dit son RÉSULTAT. Sans elle, un ré-armement automatique re-tenterait
    # toutes les fiches non datables à CHAQUE run — donc re-paierait tous les jours la
    # passe LLM pour les mêmes échecs.
    for col, decl in (("date_event_start", "TEXT"),
                      ("date_event_end", "TEXT"),
                      ("date_source", "TEXT"),
                      ("date_checked_at", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Datation des événements (texte + page).")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Ne pas aller lire les pages (parsing texte seulement).")
    parser.add_argument("--fetch-cap", type=int, default=FETCH_CAP,
                        help="Nombre max de pages à télécharger sur ce run.")
    parser.add_argument("--no-llm", action="store_true",
                        help="Ne pas utiliser la datation LLM de dernier recours.")
    parser.add_argument("--llm-cap", type=int, default=DATES_LLM_CAP,
                        help="Nombre max d'événements datés par LLM sur ce run.")
    parser.add_argument("--no-republish", action="store_true",
                        help="Ne PAS repousser vers WordPress les traductions déjà en "
                             "ligne dont les dates viennent d'être réalignées (passe 4). "
                             "Par défaut on les repousse : une date corrigée en base mais "
                             "pas sur le site reste fausse pour le visiteur.")
    parser.add_argument("--republish-cap", type=int,
                        default=int(os.getenv("DATES_REPUBLISH_CAP", "30")),
                        help="Nombre max de fiches repoussées par run (passe 4).")
    parser.add_argument("--retry", action="store_true",
                        help="Ré-armer les événements déjà marqués « non-datables » "
                             "(nodate/llm_none) pour les re-tenter — utile après une "
                             "amélioration du fetch. Ne touche pas ceux qui ont une date.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    ensure_columns(conn)
    # Canal 3 (docs/EVENEMENTS_ANNULES.md) : mêmes colonnes, même migration que le
    # canal 2 — pas de schéma parallèle. `scripts.dedupe` ne dépend pas de dates.py,
    # aucun cycle d'import.
    from scripts.dedupe import ensure_annulation_columns
    from utils.annulation import load_annulation_filter
    ensure_annulation_columns(conn)
    annulation_re = load_annulation_filter()

    # ⚠️ CE RÉ-ARMEMENT EST DEVENU AUTOMATIQUE LE 2026-08-03, comme celui de venues.py le
    # même jour. La sortie de l'impasse existait, mais elle exigeait qu'un humain tape
    # `--retry` en ayant deviné qu'il fallait le faire — et personne ne tape une commande
    # dont il ignore l'existence. Un garde-fou qui dépend d'un geste manuel n'est pas un
    # garde-fou, c'est une note.
    # ENJEU PLUS LOURD QUE POUR LE LIEU : sans `date_event_start`, une fiche ne peut pas
    # être publiée du tout — la porte de publish_batch_as refuse la création (garde-fou du
    # 2026-08-02, après la création de WP#6959 sans date ni image). Une fiche non datable
    # bloquée à vie est une fiche perdue, pas une fiche imparfaite.
    if args.retry:
        n = conn.execute(
            "UPDATE events_raw SET date_source='none' "
            "WHERE date_source IN ('nodate','llm_none') "
            "  AND COALESCE(date_event_start,'')='' AND statut != 'merged'").rowcount
        conn.commit()
        log.info("Retry : %d événement(s) non-datables ré-armés pour re-tentative "
                 "(délai ignoré, --retry)", n)
    else:
        # ⚠️ LE RÉ-ARMEMENT NE DOIT PAS ÊTRE PERPÉTUEL (2026-08-11). Le correctif
        # ci-dessus a supprimé un cul-de-sac, il en a créé un autre à l'envers : une fiche
        # dont la MATIÈRE ne contient pas la date est re-tentée tous les sept jours,
        # indéfiniment, et échoue à chaque fois. Mesuré ce jour-là : 79 fiches sur 95
        # incomplètes, toutes dans ce cycle.
        #
        # VÉRIFIÉ, pas supposé : la page de « Per Olivia » (Teatro Stabile di Torino,
        # fiche 2374) a été récupérée à la main. Elle ne contient AUCUNE date — ni en
        # texte, ni en JSON-LD, ni en méta. Le spectacle appartient à la « Stagione
        # 2026-2027 » et ses dates vivent dans la billetterie (vivaticket), pas sur la
        # page. Aucun modèle, aucun nombre de tentatives ne fera apparaître ce qui n'y
        # est pas. D'autres fiches n'ont même pas d'URL : leur `url_source` est
        # « gmail:<id>#<n> », un item extrait d'un courriel.
        #
        # On plafonne donc les re-tentatives — mais SANS refabriquer un cul-de-sac
        # (règle 3), grâce à DEUX rouvreurs qui ne dépendent d'aucun geste humain :
        #   • la MATIÈRE CHANGE — le résumé de titre+description+url est comparé à celui
        #     de la dernière tentative. Une page mise à jour, une description réparée, une
        #     fusion de doublon : le compteur repart à zéro et la fiche se retente. C'est
        #     le seul événement qui rende un nouvel essai capable de donner autre chose ;
        #   • `--retry` reste là pour forcer la main.
        # Et le nombre de fiches ainsi garées est ANNONCÉ à chaque run (règle 6), pas
        # laissé à découvrir dans six semaines.
        _ensure_colonnes_tentatives(conn)
        _rearme_matiere_changee(conn)
        n = conn.execute(
            "UPDATE events_raw SET date_source='none' "
            "WHERE date_source IN ('nodate','llm_none') "
            "  AND COALESCE(date_event_start,'')='' AND statut != 'merged' "
            "  AND COALESCE(date_tentatives,0) < ? "
            # NULL = tentative antérieure à cette colonne : traitée comme ancienne, sinon
            # les fiches bloquées AVANT ce correctif ne sortiraient jamais — c'est-à-dire
            # précisément celles pour lesquelles il est écrit.
            "  AND (date_checked_at IS NULL "
            "       OR date_checked_at < datetime('now', ?))",
            (DATE_MAX_TENTATIVES, f"-{DATE_COOLDOWN_DAYS} days")).rowcount
        conn.commit()
        if n:
            log.info("Ré-armement automatique : %d fiche(s) non datées re-tentée(s) "
                     "(dernier essai il y a plus de %d jours)", n, DATE_COOLDOWN_DAYS)
        garees = conn.execute(
            "SELECT COUNT(*) FROM events_raw WHERE date_source IN ('nodate','llm_none') "
            "AND COALESCE(date_event_start,'')='' AND statut != 'merged' "
            "AND COALESCE(date_tentatives,0) >= ?", (DATE_MAX_TENTATIVES,)).fetchone()[0]
        if garees:
            log.warning("%d fiche(s) ne sont plus re-tentées : %d essais sans résultat, "
                        "leur source ne publie pas la date. Elles repartiront TOUTES "
                        "SEULES si leur matière change ; sinon elles relèvent d'une "
                        "décision (récurrent ? hors catalogue ?) — les lister : "
                        ".venv/bin/python -m scripts.audit_incomplets --detail date",
                        garees, DATE_MAX_TENTATIVES)

    # --- Passe 1 : texte (titre + description), gratuit et instantané ---
    # ⚠️ TRADUCTIONS EXCLUES (translation_of) — bug corrigé le 2026-08-02. Une fiche
    # traduite reçoit ses dates PAR COPIE de son original (scripts/translate_events.py),
    # et c'est la seule source valable. Mais son INSERT ne renseigne pas `date_source`,
    # donc elle retombait dans cette passe, qui re-parsait ses dates depuis son titre et
    # sa description… TRADUITS EN ITALIEN, avec un parseur écrit pour le français :
    # l'échec ÉCRASAIT la date correcte (18 traductions sans date), et les rares succès
    # produisaient une date FAUSSE (Jazz Art : 2 mois d'écart avec l'original ; Matisse :
    # 1 mois). Même défense que scripts/enrich.py, qui exclut déjà les traductions pour
    # une raison analogue (il écrivait un article français par-dessus).
    #
    # ELLE NE PASSAIT QU'UNE FOIS PAR FICHE, ET C'ÉTAIT LE DÉFAUT (2026-08-11, Franck :
    # « on a toujours trop de tâches »). La sélection portait sur `date_source` vide :
    # dès le premier échec, la colonne passait à 'none' et cette passe ne regardait plus
    # JAMAIS la fiche. Or elle est gratuite et instantanée — il n'y avait aucune raison
    # de ne pas la rejouer. Entre-temps la matière change : `dedupe` fusionne une fiche
    # mieux titrée, `enrich` écrit un `article_title` qui, lui, porte la date, le parseur
    # lui-même s'améliore. Mesuré sur les titres de la file « À compléter » du 11/08, le
    # parseur d'aujourd'hui lit sans hésiter « les 8 et 9 août », « du 11 au 29 août »,
    # « jusqu'au 20 septembre », « Du 3 au 6 décembre » — sur des fiches affichées
    # « date ? » depuis des semaines.
    #
    # Et c'est un cercle vicieux, pas seulement une occasion manquée : sans date, une
    # fiche ne peut pas être classée « passée » (règle 5 — une date manquante n'est PAS
    # un événement terminé), donc elle ne quitte aucune file. Le Tour de France Femmes,
    # fini le 9 août, occupait encore l'écran le 11 pour cette seule raison.
    #
    # On lit maintenant AUSSI `article_title` : il est écrit par le modèle, mais il est
    # déjà publié sur le site, donc y lire une date n'ajoute aucun risque — et il est
    # souvent bien plus explicite que le titre brut du flux. La provenance est distinguée
    # (`parsed_article`) pour qu'un doute futur puisse être levé sans tout re-tester.
    rows = conn.execute(
        "SELECT id, title, description, article_title, date_event_end, date_source "
        "FROM events_raw "
        "WHERE COALESCE(date_event_start,'') = '' AND statut != 'merged' "
        "  AND COALESCE(translation_of,0) = 0"
    ).fetchall()
    log.info("Passe texte : %d événement(s) sans date de début à relire", len(rows))
    parsed = parsed_article = fin_seule = 0
    for r in rows:
        s, e, src = parse_dates(f"{r['title']}\n{r['description'] or ''}")
        titre_art = (r["article_title"] or "") if "article_title" in r.keys() else ""
        if src != "parsed" and titre_art.strip():
            s2, e2, src2 = parse_dates(titre_art)
            if src2 == "parsed":
                s, e, src = s2, e2, "parsed_article"
        # ON N'EFFACE JAMAIS, ET ON NE RÉÉCRIT PAS CE QU'ON SAIT DÉJÀ. Une fiche peut
        # n'avoir qu'une date de FIN (« jusqu'au 20 septembre ») : la toute première
        # version réécrivait les deux colonnes à chaque passage, ce qui aurait effacé
        # cette fin dès l'échec suivant. Chaque champ n'est donc écrit que s'il APPORTE
        # quelque chose que la fiche n'a pas.
        neuf = {}
        if src.startswith("parsed"):
            if s:
                neuf["date_event_start"] = s
            if e and not (r["date_event_end"] or "").strip():
                neuf["date_event_end"] = e
        if neuf:
            champs = ", ".join(f"{c}=?" for c in neuf) + ", date_source=?"
            conn.execute(
                f"UPDATE events_raw SET {champs}, date_checked_at=datetime('now') "
                "WHERE id=?", (*neuf.values(), src, r["id"]))
            # DEUX COMPTEURS, PARCE QU'ILS NE COMPTENT PAS LA MÊME CHOSE (règle 6, et
            # c'est ma troisième récidive de la journée). La version d'avant annonçait
            # « 64 datés par le texte » alors que le nombre de fiches sans date de début
            # ne bougeait que de dix : les 54 autres n'avaient gagné qu'une date de FIN
            # (« jusqu'au 20 septembre » ne dit pas quand ça commence). Elles restent donc
            # incomplètes, et le chiffre laissait croire l'inverse. Pire : elles étaient
            # ré-écrites à l'identique à chaque run, et recomptées à chaque fois.
            if "date_event_start" in neuf:
                parsed += 1
                parsed_article += (src == "parsed_article")
            else:
                fin_seule += 1
        elif not (r["date_source"] or "").strip():
            # Première rencontre sans résultat : on pose 'none' pour que la passe 2
            # (lecture de la page) la prenne en charge. Les suivantes ne touchent à rien.
            conn.execute("UPDATE events_raw SET date_source='none', "
                         "date_checked_at=datetime('now') WHERE id=?", (r["id"],))
    conn.commit()
    # Recompté en base (règle 6) : ce qui compte n'est pas le nombre de parsings réussis,
    # c'est le nombre de fiches qui ont VRAIMENT une date de début maintenant.
    restant = conn.execute(
        "SELECT COUNT(*) FROM events_raw WHERE COALESCE(date_event_start,'')='' "
        "AND statut != 'merged' AND COALESCE(translation_of,0)=0").fetchone()[0]
    log.info("Passe texte : %d fiche(s) ont GAGNÉ une date de début (dont %d par le titre "
             "d'article), %d n'ont gagné qu'une date de fin (« jusqu'au… », elles restent "
             "incomplètes) — %d fiche(s) restent sans date de début",
             parsed, parsed_article, fin_seule, restant)

    # --- Passe 2 : page de l'événement (JSON-LD/<time>), pour les restants ---
    from_page = 0
    if not args.no_fetch:
        todo = conn.execute(
            "SELECT id, title, url_source, wp_post_id_as, annulation_detectee_at "
            "FROM events_raw "
            "WHERE date_source = 'none' AND statut != 'merged' "
            "  AND COALESCE(translation_of,0) = 0 "     # cf. passe 1 : dates copiées, jamais re-dérivées
            "  AND url_source NOT LIKE 'gmail:%' AND url_source NOT LIKE '%news.google.com%' "
            "LIMIT ?", (args.fetch_cap,)).fetchall()
        log.info("Passe page : %d page(s) à lire (cap %d)", len(todo), args.fetch_cap)
        for r in todo:
            capture: dict = {}
            s, e, src = fetch_event_dates(r["url_source"], _capture=capture)
            # Canal 3 : la page vient d'être RÉELLEMENT téléchargée (capture non vide)
            # — on cherche un marqueur d'annulation dessus, QUEL QUE SOIT le résultat
            # de la datation (`s`/`e`/`src`) : le signal est un ajout, jamais un blocage.
            if capture.get("text"):
                signale_annulation_page(conn, dict(r), capture["text"], annulation_re,
                                        source="page (dates.py, passe JSON-LD)")
            # 'page' = trouvé ; 'nodate' = lu mais rien (ne sera plus re-fetché).
            conn.execute(
                "UPDATE events_raw SET date_event_start=?, date_event_end=?, date_source=?, date_checked_at=datetime('now') WHERE id=?",
                (s, e, src, r["id"]))
            if src == "page":
                from_page += 1
            conn.commit()
        log.info("Passe page : %d daté(s) via la page", from_page)

    # --- Passe 3 : datation LLM (dernier recours) pour les non-datés restants ---
    from_llm = 0
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if DATES_LLM and not args.no_llm and api_key:
        todo = conn.execute(
            "SELECT id, title, description, url_source, lieu, ville, wp_post_id_as, "
            "  annulation_detectee_at FROM events_raw "
            "WHERE date_source IN ('none', 'nodate') AND statut != 'merged' "
            "  AND COALESCE(translation_of,0) = 0 "     # cf. passe 1 : dates copiées, jamais re-dérivées
            "  AND url_source NOT LIKE 'gmail:%' AND url_source NOT LIKE '%news.google.com%' "
            "LIMIT ?", (args.llm_cap,)).fetchall()
        log.info("Passe LLM : %d événement(s) à dater (modèle %s, cap %d)",
                 len(todo), DATES_LLM_MODEL, args.llm_cap)
        if todo:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
            ref = date.today()
            from utils.api_limite import PlafondAPI
            for r in todo:
                # La page porte la vraie date ; à défaut, le titre + la description.
                page_text = fetch_page_text(r["url_source"], title=r["title"] or "")
                material = page_text or f"{r['title']}\n{r['description'] or ''}"
                # Canal 3 : uniquement sur du texte VENANT DE LA PAGE (page_text non
                # vide) — jamais sur le repli titre+description, qui ne relit rien.
                if page_text:
                    signale_annulation_page(conn, dict(r), page_text, annulation_re,
                                            source="page (dates.py, passe LLM)")
                ctx = ", ".join(x for x in (r["lieu"], r["ville"]) if x)
                try:
                    s, e, src = llm_dates(material, ref, client, DATES_LLM_MODEL,
                                          title=r["title"] or "", context=ctx)
                except PlafondAPI as exc:
                    # UNE ligne, un ARRÊT, RIEN d'écrit pour les fiches restantes : elles
                    # n'ont pas été jugées, leur tour revient quand le plafond est levé.
                    log.error("PLAFOND API atteint — passe LLM interrompue, %d fiche(s) "
                              "non tentée(s), aucun verdict écrit pour elles : %s",
                              len(todo) - todo.index(r), exc)
                    break
                conn.execute(
                    "UPDATE events_raw SET date_event_start=?, date_event_end=?, date_source=?, date_checked_at=datetime('now') WHERE id=?",
                    (s, e, src, r["id"]))
                # Compteur d'échecs + empreinte de la matière jugée : c'est le couple qui
                # permet de plafonner les re-tentatives SANS créer d'impasse — si la
                # matière change, _rearme_matiere_changee remet le compteur à zéro.
                # Un SUCCÈS remet tout à zéro : la fiche n'a plus rien à demander.
                if src == "llm":
                    from_llm += 1
                    conn.execute(
                        "UPDATE events_raw SET date_tentatives=0, date_matiere=NULL "
                        "WHERE id=?", (r["id"],))
                else:
                    conn.execute(
                        "UPDATE events_raw SET date_tentatives=COALESCE(date_tentatives,0)+1, "
                        "date_matiere=? WHERE id=?", (_empreinte_matiere(dict(r)), r["id"]))
                conn.commit()
            log.info("Passe LLM : %d daté(s) par le LLM", from_llm)
    elif DATES_LLM and not args.no_llm and not api_key:
        log.info("Passe LLM ignorée : ANTHROPIC_API_KEY absente.")

    # --- Passe 4 : traductions — COPIE des dates de l'original (jamais de parsing) ---
    # Les trois passes ci-dessus excluent les traductions, sans quoi elles re-parsent un
    # texte italien avec un parseur français. Mais l'exclusion seule les laisserait
    # DÉFINITIVEMENT sans date dans un cas bien réel : `scripts/link_translations_as.py`
    # pose `translation_of` sur la fiche secondaire d'une paire Polylang dont LES DEUX
    # côtés ont été scrapés indépendamment — cette fiche-là n'a jamais reçu de copie de
    # dates, et plus aucune passe n'avait le droit de la dater. Sans agenda, elle
    # disparaissait des filtres par période.
    # Une traduction n'a AUCUNE donnée factuelle propre : la seule opération légitime est
    # la copie depuis l'original. On copie donc quand la traduction n'a pas de date, ET on
    # RÉALIGNE quand les deux divergent (une divergence ne peut venir que d'une corruption
    # — c'est exactement le dommage constaté en ligne le 2026-08-01).
    _WHERE_DESALIGNEES = (
        "WHERE COALESCE(translation_of,0) <> 0 AND statut != 'merged' "
        "  AND EXISTS (SELECT 1 FROM events_raw o WHERE o.id = events_raw.translation_of "
        "              AND COALESCE(o.date_event_start,'') <> '' "
        "              AND (COALESCE(events_raw.date_event_start,'') <> "
        "                   COALESCE(o.date_event_start,'') "
        "                OR COALESCE(events_raw.date_event_end,'') <> "
        "                   COALESCE(o.date_event_end,'')))")
    # Ids relevés AVANT la correction : après l'UPDATE, ces fiches ne sont plus
    # désalignées, donc plus repérables. Celles DÉJÀ EN LIGNE devront être repoussées.
    #
    # ⚠️ CES CINQ CONDITIONS SUPPLÉMENTAIRES NE SONT PAS DÉCORATIVES. La republication
    # se fait par `publish_main(["--ids", …])`, et `--ids` DÉSACTIVE toute la sélection
    # de publish_batch_as (cf. son _select : ni « à venir », ni `duplicate_of IS NULL`,
    # ni porte qualité). Tout ce que ce SQL laisse passer part EN LIGNE, depuis un cron
    # de 8h45, sans humain. Relecture du 2026-08-02, cinq cas prouvés sur fixture :
    #   • une traduction CORBEILLÉE exprès repartait (rien n'excluait wp_deleted_at) ;
    #   • un événement DÉJÀ PASSÉ repartait ;
    #   • une fiche marquée `duplicate_of` repartait ;
    #   • un original devenu `merged` par le dedupe de 8h30 — quinze minutes plus tôt —
    #     servait quand même de référence : la garde `statut != 'merged'` ne portait que
    #     sur la traduction, jamais sur `o.` ;
    #   • un CYCLE (A.translation_of=B et B.translation_of=A) faisait repartir LES DEUX
    #     côtés, le gagnant étant décidé par l'ordre des rowid. `repair_translation_cycles`
    #     atteste que des cycles subsistent en base, et aucun cron ne le lance.
    # `COALESCE(o.translation_of,0)=0` ferme le cas du cycle en exigeant que l'original
    # soit une VRAIE fiche source, pas elle-même une traduction.
    a_repousser = [r["id"] for r in conn.execute(
        f"SELECT id FROM events_raw {_WHERE_DESALIGNEES} "
        f"  AND COALESCE(wp_post_id_as,0) > 0 "
        f"  AND COALESCE(wp_deleted_at,'') = '' "
        f"  AND duplicate_of IS NULL "
        f"  AND COALESCE(date_event_end, date_event_start, '') >= date('now') "
        f"  AND EXISTS (SELECT 1 FROM events_raw o2 WHERE o2.id = events_raw.translation_of "
        f"              AND o2.statut != 'merged' AND COALESCE(o2.translation_of,0) = 0)"
    ).fetchall()]

    copied = conn.execute(
        "UPDATE events_raw SET date_event_start = (SELECT o.date_event_start FROM events_raw o "
        "                                          WHERE o.id = events_raw.translation_of), "
        "                     date_event_end   = (SELECT o.date_event_end   FROM events_raw o "
        "                                          WHERE o.id = events_raw.translation_of), "
        "                     date_source = 'copie-traduction' "
        "WHERE COALESCE(translation_of,0) <> 0 AND statut != 'merged' "
        "  AND EXISTS (SELECT 1 FROM events_raw o WHERE o.id = events_raw.translation_of "
        "              AND COALESCE(o.date_event_start,'') <> '' "
        "              AND (COALESCE(events_raw.date_event_start,'') <> "
        "                   COALESCE(o.date_event_start,'') "
        "                OR COALESCE(events_raw.date_event_end,'') <> "
        "                   COALESCE(o.date_event_end,'')))").rowcount
    conn.commit()
    if copied:
        log.info("Passe traductions : %d fiche(s) réalignée(s) sur les dates de leur original", copied)

    # REPUBLICATION AUTOMATIQUE — corriger la date en base ne change RIEN sur le site :
    # WordPress/TEC garde la date fausse tant que la fiche n'est pas repoussée. Laisser
    # ce dernier pas à faire à la main, c'est garantir qu'il ne sera pas fait et que la
    # date fausse restera en ligne — exactement ce qu'on cherche à supprimer. `--skip-media`
    # : seules les méta changent, la photo en ligne est déjà la bonne, inutile de
    # remartéler la médiathèque. Le lot est plafonné et l'échec ne casse pas la datation
    # (les dates, elles, sont déjà corrigées en base).
    if a_repousser and not args.no_republish:
        lot = a_repousser[:args.republish_cap]
        if not lot:
            # --republish-cap 0 : `publish_main(["--ids"])` sans valeur fait sortir
            # argparse en SystemExit(2), que le except Exception ci-dessous NE RATTRAPE
            # PAS (SystemExit dérive de BaseException) — la datation entière mourait sur
            # un réglage anodin. On traite 0 comme « ne republie rien », ce qu'il veut dire.
            log.info("Passe traductions : --republish-cap 0, %d fiche(s) non repoussée(s) : %s",
                     len(a_repousser), a_repousser)
            a_repousser = []
        log.info("Passe traductions : %d fiche(s) EN LIGNE à repousser (dates fausses "
                 "affichées) — republication sans média", len(lot))
        try:
            from scripts.publish_batch_as import main as publish_main
            publish_main(["--ids", *[str(i) for i in lot], "--skip-media"])
            reste = len(a_repousser) - len(lot)
            if reste:
                log.warning("Passe traductions : %d fiche(s) au-delà du plafond "
                            "(--republish-cap %d), repoussées au prochain run",
                            reste, args.republish_cap)
        except Exception as exc:  # noqa: BLE001 — la datation reste acquise
            log.error("Passe traductions : republication échouée (%s) — les dates sont "
                      "corrigées en base, le site les verra au prochain run", exc)
    elif a_repousser:
        log.info("Passe traductions : %d fiche(s) en ligne à repousser (--no-republish, "
                 "rien envoyé) : %s", len(a_repousser), a_repousser)

    total_dated = conn.execute(
        "SELECT COUNT(*) n FROM events_raw "
        "WHERE date_source IN ('parsed','page','llm','copie-traduction') "
        "AND statut != 'merged'").fetchone()["n"]
    undated = conn.execute(
        "SELECT COUNT(*) n FROM events_raw WHERE COALESCE(date_event_start,'')='' "
        "AND COALESCE(date_event_end,'')='' AND statut != 'merged'").fetchone()["n"]
    conn.close()
    log.info("=== Datation : +%d texte +%d page +%d LLM ce run · %d datés au total, %d sans date ===",
             parsed, from_page, from_llm, total_dated, undated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
