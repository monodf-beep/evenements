#!/usr/bin/env python3
"""Réparer les fiches PUBLIÉES trop maigres — en lot, borné, et en RECOMPTANT après.

`scripts/audit_substance_published.py` sait les compter (108 sous le plancher au
2026-08-09, dont 99 sans le moindre article). Il ne sait pas les réparer, et le commit
qui a posé le portillon de substance le disait déjà : « elles demandent un enrichissement
ou une dépublication, décision par décision ». Neuf jours plus tard, personne n'a pris
ces décisions une par une — évidemment : il y en a cent huit.

Ce script fait la partie mécanisable : ré-enrichir puis republier, par lots bornés, sur
les seules fiches où ça a une chance d'aboutir. Le reste — dépublier ce qui reste maigre
après réparation — demeure un arbitrage humain, et le script le désigne au lieu de le
faire.

QUI EST REPRIS, ET POURQUOI PAS LES AUTRES
  • en ligne (`wp_post_id_as`) : une fiche maigre INVISIBLE n'abîme rien, elle passera par
    le portillon de publication comme les autres ;
  • encore devant nous (règle 5) : réparer un article dont l'événement a eu lieu ne sert
    personne, et coûterait un appel LLM à ~0,33 $ pièce ;
  • sous le plancher (utils/substance.plancher(), défaut 120 mots) ;
  • pas une traduction : on répare l'ORIGINAL puis on retraduit, jamais l'inverse —
    scripts.enrich écrit en français et écraserait la version italienne.

L'ORDRE COMPTE. Les fiches JAMAIS ENRICHIES passent d'abord : leur réparation est la plus
sûre (il n'y a rien à améliorer, tout à écrire) et la plus visible. Une fiche qui a DÉJÀ
un article et reste sous le plancher a un problème de matière, pas de rédaction — la
relancer produira souvent le même texte court. Le rapport les sépare.

RÈGLE 6 — le nombre de mots est RECOMPTÉ après coup, fiche par fiche. Un run n'annonce
jamais « N réparées » sur la foi de la liste envoyée : il annonce combien ont réellement
franchi le plancher, et nomme celles qui ne l'ont pas franchi.

RÈGLE 4 — dry-run par défaut. Avant un `--apply` de masse :
    .venv/bin/python scripts/backup_db.py

Exemples :
  .venv/bin/python -m scripts.repair_substance                  # simulation
  .venv/bin/python -m scripts.repair_substance --apply --cap 5  # 5 fiches, ~1,7 $
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import substance  # noqa: E402
from utils.logger import get_logger  # noqa: E402
from scripts.publisher import build_post  # noqa: E402

log = get_logger("repair_substance")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Coût observé d'un enrichissement sur les 14 jours précédant le 2026-08-11 (121,13 $
# pour 369 appels). Sert uniquement à ANNONCER la dépense avant de l'engager : personne
# ne devrait lancer un lot sans savoir ce qu'il coûte.
COUT_ENRICH_USD = 0.33


def _candidates(conn, today: str) -> list[dict]:
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE wp_post_id_as IS NOT NULL "
        "AND COALESCE(statut,'') NOT IN ('merged','rejected') AND duplicate_of IS NULL "
        "AND COALESCE(translation_of,0)=0 "
        "AND (COALESCE(recurring,0)=1 "
        "     OR COALESCE(NULLIF(date_event_end,''), NULLIF(date_event_start,''), '9999') >= ?)",
        (today,))]
    plancher = substance.plancher()
    out = []
    for ev in rows:
        n = substance.mots_publies(ev, build_post)
        if n < plancher:
            ev["_mots"] = n
            ev["_jamais"] = not (ev.get("article_title") or "").strip()
            out.append(ev)
    # Jamais enrichies d'abord, puis les plus maigres, puis le meilleur score.
    out.sort(key=lambda e: (not e["_jamais"], e["_mots"], -(e.get("llm_score") or 0)))
    return out


def _mots_de(conn, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    return {r["id"]: substance.mots_publies(dict(r), build_post)
            for r in conn.execute(f"SELECT * FROM events_raw WHERE id IN ({ph})", ids)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Répare les fiches publiées sous le plancher.")
    p.add_argument("--apply", action="store_true", help="Exécute (sinon simulation).")
    p.add_argument("--cap", type=int, default=5,
                   help="Nb max de fiches par run (défaut 5 — un lot se surveille).")
    p.add_argument("--inclure-deja-redigees", action="store_true",
                   help="Reprendre aussi les fiches qui ont DÉJÀ un article (par défaut, "
                        "seules les fiches jamais enrichies sont reprises).")
    args = p.parse_args(argv)

    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    tous = _candidates(conn, today)
    jamais = [e for e in tous if e["_jamais"]]
    redigees = [e for e in tous if not e["_jamais"]]
    plancher = substance.plancher()

    print(f"═══ Fiches EN LIGNE, encore devant nous, sous {plancher} mots ═══\n")
    print(f"  {len(jamais):4} jamais enrichies  — rien à améliorer, tout à écrire")
    print(f"  {len(redigees):4} déjà rédigées    — article court MALGRÉ la matière : "
          f"relancer produira souvent le même texte")
    print(f"  {len(tous):4} au total\n")

    file_ = (tous if args.inclure_deja_redigees else jamais)[:args.cap]
    if not file_:
        print("Rien à réparer dans ce périmètre. 🎉")
        conn.close()
        return 0

    for e in file_:
        print(f"  [{e['id']:>5}] {e['_mots']:3} mots · WP#{e['wp_post_id_as']} · "
              f"{(e.get('article_title') or e.get('title') or '')[:56]}")
    ids = [e["id"] for e in file_]
    print(f"\n{len(ids)} fiche(s) — coût estimé ≈ {len(ids) * COUT_ENRICH_USD:.2f} $ "
          f"(un enrichissement, mesuré à {COUT_ENRICH_USD:.2f} $ pièce).")

    if not args.apply:
        print("\nSimulation — rien n'a été lancé. Ajouter --apply pour exécuter.")
        print("Avant un lot : .venv/bin/python scripts/backup_db.py")
        conn.close()
        return 0

    avant = {e["id"]: e["_mots"] for e in file_}
    conn.close()

    from scripts.enrich import main as enrich_main
    code = enrich_main([str(i) for i in ids])
    log.info("enrich a rendu %s", code)

    # La republication est indispensable : l'article vit en base, le site n'en sait rien
    # tant qu'on ne le lui pousse pas. PAS de --skip-media ici, contrairement au SEO : une
    # fiche jamais enrichie n'a souvent pas d'image non plus, et c'est le même problème.
    from scripts.publish_batch_as import main as publish_main
    publish_main(["--ids", *[str(i) for i in ids]])

    # RÈGLE 6 : on RECOMPTE. La longueur d'une liste envoyée ne prouve rien.
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apres = _mots_de(conn, ids)
    conn.close()
    franchi = [i for i in ids if apres.get(i, 0) >= plancher]
    echoue = [i for i in ids if i not in franchi]

    print(f"\n═══ Résultat RECOMPTÉ en base ═══\n")
    for i in ids:
        fleche = "✅" if i in franchi else "⚠️ "
        print(f"  {fleche} [{i:>5}] {avant.get(i, 0):3} → {apres.get(i, 0):3} mots")
    print(f"\n{len(franchi)}/{len(ids)} au-dessus du plancher.")
    if echoue:
        # Nommer l'échec, pas seulement le compter : ces fiches-là ne se répareront pas
        # toutes seules, et les relancer coûterait le même appel pour le même résultat.
        print(f"\n{len(echoue)} fiche(s) restent sous le plancher malgré l'enrichissement : "
              f"{' '.join(str(i) for i in echoue)}")
        print("La matière disponible ne permet pas d'écrire davantage. Elles relèvent "
              "d'une décision : dépublier (.venv/bin/python -m scripts.trash_by_ids "
              f"{' '.join(str(i) for i in echoue)}) ou les laisser telles quelles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
