#!/usr/bin/env python3
"""Vide la BOÎTE DU JOUR : tous les rapports de la demi-journée en UN message Slack.

D'OÙ ÇA VIENT. Le 2026-08-13 au matin, sept messages sont tombés en deux heures — agent
quotidien, lot de publication, SEO, traduction, bilan, contradicteur de dates,
contradicteur de lieux. Franck : « J'ai trop de messages par jour. Il m'en faut un ou
deux, mais c'est tout. »

Aucun de ces messages n'était de trop pris séparément. C'est leur nombre qui les rend
illisibles, et un canal illisible ne protège plus rien : ce matin-là, le seul 🔴 qui
demandait une décision — 48 fiches que la base croit en ligne et qui ne le sont pas —
est arrivé en cinquième position, entre un rapport SEO et deux contradicteurs à zéro.

COMMENT ÇA MARCHE. `utils/slack.notify` range au lieu d'envoyer dès que `SLACK_DIGEST=1`
est dans l'environnement (posé en tête de crontab.txt). Ce script vide la boîte. Deux
vidages par jour :

    45 11 * * *  → après la chaîne du matin (scraping 8h → contradicteurs 11h35)
    0 20 * * *   → filet du soir, pour tout ce qui est tombé l'après-midi

Ce qui porte un 🔴 remonte en tête du digest : garder l'ordre chronologique
reproduirait exactement le défaut qu'on corrige.

CE QUI NE PASSE PAS PAR LA BOÎTE : `slack.notify(..., urgent=True)`. Aujourd'hui le seul
appelant est le chien de garde (`watchdog_crons`), et c'est délibéré — le vidage est
lui-même un cron, donc si la chaîne est morte le digest ne part pas ; le chien de garde
doit pouvoir aboyer quand tout le reste s'est tu.

Usage :
    .venv/bin/python -m scripts.slack_digest              # vide et poste
    .venv/bin/python -m scripts.slack_digest --titre "🌅 Matin"
    .venv/bin/python -m scripts.slack_digest --voir       # montre sans envoyer ni vider
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import slack  # noqa: E402
from utils.logger import get_logger  # noqa: E402

log = get_logger("slack_digest")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Vide la boîte du jour en un message.")
    parser.add_argument("--titre", default="", help="En-tête du message (facultatif).")
    parser.add_argument("--voir", action="store_true",
                        help="Affiche ce qui attend, sans envoyer ni vider.")
    parser.add_argument("--sans-wordpress", action="store_true",
                        help="N'interroge pas WordPress avant de vider la boîte.")
    args = parser.parse_args(argv)

    if args.voir:
        f = slack._fichier_du_jour()
        if not f.exists():
            print("Boîte vide — rien n'attend d'être envoyé.")
            print("(Si vous attendiez quelque chose : SLACK_DIGEST=1 est-il bien posé "
                  "dans l'environnement des crons ? Sans lui, chaque script poste "
                  "directement, comme avant.)")
            return 0
        lignes = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()
                  if l.strip()]
        print(f"{len(lignes)} rapport(s) en attente dans {f} :")
        for l in lignes:
            marque = " 🔴" if "🔴" in (l.get("texte") or "") else ""
            print(f"  {(l.get('at') or '')[11:16]} · {l.get('source') or '?'}{marque} "
                  f"— {len((l.get('texte') or ''))} caractères")
        return 0

    # LES RAPPORTS DE WORDPRESS, D'ABORD (2026-08-17). Les quatre audits quotidiens
    # écrits en Code Snippets et les refus de cs-completude.php postaient dans
    # #formulaire — le canal réservé au bruit des formulaires publics, que personne ne
    # lit. Ils sont désormais tenus en réserve côté WordPress (route cs/v1/slack-boite)
    # et rapatriés ICI, juste avant le vidage, pour arriver dans CE message.
    # Branché dans le digest plutôt qu'en ligne de crontab à part : une ligne de cron de
    # plus, c'est un passage de plus à surveiller pour un rapport qui n'a de sens que
    # dans ce message-là. Et jamais bloquant — si WordPress ne répond pas, le
    # récapitulatif part quand même, c'est le seul message de la matinée.
    if not args.sans_wordpress:
        try:
            from scripts.rapports_wordpress import collecter
            pris, retires = collecter()
            if pris:
                print(f"{pris} rapport(s) WordPress ajouté(s) au récapitulatif "
                      f"({retires} retiré(s) de WordPress).")
        except Exception as exc:  # noqa: BLE001 — le digest ne doit jamais tomber pour ça
            log.warning("Rapports WordPress non récupérés (%s) — digest envoyé sans eux.", exc)

    n, envoye = slack.vider_boite(args.titre)
    # RÈGLE 6 — on rapporte le RÉSULTAT, jamais l'intention. « 0 » a deux causes ici
    # (rien à dire, ou boîte jamais alimentée) : on les distingue.
    if n == 0:
        print("Boîte vide — aucun message à regrouper. Deux lectures possibles : la "
              "matinée n'a rien produit, ou SLACK_DIGEST n'était pas posé et les "
              "scripts ont posté eux-mêmes. `--voir` et logs/slack/ tranchent.")
        log.info("Boîte vide.")
        return 0
    print(f"{n} rapport(s) regroupé(s) — {'envoyé' if envoye else 'ÉCHEC D’ENVOI, '
                                          'contenu remis en boîte pour le prochain vidage'}.")
    log.info("Digest : %d rapport(s), envoyé=%s", n, envoye)
    return 0 if envoye else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
