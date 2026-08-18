#!/usr/bin/env python3
"""Fixture : une fixture ne doit JAMAIS parler au vrai Slack.

INCIDENT RÉEL, 2026-08-17 à 01h05 — trouvé le soir même en lisant #agendasabauda, une fois
l'accès en lecture branché. Deux messages y étaient tombés :

    :rotating_light: chaîne morte
    message ordinaire

Aucune panne : c'était `tests/test_slack_digest.py`. Elle retire pourtant
`SLACK_WEBHOOK_URL` de l'environnement avant de commencer — mais `utils.slack._webhook()`
rappelle `load_dotenv()` à chaque envoi, ce qui réinjecte l'URL depuis le `.env`. Le
garde-fou était défait par le code même qu'il testait.

CE QUI REND LA CHOSE SÉRIEUSE : `scripts/auto_deploiement`, écrit ce jour-là, lance TOUTES
les fixtures sur le VPS avant chaque déploiement. Sans ce correctif, une fausse alerte
« chaîne morte » serait partie chaque matin dans le canal — le message qu'on ne peut
justement pas se permettre de crier au loup, puisque c'est celui du chien de garde.

Le correctif est central (`utils.slack._depuis_les_tests`) et non dans les sept fixtures
qui appellent `notify` : une seule se protégeait, et celle qu'on écrira demain n'y
penserait pas.

Lancer : .venv/bin/python -m tests.test_slack_jamais_depuis_les_tests
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import slack  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# On pose une URL de webhook PARFAITEMENT valide dans l'environnement : c'est la situation
# du VPS, où le .env en contient une vraie. Le transport doit rester coupé quand même.
os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/services/T00000/B00000/xxxxxxxx"

verifier("l'appel est reconnu comme venant des tests", slack._depuis_les_tests())
verifier("le webhook est vu comme absent, malgré l'URL dans l'environnement",
         slack._webhook() == "", repr(slack._webhook()))

# Le chemin complet : notify ne doit rien envoyer et le DIRE (False = pas parti).
envoye = slack.notify("🚨 chaîne morte — CECI EST UNE FIXTURE, rien ne doit partir")
verifier("notify rend False : le message n'est pas parti", envoye is False, str(envoye))

# L'archive locale, elle, doit garder la trace : un message non parti est justement
# celui qu'on cherchera plus tard.
jour = slack._ARCHIVE / f"{__import__('datetime').datetime.now():%Y-%m-%d}.jsonl"
verifier("le message reste archivé localement, marqué comme NON envoyé",
         jour.exists() and '"envoye": false' in jour.read_text(encoding="utf-8"),
         str(jour))

# La contre-épreuve : hors des tests, le même code DOIT retrouver l'URL. Sans ce volet,
# un `_webhook()` qui rendrait toujours "" passerait au vert en cassant la production.
import subprocess  # noqa: E402

hors_tests = ROOT / "logs" / "_essai_webhook_hors_tests.py"
hors_tests.parent.mkdir(parents=True, exist_ok=True)
hors_tests.write_text(
    "import sys\n"
    f"sys.path.insert(0, {str(ROOT)!r})\n"
    "from utils import slack\n"
    "print(slack._webhook())\n", encoding="utf-8")
try:
    r = subprocess.run([sys.executable, str(hors_tests)], capture_output=True, text=True,
                       env={**os.environ, "SLACK_WEBHOOK_URL": "https://hooks.slack.com/x/y/z"})
    verifier("hors des tests, le webhook est bien retrouvé (le garde-fou ne casse pas la "
             "production)", "hooks.slack.com" in r.stdout, r.stdout.strip() or r.stderr[-200:])
finally:
    hors_tests.unlink(missing_ok=True)

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
