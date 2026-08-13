#!/usr/bin/env python3
"""Fixture : la BOÎTE DU JOUR — sept messages Slack deviennent un.

⚠️ Aucun réseau : `slack.notify` est remplacé par une capture en mémoire, et l'archive
comme la boîte pointent vers un dossier jetable.

CE QU'ELLE SURVEILLE, et pourquoi :

  1. LE CAS QUI DOIT PASSER : sans `SLACK_DIGEST`, RIEN ne change. Un réglage qui
     modifierait le comportement par défaut casserait les 22 scripts appelants et les
     tests des autres fixtures. La boîte est un choix, pas une fatalité.
  2. avec le réglage, les messages sont rangés et pas perdus — c'est la peur légitime :
     une boîte qui avale est pire que sept messages, parce qu'on croit le canal sain ;
  3. l'URGENT passe quand même. Le chien de garde dit que la chaîne est morte ; comme le
     vidage est lui-même un cron, le différer reviendrait à se taire précisément le jour
     où il faut parler ;
  4. les 🔴 remontent en tête — sinon le digest reproduit le défaut qu'il corrige (le
     2026-08-13, la seule décision à prendre était le cinquième message sur sept) ;
  5. un envoi qui ÉCHOUE remet le contenu en boîte. Sans ça, un incident réseau
     effacerait une matinée de rapports en silence.

Lancer : .venv/bin/python -m tests.test_slack_digest
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import slack  # noqa: E402

tmp = Path(tempfile.mkdtemp())
slack._ARCHIVE = tmp / "slack"
slack._DIFFERES = slack._ARCHIVE / "differes"

# On coupe le TRANSPORT, jamais la logique : sans SLACK_WEBHOOK_URL, `notify` prend son
# chemin « pas de webhook » et n'appelle pas le réseau. C'est donc la VRAIE fonction qui
# décide de différer ou non — une fixture qui ré-implémenterait cette décision testerait
# une copie du code au lieu du code.
os.environ.pop("SLACK_WEBHOOK_URL", None)

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


def _boite() -> list[str]:
    f = slack._fichier_du_jour()
    return f.read_text(encoding="utf-8").splitlines() if f.exists() else []


print("──── 1. sans le réglage, RIEN ne change ────")
os.environ.pop("SLACK_DIGEST", None)
slack.notify("message ordinaire")
_check("aucune boîte n'est créée", not _boite(), str(_boite()))
_check("   (et le comportement par défaut des 22 scripts appelants est intact)",
       not slack._digest_actif())

print("\n──── 2. avec le réglage, les messages sont RANGÉS, jamais perdus ────")
os.environ["SLACK_DIGEST"] = "1"
_check("le réglage est vu", slack._digest_actif())
for i in range(7):
    slack.notify(f"rapport numéro {i}")
_check("les sept messages du matin sont dans la boîte", len(_boite()) == 7, str(len(_boite())))
_check("   et chacun garde sa source, pour qu'on sache qui parle",
       all('"source"' in l for l in _boite()))

print("\n──── 3. l'URGENT passe quand même ────")
avant = len(_boite())
# Le chien de garde : on vérifie que le chemin urgent ne range PAS.
slack.notify("🚨 chaîne morte", urgent=True)
_check("un message urgent ne va pas dans la boîte", len(_boite()) == avant,
       f"{avant} → {len(_boite())}")

print("\n──── 4. les 🔴 remontent en tête ────")
slack.notify("🔴 Décision — 48 fiches ne sont pas publiques")
_transport = []


def _poste(text, blocks=None, urgent=False):
    _transport.append(text)
    return True


_vrai_notify = slack.notify
slack.notify = _poste
n, ok = slack.vider_boite()
slack.notify = _vrai_notify
_check("un seul message est parti pour huit rapports", len(_transport) == 1, str(len(_transport)))
_check(f"   et il les contient tous les huit (n={n})", n == 8, str(n))
corps = _transport[0]
_check("le 🔴 est AVANT les rapports ordinaires — sinon on refait le défaut du 13/08",
       corps.index("48 fiches") < corps.index("rapport numéro 0"),
       corps[:200])
_check("l'en-tête annonce combien de décisions attendent",
       "1 demande(nt) une décision" in corps, corps[:200])
_check("la boîte est vidée après un envoi réussi", not _boite(), str(_boite()))

print("\n──── 5. un envoi qui ÉCHOUE ne perd rien ────")
slack.notify("rapport qui ne doit pas disparaître")
_check("   (un rapport en boîte)", len(_boite()) == 1, str(len(_boite())))


def _poste_ko(text, blocks=None, urgent=False):
    return False


slack.notify = _poste_ko
n, ok = slack.vider_boite()
slack.notify = _vrai_notify
_check("l'échec est rapporté tel quel, pas maquillé en succès", n == 1 and not ok, f"{n} {ok}")
_check("et le rapport est REVENU dans la boîte pour le prochain vidage",
       len(_boite()) == 1, str(_boite()))

print("\n──── 6. vider une boîte vide ne ment pas ────")
slack._fichier_du_jour().unlink(missing_ok=True)
n, ok = slack.vider_boite()
_check("0 rapport, pas d'envoi — et le script sait dire pourquoi un 0 peut arriver",
       n == 0 and not ok, f"{n} {ok}")

os.environ.pop("SLACK_DIGEST", None)
print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
