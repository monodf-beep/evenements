#!/usr/bin/env python3
"""Lit un canal Slack — pour vérifier MOI-MÊME ce que j'affirme, au lieu de le demander.

D'OÙ ÇA VIENT — 2026-08-17. Après avoir déplacé tous les rapports WordPress vers
#agendasabauda, j'ai dû écrire à Franck : « confirmez-moi d'un mot que l'essai est bien
arrivé dans #agendasabauda et pas dans #formulaire ». Il a répondu « oui ». C'était la
question de trop : elle portait sur un fait vérifiable, pas sur un arbitrage.

Un Incoming Webhook n'écrit que dans un sens — d'où l'angle mort. Ce script le ferme avec
un jeton de LECTURE, et il ne sert qu'à ça : confirmer qu'un message est arrivé, et DANS
QUEL canal. Aucune écriture, jamais : `chat.postMessage` n'est pas appelé ici et ne doit
pas l'être. L'envoi reste le webhook de `utils/slack.py`, révocable séparément.

CE QU'IL FAUT UNE FOIS, ET UNE SEULE (côté Franck, dans Slack) :
  1. https://api.slack.com/apps → l'app qui poste déjà dans #agendasabauda (ou « Create
     New App » → From scratch, sur le plan de travail Cultura Sabauda) ;
  2. « OAuth & Permissions » → Scopes → Bot Token Scopes → ajouter **`channels:history`**
     et **`channels:read`** (rien d'autre : ces deux-là ne donnent aucun droit d'écriture) ;
  3. « Install to Workspace », puis copier le **Bot User OAuth Token** (il commence par
     `xoxb-`) et le poser dans le `.env` du VPS :  SLACK_BOT_TOKEN=xoxb-…
  4. dans Slack, inviter l'app dans le canal : `/invite @<nom de l'app>` dans
     **#agendasabauda**. Sans cette invitation, l'historique répond `not_in_channel` — et
     ce script le DIT au lieu de conclure « aucun message ».

TANT QUE LE JETON MANQUE, ce script ne prétend rien : il explique ce qui manque et sort en
erreur. Un contrôle qui ne peut pas s'exécuter ne doit jamais ressembler à un contrôle qui
passe (leçon du 2026-08-11 : un zéro doit dire d'où il vient).

Usage :
    .venv/bin/python -m scripts.lire_canal_slack                      # 10 derniers messages
    .venv/bin/python -m scripts.lire_canal_slack --canal agendasabauda
    .venv/bin/python -m scripts.lire_canal_slack --cherche "Récapitulatif du matin"
"""
from __future__ import annotations
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger  # noqa: E402

log = get_logger("lire_canal_slack")

API = "https://slack.com/api"
CANAL_DEFAUT = "agendasabauda"

AIDE_JETON = (
    "SLACK_BOT_TOKEN absent du .env. Il se crée une fois : api.slack.com/apps → "
    "OAuth & Permissions → Bot Token Scopes → channels:history + channels:read → "
    "Install to Workspace → copier le jeton xoxb-… ; puis, dans Slack, "
    "/invite @<app> dans le canal. Voir l'en-tête de ce fichier."
)


def _jeton() -> str:
    load_dotenv(ROOT / ".env")
    return (os.getenv("SLACK_BOT_TOKEN") or "").strip()


def _appel(methode: str, jeton: str, **params) -> dict:
    """Appel Slack. Renvoie toujours un dict ; `ok=False` porte le motif de Slack."""
    try:
        r = requests.get(f"{API}/{methode}", params=params,
                         headers={"Authorization": f"Bearer {jeton}"}, timeout=20)
        r.raise_for_status()
        return r.json() or {}
    except (requests.RequestException, ValueError) as exc:
        return {"ok": False, "error": f"appel impossible : {exc}"}


def resoudre_canal(nom: str, jeton: str) -> tuple[str, str]:
    """(identifiant, motif d'échec). Le NOM est ce que Franck écrit ; Slack veut un ID."""
    curseur = ""
    while True:
        rep = _appel("conversations.list", jeton, limit=200, cursor=curseur,
                     exclude_archived="true", types="public_channel,private_channel")
        if not rep.get("ok"):
            return "", rep.get("error", "inconnu")
        for c in rep.get("channels") or []:
            if (c.get("name") or "").lower() == nom.lower().lstrip("#"):
                return c.get("id", ""), ""
        curseur = ((rep.get("response_metadata") or {}).get("next_cursor") or "").strip()
        if not curseur:
            return "", f"canal « {nom} » introuvable (l'app le voit-elle ?)"


def messages(canal_id: str, jeton: str, limite: int = 10) -> tuple[list[dict], str]:
    rep = _appel("conversations.history", jeton, channel=canal_id, limit=limite)
    if not rep.get("ok"):
        motif = rep.get("error", "inconnu")
        if motif == "not_in_channel":
            motif = ("l'app n'est pas dans le canal — `/invite @<app>` dans Slack. "
                     "Ce n'est PAS « aucun message ».")
        return [], motif
    return rep.get("messages") or [], ""


def resumer(msgs: list[dict]) -> list[dict]:
    """Forme lisible : heure locale, auteur apparent, première ligne. Fonction pure,
    c'est elle que la fixture éprouve (tests/test_lire_canal_slack.py)."""
    out = []
    for m in msgs:
        try:
            quand = datetime.fromtimestamp(float(m.get("ts") or 0)).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError, OSError):
            quand = "?"
        texte = (m.get("text") or "").strip()
        premiere = texte.splitlines()[0] if texte else ""
        out.append({
            "quand": quand,
            "auteur": m.get("username") or m.get("bot_id") or m.get("user") or "?",
            "extrait": premiere[:120],
            "lignes": len(texte.splitlines()),
        })
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Lit un canal Slack (lecture seule).")
    p.add_argument("--canal", default=CANAL_DEFAUT)
    p.add_argument("--limite", type=int, default=10)
    p.add_argument("--cherche", default="",
                   help="Sort en 0 si ce texte apparaît dans les messages lus, sinon 1 — "
                        "de quoi VÉRIFIER qu'un message est bien arrivé.")
    args = p.parse_args(argv)

    jeton = _jeton()
    if not jeton:
        print(AIDE_JETON)
        return 2

    canal_id, motif = resoudre_canal(args.canal, jeton)
    if not canal_id:
        print(f"Canal non résolu : {motif}")
        return 2
    msgs, motif = messages(canal_id, jeton, args.limite)
    if motif:
        print(f"Historique illisible : {motif}")
        return 2

    resume = resumer(msgs)
    print(f"#{args.canal} ({canal_id}) — {len(resume)} message(s) lus :")
    for m in resume:
        print(f"  {m['quand']}  {str(m['auteur'])[:14]:<14} {m['lignes']:>2} ligne(s)  "
              f"{m['extrait']}")

    if args.cherche:
        trouve = any(args.cherche.lower() in (m.get("text") or "").lower() for m in msgs)
        print(f"\n« {args.cherche} » : {'TROUVÉ' if trouve else 'ABSENT'} des "
              f"{len(msgs)} derniers messages de #{args.canal}.")
        return 0 if trouve else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
