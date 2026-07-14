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
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import usage
from utils.images import fetch_og_image
from scripts.scraper_events import init_db

log = get_logger("enrich")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Modèle dédié à l'enrichissement (recherche web + rédaction). Sonnet 5 par défaut :
# bon rapport qualité/prix et compatible avec l'outil de recherche web dynamique.
DEFAULT_MODEL = "claude-sonnet-5"
# Seuil : on n'enrichit que les événements retenus (cf. CHARTE §5, coût maîtrisé).
MIN_SCORE = int(os.getenv("ENRICH_MIN_SCORE", "7"))
# Taille de lot : l'enrichissement (web + rédaction) coûte cher → petit lot.
BATCH_SIZE = int(os.getenv("ENRICH_BATCH", "10"))
# Plafond de recherches web par événement (outil serveur).
MAX_WEB_SEARCHES = int(os.getenv("ENRICH_MAX_SEARCHES", "3"))
# Budget de sortie de l'article JSON.
MAX_TOKENS = int(os.getenv("ENRICH_MAX_TOKENS", "8000"))
# Raisonnement étendu : COÛTEUX et LENT (runs de ~5 min, budget de tokens épuisé avant
# le JSON → stop_reason=max_tokens). Inutile pour « chercher + rédiger en JSON ».
# Désactivé par défaut ; ENRICH_THINKING=1 pour l'activer (articles plus fouillés, plus chers).
USE_THINKING = os.getenv("ENRICH_THINKING", "0").lower() in ("1", "true", "yes", "on")
# Outil de recherche web (serveur Anthropic) : à activer seulement s'il est disponible
# sur la clé. Par défaut OFF — on fournit nous-mêmes la PAGE OFFICIELLE comme matière
# (déterministe, fiable, moins cher). ENRICH_WEB_SEARCH=1 pour l'ajouter en bonus.
USE_WEB_SEARCH = os.getenv("ENRICH_WEB_SEARCH", "0").lower() in ("1", "true", "yes", "on")
_UA = {"User-Agent": "Mozilla/5.0 (compatible; CulturaSabaudaBot/1.0)"}

# Sentinel : échec d'APPEL API. L'événement n'est pas marqué → réenrichi plus tard.
API_ERROR = object()

WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": MAX_WEB_SEARCHES,
}

ENRICH_PROMPT = """Tu es l'agent éditorial de Cultura Sabauda, média culturel bilingue
FR/IT couvrant l'espace alpin occidental : Savoie/Haute-Savoie, Piémont, Vallée d'Aoste,
Nice/Alpes-Maritimes. Registre « Internazionale + Le Monde Diplomatique » : sérieux,
exigeant, evergreen — l'inverse d'un annuaire touristique.

MISSION : RÉDIGE un article prêt à relire à partir de la MATIÈRE fournie ci-dessous
(page officielle de l'événement, dossier de presse, flux). Appuie-toi EN PRIORITÉ sur
la PAGE OFFICIELLE et le DOSSIER DE PRESSE : ce sont tes sources primaires. N'affirme
aucun fait qui ne figure ni dans cette matière ni dans un savoir historique/géographique
solidement établi ; en cas de doute, baisse la confiance.

PRINCIPE DE L'ESCALIER : partir de l'ancrage local concret pour monter vers une question
qui dépasse le territoire (mémoire, transmission, identité alpine, art, langue).

ENRICHISSEMENT (ce que tu vas chercher SELON la nature de l'événement) :
- Lieu (théâtre, musée, château, abbaye…) : histoire/identité, importance patrimoniale.
- Artiste / groupe : origine (local ? de territoires proches ? renommée), genre.
- Conférencier / auteur : qui c'est, pourquoi ça compte.
- Plat / produit (si intérêt culturel local) : origine, tradition, ce qu'il raconte.
- Œuvre / exposition : artiste, période, intérêt.
- Date / récurrence : rendez-vous historique ? édition anniversaire ?

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
  "angle": "<l'escalier : du local à l'universel, une à deux phrases>",
  "infos_pratiques": "<dates, lieu, accès, tarif/gratuité, lien officiel — factuel>",
  "sources": ["<url officielle/libre consultée>", "..."],
  "confiance": "<haute|moyenne|faible>",
  "article": {{
    "titre": "<titre informatif et incarné, pas racoleur>",
    "chapo": "<1-2 phrases : l'essentiel + l'angle>",
    "corps": "<le savoir transmis, le regard ; relie le territoire et au-delà. MARKDOWN structuré pour la lisibilité (Yoast) : si le corps dépasse ~250 mots, découpe-le avec des sous-titres '## ' tous les 2-3 paragraphes ; phrases COURTES (vise <20 mots) ; emploie des mots de liaison (ainsi, en effet, par ailleurs, dès lors) ; mets en GRAS les faits clés (dates, noms propres, lieux, chiffres)>",
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


def fetch_official_page(url: str, timeout: int = 8) -> str:
    """Récupère le TEXTE de la page officielle de l'événement (source primaire, libre).
    Déterministe : le code va chercher la matière, le LLM la rédige. Skip radar/Gmail.
    Ne franchit aucun mur d'accès — lit simplement la page publique."""
    if not url or url.startswith("gmail:") or "news.google.com" in url:
        return ""
    try:
        r = requests.get(url, timeout=timeout, headers=_UA)
        if r.status_code != 200 or not r.text:
            return ""
        doc = r.text
    except Exception:
        return ""
    # Retire scripts/styles/navigation, puis les balises, puis décode les entités.
    doc = re.sub(r"(?is)<(script|style|nav|header|footer|noscript)[^>]*>.*?</\1>", " ", doc)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    doc = htmlmod.unescape(doc)
    return re.sub(r"\s+", " ", doc).strip()[:6000]


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
    rss = re.sub(r"(?s)<[^>]+>", " ", "\n\n---\n\n".join(parts))[:6000]

    press = gather_press_kits(conn, ev)
    if press:
        press = re.sub(r"(?s)<[^>]+>", " ", press)
    page = fetch_official_page(ev.get("url_source", ""))

    sections = []
    if press:
        sections.append(f"[DOSSIER(S) DE PRESSE — source primaire, prioritaire]\n{press}")
    if page:
        sections.append(f"[PAGE OFFICIELLE DE L'ÉVÉNEMENT — récupérée en direct, source primaire]\n{page}")
    if rss:
        sections.append(f"[SIGNAUX FLUX / RADAR]\n{rss}")
    return "\n\n".join(sections) or "(aucune — titre seul)"


def _dates_hint(ev: dict) -> str:
    """Dates réelles de l'événement pour le prompt (préférées à la date brute du flux,
    qui n'est que la date de publication RSS). Permet l'angle « en cours jusqu'au X »."""
    s = (ev.get("date_event_start") or "").strip()
    e = (ev.get("date_event_end") or "").strip()
    if s and e and s != e:
        return f"du {s} au {e} (événement en cours sur cette plage)"
    if s:
        return s
    if e:
        return f"jusqu'au {e} (en cours)"
    return ev.get("date_start") or "à confirmer"


def _final_text(message) -> str:
    """Concatène les blocs texte de la réponse (en ignorant les blocs d'outil web)."""
    out = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            out.append(block.text)
    return "\n".join(out)


def enrich_event(ev: dict, material: str, client: anthropic.Anthropic, model: str):
    """Un appel agentique (recherche web → rédaction). Gère pause_turn + API_ERROR."""
    from utils.voix import voix_block
    prompt = voix_block() + ENRICH_PROMPT.format(
        title=ev.get("title", ""),
        dates=_dates_hint(ev),
        lieu=ev.get("lieu") or ev.get("ville") or "—",
        territoire=ev.get("territoire", ""),
        organisateur=ev.get("organisateur") or ev.get("source_name") or "—",
        categorie=ev.get("llm_categorie") or "—",
        material=material,
    )
    messages = [{"role": "user", "content": prompt}]
    try:
        # Boucle de l'outil serveur : on relance tant que le tour est « en pause ».
        # STREAMING : indispensable ici (recherche web + raisonnement = requêtes longues)
        # — évite les read-timeouts silencieux. On logge chaque tour pour la traçabilité.
        kwargs = dict(model=model, max_tokens=MAX_TOKENS, messages=messages)
        if USE_WEB_SEARCH:
            kwargs["tools"] = [WEB_SEARCH_TOOL]
        if USE_THINKING:
            kwargs["thinking"] = {"type": "adaptive"}
        for turn in range(1, (MAX_WEB_SEARCHES + 4) if USE_WEB_SEARCH else 2):
            log.info("[%d] appel API tour %d… (web=%s, thinking=%s)",
                     ev["id"], turn, USE_WEB_SEARCH, USE_THINKING)
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


def build_article_md(data: dict) -> tuple[str, str]:
    """Assemble (titre, markdown) depuis le JSON de l'agent (déterministe)."""
    art = data.get("article") or {}
    titre = (art.get("titre") or "").strip()
    chapo = (art.get("chapo") or "").strip()
    corps = (art.get("corps") or "").strip()
    encadre = (art.get("encadre") or "").strip()
    sources = [s for s in (data.get("sources") or []) if s]

    md = []
    if titre:
        md.append(f"# {titre}")
    if chapo:
        md.append(f"**{chapo}**")
    if corps:
        md.append(corps)
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


def main(argv: list[str]) -> int:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY non définie")
        return 1
    model = os.getenv("ANTHROPIC_MODEL_ENRICH", DEFAULT_MODEL)
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

    events = select_events(conn, ids, dfrom, dto)
    log.info("ids à traiter : %s", [e["id"] for e in events])
    log.info("%d événement(s) à enrichir (modèle : %s, seuil score ≥ %d)",
             len(events), model, MIN_SCORE)

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
        result = enrich_event(ev, material, client, model)
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
        title, md = build_article_md(result)
        conn.execute("""
        UPDATE events_raw SET
            enrich_status='enriched', enriched_at=datetime('now'), enrich_model=?,
            enrich_data=?, article_title=?, article_md=?
        WHERE id=?
        """, (model, json.dumps(result, ensure_ascii=False), title, md, ev["id"]))
        conn.commit()
        done += 1
        log.info("[%d] enrichi (confiance=%s) | %s", ev["id"],
                 result.get("confiance", "?"), ev.get("title", "")[:60])

    conn.close()
    log.info("=== Enrichissement terminé : %d/%d ===", done, len(events))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
