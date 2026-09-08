#!/usr/bin/env python3
"""Où le vocabulaire interdit est-il DÉJÀ publié ?

LECTURE SEULE. Aucun réseau, aucun appel LLM, aucune écriture.

D'OÙ ÇA VIENT. Franck, 2026-08-21, en lisant une page en ligne :
« de l'ancienne capitale du royaume de Sardaigne […] ne jamais mettre "royaume de
Sardaigne" mais mettre "les États de Savoie" ».

POURQUOI UN AUDIT EN PLUS DES PROMPTS. « Venise des Alpes » était interdit dans QUATRE
prompts de rédaction — et il a quand même été écrit, généré, publié, puis trouvé en ligne
le 2026-08-18. Une consigne de prompt agit sur ce qu'on écrira demain ; elle ne dit rien
de ce qui est déjà en ligne. Il faut les deux.

⚠️ CE RELEVÉ NE REMPLACE RIEN, ET NE DOIT PAS. Une expression interdite peut être le titre
officiel d'une exposition ou une citation : « Il Regno di Sardegna » sur l'affiche d'un
musée n'est pas notre prose. C'est pourquoi chaque ligne montre LA PHRASE — sans elle,
personne ne peut distinguer les deux, et une réécriture automatique abîmerait un nom propre.

PÉRIMÈTRE : les fiches liées à un post, TOUTES DATES. Contrairement aux files de travail,
celle-ci ignore la règle 5 exprès — une page publiée reste lisible et indexée des années
après l'événement, et c'est le TEXTE qu'on corrige, pas l'annonce.

Usage :
    .venv/bin/python -m scripts.audit_vocabulaire
    .venv/bin/python -m scripts.audit_vocabulaire --slack
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.vocabulaire import interdits, remplacement, trouver

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _texte(ev: dict) -> str:
    parts = [ev.get("article_title") or ev.get("title") or ""]
    if ev.get("enrich_data"):
        try:
            art = (json.loads(ev["enrich_data"]) or {}).get("article") or {}
            parts += [art.get("chapo") or "", art.get("corps") or ""]
        except (ValueError, TypeError):
            pass
    # Chaque morceau est CLOS par un point avant d'être collé au suivant. Sans ça, le
    # titre bave sur le chapô et l'extrait rendu commence par le titre — « Palazzo Madama
    # Vestige de la capitale du royaume de Sardaigne. » Trouvé en écrivant la fixture :
    # l'extrait doit montrer LA phrase fautive, pas son voisinage.
    clos = [p.strip() if p.strip().endswith((".", "!", "?", "…")) else p.strip() + "."
            for p in parts if p and p.strip()]
    return " ".join(clos)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Vocabulaire interdit déjà publié. Lecture seule.")
    p.add_argument("--slack", action="store_true", help="Verdict dans la boîte du jour.")
    p.add_argument("--exemples", type=int, default=12)
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n(lancer ce script sur le VPS.)")
        return 1

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL AND wp_deleted_at IS NULL")]
    conn.close()

    trouvailles: list[tuple[dict, str, str]] = []
    par_expression: Counter = Counter()
    for ev in rows:
        for expression, phrase in trouver(_texte(ev)):
            trouvailles.append((ev, expression, phrase))
            par_expression[expression] += 1

    print("=" * 78)
    print("VOCABULAIRE INTERDIT — ce qui est déjà en ligne")
    print("=" * 78)
    print(f"Fiches liées à un post : {len(rows)} (toutes dates — une page publiée reste "
          f"lisible\n                         des années après l'événement)")
    print(f"Expressions surveillées : {len(interdits())} — "
          f"{', '.join(e['expression'] for e in interdits())}")
    print(f"FICHES CONCERNÉES       : {len(trouvailles)}")
    print()

    if not trouvailles:
        print(f"Aucune occurrence sur les {len(rows)} fiches examinées.")
        print("Ce zéro dit son dénominateur : il vient d'un corpus lu, pas d'une requête")
        print("vide. Il ne dit rien en revanche des pages HORS agenda (guides, pages")
        print("éditoriales) — celles-ci ne passent pas par events_raw.")
    else:
        for expression, n in par_expression.most_common():
            rempl = remplacement(expression)
            quoi = f" → « {rempl} »" if rempl else " → à supprimer, on nomme la chose"
            print(f"### « {expression} » — {n} fiche(s){quoi}\n")
            lot = [(e, ph) for e, ex, ph in trouvailles if ex == expression]
            for ev, phrase in lot[:args.exemples]:
                print(f"- WP#{ev['wp_post_id_as']:<6} {(ev.get('article_title') or ev.get('title') or '')[:44]}")
                print(f"    « …{phrase}… »")
            if len(lot) > args.exemples:
                print(f"- …et {len(lot) - args.exemples} autre(s).")
            print()
        print("⚠️ LIRE LA PHRASE AVANT DE CORRIGER. Une expression interdite peut être le")
        print("   titre officiel d'une exposition ou une citation — ce n'est alors pas")
        print("   notre prose, et la réécrire abîmerait un nom propre.")

    if args.slack:
        from utils import slack
        detail = " · ".join(f"{e} : {n}" for e, n in par_expression.most_common(3))
        slack.notify(
            f"🗣 *Vocabulaire interdit* — sur {len(rows)} fiches publiées :\n"
            f"{'🔴' if trouvailles else '·'} {len(trouvailles)} fiche(s) concernée(s)"
            + (f"\n   {detail}" if detail else "")
            + "\n_Chaque cas se lit avec sa phrase : ça peut être le titre officiel d'une "
              "exposition, pas notre prose._")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
