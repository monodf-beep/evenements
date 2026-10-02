#!/usr/bin/env python3
"""Les scripts qui ANNONCENT une cadence, et qu'aucun cron n'atteint.

D'OÙ ÇA VIENT — l'audit du 2026-08-18 (docs/AUDIT_COMPLETUDE_2026-08-18.md). En cherchant
pourquoi les fiches restent incomplètes, on a trouvé que `scripts/autocomplete.py` — décrit
dans son propre en-tête comme « le cœur de la demande de Franck », l'orchestrateur qui
enchaîne date → lieu → image — n'est appelé que par `deploy/cron_pipeline.sh`, qui n'est
pas planifié. Il ne s'exécute pas.

CE N'EST PAS UN ACCIDENT ISOLÉ, C'EST UN MOTIF. Cinq cas en trois semaines :

    venues.py            « cron : après la datation » — jamais planifié (02/08)
    dates_depuis_mail    ajouté au seul cron_pipeline.sh, donc inerte (11/08)
    site_health_check    « tourne chaque semaine en cron » — faux (12/08)
    autocomplete         jamais planifié (trouvé le 18/08)
    auto_deploiement     écrit et committé la veille, inerte jusqu'à l'installation

La règle 1 de CLAUDE.md a donc un frère : **un script dans le dépôt ne prouve pas qu'il
s'exécute.** `watchdog_crons` surveille les passages des scripts qu'il CONNAÎT ; il ne peut
pas signaler l'absence de ce qui n'a jamais été inscrit.

COMMENT ON ÉVITE DE CRIER AU LOUP. Ce dépôt contient des dizaines d'outils manuels
(purges, audits ponctuels, réparations) qui n'ont RIEN à faire dans un crontab. Les
signaler serait le défaut des « 454 points à contrôler » du 11/08 : une file que personne
ne peut traiter. On ne retient donc qu'un signal étroit et vérifiable :

    le script DIT lui-même qu'il est périodique (« cron », « quotidien », « chaque
    semaine », « hebdomadaire »… dans sa docstring), ET aucune ligne du crontab ne
    l'atteint — ni directement, ni par un script qui l'importe.

C'est exactement ce qui rendait les cinq cas ci-dessus détectables : leur documentation
promettait une cadence qu'ils n'avaient pas.

Lecture seule, aucun coût, aucune écriture.

    .venv/bin/python -m scripts.audit_orphelins
    .venv/bin/python -m scripts.audit_orphelins --slack
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# DEUX SIGNAUX EXACTS, ET PAS UN MOT-CLÉ. Ma première version cherchait « cron »,
# « quotidien », « hebdomadaire » dans les docstrings : elle a signalé 13 scripts sur 133,
# dont une majorité d'OUTILS MANUELS qui citaient ces mots en passant (unmerge,
# retirer_source, resolve_wp_collision…) — et elle a RATÉ `autocomplete`, le cas qui l'a
# fait naître, dont la docstring ne contient aucun de ces mots. Un détecteur bruyant qui
# manque son propre cas fondateur ne sera jamais lu : c'est le défaut des « 454 points à
# contrôler » du 11/08, reproduit en une heure.
#
# On ne garde donc que ce qui est VÉRIFIABLE, jamais interprété :
#
#   A. le script est une ÉTAPE DÉCLARÉE de deploy/cron_pipeline.sh — ce fichier est le
#      pipeline que quelqu'un a écrit pour tourner chaque jour, et qui n'est pas planifié.
#      Y figurer est une déclaration d'intention explicite, pas un indice de style ;
#   B. sa docstring porte une LIGNE DE CRON, ou la mention « Cron : ». Écrire « 30 9 * * * »
#      dans son propre en-tête, c'est promettre une cadence noir sur blanc.
LIGNE_DE_CRON = re.compile(r"(^|\n)\s*#?\s*Cron\s*:|\b[0-9]{1,2} [0-9*/,-]+ \* \* [0-9*]",
                           re.IGNORECASE)

# Scripts lancés par un agent Claude ou par un shell, donc atteints sans passer par une
# ligne `python -m`. Recensés ici plutôt que devinés.
ENTREES_SHELL = ("agent_quotidien.sh", "bilan_matin.sh", "revue_hebdo.sh", "cerveau.sh")


def docstring(fichier: Path) -> str:
    """Le début du fichier, là où vit la docstring. Lecture textuelle : importer le
    module exécuterait du code et demanderait ses dépendances."""
    texte = fichier.read_text(encoding="utf-8", errors="replace")
    return texte[:4000]


def annonce_une_cadence(texte: str) -> bool:
    """Signal B : la docstring promet une cadence noir sur blanc."""
    tete = texte.split('"""')
    doc = tete[1] if len(tete) > 2 else texte[:1500]
    return bool(LIGNE_DE_CRON.search(doc))


def etapes_du_pipeline(racine: Path) -> set[str]:
    """Signal A : les étapes déclarées de deploy/cron_pipeline.sh.

    Ce fichier décrit un pipeline quotidien complet — et le crontab réel appelle les
    scripts un par un, sans jamais l'invoquer. Tout ce qu'il déclare et que le crontab
    n'atteint pas est, par construction, une étape qui ne tourne pas.
    """
    f = racine / "deploy" / "cron_pipeline.sh"
    if not f.exists():
        return set()
    texte = f.read_text(encoding="utf-8", errors="replace")
    return {m.group(1) for m in re.finditer(r"scripts\.([a-z0-9_]+)", texte)}


def planifies(crontab: str) -> set[str]:
    """Les modules que le crontab atteint DIRECTEMENT."""
    noms = set()
    for ligne in crontab.splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        for m in re.finditer(r"scripts[./]([a-z0-9_]+)", ligne):
            noms.add(m.group(1))
    return noms


def atteints(racine: Path, directs: set[str]) -> set[str]:
    """Fermeture transitive : un script importé par un script planifié tourne aussi.

    Sans cette fermeture, `enrich` (appelé par `daily_batch`) passerait pour un orphelin —
    et un détecteur qui se trompe une fois sur deux ne sera plus lu.
    """
    vus, a_voir = set(), list(directs)
    while a_voir:
        nom = a_voir.pop()
        if nom in vus:
            continue
        vus.add(nom)
        f = racine / "scripts" / f"{nom}.py"
        if not f.exists():
            continue
        texte = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"from\s+scripts\.([a-z0-9_]+)\s+import|import\s+scripts\.([a-z0-9_]+)",
                             texte):
            a_voir.append(m.group(1) or m.group(2))
    return vus


def orphelins(racine: Path | None = None) -> list[tuple[str, str]]:
    """(nom, première ligne de sa docstring) des scripts périodiques que rien n'atteint."""
    racine = racine or ROOT
    crontab = (racine / "crontab.txt").read_text(encoding="utf-8", errors="replace")
    joignables = atteints(racine, planifies(crontab))
    # Les shells planifiés lancent des agents qui appellent des scripts : on considère
    # atteint ce qu'ils citent, sans quoi on signalerait le travail de l'agent quotidien.
    for sh in ENTREES_SHELL:
        f = racine / "scripts" / sh
        if f.exists():
            texte = f.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r"scripts[./]([a-z0-9_]+)", texte):
                joignables |= atteints(racine, {m.group(1)})
    for consigne in (racine / "config").glob("consigne_*.txt"):
        texte = consigne.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"scripts[./]([a-z0-9_]+)", texte):
            joignables |= atteints(racine, {m.group(1)})

    pipeline = etapes_du_pipeline(racine)
    trouves = []
    for f in sorted((racine / "scripts").glob("*.py")):
        nom = f.stem
        if nom in joignables:
            continue
        texte = docstring(f)
        if nom not in pipeline and not annonce_une_cadence(texte):
            continue
        premiere = ""
        if '"""' in texte:
            corps = texte.split('"""')[1].strip().splitlines()
            premiere = corps[0] if corps else ""
        motif = "étape de cron_pipeline.sh" if nom in pipeline else "cadence annoncée en docstring"
        trouves.append((nom, f"[{motif}] {premiere[:88]}"))
    return trouves


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Scripts périodiques que le crontab n'atteint pas.")
    p.add_argument("--slack", action="store_true")
    args = p.parse_args(argv)

    trouves = orphelins()
    total = len(list((ROOT / "scripts").glob("*.py")))
    # RÈGLE 6 : le compteur dit son périmètre, et un zéro dit combien de cas se sont
    # présentés — sinon « 0 orphelin » et « je n'ai rien regardé » se ressemblent.
    entete = (f"🧭 *Scripts annoncés périodiques mais jamais planifiés* — {len(trouves)} "
              f"sur {total} script(s) examiné(s)")
    print(entete)
    for nom, resume in trouves:
        print(f"  · scripts/{nom}.py — {resume}")
    if not trouves:
        print("  (aucun : tout ce qui se dit périodique est atteint par le crontab)")
    if args.slack and trouves:
        from utils import slack
        slack.notify(entete + "\n"
                     + "\n".join(f"• `scripts/{n}.py` — {r}" for n, r in trouves[:8])
                     + "\n_Un script dans le dépôt ne prouve pas qu'il s'exécute : "
                       "soit on l'inscrit au crontab, soit on écrit dans sa docstring "
                       "qu'il est manuel._")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
