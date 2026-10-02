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
        # UNE BANNIÈRE N'EST PAS UNE PHOTO (corrigé le 2026-08-11, le soir même où le
        # bilan m'a fait dire une demi-vérité). Le premier run annonçait « 57 ont gagné
        # une image » — dont QUARANTE bannières de territoire, c'est-à-dire l'image
        # générique que Franck avait déjà reprochée au pipeline le 2026-08-09 : « là
        # j'ai de nouveau une image fallback ». Compter ensemble une affiche d'événement
        # et un visuel générique, c'est exactement le « rapporter l'intention plutôt que
        # le résultat » de la règle 6. Les deux sont désormais séparés.
        "banniere": q("COALESCE(image_source,'')='banner'"),
        "vraie_photo": q("COALESCE(url_image,'')<>'' AND "
                         "COALESCE(image_source,'') NOT IN ('', 'banner')"),
        "en_ligne": q("wp_post_id_as IS NOT NULL"),
    }


def _diff(avant: dict, apres: dict) -> list[str]:
    lignes = []
    for cle, libelle in (("sans_date", "ont gagné une date"),
                         ("sans_lieu", "ont gagné un lieu")):
        gagne = avant[cle] - apres[cle]
        lignes.append(f"  {gagne:4} {libelle:26} ({avant[cle]} → {apres[cle]} sans)")
    # Deux lignes séparées, jamais une seule : une vraie photo et une bannière générique
    # ne valent pas la même chose pour le lecteur, et les additionner flatte le bilan.
    lignes.append(f"  {apres['vraie_photo'] - avant['vraie_photo']:4} "
                  f"{'ont gagné une VRAIE photo':26} (og:image ou photo de page)")
    lignes.append(f"  {apres['banniere'] - avant['banniere']:4} "
                  f"{'ont reçu une BANNIÈRE':26} (générique, faute de mieux — "
                  f"{apres['banniere']} au total)")
    mises = apres["en_ligne"] - avant["en_ligne"]
    lignes.append(f"  {mises:4} {'mises en ligne':26} ({avant['en_ligne']} → "
                  f"{apres['en_ligne']} publiées)")
    if apres["banniere"] > avant["banniere"]:
        lignes.append("")
        lignes.append("  ⚠️ Une bannière n'est pas une illustration de l'événement, c'est")
        lignes.append("     un pis-aller. Ces fiches restent candidates à une vraie photo :")
        lignes.append("     visuals.py les reprendra quand la page officielle sera")
        lignes.append("     joignable ou quand la recherche d'image redeviendra possible.")
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
    print(f"  {avant['banniere']:4} sur bannière    → générique : une vraie photo reste "
          f"à trouver")
    print(f"  {avant['en_ligne']:4} déjà en ligne\n")

    if not args.apply:
        print("Simulation — rien n'a été lancé. Les étapes qui SERAIENT exécutées :")
        print("  1. moisson_officielle       (date+lieu+ville+image, UNE lecture)")
        print("  2. dates.py --no-llm        (texte + page)")
        print("  3. venues.py --no-llm       (référentiel de lieux)")
        print("  4. visuals.py --sans-llm    (og:image + bannière)")
        if not args.sans_publication:
            print(f"  5. publish_batch_as --cap {args.cap}  (ce qui est devenu complet)")
        print("\nAjouter --apply pour exécuter. Aucun appel modèle dans aucune étape.")
        return 0

    # Chaque étape est isolée : un plantage à l'étape 2 ne doit pas priver l'étape 3 de
    # son tour. Le pipeline entier tombait autrefois sur une seule exception.
    etapes = [
        # EN PREMIER, et c'est le point de Franck du 2026-08-11 : une page officielle lue
        # UNE fois donne la date, le lieu, la ville et l'image d'un coup — alors que les
        # trois passes ci-dessous la relisent chacune pour un seul champ, chacune derrière
        # son propre délai de carence. Ce qui vient de la source officielle doit être
        # récolté avant tout le reste ; les passes suivantes ne traitent alors plus que
        # ce que la page n'a pas donné.
        ("moisson de la page officielle", "scripts.moisson_officielle",
         ["--apply", "--cap", "150"]),
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
