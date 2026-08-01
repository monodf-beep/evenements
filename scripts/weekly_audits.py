#!/usr/bin/env python3
"""Orchestre EN UN SEUL CRON HEBDO tout le nettoyage RÉVERSIBLE et DÉTERMINISTE du
catalogue — pour que Franck n'ait plus à lancer chaque script de nettoyage à la main.

Chaque étape ci-dessous répond aux deux critères qui la rendent sûre à automatiser :
  1. RÉVERSIBLE — corbeille WordPress (jamais suppression définitive) ou statut →
     'rejected' (une re-classification, pas une perte de donnée). AUCUN `--hard` ici.
  2. DÉTERMINISTE — règles fixes (regex, dates, domaines listés), zéro jugement LLM
     ambigu. Les scripts qui font appel à un LLM pour DÉCIDER (pas juste détecter) sont
     volontairement absents de cette liste.

Étapes (dans cet ordre — les purges de bruit d'abord, pour ne pas polluer les audits
plus fins qui suivent) :
  1. purge_out_of_zone   --apply           (hors zone / passés, statut→rejected)
  2. purge_past          --execute         (retenus devenus passés, statut→rejected)
  3. purge_uncompletable --execute         (radar/sans-page incomplétables, statut→rejected)
  4. discard_uncompletable --apply         (même famille, critère complémentaire)
  5. audit_non_events    --apply           (articles de presse publiés à tort → corbeille)
  6. cleanup_as_dupes    --execute         (doublons NÉS dans WordPress → corbeille)
  7. audit_bad_sources                     (lecture seule + republication UNE FOIS des
                                             fiches concernées, sans média et plafonnée —
                                             cf. _etape_bad_sources : le scan ne se vide
                                             jamais tout seul)
  8. image_audit                           (LLM vision, borné --limit — son propre digest
                                             Slack existe déjà, on ne le double pas)

TOUTES les étapes passent par _run_captured : une étape qui plante est signalée dans le
digest et comptée en `error`, elle n'interrompt plus la chaîne (les étapes 7 et 8 étaient
hors filet — leur échec supprimait purement et simplement le digest Slack ET l'entrée
dans l'historique pipeline_runs, donc le seul signal que le nettoyage a eu lieu).

Un seul digest Slack consolidé à la fin (sauf image_audit, qui envoie le sien).

Usage (cron) :
    .venv/bin/python -m scripts.weekly_audits
"""
from __future__ import annotations
import contextlib
import hashlib
import io
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import slack
from utils import pipeline_status

log = get_logger("weekly_audits")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _run_captured(fn, argv, logger_name: str | None = None) -> tuple[int, str]:
    """Exécute `fn(argv)` en capturant à la fois print() et le logger nommé (les scripts
    de ce dépôt utilisent l'un OU l'autre selon leur âge) — pour extraire un résumé sans
    reparser logs/*.log après coup."""
    buf = io.StringIO()
    handler = None
    if logger_name:
        handler = logging.StreamHandler(buf)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger(logger_name).addHandler(handler)
    try:
        with contextlib.redirect_stdout(buf):
            rc = fn(argv) or 0
    except Exception as exc:  # noqa: BLE001 — une étape en échec ne doit pas arrêter les autres
        log.error("Étape en échec (%s) : %s", logger_name or fn, exc)
        rc = 1
    finally:
        if handler:
            logging.getLogger(logger_name).removeHandler(handler)
    return rc, buf.getvalue()


def _tail(text: str, n: int = 3) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return " / ".join(lines[-n:]) if lines else "(rien à signaler)"


# Mémoire des republications de l'étape 7. NON versionné (état d'exécution, pas du code) :
# data/ est déjà le répertoire des données locales du VPS.
_ETAT = Path(os.getenv("WEEKLY_AUDITS_STATE", ROOT / "data" / "weekly_audits_state.json"))
# Plafond par run : borne le temps d'exécution et le martèlement de l'hébergement mutualisé
# le premier dimanche (l'arriéré peut être important). Le reste passe la semaine suivante.
BAD_SOURCES_CAP = int(os.getenv("WEEKLY_BAD_SOURCES_CAP", "25"))


def _charge_etat() -> dict:
    try:
        return json.loads(_ETAT.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return {}


def _ecrit_etat(etat: dict) -> None:
    try:
        _ETAT.parent.mkdir(parents=True, exist_ok=True)
        _ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as exc:
        log.warning("État weekly_audits non sauvegardé (%s) — republication possible en double", exc)


def _empreinte(dropped) -> str:
    """Signature des sources fautives d'une fiche : republier ne change PAS enrich_data,
    donc l'empreinte ne bouge que si une NOUVELLE mauvaise source apparaît (ré-enrichissement)."""
    return hashlib.sha1("|".join(sorted(str(d) for d in dropped)).encode("utf-8")).hexdigest()[:12]


def _etape_bad_sources(_argv=None) -> int:
    """Étape 7 — audit_bad_sources, en lecture seule, + republication des fiches concernées.

    ⚠️ CETTE ÉTAPE NE CONVERGE PAS TOUTE SEULE. `audit_bad_sources._scan` classe une fiche
    d'après `enrich_data.sources` ; la republication, elle, ne fait que RE-RENDRE le post
    (publisher.build_post re-filtre les sources à l'affichage) sans jamais toucher à
    `enrich_data`. La fiche reste donc signalée pour toujours : telle quelle, l'étape
    republiait chaque dimanche la TOTALITÉ des fiches jamais signalées, images réelles
    reversées à chaque fois dans la médiathèque — indéfiniment.

    D'où les trois bornes ici :
      • un état sur disque (id → empreinte des sources fautives) : une fiche n'est
        republiée qu'UNE fois, et à nouveau seulement si de nouvelles sources fautives
        apparaissent (ré-enrichissement) ;
      • `--skip-media` : le correctif est purement textuel, la photo en ligne est déjà
        la bonne — rien à re-téléverser ;
      • un plafond par run (BAD_SOURCES_CAP), l'arriéré s'écoulant sur plusieurs semaines.
    """
    from scripts.audit_bad_sources import _scan as scan_bad_sources
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, wp_post_id_as, url_officiel, url_source, enrich_data "
        "FROM events_raw WHERE enrich_data IS NOT NULL AND enrich_data != ''").fetchall()]
    conn.close()

    flagged = scan_bad_sources(rows)
    etat = _charge_etat()
    deja = etat.get("bad_sources_republies") or {}
    a_faire = [(f["id"], _empreinte(f.get("dropped") or []))
               for f in flagged if f.get("wp_post_id_as")]
    restants = [(i, emp) for i, emp in a_faire if deja.get(str(i)) != emp]
    lot = restants[:BAD_SOURCES_CAP]

    if not lot:
        print(f"{len(flagged)} fiche(s) repérée(s), 0 à republier "
              f"(déjà republiées lors d'un run précédent)")
        return 0

    from scripts.publish_batch_as import main as publish_main
    publish_main(["--ids", *[str(i) for i, _ in lot], "--skip-media"])
    for i, emp in lot:
        deja[str(i)] = emp
    etat["bad_sources_republies"] = deja
    _ecrit_etat(etat)

    reste = len(restants) - len(lot)
    print(f"{len(flagged)} fiche(s) repérée(s), {len(lot)} republiée(s) sans média"
          + (f", {reste} reportée(s) au run suivant (plafond {BAD_SOURCES_CAP})" if reste else ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    sections: list[str] = []
    echecs: list[str] = []

    from scripts.purge_out_of_zone import main as purge_zone_main
    from scripts.purge_past import main as purge_past_main
    from scripts.purge_uncompletable import main as purge_unc_main
    from scripts.discard_uncompletable import main as discard_unc_main
    from scripts.audit_non_events import main as audit_ne_main
    from scripts.cleanup_as_dupes import main as cleanup_dupes_main

    # (libellé, fonction, argv, nom du logger à capturer — None = le script utilise print())
    etapes = [
        ("Hors zone / passés (purge_out_of_zone)", purge_zone_main, ["--apply"], "purge_zone"),
        ("Retenus devenus passés (purge_past)", purge_past_main, ["--execute"], "purge_past"),
        ("Incomplétables radar/sans-page (purge_uncompletable)", purge_unc_main,
         ["--execute"], "purge_uncompletable"),
        ("Incomplétables (discard_uncompletable)", discard_unc_main, ["--apply"], None),
        ("Articles de presse publiés à tort (audit_non_events)", audit_ne_main,
         ["--apply"], "audit-non-events"),
        ("Doublons nés dans WordPress (cleanup_as_dupes)", cleanup_dupes_main,
         ["--execute"], "cleanup_as_dupes"),
    ]
    for libelle, fn, etape_argv, logger_name in etapes:
        # `rc` était calculé puis JETÉ : une étape qui plantait (rc=1 posé par
        # _run_captured) apparaissait dans le digest comme n'importe quelle autre, avec
        # « (rien à signaler) » pour tout message. Un nettoyage hebdomadaire silencieux
        # qui ne nettoie plus est exactement le genre de panne qu'on ne découvre qu'en
        # constatant les dégâts, un mois plus tard.
        rc, out = _run_captured(fn, etape_argv, logger_name)
        marque = "" if not rc else "⚠️ ÉCHEC — "
        sections.append(f"• {libelle} : {marque}{_tail(out)}")
        if rc:
            echecs.append(libelle.split(" (")[0])

    rc, out = _run_captured(_etape_bad_sources, [], "publish_batch_as")
    sections.append(f"• Sources non institutionnelles (audit_bad_sources) : {_tail(out, 1)}")
    if rc:
        echecs.append("audit_bad_sources")

    # image_audit : coût LLM (vision) réel — borné, et il envoie DÉJÀ son propre digest
    # Slack détaillé (liens vers le back-office) : pas la peine de le dupliquer ici.
    from scripts.image_audit import main as image_audit_main
    rc, _ = _run_captured(image_audit_main, ["--limit", "100"], "image_audit")
    sections.append("• Audit visuel (image_audit) : "
                    + ("digest Slack séparé" if not rc else "⚠️ ÉCHEC, voir les logs"))
    if rc:
        echecs.append("image_audit")

    entete = "🧹 *Nettoyage hebdomadaire*"
    if echecs:
        entete = f"⚠️ *Nettoyage hebdomadaire — {len(echecs)} étape(s) en échec* " \
                 f"({', '.join(echecs)})"
    msg = entete + " :\n" + "\n".join(sections)
    slack.notify(msg)
    pipeline_status.record_run("weekly_audits", ok=len(sections) - len(echecs),
                               error=len(echecs), summary=msg[:1900])
    log.info("=== Nettoyage hebdomadaire terminé (%d étape(s) en échec) ===", len(echecs))
    return 1 if echecs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
