#!/usr/bin/env python3
"""Évaluation LLM des événements pending.

SDK anthropic DIRECT — même pattern que synthesize.py de l'Observatoire.
PAS de LiteLLM.
Cron : 0 9 * * * (quotidien 9h, après le scraping de 8h)
"""
from __future__ import annotations
import anthropic
import argparse
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

log = get_logger("evaluator")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
DEFAULT_MODEL = "claude-sonnet-5"
BATCH_SIZE = 100

# Sentinel : échec d'APPEL API (réseau / statut). L'événement reste 'pending'
# et sera réévalué au prochain run — jamais rejeté à tort pour une panne API.
API_ERROR = object()

EVAL_PROMPT = """Tu es l'assistant éditorial de Cultura Sabauda, un média culturel
bilingue couvrant Savoie, Piémont, Vallée d'Aoste et Nice.

QU'EST-CE QU'UN ÉVÉNEMENT ? (à vérifier AVANT de noter)
Une manifestation CULTURELLE à laquelle le PUBLIC peut ASSISTER, à une DATE à venir
(ou en cours), dans un lieu : exposition, concert, spectacle, conférence, rencontre,
atelier, visite, projection, festival. On y va pour découvrir, apprendre, se cultiver.
Si ce n'est PAS quelque chose auquel on peut assister à une date → ce n'est pas un
événement → score 0.

Évalue ensuite si cet événement mérite d'être mis en avant sur la homepage (score 0-10).

SCORING :
+3 : transmet un savoir rare ou expert (architectural, historique, linguistique,
     gastronomique, scientifique — pas du tout-venant touristique)
+3 : engage un regard original (point de vue, thèse — pas juste divertir)
+3 : connecte le local à une question universelle (principe de l'escalier :
     ancrage territorial → question qui dépasse le territoire)
+1 : bilingue FR/IT ou en langue du territoire (savoyard, piémontais…)

POUR LE THÉÂTRE (CRÉATION VIVANTE) :
- Scène nationale, théâtre historique, salle ≤ 200 places avec création : +fort
- Ex. Teatro Regio Torino, Théâtre Charles Dullin Chambéry, Piccolo Teatro Milano
- Comédie de boulevard en tournée, humour généraliste : score ≤ 2

CATÉGORIES ACCEPTÉES :
CONFÉRENCES & RENCONTRES | EXPOSITIONS & PATRIMOINE |
CRÉATION VIVANTE | ATELIERS & TRANSMISSION | FESTIVALS

EXCLUSIONS AUTOMATIQUES (score = 0) :
- PAS un événement auquel on peut assister (voir définition ci-dessus)
- ACTUALITÉ INSTITUTIONNELLE / ADMINISTRATIVE : réunion de conseil ou de commission,
  délibération, convention/partenariat signé, subvention, nomination, communiqué de
  politique publique, bilan/rétrospective, palmarès ou remise de prix DÉJÀ tenue
- INAUGURATION ou cérémonie DÉJÀ PASSÉE (racontée comme une nouvelle, pas un rendez-vous)
- INFRASTRUCTURE / travaux / voirie / sécurité / mobilité (chantier, passage à niveau,
  totems, pont, ligne, aménagement)
- Événement hors Savoie/Piémont/Vallée d'Aoste/Nice
- Exercice protection civile ou militaire
- Sagre ou fête de village générique sans transmission de savoir
- Grand concert de masse sans ancrage territorial spécifique
- Événement purement commercial (salon, foire commerciale)

Événement à évaluer :
Titre : {title}
Description : {description}
Lieu : {lieu}, {territoire}
Source : {source_name}

Réponds UNIQUEMENT en JSON valide, sans aucun texte avant ou après :
{{"score": <0-10>, "categorie": "<catégorie>", "justification": "<une phrase>", "niveau1_eligible": <true|false>}}"""


def evaluate_event(event: dict, client: anthropic.Anthropic, model: str) -> dict | None:
    prompt = EVAL_PROMPT.format(
        title=event.get("title", ""),
        description=(event.get("description") or "")[:500],
        lieu=event.get("lieu") or event.get("ville") or "",
        territoire=event.get("territoire", ""),
        source_name=event.get("source_name", ""),
    )
    try:
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        usage.record_message(model, message, label="évaluation")
        # Récupère le bloc TEXTE (le modèle peut émettre un bloc de raisonnement en 1er).
        raw = "".join(getattr(b, "text", "") for b in message.content
                      if getattr(b, "type", None) == "text").strip()
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return None
        return json.loads(match.group())
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        usage.note_api_error(exc)
        log.error("Erreur API Anthropic : %s", exc)
        return API_ERROR
    except (json.JSONDecodeError, IndexError) as exc:
        log.warning("JSON invalide pour '%s' : %s", event.get("title", "")[:50], exc)
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Évaluation LLM des événements pending.")
    parser.add_argument("--from", dest="dfrom", default="",
                        help="Ne traiter que les événements chevauchant [from, to] (AAAA-MM-JJ).")
    parser.add_argument("--to", dest="dto", default="")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY non définie")
        return 1
    model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)  # garantit les colonnes de date même sur une base ancienne

    where, qparams = ["statut = 'pending'"], []
    scope = ""
    if args.dfrom and args.dto:
        # Circonscrit à une période de travail : n'évalue (donc ne paie) que les
        # événements qui CHEVAUCHENT la fenêtre. Voir app : « statut pilote le coût ».
        where.append("COALESCE(date_event_start,'') <= ? AND COALESCE(date_event_end,'') >= ?")
        qparams += [args.dto, args.dfrom]
        scope = f" [période {args.dfrom}→{args.dto}]"
    pending = conn.execute(
        f"SELECT * FROM events_raw WHERE {' AND '.join(where)} LIMIT ?",
        (*qparams, BATCH_SIZE)
    ).fetchall()
    log.info("%d événements à évaluer%s (modèle : %s)", len(pending), scope, model)

    for event in pending:
        ev = dict(event)
        result = evaluate_event(ev, client, model)
        if result is API_ERROR:
            # Panne API : on ne touche pas au statut (reste 'pending', réévalué
            # au prochain run). On stoppe le batch : l'API est probablement KO.
            log.warning("[%d] erreur API — laissé en pending, arrêt du batch", ev["id"])
            break
        if result is None:
            conn.execute(
                "UPDATE events_raw SET statut='rejected', llm_score=0 WHERE id=?",
                (ev["id"],)
            )
            continue
        score = result.get("score", 0)
        # Bifurcation selon score
        if score >= 7:
            new_statut = "evaluated"
        elif score >= 4:
            new_statut = "published_sub"
        else:
            new_statut = "rejected"
        conn.execute("""
        UPDATE events_raw SET
            llm_score=?, llm_categorie=?, llm_justification=?,
            llm_model=?, llm_evaluated_at=datetime('now'), statut=?
        WHERE id=?
        """, (
            score,
            result.get("categorie", ""),
            result.get("justification", ""),
            model,
            new_statut,
            ev["id"],
        ))
        log.info("[%d] score=%d statut=%s | %s", ev["id"], score, new_statut,
                 ev.get("title", "")[:60])

    conn.commit()
    conn.close()
    log.info("=== Évaluation terminée ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
