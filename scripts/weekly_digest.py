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


def _qualite(conn: sqlite3.Connection) -> list[str]:
    """Les manques de QUALITÉ des fiches en ligne encore devant nous — crédits d'images
    et notes du panel lecteurs.

    DEMANDE DE FRANCK, 2026-08-04 : « je n'ai rien par rapport aux crédits images, rien
    par rapport au panel des personas. » Il avait raison sur les deux : tout le dispositif
    surveillait des FILES (à enrichir, à traduire, à vérifier) et des ABSENCES (crons
    arrêtés), jamais la COMPLÉTUDE de ce qui est déjà publié. Une fiche en ligne sans
    crédit photo est un problème de droit d'auteur, pas un confort ; une fiche sans note
    de panel est passée au travers du portillon de publication, ou a été publiée avant que
    le panel existe — dans les deux cas, personne ne le comptait nulle part.

    Règle 5 : uniquement ce qui est encore devant nous. Compléter le crédit d'une photo
    dont l'événement est passé ne protège rien ni personne.

    Règle 1 assumée : « en ligne » signifie ici `wp_post_id_as` renseigné et non vérifié
    côté WordPress — c'est un compteur hebdomadaire, pas un audit ; les posts corbeillés
    gonflent le compte d'une poignée, et l'audit REST de reconcile_hors_ligne (même
    digest) donne le chiffre exact de ce biais."""
    lignes = []
    try:
        rows = conn.execute(
            "SELECT url_image, image_source, image_credit, home_score, recurring, "
            "       date_event_start, date_event_end FROM events_raw "
            "WHERE COALESCE(wp_post_id_as, 0) > 0 AND wp_deleted_at IS NULL "
            "  AND COALESCE(statut,'') NOT IN ('merged','rejected')").fetchall()
    except sqlite3.OperationalError:
        return []
    from datetime import date
    auj = date.today().isoformat()
    sans_credit = sans_panel = vraies_images = vivantes = 0
    for r in rows:
        d = r["date_event_end"] or r["date_event_start"]
        if not (r["recurring"] or not d or str(d)[:10] >= auj):
            continue
        vivantes += 1
        # Une BANNIÈRE de repli est à nous : elle n'exige pas de crédit. Seule une vraie
        # image (affiche, photo récupérée) engage un droit d'auteur.
        if (r["url_image"] or "").strip() and (r["image_source"] or "") != "banner":
            vraies_images += 1
            if not (r["image_credit"] or "").strip():
                sans_credit += 1
        if r["home_score"] is None:
            sans_panel += 1
    if sans_credit:
        lignes.append(f"• {sans_credit}/{vraies_images} — vraie image SANS CRÉDIT "
                      f"(droit d'auteur : compléter, ou passer en bannière)")
    if sans_panel:
        lignes.append(f"• {sans_panel}/{vivantes} — en ligne SANS note du panel lecteurs "
                      f"(publiées avant le panel, ou passées au travers du portillon)")
    return lignes


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

    qualite = _qualite(conn)
    if qualite:
        lines.append("")
        lines.append("*Qualité des fiches en ligne (encore devant nous) :*")
        lines.extend(qualite)

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
