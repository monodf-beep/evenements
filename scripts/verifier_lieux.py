#!/usr/bin/env python3
"""LE LIEU ET LA VILLE SE CONTREDISENT-ILS ? — le pendant de `verifier_dates`.

Écrit le 2026-08-11 au soir, après qu'une autre session a trouvé la fiche lieu WordPress
208 : `_VenueCity = Aosta` pour le **Forte di Bard**, qui est à Bard, cinquante kilomètres
plus bas. Trois événements pointaient dessus et affichaient au public une ville fausse.

Ce qui rend le cas instructif, ce n'est pas la faute — c'est que **la bonne réponse était
déjà dans le dépôt**. `docs/savoir/forte-di-bard.md`, écrit par Franck pour enrichir les
articles, déclare en tête `villes: Bard`. Personne ne comparait ce qu'on savait à ce qu'on
publiait. Une deuxième chose l'aggravait : `cs-publish.php` réutilise une fiche lieu
existante sans jamais toucher à sa ville. Un lieu créé faux le restait pour toujours, et
chaque nouvel événement héritait de l'erreur — un état terminal sans rouvreur, le défaut
que `docs/ETATS_TERMINAUX.md` recense depuis une semaine.

TROIS CONFRONTATIONS, AUCUNE EXTRACTION (la leçon de la journée : sur une donnée écrite
pour des humains on ne peut pas extraire, seulement confirmer depuis un fait déjà tenu) :

  ① REGISTRE — `docs/savoir/` ou `config/lieux_villes.json` nomme ce lieu et donne sa
    ville, et nous disons autre chose. C'est Franck qui l'a écrite : elle fait foi.
  ② DÉSACCORD INTERNE — le même lieu porte deux villes différentes sur deux de NOS
    fiches. Aucune connaissance extérieure n'est requise : nos deux affirmations ne
    peuvent pas être vraies ensemble. C'est le signal le plus solide du lot, et le seul
    qui ne dépende d'aucune liste.
  ③ TOPONYME — le nom du lieu contient une commune que nous connaissons, et la ville en
    nomme une autre que nous connaissons aussi. Le plus large, et le seul qui puisse se
    tromper : « Café de Turin » est à Nice depuis 1908, son nom est un hommage et pas une
    adresse. D'où sa section à part, et le registre pour l'éteindre EN UNE LIGNE.

CE QU'IL NE SIGNALE JAMAIS : l'absence. Ville vide, lieu inconnu, commune hors de nos
listes — silence, et le nombre de muettes est affiché à côté. Un « 0 » qui ne dit pas
combien de cas se sont présentés ne distingue pas une base saine d'une requête vide
(docs/ERREURS_2026-08-11.md).

Règle 5 : seulement ce qui est encore devant nous. Une ville fausse sur un événement
terminé n'envoie plus personne dans la mauvaise commune.

Déterministe, zéro appel LLM — donc utilisable pendant le plafond d'API.

  .venv/bin/python -m scripts.verifier_lieux
  .venv/bin/python -m scripts.verifier_lieux --en-ligne   # d'abord ce que le public voit
  .venv/bin/python -m scripts.verifier_lieux --apply      # applique les corrections ①
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import lieux as _lieux  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def desaccords(rows: list[sqlite3.Row]) -> dict[str, dict[str, list[int]]]:
    """{lieu affiché : {ville affichée : [ids]}} pour les lieux portant PLUSIEURS villes.

    On regroupe sur la forme pliée du lieu — sinon « Forte di Bard » et « forte di bard »
    passeraient pour deux lieux et le désaccord resterait invisible. On regroupe les
    villes sur leur forme CANONIQUE (alias compris) pour la même raison : « Aoste » et
    « Aosta » sont la même ville, les opposer fabriquerait un signalement vide.

    Mais on RÉAFFICHE l'orthographe d'origine. La première version imprimait la forme
    pliée — « chambery », « aoste » — et c'est bête : ce texte est fait pour être lu par
    quelqu'un qui doit trancher en une seconde, pas par une machine."""
    par_lieu: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    nom_lieu: dict[str, str] = {}
    nom_ville: dict[str, str] = {}
    for r in rows:
        lieu, ville = (r["lieu"] or "").strip(), (r["ville"] or "").strip()
        if not lieu or not ville:
            continue
        cl, cv = _lieux.plie(lieu), _lieux.canon(ville)
        nom_lieu.setdefault(cl, lieu)
        nom_ville.setdefault(cv, ville)
        par_lieu[cl][cv].append(r["id"])
    return {nom_lieu[l]: {nom_ville[v]: ids for v, ids in villes.items()}
            for l, villes in par_lieu.items() if len(villes) > 1}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--en-ligne", action="store_true",
                    help="ne regarde que les fiches PUBLIÉES — une ville fausse y coûte "
                         "le plus cher, puisqu'un visiteur s'y rend")
    ap.add_argument("--apply", action="store_true",
                    help="corrige `ville` pour les contradictions ① (registre) — les "
                         "seules où nous tenons un fait qui fait foi. Dry-run sans ça "
                         "(règle 4)")
    ap.add_argument("--slack", action="store_true",
                    help="alerte Slack S'IL Y A QUELQUE CHOSE — silence sinon")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    auj = date.today().isoformat()

    # RÈGLE 5. `date_event_end` décide — une exposition de mai à septembre compte tout
    # l'été. Une fiche SANS date reste dans le périmètre : c'est une donnée manquante,
    # pas un événement terminé, et elle sera peut-être publiée demain.
    where = ("COALESCE(duplicate_of,0)=0 "
             "AND COALESCE(statut,'') NOT IN ('merged','rejected') "
             "AND (COALESCE(recurring,0)=1 "
             "     OR COALESCE(NULLIF(date_event_end,''), date_event_start) IS NULL "
             "     OR COALESCE(NULLIF(date_event_end,''), date_event_start,'') = '' "
             "     OR COALESCE(NULLIF(date_event_end,''), date_event_start) >= ?)")
    params: list = [auj]
    if args.en_ligne:
        where += " AND COALESCE(wp_post_id_as,0) <> 0"

    rows = conn.execute(
        f"SELECT id, title, lieu, ville, venue_source, wp_post_id_as, source_name "
        f"FROM events_raw WHERE {where} ORDER BY COALESCE(wp_post_id_as,0) DESC, id DESC",
        params).fetchall()

    avec_lieu = [r for r in rows if (r["lieu"] or "").strip()]
    confrontables = [r for r in avec_lieu if (r["ville"] or "").strip()]

    registre, toponyme = [], []
    for r in confrontables:
        v, phrase, attendue = _lieux.confronte(r["lieu"], r["ville"])
        if v == "registre":
            registre.append((r, phrase, attendue))
        elif v == "toponyme":
            toponyme.append((r, phrase, attendue))

    desac = desaccords(confrontables)
    titre_de = {r["id"]: (r["title"] or "")[:60] for r in confrontables}

    print("═══ Le lieu et la ville se contredisent-ils ? ═══")
    print(f"Périmètre : {len(rows)} fiche(s) vivantes"
          + (", PUBLIÉES" if args.en_ligne else "")
          + f" (règle 5) · {len(avec_lieu)} avec un lieu · {len(confrontables)} avec un "
            f"lieu ET une ville — les seules confrontables.\n")
    print(f"  {len(registre):>5}  ① CONTREDITES PAR CE QUE NOUS SAVONS — le registre "
          f"nomme une autre ville")
    print(f"  {len(desac):>5}  ② DÉSACCORDS INTERNES — un même lieu, deux villes chez "
          f"nous ; les deux ne peuvent pas être vraies")
    print(f"  {len(toponyme):>5}  ③ toponymes — le nom du lieu nomme une autre commune "
          f"(peut être un hommage : à confirmer, pas à corriger)")
    print(f"  {len(avec_lieu) - len(confrontables):>5}  muettes — un lieu, pas de ville. "
          f"Ce n'est PAS un doute : on ne peut pas confronter un silence.")
    reg = _lieux.registre()
    print(f"  {len(reg):>5}  lieux au registre (notes de savoir + "
          f"config/lieux_villes.json) — c'est lui qui borne tout ce qui précède.\n")

    if registre:
        print(f"═══ ① {len(registre)} fiche(s) contredisent le registre ═══")
        print("Ici nous tenons le fait : la note a été écrite exprès. `--apply` corrige.\n")
        for r, phrase, attendue in registre:
            etat = f"EN LIGNE #{r['wp_post_id_as']}" if r["wp_post_id_as"] else "hors ligne"
            print(f"  [{r['id']:>5}] {etat}   lieu={r['lieu']!r}")
            print(f"          {(r['title'] or '')[:72]}")
            print(f"          {phrase}")
            print(f"          → {r['ville']!r} deviendrait {attendue!r}"
                  f"   (venue_source={r['venue_source'] or '?'})\n")

    if desac:
        print(f"═══ ② {len(desac)} lieu(x) portent deux villes chez nous ═══")
        print("Aucune liste n'intervient : ce sont NOS deux affirmations qui s'excluent. "
              "Trancher une fois, puis consigner dans config/lieux_villes.json — sinon la "
              "question revient au prochain événement dans ce lieu.\n")
        for nom, villes in sorted(desac.items()):
            print(f"  « {nom} »")
            for ville, ids in sorted(villes.items(), key=lambda kv: -len(kv[1])):
                exemples = ", ".join(f"{i} ({titre_de.get(i, '')[:38]})" for i in ids[:3])
                suite = f" … et {len(ids) - 3} autre(s)" if len(ids) > 3 else ""
                print(f"      {ville:<22} {len(ids):>3} fiche(s) : {exemples}{suite}")
            print()

    if toponyme:
        print(f"═══ ③ {len(toponyme)} fiche(s) dont le NOM du lieu nomme une autre "
              f"commune ═══")
        print("À CONFIRMER, PAS À CORRIGER. Un établissement peut porter le nom d'une "
              "ville sans y être — « Café de Turin », à Nice depuis 1908. Une ligne dans "
              "config/lieux_villes.json éteint le cas pour de bon ET corrige les fiches "
              "suivantes ; s'en tenir à se taire laisserait la faute se reproduire.\n")
        for r, phrase, attendue in toponyme:
            etat = f"EN LIGNE #{r['wp_post_id_as']}" if r["wp_post_id_as"] else "hors ligne"
            print(f"  [{r['id']:>5}] {etat}   {(r['title'] or '')[:56]}")
            print(f"          {phrase}")
            print(f"          source : {r['source_name'] or '?'}\n")

    if not (registre or desac or toponyme):
        print("Rien à corriger : aucune contradiction entre un lieu et sa ville dans ce "
              "périmètre.")
        if args.slack:
            print("(--slack : rien à signaler, aucun message envoyé.)")
        conn.close()
        return 0

    if registre:
        if args.apply:
            n = 0
            for r, _phrase, attendue in registre:
                conn.execute("UPDATE events_raw SET ville=?, venue_source='registre' "
                             "WHERE id=?", (attendue, r["id"]))
                n += 1
            conn.commit()
            # RECOMPTÉ EN BASE, pas sur la longueur de la liste (règle 6) : c'est la
            # seule façon de savoir qu'une écriture a eu lieu.
            ids = [r["id"] for r, _p, _a in registre]
            marques = conn.execute(
                "SELECT COUNT(*) FROM events_raw WHERE venue_source='registre' "
                f"AND id IN ({','.join('?' * len(ids))})", ids).fetchone()[0]
            print(f"✅ {n} correction(s) demandée(s), {marques} vérifiée(s) en base.")
            print("   La fiche LIEU de WordPress ne bouge pas toute seule : republier ces "
                  "événements (`publisher_as --update`) pour que le site suive — "
                  "cs-publish.php remet la ville quand elle vient du registre.")
        else:
            print("— DRY-RUN — relancer avec `--apply` pour appliquer les corrections ① "
                  "ci-dessus (elles seules : ② demande un arbitrage, ③ une confirmation).")

    if args.slack:
        from utils import slack
        msg = [f"*Lieux contredits* — périmètre : {len(confrontables)} fiche(s) avec un "
               f"lieu et une ville, encore devant nous"
               + (", publiées" if args.en_ligne else "") + " :"]
        for r, phrase, _a in registre[:5]:
            msg.append(f"• [{r['id']}] {(r['title'] or '')[:55]} — {phrase}")
        for nom, villes in list(sorted(desac.items()))[:5]:
            msg.append(f"• « {nom} » : "
                       + " / ".join(f"{v} ({len(i)})" for v, i in villes.items()))
        if toponyme:
            msg.append(f"… plus {len(toponyme)} toponyme(s) à confirmer.")
        msg.append("Détail : `.venv/bin/python -m scripts.verifier_lieux"
                   + (" --en-ligne" if args.en_ligne else "") + "`")
        slack.notify("\n".join(msg))

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
