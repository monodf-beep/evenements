#!/usr/bin/env python3
"""Passe de CONFORMITÉ éditoriale rétroactive (charte) sur les articles DÉJÀ publiés.

Relit chaque article enrichi (titre, chapô, corps, encadré, programme stockés dans
`enrich_data.article`) et **corrige UNIQUEMENT ce qui viole la charte** — sans recherche
web, sans réécrire un article conforme :
  - casse : jamais de TOUT EN CAPITALES ni de title case (CHARTE §6) ;
  - pas de superlatifs creux ni de dark pattern (CHARTE §6/§7) ;
  - ton soutenu mais accessible, pas racoleur ;
  - toponymes dans la langue de l'article (§6 bis — ici la version FR).
Les FAITS (dates, programme, lieu, distribution) ne sont jamais modifiés.

Ne touche PAS la version italienne : elle se régénère par `scripts/translate_events.py`
(dont le prompt porte désormais la charte §6 bis). Enchaîner translate APRÈS cette passe.

Cible par défaut = les articles SUR LES HOMEPAGES : publiés (`wp_post_id_as`), enrichis,
à venir. On peut restreindre à des id précis, plafonner (`--cap`), et il faut `--execute`
pour agir (DRY-RUN par défaut). Modèle éco (pas de web/thinking) → coût maîtrisé.

Après correction : mise à jour DB (`enrich_data`, `article_title`, `article_md`) PUIS
re-push WordPress via publisher_as.publish_to_as (met à jour le post existant — §10 :
le site dédié auto-publie les fiches enrichies/relues).

Usage :
    .venv/bin/python3 scripts/conform_articles.py --dry-run          # aperçu (défaut)
    .venv/bin/python3 scripts/conform_articles.py --execute --cap 30 # applique
    .venv/bin/python3 scripts/conform_articles.py 12 15 --execute    # ces id précis
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import usage
from scripts.enrich import build_article_md
from scripts.publisher_as import publish_to_as

log = get_logger("conform-articles")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
MAX_TOKENS = int(os.getenv("CONFORM_MAX_TOKENS", "4000"))

PROMPT = """Tu es le relecteur éditorial de Cultura Sabauda. On te donne un ARTICLE déjà
rédigé (au format JSON). Applique la CHARTE en CORRIGEANT UNIQUEMENT ce qui la viole ;
si une partie est déjà conforme, laisse-la EXACTEMENT telle quelle.

RÈGLES À FAIRE RESPECTER (corrige seulement les manquements) :
- CASSE : jamais de titre/nom/intertitre TOUT EN CAPITALES ni en title case anglais
  (« COREOGRAFIE DEL POSSIBILE » → « Coreografie del Possibile » ; « Les Nuits De La Photo »
  → « Les nuits de la photo »). Casse de phrase : initiale + noms propres. Préserve les
  vrais sigles (FIAF, ONU) et la casse de marque (iMac).
- Pas de SUPERLATIFS CREUX (« incontournable », « magique », « à ne pas manquer »…).
- Aucun DARK PATTERN : fausse urgence/rareté, clickbait, confirmshaming.
- Ton soutenu mais accessible, pas racoleur ; phrases claires.
- Toponymes en FRANÇAIS (version FR) : Turin, Aoste, Nice… ; chaîne ville → province →
  territoire quand elle est présente.

INTERDITS ABSOLUS :
- Ne modifie AUCUN FAIT : dates, horaires, lieu, tarifs, distribution, et surtout le
  PROGRAMME (liste) — recopie-le à l'identique, ligne à ligne.
- N'invente rien, n'ajoute pas d'information, ne raccourcis pas le corps.
- Ne change pas la langue ni la structure (mêmes champs).

ARTICLE (JSON) :
{article_json}

Réponds par un UNIQUE bloc JSON valide, sans rien avant ni après, de la forme :
{{
  "article": {{"titre": "...", "chapo": "...", "corps": "...", "encadre": "...", "programme": ["..."]}},
  "changed": <true si tu as modifié quoi que ce soit, sinon false>,
  "notes": "<ce que tu as corrigé, en une phrase ; '' si rien>"
}}
Ne mets dans "article" que les champs présents en entrée (garde-les tous)."""


def _select(conn: sqlite3.Connection, ids: list[int], cap: int) -> list[dict]:
    if ids:
        qm = ",".join("?" * len(ids))
        rows = conn.execute(f"SELECT * FROM events_raw WHERE id IN ({qm})", ids).fetchall()
        return [dict(r) for r in rows]
    # « Sur les homepages » : publiés sur Agenda Sabauda, enrichis, à venir.
    rows = conn.execute(
        "SELECT * FROM events_raw WHERE wp_post_id_as IS NOT NULL "
        "AND COALESCE(enrich_data,'') <> '' AND duplicate_of IS NULL "
        "AND COALESCE(NULLIF(date_event_end,''), date_event_start) >= date('now') "
        "ORDER BY llm_score DESC, date_event_start ASC LIMIT ?", (cap,)).fetchall()
    return [dict(r) for r in rows]


def _looks_shouty(article: dict) -> bool:
    """Heuristique rapide (gratuite) : un titre/intertitre en grande partie CAPITALES ?
    Sert juste à annoter l'aperçu ; la décision finale revient au LLM."""
    t = (article.get("titre") or "")
    letters = [c for c in t if c.isalpha()]
    up = [c for c in letters if c.isupper()]
    return len(letters) >= 6 and len(up) / len(letters) > 0.7


def conform_one(ev: dict, client: anthropic.Anthropic, model: str) -> dict | None:
    """Renvoie le dict enrich_data corrigé (ou None si rien à faire / échec)."""
    try:
        data = json.loads(ev["enrich_data"])
    except (ValueError, TypeError):
        return None
    article = (data or {}).get("article") or {}
    if not article:
        return None
    prompt = PROMPT.format(article_json=json.dumps(article, ensure_ascii=False, indent=2))
    try:
        msg = client.messages.create(
            model=model, max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}])
        usage.record_message(model, msg, label="conformité")
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        log.error("[%s] erreur API : %s", ev["id"], exc)
        return None
    raw = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        log.warning("[%s] pas de JSON en retour", ev["id"])
        return None
    try:
        out = json.loads(m.group())
    except json.JSONDecodeError:
        log.warning("[%s] JSON invalide", ev["id"])
        return None
    if not out.get("changed"):
        return None
    new_article = out.get("article") or {}
    if not new_article.get("titre") or not new_article.get("corps"):
        log.warning("[%s] réponse incomplète — ignorée (sécurité)", ev["id"])
        return None
    data["article"] = new_article
    data["_conform_notes"] = out.get("notes", "")
    return data


def main(argv: list[str]) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Passe de conformité éditoriale (charte).")
    parser.add_argument("ids", nargs="*", type=int)
    parser.add_argument("--execute", action="store_true", help="Agir (sinon DRY-RUN).")
    parser.add_argument("--cap", type=int, default=30, help="Nb max d'articles traités.")
    args = parser.parse_args(argv)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY absente.")
        return 1
    from utils import settings as pipeline_settings
    # Modèle éco par défaut (relecture ≠ rédaction) : configurable.
    model = os.getenv("ANTHROPIC_MODEL_CONFORM") or os.getenv("ANTHROPIC_MODEL_VISION") \
        or pipeline_settings.model()
    client = anthropic.Anthropic(api_key=api_key, timeout=120.0)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    events = _select(conn, args.ids, args.cap)
    log.info("%d article(s) à relire (%s).", len(events),
             "EXÉCUTION" if args.execute else "DRY-RUN")

    changed = pushed = 0
    for ev in events:
        new_data = conform_one(ev, client, model)
        if not new_data:
            log.info("[%s] conforme — inchangé.", ev["id"])
            continue
        changed += 1
        notes = new_data.get("_conform_notes", "")
        log.info("[%s] À CORRIGER : %s", ev["id"], notes or "(casse/ton)")
        if not args.execute:
            continue
        # Persiste : enrich_data corrigé + titre + markdown régénéré.
        title, md = build_article_md(new_data)
        conn.execute(
            "UPDATE events_raw SET enrich_data=?, article_title=?, article_md=? WHERE id=?",
            (json.dumps(new_data, ensure_ascii=False), title, md, ev["id"]))
        conn.commit()
        # Re-push WordPress (met à jour le post existant via wp_post_id_as).
        ev.update({"enrich_data": json.dumps(new_data, ensure_ascii=False),
                   "article_title": title, "article_md": md})
        post_id, _perma, _img = publish_to_as(ev)
        if post_id:
            pushed += 1
            log.info("[%s] re-poussé sur WordPress (post %s).", ev["id"], post_id)
        else:
            log.warning("[%s] re-push WordPress échoué.", ev["id"])
    conn.close()

    tail = "" if args.execute else " (dry-run : rien touché)"
    log.info("=== Conformité : %d à corriger, %d re-poussé(s) sur %d relu(s)%s ===",
             changed, pushed, len(events), tail)
    log.info("Pense à relancer scripts/translate_events.py pour propager en IT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
