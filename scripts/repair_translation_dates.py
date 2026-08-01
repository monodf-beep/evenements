#!/usr/bin/env python3
"""Répare les DATES des fiches traduites, écrasées par scripts/dates.py.

Cause (corrigée dans dates.py le 2026-08-02, cf. commentaire de la passe 1) : l'INSERT
de scripts/translate_events.py ne renseigne pas `date_source`, si bien que chaque
traduction retombait dans la passe de datation, qui re-parsait ses dates depuis son
titre et sa description TRADUITS EN ITALIEN avec un parseur écrit pour le français.
Résultat : soit la date correcte (copiée de l'original) était écrasée par du vide, soit
un parse « réussi » posait une date FAUSSE (constaté : 2 mois d'écart sur Jazz Art).

Ce script ré-aligne chaque traduction sur son ORIGINAL, seule source valable, et
recopie aussi `date_source` pour que la provenance reste cohérente.

Signale sans y toucher deux anomalies qui demandent une décision humaine :
  - les traductions CIRCULAIRES (A.translation_of = B et B.translation_of = A) ;
  - les originaux eux-mêmes sans date (rien à copier).

SÛR : dry-run par défaut, --apply pour écrire. AUCUN appel API.

Usage (VPS) :
    .venv/bin/python -m scripts.repair_translation_dates            # liste
    .venv/bin/python -m scripts.repair_translation_dates --apply    # répare
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

log = get_logger("repair_translation_dates")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Ré-aligne les dates des traductions sur leur original.")
    parser.add_argument("--apply", action="store_true", help="Écrit (sinon dry-run).")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = [dict(r) for r in conn.execute("""
        SELECT t.id tid, t.title ttitle, t.wp_post_id_as twp,
               t.date_event_start tstart, t.date_event_end tend,
               o.id oid, o.title otitle, o.translation_of o_tof,
               o.date_event_start ostart, o.date_event_end oend, o.date_source osrc
        FROM events_raw t JOIN events_raw o ON o.id = t.translation_of
        WHERE COALESCE(t.translation_of,0) <> 0
        ORDER BY t.id
    """).fetchall()]

    a_reparer, circulaires, sans_source = [], [], []
    for r in rows:
        if (r["o_tof"] or 0) == r["tid"]:          # A -> B et B -> A
            circulaires.append(r)
            continue
        if (r["tstart"] or "") == (r["ostart"] or "") and (r["tend"] or "") == (r["oend"] or ""):
            continue                                # déjà cohérent
        if not (r["ostart"] or "").strip():
            sans_source.append(r)                   # l'original n'a pas de date à donner
            continue
        a_reparer.append(r)

    print(f"\n{len(rows)} traduction(s) examinée(s)\n")

    if a_reparer:
        print(f"--- {len(a_reparer)} à RÉPARER (date de l'original recopiée) ---")
        for r in a_reparer:
            print(f"  [{r['tid']}] WP#{r['twp']} {(r['ttitle'] or '')[:48]}")
            print(f"        {r['tstart'] or '(vide)'} → {r['ostart']}   (original [{r['oid']}])")

    if circulaires:
        print(f"\n--- {len(circulaires)} CIRCULAIRE(S) — non touché(es), décision humaine ---")
        for r in circulaires:
            print(f"  [{r['tid']}] ↔ [{r['oid']}] : {(r['ttitle'] or '')[:44]}")
        print("  (chacune se déclare la traduction de l'autre : impossible de savoir "
              "laquelle est l'originale sans regarder le contenu)")

    if sans_source:
        print(f"\n--- {len(sans_source)} SANS SOURCE — l'original n'a pas de date non plus ---")
        for r in sans_source:
            print(f"  [{r['tid']}] WP#{r['twp']} {(r['ttitle'] or '')[:48]} (original [{r['oid']}])")

    if not args.apply:
        print(f"\n(dry-run : rien écrit — relance avec --apply pour réparer les {len(a_reparer)}.)")
        conn.close()
        return 0

    for r in a_reparer:
        conn.execute(
            "UPDATE events_raw SET date_event_start=?, date_event_end=?, date_source=? WHERE id=?",
            (r["ostart"], r["oend"], r["osrc"], r["tid"]))
    conn.commit()
    conn.close()

    log.info("%d traduction(s) ré-alignée(s) sur leur original.", len(a_reparer))

    # La commande de republication ne doit contenir QUE des fiches DÉJÀ en ligne.
    # `publish_batch_as --ids` ignore les filtres habituels et publie même ce qui ne l'a
    # jamais été : y glisser une fiche sans wp_post_id_as la CRÉERAIT sur le site. Piège
    # vérifié en conditions réelles (une fiche datée de 2024 et un jeu-concours radio
    # étaient dans le lot) — même mécanisme que l'incident --skip-media du 2026-08-01.
    en_ligne = [r for r in a_reparer if r["twp"]]
    jamais_publiees = [r for r in a_reparer if not r["twp"]]

    print(f"\n✅ {len(a_reparer)} réparée(s) en base.")
    if jamais_publiees:
        print(f"\n⚠️  {len(jamais_publiees)} JAMAIS publiée(s) — volontairement EXCLUE(S) de la "
              f"commande ci-dessous (les republier les CRÉERAIT sur le site) :")
        for r in jamais_publiees:
            print(f"     [{r['tid']}] {(r['ttitle'] or '')[:52]}  (date {r['ostart']})")
        print("     À publier seulement après vérification manuelle qu'elles le méritent.")
    if en_ligne:
        ids = " ".join(str(r["tid"]) for r in en_ligne)
        print(f"\nRepublie les {len(en_ligne)} déjà en ligne pour propager la correction :")
        print(f"   .venv/bin/python -m scripts.publish_batch_as --ids {ids} --skip-media")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
