#!/usr/bin/env python3
"""AUDIT (LECTURE SEULE) — combien de fiches DÉJÀ PUBLIÉES sont sous le plancher de
substance (utils/substance.py, portillon posé le 2026-08-05 après le refus AdSense).

Le portillon dans scripts/publish_batch_as.py ne bloque que les CRÉATIONS : une fiche
maigre déjà en ligne continue de s'afficher telle quelle (bloquer sa republication ne
la retirerait pas du site, ça y figerait une version plus ancienne). Le commit qui l'a
posé (1d50aac) le dit noir sur blanc : « Ne règle pas les 59 fiches déjà en ligne :
elles demandent un enrichissement ou une dépublication, décision par décision. » Ce
script est cette liste — pour ne plus les découvrir une par une en furetant dans
WordPress (cf. le cas Saint-Ours/WP#2174, trouvé ainsi le 2026-08-06).

CE SCRIPT N'ÉCRIT RIEN. La base est ouverte en lecture seule (`mode=ro`). Ne fait
aucun appel réseau : `build_post` est pure (elle lit le dictionnaire, ne télécharge
rien), donc mesurer 300+ fiches ne coûte ni LLM ni HTTP.

Deux paniers, pour la même raison que le portillon lui-même :
  1. SOUS LE PLANCHER (< 120 mots, PUBLISH_MIN_MOTS) — le cas indéfendable, à traiter
     en priorité : enrichir (scripts.enrich <id>) ou dépublier (trash_by_ids).
  2. BANDE MAIGRE (120-250 mots) — publiable, mais maigre : à surveiller, pas urgent.

Pour aider à choisir enrichir vs dépublier : `jamais enrichie` (article_title vide)
signale une fiche qui n'a JAMAIS eu de vrai article — la réparation naturelle est de
l'enrichir. Une fiche qui a UN article mais reste sous le plancher a un problème plus
profond (rédaction trop courte malgré la matière) — vérifier la matière avant de
relancer scripts.enrich pour rien.

Usage sur le VPS :
    cd /root/evenements && .venv/bin/python -m scripts.audit_substance_published
    cd /root/evenements && .venv/bin/python -m scripts.audit_substance_published --ids
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import substance  # noqa: E402
from scripts.publisher import build_post  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _connect_ro(path: Path) -> sqlite3.Connection:
    """Connexion STRICTEMENT en lecture (URI `mode=ro`) : garantie par SQLite lui-même,
    pas par la discipline du code — ce script tourne sur la base de production."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit LECTURE SEULE des fiches PUBLIÉES sous le plancher de substance.")
    parser.add_argument("--ids", action="store_true",
                        help="Lister les ids/titres, pas seulement les compteurs.")
    parser.add_argument("--limit", type=int, default=80,
                        help="Nombre de lignes détaillées par panier (défaut 80).")
    args = parser.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n"
              f"(data/ est hors dépôt Git — lancer ce script sur le VPS.)")
        return 1

    conn = _connect_ro(DB_PATH)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL").fetchall()]
    conn.close()

    plancher = substance.plancher()
    sous_plancher, bande_maigre = [], []
    for ev in rows:
        n = substance.mots_publies(ev, build_post)
        if n < plancher:
            sous_plancher.append((ev, n))
        elif n < substance.BANDE_MAIGRE:
            bande_maigre.append((ev, n))
    sous_plancher.sort(key=lambda t: t[1])  # les plus maigres d'abord

    jamais_enrichies = sum(1 for ev, _ in sous_plancher if not (ev.get("article_title") or "").strip())

    print("=" * 78)
    print("AUDIT « substance publiée » — lecture seule, rien n'a été modifié")
    print("=" * 78)
    print(f"Base                                     : {DB_PATH}")
    print(f"Fiches publiées (wp_post_id_as)          : {len(rows)}")
    print(f"Plancher (PUBLISH_MIN_MOTS)               : {plancher} mots")
    print()
    print(f"1. SOUS LE PLANCHER (< {plancher} mots)          : {len(sous_plancher)}"
          + (f"  ({100 * len(sous_plancher) / len(rows):.1f} % du site)" if rows else ""))
    print(f"   · dont jamais enrichies (article_title vide) : {jamais_enrichies}")
    print(f"2. BANDE MAIGRE ({plancher}-{substance.BANDE_MAIGRE} mots), publiable mais maigre : {len(bande_maigre)}")
    print()

    if args.ids:
        def _dump(titre: str, lot: list[tuple[dict, int]]) -> None:
            print(f"--- {titre} ({len(lot)}) ---")
            for ev, n in lot[:args.limit]:
                wp = f"WP#{ev['wp_post_id_as']}"
                enrichie = "" if (ev.get("article_title") or "").strip() else " · JAMAIS ENRICHIE"
                print(f"  [{ev['id']:>5}] {wp:<10} {n:>4} mot(s){enrichie:<20} "
                      f"{(ev.get('title') or '')[:55]}")
            if len(lot) > args.limit:
                print(f"  … et {len(lot) - args.limit} autre(s)")
            print()
        _dump("SOUS LE PLANCHER, à réparer en priorité", sous_plancher)
        _dump("BANDE MAIGRE (publiable, à surveiller)", bande_maigre)

    if sous_plancher:
        ids = " ".join(str(ev["id"]) for ev, _ in sous_plancher[:50])
        print("RIEN N'A ÉTÉ MODIFIÉ. Deux réparations possibles, décision par décision :")
        print("  • ENRICHIR (la fiche gagnera un vrai article, puis repart au republish) :")
        print(f"      .venv/bin/python -m scripts.enrich {ids}")
        print("      puis : .venv/bin/python -m scripts.publish_batch_as --ids " + ids)
        print("  • DÉPUBLIER (corbeille WordPress, réversible ; dry-run par défaut, "
              "--apply pour agir) :")
        print(f"      .venv/bin/python -m scripts.trash_by_ids {ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
