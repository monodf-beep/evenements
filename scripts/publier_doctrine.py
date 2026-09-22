#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dépose la doctrine Obsidian (voix + vocabulaire interdit) dans WordPress.

POURQUOI
--------
Le coffre Obsidian vit sur le VPS. Le pipeline automatique le lit sans peine
(`utils/voix.py`, `utils/vocabulaire.py` ouvrent un simple dossier), mais une
session Claude tourne dans un conteneur SANS route vers cette machine — ni clé
SSH ni accès réseau direct, vérifié le 2026-09-05. Résultat : à chaque session
de rédaction, Franck doit coller à la main la sortie de deux commandes.

Constat de Franck du 2026-09-06, toujours valable : « c'est pénible quand je
demande de la rédaction ici sur Claude, je dois systématiquement expliquer que
c'est via Obsidian, le ton, la doctrine, le vocabulaire etc. »

Ce script supprime ce geste. Le VPS pousse la doctrine dans WordPress ; la
session la lit par le canal Novamira, qui lui est accessible.

CE QU'IL NE FAIT PAS
--------------------
**Il ne copie RIEN dans le dépôt git.** La doctrine reste dans Obsidian, seule
source ; WordPress n'en tient qu'un reflet daté. C'est la règle que
`scripts/textes_hubs.py` applique déjà pour les anti-patterns, et elle vaut
pour la même raison : deux copies d'une doctrine divergent, et c'est la mauvaise
qu'on croit.

CE QU'IL REFUSE DE FAIRE
------------------------
Publier une doctrine vide ou tronquée. Un miroir vide est PIRE que pas de
miroir : il ressemble à une doctrine qui n'aurait rien à dire, et une session
écrirait sans garde-fou en croyant en avoir un. Un zéro ne dit pas s'il vient
d'un échec ou d'une absence de cas (journal des erreurs du dépôt) — donc le
script compte ce qu'il a lu et s'arrête net si le compte est anormal.

USAGE
-----
    .venv/bin/python scripts/publier_doctrine.py            # publie
    .venv/bin/python scripts/publier_doctrine.py --dry-run  # montre, n'écrit pas

Dans `crontab.txt`, une fois par jour suffit : la doctrine bouge rarement.
Ce script n'est PAS en dry-run par défaut, contrairement aux scripts
destructifs du dépôt : il n'écrit que sur SA page miroir, et un cron qui
n'écrirait rien sans option ne servirait à rien.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TITRE = "Doctrine Obsidian (miroir automatique)"
SLUG = "doctrine-obsidian-miroir"

# Seuils de vraisemblance. Ils ne valident pas le CONTENU — ils attrapent le cas
# où la lecture a échoué en silence et rendu une chaîne vide ou un bout de rien.
MIN_VOIX = 800
MIN_VOCAB = 200


class DoctrineIllisible(RuntimeError):
    """Le coffre n'a pas répondu ce qu'on attendait. On n'écrit pas."""


def lire_doctrine() -> tuple[str, str]:
    """Lit le coffre Obsidian. Lève si le résultat n'est pas vraisemblable."""
    try:
        from utils import voix as m_voix
        from utils import vocabulaire as m_vocab
    except Exception as exc:                       # noqa: BLE001
        raise DoctrineIllisible(
            "modules introuvables ({}) — ce script doit tourner depuis la "
            "racine du dépôt, sur le VPS".format(exc)) from exc

    try:
        texte_voix = (m_voix.load_voix() or "").strip()
    except Exception as exc:                       # noqa: BLE001
        raise DoctrineIllisible("voix.load_voix() a échoué : {}".format(exc)) from exc
    try:
        texte_vocab = (m_vocab.consigne_prompt() or "").strip()
    except Exception as exc:                       # noqa: BLE001
        raise DoctrineIllisible(
            "vocabulaire.consigne_prompt() a échoué : {}".format(exc)) from exc

    if len(texte_voix) < MIN_VOIX:
        raise DoctrineIllisible(
            "la voix ne fait que {} caractères (minimum attendu {}). "
            "OBSIDIAN_VOIX_PATH pointe-t-il au bon endroit ?"
            .format(len(texte_voix), MIN_VOIX))
    if len(texte_vocab) < MIN_VOCAB:
        raise DoctrineIllisible(
            "le vocabulaire ne fait que {} caractères (minimum attendu {}). "
            "OBSIDIAN_VOCAB_PATH pointe-t-il au bon endroit ?"
            .format(len(texte_vocab), MIN_VOCAB))
    return texte_voix, texte_vocab


def composer(texte_voix: str, texte_vocab: str) -> str:
    horodatage = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    interdits = [l for l in texte_vocab.splitlines() if l.strip().startswith("-")]
    return (
        "MIROIR AUTOMATIQUE — NE PAS MODIFIER ICI.\n"
        "La source est le coffre Obsidian, sur le VPS. Ce reflet est réécrit par\n"
        "scripts/publier_doctrine.py ; toute retouche faite ici sera perdue.\n"
        "\n"
        "Déposé le : {horodatage}\n"
        "Voix : {n_voix} caractères · Vocabulaire : {n_interdits} interdits\n"
        "\n"
        "=== VOIX ===\n\n{voix}\n\n"
        "=== VOCABULAIRE INTERDIT ===\n\n{vocab}\n"
    ).format(horodatage=horodatage, n_voix=len(texte_voix),
             n_interdits=len(interdits), voix=texte_voix, vocab=texte_vocab)


def _wp():
    url = os.getenv("WP_AS_URL", "").rstrip("/")
    user = os.getenv("WP_AS_USER", "")
    mdp = os.getenv("WP_AS_APP_PASSWORD", "")
    if not (url and user and mdp):
        raise DoctrineIllisible(
            "WP_AS_URL / WP_AS_USER / WP_AS_APP_PASSWORD absents de l'environnement")
    return url, (user, mdp)


def _entetes(auth) -> dict:
    """Mêmes en-têtes que le publieur : l'auth Basic est mangée par l'hébergeur,
    d'où l'en-tête personnalisé que lit cs-rest-auth.php (voir publisher.py)."""
    from scripts.publisher import _headers
    return _headers(auth)


def publier(contenu: str) -> tuple[int, str]:
    url, auth = _wp()
    entetes = _entetes(auth)

    r = requests.get("{}/wp-json/wp/v2/pages".format(url),
                     params={"slug": SLUG, "status": "private,draft,publish"},
                     auth=auth, headers=entetes, timeout=30)
    r.raise_for_status()
    existantes = r.json() if isinstance(r.json(), list) else []

    charge = {"title": TITRE, "slug": SLUG, "content": contenu, "status": "private"}
    if existantes:
        pid = existantes[0]["id"]
        rep = requests.post("{}/wp-json/wp/v2/pages/{}".format(url, pid),
                            json=charge, auth=auth, headers=entetes, timeout=45)
        geste = "mise à jour"
    else:
        rep = requests.post("{}/wp-json/wp/v2/pages".format(url),
                            json=charge, auth=auth, headers=entetes, timeout=45)
        geste = "création"
    rep.raise_for_status()
    return int(rep.json().get("id", 0)), geste


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="lit le coffre et affiche les mesures, sans rien écrire")
    args = ap.parse_args(argv)

    try:
        texte_voix, texte_vocab = lire_doctrine()
    except DoctrineIllisible as exc:
        print("REFUS — rien n'a été publié : {}".format(exc), file=sys.stderr)
        return 2

    contenu = composer(texte_voix, texte_vocab)
    interdits = len([l for l in texte_vocab.splitlines() if l.strip().startswith("-")])
    print("lu depuis Obsidian : voix {} car., vocabulaire {} car. ({} interdits)"
          .format(len(texte_voix), len(texte_vocab), interdits))

    if args.dry_run:
        print("--dry-run : rien écrit. La page aurait fait {} caractères."
              .format(len(contenu)))
        return 0

    try:
        pid, geste = publier(contenu)
    except Exception as exc:                       # noqa: BLE001
        print("ÉCHEC de la publication : {}".format(exc), file=sys.stderr)
        return 3

    # Règle 6 du dépôt : rapporter le RÉSULTAT, pas l'intention. On relit.
    url, auth = _wp()
    verif = requests.get("{}/wp-json/wp/v2/pages/{}".format(url, pid),
                         params={"context": "edit"}, auth=auth,
                         headers=_entetes(auth), timeout=30)
    if verif.ok:
        relu = verif.json().get("content", {}).get("raw", "")
        print("{} de la page {} — {} caractères relus en base (envoyés : {})"
              .format(geste, pid, len(relu), len(contenu)))
        if len(relu) < len(contenu) * 0.9:
            print("ATTENTION : la page relue est plus courte que ce qui a été "
                  "envoyé — WordPress a peut-être filtré du contenu.",
                  file=sys.stderr)
            return 4
    else:
        print("{} de la page {} — relecture impossible (HTTP {}), "
              "le dépôt n'est donc PAS confirmé".format(geste, pid, verif.status_code),
              file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
