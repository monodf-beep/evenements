#!/usr/bin/env python3
"""Apprentissage à partir de l'archive Slack — LECTURE SEULE, zéro appel LLM.

Demande de Franck (2026-08-05) : « l'autonomie c'est l'apprentissage par soi-même —
avoir les messages Slack et les envoyer aux différents agents. » Ce module fait la
moitié déterministe de cette idée : il relit `logs/slack/*.jsonl` (l'archive posée le
2026-08-04), reconnaît les messages « ⚠️ À compléter » de `scripts.autocomplete`, et
les recroise avec l'état ACTUEL de chaque fiche — ce qu'un fil Slack, lu une fois puis
oublié, ne fait jamais.

EN CONSTRUISANT CE SCRIPT, un vrai trou est apparu dans `scripts/autocomplete.py` :
l'anti-spam ne notifiait QUE si l'état changeait, donc une fiche bloquée sur le MÊME
manque (venue introuvable, image refusée) était signalée UNE FOIS puis disparaissait
de Slack pour toujours, alors que le script continuait de la retenter chaque jour en
silence — l'incident « LES 7 PROCHAINS JOURS : 0 carte » sous une autre forme. Corrigé
le même jour (résurfaçage tous les `AUTOCOMPLETE_RESURFACE_DAYS` jours). Ce script-ci
suppose donc ce correctif en place ; sans lui, l'archive elle-même serait trouée.

TROIS CHOSES QUE L'AGRÉGATION MONTRE, QU'UN FIL SLACK NE MONTRE PAS :
  • RÉSOLU depuis — la fiche est maintenant complète, ou a disparu (fusion/rejet) ;
  • ENCORE OUVERT — le résurfaçage la retente, mais un passage isolé ne dit pas si
    c'est un cas isolé ou un motif ;
  • MOTIF QUI SE RÉPÈTE — le vrai signal d'apprentissage : le MÊME champ manquant sur
    PLUSIEURS fiches d'une même source (`SLACK_LEARNING_SEUIL`, défaut 5) signe un
    problème de SOURCE (page sans image exploitable, flux sans lieu structuré), pas
    une série de fiches malchanceuses. Traiter la source une fois vaut mieux que
    retenter chaque fiche indéfiniment — c'est la vraie réponse à « envoyer ça aux
    agents » : désigner LA CAUSE, pas rejouer le symptôme fiche par fiche.

CE QUE CE SCRIPT NE FAIT PAS : il ne corrige rien, ne réévalue rien, n'appelle aucun
LLM, ne décide pas quelle source est fautive. Cf. Franck, 2026-08-04 : « on ne doit pas
faire des choses automatiques pour faire des choses automatiques sans réfléchir. » Il
DÉSIGNE ; agir sur un motif (exclure une source, forcer une image manuelle) reste un
jugement humain — exactement la distinction retenue pour les exclusions éditoriales
(config/excluded_event_keywords.txt : détection automatique, retrait décidé).

Usage :
    .venv/bin/python -m scripts.slack_learning              # 30 derniers jours
    .venv/bin/python -m scripts.slack_learning --days 60
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import completeness as comp
from scripts.scraper_events import init_db

log = get_logger("slack-learning")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
ARCHIVE = ROOT / "logs" / "slack"
STATE_FILE = ROOT / "data" / "slack_learning_state.json"
SEUIL_MOTIF = int(os.getenv("SLACK_LEARNING_SEUIL", "5"))

# L'id local n'apparaît nulle part de façon fiable dans un message SAUF dans le
# rappel `/agenda complete <id> ...` que utils.slack.notify_incomplete ajoute
# toujours (le titre affiché est celui de l'article, pas forcément unique en base).
_RE_MANQUE = re.compile(r"Il manque : \*([^*]+)\*")
_RE_ID = re.compile(r"/agenda complete (\d+)")


def _fenetre(jours: int) -> list[Path]:
    aujourdhui = date.today()
    return [p for i in range(jours)
            if (p := ARCHIVE / f"{(aujourdhui - timedelta(days=i)):%Y-%m-%d}.jsonl").exists()]


def _messages_manque(fichiers: list[Path]) -> list[dict]:
    """Lit l'archive, ne garde que les messages « À compléter » à l'id repérable."""
    out = []
    for p in fichiers:
        try:
            lignes = p.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for ligne in lignes:
            ligne = ligne.strip()
            if not ligne:
                continue
            try:
                entree = json.loads(ligne)
            except (ValueError, TypeError):
                continue
            texte = entree.get("texte", "")
            if "À compléter" not in texte:
                continue
            m_manque, m_id = _RE_MANQUE.search(texte), _RE_ID.search(texte)
            if not m_manque or not m_id:
                continue
            champs = [c.strip() for c in m_manque.group(1).split(",") if c.strip()]
            out.append({"at": entree.get("at", ""), "id": int(m_id.group(1)), "champs": champs})
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Apprentissage déterministe (motifs récurrents) depuis l'archive Slack.")
    parser.add_argument("--days", type=int, default=30, help="Fenêtre d'archive à relire.")
    args = parser.parse_args(argv)

    fichiers = _fenetre(args.days)
    messages = _messages_manque(fichiers) if fichiers else []
    if not messages:
        log.info("%d jour(s) d'archive Slack lus (%d dispo), aucun message « À "
                 "compléter » à traiter.", len(fichiers), args.days)
        return 0

    # Un seul état retenu par fiche : le message le PLUS RÉCENT (l'historique
    # intermédiaire n'ajoute rien — c'est le résurfaçage d'autocomplete.py qui gère
    # la répétition dans le temps ; ce qui manque ici est le TOTAL, pas la chronologie).
    par_id: dict[int, dict] = {}
    premiere: dict[int, str] = {}
    for m in messages:
        eid = m["id"]
        premiere[eid] = min(premiere.get(eid, m["at"]), m["at"])
        if eid not in par_id or m["at"] >= par_id[eid]["at"]:
            par_id[eid] = m

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    resolues = disparues = 0
    par_source: dict[str, dict[str, int]] = {}
    plus_ancien: tuple[int, str, str] | None = None

    for eid, dernier in par_id.items():
        row = conn.execute(
            "SELECT source_name FROM events_raw WHERE id=?", (eid,)).fetchone()
        if row is None:
            disparues += 1
            continue
        full = dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())
        if comp.is_complete(full):
            resolues += 1
            continue
        source = row["source_name"] or "?"
        for champ in dernier["champs"]:
            d = par_source.setdefault(source, {})
            d[champ] = d.get(champ, 0) + 1
        depuis = premiere[eid][:10]
        if plus_ancien is None or depuis < plus_ancien[1]:
            plus_ancien = (eid, depuis, ", ".join(dernier["champs"]))
    conn.close()
    ouvertes = len(par_id) - resolues - disparues

    # MOTIFS : (source × champ) au-dessus du seuil — cause probablement SYSTÉMIQUE.
    motifs = sorted(
        ((s, c, n) for s, champs in par_source.items() for c, n in champs.items()
         if n >= SEUIL_MOTIF),
        key=lambda t: -t[2])

    # COMPARAISON au dernier passage — l'apprentissage CUMULATIF : sans elle, ce
    # script réafficherait la même photo à chaque exécution au lieu de dire ce qui
    # a CHANGÉ depuis la dernière fois qu'un humain l'a lu.
    precedent: dict[str, int] = {}
    if STATE_FILE.exists():
        try:
            precedent = json.loads(STATE_FILE.read_text(encoding="utf-8")).get("motifs", {})
        except (ValueError, TypeError):
            precedent = {}
    actuels = {f"{s}::{c}": n for s, c, n in motifs}
    nouveaux = [(s, c, n) for s, c, n in motifs if f"{s}::{c}" not in precedent]
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(
        {"at": datetime.now().isoformat(timespec="seconds"), "motifs": actuels},
        ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("%d message(s) « À compléter » lus sur %d fiche(s) distinctes (%d jour(s) "
             "d'archive) — %d résolue(s) depuis, %d disparue(s) (fusion/rejet), "
             "%d encore ouverte(s) aujourd'hui.",
             len(messages), len(par_id), len(fichiers), resolues, disparues, ouvertes)
    for source, champ, n in motifs:
        neuf = " 🆕" if f"{source}::{champ}" in {f"{s}::{c}" for s, c, _ in nouveaux} else ""
        log.info("  MOTIF : %s → « %s » manque sur %d fiche(s)%s", source, champ, n, neuf)
    if plus_ancien:
        log.info("  Ouverte depuis le plus longtemps : [%s] depuis le %s (%s).", *plus_ancien)

    if motifs:
        resume = "; ".join(f"{s} manque {c} ({n})" for s, c, n in motifs[:3])
        log.info("%d motif(s) récurrent(s) (≥%d fiches) : %s%s", len(motifs), SEUIL_MOTIF,
                 resume, f" — dont {len(nouveaux)} nouveau(x)" if nouveaux else "")
    else:
        log.info("%d fiche(s) encore ouverte(s), aucun motif au-dessus du seuil "
                 "(≥%d fiches même source × même champ) — manques dispersés.",
                 ouvertes, SEUIL_MOTIF)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
