#!/usr/bin/env python3
"""La file « À compléter », en clair, pour qu'on la traite À LA MAIN.

Franck, 2026-08-11, après un après-midi entier de correctifs : « donc on avance pas ? »
Les pastilles étaient passées de 68/28/102 à 67/27/100. Trois tâches.

Il avait raison, et le diagnostic tient en une phrase : j'optimisais un chemin qui
alimente un AUTRE stock que celui de son écran. Les fiches de la file « À compléter » ne
manquent presque jamais de ce que je réparais — elles manquent d'un LIEU, ou d'une date
que leur page ne publie pas. Aucune passe automatique ne les touchait, et aucune ne les
touchera : c'est le plancher décrit dans docs/CE_QUE_DISENT_LES_SOURCES_OFFICIELLES.md.

À 67 fiches, la bonne réponse n'est plus un extracteur de plus. C'est de les REGARDER.
Ce script ne fait donc rien d'autre que les afficher, en un format qu'on peut coller dans
une conversation : numéro, ce qui manque, titre, ville, et l'adresse à ouvrir.

IL N'ÉCRIT RIEN, ne pose aucun état, ne consomme aucune API. C'est un lecteur.

  .venv/bin/python -m scripts.lister_a_completer            # tout, groupé par manque
  .venv/bin/python -m scripts.lister_a_completer --manque lieu
  .venv/bin/python -m scripts.lister_a_completer --cap 30
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

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Champs obligatoires, et le libellé qu'on affiche. Même périmètre que la pastille du
# back-office (app.app.incomplete_clause) : c'est la condition pour que le nombre
# affiché ici soit LE MÊME que celui de l'écran — sans quoi on retombe dans le défaut
# de la journée, deux compteurs du même nom qui comptent deux choses (règle 6).
_OBLIGATOIRES = (
    ("date_event_start", "date", "COALESCE(recurring,0)=0"),
    ("lieu", "lieu", "COALESCE(multi_lieux,0)=0"),
    ("ville", "ville", "COALESCE(multi_lieux,0)=0"),
    ("territoire", "territoire", ""),
    ("llm_categorie", "catégorie", ""),
    ("url_image", "image", ""),
)


def _clause(today: str) -> tuple[str, tuple]:
    manques = " OR ".join(
        f"(COALESCE({col},'')=''" + (f" AND {cond})" if cond else ")")
        for col, _, cond in _OBLIGATOIRES)
    return (
        "statut IN ('evaluated','published_cs','published_sub') AND duplicate_of IS NULL "
        "AND COALESCE(translation_of,0)=0 "
        # Règle 5 : à venir, en cours, ou pas encore datable. Une fiche sans date reste
        # dans la file — c'est justement la date qui lui manque.
        "AND (COALESCE(date_event_end, date_event_start, '')='' "
        "     OR COALESCE(date_event_end, date_event_start) >= ?) "
        f"AND ({manques})", (today,))


def _manques(ev: dict) -> list[str]:
    out = []
    for col, libelle, cond in _OBLIGATOIRES:
        if (ev.get(col) or "").strip():
            continue
        if col == "date_event_start" and ev.get("recurring"):
            continue
        if col in ("lieu", "ville") and ev.get("multi_lieux"):
            continue
        out.append(libelle)
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manque", help="ne montrer que celles à qui il manque ce champ "
                                     "(date, lieu, ville, territoire, catégorie, image)")
    ap.add_argument("--cap", type=int, default=200, help="nombre maximum de lignes")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    today = date.today().isoformat()
    where, params = _clause(today)
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM events_raw WHERE {where} ORDER BY COALESCE(llm_score,0) DESC, id",
        params)]
    conn.close()

    lignes = [(ev, _manques(ev)) for ev in rows]
    if args.manque:
        lignes = [(ev, m) for ev, m in lignes if args.manque.lower() in m]

    print(f"═══ {len(lignes)} fiche(s) à compléter "
          f"({'manque ' + args.manque if args.manque else 'tous manques confondus'}) ═══")
    print("Périmètre : retenues, à venir ou en cours ou non datées, hors doublons et "
          "traductions — le même que la pastille du back-office.\n")
    for ev, m in lignes[:args.cap]:
        titre = (ev.get("article_title") or ev.get("title") or "")[:76]
        url = (ev.get("url_officiel") or ev.get("url_source") or "").strip()
        debut = (ev.get("date_event_start") or "").strip() or "date ?"
        fin = (ev.get("date_event_end") or "").strip()
        quand = f"{debut}→{fin}" if fin and fin != debut else debut
        ou = " · ".join(x for x in ((ev.get("lieu") or "").strip(),
                                    (ev.get("ville") or "").strip()) if x) or "lieu ?"
        print(f"[{ev['id']:>5}] manque : {', '.join(m):<28} {titre}")
        print(f"        {quand} · {ou}")
        print(f"        {url}")
    if len(lignes) > args.cap:
        print(f"\n… {len(lignes) - args.cap} ligne(s) de plus (relancer avec --cap).")
    # Répartition : dit tout de suite si le travail est de même nature ou dispersé.
    from collections import Counter
    par_manque = Counter(x for _, m in lignes for x in m)
    print("\nCe qui manque, tous cas confondus : "
          + " · ".join(f"{k} {v}" for k, v in par_manque.most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
