#!/usr/bin/env python3
"""LA SOURCE DIT-ELLE LA MÊME DATE QUE NOUS ? — contradiction, pas extraction.

Franck, 2026-08-11 : « est-ce qu'on a des loops de script jusqu'à obtenir des résultats ?
plus vérificateur ? concernant la véracité des informations ».

Deux questions, et il faut y répondre séparément parce qu'elles ne vont pas ensemble.

SUR LES BOUCLES : on en a, et CLAUDE.md interdit celle qu'on croit vouloir. Rejouer un
refus sur la MÊME matière n'est pas un rouvreur (règle 3) — le modèle produit un résultat
équivalent, le portillon refuse à l'identique, tous les jours, en brûlant deux appels à
chaque passage. Constaté en vrai sur la fiche 3588. Nos vraies boucles ne se rejouent donc
que si QUELQUE CHOSE A CHANGÉ : `_rearme_matiere_changee` (l'empreinte du texte a bougé),
les cooldowns web (une page peut avoir été mise à jour), `purge_bylines --restaurer` (le
vocabulaire s'est amélioré). Une boucle « jusqu'à obtenir un résultat » sur une matière
figée ne converge pas : elle facture.

SUR LA VÉRACITÉ : là, il manquait vraiment quelque chose, et c'est ce script.

Tout le pipeline EXTRAIT. Personne ne CONTREDIT. Or on sait depuis le 2026-08-11, cinq
fois dans la même journée, que sur un texte écrit pour des humains on ne peut pas
extraire — seulement confirmer à partir d'un fait déjà connu. Ce script fait l'inverse du
reste de la chaîne : il part de ce qu'on a écrit et cherche à le REFUTER avec la matière
qu'on détient.

CE QU'IL SIGNALE, ET RIEN D'AUTRE

  ① CONTREDIT — le texte source ne contient QU'UNE SEULE date, et ce n'est pas la nôtre.
    Aucune ambiguïté possible sur « de quelle date parle ce texte » : il n'y en a qu'une.
  ② ANNÉE — le texte porte notre jour et notre mois, mais une autre année.

CE QU'IL NE SIGNALE PAS, ET C'EST LE PLUS IMPORTANT

  • l'ABSENCE. Un texte qui ne dit aucune date ne contredit rien. Le 2026-08-11, une file
    de 454 « points à contrôler » en comptait 315 qui n'étaient pas des faits douteux mais
    des informations que la source ne publie pas — personne ne peut vérifier la capacité
    d'accueil d'une sortie au lac, ni Franck ni le modèle. Une file pareille n'est pas un
    garde-fou, c'est l'inventaire des silences de la source, et elle noie le seul point qui
    comptait sous trois cents « tarifs non publiés » ;
  • le DÉSACCORD FLOU. Un texte qui contient cinq dates et pas la nôtre ne prouve rien :
    notre date vient peut-être de la page officielle, que ce texte ne contient pas. Compté,
    jamais listé.

Autrement dit : on ne liste que ce qui a un GESTE au bout (règle 6). Le compte des muets
et des indécis est affiché — sans lui, un « 0 contradiction » ne dirait pas s'il vient
d'une base saine ou d'une requête vide.

Déterministe, zéro appel LLM — donc utilisable pendant le plafond d'API.

  .venv/bin/python -m scripts.verifier_dates
  .venv/bin/python -m scripts.verifier_dates --en-ligne   # d'abord ce que le public voit
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

from scripts.dates import _MONTHS, _MONTH_RE, _iso, _strip, _year  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def dates_du_texte(texte: str, ref: date) -> set[str]:
    """TOUTES les dates lisibles d'un texte, en ISO. Volontairement différent de
    `dates.parse_dates`, qui rend LA date (la première qui accroche un motif).

    Ici on veut l'inventaire complet, parce que la question n'est pas « quelle date ? »
    mais « combien y en a-t-il ? ». C'est le nombre qui décide si le texte est sans
    ambiguïté (une seule date → il parle d'elle) ou muet sur le sujet (plusieurs dates →
    il faudrait comprendre, et comprendre est justement ce qu'on ne sait pas faire).

    `ref` sert à l'année sous-entendue et vaut la date de COLLECTE de la fiche, pas
    aujourd'hui : c'est le fait connu auquel on accroche le reste."""
    t = _strip(texte or "")
    trouvees: set[str] = set()

    for y, m, d in re.findall(r"\b(\d{4})-(\d{2})-(\d{2})\b", t):
        v = _iso(int(y), int(m), int(d))
        if v:
            trouvees.add(v)

    for d1, mon, yr in re.findall(rf"\b(\d{{1,2}})\s+({_MONTH_RE})\.?\s*(\d{{4}})?", t):
        mois = _MONTHS[mon]
        annee = int(yr) if yr else _year(int(d1), mois, ref)
        v = _iso(annee, mois, int(d1))
        if v:
            trouvees.add(v)

    for d1, mon, y in re.findall(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b", t):
        v = _iso(int(y), int(mon), int(d1))
        if v:
            trouvees.add(v)

    return trouvees


def _materiau(row: sqlite3.Row) -> str:
    """La matière SOURCE — jamais `article_md`.

    L'article est notre propre écriture : il a été rédigé À PARTIR de la date qu'on veut
    vérifier. Le confronter à elle ne prouverait qu'une chose, que la rédaction a bien
    recopié la base. C'est le piège du témoin qui se cite lui-même."""
    bouts = []
    for col in ("title", "description", "date_start"):
        try:
            if row[col]:
                bouts.append(str(row[col]))
        except (IndexError, KeyError):
            pass
    try:
        if row["mail_corps"]:
            bouts.append(str(row["mail_corps"]))
    except (IndexError, KeyError):
        pass
    return "\n".join(bouts)


def verdict(stockees: set[str], du_texte: set[str]) -> tuple[str, str]:
    """(verdict, motif). Verdicts : 'confirme' | 'contredit' | 'annee' | 'muet' | 'indecis'.

    L'ordre des tests compte. « confirmé » passe en premier : un texte qui contient NOTRE
    date ne la contredit pas, même s'il en contient dix autres (une page de saison cite ses
    voisines, un mail cite la date d'envoi)."""
    if not du_texte:
        return ("muet", "le texte source ne porte aucune date")
    if stockees & du_texte:
        return ("confirme", "la date figure telle quelle dans le texte source")

    # ② L'année : même jour, même mois, autre millésime. C'est la forme qu'a prise le
    #    défaut trouvé par l'agent, et elle est reconnaissable sans rien comprendre.
    for s in stockees:
        for d in du_texte:
            if s[5:] == d[5:] and s[:4] != d[:4]:
                return ("annee", f"le texte dit {d}, la base dit {s} — même jour, "
                                 f"autre année")

    # ① Une seule date dans le texte, et ce n'est pas la nôtre. Aucune ambiguïté sur ce
    #    dont le texte parle : il n'a qu'un candidat.
    if len(du_texte) == 1:
        seule = next(iter(du_texte))
        return ("contredit", f"le texte ne dit qu'UNE date, {seule} ; la base dit "
                             f"{' / '.join(sorted(stockees))}")

    return ("indecis", f"{len(du_texte)} dates dans le texte, aucune n'est la nôtre — "
                       f"notre date vient peut-être de la page officielle")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--en-ligne", action="store_true",
                    help="ne regarde que les fiches PUBLIÉES — un fait faux y coûte le "
                         "plus cher, puisqu'un visiteur le lit")
    ap.add_argument("--tout", action="store_true",
                    help="affiche aussi les indécis et les muets (par défaut on ne liste "
                         "que ce sur quoi il y a un geste à faire)")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cols = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
    corps = "mail_corps" if "mail_corps" in cols else "'' AS mail_corps"
    auj = date.today().isoformat()

    # RÈGLE 5 : seulement ce qui est encore devant nous. Une date fausse sur un événement
    # terminé n'envoie plus personne devant une porte close. C'est `date_event_end` qui
    # décide — une exposition de mai à septembre compte tout l'été.
    where = ("COALESCE(duplicate_of,0)=0 "
             "AND COALESCE(statut,'') NOT IN ('merged','rejected') "
             "AND COALESCE(date_event_start,'') <> '' "
             "AND COALESCE(recurring,0)=0 "
             "AND COALESCE(NULLIF(date_event_end,''), date_event_start) >= ?")
    params: list = [auj]
    if args.en_ligne:
        where += " AND COALESCE(wp_post_id_as,0) <> 0"

    lignes = conn.execute(
        f"SELECT id, title, description, date_start, {corps}, date_event_start, "
        "       date_event_end, date_source, scrape_date, wp_post_id_as, source_name "
        f"FROM events_raw WHERE {where} ORDER BY COALESCE(wp_post_id_as,0) DESC, id DESC",
        params).fetchall()

    compte = {"confirme": 0, "contredit": 0, "annee": 0, "muet": 0, "indecis": 0}
    a_voir: list[tuple] = []
    for r in lignes:
        try:
            ref = date.fromisoformat((r["scrape_date"] or auj)[:10])
        except ValueError:
            ref = date.today()
        stockees = {d for d in ((r["date_event_start"] or "").strip()[:10],
                                (r["date_event_end"] or "").strip()[:10]) if len(d) == 10}
        if not stockees:
            continue
        v, motif = verdict(stockees, dates_du_texte(_materiau(r), ref))
        compte[v] += 1
        if v in ("contredit", "annee") or (args.tout and v == "indecis"):
            a_voir.append((r, v, motif))

    total = sum(compte.values())
    print("═══ La source dit-elle la même date que nous ? ═══")
    print(f"Périmètre : {total} fiche(s) datées, encore devant nous"
          + (", PUBLIÉES" if args.en_ligne else "") + " (règle 5).\n")
    print(f"  {compte['confirme']:>5}  confirmées — la date est écrite dans le texte source")
    print(f"  {compte['contredit']:>5}  CONTREDITES — le texte ne dit qu'une date, "
          f"et ce n'est pas la nôtre")
    print(f"  {compte['annee']:>5}  ANNÉE — même jour, autre millésime")
    print(f"  {compte['indecis']:>5}  indécises — plusieurs dates, aucune n'est la nôtre "
          f"(notre date vient peut-être de la page)")
    print(f"  {compte['muet']:>5}  muettes — le texte source ne porte aucune date. "
          f"Ce n'est PAS un doute : on ne peut pas vérifier un silence\n")

    if not a_voir:
        print("Rien à corriger : aucune contradiction franche dans ce périmètre.")
        print("Les indécises et les muettes ne sont pas des tâches — il n'y a pas de "
              "geste au bout, et une file sans geste cache les vraies (règle 6).")
        conn.close()
        return 0

    print(f"═══ {len(a_voir)} fiche(s) à regarder, la plus coûteuse d'abord ═══\n")
    for r, v, motif in a_voir:
        etat = f"EN LIGNE #{r['wp_post_id_as']}" if r["wp_post_id_as"] else "hors ligne"
        marque = "⚠ ANNÉE" if v == "annee" else ("✗ CONTREDIT" if v == "contredit"
                                                 else "· indécis")
        print(f"  [{r['id']:>5}] {marque}   {etat}   "
              f"(date_source={r['date_source'] or '?'})")
        print(f"          {(r['title'] or '')[:72]}")
        print(f"          {motif}")
        print(f"          source : {r['source_name'] or '?'}\n")

    print("SIGNALEMENT, PAS UN VERDICT : notre date peut être la bonne — elle vient "
          "parfois de la page officielle, que ce texte ne contient pas. La correction se "
          "fait page en main, par `completer_verifie --depuis` et sa clause « remplace ».")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
