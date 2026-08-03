#!/usr/bin/env python3
"""LE CHIEN DE GARDE — est-ce que les crons tournent encore ?

LE TROU QUE ÇA FERME, et c'était le plus sérieux de tous. Quatorze automatisations font
vivre ce site, et le 2026-08-03 le constat était : **si le scraper échoue demain matin,
rien ne sonne**. `scripts/homepage_health.py` (13h) verrait la home se vider et
`scripts/site_audit.py` (14h) verrait le site diverger de la base — mais plusieurs jours
plus tard, et sur la CONSÉQUENCE, jamais sur la cause. Entre-temps le catalogue
vieillirait en silence.

C'est la forme la plus coûteuse du défaut que ce dépôt collectionne : un mécanisme qui
s'arrête sans que personne en soit averti. `utils/pipeline_status.record_run()` existait
depuis longtemps et enregistrait fidèlement chaque passage — mais RIEN ne lisait ce
journal pour s'inquiéter d'une absence. On savait ce qui avait tourné ; on ne savait pas
ce qui aurait DÛ tourner.

DEUX SIGNAUX, ET C'EST VOULU. Seuls 7 crons sur 14 appellent `record_run()` : instrumenter
les sept autres aurait demandé de toucher sept fichiers du chemin de production pour un
bénéfice de surveillance. Or ils écrivent tous un JOURNAL (`>> logs/x.log` dans le
crontab), et la date de dernière écriture d'un fichier est un signal universel, gratuit,
qui ne demande de modifier aucun script.
  1. `pipeline_runs` quand il existe — plus riche : on sait aussi si le run a ÉCHOUÉ ;
  2. la date du fichier de log sinon — on sait seulement qu'il a tourné, ce qui suffit
     à répondre à la question posée.
Un cron qui tourne mais dont le journal ne bouge pas est signalé quand même : c'est
l'anomalie, pas le contraire.

CE QU'IL NE FAIT PAS. Il ne relance rien, ne répare rien, n'écrit pas une ligne en base.
Un chien de garde qui essaie de réparer devient une deuxième source de panne — et
celle-là, personne ne la surveillerait.

Usage :
    .venv/bin/python scripts/watchdog_crons.py            # affiche l'état
    .venv/bin/python scripts/watchdog_crons.py --slack    # + alerte Slack si retard
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import pipeline_status

log = get_logger("watchdog-crons")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
LOGS = ROOT / "logs"

# (nom lisible, script, fichier de log, tolérance en heures)
#
# LA TOLÉRANCE, C'EST LA CADENCE + UNE MARGE. Un cron quotidien est en retard au bout de
# ~30 h : la marge absorbe un décalage d'horloge, un run qui déborde, un serveur redémarré
# pendant la nuit. Trop serré, l'alerte crie pour rien et on cesse de la lire ; trop large,
# on découvre la panne trois jours après. 30 h laisse passer UN oubli, jamais deux.
#
# La traduction est ABSENTE de cette table : son cron est volontairement commenté depuis
# le 2026-08-01 (cf. docs/GO_NOGO_TRADUCTION.md). Surveiller un cron qu'on a éteint
# exprès produirait une alerte quotidienne parfaitement inutile — le genre qui apprend à
# ignorer les alertes. À rajouter ici LE JOUR où la ligne 49 du crontab est décommentée.
ATTENDUS = [
    ("Collecte des sources",      "scraper_events",  "scraper.log",          30),
    ("Relève Gmail",              "gmail_collect",   "gmail.log",            30),
    ("Dates",                     "dates",           "dates.log",            30),
    ("Dédoublonnage",             "dedupe",          "dedupe.log",           30),
    ("Lieux",                     "venues",          "venues.log",           30),
    ("Évaluation",                "evaluator",       "evaluator.log",        30),
    ("Lot quotidien",             "daily_batch",     "daily_batch.log",      30),
    ("Référencement",             "seo_batch",       "seo_batch.log",        30),
    # Ajouté le 2026-08-03 avec le cron lui-même : un rafraîchissement de classement qui
    # s'arrête ne casse rien de visible — la section continue d'afficher un tri, seulement
    # il vieillit. C'est précisément le genre de panne qu'on découvre trois semaines plus
    # tard en se demandant pourquoi un événement passé est encore en tête.
    ("Tri « Ça vaut le déplacement »", "refresh_deplacement", "refresh_deplacement.log", 30),
    ("Santé de la home",          "homepage_health", "homepage_health.log",  30),
    ("Relecture du site",         "site_audit",      "site_audit.log",       30),
    ("Sauvegarde de la base",     "backup_db",       "backup.log",           30),
    ("Grand ménage hebdomadaire", "weekly_audits",   "weekly_audits.log",   200),
    ("Récapitulatif hebdomadaire", "weekly_digest",  "weekly_digest.log",   200),
]


def _dernier_run(script: str) -> tuple[datetime | None, dict | None]:
    """Dernier passage enregistré dans pipeline_runs (None si le script n'y écrit pas)."""
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        r = conn.execute("SELECT * FROM pipeline_runs WHERE script=? "
                         "ORDER BY ran_at DESC LIMIT 1", (script,)).fetchone()
        conn.close()
    except sqlite3.Error:
        return None, None
    if not r:
        return None, None
    try:
        return datetime.fromisoformat(r["ran_at"]), dict(r)
    except (ValueError, TypeError):
        return None, dict(r)


def _dernier_log(fichier: str) -> datetime | None:
    """Date de dernière écriture du journal — le signal universel."""
    p = LOGS / fichier
    try:
        return datetime.fromtimestamp(p.stat().st_mtime)
    except OSError:
        return None


def etat(maintenant: datetime | None = None) -> list[dict]:
    """Un dict par cron attendu, avec son retard et sa source d'information."""
    now = maintenant or datetime.now()
    out = []
    for libelle, script, fichier, tolerance in ATTENDUS:
        vu_run, detail = _dernier_run(script)
        vu_log = _dernier_log(fichier)
        # On retient le plus RÉCENT des deux : un script instrumenté qui a planté AVANT
        # son record_run() a quand même laissé une trace dans son journal, et c'est cette
        # trace-là qui dit la vérité sur « a-t-il tourné ».
        vu = max([d for d in (vu_run, vu_log) if d], default=None)
        source = ("aucune trace" if vu is None
                  else "journal + registre" if vu_run and vu_log
                  else "registre" if vu_run else "journal")
        retard_h = None if vu is None else (now - vu).total_seconds() / 3600
        out.append({
            "libelle": libelle, "script": script, "vu": vu, "source": source,
            "retard_h": retard_h, "tolerance": tolerance,
            "en_retard": vu is None or retard_h > tolerance,
            # Un run enregistré EN ERREUR est une anomalie distincte du retard : le cron a
            # bien tourné, il a échoué. Les deux méritent d'être dits, jamais confondus.
            "erreurs": (detail or {}).get("error_count") or 0,
        })
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Vérifie que les crons tournent encore.")
    p.add_argument("--slack", action="store_true",
                   help="Envoie une alerte Slack s'il y a du retard (silence sinon).")
    args = p.parse_args(argv)

    lignes = etat()
    retards = [l for l in lignes if l["en_retard"]]
    en_erreur = [l for l in lignes if not l["en_retard"] and l["erreurs"]]

    print(f"\n{len(lignes)} automatisation(s) surveillée(s) — {len(retards)} en retard, "
          f"{len(en_erreur)} en erreur au dernier passage.\n")
    for l in sorted(lignes, key=lambda x: (not x["en_retard"], x["libelle"])):
        if l["vu"] is None:
            quand, marque = "JAMAIS VUE", "⛔"
        else:
            h = l["retard_h"]
            quand = (f"il y a {h:.0f} h" if h >= 1 else f"il y a {h*60:.0f} min")
            marque = "⛔" if l["en_retard"] else ("⚠️ " if l["erreurs"] else "✅")
        print(f"  {marque} {l['libelle']:<28} {quand:<16} "
              f"({l['source']}, tolérance {l['tolerance']} h)"
              + (f" · {l['erreurs']} erreur(s)" if l["erreurs"] else ""))

    if not args.slack:
        print("\n(lecture seule. --slack pour alerter en cas de retard.)\n")
        return 1 if retards else 0

    # SILENCE QUAND TOUT VA BIEN. Une notification quotidienne « rien à signaler » finit
    # par ne plus être lue, et le jour où elle manque, personne ne le remarque — ce serait
    # reproduire le défaut qu'on répare. On ne parle que s'il y a quelque chose à dire.
    if not retards and not en_erreur:
        log.info("Toutes les automatisations sont à l'heure — pas d'alerte envoyée.")
        return 0

    from utils import slack
    msg = ["🐕 *Chien de garde des automatisations*"]
    for l in retards:
        quand = "JAMAIS VUE" if l["vu"] is None else f"dernier passage il y a {l['retard_h']:.0f} h"
        msg.append(f"⛔ *{l['libelle']}* — {quand} (tolérance {l['tolerance']} h)")
    for l in en_erreur:
        msg.append(f"⚠️ *{l['libelle']}* — a tourné, mais {l['erreurs']} erreur(s)")
    msg.append("\n_Rien n'a été relancé : ce contrôle ne répare pas, il prévient._")
    slack.notify("\n".join(msg))
    log.warning("Alerte envoyée : %d en retard, %d en erreur.", len(retards), len(en_erreur))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
