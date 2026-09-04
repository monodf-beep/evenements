#!/usr/bin/env python3
"""Le TITRE publié est-il dans la même langue que le CORPS publié ?

LECTURE SEULE. Aucun appel LLM, aucune écriture, aucun réseau.

D'OÙ ÇA VIENT (2026-09-04). Franck a signalé la fiche « Regine in scena. L'arte del
costume italiano tra cinema e teatro » : étiquetée Polylang FR (elle sort sur les pages
territoire filtrées FR), son corps est bien rédigé en français, mais son TITRE est resté
en italien tel quel. `scripts.audit_langue_polylang` ne l'aurait pas vue : ce script-là
compare la langue VOULUE d'une traduction à la langue DEVINÉE au moment d'une éventuelle
republication — il ne regarde jamais si le titre et le corps d'UNE MÊME fiche parlent la
même langue.

Le mécanisme suspecté (`utils/lang.py`, docstring de `effective_lang`) : `scripts.enrich`
écrit TOUJOURS l'article en français par défaut, indépendamment de la langue du titre
scrapé. Un événement dont le titre est resté italien (jamais passé par
`translate_title_desc`, dans `scripts.translate_events`) peut donc porter un corps
français sous un titre italien — ou l'inverse si l'enrichissement a un jour tourné côté
italien. `detect_lang(title, description, territoire)` peut alors classer Polylang="fr"
(le corps, plus long, pèse plus que le titre dans le score combiné) sans que personne
n'ait retraduit le titre : la fiche sort bien côté FR, mais son titre ment.

CE QUE CE SCRIPT FAIT. Pour chaque fiche PUBLIÉE encore devant nous (règle 5), on
compare :
  - la langue du TITRE SEUL (`_score` sur `title`, décision nette uniquement — un titre
    ambigu, ex. un seul nom propre, ne prouve rien et est écarté) ;
  - la langue du CORPS SEUL (`_score` sur l'article rédigé si présent — chapô+corps —
    sinon sur `description`, décision nette uniquement).
Un écart entre les deux, quand les deux sont nets, est le signe concret du bug : le
lecteur voit un titre dans une langue et un texte dans une autre.

CE QU'ON EN FAIT. Une ligne ici est un CANDIDAT à retraduire le TITRE (pas la fiche
entière) via `scripts.translate_events`, ou à vérifier à la main si le titre est un nom
propre légitimement resté en langue source (ex. nom d'exposition en VO — voir le cas
Ankama documenté dans `titre_reecrit_mauvaise_langue`). Ce script ne tranche PAS lui-même
lequel des deux cas s'applique : il ne fait que désigner, jamais republier.

Usage (VPS) :
    .venv/bin/python -m scripts.audit_titre_corps_langue
    .venv/bin/python -m scripts.audit_titre_corps_langue --tout   # passé compris
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.lang import _score  # noqa: E402 — heuristique déterministe, pas de LLM
from scripts.audit_substance_published import devant_nous  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _lang_nette(texte: str) -> str:
    """'fr' / 'it' si le texte tranche nettement, '' sinon (ambigu ou vide) — même
    seuil de marge (>=2) que `detect_lang` pour rester cohérent avec le reste du dépôt."""
    fr, it = _score(texte or "")
    if abs(fr - it) < 2:
        return ""
    return "it" if it > fr else "fr"


def _corps_de(ev: dict) -> str:
    """Le texte du CORPS publié : l'article rédigé (chapô+corps) s'il existe — c'est LUI
    que le lecteur voit sur la fiche — sinon la description brute. Jamais le titre."""
    try:
        art = (json.loads(ev.get("enrich_data") or "") or {}).get("article") or {}
    except (ValueError, TypeError):
        art = {}
    if art:
        return f"{art.get('chapo', '')} {art.get('corps', '')}"
    return ev.get("description") or ""


def cote_du_permalien(url: str) -> str:
    """Le versant que WordPress a servi à la publication, lu dans l'adresse — '' si muet.
    Même fonction que dans `audit_langue_polylang` : un champ de la base, pas l'état
    d'aujourd'hui (règle 1) — d'où l'adresse REST fournie à côté pour vérifier."""
    u = (url or "").strip().lower()
    for lang in ("it", "fr"):
        if f"/{lang}/" in u:
            return lang
    return ""


def url_de_verification(url: str, post_id) -> str:
    """L'adresse REST qui répond VRAIMENT — pas le lien public (`?p=<id>` répond 404
    pour tout tribe_events, vivant ou mort, CLAUDE.md règle 1)."""
    origine = ""
    u = (url or "").strip()
    if "//" in u:
        origine = "/".join(u.split("/")[:3])
    if not origine or not post_id:
        return "—"
    return (f"{origine}/wp-json/wp/v2/tribe_events/{post_id}"
            f"?_fields=link,status,title")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Titre vs corps publiés : parlent-ils la même langue ? Lecture seule.")
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
        "AND duplicate_of IS NULL")]
    conn.close()

    publiees = [r for r in rows if args.tout or devant_nous(r, auj)]
    perimetre = "toutes dates" if args.tout else "encore devant nous"

    # Combien de fiches ont un titre ET un corps assez nets pour trancher — un zéro
    # d'écarts doit dire sur combien de cas il porte, sinon il ne prouve rien (règle 6).
    tranchables = []
    ecarts = []
    for r in publiees:
        lt = _lang_nette(r.get("title") or "")
        lc = _lang_nette(_corps_de(r))
        if not lt or not lc:
            continue
        tranchables.append(r)
        if lt != lc:
            ecarts.append((r, lt, lc))

    print("=" * 78)
    print("Titre vs corps publiés — même langue ?")
    print("=" * 78)
    print(f"Fiches publiées         : {len(rows)}, toutes dates")
    print(f"EXAMINÉES ici           : {len(publiees)} ({perimetre})")
    print(f"— dont titre ET corps tranchables : {len(tranchables)}")
    print(f"Écarts titre/corps      : {len(ecarts)}")
    print()

    if not ecarts:
        print(f"Aucun écart sur les {len(tranchables)} fiche(s) où titre et corps "
              f"tranchaient tous les deux nettement. Rien à faire.")
        if len(tranchables) < len(publiees):
            print(f"({len(publiees) - len(tranchables)} fiche(s) écartée(s) : titre ou "
                  f"corps trop court/ambigu pour trancher — ni preuve ni absence.)")
        return 0

    print("Chaque ligne : un titre publié dans une langue, sous un corps publié dans")
    print("l'autre. « Servie » est le versant que WordPress a rangé À LA PUBLICATION")
    print("(préfixe de l'adresse enregistrée) — pas l'état d'aujourd'hui : ouvrir")
    print("l'adresse REST de la dernière colonne pour ça (règle 1, CLAUDE.md).\n")
    print("| Fiche | Titre | Corps | Servie | Titre publié | Vérifier (API REST) |")
    print("|---:|---|---|---|---|---|")
    for r, lt, lc in ecarts:
        servie = cote_du_permalien(r.get("wp_permalink_as") or "")
        marque = f"**{servie}**" if servie and servie not in (lt, lc) else (servie or "—")
        print(f"| {r['id']} | {lt} | {lc} | {marque} | "
              f"{(r.get('title') or '')[:44]} | "
              f"{url_de_verification(r.get('wp_permalink_as') or '', r.get('wp_post_id_as'))} |")
    print()
    print("Pour chaque ligne : vérifier à la main si le titre est un NOM PROPRE resté")
    print("légitimement en langue source (ex. titre d'œuvre en VO — cas Ankama, voir")
    print("`titre_reecrit_mauvaise_langue` dans utils/lang.py) avant de retraduire — ce")
    print("script désigne, il ne tranche pas lequel des deux cas s'applique.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
