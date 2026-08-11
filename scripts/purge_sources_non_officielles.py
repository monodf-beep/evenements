#!/usr/bin/env python3
"""Les fiches nées d'une source NON OFFICIELLE (presse, guide tiers) — les sortir.

Franck, 2026-08-11, en lisant la liste des fiches sans date : « on a encore du guida
torino ? alors que c'est du radar et qu'on en veut pas ? il faut faire un vrai travail
sur les sources en enlevant les radar, je veux que des sources officielles. »

Il avait raison, et le trou était précis. Le tier radar a bien été supprimé de
config/sources.txt le 2026-08-05, et 146 fiches purgées. Mais les newsletters entrent par
une AUTRE porte — scripts/gmail_collect.py — et celle-ci ne consultait aucune des deux
listes. guidatorino.com figurait pourtant déjà dans config/non_institutional_sources.txt :
la liste existait, ce canal ne la lisait pas. Le contrôle est désormais posé à l'entrée
(cf. `gmail_collect.expediteur_officiel`) ; ce script traite ce qui est DÉJÀ passé.

DEUX PANIERS, comme purge_radar.py et pour la même raison :
  1. PURGEABLES — pas en ligne : `statut='rejected'`, rien n'est supprimé, la fiche reste
     en base et se ré-ouvre en repassant le statut ;
  2. DÉJÀ EN LIGNE — seulement LISTÉES. Les retirer du site est une décision à part
     (règle 1 : un identifiant en base ne prouve rien sur le site ; et dépublier ce que
     des visiteurs voient déjà mérite un geste explicite, pas un effet de bord).

RÈGLE 5 : le passé est compté à part. Rejeter la fiche d'un événement terminé ne change
rien pour personne.

RÈGLE 4 : dry-run par défaut. Avant un --apply : `.venv/bin/python scripts/backup_db.py`.

Exemples :
  .venv/bin/python -m scripts.purge_sources_non_officielles
  .venv/bin/python -m scripts.purge_sources_non_officielles --apply
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger  # noqa: E402
from utils import radar  # noqa: E402

log = get_logger("purge_non_officielles")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _domaine(ev: dict) -> str:
    """Le domaine d'origine de la fiche : celui de son url_source si c'en est une, sinon
    celui de l'adresse d'expéditeur conservée dans source_name (fiches de newsletter,
    dont l'url_source est un pseudo-lien « gmail:… »)."""
    url = (ev.get("url_source") or "").strip()
    if url.startswith(("http://", "https://")):
        return url
    m = re.search(r"[\w.+-]+@([\w.-]+)", ev.get("source_name") or "")
    return "https://" + m.group(1).strip().lower() if m else ""


def _non_officielle(ev: dict) -> bool:
    d = _domaine(ev)
    # Sans domaine identifiable, on NE TOUCHE À RIEN : rejeter sur un doute couperait
    # des fiches d'organisateurs dont on n'a simplement pas su lire la provenance.
    return bool(d) and not radar.source_officielle(d)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Rejette les fiches issues de sources non officielles (presse/guides).")
    p.add_argument("--apply", action="store_true", help="Exécute (sinon simulation).")
    args = p.parse_args(argv)

    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(statut,'') NOT IN ('rejected','merged') "
        "AND duplicate_of IS NULL AND COALESCE(translation_of,0)=0")]

    concernees = [ev for ev in rows if _non_officielle(ev)]

    def _devant(ev):
        if ev.get("recurring"):
            return True
        fin = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()
        return not fin or fin[:10] >= today

    en_ligne = [ev for ev in concernees if ev.get("wp_post_id_as")]
    purgeables = [ev for ev in concernees if not ev.get("wp_post_id_as") and _devant(ev)]
    passees = [ev for ev in concernees
               if not ev.get("wp_post_id_as") and not _devant(ev)]

    print(f"═══ {len(concernees)} fiche(s) issues d'une source NON officielle ═══\n")

    par_dom: dict[str, int] = {}
    for ev in concernees:
        d = _domaine(ev).replace("https://", "").split("/")[0]
        par_dom[d] = par_dom.get(d, 0) + 1
    for d, n in sorted(par_dom.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4} {d}")

    print(f"\n  {len(purgeables):4} à rejeter (pas en ligne, encore devant nous)")
    print(f"  {len(passees):4} passées — comptées à part, les rejeter ne change rien")
    print(f"  {len(en_ligne):4} DÉJÀ EN LIGNE — listées seulement, jamais touchées ici\n")

    for ev in en_ligne[:40]:
        print(f"  ⚠️  [{ev['id']:>5}] WP#{ev['wp_post_id_as']} · "
              f"{(ev.get('title') or '')[:52]}")
    if en_ligne:
        print("\n  Ces fiches sont visibles du public. Les retirer est une décision à "
              "part :\n  .venv/bin/python -m scripts.trash_by_ids "
              + " ".join(str(e["id"]) for e in en_ligne[:30]) + "\n")

    if not args.apply:
        print("Simulation — RIEN n'a été modifié. Ajouter --apply pour rejeter.")
        print("Avant un lot : .venv/bin/python scripts/backup_db.py")
        conn.close()
        return 0

    ids = [ev["id"] for ev in purgeables]
    if ids:
        ph = ",".join("?" * len(ids))
        conn.execute(f"UPDATE events_raw SET statut='rejected' WHERE id IN ({ph})", ids)
        conn.commit()
    # RÈGLE 6 : recompter en base, ne jamais annoncer la longueur d'une liste.
    fait = conn.execute(
        f"SELECT COUNT(*) FROM events_raw WHERE statut='rejected' AND id IN "
        f"({','.join('?' * len(ids)) or 'NULL'})", ids).fetchone()[0] if ids else 0
    conn.close()
    print(f"\n{fait} fiche(s) réellement rejetée(s) en base (attendu : {len(ids)}).")
    if fait != len(ids):
        print("⚠️ ÉCART — recompter à la main avant d'aller plus loin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
