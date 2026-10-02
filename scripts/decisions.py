#!/usr/bin/env python3
"""Le registre des décisions, en ligne de commande — la mémoire partagée des agents.

Pourquoi un CLI : le cerveau de 10h40 et le bilan de 11h n'ont PAS d'outil d'écriture de
fichiers (c'est leur verrou), mais ils savent taper des commandes. Ce script est donc
leur seule porte vers le registre — et le bilan n'est autorisé qu'à `--liste` (son
harnais borne le motif de commande), pour que le contrôleur ne puisse pas amender la
mémoire de l'acteur qu'il contrôle.

Usage :
    .venv/bin/python -m scripts.decisions --liste
    .venv/bin/python -m scripts.decisions --signaler fiche-4839 \
        --titre "Coro & Bentu : restaurant classé événement" --source bilan_matin \
        --geste "trash_by_ids 4839"
    .venv/bin/python -m scripts.decisions --escalader fiche-4839 --question "…"
    .venv/bin/python -m scripts.decisions --resoudre fiche-4839 \
        --resultat "statut rejected posé, vérifié en base" --par cerveau

Voir utils/decisions.py pour le modèle (journal en ajout seul, réouverture automatique).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import decisions  # noqa: E402


def _lister() -> int:
    tous = decisions.etats()
    ouvertes = decisions.en_attente()
    # LE PÉRIMÈTRE À CÔTÉ DU NOMBRE, toujours : « 0 en attente » sans dénominateur
    # ressemble à un registre jamais alimenté.
    print(f"# Décisions : {len(ouvertes)} en attente sur {len(tous)} enregistrée(s)")
    if not ouvertes:
        return 0
    print()
    print("| Clé | Depuis | Vues | Escaladée | Réouv. | Titre |")
    print("|---|---|---|---|---|---|")
    for e in ouvertes:
        print(f"| {e['cle']} | {e['premiere_vue'][:10]} | {e['vues']} "
              f"| {'oui, ' + e['escalade_le'][:10] if e['escalade_le'] else 'non'} "
              f"| {e['reouvertures']} | {e['titre'][:70]} |")
    for e in ouvertes:
        if e["geste"]:
            print(f"\n{e['cle']} — geste proposé : {e['geste']}")
        if e["reouvertures"]:
            print(f"{e['cle']} — ⚠️ ROUVERTE {e['reouvertures']} fois : le correctif "
                  f"précédent n'a pas tenu, ne pas rejouer le même geste sans comprendre.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Registre des décisions (journal en ajout seul).")
    p.add_argument("--liste", action="store_true", help="Les décisions en attente (défaut).")
    p.add_argument("--signaler", metavar="CLE")
    p.add_argument("--escalader", metavar="CLE")
    p.add_argument("--resoudre", metavar="CLE")
    p.add_argument("--titre", default="")
    p.add_argument("--source", default="")
    p.add_argument("--geste", default=None)
    p.add_argument("--question", default="")
    p.add_argument("--resultat", default="")
    p.add_argument("--par", default="")
    args = p.parse_args(argv)

    try:
        if args.signaler:
            if not args.titre or not args.source:
                p.error("--signaler exige --titre et --source : un signalement sans titre "
                        "ni provenance est illisible dans trois jours")
            e = decisions.signaler(args.signaler, args.titre, args.source, args.geste)
            print(f"signalée : {e['cle']} (vue {e['vues']} fois, "
                  f"première le {e['premiere_vue'][:10]})"
                  + (f" — ROUVERTE {e['reouvertures']} fois" if e["reouvertures"] else ""))
        elif args.escalader:
            e = decisions.escalader(args.escalader, args.question)
            print(f"escaladée : {e['cle']} le {e['escalade_le']} — ne plus la re-poser "
                  f"tant qu'elle reste sans réponse, elle est comptée.")
        elif args.resoudre:
            if not args.resultat or not args.par:
                p.error("--resoudre exige --resultat (le constat, pas l'intention — "
                        "règle 6) et --par (qui a agi)")
            e = decisions.resoudre(args.resoudre, args.resultat, args.par)
            print(f"résolue : {e['cle']} par {e['resolution']['par']} — "
                  f"{e['resolution']['resultat']}")
        else:
            return _lister()
    except ValueError as exc:
        print(f"REFUS : {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
