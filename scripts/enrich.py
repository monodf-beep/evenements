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
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import usage
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
MAX_WEB_SEARCHES = int(os.getenv("ENRICH_MAX_SEARCHES", "5"))

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

MISSION : à partir du signal et de la matière ci-dessous, RECHERCHE le contexte sur le
web puis RÉDIGE un article prêt à relire.

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
Date (brute du flux) : {date_start}
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
    "corps": "<le savoir transmis, le regard ; relie le territoire et au-delà (markdown)>",
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


def gather_material(conn: sqlite3.Connection, ev: dict) -> str:
    """Agrège (déterministe) la matière : dossiers de presse PRIORITAIRES, puis la
    description de l'événement + celle des doublons fusionnés (duplicate_of=ev.id)."""
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
    text = re.sub(r"(?s)<[^>]+>", " ", "\n\n---\n\n".join(parts))[:6000]

    press = gather_press_kits(conn, ev)
    if press:
        press = re.sub(r"(?s)<[^>]+>", " ", press)
        return (f"[DOSSIER(S) DE PRESSE — source primaire, matière prioritaire]\n{press}"
                f"\n\n[AUTRES SIGNAUX (flux/radar)]\n{text or '(aucun)'}")
    return text or "(aucune — titre seul)"


def _final_text(message) -> str:
    """Concatène les blocs texte de la réponse (en ignorant les blocs d'outil web)."""
    out = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            out.append(block.text)
    return "\n".join(out)


def enrich_event(ev: dict, material: str, client: anthropic.Anthropic, model: str):
    """Un appel agentique (recherche web → rédaction). Gère pause_turn + API_ERROR."""
    prompt = ENRICH_PROMPT.format(
        title=ev.get("title", ""),
        date_start=ev.get("date_start") or "—",
        lieu=ev.get("lieu") or ev.get("ville") or "—",
        territoire=ev.get("territoire", ""),
        organisateur=ev.get("organisateur") or ev.get("source_name") or "—",
        categorie=ev.get("llm_categorie") or "—",
        material=material,
    )
    messages = [{"role": "user", "content": prompt}]
    try:
        # Boucle de l'outil serveur : on relance tant que le tour est en pause.
        for _ in range(MAX_WEB_SEARCHES + 3):
            message = client.messages.create(
                model=model,
                # marge pour le raisonnement adaptatif + l'article complet
                max_tokens=4096,
                tools=[WEB_SEARCH_TOOL],
                thinking={"type": "adaptive"},
                messages=messages,
            )
            usage.record_message(model, message, label="enrichissement")
            if message.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": message.content})
                continue
            break
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        usage.note_api_error(exc)
        log.error("Erreur API Anthropic : %s", exc)
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


def select_events(conn: sqlite3.Connection, ids: list[int]) -> list[sqlite3.Row]:
    if ids:
        qmarks = ",".join("?" * len(ids))
        return conn.execute(
            f"SELECT * FROM events_raw WHERE id IN ({qmarks})", ids).fetchall()
    # Événements retenus (≥ seuil), pas encore enrichis. Les doublons 'merged' sont
    # exclus : leur matière est déjà agrégée vers le gagnant.
    return conn.execute(
        "SELECT * FROM events_raw "
        "WHERE statut IN ('evaluated', 'published_sub') "
        "  AND llm_score >= ? "
        "  AND (enrich_status IS NULL OR enrich_status = '') "
        "  AND (duplicate_of IS NULL) "
        "ORDER BY llm_score DESC, scrape_date DESC LIMIT ?",
        (MIN_SCORE, BATCH_SIZE)).fetchall()


def main(argv: list[str]) -> int:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY non définie")
        return 1
    model = os.getenv("ANTHROPIC_MODEL_ENRICH", DEFAULT_MODEL)
    ids = [int(a) for a in argv if a.isdigit()]
    client = anthropic.Anthropic(api_key=api_key)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    events = select_events(conn, ids)
    log.info("%d événement(s) à enrichir (modèle : %s, seuil score ≥ %d)",
             len(events), model, MIN_SCORE)

    done = 0
    for event in events:
        ev = dict(event)
        material = gather_material(conn, ev)
        result = enrich_event(ev, material, client, model)
        if result is API_ERROR:
            log.warning("[%d] erreur API — laissé tel quel, arrêt du lot", ev["id"])
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
