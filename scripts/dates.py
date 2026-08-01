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
from scripts.scraper_events import init_db
from dotenv import load_dotenv

log = get_logger("dates")
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
    Ne devine JAMAIS depuis le texte libre de la page (trop de faux positifs)."""
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
    return ("", "", "")


def fetch_event_dates(url: str) -> tuple[str, str, str]:
    """Télécharge la page et en extrait la date (JSON-LD/<time>). ('','','nodate') si rien."""
    if not url or url.startswith("gmail:") or "news.google.com" in url:
        return ("", "", "nodate")
    r = _robust_get(url)
    if r is None:
        return ("", "", "nodate")
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
    except Exception as exc:  # jamais bloquant
        log.warning("Datation LLM échouée : %s", exc)
        return ("", "", "llm_none")
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text").strip()
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


def ensure_columns(conn: sqlite3.Connection) -> None:
    for col, decl in (("date_event_start", "TEXT"),
                      ("date_event_end", "TEXT"),
                      ("date_source", "TEXT")):
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

    if args.retry:
        n = conn.execute(
            "UPDATE events_raw SET date_source='none' "
            "WHERE date_source IN ('nodate','llm_none') "
            "  AND COALESCE(date_event_start,'')='' AND statut != 'merged'").rowcount
        conn.commit()
        log.info("Retry : %d événement(s) non-datables ré-armés pour re-tentative", n)

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
    rows = conn.execute(
        "SELECT id, title, description FROM events_raw "
        "WHERE (date_source IS NULL OR date_source = '') AND statut != 'merged' "
        "  AND COALESCE(translation_of,0) = 0"
    ).fetchall()
    log.info("Passe texte : %d événement(s) à dater", len(rows))
    parsed = 0
    for r in rows:
        s, e, src = parse_dates(f"{r['title']}\n{r['description'] or ''}")
        conn.execute(
            "UPDATE events_raw SET date_event_start=?, date_event_end=?, date_source=? WHERE id=?",
            (s, e, src, r["id"]))
        if src == "parsed":
            parsed += 1
    conn.commit()
    log.info("Passe texte : %d daté(s) par le texte", parsed)

    # --- Passe 2 : page de l'événement (JSON-LD/<time>), pour les restants ---
    from_page = 0
    if not args.no_fetch:
        todo = conn.execute(
            "SELECT id, url_source FROM events_raw "
            "WHERE date_source = 'none' AND statut != 'merged' "
            "  AND COALESCE(translation_of,0) = 0 "     # cf. passe 1 : dates copiées, jamais re-dérivées
            "  AND url_source NOT LIKE 'gmail:%' AND url_source NOT LIKE '%news.google.com%' "
            "LIMIT ?", (args.fetch_cap,)).fetchall()
        log.info("Passe page : %d page(s) à lire (cap %d)", len(todo), args.fetch_cap)
        for r in todo:
            s, e, src = fetch_event_dates(r["url_source"])
            # 'page' = trouvé ; 'nodate' = lu mais rien (ne sera plus re-fetché).
            conn.execute(
                "UPDATE events_raw SET date_event_start=?, date_event_end=?, date_source=? WHERE id=?",
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
            "SELECT id, title, description, url_source, lieu, ville FROM events_raw "
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
            for r in todo:
                # La page porte la vraie date ; à défaut, le titre + la description.
                material = (fetch_page_text(r["url_source"], title=r["title"] or "")
                            or f"{r['title']}\n{r['description'] or ''}")
                ctx = ", ".join(x for x in (r["lieu"], r["ville"]) if x)
                s, e, src = llm_dates(material, ref, client, DATES_LLM_MODEL,
                                      title=r["title"] or "", context=ctx)
                conn.execute(
                    "UPDATE events_raw SET date_event_start=?, date_event_end=?, date_source=? WHERE id=?",
                    (s, e, src, r["id"]))
                conn.commit()
                if src == "llm":
                    from_llm += 1
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
    a_repousser = [r["id"] for r in conn.execute(
        f"SELECT id FROM events_raw {_WHERE_DESALIGNEES} "
        f"  AND COALESCE(wp_post_id_as,0) > 0").fetchall()]

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
