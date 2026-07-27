#!/usr/bin/env python3
"""Nettoyage RÉTROACTIF des séances de cinéma — tri par ORGANISATEUR.

Règle éditoriale (Franck) : on EXCLUT les projections de cinéma en programmation
COURANTE d'une salle COMMERCIALE (Pathé, UGC, multiplexe : un film à l'affiche).
On GARDE les rendez-vous cinéma à dimension culturelle portés par une association,
une collectivité territoriale, une institution culturelle ou un festival :
festivals, rétrospectives, hommages, cycles thématiques, avant-premières
événementielles, plein air associatif. Le critère décisif est l'ORGANISATEUR.

Décision par un classifieur BINAIRE dédié (stable), pas par un seuil de score
(bruité). Les paires FR/IT (traductions) sont traitées ENSEMBLE (même verdict).
Idempotent et auto-correcteur : re-garde ce qui aurait été rejeté à tort lors d'un
passage précédent (statut repasse 'evaluated'/'published_sub').

  séance courante commerciale → statut 'rejected' + CORBEILLE WordPress (réversible) ;
  événement cinéma culturel    → gardé (ou rétabli s'il avait été rejeté à tort).

Sécurité : DRY-RUN par défaut. --execute pour agir. Réversible (corbeille WP).
La corbeille d'une fiche PUBLIÉE exige cs-trash.php >= v1.1 (option force) déployé.

Exemples :
  .venv/bin/python3 -m scripts.cleanup_cinema            # dry-run
  .venv/bin/python3 -m scripts.cleanup_cinema --execute
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.cleanup_as_trash import trash_one

log = get_logger("cleanup_cinema")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

_CINEMA = ("Cinéma", "Cinema")
_RETAINED = ("evaluated", "published_cs", "published_sub")
# Marqueur laissé par CE script sur ses propres rejets → permet de les ré-examiner
# (et d'en rétablir un rejeté à tort) sans ressusciter les rejets « normaux ».
_MARK = "nettoyage cinéma"
# Motif de sélection des rejets À RÉ-EXAMINER : couvre l'ancien libellé (« nettoyage
# rétroactif ») ET le nouveau — tous nos rejets cinéma commencent par « Séance de cinéma ».
_REJECT_LIKE = "%Séance de cinéma%"

CLASSIFY_PROMPT = """Tu tries des événements de catégorie CINÉMA pour un agenda culturel.

RÈGLE STRICTE. On ne GARDE (garder=true) QUE les vrais FESTIVALS DE CINÉMA : un événement
MULTI-FILMS à identité de festival — nom de festival, édition numérotée, programmation sur
plusieurs jours, sélection ou compétition (ex. « Torino Film Festival », un festival dédié
à Marilyn Monroe, un festival du documentaire).

On EXCLUT (garder=false) TOUT LE RESTE, même porté par une institution culturelle ou un
cinéma d'art et d'essai :
- projection d'un film ordinaire (salle commerciale OU non) ;
- RÉTROSPECTIVE, CYCLE ou HOMMAGE à un réalisateur (ex. « Les films de Bong Joon-ho ») ;
- ciné en PLEIN AIR, séance unique, avant-première isolée, ciné-club.
Le critère : est-ce un FESTIVAL identifié (garder) ou une simple PROGRAMMATION de
projections, aussi culturelle soit-elle (exclure) ? En cas de doute → EXCLURE.

Événement :
Titre : {title}
Description : {description}
Lieu : {lieu} · Ville : {ville}
Source : {source}

Réponds UNIQUEMENT en JSON : {{"garder": true|false, "type": "<festival|rétrospective|
hommage|cycle|avant-première|plein air|séance courante|autre>", "organisateur":
"<commercial|association|collectivité|institution|festival|inconnu>", "raison": "<courte>"}}"""


def _clean(s) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()[:600]


def classify(ev: dict, client, model: str) -> dict | None:
    """Classifieur binaire (garder/exclure) fondé sur l'organisateur. None si panne API."""
    prompt = CLASSIFY_PROMPT.format(
        title=_clean(ev.get("article_title") or ev.get("title")),
        description=_clean(ev.get("description")),
        lieu=_clean(ev.get("lieu")), ville=_clean(ev.get("ville")),
        source=_clean(ev.get("source_name")))
    try:
        msg = client.messages.create(
            model=model, max_tokens=300,
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:  # noqa: BLE001
        log.warning("Classement cinéma indisponible (%s)", exc)
        return None
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text")
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except (ValueError, TypeError):
        return None


def _pair_key(ev: dict) -> int:
    """Clé de regroupement des jumeaux FR/IT : l'id de l'original (translation_of) si
    c'est une traduction, sinon l'id propre. Original et traduction partagent la clé."""
    return int(ev.get("translation_of") or ev.get("id"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Nettoyage rétroactif des séances de cinéma (tri par organisateur).")
    p.add_argument("--execute", action="store_true", help="Agir réellement (sinon DRY-RUN).")
    p.add_argument("--cap", type=int, default=300, help="Nombre max d'événements à examiner.")
    p.add_argument("--delay", type=float, default=0.5, help="Pause (s) entre deux appels.")
    args = p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY non définie")
        return 1
    from utils import settings as pipeline_settings
    model = os.getenv("ANTHROPIC_MODEL") or pipeline_settings.model()
    client = anthropic.Anthropic(api_key=api_key)
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    have_wp = all([wp_url, auth[0], auth[1]])

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cat_ph = ",".join("?" * len(_CINEMA))
    st_ph = ",".join("?" * len(_RETAINED))
    # Retenus + nos propres rejets précédents (pour rattraper un rejet à tort).
    rows = conn.execute(
        f"SELECT * FROM events_raw WHERE llm_categorie IN ({cat_ph}) AND duplicate_of IS NULL "
        f"AND (statut IN ({st_ph}) OR (statut='rejected' AND llm_justification LIKE ?)) "
        "ORDER BY COALESCE(date_event_start,'') LIMIT ?",
        (*_CINEMA, *_RETAINED, _REJECT_LIKE, args.cap)).fetchall()
    rows = [dict(r) for r in rows]

    # Regroupe les jumeaux FR/IT → un seul classement par groupe, appliqué à tous.
    groups: dict[int, list[dict]] = {}
    for ev in rows:
        groups.setdefault(_pair_key(ev), []).append(ev)

    mode = "EXÉCUTION" if args.execute else "DRY-RUN (rien ne bouge)"
    log.info("Cinéma à trier : %d fiche(s) en %d groupe(s) FR/IT (modèle %s) — %s",
             len(rows), len(groups), model, mode)

    to_reject, to_restore, keep = [], [], []
    for i, (key, grp) in enumerate(groups.items(), 1):
        # Classe sur la fiche la plus renseignée du groupe.
        rep = max(grp, key=lambda e: len(e.get("description") or ""))
        verdict = classify(rep, client, model)
        if verdict is None:  # panne API : on ne touche pas au groupe
            log.warning("groupe %s ignoré (panne API)", key)
            continue
        garder = bool(verdict.get("garder"))
        kind = verdict.get("type", "?")
        orga = verdict.get("organisateur", "?")
        # Garde-fou déterministe : on ne garde QUE les FESTIVALS. Tout autre type
        # (rétrospective, cycle, hommage, plein air, avant-première, séance…) est exclu,
        # quel que soit l'organisateur ou ce qu'a répondu le modèle.
        garder = kind.strip().lower() == "festival"
        title = _clean(rep.get("title"))[:52]
        for ev in grp:
            is_rejected = ev.get("statut") == "rejected"
            if not garder and not is_rejected:
                to_reject.append((ev, verdict))
            elif garder and is_rejected:
                to_restore.append((ev, verdict))
            else:
                keep.append(ev)
        tag = "GARDER" if garder else "RETIRER"
        icon = "✓" if garder else "✂️"
        print(f"  {icon} {tag:<7} {kind:<14} [{orga}] · {len(grp)} fiche(s) · {title}")
        if args.delay and i < len(groups):
            time.sleep(args.delay)

    print(f"\n{len(to_reject)} à retirer · {len(to_restore)} à rétablir (rejet à tort) · "
          f"{len(keep)} déjà OK")

    if not args.execute:
        print("\nDRY-RUN : rien n'a changé. Relance avec --execute pour appliquer.")
        conn.close()
        return 0

    if not have_wp:
        log.warning("WP_AS_URL/USER/APP_PASSWORD manquants — corbeille WP impossible.")

    trashed = rejected = restored = failed_trash = 0
    for ev, verdict in to_reject:
        wp_id = ev.get("wp_post_id_as")
        if wp_id and have_wp:
            if trash_one(wp_url, auth, int(wp_id), force=True):
                conn.execute("UPDATE events_raw SET wp_post_id_as=NULL, published_as_date=NULL "
                             "WHERE id=?", (ev["id"],))
                trashed += 1
            else:
                failed_trash += 1
        conn.execute(
            "UPDATE events_raw SET statut='rejected', llm_score=0, llm_justification=? WHERE id=?",
            (f"Séance de cinéma commerciale exclue ({_MARK}). {verdict.get('raison','')}"[:400],
             ev["id"]))
        conn.commit()
        rejected += 1
        log.info("[%s] retiré (%s/%s) : %s", ev["id"], verdict.get("type"),
                 verdict.get("organisateur"), _clean(ev.get("title"))[:50])
    for ev, verdict in to_restore:
        # Rétabli : score plancher de rétention (l'original était retenu) ; statut = AS si
        # une fiche WP subsiste, sinon 'evaluated'.
        new_statut = "published_sub" if ev.get("wp_post_id_as") else "evaluated"
        conn.execute(
            "UPDATE events_raw SET statut=?, llm_score=7, llm_justification=? WHERE id=?",
            (new_statut, f"Événement cinéma culturel rétabli ({_MARK} : {verdict.get('organisateur','')}).",
             ev["id"]))
        conn.commit()
        restored += 1
        log.info("[%s] rétabli (%s) : %s", ev["id"], verdict.get("type"),
                 _clean(ev.get("title"))[:50])

    conn.close()
    print(f"\n=== Terminé : {rejected} rejetée(s), {trashed} à la corbeille WP, "
          f"{restored} rétablie(s)"
          + (f", {failed_trash} corbeille ÉCHOUÉE (redéployer cs-trash.php v1.1 ?)" if failed_trash else "")
          + " ===")
    print("Réversible : Événements → Corbeille dans WordPress pour restaurer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
