#!/usr/bin/env python3
"""Quels articles racontent au lieu d'annoncer ?

Franck, 2026-08-11, sur l'article de Stefano Mancuso : « il faut toujours parler au futur
puisqu'on propose des événements qui se passent dans le futur. Ce n'est pas du tout ce que
je veux pour Agenda Sabauda. »

La cause est corrigée dans `scripts/enrich.py` — sa sélection excluait pas les événements
terminés, et sa consigne leur ordonnait alors « parle au passé ». Reste à savoir ce qui a
été écrit AVANT la correction, et surtout lesquels méritent qu'on s'en occupe.

DEUX FAMILLES, ET UNE SEULE EST DU TRAVAIL (règles 5 et 6) :

  • un compte rendu sur un événement ENCORE DEVANT NOUS est une vraie faute, et grave :
    la fiche annonce au passé quelque chose qui n'a pas eu lieu. Un lecteur croit que
    c'est fini et ne se déplace pas. Celles-là se réécrivent ;
  • un compte rendu sur un événement TERMINÉ est mal écrit, mais plus personne ne le
    cherche. Le compter, oui — pour connaître l'ampleur ; en faire une file de travail,
    non. C'est le reproche exact que Franck a fait le 2026-08-03 à audit_dedupe_damage.

Les deux nombres sont donc affichés séparément, avec leur périmètre écrit à côté.

  .venv/bin/python -m scripts.audit_temps_recit
  .venv/bin/python -m scripts.audit_temps_recit --tout      # montre aussi les passés
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

from utils.temps_recit import extraits_de_recit  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tout", action="store_true",
                    help="affiche aussi les événements terminés (par défaut : comptés seulement)")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    today = date.today().isoformat()

    devant, passes = [], []
    for r in conn.execute(
            "SELECT id, article_title, title, article_md, date_event_start, "
            "date_event_end, recurring, wp_post_id_as FROM events_raw "
            "WHERE COALESCE(article_md,'') <> '' AND statut NOT IN ('merged') "
            "AND COALESCE(translation_of,0)=0"):
        extraits = extraits_de_recit(r["article_md"])
        if not extraits:
            continue
        fin = (r["date_event_end"] or r["date_event_start"] or "").strip()
        a_venir = bool(r["recurring"]) or not fin or fin >= today
        (devant if a_venir else passes).append((dict(r), extraits))
    conn.close()

    print(f"═══ {len(devant)} article(s) au passé sur un événement ENCORE DEVANT NOUS ═══")
    print("C'est la seule famille qui soit du travail : la fiche raconte au passé quelque "
          "chose qui n'a pas encore eu lieu.\n")
    for r, extraits in sorted(devant, key=lambda x: x[0]["id"]):
        etat = "EN LIGNE" if r["wp_post_id_as"] else "hors ligne"
        titre = (r["article_title"] or r["title"] or "")[:66]
        print(f"  [{r['id']:>5}] {etat:10} {titre}")
        for e in extraits[:2]:
            print(f"          ↳ « …{e[:104]}… »")
    if not devant:
        print("  (aucun — les articles à venir annoncent bien)")

    print(f"\n{len(passes)} autre(s) article(s) au passé portent sur un événement TERMINÉ.")
    print("Mal écrits, mais plus personne ne les cherche : comptés, pas mis en file "
          "(règle 5). Ajouter --tout pour les voir.")
    if args.tout:
        for r, extraits in sorted(passes, key=lambda x: x[0]["id"]):
            titre = (r["article_title"] or r["title"] or "")[:66]
            print(f"  [{r['id']:>5}] {r['date_event_end'] or r['date_event_start']} {titre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
