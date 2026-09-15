#!/usr/bin/env python3
"""AUDIT (LECTURE SEULE) — combien de fiches le verrou « radar = détection seule » touche.

Répond à trois questions distinctes, qu'on confond facilement :

  1. DÉJÀ EN LIGNE — combien de fiches publiées sur Agenda Sabauda viennent d'un
     radar (presse / Google News / guides tiers) SANS qu'aucune page officielle
     n'ait été résolue ? Ce sont les WP#1097 / WP#1105 du monde réel. Le verrou
     de publication ne les retire PAS : il empêche les suivantes. Leur sort est
     une décision explicite de Franck (voir la fin du rapport).
  2. À VENIR — combien de fiches radar non résolues sont en file et auraient été
     publiées au prochain lot ? C'est le flux que le verrou coupe désormais.
  3. FAUX POSITIFS POTENTIELS — combien de fiches radar ont bien été RÉSOLUES vers
     une page officielle ? Celles-là passent, et c'est la preuve que la règle ne
     tue pas le radar : détecter puis remonter à l'officiel reste le trajet normal.

CE SCRIPT N'ÉCRIT RIEN. La base est ouverte en lecture seule (`mode=ro`) : même une
erreur de programmation ici ne peut pas modifier events.db.

Usage sur le VPS :
    cd /root/evenements && .venv/bin/python -m scripts.audit_radar_published
    cd /root/evenements && .venv/bin/python -m scripts.audit_radar_published --ids
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import radar  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _connect_ro(path: Path) -> sqlite3.Connection:
    """Connexion STRICTEMENT en lecture (URI `mode=ro`) : garantie par SQLite lui-même,
    pas par la discipline du code — ce script tourne sur la base de production."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit LECTURE SEULE des fiches d'origine radar (verrou utils/radar.py).")
    parser.add_argument("--ids", action="store_true",
                        help="Lister les ids et titres, pas seulement les compteurs.")
    parser.add_argument("--limit", type=int, default=40,
                        help="Nombre de lignes détaillées par catégorie (défaut 40).")
    args = parser.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n"
              f"(data/ est hors dépôt Git — lancer ce script sur le VPS.)")
        return 1

    conn = _connect_ro(DB_PATH)
    rows = [dict(r) for r in conn.execute("SELECT * FROM events_raw")]
    conn.close()

    total = len(rows)
    radar_rows = [r for r in rows if radar.is_radar(r)]
    by_id = {r["id"]: r for r in rows}

    def anchored(ev: dict) -> bool:
        if radar.official_anchor(ev):
            return True
        parent = by_id.get(ev.get("translation_of") or 0)
        return bool(parent and radar.official_anchor(parent))

    en_ligne = [r for r in radar_rows if (r.get("wp_post_id_as") or 0) > 0]
    en_ligne_ko = [r for r in en_ligne if not anchored(r)]
    en_ligne_ok = [r for r in en_ligne if anchored(r)]

    # File : ce que publish_batch_as aurait pris (mêmes critères que sa sélection).
    file_att = [r for r in radar_rows
                if (r.get("wp_post_id_as") or 0) == 0
                and (r.get("statut") or "") in ("evaluated", "published_cs", "published_sub")
                and not r.get("duplicate_of")
                and (r.get("date_event_start") or "").strip()]
    file_ko = [r for r in file_att if not anchored(r)]
    file_ok = [r for r in file_att if anchored(r)]

    pub_total = sum(1 for r in rows if (r.get("wp_post_id_as") or 0) > 0)

    print("=" * 78)
    print("AUDIT « radar = DÉTECTION seule » — lecture seule, rien n'a été modifié")
    print("=" * 78)
    print(f"Base                                     : {DB_PATH}")
    print(f"Fiches en base                           : {total}")
    print(f"  · d'origine radar                      : {len(radar_rows)}")
    print(f"Fiches publiées sur Agenda Sabauda       : {pub_total}")
    print()
    print("1. DÉJÀ EN LIGNE (le verrou ne les retire PAS)")
    print(f"   · publiées ET d'origine radar         : {len(en_ligne)}")
    print(f"     ↳ SANS page officielle résolue      : {len(en_ligne_ko)}"
          + (f"  ({100 * len(en_ligne_ko) / pub_total:.1f} % du site)" if pub_total else ""))
    print(f"     ↳ avec page officielle résolue      : {len(en_ligne_ok)}  (légitimes)")
    print()
    print("2. À VENIR (ce que le verrou coupe désormais)")
    print(f"   · radar en file de publication        : {len(file_att)}")
    print(f"     ↳ RETENUES par le verrou            : {len(file_ko)}")
    print(f"     ↳ laissées passer (résolues)        : {len(file_ok)}")
    print()

    if args.ids:
        def _dump(titre: str, lot: list[dict]) -> None:
            print(f"--- {titre} ({len(lot)}) ---")
            for r in lot[:args.limit]:
                wp = f"WP#{r['wp_post_id_as']}" if (r.get("wp_post_id_as") or 0) else "—"
                print(f"  id={r['id']:<6} {wp:<10} {(r.get('source_name') or '')[:28]:<28} "
                      f"{(r.get('title') or '')[:60]}")
            if len(lot) > args.limit:
                print(f"  … et {len(lot) - args.limit} autre(s)")
            print()
        _dump("EN LIGNE, radar non résolu", en_ligne_ko)
        _dump("EN FILE, retenues par le verrou", file_ko)
        _dump("EN LIGNE, radar résolu (contre-exemples : la règle les laisse passer)",
              en_ligne_ok)

    if en_ligne_ko:
        ids = " ".join(str(r["id"]) for r in en_ligne_ko[:50])
        print("RIEN N'A ÉTÉ SUPPRIMÉ NI DÉPUBLIÉ. Le rétroactif est une décision explicite :")
        print("  • relire d'abord la liste ci-dessus (--ids) — certaines de ces fiches")
        print("    sont peut-être de vrais événements dont la page officielle n'a jamais")
        print("    été tentée (fiches enrichies avant le suivi url_officiel) ;")
        print("  • une fiche qu'on veut GARDER se répare en la ré-enrichissant (elle")
        print("    gagnera son url_officiel), pas en la republiant telle quelle ;")
        print("  • pour mettre à la CORBEILLE WordPress (réversible, restaurable ;")
        print("    dry-run par défaut, il faut ajouter --apply pour agir) :")
        print(f"      .venv/bin/python -m scripts.trash_by_ids {ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
