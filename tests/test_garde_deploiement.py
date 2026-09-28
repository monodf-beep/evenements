#!/usr/bin/env python3
"""Fixture : le garde-fou qui empêche le déploiement d'effacer du travail local.

D'OÙ ÇA VIENT — 2026-09-22 au matin. `deploy/update.sh` fait `git reset --hard` à chaque
passage. Le VPS portait 26 commits jamais poussés (quatre fusions faites sur place) ; le
déploiement les a effacés. L'avertissement était à l'écran — « have diverged, and have 26
and 3 different commits each » — mais il ne bloquait rien, donc personne ne l'a lu. Et
c'était une RÉCIDIVE : le même incident, à deux commits, est écrit dans le CLAUDE.md
depuis le 08/09. Écrire la règle n'avait pas suffi ; il fallait une conséquence.

POURQUOI CETTE FIXTURE EST EXIGEANTE DANS LES DEUX SENS. Un garde-fou de déploiement qui
refuse à tort est PIRE que pas de garde-fou : il bloque la mise en production d'un
correctif urgent, et la première réaction sera de le contourner définitivement. Elle
teste donc autant les cas qui doivent PASSER que ceux qui doivent bloquer — et le cas
qui doit passer est pris près de la frontière : une branche EN RETARD (c'est l'état
normal d'un déploiement réussi, celui de 12h43 ce jour-là) ne doit jamais être arrêtée.

Lancer : .venv/bin/python -m tests.test_garde_deploiement
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GARDE = ROOT / "deploy" / "verifier_avant_reset.sh"

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


def git(ou, *args, **kw):
    return subprocess.run(["git", *args], cwd=ou, capture_output=True, text=True, **kw)


def scene():
    """Un « GitHub » nu, un « VPS » qui l'a cloné, un commit commun. Comme en vrai."""
    base = Path(tempfile.mkdtemp())
    distant, local = base / "github.git", base / "vps"
    distant.mkdir()
    git(distant, "init", "--bare", "--initial-branch=principale")
    git(base, "clone", str(distant), "vps")
    for k, v in (("user.email", "f@x.tld"), ("user.name", "Fixture")):
        git(local, "config", k, v)
    (local / "a.txt").write_text("un")
    git(local, "add", "-A"); git(local, "commit", "-m", "socle")
    git(local, "branch", "-M", "principale")
    git(local, "push", "-u", "origin", "principale")
    return local


def lancer(ou, env=None):
    r = subprocess.run(["bash", str(GARDE), "principale"], cwd=ou,
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


# --- 1. À jour : rien à perdre, ça doit passer -------------------------------------
vps = scene()
code, sortie = lancer(vps)
verifier("branche à jour : le déploiement passe", code == 0, sortie[:200])
verifier("et il ne dit rien (pas de bruit quand tout va bien)", not sortie.strip(),
         repr(sortie[:120]))

# --- 2. EN RETARD : c'est l'état normal d'un déploiement — CAS QUI DOIT PASSER ------
# On fabrique de l'avance CÔTÉ DISTANT (une autre session qui pousse), sans rien
# commiter ici : c'est exactement l'état d'un VPS avant un déploiement normal.
pousseur = Path(tempfile.mkdtemp()) / "pousseur"
distant_url = git(vps, "remote", "get-url", "origin").stdout.strip()
git(Path(pousseur).parent, "clone", distant_url, str(pousseur))
for k, v in (("user.email", "f@x.tld"), ("user.name", "Fixture")):
    git(pousseur, "config", k, v)
(pousseur / "b.txt").write_text("deux")
git(pousseur, "add", "-A"); git(pousseur, "commit", "-m", "travail d'une autre session")
git(pousseur, "push", "origin", "principale")
git(vps, "fetch", "origin")
code, sortie = lancer(vps)
verifier("branche EN RETARD : le déploiement passe — c'est le cas normal",
         code == 0, sortie[:200])

# --- 3. EN AVANCE : du travail local, il faut s'arrêter ----------------------------
(vps / "local.txt").write_text("fusion faite sur le VPS")
git(vps, "add", "-A"); git(vps, "commit", "-m", "fusion faite sur place, jamais poussée")
code, sortie = lancer(vps)
verifier("un commit local jamais poussé ARRÊTE le déploiement", code == 1, str(code))
verifier("il nomme le commit menacé", "jamais poussée" in sortie, sortie[:300])
verifier("il donne la commande exacte à taper",
         "git push origin principale && bash deploy/update.sh" in sortie, sortie[:400])
verifier("il rassure : rien n'a bougé", "Le travail local est intact" in sortie)
verifier("il cite l'incident qui l'a motivé", "26 commits" in sortie)

# --- 4. DIVERGENCE (avance ET retard) : l'état exact du 22/09 ----------------------
(pousseur / "c.txt").write_text("trois")
git(pousseur, "add", "-A"); git(pousseur, "commit", "-m", "encore une autre session")
git(pousseur, "push", "origin", "principale")
git(vps, "fetch", "origin")
code, sortie = lancer(vps)
verifier("divergence des deux côtés : on s'arrête quand même", code == 1, str(code))

# --- 5. L'échappatoire existe, mais elle doit se taper exprès ----------------------
import os
env = dict(os.environ, DEPLOY_ABANDONNER_LOCAL="1")
code, sortie = lancer(vps, env=env)
verifier("l'échappatoire explicite laisse passer", code == 0, sortie[:200])
verifier("mais elle DIT ce qu'elle abandonne", "ABANDONNÉS" in sortie, sortie[:200])

# --- 6. Premier déploiement : la branche n'existe pas encore chez le distant -------
neuf = Path(tempfile.mkdtemp()) / "neuf"
neuf.mkdir()
git(neuf, "init", "--initial-branch=principale")
for k, v in (("user.email", "f@x.tld"), ("user.name", "Fixture")):
    git(neuf, "config", k, v)
(neuf / "a.txt").write_text("un")
git(neuf, "add", "-A"); git(neuf, "commit", "-m", "socle")
code, sortie = lancer(neuf)
verifier("aucune référence distante : rien à perdre, ça passe", code == 0, sortie[:200])

# --- 7. Ce que le garde-fou NE protège PAS, et qu'il ne doit pas prétendre ---------
vps2 = scene()
(vps2 / "a.txt").write_text("édité à la main, jamais commité")
code, sortie = lancer(vps2)
verifier("une modification NON COMMITÉE ne l'arrête pas (et c'est documenté)",
         code == 0, sortie[:200])
verifier("le script le dit en toutes lettres dans son en-tête",
         "modifications non COMMITÉES" in GARDE.read_text(encoding="utf-8"))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
