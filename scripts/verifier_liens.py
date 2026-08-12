#!/usr/bin/env python3
"""LE LIEN QU'ON PUBLIE MÈNE-T-IL ENCORE QUELQUE PART ? — troisième contradicteur.

Après les dates (`verifier_dates`) et les lieux (`verifier_lieux`), celui-ci confronte la
dernière chose qu'une fiche affirme au public : « voici la page officielle de cet
événement ». Signalé par une autre session le 2026-08-12 sur la fiche 909, dont le lien
vers `opera-nice.org` répondait 404 — le visiteur qui cherche à réserver tombe sur rien.

CE N'EST PAS UN CONTRÔLE DE PLUS SUR LES SOURCES. `audit_sources_bloquees` regarde les
DOMAINES qui refusent notre serveur, une requête par domaine, pour savoir si la chaîne
peut encore aller lire des pages. Ici on regarde la PAGE PRÉCISE qu'un lecteur va cliquer
sur le site — c'est `url_officiel`, publié dans `as_source_officielle_url` et dans le champ
natif TEC `EventURL`.

CE QUI EST UNE TÂCHE, ET RIEN D'AUTRE : le 404 et le 410. La page a été retirée, notre
lien ment, et le geste est clair — retrouver l'adresse ou retirer le lien.

CE QUI N'EN EST PAS, ET C'EST LA MOITIÉ DU TRAVAIL :

  • le 403 / 401 / 429 — c'est NOTRE serveur qu'on refuse, pas la page qui a disparu. Le
    navigateur d'un visiteur l'ouvrirait sans difficulté. En faire une tâche, c'est
    envoyer quelqu'un réparer un lien qui marche : `agendaculturel.fr` répond 403 à ce
    serveur sur ses quatre sous-domaines et porte 338 fiches (audit du 2026-08-04) ;
  • le 5xx et l'injoignable — une panne d'hébergeur ou une coupure réseau ne dit rien de
    la page. Ça revient tout seul, et un signalement qui revient tout seul n'apprend rien ;
  • l'ABSENCE de lien. Une fiche sans `url_officiel` ne ment sur rien.

Les trois sont COMPTÉS, jamais listés : sans leur nombre, un « 0 lien mort » ne dirait pas
s'il vient d'un site sain ou d'un réseau coupé (docs/ERREURS_2026-08-11.md — « un zéro ne
dit pas s'il vient d'un échec ou d'une absence de cas »).

POURQUOI IL A LE DROIT DE SE REJOUER, alors que la règle 3 l'interdit ailleurs : la
matière CHANGE d'un passage à l'autre. Une page peut revenir, une page peut mourir. Ce
n'est pas un refus qui se rejoue sur la même entrée, c'est une surveillance — et elle
tourne à la semaine, pas au jour, parce que les pages ne meurent pas tous les matins.

Règle 5 : seulement ce qui est encore devant nous. Un lien mort sur un événement terminé
n'envoie plus personne nulle part.

Déterministe, zéro appel LLM. Lecture seule : aucune écriture en base.

  .venv/bin/python -m scripts.verifier_liens
  .venv/bin/python -m scripts.verifier_liens --slack
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
UA = {"User-Agent": "Mozilla/5.0 (compatible; AgendaSabauda/1.0; +https://agendasabauda.eu)"}
TIMEOUT = int(os.getenv("LIENS_TIMEOUT", "15"))
PARALLELE = int(os.getenv("LIENS_PARALLELE", "8"))


def etat(url: str) -> tuple[str, int | None]:
    """('vivant' | 'disparue' | 'refus' | 'panne' | 'injoignable', code HTTP ou None).

    GET et non HEAD : trop de serveurs répondent 405 ou 404 à un HEAD sur une page qui
    s'affiche parfaitement. On paie quelques kilo-octets pour ne pas inventer des liens
    morts — et un faux lien mort coûte plus cher qu'une requête, puisqu'il envoie
    quelqu'un réparer ce qui marche."""
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=UA, allow_redirects=True)
    except requests.RequestException:
        return "injoignable", None
    c = r.status_code
    if c < 400:
        return "vivant", c
    if c in (404, 410):
        return "disparue", c
    if c in (401, 403, 429):
        return "refus", c
    return ("panne" if c >= 500 else "disparue"), c


def lien_publie(row) -> str:
    """L'adresse que le SITE affiche pour cette fiche, ou "" — telle que la calcule la
    publication elle-même.

    ON NE LA RECALCULE PAS. La première version lisait la colonne `url_officiel`, ce qui
    paraissait évident et était faux : `publisher_as._source_publiable()` lit TROIS
    signaux (la colonne, les pages officielles réellement téléchargées dans
    `enrich_data.source.pages`, le booléen « matière officielle lue ») et, hors radar,
    retombe sur `url_source`. Sur la base réelle du 2026-08-12, ma version ne voyait que
    34 adresses là où le site en publie davantage : le « 0 lien mort » portait donc sur un
    périmètre plus étroit que celui qu'il annonçait — le défaut exact que
    docs/ERREURS_2026-08-11.md appelle « un zéro qui ne dit pas combien de cas se sont
    présentés ».

    Réutiliser la fonction qui DÉCIDE, au lieu d'en écrire une deuxième qui lui
    ressemble, est la seule façon que les deux ne divergent pas un jour."""
    ev = dict(row)
    from scripts.publisher_as import _source_publiable
    is_radar = (ev.get("source_type") == "radar"
                or "(radar)" in (ev.get("source_name") or ""))
    u = (_source_publiable(ev, is_radar) or "").strip()
    return u if u.startswith("http") else ""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tout", action="store_true",
                    help="regarde aussi les fiches NON publiées (par défaut, seules "
                         "comptent celles qu'un visiteur peut cliquer)")
    ap.add_argument("--cap", type=int, default=400,
                    help="plafond d'URL interrogées ; ce qui est laissé de côté est DIT")
    ap.add_argument("--slack", action="store_true",
                    help="alerte Slack s'il y a des liens morts — silence sinon")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    auj = date.today().isoformat()

    # RÈGLE 5. Une fiche SANS date reste dans le périmètre : donnée manquante, pas
    # événement terminé.
    where = ("COALESCE(duplicate_of,0)=0 "
             "AND COALESCE(statut,'') NOT IN ('merged','rejected') "
             "AND (COALESCE(recurring,0)=1 "
             "     OR COALESCE(NULLIF(date_event_end,''), date_event_start,'') = '' "
             "     OR COALESCE(NULLIF(date_event_end,''), date_event_start) >= ?)")
    params: list = [auj]
    if not args.tout:
        where += " AND COALESCE(wp_post_id_as,0) <> 0"

    rows = conn.execute(
        f"SELECT * FROM events_raw WHERE {where} "
        f"ORDER BY COALESCE(wp_post_id_as,0) DESC", params).fetchall()
    conn.close()

    # UNE URL, UNE REQUÊTE. Plusieurs fiches partagent souvent la même page officielle
    # (une saison, un festival) : les interroger une fois chacune multiplierait le coût
    # sans rien apprendre de plus.
    par_url: dict[str, list[sqlite3.Row]] = defaultdict(list)
    sans_lien = 0
    for r in rows:
        u = lien_publie(r)
        if u:
            par_url[u].append(r)
        else:
            sans_lien += 1

    urls = sorted(par_url)
    laisses = max(0, len(urls) - args.cap)
    urls = urls[:args.cap]

    print("═══ Le lien que nous publions mène-t-il encore quelque part ? ═══")
    print(f"Périmètre : {len(rows)} fiche(s) vivantes"
          + ("" if args.tout else ", PUBLIÉES")
          + f" (règle 5) · {sum(len(v) for v in par_url.values())} affichent un lien "
            f"officiel · {len(par_url)} adresse(s) distincte(s).")
    # LE NOMBRE DE FICHES SANS LIEN, DIT ICI ET PAS AILLEURS. Ce n'est pas l'objet de ce
    # contrôle et ce n'est pas une tâche — beaucoup de sources ne publient pas de page
    # par événement. Mais sans lui, on lirait « aucun lien mort » comme « tous nos liens
    # sont bons », alors que la question ne se pose que pour une partie des fiches.
    print(f"            {sans_lien} fiche(s) n'affichent AUCUN lien officiel — hors sujet "
          f"ici, mais c'est ce qui borne tout ce qui suit.")
    if laisses:
        # AUCUN PLAFOND SILENCIEUX : ce qui n'a pas été regardé est dit, sinon la sortie
        # se lit comme une couverture complète alors qu'elle ne l'est pas.
        print(f"⚠️  {laisses} adresse(s) au-delà du plafond --cap={args.cap} : PAS "
              f"interrogées. Relancer avec --cap plus haut pour les couvrir.")
    print()

    with ThreadPoolExecutor(max_workers=PARALLELE) as pool:
        resultats = list(pool.map(etat, urls))

    compte = {"vivant": 0, "disparue": 0, "refus": 0, "panne": 0, "injoignable": 0}
    morts: list[tuple[str, int | None, list[sqlite3.Row]]] = []
    for u, (verdict, code) in zip(urls, resultats):
        compte[verdict] += 1
        if verdict == "disparue":
            morts.append((u, code, par_url[u]))

    fiches_mortes = sum(len(f) for _u, _c, f in morts)
    print(f"  {compte['vivant']:>5}  vivants")
    print(f"  {compte['disparue']:>5}  DISPARUS (404/410) — {fiches_mortes} fiche(s) "
          f"envoient un lecteur sur une page retirée")
    print(f"  {compte['refus']:>5}  refus (401/403/429) — c'est NOTRE serveur qu'on "
          f"écarte, pas la page. Un visiteur l'ouvrirait : ce n'est pas une tâche")
    print(f"  {compte['panne']:>5}  pannes (5xx) — hébergeur en défaut, ça revient seul")
    print(f"  {compte['injoignable']:>5}  injoignables — réseau ou DNS ; idem, on ne "
          f"répare pas une coupure\n")

    if not morts:
        print("Aucun lien mort dans ce périmètre.")
        if args.slack:
            print("(--slack : rien à signaler, aucun message envoyé.)")
        return 0

    print(f"═══ {len(morts)} adresse(s) morte(s), la plus partagée d'abord ═══")
    print("Le geste : retrouver l'adresse à jour sur le site de l'organisateur, la poser "
          "par `completer_verifie --depuis` (colonne url_officiel), puis republier. Si la "
          "page n'existe plus du tout, vider le champ vaut mieux que mentir.\n")
    for u, code, fiches in sorted(morts, key=lambda m: -len(m[2])):
        print(f"  {code}  {u}")
        for f in fiches[:4]:
            etiq = f"EN LIGNE #{f['wp_post_id_as']}" if f["wp_post_id_as"] else "hors ligne"
            print(f"        [{f['id']:>5}] {etiq}   {(f['title'] or '')[:60]}")
        if len(fiches) > 4:
            print(f"        … et {len(fiches) - 4} autre(s) fiche(s)")
        print()

    if args.slack:
        from utils import slack
        lignes = [f"*{len(morts)} lien(s) officiel(s) mort(s)* — {fiches_mortes} fiche(s) "
                  f"publiées envoient un lecteur sur une page retirée "
                  f"(périmètre : {len(par_url)} adresses vérifiées) :"]
        for u, code, fiches in sorted(morts, key=lambda m: -len(m[2]))[:8]:
            lignes.append(f"• {code} {u} — {len(fiches)} fiche(s), ex. "
                          f"[{fiches[0]['id']}] {(fiches[0]['title'] or '')[:45]}")
        if len(morts) > 8:
            lignes.append(f"… et {len(morts) - 8} autre(s).")
        lignes.append("Détail : `.venv/bin/python -m scripts.verifier_liens`")
        slack.notify("\n".join(lignes))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
