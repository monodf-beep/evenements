#!/usr/bin/env python3
"""Digest Slack hebdomadaire — la version « pour Franck » de scripts/status_report.py,
postée automatiquement au lieu d'avoir à se connecter pour la lire.

Usage (cron, hebdo) :
    .venv/bin/python -m scripts.weekly_digest
"""
from __future__ import annotations
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import slack
from utils import pipeline_status
from scripts.status_report import _backlog_counts, _KNOWN_SCRIPTS

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _garees(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Les fiches écartées de la vitrine À LA MAIN (`home_override='excluded'`).

    POURQUOI ELLES SONT COMPTÉES ICI. Cet état est parfaitement réversible — un bouton du
    back-office le lève — mais RIEN ne disait jamais combien de fiches y dormaient, ni
    depuis quand. C'est très exactement la troisième question de docs/ETATS_TERMINAUX.md
    (« où se voit le nombre de fiches garées ? »), et elle n'avait pas de réponse.

    Le cas qui l'a révélé, le 2026-08-04 : [2153] « Une semaine pas plus » a été exclue
    parce que sa description était celle d'un autre événement et qu'aucune source ne
    permettait de récupérer la vraie (domaine source en 403, dix sauvegardes déjà
    polluées). Décision juste. Mais le motif peut CESSER — `autocomplete` peut la
    re-remplir un jour depuis une autre source — et personne ne se souviendrait alors de
    lever l'exclusion. La fiche resterait invisible pour une raison disparue.

    Règle 5 : seules celles encore devant nous. Une fiche exclue dont l'événement est
    passé n'intéresse plus personne, et l'afficher noierait celles qui comptent."""
    try:
        return conn.execute(
            "SELECT id, title, home_override_at, date_event_start, date_event_end "
            "FROM events_raw WHERE home_override='excluded' "
            "  AND (COALESCE(date_event_end, date_event_start) >= date('now') "
            "       OR COALESCE(date_event_end, date_event_start) IS NULL) "
            "ORDER BY COALESCE(home_override_at, '') ASC").fetchall()
    except sqlite3.OperationalError:
        return []


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)

    lines = ["📊 *Digest hebdomadaire — Agenda Sabauda*", "", "*Automatisations :*"]

    # QUI GARDE LE GARDIEN — trou trouvé au tour des automatisations du 2026-08-04. Le
    # chien de garde de 12h surveille dix-huit automatisations, mais rien ne surveillait
    # LE CHIEN DE GARDE : sa panne est un silence, et un silence est précisément ce qu'il
    # existe pour dénoncer. Il ne peut pas se surveiller lui-même (s'il ne tourne pas, il
    # ne peut rien signaler) — c'est donc le digest du lundi qui le fait, par la date de
    # son journal, et le chien de garde surveille le digest en retour (tolérance 200 h) :
    # la boucle est fermée, chacun couvre l'angle mort de l'autre.
    try:
        from datetime import datetime, timedelta
        age = datetime.now() - datetime.fromtimestamp(
            (ROOT / "logs" / "watchdog.log").stat().st_mtime)
        if age > timedelta(hours=30):
            lines.append(f"• 🔴 *LE CHIEN DE GARDE LUI-MÊME* n'a pas tourné depuis "
                         f"{age.total_seconds() / 3600:.0f} h — les absences des autres "
                         f"automatisations ne sont PLUS détectées. Vérifier le crontab.")
    except OSError:
        lines.append("• 🔴 *LE CHIEN DE GARDE LUI-MÊME* : aucun journal "
                     "(logs/watchdog.log absent) — a-t-il jamais tourné sur ce serveur ?")
    runs = pipeline_status.last_runs(limit_per_script=1)
    for script in _KNOWN_SCRIPTS:
        entries = runs.get(script)
        if not entries:
            lines.append(f"• `{script}` : jamais exécuté")
            continue
        r = entries[0]
        icon = "✅" if not r["error_count"] else "⚠️"
        lines.append(f"• {icon} `{script}` — {r['ran_at']} "
                     f"(ok={r['ok_count']} warn={r['warn_count']} error={r['error_count']})")

    lines.append("")
    lines.append("*Reste à faire :*")
    for label, n in _backlog_counts(conn).items():
        lines.append(f"• {n} — {label}")

    garees = _garees(conn)
    if garees:
        # Nommées et datées, pas seulement comptées : c'est la DATE qui donne envie d'aller
        # revoir. « 3 fiches exclues » se lit et s'oublie ; « exclue depuis le 4 août » se
        # rouvre.
        lines.append("")
        lines.append(f"*Écartées de la vitrine à la main ({len(garees)})* — "
                     f"le motif tient-il toujours ?")
        for r in garees[:6]:
            depuis = (r["home_override_at"] or "")[:10] or "date inconnue"
            lines.append(f"• [{r['id']}] {(r['title'] or '')[:52]} — depuis {depuis}")
        if len(garees) > 6:
            lines.append(f"• … {len(garees) - 6} autres")
    conn.close()

    msg = "\n".join(lines)
    slack.notify(msg)
    pipeline_status.record_run("weekly_digest", ok=1, summary=msg[:1900])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
