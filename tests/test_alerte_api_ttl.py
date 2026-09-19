#!/usr/bin/env python3
"""Fixture : combien de temps le drapeau d'accès API bloque le pipeline.

Aucun réseau, aucune base : on écrit un `logs/api_alert.json` daté à la main dans un
dossier jetable, et on lit ce que `get_alert()` en fait.

CE QU'IL PROTÈGE. Le drapeau sert à deux causes qui ne se lèvent pas pareil :

  · LIMITE D'USAGE — se résout par l'écoulement du temps. Bloquer sept jours est juste,
    retenter avant l'heure de reset ne peut que réechouer.
  · SOLDE À RECHARGER — se résout par une action humaine de trente secondes, à un moment
    que le code ne peut pas connaître. Le 2026-08-05, le solde est tombé à zéro pendant
    le cron de 07:00 UTC ; le compte a été rechargé dans la journée ; le pipeline est
    resté bloqué. Le drapeau ne se lève qu'au prochain appel RÉUSSI, or il empêche
    justement tout appel — une demi-journée perdue.

Le cas le plus important est donc le troisième : un message de solde de plus de trente
minutes NE DOIT PLUS bloquer, même s'il a moins de sept jours.

Lancer : .venv/bin/python -m tests.test_alerte_api_ttl
"""
import importlib
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import usage  # noqa: E402

# Dossier jetable : on ne touche JAMAIS le logs/api_alert.json de production.
usage.ALERT_FILE = Path(tempfile.mkdtemp()) / "api_alert.json"

SOLDE = ("Error code: 400 - {'type': 'error', 'error': {'type': "
         "'invalid_request_error', 'message': 'Your credit balance is too low to "
         "access the Anthropic API.'}}")
LIMITE = ("Error code: 429 - You have reached your usage limit. You will regain "
          "access on 2026-08-06 at 09:00 UTC.")
RATE = "Error code: 429 - rate limit exceeded, please retry later"
INCONNU = "Error code: 500 - internal server error"


def poser(message: str, age: timedelta) -> None:
    usage.ALERT_FILE.parent.mkdir(parents=True, exist_ok=True)
    usage.ALERT_FILE.write_text(json.dumps({
        "ts": (datetime.now(timezone.utc) - age).isoformat(), "message": message,
    }, ensure_ascii=False), encoding="utf-8")


# (libellé, message, âge, bloque encore ?)
CAS = [
    ("solde, 5 minutes — on ne martèle pas dans la foulée",
     SOLDE, timedelta(minutes=5), True),
    ("solde, 29 minutes — toujours dans la fenêtre courte",
     SOLDE, timedelta(minutes=29), True),
    ("solde, 45 minutes — LE CAS DU 5 AOÛT : rechargé, ça doit repartir",
     SOLDE, timedelta(minutes=45), False),
    ("solde, 10 heures — sûrement pas une semaine de blocage",
     SOLDE, timedelta(hours=10), False),

    ("limite d'usage, 45 minutes — le temps seul la lève, on attend",
     LIMITE, timedelta(minutes=45), True),
    ("limite d'usage, 6 jours — encore dans les sept jours",
     LIMITE, timedelta(days=6), True),
    ("limite d'usage, 8 jours — périmée",
     LIMITE, timedelta(days=8), False),

    ("rate limit, 45 minutes — cause temporelle, blocage long",
     RATE, timedelta(minutes=45), True),
    ("message non qualifiable, 45 minutes — le doute va au blocage long",
     INCONNU, timedelta(minutes=45), True),
]

echecs = 0

print("──── durée de blocage selon la cause ────")
for libelle, message, age, bloque in CAS:
    poser(message, age)
    obtenu = usage.get_alert() is not None
    if obtenu == bloque:
        print(f"OK    {'bloque ' if bloque else 'repart '}  {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}\n      attendu {'bloque' if bloque else 'repart'}, "
              f"obtenu {'bloque' if obtenu else 'repart'}")

print("\n──── cycle de vie du drapeau ────")
poser(SOLDE, timedelta(minutes=1))
if usage.get_alert() is not None:
    print("OK    posé, il bloque")
else:
    echecs += 1
    print("ÉCHEC un drapeau frais devrait bloquer")

# `record()` est appelé à CHAQUE appel réussi : c'est lui qui referme l'incident.
usage.USAGE_FILE = usage.ALERT_FILE.parent / "api_usage.jsonl"
usage.record("claude-sonnet-5", 10, 5, label="test")
if usage.get_alert() is None and not usage.ALERT_FILE.exists():
    print("OK    un appel réussi (record) lève le drapeau et efface le fichier")
else:
    echecs += 1
    print("ÉCHEC record() aurait dû lever le drapeau")

# Le fichier absent ne doit jamais faire tomber le pipeline.
if usage.get_alert() is None:
    print("OK    fichier absent = pas d'alerte, pas d'exception")
else:
    echecs += 1
    print("ÉCHEC un fichier absent ne doit pas produire d'alerte")

usage.ALERT_FILE.write_text("{ceci n'est pas du json", encoding="utf-8")
if usage.get_alert() is None:
    print("OK    fichier illisible = pas d'alerte, pas d'exception")
else:
    echecs += 1
    print("ÉCHEC un fichier illisible ne doit pas produire d'alerte")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s) sur {len(CAS) + 4} cas.")
sys.exit(1 if echecs else 0)
