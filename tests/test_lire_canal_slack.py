#!/usr/bin/env python3
"""Fixture : la lecture d'un canal Slack (scripts.lire_canal_slack), sans réseau.

D'OÙ ÇA VIENT — 2026-08-17. Après avoir déplacé les rapports WordPress vers #agendasabauda,
j'ai demandé à Franck de confirmer que l'essai était bien arrivé dans le bon canal. C'était
une question de trop : elle portait sur un fait vérifiable. Un webhook n'écrit que dans un
sens, d'où l'angle mort ; un jeton de lecture le ferme.

CE QUE LA FIXTURE ÉPROUVE — la mise en forme (pure), et surtout les DEUX SILENCES qui ne
doivent jamais se ressembler :

  • pas de jeton → le script explique et sort en 2. Un contrôle qui ne peut pas s'exécuter
    ne doit pas ressembler à un contrôle qui passe ;
  • `not_in_channel` → l'app n'est pas invitée dans le canal, et le message le dit. Sans ça,
    Slack rend une liste vide et on conclurait « aucun message n'est arrivé » alors que
    c'est la LECTURE qui est aveugle. C'est le « zéro qui ne dit pas d'où il vient » du
    2026-08-11, transposé à Slack.

Lancer : .venv/bin/python -m tests.test_lire_canal_slack
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import lire_canal_slack as m  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# ── 1. Mise en forme : charge réelle de conversations.history ────────────────────
PAYLOAD = [
    {"ts": "1786960208.000100", "username": "Agenda Sabauda",
     "text": "🌅 *Récapitulatif du matin* — 11 rapport(s)\n\n───── 09:50\nligne deux"},
    {"ts": "pas-un-nombre", "bot_id": "B123", "text": ""},
]
r = m.resumer(PAYLOAD)
verifier("chaque message rend une ligne", len(r) == 2, r)
verifier("l'extrait est la PREMIÈRE ligne, pas tout le message",
         r[0]["extrait"] == "🌅 *Récapitulatif du matin* — 11 rapport(s)", r[0]["extrait"])
verifier("le nombre de lignes est compté", r[0]["lignes"] == 4, r[0])
verifier("l'auteur apparent est repris", r[0]["auteur"] == "Agenda Sabauda", r[0])
verifier("un horodatage illisible ne fait pas tomber la lecture", r[1]["quand"] == "?", r[1])
verifier("un message vide rend un extrait vide, pas une erreur", r[1]["extrait"] == "", r[1])

# ── 2. Les deux silences, qui ne doivent pas se ressembler ──────────────────────
verifier("l'aide au jeton nomme les deux scopes nécessaires",
         "channels:history" in m.AIDE_JETON and "channels:read" in m.AIDE_JETON)
verifier("l'aide dit qu'il faut inviter l'app dans le canal",
         "/invite" in m.AIDE_JETON)

# `not_in_channel` doit être TRADUIT, pas rendu tel quel : c'est le cas où Slack rend une
# liste vide alors que la lecture est simplement aveugle.
appels = []


def _faux_appel(methode, jeton, **params):
    appels.append(methode)
    return {"ok": False, "error": "not_in_channel"}


vrai = m._appel
m._appel = _faux_appel
try:
    msgs, motif = m.messages("C123", "xoxb-faux")
finally:
    m._appel = vrai
verifier("aucun message rendu quand la lecture est aveugle", msgs == [])
verifier("le motif explique l'invitation manquante", "invite" in motif, motif)
verifier("le motif dit explicitement que ce n'est PAS « aucun message »",
         "PAS" in motif, motif)

# ── 3. Aucune écriture possible : le script ne doit jamais poster ───────────────
source = (ROOT / "scripts" / "lire_canal_slack.py").read_text(encoding="utf-8")
verifier("le script n'appelle jamais chat.postMessage",
         "chat.postMessage" not in source.replace(
             "`chat.postMessage` n'est pas appelé ici", ""))
verifier("il n'utilise que des requêtes GET", "requests.post" not in source)

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
