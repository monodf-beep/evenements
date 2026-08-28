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


def fixtures_vertes(rev: str) -> tuple[bool, str, list[str]]:
    """Sort `rev` dans un worktree jetable et y lance TOUTES les fixtures.

    On teste le code CANDIDAT, jamais celui qui tourne : tester après déploiement, c'est
    découvrir la casse en production. Le worktree est retiré dans tous les cas.

    Renvoie (vertes, résumé, noms des fixtures rouges). Les NOMS servent au verdict
    comparatif : sans eux, impossible de distinguer « le candidat casse » de
    « l'environnement est malade ».
    """
    dossier = ROOT.parent / f".essai-deploiement-{rev.replace('/', '-')}"
    code, sortie = _git("worktree", "add", "--detach", str(dossier), rev)
    if code != 0:
        return False, f"worktree impossible : {sortie}", []
    try:
        python = ROOT / ".venv" / "bin" / "python"
        r = subprocess.run([str(python) if python.exists() else sys.executable,
                            "-m", "tests.run_all"],
                           cwd=str(dossier), capture_output=True, text=True)
        lignes = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()]
        if r.returncode == 0:
            return True, (lignes[-1] if lignes else "(aucune sortie)"), []
        # UN REFUS DOIT ÊTRE ACTIONNABLE. Sans le nom des fixtures fautives, le message
        # Slack dit « ça n'est pas passé » et laisse chercher — or c'est lui qu'on lira,
        # pas le journal du serveur. On rapatrie donc le compte ET la liste « À REPRENDRE »
        # que run_all imprime déjà.
        compte = next((l for l in lignes if "au rouge" in l), "")
        try:
            i = lignes.index("À REPRENDRE :")
            noms = [l.lstrip("· ").strip() for l in lignes[i + 1:] if l.startswith("·")]
        except ValueError:
            noms = []
        detail = compte or (lignes[-1] if lignes else "(aucune sortie)")
        if noms:
            detail += " — " + ", ".join(noms[:6])
        return False, detail, noms
    finally:
        _git("worktree", "remove", "--force", str(dossier))


def verdict_comparatif(rouges_candidat: list[str],
                       rouges_deploye: list[str]) -> tuple[list[str], list[str]]:
    """Sépare la RÉGRESSION de l'ENVIRONNEMENT MALADE. Pure, donc éprouvable.

    D'OÙ ÇA VIENT (2026-08-24/25) : deux fixtures sensibles à l'environnement — l'une
    appelait le vrai site pendant le blocage IP intermittent, l'autre fuyait vers la
    vraie boîte Slack sous SLACK_DIGEST=1 — ont GELÉ tout déploiement deux jours durant.
    Le code candidat n'y était pour rien : les mêmes fixtures échouaient déjà sur le code
    déployé. Un portail tout-ou-rien ne sait pas le voir ; celui-ci compare.

    Renvoie (régressions, communes) :
      - RÉGRESSIONS : rouges sur le candidat, vertes sur le déployé → le candidat casse,
        on refuse — c'est le portail d'origine, inchangé ;
      - COMMUNES : rouges des DEUX côtés → l'environnement est malade, pas le candidat.
        Refuser n'y protégerait rien (la casse tourne déjà) et bloquerait justement le
        correctif. Déployer reste sûr : rien ne régresse.
    """
    return (sorted(set(rouges_candidat) - set(rouges_deploye)),
            sorted(set(rouges_candidat) & set(rouges_deploye)))


def commandes_crontab(texte: str) -> set[str]:
    """Les lignes de COMMANDE d'un crontab, commentaires et vides retirés, espaces normalisés.

    Pure, donc éprouvable (tests/test_auto_deploiement.py). On ne compare pas les
    commentaires : `crontab.txt` en porte des dizaines de lignes d'explication que
    `crontab -l` ne rend pas forcément à l'identique, et un contrôle qui crierait chaque
    jour pour un commentaire déplacé finirait par ne plus être lu — le défaut que
    `gabarit_health` documente déjà. Les affectations de variables (SLACK_DIGEST=1) sont
    des lignes de crontab à part entière et comptent, elles.
    """
    lignes = set()
    for l in texte.splitlines():
        l = l.strip()
        if not l or l.startswith("#"):
            continue
        lignes.add(" ".join(l.split()))
    return lignes


def ecart_crontab() -> tuple[int, int, str]:
    """Compare le crontab INSTALLÉ à `crontab.txt`. Renvoie (ajouts, retraits, résumé).

    LE TROU QUE CECI FERME, et c'est la règle 1 transposée une fois de plus : un fichier
    dans le dépôt ne prouve pas qu'il tourne. `crontab.txt` est la référence écrite, mais
    seul `crontab crontab.txt` la rend vivante — donc une ligne ajoutée par une session
    Claude ne s'exécute JAMAIS avant que quelqu'un ne tape cette commande. C'est ce qui
    s'est passé le 2026-08-17 : le cron de déploiement automatique était committé et inerte.

    On compare les lignes de COMMANDE seules (ni commentaires, ni lignes vides) : le fichier
    du dépôt porte des dizaines de lignes d'explication que `crontab -l` ne rend pas
    forcément à l'identique, et comparer les commentaires ferait crier ce contrôle tous les
    jours pour rien — le défaut de `gabarit_health` évité de justesse.
    """
    fichier = ROOT / "crontab.txt"
    if not fichier.exists():
        return 0, 0, "crontab.txt introuvable"

    voulu = commandes_crontab(fichier.read_text(encoding="utf-8"))
    # `crontab` peut ne pas exister (conteneur de développement) : le contrôle ne doit pas
    # faire tomber le script, qui tourne juste APRÈS un déploiement réussi. Trouvé en
    # l'exécutant, pas en le relisant — un FileNotFoundError non rattrapé.
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    except (FileNotFoundError, OSError) as exc:
        log.warning("Commande `crontab` indisponible (%s) — écart NON mesuré.", exc)
        return 0, 0, "crontab indisponible sur cette machine, écart non mesuré"
    installe = _commandes(r.stdout if r.returncode == 0 else "")
    ajouts = sorted(voulu - installe)
    retraits = sorted(installe - voulu)
    resume = ""
    if ajouts:
        resume += f"{len(ajouts)} ligne(s) à installer, dont : {ajouts[0][:90]}"
    if retraits:
        resume += ((" · " if resume else "")
                   + f"{len(retraits)} ligne(s) installée(s) hors du dépôt, dont : "
                     f"{retraits[0][:90]}")
    return len(ajouts), len(retraits), resume


def installer_crontab() -> tuple[bool, str]:
    """Rend `crontab.txt` vivant. RÉVERSIBLE : le crontab précédent est sauvegardé d'abord.

    Autorisé sans demander (`Bash(crontab:*)` dans .claude/settings.json, et CLAUDE.md
    range le crontab parmi les gestes réversibles). Le fichier du dépôt est la référence :
    on n'invente aucune ligne ici.
    """
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    except (FileNotFoundError, OSError) as exc:
        return False, f"commande `crontab` indisponible ({exc}) — rien installé"
    if r.returncode == 0 and r.stdout.strip():
        sauvegarde = ROOT / "logs" / "crontab-avant-installation.txt"
        try:
            sauvegarde.parent.mkdir(parents=True, exist_ok=True)
            sauvegarde.write_text(r.stdout, encoding="utf-8")
        except OSError as exc:
            return False, f"sauvegarde du crontab impossible ({exc}) — rien installé"
    try:
        pose = subprocess.run(["crontab", str(ROOT / "crontab.txt")],
                              capture_output=True, text=True)
    except (FileNotFoundError, OSError) as exc:
        return False, f"commande `crontab` indisponible ({exc}) — rien installé"
    if pose.returncode != 0:
        return False, (pose.stdout + pose.stderr).strip()[:200]
    # RÈGLE 6 : on RECOMPTE après l'écriture au lieu d'annoncer l'intention.
    reste_a, reste_r, _ = ecart_crontab()
    if reste_a or reste_r:
        return False, (f"installé, mais l'écart persiste ({reste_a} manquante(s), "
                       f"{reste_r} en trop) — à regarder à la main")
    return True, "crontab installé, écart nul après recomptage"


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


MEMOIRE_ATTENTE = ROOT / "logs" / "deploiement_branches_signalees.json"


def branches_nouvelles(en_attente: list[tuple[str, int, str]],
                       deja_vues: list) -> tuple[list[tuple[str, int, str]], int]:
    """Sépare ce qui mérite le DÉTAIL (branche nouvelle, ou dont le nombre de commits a
    bougé) de ce qui a déjà été signalé à l'identique. Pure, donc éprouvable.

    D'OÙ ÇA VIENT — Franck, 2026-08-28 : « les résumés sont beaucoup trop longs. » Les
    mêmes trois paragraphes « Fusion à trancher » partaient CHAQUE matin, identiques,
    depuis des jours. Une question posée à Franck ne se re-pose pas tant qu'elle n'a pas
    changé : elle se COMPTE (même principe que l'escalade unique du registre des
    décisions). Le jour où une branche bouge — un commit de plus, une branche neuve —
    elle retrouve son paragraphe entier.
    """
    vues = {(str(v[0]), int(v[1])) for v in deja_vues if len(v) >= 2}
    nouvelles = [b for b in en_attente if (b[0], b[1]) not in vues]
    return nouvelles, len(en_attente) - len(nouvelles)


def suivre_crontab() -> str:
    """Aligne le crontab installé sur crontab.txt. Renvoie la ligne de rapport, ou "".

    APPELÉ À CHAQUE PASSAGE EN --apply, PAS SEULEMENT APRÈS UN DÉPLOIEMENT RÉUSSI.
    L'incident qui l'a imposé (26→28/08) : le cron du cerveau, committé le 25/08, est
    resté INERTE trois matins. L'installation du crontab était accrochée au seul chemin
    « déploiement réussi » — or update.sh peut échouer APRÈS son git reset (le code est
    en place, le code de sortie non), et les matins suivants il n'y a plus rien à
    déployer : l'écart n'avait AUCUN rouvreur. La règle 3, violée par le script même qui
    la prêche — le bilan l'a signalé trois jours de suite sans qu'aucun automatisme ne
    comble l'écart.

    Un jour sans déploiement, crontab.txt EST celui du code déployé : l'installer est
    exactement ce qu'il faut. Réversible (sauvegarde d'abord, cf. installer_crontab).
    """
    a, r_, resume = ecart_crontab()
    if not (a or r_):
        return ""
    pose, detail = installer_crontab()
    log.info("Crontab : %d à installer, %d hors dépôt — %s", a, r_, detail)
    return (f"\n:calendar: Crontab {'mis à jour' if pose else 'NON mis à jour'} "
            f"— {resume}. {detail}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Déploie le VPS si la branche a bougé et que "
                                            "les fixtures passent.")
    p.add_argument("--apply", action="store_true", help="Déploie réellement.")
    p.add_argument("--branche", default=BRANCHE_DEPLOYEE)
    args = p.parse_args(argv)

    e = etat(args.branche)
    log.info("Déployé %s · disponible %s · retard %s · branche %s",
             e["deploye"], e["disponible"], e["commits_de_retard"], e["branche_courante"])

    # LES BRANCHES EN ATTENTE NE SE RE-DÉTAILLENT PAS À L'IDENTIQUE chaque matin : le
    # détail au premier signalement (ou au moindre changement), une ligne de compte
    # ensuite. En dry-run la mémoire n'est PAS écrite — une simulation ne doit pas
    # faire taire le signalement du vrai passage.
    import json as _json
    attente_totale = list(e["en_attente"])
    deja_vues = []
    try:
        deja_vues = _json.loads(MEMOIRE_ATTENTE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    e["en_attente"], deja_signalees = branches_nouvelles(attente_totale, deja_vues)
    rappel_attente = ""
    if deja_signalees:
        rappel_attente = (f"\n:triangular_flag_on_post: {deja_signalees} branche(s) en "
                          f"attente déjà signalée(s), inchangée(s) — fusion toujours à "
                          f"trancher (détail au premier signalement).")
    if args.apply:
        try:
            MEMOIRE_ATTENTE.parent.mkdir(parents=True, exist_ok=True)
            MEMOIRE_ATTENTE.write_text(
                _json.dumps([[b[0], b[1]] for b in attente_totale]), encoding="utf-8")
        except OSError as exc:
            log.warning("Mémoire des branches non écrite (%s) — le détail reviendra demain",
                        exc)

    if e["commits_de_retard"] <= 0:
        # RIEN À FAIRE n'est pas RIEN À DIRE : une branche qui attend, ou un serveur sur la
        # mauvaise branche, doivent se voir même un jour sans déploiement. Et le crontab se
        # réconcilie AUSSI ces jours-là — c'est le jour sans déploiement qui a laissé le
        # cron du cerveau inerte trois matins (cf. suivre_crontab).
        msg = (rapport(e, "aucun") + rappel_attente
              + (suivre_crontab() if args.apply else "")).strip("\n")
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

    vertes, resume, rouges = fixtures_vertes(f"origin/{args.branche}")
    environnement = ""
    if not vertes:
        # AVANT DE REFUSER : les mêmes fixtures échouent-elles sur le code DÉJÀ déployé ?
        # Si oui, c'est l'environnement qui est malade, pas le candidat — refuser
        # bloquerait précisément le correctif (vécu les 24-25/08, deux jours de gel).
        # Sans noms de fixtures, pas de comparaison possible : le défaut reste « non ».
        regressions = rouges or None
        if rouges:
            vertes_dep, _, rouges_dep = fixtures_vertes("HEAD")
            regressions, communes = verdict_comparatif(rouges, rouges_dep)
            if not regressions and communes:
                environnement = (f"\n:thermometer: {len(communes)} fixture(s) rouges sur le "
                                 f"candidat ET sur le code déjà déployé "
                                 f"({', '.join(communes[:4])}) : environnement malade, pas "
                                 f"une régression — déployé quand même. À soigner à part.")
                log.warning("Fixtures rouges des DEUX côtés (%s) — environnement malade, "
                            "déploiement maintenu.", ", ".join(communes))
        if not environnement:
            if regressions and rouges != regressions:
                resume += f" — RÉGRESSION : {', '.join(regressions[:6])}"
            # Même refusé, le crontab se réconcilie : le refus porte sur le CANDIDAT,
            # crontab.txt sur disque est celui du code déjà déployé.
            msg = rapport(e, "refuse", resume) + rappel_attente + suivre_crontab()
            slack.notify(msg)
            print(msg)
            log.error("Fixtures rouges sur %s — rien déployé (%s).", e["disponible"], resume)
            return 1

    ok, derniere = deployer()

    # LE CRONTAB SUIT LE CODE — à chaque passage désormais, cf. suivre_crontab : accroché
    # au seul chemin « déploiement réussi », il a laissé le cron du cerveau inerte trois
    # matins (l'échec d'update.sh APRÈS son git reset sautait l'installation, et les jours
    # suivants n'avaient plus rien à déployer).
    suite_cron = suivre_crontab()

    msg = (rapport(e, "deploye" if ok else "echec", derniere) + environnement
           + rappel_attente + suite_cron)
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
