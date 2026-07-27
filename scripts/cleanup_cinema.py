#!/usr/bin/env python3
"""Nettoyage RÉTROACTIF des séances de cinéma déjà retenues/publiées.

La règle éditoriale « garder les festivals cinéma, exclure les séances courantes »
(cf. scripts/evaluator EVAL_PROMPT, PIÈGE CINÉMA) ne s'applique qu'aux NOUVEAUX
événements évalués. Ce script la passe RÉTROACTIVEMENT sur l'existant :

  1. sélectionne les événements de catégorie « Cinéma » retenus/publiés ;
  2. les RE-ÉVALUE avec le prompt courant (une séance de salle repasse à score 0,
     un festival/rétrospective garde son score) ;
  3. séance → statut 'rejected' + mise à la CORBEILLE WordPress (réversible) ;
     festival/rétrospective (score >= seuil) → CONSERVÉ, inchangé.

Sécurité : DRY-RUN par défaut (liste sans rien changer). Il faut --execute pour agir.
Réversible : les fiches partent à la corbeille WP (Événements → Corbeille pour
restaurer) ; en base on repasse statut='rejected' et on efface wp_post_id_as.

Exemples :
  .venv/bin/python3 -m scripts.cleanup_cinema             # dry-run
  .venv/bin/python3 -m scripts.cleanup_cinema --execute
  .venv/bin/python3 -m scripts.cleanup_cinema --cap 20 --execute
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.evaluator import evaluate_event, RETAIN_MIN_SCORE
from scripts.cleanup_as_trash import trash_one

log = get_logger("cleanup_cinema")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Catégorie cinéma telle qu'écrite par l'évaluateur (accentuée) + variante défensive.
_CINEMA = ("Cinéma", "Cinema")
# Statuts « retenus » (évalués et/ou publiés) — on ne touche pas au 'pending'/'rejected'.
_RETAINED = ("evaluated", "published_cs", "published_sub")


def _effective_score(result: dict) -> int:
    """Score effectif après application des gates de l'évaluateur : hors périmètre ou
    non-événement ⇒ 0 ; sinon le score brut. (Miroir de scripts/evaluator.main.)"""
    if not result.get("est_evenement") or result.get("hors_perimetre"):
        return 0
    try:
        return int(result.get("score") or 0)
    except (TypeError, ValueError):
        return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Nettoyage rétroactif des séances de cinéma (corbeille WP, réversible).")
    p.add_argument("--execute", action="store_true", help="Agir réellement (sinon DRY-RUN).")
    p.add_argument("--cap", type=int, default=200, help="Nombre max d'événements à examiner.")
    p.add_argument("--delay", type=float, default=0.6, help="Pause (s) entre deux appels.")
    args = p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY non définie")
        return 1
    from utils import settings as pipeline_settings
    model = os.getenv("ANTHROPIC_MODEL") or pipeline_settings.model()
    client = anthropic.Anthropic(api_key=api_key)
    from utils import score_memory
    calibration = score_memory.calibration_block()

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(_CINEMA))
    st_ph = ",".join("?" * len(_RETAINED))
    rows = conn.execute(
        f"SELECT * FROM events_raw WHERE llm_categorie IN ({placeholders}) "
        f"AND duplicate_of IS NULL AND statut IN ({st_ph}) "
        "ORDER BY COALESCE(date_event_start,'') LIMIT ?",
        (*_CINEMA, *_RETAINED, args.cap)).fetchall()

    mode = "EXÉCUTION" if args.execute else "DRY-RUN (rien ne bouge)"
    log.info("Cinéma retenus à re-juger : %d (modèle %s) — %s", len(rows), model, mode)

    seances, festivals, failed = [], [], 0
    for i, row in enumerate(rows, 1):
        ev = dict(row)
        result = evaluate_event(ev, client, model, calibration)
        if result is None:  # panne API : on ne touche à rien
            failed += 1
            log.warning("[%s] ré-évaluation indisponible (panne API) — ignoré : %s",
                        ev["id"], (ev.get("title") or "")[:50])
            continue
        new_score = _effective_score(result)
        title = (ev.get("title") or "")[:58]
        if new_score < RETAIN_MIN_SCORE:
            seances.append((ev, new_score, result.get("justification", "")))
            print(f"  ✂️  RETIRER  séance  · score {ev.get('llm_score')}→{new_score} · "
                  f"WP#{ev.get('wp_post_id_as') or '—'} · {title}")
        else:
            festivals.append(ev)
            print(f"  ✓  garder   festival · score {ev.get('llm_score')}→{new_score} · {title}")
        if args.delay and i < len(rows):
            time.sleep(args.delay)

    print(f"\n{len(seances)} séance(s) à retirer · {len(festivals)} festival(s) gardé(s)"
          f"{f' · {failed} ignoré(s) (panne API)' if failed else ''}")

    if not args.execute:
        print("\nDRY-RUN : rien n'a changé. Relance avec --execute pour retirer les séances.")
        conn.close()
        return 0

    have_wp = all([wp_url, auth[0], auth[1]])
    if not have_wp:
        log.warning("WP_AS_URL/USER/APP_PASSWORD manquants — dépublication WP impossible, "
                    "on marque quand même 'rejected' en base.")

    trashed = rejected = 0
    for ev, new_score, justif in seances:
        wp_id = ev.get("wp_post_id_as")
        # Corbeille WP (réversible) — force=True car la fiche est publiée ('publish').
        if wp_id and have_wp and trash_one(wp_url, auth, int(wp_id), force=True):
            conn.execute("UPDATE events_raw SET wp_post_id_as=NULL, published_as_date=NULL "
                         "WHERE id=?", (ev["id"],))
            trashed += 1
        conn.execute(
            "UPDATE events_raw SET statut='rejected', llm_score=0, "
            "llm_justification=? WHERE id=?",
            (f"Séance de cinéma courante exclue (nettoyage rétroactif). {justif}"[:400], ev["id"]))
        conn.commit()
        rejected += 1
        log.info("[%s] séance retirée (rejected%s) : %s", ev["id"],
                 ", corbeille WP" if wp_id and have_wp else "", (ev.get("title") or "")[:50])

    conn.close()
    print(f"\n=== Terminé : {rejected} rejetée(s) en base, {trashed} mise(s) à la corbeille WP ===")
    print("Réversible : Événements → Corbeille dans WordPress pour restaurer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
