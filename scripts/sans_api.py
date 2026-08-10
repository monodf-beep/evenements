#!/usr/bin/env python3
"""Tout ce que la chaîne sait faire SANS le moindre appel de modèle.

Le plafond API est atteint jusqu'au 2026-09-01. Franck, 2026-08-11 : « on peut faire
tout ce qui est possible sans appel api ? ». Oui, et bien plus qu'il n'y paraît — mais
c'était éparpillé dans six commandes et trois drapeaux, dont personne ne se souvient au
moment où il faudrait s'en servir.

Ce que chaque étape sait faire seule, et pourquoi c'est gratuit :

  1. DATER par le texte et par la page — `dates.py --no-llm`. La passe texte lit le titre
     et la description ; la passe page télécharge l'URL de la fiche et y cherche le
     JSON-LD, les <time> et les motifs de date. Aucun modèle : de l'analyse syntaxique.
  2. TROUVER LE LIEU sans modèle — `venues.py --no-llm`. Appariement sur le référentiel
     de lieux déjà connus et sur le texte.
  3. TROUVER UNE IMAGE sans modèle — `visuals.py --sans-llm`. L'og:image de la page
     officielle et la photo de page ne coûtent rien ; seules la recherche Commons et la
     vérification vision appellent un modèle, et on les saute.
  4. PUBLIER ce qui est devenu complet — `publish_batch_as`. La publication n'a JAMAIS
     eu besoin d'un modèle : elle assemble et envoie. C'est l'étape qui transforme le
     travail des trois précédentes en pages réellement en ligne.

L'ORDRE N'EST PAS DÉCORATIF : la publication exige date + lieu + image (porte qualité de
utils/completeness). Publier avant d'avoir daté ne publierait rien. C'est aussi pourquoi
ce script existe plutôt qu'une liste de commandes dans un message : l'ordre se perd, pas
un script.

RÈGLE 6 — le bilan est RECOMPTÉ en base, avant/après, champ par champ. Jamais « N fiches
traitées » : combien ont GAGNÉ une date, un lieu, une image, et combien sont réellement
passées en ligne.

RÈGLE 4 — dry-run par défaut : la liste des étapes et le nombre de fiches concernées,
sans rien lancer.

Exemples :
  .venv/bin/python -m scripts.sans_api                 # simulation
  .venv/bin/python -m scripts.sans_api --apply
  .venv/bin/python -m scripts.sans_api --apply --sans-publication
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
from utils.logger import get_logger  # noqa: E402

log = get_logger("sans_api")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _etat(conn, today: str) -> dict:
    """Photographie des manques, sur le seul périmètre qui compte (règle 5 : à venir,
    en cours, récurrent, ou sans date — une date absente n'est pas un événement fini)."""
    devant = ("statut IN ('evaluated','published_cs','published_sub') "
              "AND duplicate_of IS NULL AND COALESCE(translation_of,0)=0 "
              "AND (COALESCE(recurring,0)=1 OR COALESCE(NULLIF(date_event_end,''), "
              "     NULLIF(date_event_start,''), '9999') >= ?)")
    q = lambda cond: conn.execute(  # noqa: E731
        f"SELECT COUNT(*) FROM events_raw WHERE {devant} AND {cond}", (today,)).fetchone()[0]
    return {
        "sans_date": q("COALESCE(date_event_start,'')='' AND COALESCE(recurring,0)=0"),
        "sans_lieu": q("COALESCE(lieu,'')='' AND COALESCE(multi_lieux,0)=0"),
        "sans_image": q("COALESCE(url_image,'')=''"),
        "en_ligne": q("wp_post_id_as IS NOT NULL"),
    }


def _diff(avant: dict, apres: dict) -> list[str]:
    lignes = []
    for cle, libelle in (("sans_date", "ont gagné une date"),
                         ("sans_lieu", "ont gagné un lieu"),
                         ("sans_image", "ont gagné une image")):
        gagne = avant[cle] - apres[cle]
        lignes.append(f"  {gagne:4} {libelle:22} ({avant[cle]} → {apres[cle]} sans)")
    mises = apres["en_ligne"] - avant["en_ligne"]
    lignes.append(f"  {mises:4} {'mises en ligne':22} ({avant['en_ligne']} → "
                  f"{apres['en_ligne']} publiées)")
    return lignes


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Fait avancer la chaîne sans aucun appel LLM.")
    p.add_argument("--apply", action="store_true", help="Exécute (sinon simulation).")
    p.add_argument("--sans-publication", action="store_true",
                   help="S'arrête avant la publication (compléter seulement).")
    p.add_argument("--cap", type=int, default=50,
                   help="Nb max de fiches publiées par run (défaut 50).")
    args = p.parse_args(argv)

    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    avant = _etat(conn, today)
    conn.close()

    print("═══ Ce qui manque aujourd'hui, sur ce qui est encore devant nous ═══\n")
    print(f"  {avant['sans_date']:4} sans date       → passes texte et page (aucun modèle)")
    print(f"  {avant['sans_lieu']:4} sans lieu       → appariement sur les lieux connus")
    print(f"  {avant['sans_image']:4} sans image      → og:image, photo de page, bannière")
    print(f"  {avant['en_ligne']:4} déjà en ligne\n")

    if not args.apply:
        print("Simulation — rien n'a été lancé. Les étapes qui SERAIENT exécutées :")
        print("  1. dates.py --no-llm        (texte + page)")
        print("  2. venues.py --no-llm       (référentiel de lieux)")
        print("  3. visuals.py --sans-llm    (og:image + bannière)")
        if not args.sans_publication:
            print(f"  4. publish_batch_as --cap {args.cap}  (ce qui est devenu complet)")
        print("\nAjouter --apply pour exécuter. Aucun appel modèle dans aucune étape.")
        return 0

    # Chaque étape est isolée : un plantage à l'étape 2 ne doit pas priver l'étape 3 de
    # son tour. Le pipeline entier tombait autrefois sur une seule exception.
    etapes = [
        ("datation (texte + page)", "scripts.dates", ["--no-llm", "--no-republish"]),
        ("lieux (référentiel)", "scripts.venues", ["--no-llm"]),
        ("images (og + bannière)", "scripts.visuals", ["--sans-llm"]),
    ]
    if not args.sans_publication:
        etapes.append(("publication", "scripts.publish_batch_as", ["--cap", str(args.cap)]))

    for libelle, module, argv_etape in etapes:
        print(f"\n──── {libelle} ────")
        try:
            mod = __import__(module, fromlist=["main"])
            code = mod.main(argv_etape)
            log.info("%s : code %s", libelle, code)
        except Exception as exc:  # noqa: BLE001 — une étape ratée n'annule pas les autres
            log.error("%s : ÉCHEC (%s) — les étapes suivantes continuent : %s",
                      libelle, type(exc).__name__, exc)

    # RÈGLE 6 : on recompte en base, on n'additionne pas des intentions.
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apres = _etat(conn, today)
    conn.close()
    print("\n═══ Résultat RECOMPTÉ en base ═══\n")
    for ligne in _diff(avant, apres):
        print(ligne)
    if avant == apres:
        # Le dire franchement plutôt que d'afficher quatre zéros sans commentaire : un run
        # sans effet est une information, souvent la plus utile.
        print("\nRien n'a bougé. Ce qui reste demande soit un modèle, soit une décision "
              "humaine — voir scripts/audit_incomplets.py pour savoir laquelle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
