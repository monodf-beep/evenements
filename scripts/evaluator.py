#!/usr/bin/env python3
"""Évaluation LLM des événements pending.

SDK anthropic DIRECT — même pattern que synthesize.py de l'Observatoire.
PAS de LiteLLM.
Cron : 0 9 * * * (quotidien 9h, après le scraping de 8h)
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

log = get_logger("evaluator")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
DEFAULT_MODEL = "claude-sonnet-4-6"
BATCH_SIZE = 100

EVAL_PROMPT = """Tu es l'assistant éditorial de Cultura Sabauda, un média culturel
bilingue couvrant Savoie, Piémont, Vallée d'Aoste et Nice.

Évalue si cet événement mérite d'être mis en avant sur la homepage (score 0-10).

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
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return None
        return json.loads(match.group())
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        log.error("Erreur API Anthropic : %s", exc)
        return None
    except (json.JSONDecodeError, IndexError) as exc:
        log.warning("JSON invalide pour '%s' : %s", event.get("title", "")[:50], exc)
        return None


def main() -> int:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY non définie")
        return 1
    model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    pending = conn.execute(
        "SELECT * FROM events_raw WHERE statut = 'pending' LIMIT ?",
        (BATCH_SIZE,)
    ).fetchall()
    log.info("%d événements à évaluer (modèle : %s)", len(pending), model)

    for event in pending:
        ev = dict(event)
        result = evaluate_event(ev, client, model)
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
    raise SystemExit(main())
