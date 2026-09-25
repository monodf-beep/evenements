#!/usr/bin/env python3
"""Poste sur Slack ce qui arrive sur l'ENTRÉE STANDARD. Rien d'autre.

POURQUOI CE SCRIPT EXISTE. `utils/slack.py` sait poster, mais uniquement depuis du
Python. Le bilan de 11h est produit par `claude -p`, qui écrit son résultat sur la
sortie standard : il manquait le maillon entre les deux.

C'est aussi ce qui permet de tenir la contrainte posée par Franck le 2026-08-03 —
« restreins-le aux outils de la liste allow ». Cette liste ne contient AUCUN moyen de
poster sur Slack, et c'est très bien ainsi : l'agent du matin reste en lecture seule,
sa sortie est du texte, et c'est le CRON qui l'envoie. L'agent ne peut donc pas poster
quelque chose que Franck n'aurait pas vu passer par ce tuyau-là.

Usage :
    ... | .venv/bin/python scripts/slack_send.py [--prefixe "🌅 *Bilan du matin*"]

Sort en 0 si le message est parti, 1 sinon. Une entrée vide n'est PAS une erreur mais
n'envoie rien : un cron muet vaut mieux qu'une notification vide tous les matins.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.slack import enabled, notify  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Poste stdin sur Slack.")
    p.add_argument("--prefixe", default="", help="Ligne de titre ajoutée au-dessus.")
    args = p.parse_args(argv)

    corps = sys.stdin.read().strip()
    if not corps:
        print("Entrée vide — rien à poster.", file=sys.stderr)
        return 0

    if not enabled():
        # On ne perd pas le message : sans webhook, il part au moins dans le journal.
        print("SLACK_WEBHOOK_URL absente — message NON envoyé :", file=sys.stderr)
        print(corps, file=sys.stderr)
        return 1

    texte = f"{args.prefixe}\n{corps}" if args.prefixe else corps
    return 0 if notify(texte) else 1


if __name__ == "__main__":
    raise SystemExit(main())
