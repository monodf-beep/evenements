#!/usr/bin/env python3
"""Déploie le VPS tout seul quand la branche de travail a bougé — SI les fixtures passent.

D'OÙ ÇA VIENT — Franck, 2026-08-17 : « j'aimerais que tu sois autonome et que tu n'aies pas
besoin de moi. Comment faire ? »

L'inventaire de la journée est sans appel : il a tapé lui-même `bash deploy/update.sh`, deux
fois, dont une avec une variable d'environnement que je lui avais dictée. Rien là-dedans
n'était une décision — c'était de la frappe. Et le pire : la première fois, la commande
n'a RIEN déployé de mon travail, parce que le script vise `claude/quirky-davinci-jvqrnw` et
que je poussais ailleurs. Personne ne l'aurait su sans lecture du script.

Ce fichier retire les deux dépendances : il déploie, et il DIT quand quelque chose attend
d'être déployé sans l'être.

CE QUI REND CE DÉPLOIEMENT SÛR, et sans quoi il ne faudrait pas l'écrire :

  1. **les fixtures décident.** Le code candidat est sorti dans un `git worktree` jetable,
     `tests.run_all` y tourne, et le déploiement N'A LIEU QUE si le code de sortie est 0.
     Ce lanceur existe justement parce qu'une boucle shell affichait « ÉCHEC » en rendant 0
     (2026-08-16) : une sortie qui dit la bonne chose pendant que le programme en fait une
     autre. Ici l'échec a une conséquence — rien ne part ;
  2. **rien n'est écrasé.** On ne touche au dépôt de production qu'en appelant
     `deploy/update.sh`, le même script que Franck tape à la main, avec sa protection de
     `.claude/settings.json` ;
  3. **dry-run par défaut** (règle 4). Sans `--apply`, il dit ce qu'il ferait ;
  4. **il se tait quand il n'y a rien** — mais jamais quand il a échoué.

CE QU'IL NE FAIT PAS, ET NE DOIT PAS FAIRE. Il ne choisit pas la branche, ne fusionne rien,
ne force aucun push. Le jour où deux branches divergent, c'est un arbitrage : il le SIGNALE
(voir `branches_en_attente`) et s'arrête là.

Usage :
    .venv/bin/python -m scripts.auto_deploiement            # dry-run
    .venv/bin/python -m scripts.auto_deploiement --apply    # cron de 7h50
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import slack  # noqa: E402
from utils.logger import get_logger  # noqa: E402

log = get_logger("auto_deploiement")

# La MÊME valeur par défaut que deploy/update.sh. Elle est répétée ici en connaissance de
# cause : deux endroits qui portent la même constante finissent par se contredire, mais un
# script qui LIRAIT l'autre pour en extraire sa variable serait plus fragile encore. La
# fixture (tests/test_auto_deploiement.py) vérifie que les deux valeurs concordent — c'est
# le contrôle qui manquait, pas la centralisation.
BRANCHE_DEPLOYEE = "claude/quirky-davinci-jvqrnw"
UPDATE_SH = ROOT / "deploy" / "update.sh"


def _git(*args: str, cwd: Path | None = None) -> tuple[int, str]:
    r = subprocess.run(["git", *args], cwd=str(cwd or ROOT),
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def branches_en_attente(branche: str = BRANCHE_DEPLOYEE) -> list[tuple[str, int, str]]:
    """Branches `claude/*` qui portent des commits ABSENTS de la branche déployée.

    C'est le piège du 2026-08-17, écrit en code : mon travail était sur
    `claude/morning-api-credit-duplicates-sobc4i`, le déploiement visait une autre branche,
    et le prochain passage aurait EFFACÉ les fichiers du serveur. Personne ne l'aurait vu.

    Renvoie (branche, nombre de commits en avance, date du plus récent).
    """
    code, sortie = _git("for-each-ref", "--format=%(refname:short)",
                        "refs/remotes/origin/claude")
    if code != 0:
        log.warning("Branches non listées (%s).", sortie)
        return []
    en_attente = []
    for ref in sortie.splitlines():
        ref = ref.strip()
        if not ref or ref.endswith(f"/{branche}"):
            continue
        code, n = _git("rev-list", "--count", f"origin/{branche}..{ref}")
        if code != 0 or not n.isdigit() or int(n) == 0:
            continue
        _, quand = _git("log", "-1", "--format=%cs", ref)
        en_attente.append((ref, int(n), quand))
    return en_attente


def etat(branche: str = BRANCHE_DEPLOYEE) -> dict:
    """Ce qui est déployé, ce qui attend. Aucune écriture."""
    _git("fetch", "--quiet", "origin", branche)
    _, local = _git("rev-parse", "--short", "HEAD")
    _, distant = _git("rev-parse", "--short", f"origin/{branche}")
    _, branche_courante = _git("rev-parse", "--abbrev-ref", "HEAD")
    code, retard = _git("rev-list", "--count", f"HEAD..origin/{branche}")
    return {
        "branche_visee": branche,
        "branche_courante": branche_courante,
        "deploye": local,
        "disponible": distant,
        "commits_de_retard": int(retard) if code == 0 and retard.isdigit() else -1,
        "hors_branche": branche_courante != branche,
        "en_attente": branches_en_attente(branche),
    }


def fixtures_vertes(rev: str) -> tuple[bool, str]:
    """Sort `rev` dans un worktree jetable et y lance TOUTES les fixtures.

    On teste le code CANDIDAT, jamais celui qui tourne : tester après déploiement, c'est
    découvrir la casse en production. Le worktree est retiré dans tous les cas.
    """
    dossier = ROOT.parent / f".essai-deploiement-{rev}"
    code, sortie = _git("worktree", "add", "--detach", str(dossier), rev)
    if code != 0:
        return False, f"worktree impossible : {sortie}"
    try:
        python = ROOT / ".venv" / "bin" / "python"
        r = subprocess.run([str(python) if python.exists() else sys.executable,
                            "-m", "tests.run_all"],
                           cwd=str(dossier), capture_output=True, text=True)
        derniere = [l for l in (r.stdout or "").splitlines() if l.strip()]
        return r.returncode == 0, (derniere[-1] if derniere else "(aucune sortie)")
    finally:
        _git("worktree", "remove", "--force", str(dossier))


def deployer() -> tuple[bool, str]:
    r = subprocess.run(["bash", str(UPDATE_SH)], cwd=str(ROOT),
                       capture_output=True, text=True)
    lignes = [l for l in (r.stdout + r.stderr).splitlines() if l.strip()]
    return r.returncode == 0, (lignes[-1] if lignes else "(aucune sortie)")


def rapport(e: dict, action: str, detail: str = "") -> str:
    """Le message Slack. Il ne part que s'il a quelque chose à dire."""
    lignes = []
    if action == "deploye":
        lignes.append(f":rocket: *Déploiement automatique* — {e['deploye']} → "
                      f"{e['disponible']} ({e['commits_de_retard']} commit(s))")
        if detail:
            lignes.append(f"_{detail}_")
    elif action == "refuse":
        lignes.append(f":no_entry: *Déploiement REFUSÉ* — les fixtures échouent sur "
                      f"{e['disponible']}, le serveur reste sur {e['deploye']}")
        lignes.append(f"_{detail}_")
        lignes.append("_Rien n'a été déployé : c'est voulu. Le correctif passe par le "
                      "dépôt, pas par le serveur._")
    elif action == "echec":
        lignes.append(f":warning: *Déploiement en échec* sur {e['disponible']} — "
                      f"fixtures vertes mais `deploy/update.sh` a rendu une erreur")
        lignes.append(f"_{detail}_")
    if e["hors_branche"]:
        lignes.append(f":triangular_flag_on_post: Le serveur est sur "
                      f"*{e['branche_courante']}*, pas sur *{e['branche_visee']}* : "
                      f"le prochain déploiement normal changera de branche.")
    for ref, n, quand in e["en_attente"]:
        lignes.append(f":triangular_flag_on_post: *{n} commit(s) jamais déployés* sur "
                      f"`{ref}` (dernier : {quand}) — ils ne partiront JAMAIS tant qu'ils "
                      f"ne sont pas dans `{e['branche_visee']}`, et seront effacés du "
                      f"serveur au prochain déploiement. Fusion à trancher.")
    return "\n".join(lignes)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Déploie le VPS si la branche a bougé et que "
                                            "les fixtures passent.")
    p.add_argument("--apply", action="store_true", help="Déploie réellement.")
    p.add_argument("--branche", default=BRANCHE_DEPLOYEE)
    args = p.parse_args(argv)

    e = etat(args.branche)
    log.info("Déployé %s · disponible %s · retard %s · branche %s",
             e["deploye"], e["disponible"], e["commits_de_retard"], e["branche_courante"])

    if e["commits_de_retard"] <= 0:
        # RIEN À FAIRE n'est pas RIEN À DIRE : une branche qui attend, ou un serveur sur la
        # mauvaise branche, doivent se voir même un jour sans déploiement.
        msg = rapport(e, "aucun")
        if msg:
            slack.notify(msg)
            print(msg)
        else:
            print(f"À jour ({e['deploye']}), rien à déployer.")
        return 0

    if not args.apply:
        print(f"DRY-RUN — {e['commits_de_retard']} commit(s) à déployer "
              f"({e['deploye']} → {e['disponible']}).")
        print("Les fixtures seraient jouées sur le code candidat, et le déploiement "
              "n'aurait lieu qu'en cas de succès. Relancer avec --apply.")
        return 0

    vertes, resume = fixtures_vertes(f"origin/{args.branche}")
    if not vertes:
        msg = rapport(e, "refuse", resume)
        slack.notify(msg)
        print(msg)
        log.error("Fixtures rouges sur %s — rien déployé (%s).", e["disponible"], resume)
        return 1

    ok, derniere = deployer()
    msg = rapport(e, "deploye" if ok else "echec", derniere)
    slack.notify(msg)
    print(msg)
    # RÈGLE 6 — on rapporte le RÉSULTAT : on RELIT ce que le dépôt dit de lui-même après
    # coup, au lieu d'annoncer ce qu'on a demandé.
    _, apres = _git("rev-parse", "--short", "HEAD")
    log.info("Après déploiement, HEAD = %s (attendu %s)", apres, e["disponible"])
    if ok and apres != e["disponible"]:
        alerte = (f":warning: `deploy/update.sh` a réussi mais HEAD vaut {apres} et non "
                  f"{e['disponible']} — déploiement à vérifier à la main.")
        slack.notify(alerte)
        print(alerte)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
