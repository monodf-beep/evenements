#!/usr/bin/env python3
"""Écoule le STOCK de fiches d'origine RADAR laissé par la désactivation du tier
(config/sources.txt, 2026-08-05 : « trop de bruit, on garde les sources officielles »).

Couper la collecte (sources.txt) empêche les NOUVELLES fiches radar — celui-ci
nettoie celles qui restaient déjà en base, exactement la même distinction que
`scripts/purge_out_of_zone.py` (hors zone / passés).

DEUX PANIERS, jamais confondus :

  1. PAS ENCORE EN LIGNE, sans page officielle résolue (`utils.radar.official_anchor`
     vide) — le radar a fait son travail (détecter), mais n'a jamais abouti. Ce sont
     ces fiches qui encombrent l'évaluation, les audits, le dashboard : purgeables
     (statut→'rejected', réversible — voir docs/ETATS_TERMINAUX.md, 'rejected' se
     rouvre en 'pending' à la main si besoin). AUCUNE fiche RÉSOLUE n'est touchée :
     un radar qui a bien remonté jusqu'à la page officielle a fait exactement ce
     pour quoi il existe, ce n'est pas du bruit.

  2. DÉJÀ EN LIGNE et sans page officielle résolue — le cas WP#1097/WP#1105 du
     verrou (utils/radar.py). Seulement LISTÉES, jamais touchées ici : une
     dépublication est plus visible qu'un rejet de fiche jamais parue, et
     `scripts.audit_radar_published` existe déjà pour ce diagnostic précis — on ne
     duplique pas sa décision, on pointe vers elle (trash_by_ids, réversible).

Usage :
    .venv/bin/python -m scripts.purge_radar             # aperçu (rien n'est modifié)
    .venv/bin/python -m scripts.purge_radar --apply      # rejette (statut='rejected')
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
from utils import radar

log = get_logger("purge_radar")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

_MOTIF = ("Tier radar désactivé (2026-08-05, config/sources.txt) — aucune page "
          "officielle jamais résolue.")


def _colonnes(conn: sqlite3.Connection) -> set[str]:
    return {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}


def fiches_radar(conn: sqlite3.Connection) -> tuple[list[dict], list[dict]]:
    """(à purger, déjà en ligne) — fiches radar SANS ancre officielle résolue.

    Exclut d'office `rejected` (déjà écarté) et `merged` (absorbé ailleurs, la
    fiche gagnante décide) : ce script ne fait que fermer ce qui traîne encore
    ouvert, jamais rouvrir un état déjà tranché."""
    cols = _colonnes(conn)
    wp_cols = [c for c in ("wp_post_id_as", "wp_post_id_cs") if c in cols]
    sel = ", ".join(
        ["id", "title", "source_type", "source_name", "statut", "territoire",
         "translation_of", "url_officiel", "enrich_data"] + wp_cols)
    rows = [dict(r) for r in conn.execute(
        f"SELECT {sel} FROM events_raw "
        "WHERE statut NOT IN ('rejected', 'merged') AND duplicate_of IS NULL"
    ).fetchall()]
    by_id = {r["id"]: r for r in rows}

    def anchored(ev: dict) -> bool:
        if radar.official_anchor(ev):
            return True
        parent = by_id.get(ev.get("translation_of") or 0)
        return bool(parent and radar.official_anchor(parent))

    cible = [r for r in rows if radar.is_radar(r) and not anchored(r)]
    a_purger, en_ligne = [], []
    for r in cible:
        (en_ligne if any(r.get(c) for c in wp_cols) else a_purger).append(r)
    return a_purger, en_ligne


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Purge du stock radar non résolu (config/sources.txt, tier désactivé).")
    parser.add_argument("--apply", action="store_true",
                        help="Applique (par défaut : aperçu seul, rien n'est modifié).")
    args = parser.parse_args(argv)

    if not DB_PATH.exists():
        log.error("Base introuvable : %s (data/ est hors dépôt Git — lancer sur le VPS).", DB_PATH)
        return 1

    # timeout=30 : incident réel du 2026-08-06 (VPS, --apply) — "database is locked" au
    # tout premier UPDATE, un cron concurrent (le délai par défaut de sqlite3, 5s, était
    # trop court un jeudi matin chargé). SQLite retente tout seul jusqu'à `timeout`
    # avant de lever l'erreur ; les autres scripts d'écriture du dépôt (purge_out_of_
    # zone.py, dedupe.py…) n'en fixent aucun et héritent donc du défaut — celui-ci est
    # plus exposé (146 UPDATE dans le même executemany, donc une fenêtre plus longue).
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    a_purger, en_ligne = fiches_radar(conn)

    print(f"\n{len(a_purger)} fiche(s) radar non résolue(s), pas encore en ligne — "
          "purgeables (statut → 'rejected').")
    for r in a_purger[:60]:
        print(f"  [{r['id']:>5}] {r['territoire'] or '—':<14} {(r['source_name'] or '')[:28]:<28} "
              f"{r['title'][:55]}")
    if len(a_purger) > 60:
        print(f"  … et {len(a_purger) - 60} autres.")

    if en_ligne:
        print(f"\n⚠️  {len(en_ligne)} fiche(s) radar non résolue(s) DÉJÀ EN LIGNE — "
              "listées, JAMAIS modifiées par ce script.")
        for r in en_ligne[:30]:
            wp = f"WP#{r.get('wp_post_id_as')}" if r.get("wp_post_id_as") else \
                 (f"CS#{r.get('wp_post_id_cs')}" if r.get("wp_post_id_cs") else "?")
            print(f"  [{r['id']:>5}] {wp:<10} {(r['source_name'] or '')[:28]:<28} {r['title'][:50]}")
        if len(en_ligne) > 30:
            print(f"  … et {len(en_ligne) - 30} autres.")
        print("  → diagnostic déjà écrit pour ce cas précis (WP#1097/WP#1105) : "
              ".venv/bin/python -m scripts.audit_radar_published --ids")

    if not args.apply:
        print("\nAperçu seul. Relance avec --apply pour rejeter les fiches pas encore en ligne.")
        conn.close()
        return 0

    ids = [r["id"] for r in a_purger]
    if ids:
        conn.executemany(
            "UPDATE events_raw SET statut='rejected', llm_justification=? WHERE id=?",
            [(_MOTIF, i) for i in ids])
        conn.commit()
    conn.close()
    print(f"\n✅ {len(ids)} fiche(s) radar rejetée(s).")
    log.info("Purge radar : %d fiche(s) rejetée(s), %d déjà en ligne laissée(s) intacte(s).",
             len(ids), len(en_ligne))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
