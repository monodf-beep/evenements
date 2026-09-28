#!/usr/bin/env python3
"""Pose une SOURCE OFFICIELLE choisie à la main sur des fiches en ligne, à partir d'une liste.

Né le 24/09/2026. En lisant le flux RSS, Franck a vu Palazzo Carignano renvoyer, en « Site
officiel », vers une page du château de RACCONIGI ; « À Turin, la recherche sort des
laboratoires » (Nuit des chercheurs) renvoyait vers la page de la Cosplayer Run. Deux
sources précises, mais fausses : `affiner_source` ne les voit pas (il ne traite que les
sources génériques, racine ou rubrique), et aucun script ne permettait d'en poser une.

Ce script ne choisit rien : il applique une liste préparée par un humain (ou une session
qui a LU la page et vérifié qu'elle parle de l'événement), au format TSV
`id_wordpress<TAB>url<TAB>motif`. L'id est celui de N'IMPORTE LEQUEL des versants (FR ou
IT) : la fiche d'origine et toutes ses traductions reçoivent la même source.

Ce qu'il écrit : `url_officiel`, la colonne que `radar.official_anchor` lit EN PREMIER, et
donc celle qui décide de la source publiée (`publisher_as._source_publiable`). Puis, avec
--apply, il republie les fiches en ligne (publish_batch_as --ids) : la méta
`as_source_officielle_url` et le bouton « Source officielle » suivent. ⚠️ Le lien écrit DANS
le corps d'une fiche GELÉE ne suit pas — le pipeline ne touche plus à son texte. Il se
corrige côté site (Novamira), fiche par fiche.

Dry-run par défaut (règle 4).

    .venv/bin/python scripts/poser_source.py config/sources_manuelles_2026_09.tsv
    .venv/bin/python scripts/poser_source.py config/sources_manuelles_2026_09.tsv --apply
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
    """Lignes `id<TAB>url<TAB>motif` ; `#` = commentaire. Une ligne mal formée arrête tout
    plutôt que d'être sautée en silence."""
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
        "SELECT id, translation_of, wp_post_id_as, statut, url_officiel, url_source "
        "FROM events_raw WHERE (id=? OR translation_of=?) AND duplicate_of IS NULL ORDER BY id",
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
    for wp_id, url, motif in lignes:
        g = groupe(conn, wp_id)
        if not g:
            introuvables.append(wp_id)
            print(f"WP#{wp_id} : AUCUNE fiche en base ne porte ce post — ignoré")
            continue
        print(f"WP#{wp_id} → {url}\n   motif : {motif}")
        for r in g:
            print(f"   fiche {r['id']:>5} (WP#{r['wp_post_id_as'] or '-'}, {r['statut']}) "
                  f"avant url_officiel={(r['url_officiel'] or '-')[:80]}")
            if (r["wp_post_id_as"] or 0) > 0:
                a_publier.append(r["id"])
        if args.apply:
            ids = [r["id"] for r in g]
            conn.execute(f"UPDATE events_raw SET url_officiel=? "
                         f"WHERE id IN ({','.join('?' * len(ids))})", [url, *ids])
    if args.apply:
        conn.commit()
        # RELIRE, pas supposer (règle 6).
        poses = conn.execute(
            f"SELECT COUNT(*) FROM events_raw WHERE url_officiel IN "
            f"({','.join('?' * len(lignes))})", [u for _, u, _ in lignes]).fetchone()[0]
        print(f"\nRelu en base : {poses} fiche(s) portent maintenant une de ces sources.")
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
