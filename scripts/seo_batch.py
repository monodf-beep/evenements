#!/usr/bin/env python3
"""Génération SEO EN LOT (agent) — pour le HAUT DU PANIER seulement.

Lance utils.seo.optimize_seo() sur les événements retenus, datés, à venir et de
score élevé qui n'ont pas encore de SEO (seo_at IS NULL). Stocke seo_* + seo_at.
Ces champs sont ensuite poussés vers Yoast au (re)publish (publish_batch_as).

⚠️ Coût LLM : chaque événement = un appel. À réserver aux événements qui comptent
(le SEO de l'agenda se joue surtout sur les pages hubs, pas sur les fiches de masse).
Borné (--cap), seuil (--min-score, défaut 7), --dry-run.

Exemples :
  .venv/bin/python3 -m scripts.seo_batch --dry-run
  .venv/bin/python3 -m scripts.seo_batch --cap 30            # score >= 7 par défaut
  .venv/bin/python3 -m scripts.seo_batch --min-score 8 --cap 50
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import seo as seo_mod
from utils.api_limite import PlafondAPI, est_plafond

log = get_logger("seo_batch")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _select(conn, args, today: str):
    where = [
        "statut IN ('evaluated','published_cs','published_sub')",
        "duplicate_of IS NULL",
        "COALESCE(date_event_start,'') <> ''",              # daté
        "COALESCE(llm_score,0) >= ?",
        # ⚠️ TRADUCTIONS EXCLUES (ajouté le 2026-08-02, dégât ACTIF découvert en audit).
        # Le prompt de utils/seo.py impose « Produis, EN FRANÇAIS » (l.118). Rien ici ne
        # filtrait `translation_of` : ce cron de 10h30 sélectionnait donc les fiches
        # ITALIENNES (elles héritent du statut, de la date et du score de leur original),
        # leur fabriquait un titre SEO, une méta description, une expression clé et un
        # slug EN FRANÇAIS — puis les REPUBLIAIT (l.127-129), poussant le tout dans Yoast
        # sur une fiche italienne en ligne. Tous les jours, en silence.
        # Ce n'est PAS le correctif définitif : la bonne réponse est un SEO rédigé dans la
        # LANGUE de la fiche (translated_lang), pas une exclusion. Mais toucher au prompt
        # d'un cron qui pousse vers Yoast sans pouvoir vérifier la sortie du LLM, c'est
        # exactement le genre de pari qui a coûté cher. Une fiche IT sans méta SEO est
        # neutre ; une fiche IT avec une méta française est fausse pour le visiteur ET
        # pour Google. On exclut d'abord, on rédigera en italien ensuite.
        "COALESCE(translation_of,0) = 0",
        # ANNULÉ EXCLU (docs/EVENEMENTS_ANNULES.md, « effets de bord » du canal 1) :
        # « ne pas optimiser une annulation ». Générer un title/méta SEO pour une fiche
        # qui ne se déplacera plus n'a aucun public — et ça coûte un appel LLM pour rien.
        "annule_le IS NULL",
    ]
    params: list = [args.min_score]
    if not args.redo:
        where.append("seo_at IS NULL")                      # pas déjà fait
    if not args.include_past:
        where.append("COALESCE(date_event_end, date_event_start) >= ?")
        params.append(today)
    sql = (f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
           f"ORDER BY COALESCE(llm_score,0) DESC, date_event_start ASC LIMIT ?")
    params.append(args.cap)
    return conn.execute(sql, params).fetchall()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Génération SEO en lot (agent).")
    parser.add_argument("--cap", type=int, default=30, help="Nombre max d'événements par run.")
    parser.add_argument("--min-score", type=int, default=7, help="Score minimum (défaut 7).")
    parser.add_argument("--delay", type=float, default=1.0, help="Pause (s) entre deux appels.")
    parser.add_argument("--redo", action="store_true", help="Régénérer même si déjà fait.")
    parser.add_argument("--include-past", action="store_true", help="Inclure les événements passés.")
    parser.add_argument("--dry-run", action="store_true", help="Lister la sélection sans appeler le LLM.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model = (os.getenv("ANTHROPIC_MODEL_SEO") or os.getenv("ANTHROPIC_MODEL_VISUALS")
             or "claude-haiku-4-5")
    today = date.today().isoformat()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = _select(conn, args, today)
    log.info("Sélection : %d événement(s) (cap %d, min-score %d, modèle %s)",
             len(rows), args.cap, args.min_score, model)

    if args.dry_run:
        for r in rows:
            print(f"  [{r['id']}] score={r['llm_score']} · {(r['title'] or '')[:70]}")
        print(f"\n{len(rows)} événement(s) SERAIENT optimisés (dry-run — aucun appel LLM).")
        conn.close()
        return 0

    if not api_key:
        log.error("ANTHROPIC_API_KEY absente — génération SEO impossible.")
        conn.close()
        return 1

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    ok = fail = 0
    plafonne = False
    republish_ids = []  # déjà EN LIGNE : le nouveau SEO doit être repoussé pour être visible
    for i, r in enumerate(rows, 1):
        try:
            result = seo_mod.optimize_seo(dict(r), client, model)
        except Exception as exc:
            # UN PLAFOND N'EST PAS UNE ERREUR DE FICHE (2026-08-05, trouvé en prod : 16
            # erreurs identiques « credit balance is too low », martelées une par fiche
            # en 13 secondes — le même trou que translate_events.py avait avant sa
            # garde du matin même, jamais bouché ici). utils.seo.optimize_seo laisse
            # VOLONTAIREMENT remonter les exceptions API (sa docstring : sa seconde
            # appelante, la route Flask, les gère elle-même) — mais ce lot-ci doit
            # s'ARRÊTER sur un plafond, pas continuer à essayer les 9 fiches suivantes
            # pour rien.
            if est_plafond(exc):
                log.error("PLAFOND API atteint sur la fiche %s — lot arrêté, %d "
                         "fiche(s) non tentée(s) : %s", r["id"], len(rows) - i + 1, exc)
                plafonne = True
                break
            log.warning("SEO échoué id=%s : %s", r["id"], exc)  # jamais bloquant pour une fiche
            result = None
        if result:
            conn.execute(
                "UPDATE events_raw SET seo_title=?, seo_meta=?, seo_answer=?, seo_faq=?, "
                "seo_keyphrase=?, seo_slug=?, seo_tags=?, seo_model=?, seo_at=datetime('now') "
                "WHERE id=?",
                (result["seo_title"], result["seo_meta"], result["seo_answer"],
                 json.dumps(result["seo_faq"], ensure_ascii=False),
                 result["seo_keyphrase"], result["seo_slug"],
                 json.dumps(result["seo_tags"], ensure_ascii=False), model, r["id"]))
            conn.commit()
            ok += 1
            if r["wp_post_id_as"]:
                republish_ids.append(r["id"])
        else:
            fail += 1
        if i % 10 == 0 or i == len(rows):
            log.info("Progression : %d/%d (%d ok, %d échec)", i, len(rows), ok, fail)
        if args.delay and i < len(rows):
            time.sleep(args.delay)

    conn.close()

    # Le SEO stocké en base ne sert à rien tant qu'il n'est pas repoussé (cs-publish.php
    # ne lit `seo_*` qu'au (re)publish) : sans ça, "optimisé" en base mais invisible sur
    # Yoast jusqu'au prochain republish, potentiellement jamais si l'événement est déjà en
    # ligne et ne bouge plus. --skip-media : texte/méta seuls, on ne retouche pas la photo.
    if republish_ids:
        from scripts.publish_batch_as import main as publish_main
        publish_main(["--ids", *[str(i) for i in republish_ids], "--skip-media"])

    from utils import slack
    from utils import pipeline_status
    msg = f"🔍 *SEO quotidien* — {ok} optimisé(s) ({len(republish_ids)} republié(s)), {fail} échec(s)"
    if plafonne:
        msg += "\n🔴 Plafond API atteint — lot arrêté, fiches restantes non tentées."
    slack.notify(msg)
    pipeline_status.record_run("seo_batch", ok=ok, error=fail, summary=msg)
    log.info("=== Lot SEO : %d optimisé(s), %d échec(s), %d republié(s) ===",
             ok, fail, len(republish_ids))
    if plafonne:
        log.error("Le lot s'est arrêté sur un plafond API. Relever le plafond ou "
                  "recharger le crédit (console Anthropic), puis relancer.")
        return 3
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
