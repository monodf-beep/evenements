#!/usr/bin/env python3
"""Rebranche les traductions dont le lien vers l'original a été perdu.

TROUVÉ PAR L'AGENT QUOTIDIEN, à son premier run réel (2026-08-11, 18h) : « Une traduction
n'hérite pas des dates de son original. 3508 était sans date alors que 198, sa source, est
publiée avec 19/06 → 17/09. Je l'ai comblée à la main ; le trou se rouvrira à la prochaine
traduction. »

Il avait raison sur le symptôme et il ne pouvait pas voir la cause — il n'ouvre pas le
code, c'est sa consigne. La voici.

Une fiche traduite porte DEUX marques de son origine : la colonne `translation_of` et une
adresse synthétique « translated:<id>:<langue> ». `scripts/translate_events.py` pose bien
les deux à l'insertion. Mais certaines fiches n'ont plus que la seconde — et comme TOUS
les garde-fous interrogent la colonne, jamais l'adresse, ces fiches échappent à tout :

  • `scripts/dates.py` passe 4 ne leur recopie pas les dates de l'original ;
  • `scripts/enrich.py` ne les exclut pas, et peut écrire un article FRANÇAIS par-dessus
    une fiche italienne — le bug du 2026-08-02, qui avait justement motivé l'exclusion ;
  • la file « À compléter » du back-office les affiche, alors qu'on ne complète jamais une
    traduction à la main : on répare l'ORIGINAL, puis on retraduit.

C'est ce dernier point qui a servi de preuve : 3508 apparaissait dans une file dont la
requête exige `COALESCE(translation_of,0)=0`. Elle ne pouvait donc y être qu'avec une
colonne vide.

CE QUE FAIT LA RÉPARATION : elle relit l'identifiant dans l'adresse et repose la colonne.
Rien d'inventé — le numéro est écrit dans la fiche depuis sa création.

DEUX REFUS, parce qu'un lien faux serait pire que pas de lien :
  • l'original doit EXISTER et ne pas être lui-même une traduction (sinon on fabrique un
    cycle, et `repair_translation_cycles` atteste qu'il en subsiste en base) ;
  • une fiche ne peut pas être sa propre traduction.

  .venv/bin/python -m scripts.repair_lien_traduction            # simulation
  .venv/bin/python -m scripts.repair_lien_traduction --apply
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def origine_de(url_source: str) -> tuple[int, str]:
    """« translated:198:fr » → (198, 'fr'). (0, '') si ce n'est pas une traduction."""
    m = re.match(r"^translated:(\d+):([a-z]{2})$", (url_source or "").strip())
    return (int(m.group(1)), m.group(2)) if m else (0, "")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="écrit (défaut : simulation)")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    a_relier, refuses = [], []
    for r in conn.execute(
            "SELECT id, url_source, title, translated_lang, date_event_start, "
            "wp_post_id_as FROM events_raw "
            "WHERE url_source LIKE 'translated:%' AND COALESCE(translation_of,0)=0"):
        origine, langue = origine_de(r["url_source"])
        if not origine or origine == r["id"]:
            refuses.append((r["id"], "adresse illisible ou fiche pointant sur elle-même"))
            continue
        o = conn.execute("SELECT id, translation_of, date_event_start, date_event_end, "
                         "statut FROM events_raw WHERE id=?", (origine,)).fetchone()
        if o is None:
            refuses.append((r["id"], f"original {origine} introuvable"))
            continue
        if o["translation_of"]:
            # Relier ici fabriquerait un CYCLE (A→B et B→A), dont on sait qu'il fait
            # repartir les deux côtés au hasard de l'ordre des rowid.
            refuses.append((r["id"], f"l'original {origine} est lui-même une traduction"))
            continue
        a_relier.append((r["id"], origine, langue or (r["translated_lang"] or "?"),
                         (r["title"] or "")[:52], (o["date_event_start"] or "").strip(),
                         (r["date_event_start"] or "").strip()))

    print(f"═══ {len(a_relier)} traduction(s) à rebrancher sur leur original ═══\n")
    for eid, origine, langue, titre, date_o, date_t in a_relier:
        gain = ""
        if date_o and not date_t:
            gain = f"  → héritera de la date {date_o}"
        print(f"  [{eid:>5}] → original {origine} ({langue}){gain}\n          {titre}")
    for eid, motif in refuses:
        print(f"  [{eid:>5}] REFUSÉ : {motif}")

    if not args.apply:
        print(f"\nSimulation — RIEN n'a été écrit. Ajouter --apply.")
        conn.close()
        return 0

    for eid, origine, *_ in a_relier:
        conn.execute("UPDATE events_raw SET translation_of=? WHERE id=?", (origine, eid))
    conn.commit()
    # Recompté en base (règle 6) : ce qui compte est le nombre de traductions ORPHELINES
    # qu'il reste, pas la longueur de la liste qu'on vient de parcourir.
    restant = conn.execute(
        "SELECT COUNT(*) FROM events_raw WHERE url_source LIKE 'translated:%' "
        "AND COALESCE(translation_of,0)=0").fetchone()[0]
    conn.close()
    print(f"\n✅ {len(a_relier)} traduction(s) rebranchée(s).")
    print(f"   {restant} traduction(s) restent sans lien (les refus ci-dessus).")
    print("   Les dates de l'original leur seront recopiées au prochain passage de "
          "scripts.dates (passe 4), et elles quittent la file « À compléter » : "
          "on répare l'ORIGINAL, jamais la traduction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
