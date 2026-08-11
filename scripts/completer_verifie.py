#!/usr/bin/env python3
"""Pose les valeurs VÉRIFIÉES et écarte ce qui n'a rien à faire dans l'agenda.

Franck, 2026-08-11, trois fois dans l'après-midi : « donc on avance pas ? », « pour
l'instant ça avance toujours pas ». La pastille « À compléter » était à 68 le matin et à
67 le soir, après quatre correctifs poussés en production. Tous justes, tous mesurés,
tous sans effet sur son écran — j'optimisais des passes automatiques alors que la file
contenait surtout des fiches qu'AUCUNE passe ne peut servir.

La lecture des 67, une par une, l'a montré :

  • 26 n'ont aucune page lisible — 16 viennent d'un mail (« gmail:… »), 8 pointent vers
    un lien de TRAÇAGE de newsletter (sendibm1, musvc6, marketingcloud) au lieu de la
    page de l'événement, 2 sont des traductions mal marquées ;
  • ~14 ne relèvent pas de la charte — le CCAS de La Ravoire (« gestes qui sauvent »,
    « le sommeil », « visite du stade »), trois congrès, quatre billets de BLOG du
    Circolo dei Lettori dont l'adresse contient « /blog/ » ;
  • et une poignée attendait une donnée que j'avais déjà vérifiée le matin même, pour
    répondre aux doutes de la file « À vérifier ».

Ce script fait ce dernier tiers, qui est le seul à pouvoir bouger aujourd'hui. Il n'est
pas un extracteur de plus : les valeurs sont écrites en dur, chacune avec la source qui
la prouve, parce qu'elles ont été vérifiées à la main et qu'aucun automatisme ne les
aurait trouvées.

CE QU'IL RESPECTE
  • dry-run par défaut (règle 4) ;
  • il n'écrase RIEN : un champ déjà rempli est laissé tel quel, et il le dit ;
  • « écarter » = `statut='rejected'`, c'est-à-dire la même chose que le bouton du
    back-office : une RE-CLASSIFICATION réversible, aucune ligne supprimée ;
  • le bilan est recompté en base après écriture (règle 6).

  .venv/bin/python -m scripts.completer_verifie            # simulation
  .venv/bin/python -m scripts.completer_verifie --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
COMMUNES = ROOT / "config" / "communes_comte_de_nice.json"

# ── Valeurs vérifiées à la main, avec la source qui les prouve ───────────────────────
# Rien ici ne vient d'une déduction : chaque ligne a été ouverte et lue. La source est
# gardée pour qu'un désaccord futur se règle en rouvrant la page, pas en me croyant.
_VALEURS: dict[int, tuple[dict, str]] = {
    4621: ({"lieu": "Teatro Regio"},
           "torinofilmfest.org — la soirée d'ouverture du 44e TFF a lieu au Teatro Regio"),
    3280: ({"ville": "Torino"}, "teatroregio.torino.it — le Teatro Regio est à Turin"),
    3279: ({"ville": "Torino"}, "basilicadisuperga.org — Superga est sur la commune de Turin"),
    4564: ({"lieu": "Polo Espositivo ARCA", "ville": "Vercelli"},
           "visitvalsesiavercelli.it — l'ARCA est l'ancienne église San Marco, à Verceil"),
    4705: ({"lieu": "Citadelle Saint-Elme", "ville": "Villefranche-sur-Mer"},
           "villefranche-sur-mer.fr — cinéma de plein air à la Citadelle"),
    4720: ({"ville": "Villefranche-sur-Mer"}, "site de la commune de Villefranche-sur-Mer"),
    4721: ({"ville": "Villefranche-sur-Mer"}, "site de la commune de Villefranche-sur-Mer"),
    4722: ({"ville": "Villefranche-sur-Mer"}, "site de la commune de Villefranche-sur-Mer"),
    4723: ({"ville": "Villefranche-sur-Mer"}, "site de la commune de Villefranche-sur-Mer"),
    3948: ({"date_event_start": "2026-06-03", "date_event_end": "2026-09-13"},
           "lavenaria.it — Milo Manara, Il nome della rosa, 3 juin au 13 septembre 2026"),
}

# ── Fiches à écarter, et POURQUOI (le motif est la moitié de la décision) ────────────
_ECARTS: dict[int, str] = {
    # Événements TERMINÉS, que leur absence de date empêchait de classer (règle 5).
    3082: "Nice Jazz Fest : 23-25 juillet 2026, terminé",
    3094: "Guitare en Scène : la date citée était le 18 juillet 2026, terminé",
    # PAS DES ÉVÉNEMENTS — billets de blog du Circolo dei Lettori. Leur adresse contient
    # « /blog/ », et la 2676 n'a même pas de titre. La charte §3 est explicite : n'est pas
    # un événement ce à quoi on ne peut pas assister à une date.
    218: "billet de blog du Circolo dei Lettori, pas un événement",
    219: "billet de blog du Circolo dei Lettori, pas un événement",
    227: "billet de blog du Circolo dei Lettori (« blog-marginalia »), pas un événement",
    2676: "page de blog du Circolo dei Lettori, sans même un titre",
    # CONGRÈS ET B2B — charte : « un congrès, un colloque scientifique ou un salon B2B
    # n'a pas sa place, même ouvert à tous ». C'est le PUBLIC VISÉ qui décide.
    3089: "IASP World Conference — congrès professionnel (et Sophia Antipolis est dans "
          "l'arrondissement de Grasse)",
    3090: "Talent in Tech — rencontre professionnelle",
    3091: "Colloque International Villes et Santé Mentale — colloque scientifique",
    # ACTION SOCIALE MUNICIPALE (La Ravoire). Public visé : les administrés d'une commune,
    # pas un public culturel. « Récital chant et piano » (4658) est GARDÉ : celui-là est
    # bien un événement culturel, et la frontière se trace là.
    4657: "La Ravoire — fête de rentrée municipale",
    4659: "La Ravoire — sensibilisation aux gestes qui sauvent, action de prévention",
    4660: "La Ravoire — thé dansant du CCAS",
    4661: "La Ravoire — atelier « bien vivre à domicile », action sociale",
    4662: "La Ravoire — visite d'équipement municipal",
    4663: "La Ravoire — conférence santé « le sommeil », action de prévention",
}


def _norm(s: str) -> str:
    n = unicodedata.normalize("NFKD", (s or "").strip().lower())
    return " ".join("".join(c for c in n if not unicodedata.combining(c)).split())


def _communes_grasse() -> set[str]:
    """Les 62 communes de l'arrondissement de Grasse — HORS PÉRIMÈTRE.

    Arbitrage Franck confirmé le 2026-08-11 : « hors périmètre », sans nuance. La charte
    le disait déjà (« pas seulement sans étiquette »), le fichier de configuration disait
    l'inverse ; c'est le fichier qui avait tort, il a été corrigé le même jour."""
    d = json.loads(COMMUNES.read_text(encoding="utf-8"))
    return {_norm(c) for c in d["arrondissement_de_grasse"]}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="écrit (défaut : simulation)")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    grasse = _communes_grasse()

    # ── 1. Les valeurs vérifiées ────────────────────────────────────────────────────
    print("═══ Valeurs vérifiées à poser ═══\n")
    a_ecrire: list[tuple[int, dict, str]] = []
    for eid, (champs, source) in _VALEURS.items():
        row = conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone()
        if row is None:
            print(f"  [{eid:5}] introuvable en base — ignorée")
            continue
        # ON N'ÉCRASE JAMAIS : si Franck a rempli le champ entre-temps, sa valeur gagne.
        neufs = {c: v for c, v in champs.items() if not (row[c] or "").strip()}
        deja = {c: row[c] for c in champs if (row[c] or "").strip()}
        if deja:
            print(f"  [{eid:5}] déjà rempli, laissé tel quel : {deja}")
        if neufs:
            a_ecrire.append((eid, neufs, source))
            detail = ", ".join(f"{c}={v}" for c, v in neufs.items())
            print(f"  [{eid:5}] {detail}\n          ↳ {source}")

    # ── 2. Les écarts nommés ────────────────────────────────────────────────────────
    print(f"\n═══ À écarter (statut « rejeté », réversible) ═══\n")
    a_ecarter: list[tuple[int, str]] = []
    for eid, motif in _ECARTS.items():
        row = conn.execute("SELECT id, statut, title FROM events_raw WHERE id=?",
                           (eid,)).fetchone()
        if row is None or row["statut"] == "rejected":
            continue
        a_ecarter.append((eid, motif))
        print(f"  [{eid:5}] {motif}\n          {(row['title'] or '')[:74]}")

    # ── 3. L'arrondissement de Grasse, par la RÈGLE et non par une liste d'identifiants
    # Écrire les numéros à la main aurait raté celles qui arrivent demain. La règle, elle,
    # vaut pour toutes les collectes futures.
    print(f"\n═══ Hors périmètre : arrondissement de Grasse ═══\n")
    for row in conn.execute(
            "SELECT id, ville, title FROM events_raw WHERE COALESCE(ville,'') <> '' "
            "AND statut NOT IN ('rejected','merged')"):
        if _norm(row["ville"]) not in grasse:
            continue
        a_ecarter.append((row["id"], f"{row['ville']} — arrondissement de Grasse"))
        print(f"  [{row['id']:5}] {row['ville']:<24} {(row['title'] or '')[:56]}")

    if not args.apply:
        print(f"\nSimulation — RIEN n'a été écrit."
              f"\n{len(a_ecrire)} fiche(s) recevraient une valeur, "
              f"{len(a_ecarter)} seraient écartées. Ajouter --apply.")
        conn.close()
        return 0

    for eid, neufs, _ in a_ecrire:
        sets = ", ".join(f"{c}=?" for c in neufs)
        conn.execute(f"UPDATE events_raw SET {sets} WHERE id=?", (*neufs.values(), eid))
    for eid, _ in a_ecarter:
        conn.execute("UPDATE events_raw SET statut='rejected' WHERE id=?", (eid,))
    conn.commit()

    # RECOMPTÉ EN BASE, et sur le périmètre EXACT de la pastille (règle 6) : c'est le
    # seul nombre qui répond à « est-ce que ça avance ? ».
    from scripts.lister_a_completer import _clause
    from datetime import date
    where, params = _clause(date.today().isoformat())
    reste = conn.execute(f"SELECT COUNT(*) FROM events_raw WHERE {where}",
                         params).fetchone()[0]
    rejetees = conn.execute("SELECT COUNT(*) FROM events_raw WHERE statut='rejected'"
                            ).fetchone()[0]
    conn.close()
    print(f"\n✅ {len(a_ecrire)} fiche(s) complétées, {len(a_ecarter)} écartées.")
    print(f"   La file « À compléter » contient maintenant {reste} fiche(s) "
          f"— même périmètre que la pastille du back-office.")
    print(f"   {rejetees} fiche(s) rejetées au total en base (rien n'est supprimé : "
          f"un rejet se défait).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
