#!/usr/bin/env python3
"""Automatise le PROTOCOLE DE LOT (docs/BACKLOG.md, 2026-08-01) : sélectionne un lot
d'événements, les enrichit, vérifie CHACUN avec les mêmes règles que
`scripts/batch_report.py`, ne publie QUE ceux qui sont COMPLETS, et notifie Slack —
pour que le protocole tourne seul au lieu d'être déroulé à la main sur le VPS.

Rien n'est publié à moitié fait : un événement qui reste INCOMPLET (score/article/
panel/date manquant) est laissé en base tel quel, il retentera au prochain run
(cap quotidien, mode auto : score bas → court, score haut/matière officielle →
long+panel, cf. scripts/enrich.py). Slack liste les incomplets avec la RAISON
précise, pour que Franck sache s'il doit intervenir sans avoir à se connecter.

Usage (cron) :
    .venv/bin/python -m scripts.daily_batch                # lot du jour (DAILY_BATCH_SIZE)
    .venv/bin/python -m scripts.daily_batch --cap 5         # override ponctuel
"""
from __future__ import annotations
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import slack
from utils import completeness as comp
from utils import radar
from scripts.enrich import select_events, main as enrich_main, BATCH_SIZE as ENRICH_BATCH
from scripts.batch_report import _row_report
from scripts.publish_batch_as import main as publish_main

log = get_logger("daily_batch")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
DAILY_BATCH_SIZE = int(os.getenv("DAILY_BATCH_SIZE", "10"))


def _fetch(conn: sqlite3.Connection, ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    return {r["id"]: dict(r) for r in
            conn.execute(f"SELECT * FROM events_raw WHERE id IN ({ph})", ids).fetchall()}


def _porte_publication(ev: dict, today: str) -> list[str]:
    """Raisons de NE PAS publier cet événement, en plus du rapport de batch_report.

    ⚠️ POURQUOI CE DOUBLON APPARENT — il ne l'est pas. `publish_batch_as` applique deux
    garde-fous à sa sélection : la porte qualité `utils/completeness` (lieu, ville,
    territoire, catégorie, image) et le filtre « à venir ». Or les DEUX sont désactivés
    dès qu'on passe `--ids` (voir publish_batch_as._select et la condition
    `not args.allow_incomplete and not args.ids`) — un contournement VOULU pour la
    republication manuelle après correctif, où la décision est déjà prise par un humain.
    daily_batch, lui, passe `--ids` sans aucun humain dans la boucle : il hérite donc du
    contournement sans en avoir la légitimité. Ces contrôles sont refaits ICI, avant
    l'appel, pour que le seul chemin non supervisé du dépôt qui crée des fiches PUBLIQUES
    soit au moins aussi strict que le chemin manuel.

    `batch_report._row_report` ne les couvre pas : il exige une date ISO mais jamais
    qu'elle soit à venir, et il ne regarde l'image qu'APRÈS publication (`if wp_id`) —
    trop tard. `purge_past` ne tourne que le dimanche : sans ce filtre, un événement
    scrapé en retard peut partir en ligne et y rester jusqu'à six jours."""
    raisons = []
    manques = comp.missing_labels(ev)
    if manques:
        raisons.append(f"  ✗ complétude   : manque {', '.join(manques)}")
    fin = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()
    jour = fin[:10] if re.match(r"\d{4}-\d{2}-\d{2}", fin) else ""
    if jour and jour < today:
        raisons.append(f"  ✗ date         : DÉJÀ PASSÉ (fin {jour} < {today})")
    # VERROU RADAR (utils/radar.py) : `publish_batch_as` l'applique aussi, mais il faut
    # le SAVOIR ici — sinon la fiche est comptée « complète », publish_main la retient
    # en silence, et Slack annonce « ✅ … — WP#None ». Le contrôle est donc refait avant
    # l'appel, pour que la fiche soit annoncée comme RETENUE avec sa vraie raison.
    # (Pas de `parent` à chercher : select_events exclut déjà les traductions.)
    raison_radar = radar.publication_block_reason(ev)
    if raison_radar:
        raisons.append(f"  ✗ source       : {raison_radar}")
    return raisons


def _run(argv: list[str]) -> int:
    load_dotenv(ROOT / ".env")
    cap = DAILY_BATCH_SIZE
    if "--cap" in argv:
        try:
            cap = int(argv[argv.index("--cap") + 1])
        except (IndexError, ValueError):
            pass

    if cap > ENRICH_BATCH:
        # select_events applique `LIMIT ENRICH_BATCH` : demander 20 alors que ENRICH_BATCH
        # vaut 10 en renvoie silencieusement 10. On le DIT plutôt que de laisser croire
        # que le lot du jour fait la taille demandée.
        log.warning("cap demandé %d > ENRICH_BATCH (%d) : le lot sera plafonné à %d. "
                    "Relever ENRICH_BATCH dans .env pour un lot plus gros.",
                    cap, ENRICH_BATCH, ENRICH_BATCH)

    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = select_events(conn, [], "", "")
    conn.close()
    ids = [r["id"] for r in rows][:cap]

    if not ids:
        log.info("Lot du jour : rien à enrichir (file vide sous le seuil MIN_SCORE).")
        slack.notify("📭 Lot quotidien : rien à enrichir aujourd'hui (file vide).")
        return 0

    log.info("Lot du jour : %d id(s) sélectionné(s) : %s", len(ids), ids)
    enrich_main([str(i) for i in ids])

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    events = _fetch(conn, ids)
    conn.close()

    complet, incomplet = [], []
    for i in ids:
        ev = events.get(i)
        if not ev:
            incomplet.append((i, "— introuvable en base —", ["  ✗ disparu de la base"]))
            continue
        ok, lines = _row_report(ev)
        bloquants = _porte_publication(ev, today)
        lines = lines + bloquants
        (complet if (ok and not bloquants) else incomplet).append(
            (i, ev.get("title") or "", lines))

    log.info("Lot du jour : %d complet(s), %d incomplet(s) avant publication",
             len(complet), len(incomplet))

    published_lines = []
    if complet:
        publish_main(["--ids", *[str(i) for i, _, _ in complet]])
        # Re-vérification POST-publication (image réelle + wp id désormais posés).
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        events2 = _fetch(conn, [i for i, _, _ in complet])
        conn.close()
        for i, title, _ in complet:
            ev2 = events2.get(i) or {}
            ok2, lines2 = _row_report(ev2)
            wp_id = ev2.get("wp_post_id_as")
            # ⚠️ `and wp_id` EST INDISPENSABLE. `_row_report` ne met JAMAIS ok=False
            # quand wp_post_id_as est vide : il se contente d'écrire « publication AS :
            # PAS ENCORE publié » (batch_report l.333-335). Sans ce test, une fiche que
            # publish_to_as n'a PAS réussi à mettre en ligne — échec réseau, erreur WP,
            # ou rétention par le verrou radar — était annoncée sur Slack en
            # « ✅ … — WP#None ». Le rapport quotidien mentait dans le sens le plus
            # coûteux : croire publié ce qui ne l'est pas. Et depuis le verrou radar,
            # cette branche est empruntée tous les jours.
            if ok2 and wp_id:
                published_lines.append(f"✅ [{i}] {title[:60]} — WP#{wp_id}")
            elif not wp_id:
                published_lines.append(
                    f"🔴 [{i}] {title[:60]} — NON PUBLIÉE (aucun id WordPress en retour) "
                    f"— voir logs/daily_batch.log")
            else:
                # Publié mais un contrôle post-publication a quand même échoué
                # (ex. échec réseau au push) : signalé, pas silencieux.
                bad = "; ".join(l.strip() for l in lines2 if l.strip().startswith("✗"))
                published_lines.append(f"⚠️ [{i}] {title[:60]} — WP#{wp_id} mais {bad}")

    # TON DU MESSAGE — une fiche « incomplète » n'est PAS un échec du lot : c'est une
    # publication ratée qui a été ÉVITÉE. Le pipeline a fait exactement son travail, et
    # la fiche repart au lot du lendemain avec ce qui lui manque, nommé. Formulé comme
    # une perte (« laissé(s) pour un prochain run »), le même chiffre se lit comme un
    # retard tous les matins — alors que sa hausse signifie que le portillon filtre
    # davantage, donc que moins de fiches fausses partent en ligne.
    # AGRÉGÉES PAR CAUSE, plus une ligne par fiche — Franck, 2026-08-28 : « les résumés
    # sont beaucoup trop longs. » Dix lignes « 🛠️ [id] titre — article : VIDE » disent
    # dix fois la même chose ; « 10 fiches : article vide [ids] » le dit une fois, et le
    # détail par fiche reste dans logs/daily_batch.log. Le lecteur du digest n'a AUCUN
    # geste par fiche à faire ici (elles repassent seules) : la cause et le compte
    # suffisent, les identifiants permettent de creuser si besoin.
    par_cause: dict[str, list[int]] = {}
    for i, title, lines in incomplet:
        reasons = "; ".join(l.strip().lstrip("✗ ") for l in lines if l.strip().startswith("✗"))
        par_cause.setdefault(reasons or "incomplet", []).append(i)
        log.info("Retenue [%d] %s — %s", i, title[:60], reasons or "incomplet")
    incomplet_lines = [
        f"🛠️ {len(ids)} fiche(s) — {cause} — [{', '.join(str(x) for x in ids)}]"
        for cause, ids in sorted(par_cause.items(), key=lambda kv: -len(kv[1]))]

    msg = (f"📰 *Lot quotidien Agenda Sabauda* — {len(complet)} fiche(s) en ligne, "
           f"{len(incomplet)} retenue(s) avant publication\n")
    if published_lines:
        msg += "\n".join(published_lines) + "\n"
    if incomplet_lines:
        msg += (f"\n_Ces {len(incomplet)} fiche(s) auraient été publiées incomplètes : "
                f"le portillon les a arrêtées. Elles repassent automatiquement au "
                f"prochain lot, rien à faire de ton côté._\n")
        msg += "\n".join(incomplet_lines)
    slack.notify(msg)
    from utils import pipeline_status
    pipeline_status.record_run("daily_batch", ok=len(complet), warn=len(incomplet),
                               summary=msg[:1500])
    log.info("=== Lot quotidien terminé : %d publié(s), %d laissé(s) incomplet(s) ===",
             len(complet), len(incomplet))
    return 0


def main(argv: list[str]) -> int:
    """Enveloppe le lot du jour : une exception non rattrapée dans un cron ne produit
    qu'une ligne dans logs/daily_batch.log — que personne ne lit. Le but affiché de ce
    script étant que Franck n'ait plus à se connecter au VPS, un plantage DOIT arriver
    sur Slack et dans l'historique pipeline_runs, au même titre qu'un succès."""
    try:
        return _run(argv)
    except Exception as exc:  # noqa: BLE001 — remonter, pas mourir en silence
        log.exception("Lot quotidien INTERROMPU")
        msg = (f"🔴 *Lot quotidien Agenda Sabauda INTERROMPU* — "
               f"{type(exc).__name__}: {exc}\nVoir logs/daily_batch.log sur le VPS.")
        try:
            slack.notify(msg)
            from utils import pipeline_status
            pipeline_status.record_run("daily_batch", error=1, summary=msg[:1500])
        except Exception:  # noqa: BLE001 — la notification ne doit pas masquer la cause
            log.exception("Notification de l'échec impossible")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
