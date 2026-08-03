#!/usr/bin/env python3
"""Inventaire LECTURE SEULE des fiches de l'ARRONDISSEMENT DE GRASSE.

Combien de fiches, en base et en ligne, relèvent d'un territoire devenu hors périmètre
le 2026-08-02 (charte §2 : « Comté de Nice » = arrondissement de NICE, pas les
Alpes-Maritimes) ? Ce script répond à cette question et NE FAIT RIEN D'AUTRE.

GARANTIE D'INNOCUITÉ, vérifiable ligne à ligne :
  • la base est ouverte en `file:...?mode=ro` (URI SQLite, mode read-only) — toute
    tentative d'écriture lèverait une exception au lieu de modifier quoi que ce soit ;
  • aucun UPDATE / DELETE / INSERT n'est écrit dans ce fichier ;
  • aucun appel réseau : ni WordPress, ni LLM. Rien n'est dépublié, rien n'est purgé.
Le script imprime, à la fin, les commandes de purge à lancer — sans les exécuter.

« EN LIGNE » se lit dans la BASE (wp_post_id_as / wp_post_id_cs non nuls), pas en
sondant le site. C'est délibéré : sonder une URL pour en déduire l'existence d'un post
a déjà produit un faux diagnostic sur ce projet (une sonde `/?p=<id>` renvoyant 404
pour TOUS les posts d'un type donné, d'où « 61 posts supprimés » alors qu'aucun ne
l'était). On rapporte donc ce que la base AFFIRME, et on imprime les permaliens pour
que la vérification se fasse à l'œil, sur le vrai site.

    python scripts/count_grasse.py             # les compteurs
    python scripts/count_grasse.py --list      # + le détail fiche par fiche
    python scripts/count_grasse.py --csv x.csv # + export CSV (seule écriture possible,
                                               #   dans le fichier que TU nommes)
"""
from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.perimetre import ville_hors_perimetre
from scripts.purge_out_of_zone import GRASSE_STATUTS

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Colonnes souhaitées ; certaines sont des colonnes de MIGRATION (ajoutées après coup)
# et peuvent manquer sur une base ancienne — on ne demande que celles qui existent.
VOULUES = ("id", "title", "ville", "lieu", "territoire", "statut", "llm_score",
           "wp_post_id_as", "wp_post_id_cs", "wp_permalink_as", "published_as_date",
           "translation_of", "translated_lang", "duplicate_of", "venue_source")


def ouvrir_ro(path: Path) -> sqlite3.Connection:
    """Ouvre la base en LECTURE SEULE (mode=ro). Échoue franchement si impossible."""
    if not path.exists():
        raise SystemExit(f"Base introuvable : {path}\n"
                         "Sur le VPS : DB_PATH=/root/evenements/data/events.db")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def colonnes(conn: sqlite3.Connection) -> list[str]:
    presentes = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
    return [c for c in VOULUES if c in presentes]


def charger(conn: sqlite3.Connection) -> tuple[list, list, int]:
    """(fiches Grasse, fiches sans ville en territoire Nice, total lignes examinées)."""
    cols = colonnes(conn)
    rows = conn.execute(f"SELECT {', '.join(cols)} FROM events_raw").fetchall()
    grasse = [r for r in rows if ville_hors_perimetre(r["ville"] if "ville" in cols else "")]
    # Angle mort à documenter : territoire « Nice » mais `ville` vide → ni le
    # pré-filtre de l'évaluateur ni ce comptage ne peuvent trancher. Seule l'ÉTAPE 0
    # du prompt LLM les voit. On les compte pour que la limite soit chiffrée, pas devinée.
    aveugles = [r for r in rows
                if not (r["ville"] or "").strip()
                and "nice" in (r["territoire"] or "").lower()]
    return grasse, aveugles, len(rows)


def en_ligne(r: sqlite3.Row, cols: list[str]) -> bool:
    return any(r[c] for c in ("wp_post_id_as", "wp_post_id_cs") if c in cols)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Inventaire LECTURE SEULE des fiches de l'arrondissement de Grasse.")
    p.add_argument("--list", action="store_true", help="Détail fiche par fiche.")
    p.add_argument("--csv", default="", help="Chemin d'un export CSV (optionnel).")
    p.add_argument("--db", default="", help="Base à lire (défaut : $DB_PATH).")
    args = p.parse_args(argv)

    path = Path(args.db) if args.db else DB_PATH
    conn = ouvrir_ro(path)
    cols = colonnes(conn)
    grasse, aveugles, total = charger(conn)

    manquantes = [c for c in VOULUES if c not in cols]
    print(f"\nBase : {path}  (LECTURE SEULE, mode=ro)")
    print(f"Lignes examinées dans events_raw : {total}")
    if manquantes:
        print(f"Colonnes absentes de cette base (ignorées) : {', '.join(manquantes)}")

    online = [r for r in grasse if en_ligne(r, cols)]
    # Le décompte « purgeable » DOIT utiliser exactement le périmètre de
    # scripts/purge_out_of_zone.py (mêmes statuts, non publiées) : deux chiffres
    # proches mais différents feraient croire à une purge incomplète.
    purgeables = [r for r in grasse
                  if not en_ligne(r, cols) and (r["statut"] or "") in GRASSE_STATUTS]
    inertes = [r for r in grasse if r not in online and r not in purgeables]

    print("\n" + "=" * 72)
    print("ARRONDISSEMENT DE GRASSE — hors périmètre depuis le 2026-08-02 (charte §2)")
    print("=" * 72)
    print(f"  TOTAL en base .................. {len(grasse)}")
    print(f"    dont EN LIGNE (wp_post_id) ... {len(online)}   ← à dépublier à la main")
    print(f"    dont purgeables .............. {len(purgeables)}   ← ce que "
          f"purge_out_of_zone.py --apply rejettera")
    print(f"    dont déjà écartées ........... {len(inertes)}   ← statut hors "
          f"{'/'.join(GRASSE_STATUTS)} (rejected, merged…), rien à faire")

    if grasse:
        print("\n  Par statut :")
        for st, n in Counter((r["statut"] or "?") for r in grasse).most_common():
            print(f"    {st:<16} {n}")
        print("\n  Par commune :")
        for v, n in Counter((r["ville"] or "?").strip() for r in grasse).most_common():
            print(f"    {v:<26} {n}")
        if "translation_of" in cols:
            jumeaux = sum(1 for r in grasse if r["translation_of"])
            print(f"\n  Dont fiches TRADUITES (jumeau IT d'une fiche FR) : {jumeaux}")
            print("  → une purge doit traiter les deux jumeaux ensemble, sinon la version"
                  "\n    italienne reste seule en ligne, orpheline.")

    print(f"\n  ANGLE MORT : {len(aveugles)} fiche(s) de territoire « Nice » ont une "
          f"`ville` VIDE.\n  Ni ce comptage ni le pré-filtre de l'évaluateur ne peuvent "
          "les classer ; seule\n  l'ÉTAPE 0 du prompt LLM les juge. Le chiffre ci-dessus "
          "est donc un PLANCHER,\n  pas un total certain.")

    if args.list and grasse:
        print("\n" + "-" * 72)
        for r in sorted(grasse, key=lambda x: (not en_ligne(x, cols), x["ville"] or "")):
            marque = "EN LIGNE" if en_ligne(r, cols) else "  base  "
            wp = r["wp_post_id_as"] if "wp_post_id_as" in cols else ""
            print(f"[{r['id']:>5}] {marque} {(r['ville'] or '—'):<22} "
                  f"{(r['statut'] or '—'):<15} wp_as={wp or '—':<7} {r['title'][:52]}")
            if "wp_permalink_as" in cols and r["wp_permalink_as"]:
                print(f"        {r['wp_permalink_as']}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(list(cols) + ["en_ligne"])
            for r in grasse:
                w.writerow([r[c] for c in cols] + [int(en_ligne(r, cols))])
        print(f"\nCSV écrit : {args.csv} ({len(grasse)} lignes)")

    conn.close()
    print("\n" + "=" * 72)
    print("AUCUNE MODIFICATION N'A ÉTÉ FAITE (base ouverte en lecture seule).")
    print("Suites possibles, À LANCER TOI-MÊME, dans cet ordre :")
    print("  1) sauvegarde        : python scripts/backup_db.py")
    print("  2) aperçu de la purge: python scripts/purge_out_of_zone.py")
    print("     (dry-run par défaut ; il liste séparément les fiches déjà en ligne,")
    print("      qu'il ne touche jamais)")
    print("  3) purge des non publiées, si l'aperçu te convient :")
    print("       python scripts/purge_out_of_zone.py --apply")
    print("     → statut='rejected', réversible en base ; --hard supprimerait les lignes.")
    print("  4) les fiches EN LIGNE se dépublient à la main (corbeille WordPress),")
    print("     jumeaux FR/IT ensemble — aucun script de ce lot ne le fait.")
    print("=" * 72 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
