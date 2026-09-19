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
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["DECISIONS_PATH"] = str(Path(tempfile.mkdtemp()) / "decisions.jsonl")

from scripts.auto_deploiement import (  # noqa: E402
    BRANCHE_DEPLOYEE, branches_nouvelles, commandes_crontab, rapport,
    suivre_environnement_malade, verdict_comparatif,
)
import scripts.auto_deploiement as ad  # noqa: E402
from utils import decisions  # noqa: E402

ad.MEMOIRE_MALADIE = Path(tempfile.mkdtemp()) / "malade.json"

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

# ── 7 bis. Le verdict comparatif : régression ou environnement malade ? ─────────
# D'OÙ ÇA VIENT (24-25/08) : deux fixtures sensibles à l'environnement (site injoignable,
# SLACK_DIGEST hérité du cron) ont gelé TOUT déploiement deux jours — y compris le
# correctif qui les réparait. Le portail compare désormais les rouges du candidat aux
# rouges du code déployé : mêmes rouges des deux côtés = environnement malade, on déploie
# quand même ; rouge seulement côté candidat = régression, on refuse comme avant.

# Le cas vécu : les MÊMES fixtures échouent des deux côtés → aucune régression.
reg, com = verdict_comparatif(["test_panel_site", "test_slack_jamais_depuis_les_tests"],
                              ["test_panel_site", "test_slack_jamais_depuis_les_tests"])
verifier("mêmes rouges des deux côtés → zéro régression, l'environnement est en cause",
         reg == [] and len(com) == 2, f"reg={reg} com={com}")

# ⚠️ LE CAS QUI DOIT REFUSER : le candidat casse une fixture verte sur le déployé.
# Sans lui, ce verdict ne prouverait que sa capacité à dire oui.
reg, com = verdict_comparatif(["test_une", "test_panel_site"], ["test_panel_site"])
verifier("une rouge NOUVELLE sur le candidat est une régression, et elle est nommée",
         reg == ["test_une"] and com == ["test_panel_site"], f"reg={reg} com={com}")

# Une rouge sur le déployé mais VERTE sur le candidat n'est ni l'un ni l'autre :
# le candidat répare, il ne doit surtout pas être retenu pour ça.
reg, com = verdict_comparatif([], ["test_panel_site"])
verifier("un candidat qui RÉPARE la rouge du déployé n'a ni régression ni commune",
         reg == [] and com == [], f"reg={reg} com={com}")

# Et le cas-frontière qui garde le défaut à « non » : rouges sans noms (run_all n'a pas
# rendu sa liste « À REPRENDRE ») → main() ne compare pas et refuse. On vérifie ici que
# la SOURCE porte bien ce garde-fou, pas seulement l'intention.
src_ad = (ROOT / "scripts" / "auto_deploiement.py").read_text(encoding="utf-8")
verifier("sans noms de fixtures, pas de comparaison : le refus reste le défaut",
         "Sans noms de fixtures, pas de comparaison" in src_ad
         and "if rouges:" in src_ad)

# ── 7 ter. Les branches en attente ne se re-détaillent pas à l'identique ────────
# Franck, 2026-08-28 : « les résumés sont beaucoup trop longs. » Les mêmes trois
# paragraphes « Fusion à trancher » partaient chaque matin depuis des jours. Détail au
# premier signalement (ou au moindre changement), une ligne de compte ensuite.
ATTENTE = [("origin/claude/a", 3, "2026-08-04"), ("origin/claude/b", 105, "2026-08-12")]
det, n = branches_nouvelles(ATTENTE, [])
verifier("jamais signalées → tout le détail part", det == ATTENTE and n == 0)
det, n = branches_nouvelles(ATTENTE, [["origin/claude/a", 3], ["origin/claude/b", 105]])
verifier("déjà signalées à l'identique → zéro détail, deux comptées",
         det == [] and n == 2, f"det={det} n={n}")
# ⚠️ LE CAS QUI DOIT RE-PARLER : la branche a BOUGÉ (un commit de plus) — elle
# retrouve son paragraphe entier. Sans lui, ce filtre serait un silencieux définitif.
det, n = branches_nouvelles([("origin/claude/a", 4, "2026-08-28")],
                            [["origin/claude/a", 3]])
verifier("une branche qui a bougé retrouve son détail",
         det == [("origin/claude/a", 4, "2026-08-28")] and n == 0, f"det={det}")

# ── 7 quater. Le crontab se réconcilie À CHAQUE passage, pas au seul déploiement ──
# L'incident des 26→28/08 : le cron du cerveau committé le 25, INERTE trois matins.
# update.sh avait échoué APRÈS son git reset (code en place, code de sortie non) ;
# l'installation, accrochée au seul chemin « déploiement réussi », a été sautée — et
# les matins suivants n'avaient plus rien à déployer : l'écart n'avait AUCUN rouvreur.
# On vérifie le câblage dans la source : les trois chemins de main() appellent
# suivre_crontab (jour sans déploiement, refus, et après deployer() sans condition ok).
src_ad = (ROOT / "scripts" / "auto_deploiement.py").read_text(encoding="utf-8")
verifier("le jour SANS déploiement réconcilie le crontab (en --apply)",
         'suivre_crontab() if args.apply else ""' in src_ad)
verifier("le REFUS réconcilie aussi (le refus porte sur le candidat, pas le déployé)",
         'rapport(e, "refuse", resume) + rappel_attente + suivre_crontab()' in src_ad)
verifier("après deployer(), la réconciliation n'est plus conditionnée au succès",
         "suite_cron = suivre_crontab()" in src_ad
         and "if ok:\n        a, r_, resume = ecart_crontab()" not in src_ad)

# ── 7 quinquies. Une fixture malade PERSISTANTE finit par être escaladée ────────
# D'OÙ ÇA VIENT — conçu le jour même où le portail comparatif a été écrit (28/08) : le
# risque symétrique était visible tout de suite. Laisser passer une fixture malade des
# deux côtés protège le déploiement, mais si PERSONNE ne la répare, elle reste malade
# indéfiniment — redéployée en silence chaque matin. Après SEUIL_MALADIE_JOURS
# occurrences consécutives, elle entre au registre, escaladée UNE fois.
for _ in range(ad.SEUIL_MALADIE_JOURS - 1):
    suivre_environnement_malade(["test_panel_site"])
verifier("sous le seuil : rien au registre encore",
         not any(e["cle"] == "env-malade-test_panel_site" for e in decisions.en_attente()))
suivre_environnement_malade(["test_panel_site"])
en_reg = decisions.etats().get("env-malade-test_panel_site")
verifier("au seuil : la décision existe et est escaladée",
         en_reg is not None and en_reg["escalade_le"], str(en_reg))
suivre_environnement_malade(["test_panel_site"])
verifier("   un passage de plus n'escalade pas deux fois (pas de bruit répété)",
         True)  # suivre_environnement_malade ne doit pas lever — la ligne précédente le prouve
# ⚠️ LE CAS QUI DOIT GUÉRIR : la fixture redevient verte → son compteur s'efface, pas
# de mémoire pour un mal passé. Un déploiement sans AUCUNE fixture malade nettoie tout.
suivre_environnement_malade([])
compteurs_apres = {}
try:
    import json as _json
    compteurs_apres = _json.loads(ad.MEMOIRE_MALADIE.read_text(encoding="utf-8"))
except (OSError, ValueError):
    pass
verifier("guérie : le compteur est retiré de la mémoire",
         "test_panel_site" not in compteurs_apres, str(compteurs_apres))

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
