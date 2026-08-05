#!/usr/bin/env python3
"""Liste les suspicions d'annulation encore NON résolues — et permet de les clore.

« Où se voit le nombre de fiches garées, et qui les rouvre ? » (docs/
ETATS_TERMINAUX.md). scripts.dedupe bloque la fusion et alerte une fois sur Slack
(config/annulation_keywords.txt, utils.annulation) — mais une alerte lue puis
oubliée est exactement l'incident « LES 7 PROCHAINS JOURS : 0 carte » sous une
autre forme. Ce script recompte, à chaque passage, tout ce qui reste en attente.

DEUX ROUVREURS, parce que la fiche VISÉE n'est pas toujours publiée au moment du
signal (le dedupe quotidien tourne SANS --rescan — il compare des fiches encore
'pending' entre elles, donc la plupart des suspicions naissent AVANT publication) :

  • AUTOMATIQUE — la fiche visée ÉTAIT publiée au moment du signal
    (`annulation_visee_etait_publiee`, capturé par scripts.dedupe) ET ne l'est
    plus aujourd'hui (`wp_post_id_as` vidé, par reconcile_wp_deleted ou une
    dépublication manuelle — les deux le vident SANS changer `statut`, vérifié
    dans reconcile_wp_deleted.py) OU son statut est devenu rejected/merged ;
  • MANUEL — dans tous les autres cas (visée jamais publiée au moment du signal :
    sa perte de wp_post_id_as ne prouverait rien, elle n'en avait pas), rien ne
    peut deviner qu'un humain a vérifié : `--resolu <id de la fiche SUSPECTE>`
    efface le signal après coup.

⚠️ Ne PAS regarder le statut de la fiche SUSPECTE (l'article de presse) pour
décider d'une résolution automatique : elle sera de toute façon rejetée par
l'évaluateur le lendemain, que l'annulation soit confirmée ou non — la confondre
avec une résolution fabriquerait une fausse clôture dès le jour suivant.

Rien n'est appliqué sur WordPress ici — ni dépublication, ni bandeau : cf. la
décision du 2026-08-05, alerte seulement, confirmation humaine.

Usage :
    .venv/bin/python -m scripts.audit_annulations                # liste
    .venv/bin/python -m scripts.audit_annulations --resolu 4213   # clôt à la main
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.scraper_events import init_db

log = get_logger("audit-annulations")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Suspicions d'annulation en attente.")
    parser.add_argument("--resolu", type=int, default=None,
                        help="Id de la fiche SUSPECTE (l'article, pas la fiche visée) "
                             "à clore manuellement, une fois vérifiée à la main.")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    if args.resolu is not None:
        row = conn.execute(
            "SELECT annulation_detectee_at FROM events_raw WHERE id=?", (args.resolu,)
        ).fetchone()
        if row is None:
            log.error("Fiche %s introuvable.", args.resolu)
            conn.close()
            return 2
        if not row["annulation_detectee_at"]:
            log.info("Fiche %s : aucune suspicion active, rien à faire.", args.resolu)
            conn.close()
            return 0
        conn.execute(
            "UPDATE events_raw SET annulation_detectee_at=NULL, annulation_source_url=NULL, "
            "annulation_fiche_visee_id=NULL WHERE id=?", (args.resolu,))
        conn.commit()
        log.info("[%s] suspicion clôturée manuellement.", args.resolu)
        conn.close()
        return 0

    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, annulation_source_url, annulation_detectee_at, "
        "annulation_fiche_visee_id, annulation_visee_etait_publiee FROM events_raw "
        "WHERE COALESCE(annulation_detectee_at,'') <> ''"
    ).fetchall()]

    en_attente, resolues_auto = [], 0
    for suspect in rows:
        visee_id = suspect.get("annulation_fiche_visee_id")
        visee = conn.execute(
            "SELECT wp_post_id_as, statut, title FROM events_raw WHERE id=?", (visee_id,)
        ).fetchone() if visee_id else None
        etait_publiee = bool(suspect.get("annulation_visee_etait_publiee"))
        # Résolution AUTOMATIQUE :
        #   1. la fiche visée n'existe plus du tout ;
        #   2. son statut est devenu rejected/merged — plus rien à protéger ;
        #   3. UNIQUEMENT si elle était publiée AU MOMENT DU SIGNAL, la perte de
        #      wp_post_id_as depuis compte aussi (Franck l'a dépubliée). Si elle
        #      n'était PAS publiée à l'époque, l'absence de wp_post_id_as ne prouve
        #      rien — elle n'en avait simplement pas encore.
        resolu = (visee is None
                 or visee["statut"] in ("rejected", "merged")
                 or (etait_publiee and not (visee["wp_post_id_as"] or 0)))
        if resolu:
            resolues_auto += 1
            continue
        en_attente.append((suspect, dict(visee)))

    log.info("%d suspicion(s) au total, %d résolue(s) automatiquement, %d encore EN "
             "ATTENTE.", len(rows), resolues_auto, len(en_attente))
    for suspect, visee in en_attente:
        log.info("  suspect [%s] → fiche visée [%s] « %s » — signal du %s, source : %s",
                 suspect["id"], suspect.get("annulation_fiche_visee_id"),
                 (visee.get("title") or "")[:50],
                 (suspect.get("annulation_detectee_at") or "")[:10],
                 suspect.get("annulation_source_url") or "?")
    if not en_attente:
        log.info("Rien en attente. 👍")
    else:
        log.info("Pour clore une suspicion vérifiée : "
                 "python -m scripts.audit_annulations --resolu <id suspect>")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
