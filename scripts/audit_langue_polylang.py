#!/usr/bin/env python3
"""Les traductions publiées portent-elles la langue qu'on leur a demandée ?

LECTURE SEULE. Aucun appel LLM, aucune écriture, aucun réseau.

D'OÙ ÇA VIENT (2026-08-17). En réparant la séparation des versants de « À la une », j'ai
regardé comment la langue Polylang est réellement posée, et trouvé ceci :

  · `scripts.translate_events` publie une traduction avec `force_lang` — la langue est
    IMPOSÉE, jamais devinée. C'est le bon chemin ;
  · `scripts.publish_batch_as --update`, lui, republie les mêmes fiches depuis la base
    SANS `force_lang`. `publisher_as._lang` retombe alors sur `detect_lang`, qui devine
    à partir du titre, de la description et — en dernier recours — du TERRITOIRE.

Le texte d'une traduction est bien traduit (titre ET description), donc la devinette
tombe juste la plupart du temps. Mais quand le texte ne tranche pas — titre court, nom
propre, programme sans phrase — c'est le territoire qui décide : « Piemonte » ⇒ italien.
Une traduction FRANÇAISE d'un événement piémontais peut donc être republiée en ITALIEN,
et se retrouver du mauvais côté du sélecteur de langue.

Ce script ne prouve RIEN sur le site : il dit seulement quelles fiches sont exposées à
l'écart. La règle 1 tient toujours — pour savoir ce que WordPress sert, il faut le lui
demander, et la dernière colonne donne l'adresse à ouvrir pour ça.

CE QU'ON EN FAIT. Une ligne ici veut dire : « republier cette fiche pourrait changer sa
langue ». Le geste est alors `translate_events --retranslate <id de l'original>`, qui
repasse par `force_lang`. S'il n'y a aucune ligne, le compteur dit quand même combien de
fiches ont été examinées — un zéro qui ne dit pas son dénominateur ne prouve pas qu'il
n'y a rien à trouver (journal du 2026-08-11).

Usage (VPS) :
    .venv/bin/python -m scripts.audit_langue_polylang
    .venv/bin/python -m scripts.audit_langue_polylang --tout   # passé compris
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
from scripts.publisher_as import _lang as _lang_publiee
from scripts.audit_substance_published import devant_nous

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Langue Polylang des traductions. Lecture seule.")
    p.add_argument("--tout", action="store_true",
                   help="Inclure les événements passés (par défaut : seulement ce qui "
                        "est encore devant nous, règle 5).")
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n(lancer ce script sur le VPS.)")
        return 1
    auj = date.today().isoformat()

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL AND translation_of IS NOT NULL "
        "AND COALESCE(translated_lang,'') <> ''")]
    conn.close()

    examinees = [r for r in rows if args.tout or devant_nous(r, auj)]
    # Le périmètre s'écrit À CÔTÉ du nombre, pas dans le titre d'une section (règle 6).
    perimetre = "toutes dates" if args.tout else "encore devant nous"

    ecarts = []
    for r in examinees:
        voulue = (r.get("translated_lang") or "").strip().lower()
        devinee = _lang_publiee({k: v for k, v in r.items() if k != "force_lang"})
        if devinee != voulue:
            ecarts.append((r, voulue, devinee))

    print("=" * 78)
    print("Langue Polylang des traductions publiées")
    print("=" * 78)
    print(f"Traductions publiées   : {len(rows)}, toutes dates")
    print(f"EXAMINÉES ici          : {len(examinees)} ({perimetre})")
    print(f"Exposées à un écart    : {len(ecarts)}")
    print()

    if not ecarts:
        print(f"Aucun écart sur les {len(examinees)} traduction(s) examinée(s) : une")
        print("republication par `publish_batch_as --update` leur rendrait la même langue")
        print("que celle demandée à la traduction. Rien à faire.")
        return 0

    print("Pour chacune, une republication SANS `force_lang` poserait l'autre langue.")
    print("Vérifier d'abord ce que WordPress sert AUJOURD'HUI (règle 1) — la republication")
    print("de cette nuit a pu déjà la déplacer, ou pas :\n")
    print("| Fiche | Voulue | Devinée | Territoire | Titre | Page à ouvrir |")
    print("|---:|---|---|---|---|---|")
    for r, voulue, devinee in ecarts:
        print(f"| {r['id']} | {voulue} | **{devinee}** | {r.get('territoire') or '—'} | "
              f"{(r.get('title') or '')[:38]} | {r.get('wp_permalink_as') or '—'} |")
    print()
    print("Le geste, si la page est du mauvais côté du sélecteur de langue :")
    originaux = sorted({str(r["translation_of"]) for r, _v, _d in ecarts})
    print(f"    .venv/bin/python -m scripts.translate_events --retranslate "
          f"{' '.join(originaux)} --apply")
    print("(il republie par `force_lang`, donc il IMPOSE la langue au lieu de la deviner.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
