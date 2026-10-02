#!/usr/bin/env python3
"""Fixture : le détecteur de scripts périodiques jamais planifiés (scripts.audit_orphelins).

D'OÙ ÇA VIENT — audit du 2026-08-18. Cinq scripts en trois semaines annonçaient une cadence
sans être atteints par le crontab (venues, dates_depuis_mail, site_health_check,
autocomplete, auto_deploiement). Ce détecteur existe pour que le sixième se signale seul.

ET IL A ÉCHOUÉ À SA PREMIÈRE ÉCRITURE, c'est pour ça que cette fixture est exigeante. La
version initiale cherchait les mots « cron », « quotidien », « hebdomadaire » dans les
docstrings : 13 signalements sur 133 scripts, en majorité des outils MANUELS qui citaient
ces mots en passant — et elle ratait `autocomplete`, le cas fondateur, dont la docstring
n'en contient aucun. Bruyante ET aveugle sur son propre motif.

D'où deux exigences opposées, que la fixture tient ensemble :

  • le cas FONDATEUR doit être attrapé (une étape déclarée du pipeline, sans mot-clé) ;
  • un outil MANUEL qui parle de cron en passant ne doit PAS l'être — sinon la file
    redevient les « 454 points à contrôler » du 11/08, et personne ne la lit.

Lancer : .venv/bin/python -m tests.test_audit_orphelins
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.audit_orphelins import orphelins  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


def ecrire(base: Path, chemin: str, contenu: str) -> None:
    f = base / chemin
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(contenu, encoding="utf-8")


with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    ecrire(base, "crontab.txt", """
# un vrai crontab, avec des commentaires
0 8 * * * cd /root/evenements && .venv/bin/python scripts/scraper_events.py
30 9 * * * cd /root/evenements && .venv/bin/python scripts/daily_batch.py
""")
    ecrire(base, "deploy/cron_pipeline.sh", """#!/usr/bin/env bash
step "autocomplete" "$PY" -m scripts.autocomplete --cap 30
step "visuels" "$PY" -m scripts.visuals
""")
    # planifié directement
    ecrire(base, "scripts/scraper_events.py", '"""Le scraper.\n\nCron : 0 8 * * *\n"""\n')
    # planifié, et il IMPORTE enrich : la fermeture transitive doit le couvrir
    ecrire(base, "scripts/daily_batch.py",
           '"""Le lot quotidien."""\nfrom scripts.enrich import main\n')
    ecrire(base, "scripts/enrich.py", '"""Rédaction. Cron : appelé par daily_batch."""\n')
    # LE CAS FONDATEUR : étape du pipeline, aucun mot de cadence dans la docstring
    ecrire(base, "scripts/autocomplete.py",
           '"""AGENT D\'AUTO-COMPLÉTION + PORTE QUALITÉ.\n\nBoucle sur les fiches."""\n')
    # deuxième étape du pipeline
    ecrire(base, "scripts/visuals.py", '"""Complète les VISUELS d\'une période."""\n')
    # docstring qui promet une ligne de cron, hors pipeline
    ecrire(base, "scripts/semaine_reminder.py",
           '"""Rappel hebdomadaire.\n\n  0 9 * * 1 rappel de la semaine\n"""\n')
    # LE CAS QUI DOIT PASSER : outil manuel qui PARLE de cron sans en être un
    ecrire(base, "scripts/unmerge.py",
           '"""DÉFAIRE une fusion — à la main, JAMAIS en cron.\n\nUsage manuel."""\n')
    ecrire(base, "scripts/retirer_source.py",
           '"""Retire une source. Ne pas mettre dans un cron quotidien."""\n')

    trouves = dict(orphelins(base))

    verifier("le cas fondateur est attrapé (étape du pipeline, sans mot-clé)",
             "autocomplete" in trouves, str(sorted(trouves)))
    verifier("le motif dit POURQUOI il est signalé",
             "cron_pipeline" in trouves.get("autocomplete", ""), trouves.get("autocomplete"))
    verifier("la deuxième étape du pipeline aussi", "visuals" in trouves)
    verifier("une docstring qui porte une ligne de cron est attrapée",
             "semaine_reminder" in trouves)

    # Les cas qui doivent PASSER — c'est ce volet qui manquait à la première version.
    verifier("un script planifié n'est pas signalé", "scraper_events" not in trouves)
    verifier("un script atteint par IMPORT ne l'est pas non plus (fermeture transitive)",
             "enrich" not in trouves, "enrich signalé à tort")
    verifier("un outil manuel qui dit « jamais en cron » n'est PAS signalé",
             "unmerge" not in trouves, "faux positif : unmerge")
    verifier("un outil manuel qui cite « cron quotidien » en passant non plus",
             "retirer_source" not in trouves, "faux positif : retirer_source")
    verifier("le détecteur ne signale que ces trois-là ici",
             set(trouves) == {"autocomplete", "visuals", "semaine_reminder"}, str(sorted(trouves)))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
