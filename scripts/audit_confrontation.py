#!/usr/bin/env python3
"""REJOUER `utils.confronter` sur la matière réellement collectée — une mesure, pas une file.

POURQUOI CE SCRIPT EXISTE, et pourquoi il est arrivé APRÈS le garde-fou qu'il mesure.

`utils/confronter.py` a été écrit le 2026-08-13 et n'a été passé sur des données réelles
que le 16. Ce jour-là il rendait 7 signalements, et **deux des quatre événements signalés
étaient faux** : la matière collectée n'est presque jamais une page d'événement, c'est un
item de newsletter ou un article de presse, et ces textes-là citent couramment la plage de
l'événement d'À CÔTÉ (le Nice Classic Festival dans la lettre de Matisse–YSL, les ATP
Finals qui contiennent la soirée d'Achille Lauro). La règle fautive — « une seule plage
dans le texte, donc aucune ambiguïté sur ce dont il parle » — est morte de cette mesure.

Franck, le soir même : « une mesure hors dépôt n'est pas rejouable, et c'est précisément
comme ça qu'une fausse règle survit. » D'où ce fichier. Les nombres cités dans l'en-tête
de `utils/confronter.py` se rejouent tous par :

    .venv/bin/python -m scripts.audit_confrontation --en-ligne

CE QUE CE SCRIPT N'EST PAS — et la distinction n'est pas cosmétique (règle 6 : deux
compteurs qui portent le même nom et comptent deux choses se contrediront un jour, et
c'est le plus gros qu'on croira).

`scripts/verifier_dates.py` est la FILE : il tourne à 11h30 par cron, alerte Slack quand
il trouve, et ses lignes ont un geste au bout. Celui-ci ne tourne dans aucun cron,
n'alerte personne, n'écrit rien en base : c'est un banc d'essai, on le lance quand on
touche à la règle, pour lire ce qu'elle refuse AVANT de la croire. Les deux se recoupent
mais ne lisent pas la même chose au même moment :

  • `verifier_dates` cherche une CONTRADICTION de date sur la matière collectée, après
    publication, avec ses trois familles (une seule date, année, jour de semaine) ;
  • `confronter` est destiné à l'ENRICHISSEMENT, quand la page officielle vient d'être
    téléchargée et qu'elle est encore en mémoire — ses bornes, son année, son URL.

Ici, faute de page officielle sous la main, on lui donne la MATIÈRE COLLECTÉE. C'est un
substitut, et il faut le savoir en lisant les nombres : une fiche datée depuis la page
officielle sera comptée « muette » par ce banc alors qu'elle est parfaitement vérifiée.

LE TEXTE DONNÉ AU GARDE-FOU est celui de `verifier_dates._materiau`, réutilisé tel quel et
surtout pas réécrit : titre + description (+ corps de mail), balises retirées. Ses deux
exclusions ont déjà été payées en production — `article_md` est notre propre écriture,
rédigée À PARTIR de la date qu'on veut vérifier (le témoin qui se cite lui-même), et
`date_start` n'est que l'horodatage de publication du flux RSS.

  .venv/bin/python -m scripts.audit_confrontation              # tout le périmètre règle 5
  .venv/bin/python -m scripts.audit_confrontation --en-ligne   # d'abord ce que le public voit
  .venv/bin/python -m scripts.audit_confrontation --ids 2414 527
  .venv/bin/python -m scripts.audit_confrontation --tout       # affiche aussi muets/ambigus

Déterministe, lecture seule, zéro appel LLM et zéro requête réseau (sauf `--urls`).
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import utils.confronter as C  # noqa: E402
from scripts.verifier_dates import _materiau  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Ce que chaque verdict veut dire, en une ligne, IMPRIMÉE à côté de son compte. Un
# compteur doit dire ce qu'il compte (règle 6) : « 97 muettes » ne s'interprète pas sans
# « on ne peut pas vérifier un silence », et c'est ce genre de nombre nu qui a fait dire
# « 548 tâches, c'est ingérable ».
LEGENDE = {
    C.CONFIRME:  "la matière porte NOTRE plage, ou notre jour écrit seul",
    C.EFFONDREE: "la matière annonce une plage, la fiche ne garde que son premier jour",
    C.CONTREDIT: "une borne commune (même début ou même fin), l'autre diffère → à lire",
    C.AMBIGU:    "des dates, mais aucune borne commune : rien ne dit que ce texte parle "
                 "de nous. Compté, jamais listé",
    C.MUET:      "la matière ne porte aucune plage. Ce n'est PAS un doute : on ne peut "
                 "pas vérifier un silence",
}
ORDRE = (C.EFFONDREE, C.CONTREDIT, C.CONFIRME, C.AMBIGU, C.MUET)


def _lignes(conn: sqlite3.Connection, en_ligne: bool, ids: list[int] | None):
    """Le périmètre, identique à celui de `verifier_dates` — exprès.

    Deux bancs qui mesurent la même chose sur deux populations différentes rendent des
    nombres incomparables, et on finit par croire le plus gros. Donc : règle 5 (encore
    devant nous, `date_event_end` décide), pas de doublon, pas de `merged`/`rejected`,
    une date de début non vide (sans elle il n'y a rien à confronter), et les récurrents
    écartés — ils n'ont pas de date unique, les confronter n'a pas de sens.
    """
    from datetime import date as _date
    cols = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
    corps = "mail_corps" if "mail_corps" in cols else "'' AS mail_corps"
    champs = (f"id, title, description, {corps}, date_event_start, date_event_end, "
              "date_source, scrape_date, url_source, wp_post_id_as, source_name")
    if ids:
        marques = ",".join("?" * len(ids))
        return conn.execute(f"SELECT {champs} FROM events_raw WHERE id IN ({marques}) "
                            f"OR wp_post_id_as IN ({marques})", (*ids, *ids)).fetchall()
    where = ("COALESCE(duplicate_of,0)=0 "
             "AND COALESCE(statut,'') NOT IN ('merged','rejected') "
             "AND COALESCE(date_event_start,'') <> '' "
             "AND COALESCE(recurring,0)=0 "
             "AND COALESCE(NULLIF(date_event_end,''), date_event_start) >= ?")
    params: list = [_date.today().isoformat()]
    if en_ligne:
        where += " AND COALESCE(wp_post_id_as,0) <> 0"
    return conn.execute(f"SELECT {champs} FROM events_raw WHERE {where} "
                        "ORDER BY COALESCE(wp_post_id_as,0) DESC, id DESC",
                        params).fetchall()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Rejoue utils.confronter sur la matière collectée (mesure, pas file).")
    ap.add_argument("--en-ligne", action="store_true",
                    help="ne regarde que les fiches PUBLIÉES — une date fausse y coûte le "
                         "plus cher, un visiteur peut se déplacer dessus")
    ap.add_argument("--ids", nargs="*", type=int, default=None,
                    help="rejoue sur des fiches précises (id events_raw OU numéro WP), "
                         "hors périmètre — pour instruire un cas nommé")
    ap.add_argument("--tout", action="store_true",
                    help="affiche aussi les muets et les ambigus (par défaut on ne liste "
                         "que ce sur quoi il y aurait un geste)")
    ap.add_argument("--urls", action="store_true",
                    help="interroge AUSSI les URL de source (contrôle b). Réseau, lent, "
                         "et un 4xx ne prouve pas grand-chose sur un site qui filtre les "
                         "robots — donc désactivé par défaut")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    lignes = _lignes(conn, args.en_ligne, args.ids)

    bornes, annees, sources = Counter(), Counter(), Counter()
    sans_matiere = 0
    a_lire: list[tuple] = []
    autres: list[tuple] = []

    for r in lignes:
        ev = dict(r)
        texte = _materiau(r)
        # « Un zéro ne dit pas s'il vient d'un échec ou d'une absence de cas » (CLAUDE.md,
        # journal des erreurs). Une fiche sans matière n'est pas une fiche muette : c'est
        # une fiche qu'on n'a pas pu regarder, et les deux doivent se compter à part.
        if not texte.strip():
            sans_matiere += 1
            continue
        res = C.confronter(ev, texte, verifier_url=args.urls)
        bornes[res["bornes"]["verdict"]] += 1
        annees[res["annee"]["verdict"]] += 1
        sources[res["source"]["verdict"]] += 1
        (a_lire if res["a_lire"] else autres).append((ev, res))

    total = len(lignes)
    perimetre = ("PUBLIÉES, " if args.en_ligne else "") + "datées, encore devant nous (règle 5)"
    if args.ids:
        perimetre = "fiches nommées en argument — HORS périmètre règle 5"
    print("═══ La matière collectée confirme-t-elle nos bornes ? ═══")
    print(f"Périmètre : {total} fiche(s) {perimetre}.")
    print(f"Matière lue : titre + description (+ corps de mail), balises retirées — "
          f"`verifier_dates._materiau`. PAS `article_md` : notre propre écriture, rédigée "
          f"à partir de la date qu'on vérifie.")
    if sans_matiere:
        print(f"⚠️  {sans_matiere} fiche(s) SANS matière lisible — ni regardées ni comptées "
              f"ci-dessous. Elles ne sont pas « muettes », elles sont invisibles à ce banc.")
    print()
    for v in ORDRE:
        if bornes.get(v) or v in (C.EFFONDREE, C.CONTREDIT):
            print(f"  {bornes.get(v, 0):5d}  {v.upper():<10} {LEGENDE[v]}")
    print()
    print(f"  (a) année : " + ", ".join(f"{n} {v}" for v, n in sorted(annees.items())))
    if args.urls:
        print(f"  (b) URL   : " + ", ".join(f"{n} {v}" for v, n in sorted(sources.items())))
    else:
        print("  (b) URL   : non interrogée (--urls pour le faire)")

    print(f"\n─── {len(a_lire)} fiche(s) sur lesquelles il y aurait un geste ───")
    if not a_lire:
        print("Aucune. Et ce zéro est lisible : le détail des verdicts ci-dessus dit "
              "combien de cas se sont présentés.")
    for ev, res in a_lire:
        etat = f"EN LIGNE #{ev['wp_post_id_as']}" if ev["wp_post_id_as"] else "hors ligne"
        print(f"\n  [{ev['id']}] · {res['bornes']['verdict']:<9} {etat}   "
              f"(date_source={ev['date_source']})")
        print(f"        {(ev['title'] or '')[:78]}")
        print(f"        base : {ev['date_event_start']} → {ev['date_event_end'] or '—'}")
        for m in res["motifs"]:
            print(f"        → {m}")
        print(f"        source : {ev['source_name'] or '?'}")

    if args.tout:
        print(f"\n─── les {len(autres)} autres, pour mémoire ───")
        for ev, res in autres:
            print(f"  [{ev['id']}] {res['bornes']['verdict']:<9} "
                  f"{(ev['title'] or '')[:60]} — {res['bornes']['plages']} plage(s) lue(s)")

    print("\nSIGNALEMENT, PAS UN VERDICT : notre date peut être la bonne — elle vient "
          "parfois de la page officielle, que cette matière ne contient pas. Et sur Terra "
          "Madre, c'est la source officielle qui se trompait, pas nous.")
    print("Ce banc n'écrit rien et ne tourne dans aucun cron. La file quotidienne, c'est "
          "`scripts.verifier_dates` ; celui-ci sert à mesurer une RÈGLE avant de la croire.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
