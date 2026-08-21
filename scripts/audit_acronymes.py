#!/usr/bin/env python3
"""Quels sigles le lecteur rencontre-t-il sans explication ?

LECTURE SEULE. Aucun réseau, aucun appel LLM, aucune écriture.

D'OÙ ÇA VIENT. Franck, 2026-08-18 : « TNN, personne ne comprend […]. Je ne sais pas s'il y
en a d'autres, mettre en place une règle. » La règle est dans `utils/acronymes.py` ; ce
script répond à la seconde moitié de la phrase — **combien y en a-t-il, et lesquels**.

DEUX RELEVÉS, ET ILS NE SE LISENT PAS PAREIL :

  1. **À DÉVELOPPER** — des sigles CONNUS du dictionnaire, présents dans un texte publié
     sans leur développement. C'est une file de travail : chaque ligne a un geste au bout ;
  2. **CANDIDATS** — des suites de capitales qui RESSEMBLENT à des sigles et qui ne sont
     pas au dictionnaire. Ça n'est pas une file, c'est une liste à LIRE : seul un œil sait
     que « ARCA » est peut-être un nom propre, et personne ne peut développer un sigle
     sans aller vérifier à la source.

⚠️ ON N'INVENTE JAMAIS UN DÉVELOPPEMENT. Un sigle mal développé est pire que le sigle seul :
il a l'air d'une information, donc plus personne ne le vérifie. Ce script ne propose donc
aucune expansion — il compte, il nomme, et il s'arrête là.

PÉRIMÈTRE : les fiches encore devant nous et liées à un post (règle 5). Développer un sigle
dans une fiche dont l'événement a eu lieu ne sert personne.

Usage :
    .venv/bin/python -m scripts.audit_acronymes
    .venv/bin/python -m scripts.audit_acronymes --slack
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.acronymes import a_developper, candidats, sigles_connus
from scripts.audit_substance_published import devant_nous

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _textes(ev: dict) -> tuple[str, str]:
    """(titre publié, corps). Le TITRE d'abord : c'est lui qui est sur la carte, donc le
    seul que le visiteur lit à coup sûr — le corps, il faut cliquer pour l'atteindre."""
    titre = (ev.get("article_title") or ev.get("title") or "").strip()
    corps = ""
    if ev.get("enrich_data"):
        try:
            art = (json.loads(ev["enrich_data"]) or {}).get("article") or {}
            corps = f"{art.get('chapo') or ''} {art.get('corps') or ''}"
        except (ValueError, TypeError):
            pass
    return titre, corps


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Sigles rencontrés sans explication. Lecture seule.")
    p.add_argument("--slack", action="store_true", help="Verdict dans la boîte du jour.")
    p.add_argument("--exemples", type=int, default=15)
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n(lancer ce script sur le VPS.)")
        return 1
    auj = date.today().isoformat()

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL AND wp_deleted_at IS NULL")]
    conn.close()
    vivantes = [e for e in rows if devant_nous(e, auj)]

    a_faire: list[tuple[dict, str, str]] = []      # (fiche, sigle, où)
    reperes: Counter = Counter()
    exemples: dict[str, str] = {}
    for ev in vivantes:
        langue = (ev.get("translated_lang") or "fr").strip().lower() or "fr"
        titre, corps = _textes(ev)
        for sigle in a_developper(titre, langue):
            a_faire.append((ev, sigle, "titre"))
        for sigle in a_developper(corps, langue):
            if not any(s == sigle and e is ev for e, s, _o in a_faire):
                a_faire.append((ev, sigle, "corps"))
        for c in candidats(f"{titre} {corps}"):
            if c in sigles_connus():
                continue
            reperes[c] += 1
            exemples.setdefault(c, titre[:60])

    print("=" * 78)
    print("SIGLES — ce que le lecteur rencontre sans explication")
    print("=" * 78)
    print(f"Fiches liées à un post : {len(rows)}")
    print(f"…encore devant nous    : {len(vivantes)}  ← LE PÉRIMÈTRE (règle 5)")
    print(f"Sigles au dictionnaire : {len(sigles_connus())} — {', '.join(sorted(sigles_connus()))}")
    print()

    print(f"## À DÉVELOPPER — {len(a_faire)} mention(s) sur des sigles CONNUS\n")
    if not a_faire:
        print(f"Aucune sur les {len(vivantes)} fiches examinées. Ce zéro peut vouloir dire")
        print("deux choses opposées : soit tout est développé, soit le dictionnaire ne")
        print(f"contient encore que {len(sigles_connus())} sigles. La liste des candidats")
        print("ci-dessous dit laquelle des deux.\n")
    else:
        print("Chaque ligne a un geste au bout : le développement existe, il manque juste")
        print("dans ce texte.\n")
        for ev, sigle, ou in a_faire[:args.exemples]:
            print(f"- **{sigle}** ({ou}) · WP#{ev['wp_post_id_as']} · "
                  f"{(ev.get('article_title') or ev.get('title') or '')[:52]}")
        if len(a_faire) > args.exemples:
            print(f"- …et {len(a_faire) - args.exemples} autre(s).")
        print()

    print(f"## CANDIDATS — {len(reperes)} suite(s) de capitales absentes du dictionnaire\n")
    print("⚠️ CECI N'EST PAS UNE FILE DE TRAVAIL. Personne ne peut développer un sigle sans")
    print("aller le vérifier à la source, et certains n'en sont pas — un nom propre en")
    print("capitales ressemble à un sigle. À LIRE, puis à trancher un par un.\n")
    if reperes:
        print("| Suite | Mentions | Vu dans |")
        print("|---|---:|---|")
        for c, n in reperes.most_common(args.exemples):
            print(f"| **{c}** | {n} | {exemples.get(c, '')[:48]} |")
        if len(reperes) > args.exemples:
            print(f"\n…et {len(reperes) - args.exemples} autre(s) moins fréquente(s).")
    print()
    print("Pour en ajouter un : `config/acronymes.json`, section `sigles`, avec sa source.")

    if args.slack:
        from utils import slack
        top = ", ".join(f"{c} ({n})" for c, n in reperes.most_common(5))
        slack.notify(
            f"🔤 *Sigles* — sur {len(vivantes)} fiches devant nous :\n"
            f"{'🔴' if a_faire else '·'} {len(a_faire)} mention(s) d'un sigle CONNU sans "
            f"son développement\n"
            f"· {len(reperes)} suite(s) de capitales pas encore au dictionnaire"
            + (f"\n   les plus fréquentes : {top}" if top else "")
            + "\n_Les candidates se LISENT : certaines sont des noms propres, et un "
              "développement inventé serait pire que le sigle._")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
