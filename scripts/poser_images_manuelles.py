#!/usr/bin/env python3
"""Pose des photos CHOISIES À LA MAIN sur des fiches en ligne, à partir d'une liste.

Né le 23/09/2026, Journées européennes du patrimoine : sur les 40 fiches valdôtaines,
25 affichaient la même bannière générique. Franck : « mieux des sites des musées ». Les
photos ont été cherchées sur les sites officiels (lovevda.it, castellogamba.vda.it,
regione.vda.it, lartisana.vda.it…) et REGARDÉES une à une avant d'être retenues.

Ce script ne choisit rien : il applique une liste préparée par un humain (ou une session
qui a vu les images), au format TSV `id_wordpress<TAB>url_image<TAB>crédit`, une ligne
par fiche. L'id est celui de N'IMPORTE LEQUEL des deux versants (FR ou IT) : la fiche
d'origine et toutes ses traductions reçoivent la même photo.

Ce qu'il écrit, pour chaque fiche du groupe :
  - url_image = la photo, image_source = 'manual' (aucun cron ne la remplace ensuite,
    et les traductions en héritent — cf. publish_batch_as._heriter_image_traduction) ;
  - image_credit = le crédit, affiché en légende ;
  - url_image_portrait et url_image_wide VIDÉS. publisher_as PRÉFÈRE url_image_portrait
    pour la vignette (incident du 21/09 : l'affiche de saison de Malraux restée dans
    cette colonne a supplanté la bonne image). Une photo choisie à la main doit être
    celle qu'on voit, dans les trois formats.

Puis, avec --apply, republie les fiches déjà en ligne (publish_batch_as --ids).

Dry-run par défaut (règle 4) : il affiche, ligne par ligne, quelle fiche de la base est
touchée et ce qu'elle portait avant.

    .venv/bin/python scripts/poser_images_manuelles.py config/images_manuelles_jep_2026.tsv
    .venv/bin/python scripts/poser_images_manuelles.py config/images_manuelles_jep_2026.tsv --apply
"""
from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "events.db"


def lire_liste(chemin: Path) -> list[tuple[int, str, str]]:
    """Lignes `id<TAB>url<TAB>crédit` ; `#` = commentaire. Refuse une ligne mal formée
    plutôt que de la sauter : une photo oubliée en silence ne se voit qu'en ligne."""
    out = []
    for n, brute in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
        ligne = brute.strip()
        if not ligne or ligne.startswith("#"):
            continue
        parts = [p.strip() for p in ligne.split("\t")]
        if len(parts) < 3 or not parts[0].isdigit() or not parts[1].startswith("http"):
            raise SystemExit(f"{chemin}:{n} : ligne mal formée — {ligne[:80]}")
        out.append((int(parts[0]), parts[1], parts[2]))
    return out


def groupe(conn: sqlite3.Connection, wp_id: int) -> list[sqlite3.Row]:
    """La fiche portant ce post WordPress, sa fiche d'origine et toutes les traductions."""
    r = conn.execute("SELECT id, translation_of FROM events_raw WHERE wp_post_id_as=? "
                     "AND duplicate_of IS NULL", (wp_id,)).fetchone()
    if not r:
        return []
    racine = r["translation_of"] or r["id"]
    return conn.execute(
        "SELECT id, translation_of, wp_post_id_as, statut, url_image, image_source, "
        "url_image_portrait, url_image_wide FROM events_raw "
        "WHERE (id=? OR translation_of=?) AND duplicate_of IS NULL ORDER BY id",
        (racine, racine)).fetchall()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("liste", type=Path)
    ap.add_argument("--apply", action="store_true", help="écrire et republier")
    args = ap.parse_args(argv)

    lignes = lire_liste(args.liste)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    a_publier: list[int] = []
    introuvables = []
    for wp_id, url, credit in lignes:
        g = groupe(conn, wp_id)
        if not g:
            introuvables.append(wp_id)
            print(f"WP#{wp_id} : AUCUNE fiche en base ne porte ce post — ignoré")
            continue
        print(f"WP#{wp_id} → {url}")
        for r in g:
            avant = (r["url_image_portrait"] or r["url_image"] or "")[:70]
            print(f"   fiche {r['id']:>5} (WP#{r['wp_post_id_as'] or '-'}, {r['statut']}) "
                  f"avant [{r['image_source'] or '-'}] {avant}")
            if (r["wp_post_id_as"] or 0) > 0:
                a_publier.append(r["id"])
        if args.apply:
            ids = [r["id"] for r in g]
            conn.execute(
                f"UPDATE events_raw SET url_image=?, image_source='manual', image_credit=?, "
                f"url_image_portrait='', url_image_wide='' "
                f"WHERE id IN ({','.join('?' * len(ids))})", [url, credit, *ids])
    if args.apply:
        conn.commit()
        # RELIRE, pas supposer (règle 6).
        poses = conn.execute(
            "SELECT COUNT(*) FROM events_raw WHERE image_source='manual' AND url_image IN "
            f"({','.join('?' * len(lignes))})", [u for _, u, _ in lignes]).fetchone()[0]
        print(f"\nRelu en base : {poses} fiche(s) portent maintenant une de ces photos "
              f"(image_source='manual').")
    conn.close()

    print(f"\n{len(lignes)} ligne(s) dans la liste, {len(introuvables)} introuvable(s), "
          f"{len(a_publier)} fiche(s) en ligne à republier"
          + ("" if args.apply else " — SIMULATION, rien n'a été écrit (--apply pour écrire)."))
    if args.apply and a_publier:
        return subprocess.call([sys.executable, str(ROOT / "scripts" / "publish_batch_as.py"),
                                "--ids", *map(str, a_publier)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
