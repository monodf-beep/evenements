#!/usr/bin/env python3
"""Classe un signalement de date SANS SUITE — vérifié, notre date est bonne.

POURQUOI IL FALLAIT ÇA. `verifier_dates` a rendu cinq signalements le 2026-08-11 au soir.
Les cinq ont été vérifiés à la source, les cinq sont bons : Terra Madre (deux fiches, où
c'est le communiqué de la Ville de Turin qui se trompe de jour), la Saint-Ours, Charlie
Winston, et une lettre de GuidaTorino. Sans mémoire, ils réapparaissent demain, après-
demain, en septembre — mot pour mot.

C'est la règle 3 : « un refus qui se rejoue sur la MÊME entrée n'est pas un rouvreur ».
Ici le coût n'est pas en appels d'API, il est pire : une liste qui affiche toujours les
mêmes lignes connues apprend à ne plus être lue, et le jour où une SIXIÈME arrive, personne
ne la voit. Un garde-fou qui crie tous les jours ne garde plus rien.

CE QUI ROUVRE LE CLASSEMENT, et c'est tout l'enjeu — un classement sans suite définitif
serait un cul-de-sac de plus. On enregistre l'EMPREINTE de ce qui a servi à juger : le
texte source ET notre date. Si l'un des deux bouge, le classement tombe de lui-même et le
signalement revient. C'est le même mécanisme que `dates._rearme_matiere_changee`, et c'est
une condition de FAIT, pas un délai : on ne rouvre pas « au bout de trente jours », on
rouvre quand la question a changé.

Concrètement :
  • la source corrige son jour de semaine → l'empreinte change → on re-signale ;
  • quelqu'un modifie la date en base → l'empreinte change → on re-signale ;
  • rien ne bouge → silence, et c'est justifié : la réponse est déjà connue.

  .venv/bin/python -m scripts.classer_sans_suite --liste
  .venv/bin/python -m scripts.classer_sans_suite 3491 2507 \\
      --motif "TorinoClick écrit « vendredi 24 au lundi 27 » ; les vraies bornes de Terra
               Madre 2026 sont un jeudi et un dimanche (slowfood.it). Notre date est juste."
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
MEMOIRE = ROOT / "config" / "dates_classees_sans_suite.json"


def empreinte(materiau: str, debut: str, fin: str) -> str:
    """Ce qui a servi à juger : le texte de la source ET notre date.

    Les deux, parce que le signalement est une CONFRONTATION. Ne garder que le texte
    laisserait passer une date modifiée en base sous un classement qui ne la couvre pas ;
    ne garder que la date laisserait passer une source qui s'est corrigée."""
    brut = f"{(materiau or '').strip()}\x00{debut or ''}\x00{fin or ''}"
    return hashlib.sha1(brut.encode("utf-8", "replace")).hexdigest()[:16]


def charger() -> dict:
    if not MEMOIRE.exists():
        return {}
    try:
        return json.loads(MEMOIRE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def est_classe(eid: int, materiau: str, debut: str, fin: str,
               memoire: dict | None = None) -> dict | None:
    """Le classement tient-il encore ? Renvoie l'entrée, ou None s'il a expiré.

    « Expiré » ne veut pas dire « trop vieux » : ça veut dire que la matière ou la date a
    changé, donc que la question n'est plus la même. Un classement qui expirerait au
    calendrier ferait revenir des signalements déjà tranchés — exactement le bruit qu'on
    cherche à supprimer."""
    m = (memoire if memoire is not None else charger()).get(str(eid))
    if not m:
        return None
    return m if m.get("empreinte") == empreinte(materiau, debut, fin) else None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fiches", nargs="*", type=int, help="identifiants à classer")
    ap.add_argument("--motif", default="", help="POURQUOI notre date est bonne, avec la "
                                                "source qui l'atteste")
    ap.add_argument("--liste", action="store_true", help="montre les classements en cours")
    ap.add_argument("--oublier", nargs="+", type=int, metavar="ID",
                    help="retire un classement (le signalement reviendra)")
    args = ap.parse_args(argv)

    memoire = charger()

    if args.oublier:
        for eid in args.oublier:
            memoire.pop(str(eid), None)
        MEMOIRE.write_text(json.dumps(memoire, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        print(f"{len(args.oublier)} classement(s) retiré(s) — ils reviendront au prochain "
              f"passage de verifier_dates.")
        return 0

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    from scripts.verifier_dates import _materiau

    if args.liste or not args.fiches:
        if not memoire:
            print("Aucun signalement classé sans suite.")
            conn.close()
            return 0
        print(f"═══ {len(memoire)} signalement(s) classé(s) sans suite ═══\n")
        perimes = 0
        for eid, m in sorted(memoire.items(), key=lambda kv: int(kv[0])):
            r = conn.execute("SELECT * FROM events_raw WHERE id=?", (int(eid),)).fetchone()
            if r is None:
                print(f"  [{eid:>5}] fiche disparue — classement sans objet")
                continue
            vivant = est_classe(int(eid), _materiau(r),
                                r["date_event_start"], r["date_event_end"], memoire)
            etat = "actif" if vivant else "PÉRIMÉ — la matière ou la date a changé"
            perimes += 0 if vivant else 1
            print(f"  [{eid:>5}] {(r['title'] or '')[:56]}")
            print(f"          classé le {m.get('le', '?')} · {etat}")
            print(f"          {m.get('motif', '(sans motif)')[:150]}\n")
        # Recompté, et le périmètre écrit à côté (règle 6) : un classement périmé N'EST PAS
        # une anomalie, c'est le mécanisme qui fonctionne — la question a changé.
        print(f"{len(memoire) - perimes} actif(s), {perimes} périmé(s) : ces derniers "
              f"seront re-signalés, c'est voulu.")
        conn.close()
        return 0

    if len(args.motif.strip()) < 30:
        print("Le motif est obligatoire et doit porter la PREUVE, pas un mot. C'est lui "
              "qu'on relira dans six mois pour savoir pourquoi on s'est tu.")
        conn.close()
        return 1

    for eid in args.fiches:
        r = conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone()
        if r is None:
            print(f"  [{eid:>5}] introuvable — ignorée")
            continue
        memoire[str(eid)] = {
            "empreinte": empreinte(_materiau(r), r["date_event_start"],
                                   r["date_event_end"]),
            "motif": args.motif.strip(),
            "le": date.today().isoformat(),
            "titre": (r["title"] or "")[:80],
            "date_alors": f"{r['date_event_start']} → {r['date_event_end']}",
        }
        print(f"  [{eid:>5}] classé sans suite — {(r['title'] or '')[:56]}")

    MEMOIRE.parent.mkdir(parents=True, exist_ok=True)
    MEMOIRE.write_text(json.dumps(memoire, ensure_ascii=False, indent=2), encoding="utf-8")
    conn.close()
    print(f"\n✅ {len(memoire)} classement(s) en mémoire dans {MEMOIRE.name}.")
    print("   Ils reviendront d'eux-mêmes si le texte de la source ou notre date change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
