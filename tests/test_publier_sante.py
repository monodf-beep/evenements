#!/usr/bin/env python3
"""Fixture : le relevé de santé déposé sur WordPress (scripts.publier_sante).

D'OÙ ÇA VIENT — Franck, 2026-08-17 : « fais les deux accès. » Le relevé sert à ce qu'une
session Claude LISE l'état du serveur — files, crons, crédit API, révision déployée — sans
accès au serveur et sans qu'un secret soit dupliqué quelque part.

CE QUE LA FIXTURE PROTÈGE, dans l'ordre d'importance :

  1. **aucun secret ne sort.** Le relevé part vers une option WordPress lisible par tout
     compte capable d'éditer le site : une clé Anthropic ou un webhook qui s'y glisserait
     serait une fuite, pas un bug d'affichage ;
  2. **et pourtant le portillon ne refuse pas à tort.** Un relevé de coût API porte
     légitimement `tokens_utilises` : c'est le cas près de la frontière qui doit PASSER.
     `token` seul figurait dans la liste des motifs, il a été retiré pour cette raison —
     un faux refus bloque le relevé entier, donc rend le dispositif muet ;
  3. **la structure est stable** : quatre sections, parce que ce sont les quatre questions
     qui ont provoqué des allers-retours ce jour-là (est-ce déployé ? les crons tournent-ils ?
     où sont les files ? le crédit est-il revenu ?).

Lancer : .venv/bin/python -m tests.test_publier_sante
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publier_sante import (  # noqa: E402
    MOTS_INTERDITS, contient_un_secret, releve,
)

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# ── 1. Ce qui doit être REFUSÉ ──────────────────────────────────────────────────
fuites = {
    "clé Anthropic": {"api": {"cle": "sk-ant-api03-XXXXXXXXXXXX"}},
    "webhook Slack": {"slack": {"url": "https://hooks.slack.com/services/T00/B00/xxxx"}},
    "jeton de bot Slack": {"slack": {"bot": "xoxb-123456-abcdef"}},
    "mot de passe d'application": {"wp": {"app_password": "abcd efgh ijkl"}},
    "champ nommé api_key": {"conf": {"api_key": ""}},
    "en-tête d'autorisation": {"http": {"Authorization": "Basic abcdef"}},
}
for quoi, objet in fuites.items():
    verifier(f"REFUSÉ : {quoi}", bool(contient_un_secret(objet)),
             f"{objet} est passé")

# ── 2. LE CAS QUI DOIT PASSER, choisi près de la frontière ──────────────────────
# Un relevé de coût API parle de « tokens ». Il ne doit PAS être refusé : un faux refus
# rend le relevé muet, et c'est exactement le défaut que CLAUDE.md reproche aux portillons.
legitimes = {
    "un relevé de coût API": {"api": {"tokens_utilises": 12345, "tokens_entree": 900}},
    "un relevé normal": {"git": {"head": "68c328f", "branche": "claude/quirky-davinci-jvqrnw"},
                         "files": {"goulot": "datation", "etages": [{"nom": "dates",
                                                                    "restants": 150}]},
                         "api": {"api_error": 12, "dernier_enrichissement": "2026-08-14"}},
    "un nom de script contenant « pass »": {"crons": {"passe_3": {"il_y_a_h": 2.0}}},
}
for quoi, objet in legitimes.items():
    faute = contient_un_secret(objet)
    verifier(f"ACCEPTÉ : {quoi}", not faute, f"refusé à tort sur « {faute} »")

# ── 3. La liste des motifs couvre les secrets RÉELS de ce dépôt ─────────────────
for motif in ("sk-ant", "hooks.slack.com", "xoxb-", "app_password", "api_key"):
    verifier(f"le motif « {motif} » est surveillé", motif in MOTS_INTERDITS)
verifier("« token » seul n'est PAS un motif (faux refus sur tokens_utilises)",
         "token" not in MOTS_INTERDITS)

# ── 4. La structure du relevé, et sa robustesse hors production ─────────────────
# Ici, ni base ni journal : le relevé doit quand même se composer et le DIRE, sans lever.
r = releve()
for section in ("date", "git", "crons", "files", "api"):
    verifier(f"le relevé porte la section « {section} »", section in r, list(r))
verifier("le relevé composé sur une machine sans base ne contient aucun secret",
         not contient_un_secret(r), contient_un_secret(r))
verifier("une base absente est DITE, pas passée sous silence",
         "erreur" in r["files"] or r["files"].get("etages") is not None, r["files"])

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
