#!/usr/bin/env python3
"""Orchestre EN UN SEUL CRON HEBDO tout le nettoyage RÉVERSIBLE et DÉTERMINISTE du
catalogue — pour que Franck n'ait plus à lancer chaque script de nettoyage à la main.

Chaque étape ci-dessous répond aux deux critères qui la rendent sûre à automatiser :
  1. RÉVERSIBLE — corbeille WordPress (jamais suppression définitive) ou statut →
     'rejected' (une re-classification, pas une perte de donnée). AUCUN `--hard` ici.
  2. DÉTERMINISTE — règles fixes (regex, dates, domaines listés), zéro jugement LLM
     ambigu. Les scripts qui font appel à un LLM pour DÉCIDER (pas juste détecter) sont
     volontairement absents de cette liste.

Étapes (dans cet ordre — les purges de bruit d'abord, pour ne pas polluer les audits
plus fins qui suivent) :
  1. purge_out_of_zone   --apply           (hors zone / passés, statut→rejected)
  2. purge_past          --execute         (retenus devenus passés, statut→rejected)
  3. purge_uncompletable --execute         (radar/sans-page incomplétables, statut→rejected)
  4. discard_uncompletable --apply         (même famille, critère complémentaire)
  5. audit_non_events    --apply           (articles de presse publiés à tort → corbeille)
  6. cleanup_as_dupes    --execute         (doublons NÉS dans WordPress → corbeille)
  7. audit_bad_sources                     (lecture seule + republication auto des fiches
                                             concernées — republier ne fait que renettoyer
                                             le texte déjà en base, zéro coût LLM)
  8. image_audit                           (LLM vision, borné --limit — son propre digest
                                             Slack existe déjà, on ne le double pas)

Un seul digest Slack consolidé à la fin (sauf image_audit, qui envoie le sien).

Usage (cron) :
    .venv/bin/python -m scripts.weekly_audits
"""
from __future__ import annotations
import contextlib
import io
import logging
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import slack
from utils import pipeline_status

log = get_logger("weekly_audits")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _run_captured(fn, argv, logger_name: str | None = None) -> tuple[int, str]:
    """Exécute `fn(argv)` en capturant à la fois print() et le logger nommé (les scripts
    de ce dépôt utilisent l'un OU l'autre selon leur âge) — pour extraire un résumé sans
    reparser logs/*.log après coup."""
    buf = io.StringIO()
    handler = None
    if logger_name:
        handler = logging.StreamHandler(buf)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger(logger_name).addHandler(handler)
    try:
        with contextlib.redirect_stdout(buf):
            rc = fn(argv) or 0
    except Exception as exc:  # noqa: BLE001 — une étape en échec ne doit pas arrêter les autres
        log.error("Étape en échec (%s) : %s", logger_name or fn, exc)
        rc = 1
    finally:
        if handler:
            logging.getLogger(logger_name).removeHandler(handler)
    return rc, buf.getvalue()


def _tail(text: str, n: int = 3) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return " / ".join(lines[-n:]) if lines else "(rien à signaler)"


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    sections: list[str] = []

    from scripts.purge_out_of_zone import main as purge_zone_main
    rc, out = _run_captured(purge_zone_main, ["--apply"], "purge_zone")
    sections.append(f"• Hors zone / passés (purge_out_of_zone) : {_tail(out)}")

    from scripts.purge_past import main as purge_past_main
    rc, out = _run_captured(purge_past_main, ["--execute"], "purge_past")
    sections.append(f"• Retenus devenus passés (purge_past) : {_tail(out)}")

    from scripts.purge_uncompletable import main as purge_unc_main
    rc, out = _run_captured(purge_unc_main, ["--execute"], "purge_uncompletable")
    sections.append(f"• Incomplétables radar/sans-page (purge_uncompletable) : {_tail(out)}")

    from scripts.discard_uncompletable import main as discard_unc_main
    rc, out = _run_captured(discard_unc_main, ["--apply"])  # print(), pas de logger nommé
    sections.append(f"• Incomplétables (discard_uncompletable) : {_tail(out)}")

    from scripts.audit_non_events import main as audit_ne_main
    rc, out = _run_captured(audit_ne_main, ["--apply"], "audit-non-events")
    sections.append(f"• Articles de presse publiés à tort (audit_non_events) : {_tail(out)}")

    from scripts.cleanup_as_dupes import main as cleanup_dupes_main
    rc, out = _run_captured(cleanup_dupes_main, ["--execute"], "cleanup_as_dupes")
    sections.append(f"• Doublons nés dans WordPress (cleanup_as_dupes) : {_tail(out)}")

    # audit_bad_sources : lecture seule par nature. On republie nous-mêmes les fiches
    # concernées (zéro coût LLM — build_post relit enrich_data et re-filtre les sources).
    from scripts.audit_bad_sources import _scan as scan_bad_sources
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, wp_post_id_as, url_officiel, url_source, enrich_data "
        "FROM events_raw WHERE enrich_data IS NOT NULL AND enrich_data != ''").fetchall()]
    conn.close()
    flagged = scan_bad_sources(rows)
    republish_ids = [f["id"] for f in flagged if f.get("wp_post_id_as")]
    if republish_ids:
        from scripts.publish_batch_as import main as publish_main
        publish_main(["--ids", *[str(i) for i in republish_ids]])
        sections.append(f"• Sources non institutionnelles (audit_bad_sources) : "
                        f"{len(flagged)} fiche(s) repérée(s), {len(republish_ids)} republiée(s)")
    else:
        sections.append("• Sources non institutionnelles (audit_bad_sources) : rien à signaler")

    # image_audit : coût LLM (vision) réel — borné, et il envoie DÉJÀ son propre digest
    # Slack détaillé (liens vers le back-office) : pas la peine de le dupliquer ici.
    from scripts.image_audit import main as image_audit_main
    image_audit_main(["--limit", "100"])
    sections.append("• Audit visuel (image_audit) : digest Slack séparé")

    msg = "🧹 *Nettoyage hebdomadaire* :\n" + "\n".join(sections)
    slack.notify(msg)
    pipeline_status.record_run("weekly_audits", ok=len(sections), summary=msg[:1900])
    log.info("=== Nettoyage hebdomadaire terminé ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
