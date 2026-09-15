#!/usr/bin/env python3
"""Note ce qui a été cherché sur une fiche, et ce que ça a donné.

D'OÙ ÇA VIENT — Franck, 2026-08-18 : « toutes les informations, on les trouve. C'est juste
que des fois c'est mal cherché […] il faut relancer sur des événements spécifiques. »

Ce script est la moitié ÉCRITURE de `utils.tentatives` ; `lister_a_completer` en est la
moitié lecture. Sans lui la mémoire reste vide, et la file redevient ce qu'elle était : la
même liste tous les matins, sans indication de ce qui a déjà échoué.

C'EST L'AGENT QUOTIDIEN QUI L'APPELLE, à chaque fiche ouverte — qu'il trouve ou non. Le
« muet » compte AUTANT que le « trouvé » : c'est lui qui fait avancer l'angle suivant, et
c'est la seule chose qui distingue une relance d'une répétition (CLAUDE.md, règle 3).

La NOTE est le champ le plus utile de tous : elle dit ce qu'on a lu — « la page ne donne
que l'heure », « turismoinlanga ne nomme aucun point de rendez-vous ». Celui qui reprendra
la fiche dans trois semaines n'aura pas à relire ce qu'on a déjà lu.

Il n'écrit RIEN dans la fiche elle-même : compléter passe par `completer_verifie`, qui
vérifie. Ici on ne note que la RECHERCHE.

Exemples :
  .venv/bin/python -m scripts.noter_tentative 4771 lieu page_fiche muet \
      --note "la page ne donne que « Domenica 6 settembre, ore 10 »"
  .venv/bin/python -m scripts.noter_tentative 4771 lieu recherche_nom trouve \
      --note "site de la Pro Loco : rendez-vous piazza Umberto I"
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import tentatives as t  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Note une tentative de recherche sur une fiche.")
    p.add_argument("event_id", type=int)
    p.add_argument("champ", help="le champ cherché : lieu, ville, date, url_image, …")
    p.add_argument("angle", choices=list(t.ANGLES), help="par où on a cherché")
    p.add_argument("resultat", choices=list(t.RESULTATS),
                   help="trouve · muet (la source ne le dit pas) · inaccessible (page HS)")
    p.add_argument("--note", default="", help="CE QU'ON A LU — le champ le plus utile.")
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    fiche = conn.execute("SELECT id, title FROM events_raw WHERE id=?",
                         (args.event_id,)).fetchone()
    if not fiche:
        print(f"Aucune fiche [{args.event_id}] — rien noté.")
        conn.close()
        return 1
    t.enregistrer(conn, args.event_id, args.champ, args.angle, args.resultat, args.note)
    faits = t.deja_tentes(conn, args.event_id, args.champ)
    conn.close()
    # RÈGLE 6 : on rend le RÉSULTAT, relu depuis la base, et on dit la suite.
    print(f"[{args.event_id}] {(fiche['title'] or '')[:50]} · {args.champ} : "
          f"{args.angle}={args.resultat} noté.")
    print(f"  {t.resume(faits)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
