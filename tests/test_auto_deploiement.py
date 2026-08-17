#!/usr/bin/env python3
"""Fixture : le déploiement autonome (scripts.auto_deploiement).

D'OÙ ÇA VIENT — Franck, 2026-08-17 : « j'aimerais que tu sois autonome et que tu n'aies pas
besoin de moi. Comment faire ? » Ce jour-là il a tapé `bash deploy/update.sh` deux fois,
dont une avec une variable que je lui avais dictée — et la première fois, la commande n'a
RIEN déployé de mon travail, parce que le script vise une branche et que je poussais sur une
autre.

CE QUE LA FIXTURE ÉPROUVE, sans jamais rien déployer ni toucher à git :

  • **la concordance des deux branches**. `auto_deploiement` répète la valeur par défaut de
    `deploy/update.sh`. Une constante écrite à deux endroits finit par se contredire : ce
    test est le prix de cette répétition, et il vaut mieux que la centralisation, car il
    échoue le jour où quelqu'un change le shell sans changer le Python ;
  • **le rapport dit la vérité dans les quatre cas** — déployé, refusé, en échec, rien ;
  • **le piège du jour est signalé** : des commits sur une autre branche `claude/*` ne
    partiront jamais, et seront effacés du serveur au prochain déploiement. C'est
    exactement ce que personne n'aurait vu ;
  • **« rien à faire » n'est pas « rien à dire »** : un serveur resté sur la mauvaise
    branche doit se voir même un jour sans déploiement.

Lancer : .venv/bin/python -m tests.test_auto_deploiement
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.auto_deploiement import (  # noqa: E402
    BRANCHE_DEPLOYEE, commandes_crontab, rapport,
)

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# ── 1. Les deux branches par défaut doivent être la MÊME ────────────────────────
shell = (ROOT / "deploy" / "update.sh").read_text(encoding="utf-8")
m = re.search(r'BRANCH="\$\{DEPLOY_BRANCH:-([^}"]+)\}"', shell)
verifier("la branche par défaut de deploy/update.sh est lisible", bool(m))
if m:
    verifier("auto_deploiement vise la MÊME branche que deploy/update.sh",
             m.group(1) == BRANCHE_DEPLOYEE, f"{m.group(1)} ≠ {BRANCHE_DEPLOYEE}")

BASE = {
    "branche_visee": BRANCHE_DEPLOYEE,
    "branche_courante": BRANCHE_DEPLOYEE,
    "deploye": "4b3f810",
    "disponible": "cd2ba57",
    "commits_de_retard": 3,
    "hors_branche": False,
    "en_attente": [],
}

# ── 2. Un déploiement réussi se dit avec ses deux révisions ─────────────────────
r = rapport(BASE, "deploye", "✅ Déploiement terminé (cd2ba57).")
verifier("le déploiement nomme l'avant et l'après",
         "4b3f810" in r and "cd2ba57" in r, r)
verifier("il dit combien de commits", "3 commit(s)" in r, r)

# ── 3. LE CAS QUI COMPTE : refus sur fixtures rouges ────────────────────────────
# Le serveur doit RESTER en place, et le message doit le dire — sans quoi on croirait
# à une panne de déploiement alors que c'est une protection qui a fonctionné.
r = rapport(BASE, "refuse", "3 problème(s).")
verifier("un refus dit que le serveur reste en place",
         "reste sur 4b3f810" in r, r)
verifier("un refus dit que c'est voulu", "c'est voulu" in r, r)
verifier("un refus n'annonce jamais un déploiement",
         "Déploiement automatique" not in r, r)

# ── 4. Fixtures vertes mais update.sh en erreur : c'est un AUTRE cas ────────────
r = rapport(BASE, "echec", "erreur systemd")
verifier("l'échec de update.sh est distingué du refus",
         "en échec" in r and "REFUSÉ" not in r, r)

# ── 5. Le piège du 2026-08-17 : des commits qui ne partiront jamais ─────────────
avec_attente = dict(BASE, commits_de_retard=0,
                    en_attente=[("origin/claude/morning-api-credit-duplicates-sobc4i",
                                 3, "2026-08-17")])
r = rapport(avec_attente, "aucun")
verifier("une branche en attente est signalée même sans déploiement", bool(r.strip()), r)
verifier("le message dit qu'ils seront EFFACÉS", "effacés" in r, r)
verifier("il nomme la branche et le nombre",
         "morning-api-credit-duplicates-sobc4i" in r and "3 commit(s)" in r, r)

# ── 6. Serveur sur la mauvaise branche : à dire, toujours ───────────────────────
hors = dict(BASE, commits_de_retard=0, hors_branche=True,
            branche_courante="claude/morning-api-credit-duplicates-sobc4i")
r = rapport(hors, "aucun")
verifier("un serveur hors branche est signalé", "pas sur" in r, r)

# ── 7. …et le silence quand tout va bien ────────────────────────────────────────
r = rapport(dict(BASE, commits_de_retard=0), "aucun")
verifier("rien à dire quand tout est à jour et propre", r.strip() == "", repr(r))

# ── 8. Le crontab du dépôt n'est pas le crontab installé ────────────────────────
# Le trou trouvé le 2026-08-17 : la ligne de cron de ce script même était committée et
# INERTE, faute d'un `crontab crontab.txt`. La comparaison ignore les commentaires (sinon
# elle crierait tous les jours), garde les affectations de variables, et normalise les
# espaces (`crontab -l` ne rend pas toujours l'alignement du fichier).
TEXTE = """
# un commentaire, qui ne compte pas
SLACK_DIGEST=1

0 8 * * *   cd /root/evenements &&  .venv/bin/python scripts/scraper_events.py
# 30 9 * * * une ligne COMMENTÉE, donc désactivée
"""
cmd = commandes_crontab(TEXTE)
verifier("les commentaires ne comptent pas", not any("commentaire" in c for c in cmd), cmd)
verifier("une ligne commentée n'est pas prise pour une tâche active",
         not any(c.startswith("30 9") for c in cmd), cmd)
verifier("l'affectation de variable compte", "SLACK_DIGEST=1" in cmd, cmd)
verifier("les espaces sont normalisés",
         "0 8 * * * cd /root/evenements && .venv/bin/python scripts/scraper_events.py" in cmd,
         cmd)
verifier("deux lignes seulement dans cet exemple", len(cmd) == 2, cmd)

# Et le fichier réel du dépôt doit contenir le cron de déploiement : sans lui, tout ce
# fichier ne sert à rien.
reel = commandes_crontab((ROOT / "crontab.txt").read_text(encoding="utf-8"))
verifier("crontab.txt planifie bien le déploiement autonome",
         any("scripts.auto_deploiement --apply" in c for c in reel))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
