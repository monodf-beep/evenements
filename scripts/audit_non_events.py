#!/usr/bin/env python3
"""Repère (et, sur --apply, retire) les ARTICLES DE PRESSE publiés par erreur comme
événements sur l'Agenda — logistique « où se garer », comptes-rendus « le conseil s'est
réuni », portraits « caravane publicitaire »… (cf. utils.eventness).

Ces fiches ont été notées haut par le LLM (il s'accroche au gros mot-clé) AVANT le
pré-filtre déterministe ajouté à l'évaluateur. Elles polluent l'agenda, et comme on
traduit les hauts scores, elles ont parfois une JUMELLE dans l'autre langue → on propage
le retrait aux traductions liées.

Retrait = mise à la CORBEILLE WordPress (réversible, via cs/v1/trash) + statut='rejected'
en base + effacement de wp_post_id_as. RIEN n'est supprimé définitivement.

SÛR : dry-run par défaut. --apply pour agir. N'appelle AUCUNE API LLM.

Usage (VPS) :
    .venv/bin/python -m scripts.audit_non_events            # liste (dry-run)
    .venv/bin/python -m scripts.audit_non_events --apply    # corbeille + rejette
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.eventness import non_event_reason
from scripts.scraper_events import init_db
from scripts.cleanup_as_trash import trash_one

log = get_logger("audit-non-events")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _flagged(rows: list[dict]) -> dict[int, str]:
    """id → raison, pour les fiches non-événement + leurs jumelles/originaux liés."""
    by_id = {r["id"]: r for r in rows}
    flags: dict[int, str] = {}
    for r in rows:                                       # 1. par leur propre texte
        reason = non_event_reason(r.get("title", ""), r.get("description", ""))
        if reason:
            flags[r["id"]] = reason
    for r in rows:                                       # 2. traduction d'un signalé
        tof = r.get("translation_of") or 0
        if tof in flags and r["id"] not in flags:
            flags[r["id"]] = flags[tof] + " (traduction liée)"
    for rid in list(flags):                              # 3. original d'un signalé
        tof = by_id[rid].get("translation_of") or 0
        if tof and tof in by_id and tof not in flags:
            flags[tof] = flags[rid].replace(" (traduction liée)", "") + " (original lié)"
    return flags


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Repère/retire les articles de presse publiés à tort.")
    parser.add_argument("--apply", action="store_true", help="Exécute (sinon dry-run).")
    parser.add_argument("--cap", type=int, default=0, help="Limite le nombre traité (0 = tout).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, description, translation_of, wp_post_id_as, translated_lang "
        "FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0").fetchall()]
    flags = _flagged(rows)
    by_id = {r["id"]: r for r in rows}
    targets = sorted(flags)
    if args.cap:
        targets = targets[:args.cap]

    log.info("%d fiche(s) publiée(s) · %d non-événement(s) repéré(s)%s",
             len(rows), len(flags), " (cap %d)" % args.cap if args.cap else "")
    for rid in targets:
        r = by_id[rid]
        log.info("  WP#%s [%s] %s — « %s »", r["wp_post_id_as"], rid, flags[rid],
                 (r.get("title") or "")[:55])

    if not targets:
        log.info("Rien à retirer. 👍")
        conn.close()
        return 0
    if not args.apply:
        log.info("=== DRY-RUN : %d à mettre à la corbeille. Relance avec --apply. ===", len(targets))
        conn.close()
        return 0

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    if not (wp_url and auth[0] and auth[1]):
        log.error("WP_AS_URL/USER/APP_PASSWORD manquants — impossible d'agir.")
        conn.close()
        return 2

    ok = fail = 0
    for rid in targets:
        r = by_id[rid]
        wp_id = int(r["wp_post_id_as"])
        if trash_one(wp_url, auth, wp_id):
            conn.execute("UPDATE events_raw SET statut='rejected', wp_post_id_as=NULL, "
                         "published_as_date=NULL, llm_justification=? WHERE id=?",
                         ("Retiré : article de presse, pas un événement (%s)." % flags[rid], rid))
            conn.commit()
            ok += 1
            log.info("  WP#%s → corbeille, fiche %s rejetée.", wp_id, rid)
        else:
            fail += 1
            log.warning("  WP#%s : mise à la corbeille échouée (fiche %s laissée).", wp_id, rid)

    log.info("=== Terminé : %d à la corbeille, %d échec(s). ===", ok, fail)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
