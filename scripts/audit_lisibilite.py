#!/usr/bin/env python3
"""Quels articles dépassent les seuils de lisibilité de Yoast (phrases longues, passif) ?

LECTURE SEULE, SIGNALEMENT. Même forme que scripts/audit_temps_recit : seuls les
événements ENCORE DEVANT NOUS sont du travail (règle 5) ; les terminés sont comptés,
pas listés. Et pour chaque fiche signalée, l'audit MONTRE les phrases en cause : « un
défaut de forme ne se voit pas dans le code, il se voit dans les résultats » — c'est en
lisant la liste qu'on saura si le détecteur a raison.

Pourquoi un audit et pas un portillon : mesuré le 2026-09-09 sur 143 fiches publiées,
92 % dépassent le seuil de phrases longues. Un refus à l'enrichissement se déclencherait
sur presque tout et doublerait le coût LLM ; la règle, elle, est déjà dans le prompt. La
consigne a été resserrée le même jour (scripts/enrich.py, scripts/translate_events.py) :
cet audit est ce qui dira, dans deux semaines, si elle a fait bouger la médiane — un
prompt modifié est une HYPOTHÈSE tant qu'on ne l'a pas remesurée.

  .venv/bin/python -m scripts.audit_lisibilite            # devant nous, 15 pires
  .venv/bin/python -m scripts.audit_lisibilite --tout     # aussi les terminés
  .venv/bin/python -m scripts.audit_lisibilite --cap 40
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import lisibilite as lis

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tout", action="store_true", help="lister aussi les terminés")
    ap.add_argument("--cap", type=int, default=15, help="fiches listées au plus (les pires)")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    today = date.today().isoformat()

    devant, passes, sans_matiere = [], [], 0
    for r in conn.execute(
            "SELECT id, article_title, title, article_md, date_event_start, date_event_end, "
            "recurring, wp_post_id_as FROM events_raw "
            "WHERE COALESCE(article_md,'') <> '' AND statut NOT IN ('merged','rejected') "
            "AND COALESCE(wp_post_id_as,0) > 0"):
        m = lis.mesurer(r["article_md"])
        if m["phrases"] < 3:
            sans_matiere += 1
            continue
        fin = (r["date_event_end"] or r["date_event_start"] or "").strip()
        a_venir = bool(r["recurring"]) or not fin or fin >= today
        (devant if a_venir else passes).append((dict(r), m))
    conn.close()

    def hors_seuil(m):
        return m["pc_longues"] > lis.YOAST_MAX_LONGUES or m["pc_passif"] > lis.YOAST_MAX_PASSIF

    dv_hors = [x for x in devant if hors_seuil(x[1])]
    print(f"═══ Lisibilité des fiches EN LIGNE et DEVANT NOUS : {len(dv_hors)} sur {len(devant)} "
          f"hors seuil Yoast ═══")
    if sans_matiere:
        print(f"({sans_matiere} fiche(s) sans assez de phrases pour mesurer — ni bonnes ni mauvaises)")
    if devant:
        med_l = statistics.median(m["pc_longues"] for _, m in devant)
        med_p = statistics.median(m["pc_passif"] for _, m in devant)
        med_m = statistics.median(m["mots_par_phrase"] for _, m in devant)
        print(f"Médianes : {med_l:.0f} % de phrases > {lis.SEUIL_MOTS_LONGUE} mots (Yoast ≤ "
              f"{lis.YOAST_MAX_LONGUES:.0f} %) · {med_p:.0f} % de passif (Yoast ≤ "
              f"{lis.YOAST_MAX_PASSIF:.0f} %) · {med_m:.0f} mots par phrase")
    print("⚠️  SIGNALEMENT, pas verdict : lis les phrases. Un « est portée par deux "
          "commissaires » est un passif légitime de journaliste.\n")
    pires = sorted(dv_hors, key=lambda x: -(x[1]["pc_longues"] + x[1]["pc_passif"]))[:args.cap]
    for r, m in pires:
        titre = (r["article_title"] or r["title"] or "")[:60]
        print(f"  [{r['id']:>5}] WP#{r['wp_post_id_as']:<6} {m['pc_longues']:3.0f} % longues · "
              f"{m['pc_passif']:3.0f} % passif · {titre}")
        for p in sorted(m["longues"], key=lambda p: -len(p.split()))[:1]:
            print(f"          ↳ [{len(p.split())} mots] « {p[:110]}… »")
        for p, marque in m["passives"][:1]:
            print(f"          ↳ [passif : {marque}] « {p[:100]}… »")
    if len(dv_hors) > len(pires):
        print(f"  … et {len(dv_hors) - len(pires)} autre(s) (--cap pour en voir plus)")

    ps_hors = [x for x in passes if hors_seuil(x[1])]
    print(f"\n{len(ps_hors)} sur {len(passes)} fiche(s) TERMINÉES sont hors seuil : comptées, "
          f"pas mises en file (règle 5). --tout pour les voir.")
    if args.tout:
        for r, m in ps_hors:
            print(f"  [{r['id']:>5}] {r['date_event_end'] or r['date_event_start']} "
                  f"{(r['article_title'] or r['title'] or '')[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
