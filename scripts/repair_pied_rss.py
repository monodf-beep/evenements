#!/usr/bin/env python3
"""Retire le pied de flux RSS resté dans les descriptions, et republie ce qui est en ligne.

D'OÙ ÇA VIENT — 2026-09-08, audit SEO. Treize fiches PUBLIÉES portaient encore
« L'article … est apparu en premier sur Mairie de Villefranche-sur-Mer . » — et sur trois
d'entre elles, cette phrase était la meta description que Google affiche, parce que
`publisher_as.build_post` fabrique l'extrait depuis la description quand `seo_answer`
manque, et que Yoast sert l'extrait quand il n'a pas de meta.

`utils.clean_text.strip_boilerplate` est corrigé (il ne reconnaissait pas « L'article »,
la forme française réelle du pied). Mais un nettoyeur corrigé ne nettoie que ce qui
passe par lui APRÈS : les descriptions déjà en base gardent la version d'avant, et rien
ne les republie. Ce script est ce rouvreur (règle 3, CLAUDE.md) : il est appelé par
`weekly_audits`, pas par un humain.

CE QU'IL FAIT
  1. lit toutes les descriptions qui contiennent un verbe de pied RSS ;
  2. les passe dans `strip_boilerplate` et n'écrit que si le texte a changé ;
  3. republie SANS média (texte + méta seuls) celles qui sont EN LIGNE et encore
     DEVANT NOUS (règle 5 : à venir, en cours, ou récurrente ; une fiche sans date n'est
     pas « passée »). Une fiche terminée est nettoyée en base mais pas republiée :
     personne ne la cherche plus.

Dry-run par défaut, `--apply` pour écrire. Déterministe, zéro LLM.

Usage :
    .venv/bin/python -m scripts.repair_pied_rss            # liste
    .venv/bin/python -m scripts.repair_pied_rss --apply    # nettoie + republie
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
from utils.logger import get_logger
from utils.clean_text import _FOOTER_VERB, strip_boilerplate
from utils.completeness import is_recurring

log = get_logger("repair_pied_rss")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Même filtre SQL grossier que le verbe du nettoyeur : LIKE ne connaît pas la casse
# des accents, c'est `_FOOTER_VERB` en Python qui tranche ensuite.
_LIKE = ("description LIKE '%apparu en premier sur%' OR description LIKE '%appeared first on%'"
         " OR description LIKE '%proviene da%' OR description LIKE '%apparso%'")


def _devant_nous(ev: dict, today: str) -> bool:
    if is_recurring(ev):
        return True
    fin = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()
    return not fin or fin[:10] >= today


def selectionner(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, description, wp_post_id_as, date_event_start, date_event_end, "
        "recurring FROM events_raw WHERE duplicate_of IS NULL AND (" + _LIKE + ")").fetchall()]
    return [r for r in rows if _FOOTER_VERB.search(r.get("description") or "")]


def republier(ids: list[int]) -> None:
    """Isolé pour que la fixture le remplace : le vrai chemin parle à WordPress."""
    from scripts.publish_batch_as import main as publish_main
    publish_main(["--ids", *[str(i) for i in ids], "--skip-media"])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Retire le pied RSS des descriptions et republie.")
    p.add_argument("--apply", action="store_true", help="Écrit et republie (sinon dry-run).")
    p.add_argument("--cap", type=int, default=25, help="Republications max par run.")
    args = p.parse_args(argv)

    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    rows = selectionner(conn)

    a_ecrire: list[tuple[str, int]] = []
    a_republier: list[dict] = []
    for r in rows:
        propre = strip_boilerplate(r["description"])
        if propre == r["description"]:
            continue   # verbe présent mais pas de marque devant : pas un pied, on ne touche pas
        a_ecrire.append((propre, r["id"]))
        if (r.get("wp_post_id_as") or 0) > 0 and _devant_nous(r, today):
            a_republier.append(r)

    mode = "APPLY" if args.apply else "DRY-RUN (rien ne bouge)"
    print(f"\nPied RSS dans les descriptions — {mode}")
    print(f"  {len(rows)} fiche(s) portent un verbe de pied · {len(a_ecrire)} à nettoyer · "
          f"{len(a_republier)} en ligne ET devant nous → à republier (cap {args.cap})")
    for r in a_republier[:args.cap]:
        print(f"    WP#{r['wp_post_id_as']:<6} [{r['id']}] {(r['title'] or '')[:60]}")
    if not args.apply:
        conn.close()
        return 0

    conn.executemany("UPDATE events_raw SET description=? WHERE id=?", a_ecrire)
    conn.commit()
    # Recompté après écriture, pas déduit de la longueur de la liste (règle 6).
    restants = len(selectionner(conn))
    conn.close()
    lot = [r["id"] for r in a_republier[:args.cap]]
    if lot:
        republier(lot)
    print(f"  {len(a_ecrire)} description(s) nettoyée(s), {restants} portent encore un verbe "
          f"de pied sans marque (laissées telles quelles), {len(lot)} republiée(s) sans média"
          + (f", {len(a_republier) - len(lot)} reportée(s) au run suivant" if len(a_republier) > len(lot) else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
