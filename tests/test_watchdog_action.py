#!/usr/bin/env python3
"""Fixture : l'alerte Slack du chien de garde (scripts/watchdog_crons.py) dit
maintenant QUOI FAIRE, pas seulement CE qui ne va pas.

Franck, 2026-08-06, sur l'alerte « JAMAIS VUE (tolérance 200 h) » : « cette alerte
ne me sert à rien, soit il faut qu'elle soit compréhensible et que je fasse quelque
chose, soit l'enlever. » Le message d'origine ne donnait aucune commande : un
non-développeur qui le relaie n'a aucun moyen d'agir sans deviner.

Deux causes réelles distinctes, deux formulations distinctes :
  • JAMAIS VUE (vu=None) : la cause la plus fréquente est un cron ajouté à
    crontab.txt mais jamais réinstallé sur le VPS → vérifier `crontab -l`.
  • EN RETARD (déjà vu avant) : le cron tournait puis s'est arrêté → lire le
    journal pour l'erreur, pas la peine de vérifier le crontab.

⚠️ Aucun réseau : slack.notify est mocké. `etat`/`fuseau` sont monkey-patchés
pour ne pas dépendre du vrai système de fichiers/de la vraie base.

Lancer : .venv/bin/python -m tests.test_watchdog_action
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.watchdog_crons as wd  # noqa: E402
from utils import slack  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ── 1. _action() : deux formulations distinctes selon la cause ─────────────────
print("──── _action() ────")
jamais_vue = {"script": "audit_calibrage", "fichier": "calibrage.log", "vu": None}
action = wd._action(jamais_vue)
_check("JAMAIS VUE mentionne crontab -l", "crontab -l" in action, action)
_check("JAMAIS VUE mentionne crontab crontab.txt (le vrai correctif rencontré)",
      "crontab crontab.txt" in action, action)
_check("JAMAIS VUE mentionne aussi le journal (2e cause possible)",
      "calibrage.log" in action, action)

en_retard = {"script": "seo_batch", "fichier": "seo_batch.log", "vu": datetime.now() - timedelta(hours=50)}
action = wd._action(en_retard)
_check("EN RETARD pointe directement le journal", "tail -50 logs/seo_batch.log" in action, action)
_check("EN RETARD ne mentionne PAS crontab (déjà tourné, pas un problème d'install)",
      "crontab" not in action, action)

# ── 2. etat() expose bien `fichier` (nécessaire à _action) ──────────────────────
print("\n──── etat() expose 'fichier' ────")
lignes = wd.etat()
_check("chaque ligne porte une clé 'fichier'", all("fichier" in l for l in lignes))

# ── 3. main(['--slack']) : le message envoyé contient une action concrète ───────
print("\n──── main(['--slack']) : message Slack actionnable ────")
messages = []
urgences = []
# Le stub accepte `urgent` ET l'enregistre : ce n'est pas de la complaisance envers la
# signature, c'est le point qui compte depuis le 2026-08-13. La boîte du jour
# (utils/slack.py) regroupe tous les rapports en un message pour tenir la demande de
# Franck — « un ou deux par jour, pas sept ». Le chien de garde, lui, doit rester HORS
# de la boîte : le vidage est un cron, donc si la chaîne est morte le digest ne part
# pas. Différer l'alerte reviendrait à se taire précisément le jour où il faut parler.
slack.notify = (lambda texte, blocks=None, urgent=False:
                (messages.append(texte), urgences.append(urgent))[0] or True)

wd.etat = lambda maintenant=None: [
    {"libelle": "Calibrage de l'évaluateur", "script": "audit_calibrage",
     "fichier": "calibrage.log", "vu": None, "source": "aucune trace",
     "retard_h": None, "tolerance": 200, "en_retard": True, "erreurs": 0},
]
wd.fuseau = lambda: ("Europe/Paris (UTC+2)", True)

rc = wd.main(["--slack"])
_check("rc=1 (il y avait du retard)", rc == 1)
_check("un message a bien été envoyé", len(messages) == 1, str(messages))
if messages:
    _check("le message contient la commande crontab -l",
          "crontab -l" in messages[0], messages[0])
    _check("le message invite à coller le résultat à Claude",
          "Claude" in messages[0], messages[0])
    _check("il part en URGENT — hors de la boîte du jour, sinon il attendrait un "
          "vidage qui ne viendra pas si la chaîne est morte",
          urgences == [True], str(urgences))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
