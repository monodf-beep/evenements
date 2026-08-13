#!/usr/bin/env python3
"""AUDIT (LECTURE SEULE) — combien de fiches DÉJÀ PUBLIÉES sont sous le plancher de
substance (utils/substance.py, portillon posé le 2026-08-05 après le refus AdSense).

Le portillon dans scripts/publish_batch_as.py ne bloque que les CRÉATIONS : une fiche
maigre déjà en ligne continue de s'afficher telle quelle (bloquer sa republication ne
la retirerait pas du site, ça y figerait une version plus ancienne). Le commit qui l'a
posé (1d50aac) le dit noir sur blanc : « Ne règle pas les 59 fiches déjà en ligne :
elles demandent un enrichissement ou une dépublication, décision par décision. » Ce
script est cette liste — pour ne plus les découvrir une par une en furetant dans
WordPress (cf. le cas Saint-Ours/WP#2174, trouvé ainsi le 2026-08-06).

CE SCRIPT N'ÉCRIT RIEN. La base est ouverte en lecture seule (`mode=ro`). Ne fait
aucun appel réseau : `build_post` est pure (elle lit le dictionnaire, ne télécharge
rien), donc mesurer 300+ fiches ne coûte ni LLM ni HTTP.

Trois paniers, pour la même raison que le portillon lui-même :
  1. SOUS LE PLANCHER (< 120 mots, PUBLISH_MIN_MOTS) et ENCORE DEVANT NOUS — le cas
     indéfendable, à traiter en priorité : scripts.repair_substance les répare en lot.
  2. BANDE MAIGRE (120-250 mots) — publiable, mais maigre : à surveiller, pas urgent.
  3. MAIGRES MAIS PASSÉES — comptées à part depuis le 2026-08-11 (règle 5). Ce script
     annonçait « 108 sous le plancher » sans faire le tri, et ce chiffre a servi trois
     jours à décrire l'état du site : il y en a SEIZE encore devant nous. Les autres
     concernent des événements terminés, qui ne seront pas republiés — les réparer
     coûterait 0,33 $ pièce pour personne.

Pour aider à choisir enrichir vs dépublier : `jamais enrichie` (article_title vide)
signale une fiche qui n'a JAMAIS eu de vrai article — la réparation naturelle est de
l'enrichir. Une fiche qui a UN article mais reste sous le plancher a un problème plus
profond (rédaction trop courte malgré la matière) — vérifier la matière avant de
relancer scripts.enrich pour rien.

Usage sur le VPS :
    cd /root/evenements && .venv/bin/python -m scripts.audit_substance_published
    cd /root/evenements && .venv/bin/python -m scripts.audit_substance_published --ids
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
from utils import substance  # noqa: E402
from scripts.publisher import build_post  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _connect_ro(path: Path) -> sqlite3.Connection:
    """Connexion STRICTEMENT en lecture (URI `mode=ro`) : garantie par SQLite lui-même,
    pas par la discipline du code — ce script tourne sur la base de production."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def devant_nous(ev: dict, today: str) -> bool:
    """L'événement est-il encore devant nous ? Au niveau module pour être TESTABLE : la
    frontière passé/à-venir décide de ce qu'on répare et de ce qu'on paie, elle mérite sa
    fixture (tests/test_audit_substance_published.py)."""
    if ev.get("recurring"):
        return True                       # pas de date unique : jamais « passé »
    fin = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()
    return not fin or fin[:10] >= today   # sans date = donnée manquante, pas un événement fini


def _article_de(ev: dict) -> dict:
    """L'article rédigé d'une fiche, ou {} — sans jamais lever sur un JSON abîmé."""
    try:
        return (json.loads(ev.get("enrich_data") or "") or {}).get("article") or {}
    except (ValueError, TypeError):
        return {}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit LECTURE SEULE des fiches PUBLIÉES sous le plancher de substance.")
    parser.add_argument("--ids", action="store_true",
                        help="Lister les ids/titres, pas seulement les compteurs.")
    parser.add_argument("--limit", type=int, default=80,
                        help="Nombre de lignes détaillées par panier (défaut 80).")
    args = parser.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n"
              f"(data/ est hors dépôt Git — lancer ce script sur le VPS.)")
        return 1

    conn = _connect_ro(DB_PATH)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL").fetchall()]
    conn.close()

    # RÈGLE 5, AJOUTÉE LE 2026-08-11 — ce script annonçait « 108 fiches sous le plancher »
    # sans distinguer le passé de l'à-venir. Le chiffre a servi trois jours de suite à
    # décrire l'état du site, et il était trompeur : scripts/repair_substance.py, écrit
    # avec le filtre, en a trouvé SEIZE encore devant nous. Les 92 autres concernent des
    # événements terminés — réparer leur article ne servirait personne, et coûterait
    # 0,33 $ pièce. C'est exactement le reproche fait à audit_dedupe_damage le 2026-08-03 :
    # « un rapport qui mélange passé et à-venir FABRIQUE du travail au lieu d'en désigner ».
    # Le passé n'est pas supprimé du rapport, il est COMPTÉ À PART : une fiche maigre
    # toujours en ligne reste une fiche maigre en ligne, mais elle ne se répare pas.
    today = date.today().isoformat()

    plancher = substance.plancher()
    sous_plancher, bande_maigre, passees = [], [], []
    # QUATRIÈME PANIER, AJOUTÉ LE 2026-08-13 : les fiches publiées SANS ARTICLE RÉDIGÉ.
    # Ce script mesure une LONGUEUR ; il ne regardait pas la PROVENANCE du texte. Or
    # `publisher.build_post` a un repli explicite — « article non enrichi → description
    # brute » — qui publie le texte de la SOURCE dans un simple <p>. Une description de
    # trois cents mots passe donc le plancher sans qu'une ligne ait été écrite par nous.
    #
    # Découvert en cherchant pourquoi `panel_rattrapage` en écartait 23 avec « aucun
    # article en base ». Elles cumulent deux défauts qui se renforcent : c'est exactement
    # le contenu qu'AdSense a qualifié de « faible valeur informative » le 2026-08-05, et
    # elles sont INVISIBLES à tout notre appareil de contrôle, qui lit `enrich_data`.
    # Visibles du public, invisibles de nous.
    #
    # Compté à part et NON mélangé aux maigres : une fiche peut être longue ET non
    # rédigée. Ce sont deux questions différentes, et les confondre referait le défaut de
    # périmètre que ce fichier documente déjà trois paragraphes plus haut.
    sans_article = []
    for ev in rows:
        if not ((_article_de(ev) or {}).get("corps") or "").strip():
            sans_article.append((ev, substance.mots_publies(ev, build_post)))
        n = substance.mots_publies(ev, build_post)
        if n >= substance.BANDE_MAIGRE:
            continue
        if not devant_nous(ev, today):
            passees.append((ev, n))
        elif n < plancher:
            sous_plancher.append((ev, n))
        else:
            bande_maigre.append((ev, n))
    sous_plancher.sort(key=lambda t: t[1])  # les plus maigres d'abord

    jamais_enrichies = sum(1 for ev, _ in sous_plancher if not (ev.get("article_title") or "").strip())
    # RÈGLE 5 ici aussi : une fiche non rédigée dont l'événement est passé ne sera pas
    # republiée. Elle reste en ligne, donc elle est comptée — mais à part.
    sans_article_vivantes = [t for t in sans_article if devant_nous(t[0], today)]
    # Le panier 1 et le panier 4 se RECOUVRENT largement : une fiche jamais enrichie est
    # à la fois maigre et non rédigée. Additionner les deux fabriquerait du travail qui
    # n'existe pas (règle 6). On isole donc ce que le panier 4 apporte VRAIMENT : les
    # fiches assez longues pour passer tous les contrôles, mais dont pas une ligne n'est
    # de nous. Celles-là, aucune commande de ce script ne les visait.
    _deja = {ev["id"] for ev, _ in sous_plancher}
    sans_article_seules = [t for t in sans_article_vivantes if t[0]["id"] not in _deja]

    print("=" * 78)
    print("AUDIT « substance publiée » — lecture seule, rien n'a été modifié")
    print("=" * 78)
    print(f"Base                                     : {DB_PATH}")
    print(f"Fiches publiées (wp_post_id_as)          : {len(rows)}")
    print(f"Plancher (PUBLISH_MIN_MOTS)               : {plancher} mots")
    print()
    print(f"1. SOUS LE PLANCHER (< {plancher} mots), ENCORE DEVANT NOUS : {len(sous_plancher)}"
          + (f"  ({100 * len(sous_plancher) / len(rows):.1f} % du site)" if rows else ""))
    print(f"   · dont jamais enrichies (article_title vide) : {jamais_enrichies}")
    print(f"   · réparation en lot : .venv/bin/python -m scripts.repair_substance")
    print(f"2. BANDE MAIGRE ({plancher}-{substance.BANDE_MAIGRE} mots), publiable mais maigre : {len(bande_maigre)}")
    print(f"3. MAIGRES MAIS PASSÉES (comptées à part, NON réparables) : {len(passees)}")
    print(f"   L'événement a eu lieu : la fiche ne sera pas republiée, plus aucun visiteur")
    print(f"   ne la cherche. Les réparer coûterait ~{0.33 * len(passees):.0f} $ pour rien.")
    # RÈGLE 6 — le périmètre s'écrit À CÔTÉ du nombre. Celui-ci se compare mal avec les
    # « 23 sans article » de `panel_rattrapage`, qui ne regarde que les fiches VIVANTES
    # (à venir, en cours, récurrentes) : deux périmètres, pas deux mesures qui se
    # contredisent. Sans cette ligne, c'est le plus gros des deux qu'on croira.
    print(f"4. PUBLIÉES SANS ARTICLE RÉDIGÉ : {len(sans_article)} sur les {len(rows)} "
          f"publiées, toutes dates confondues,")
    print(f"   dont {len(sans_article_vivantes)} encore devant nous — ce sont celles-là "
          f"qui se réparent,")
    print(f"   et parmi elles {len(sans_article_seules)} qu'AUCUNE commande ne visait "
          f"(les {len(sans_article_vivantes) - len(sans_article_seules)} autres sont déjà")
    print(f"   comptées au panier 1 — être maigre et n'être pas rédigée va souvent ensemble).")
    print(f"   C'est la DESCRIPTION BRUTE de la source qui s'affiche (repli de")
    print(f"   publisher.build_post), pas notre rédaction — quelle que soit sa longueur.")
    print(f"   Ces fiches échappent AUSSI au panel de lecteurs et à tout contrôle qui lit")
    print(f"   enrich_data : visibles du public, invisibles de nous.")
    print()

    if args.ids:
        def _dump(titre: str, lot: list[tuple[dict, int]]) -> None:
            print(f"--- {titre} ({len(lot)}) ---")
            for ev, n in lot[:args.limit]:
                wp = f"WP#{ev['wp_post_id_as']}"
                enrichie = "" if (ev.get("article_title") or "").strip() else " · JAMAIS ENRICHIE"
                print(f"  [{ev['id']:>5}] {wp:<10} {n:>4} mot(s){enrichie:<20} "
                      f"{(ev.get('title') or '')[:55]}")
            if len(lot) > args.limit:
                print(f"  … et {len(lot) - args.limit} autre(s)")
            print()
        _dump("SOUS LE PLANCHER, à réparer en priorité", sous_plancher)
        _dump("BANDE MAIGRE (publiable, à surveiller)", bande_maigre)
        _dump("SANS ARTICLE RÉDIGÉ mais AU-DESSUS du plancher — hors panier 1",
              sans_article_seules)

    if sans_article_seules:
        ids = " ".join(str(ev["id"]) for ev, _ in sans_article_seules[:50])
        print(f"CES {len(sans_article_seules)} FICHES-LÀ passent le plancher — avec le texte de la")
        print("source. Aucune commande de ce script ne les visait : le panier 1 ne les")
        print("voit pas (elles sont assez longues) et le panier 2 n'en propose aucune.")
        print(f"      .venv/bin/python -m scripts.enrich {ids}")
        print("      puis : .venv/bin/python -m scripts.publish_batch_as --ids " + ids)
        print()

    if sous_plancher:
        ids = " ".join(str(ev["id"]) for ev, _ in sous_plancher[:50])
        print("RIEN N'A ÉTÉ MODIFIÉ. Deux réparations possibles, décision par décision :")
        print("  • ENRICHIR (la fiche gagnera un vrai article, puis repart au republish) :")
        print(f"      .venv/bin/python -m scripts.enrich {ids}")
        print("      puis : .venv/bin/python -m scripts.publish_batch_as --ids " + ids)
        print("  • DÉPUBLIER (corbeille WordPress, réversible ; dry-run par défaut, "
              "--apply pour agir) :")
        print(f"      .venv/bin/python -m scripts.trash_by_ids {ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
