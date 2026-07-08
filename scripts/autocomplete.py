#!/usr/bin/env python3
"""AGENT D'AUTO-COMPLÉTION + PORTE QUALITÉ (le cœur de la demande de Franck).

Boucle sur les événements RETENUS, À VENIR mais INCOMPLETS (il manque un champ
obligatoire — cf. utils/completeness.py). Pour chacun, il tente de COMPLÉTER en
réutilisant tout l'outillage existant, du plus sûr au dernier recours :

    Date    : page (JSON-LD) → texte FR/IT (LLM)                 [scripts/dates]
    Lieu    : page (JSON-LD) → texte (LLM) → recherche web        [scripts/venues(_web)]
    Image   : og:image → Wikimedia Commons → recherche web+vision [scripts/visuals + images_web]
              (la bannière territoire reste le filet ; on préfère une vraie photo vérifiée)

Puis il RE-VÉRIFIE la complétude et émet un SIGNAL :
    • « bon »     → tout est là : on POUSSE en brouillon sur Agenda Sabauda
                    (draft, jamais en ligne auto) + notification Slack ;
    • « pas bon » → il manque encore : l'événement RESTE dans le dashboard
                    (liste « À compléter ») + notification Slack à Franck avec la
                    liste des manques, pour qu'il complète (dashboard ou réponse Slack).

Anti-spam : on mémorise le dernier signal émis (autocomplete_state) ; on ne
re-notifie que si l'état a CHANGÉ depuis la dernière fois.

Exemples :
  .venv/bin/python3 -m scripts.autocomplete --dry-run
  .venv/bin/python3 -m scripts.autocomplete --cap 20 --min-score 5
  .venv/bin/python3 -m scripts.autocomplete --cap 20 --no-web      # sans recherche web (moins cher)
  .venv/bin/python3 -m scripts.autocomplete --cap 20 --no-publish  # complète mais ne pousse pas
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import completeness as comp
from utils import slack
from scripts.scraper_events import init_db

log = get_logger("autocomplete")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def ensure_columns(conn: sqlite3.Connection) -> None:
    """Traçe le dernier passage de l'agent (horodatage + état signalé)."""
    for col, decl in (("autocomplete_at", "TEXT"),
                      ("autocomplete_state", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()


# --------------------------------------------------------------------------- #
# Complétion d'UN événement, champ par champ, en réutilisant l'outillage.
# Chaque passe est idempotente et ne s'exécute QUE si le champ est encore vide.
# --------------------------------------------------------------------------- #
def _fill_date(ev: dict, client, model_extract: str) -> dict:
    if not comp._empty(ev.get("date_event_start")):
        return {}
    from scripts.dates import (parse_dates, fetch_event_dates, fetch_page_text,
                               llm_dates)
    today = date.today()
    # 1) ré-extraction du texte brut déjà en base
    if (ev.get("date_start") or "").strip():
        try:
            s, e, _ = parse_dates(ev["date_start"], today)
            if s:
                return {"date_event_start": s, "date_event_end": e, "date_source": "reparse"}
        except Exception:
            pass
    # 2) page officielle (JSON-LD)
    s, e, src = fetch_event_dates(ev.get("url_source", ""))
    if s:
        return {"date_event_start": s, "date_event_end": e, "date_source": src}
    # 3) LLM sur la matière de la page (dernier recours)
    if client is not None:
        material = fetch_page_text(ev.get("url_source", "")) or \
            f"{ev.get('title','')}\n{ev.get('description') or ''}"
        s, e, src = llm_dates(material, today, client, model_extract)
        if s:
            return {"date_event_start": s, "date_event_end": e, "date_source": src}
    return {}


def _fill_venue(ev: dict, client, model_extract: str, allow_web: bool) -> dict:
    if not comp._empty(ev.get("lieu")):
        return {}
    from scripts.venues import fetch_event_venue, llm_venue
    from scripts.dates import fetch_page_text
    # 1) page (JSON-LD location)
    lieu, ville, src = fetch_event_venue(ev.get("url_source", ""))
    if lieu:
        return {"lieu": lieu, "ville": ville or ev.get("ville") or "", "venue_source": src}
    # 2) LLM sur la matière
    if client is not None:
        material = fetch_page_text(ev.get("url_source", "")) or \
            f"{ev.get('title','')}\n{ev.get('description') or ''}"
        lieu, ville, src = llm_venue(material, client, model_extract)
        if lieu:
            return {"lieu": lieu, "ville": ville or ev.get("ville") or "", "venue_source": src}
    # 3) recherche web (dernier recours, coûteux)
    if allow_web and client is not None:
        from scripts.venues_web import web_venue
        lieu, ville, src = web_venue(ev, client)
        if lieu:
            return {"lieu": lieu, "ville": ville or ev.get("ville") or "", "venue_source": src}
    return {}


def _fill_image(ev: dict, client, blocked, banners, allow_web: bool,
                want_banner: bool) -> dict:
    # Déjà une vraie photo → rien à faire.
    if comp.has_real_image(ev):
        return {}
    # 1) recherche web + vérificateur vision (meilleure photo pertinente)
    if allow_web and client is not None:
        from scripts.images_web import find_verified_image
        url, credit = find_verified_image(ev, client, blocked)
        if url:
            return {"url_image": url, "image_credit": credit, "image_source": "web"}
    # 2) chaîne déterministe (og:image → Commons → bannière). On ne garde la
    #    bannière que si on veut boucher le trou pour atteindre la complétude.
    from scripts.visuals import resolve_image
    url, credit, source = resolve_image(ev, client, blocked, banners)
    if url and (source != "banner" or (want_banner and comp._empty(ev.get("url_image")))):
        return {"url_image": url, "image_credit": credit, "image_source": source}
    return {}


def complete_event(ev: dict, conn, client, blocked, banners, *,
                   allow_web: bool, want_banner: bool, model_extract: str) -> dict:
    """Applique les passes de complétion et renvoie l'événement à jour (en base)."""
    updates: dict = {}
    for filler in (
        lambda: _fill_date(ev, client, model_extract),
        lambda: _fill_venue(ev, client, model_extract, allow_web),
        lambda: _fill_image({**ev, **updates}, client, blocked, banners,
                            allow_web, want_banner),
    ):
        got = filler()
        if got:
            updates.update(got)
            ev = {**ev, **got}
    if updates:
        sets = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE events_raw SET {sets} WHERE id=?",
                     [*updates.values(), ev["id"]])
        conn.commit()
        log.info("id=%s complété : %s", ev["id"], ", ".join(updates.keys()))
    return ev


def _select(conn, args, today: str):
    where = [
        "statut IN ('evaluated','published_cs','published_sub')",
        "duplicate_of IS NULL",
        "COALESCE(llm_score,0) >= ?",
    ]
    params: list = [args.min_score]
    if args.dfrom and args.dto:
        # PÉRIODE : uniquement les événements DATÉS qui chevauchent [from, to]
        # (« pour ne pas tout faire »). Les non-datés n'ont pas de fenêtre → exclus.
        where.append("COALESCE(date_event_start,'') <> '' "
                     "AND COALESCE(date_event_start,'') <= ? "
                     "AND COALESCE(date_event_end, date_event_start) >= ?")
        params += [args.dto, args.dfrom]
    elif not args.include_past:
        # « à venir » : on ignore les événements clairement terminés (datés et passés).
        where.append("(COALESCE(date_event_end, date_event_start, '') = '' "
                     "OR COALESCE(date_event_end, date_event_start) >= ?)")
        params.append(today)
    sql = (f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
           f"ORDER BY COALESCE(llm_score,0) DESC, date_event_start ASC LIMIT ?")
    params.append(args.cap)
    return conn.execute(sql, params).fetchall()


def _is_upcoming(ev: dict, today: str) -> bool:
    """True si l'événement se termine (ou commence) aujourd'hui ou après.

    Garde-fou de la porte : un événement peut devenir « complet » après complétion
    mais avec une date PASSÉE (article sur une édition révolue, ou année mal
    extraite). On ne pousse jamais un passé sur l'agenda — cf. run du 2026-07 où
    « Nice Jazz Fest » s'est retrouvé daté 2024.
    """
    end = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()
    return bool(end) and end >= today


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Agent d'auto-complétion + porte qualité.")
    parser.add_argument("--cap", type=int, default=20, help="Nombre max d'événements par run.")
    parser.add_argument("--min-score", type=int, default=0,
                        help="Score minimum (défaut 0 : toute la masse retenue).")
    parser.add_argument("--delay", type=float, default=1.0, help="Pause (s) entre deux événements.")
    parser.add_argument("--no-web", action="store_true",
                        help="Pas de recherche web (lieu/image) — moins cher, moins complet.")
    parser.add_argument("--no-banner", action="store_true",
                        help="Ne PAS boucher l'image avec la bannière territoire "
                             "(un événement sans vraie photo restera « à compléter »).")
    parser.add_argument("--no-publish", action="store_true",
                        help="Compléter et signaler, mais NE PAS pousser en brouillon.")
    parser.add_argument("--no-slack", action="store_true", help="Ne pas notifier Slack.")
    parser.add_argument("--include-past", action="store_true", help="Inclure les événements passés.")
    parser.add_argument("--from", dest="dfrom", default="",
                        help="Début de période AAAA-MM-JJ — limite l'agent aux événements "
                             "datés chevauchant la fenêtre (pour ne pas tout traiter).")
    parser.add_argument("--to", dest="dto", default="", help="Fin de période AAAA-MM-JJ.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Lister les incomplets et leurs manques, sans rien faire.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    ensure_columns(conn)

    rows = _select(conn, args, today)
    # On ne garde que les INCOMPLETS (la sélection SQL ne peut pas tout tester).
    incomplete = [dict(r) for r in rows if not comp.is_complete(dict(r))]
    log.info("Sélection : %d retenu(s) à venir, dont %d incomplet(s) (cap %d, min-score %d)",
             len(rows), len(incomplete), args.cap, args.min_score)

    if args.dry_run:
        for ev in incomplete:
            print(f"  [{ev['id']}] score={ev.get('llm_score')} · "
                  f"{(ev.get('title') or '')[:55]:55} · manque : "
                  f"{', '.join(comp.missing_labels(ev)) or '—'}")
        print(f"\n{len(incomplete)} événement(s) incomplet(s) (dry-run — aucune action).")
        conn.close()
        return 0

    # Outillage LLM (optionnel : sans clé, on fait le déterministe seulement).
    client = None
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key, timeout=90.0)
    else:
        log.warning("ANTHROPIC_API_KEY absente : complétion déterministe seulement.")
    model_extract = os.getenv("ANTHROPIC_MODEL_EXTRACT", "claude-haiku-4-5")

    from utils.sources import load_blocked_image_domains, load_territory_images
    blocked = load_blocked_image_domains()
    banners = load_territory_images()

    allow_web = not args.no_web
    want_banner = not args.no_banner
    ready = still = 0

    # Publication (import tardif : n'échoue pas si WP_AS_* absent en dry-run).
    publish_to_as = None
    if not args.no_publish:
        from scripts.publisher_as import publish_to_as as _pub
        publish_to_as = _pub
    wp_as_base = (os.getenv("WP_AS_URL", "") or "").rstrip("/")

    for i, ev in enumerate(incomplete, 1):
        ev = complete_event(ev, conn, client, blocked, banners,
                            allow_web=allow_web, want_banner=want_banner,
                            model_extract=model_extract)
        now_complete = comp.is_complete(ev)
        upcoming = _is_upcoming(ev, today)
        # On ne pousse QUE si complet ET à venir (jamais un passé, cf. _is_upcoming).
        publishable = now_complete and upcoming
        end_date = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()

        # État pour l'anti-spam : ready / past:<date> / missing:<champs>.
        if publishable:
            state = "ready"
        elif now_complete and not upcoming:
            state = f"past:{end_date}"
        else:
            state = "missing:" + ",".join(comp.missing_labels(ev))
        prev = ev.get("autocomplete_state") or ""

        wp_id = None
        if publishable and publish_to_as and not ev.get("wp_post_id_as"):
            wp_id = publish_to_as(ev)
            if wp_id:
                conn.execute(
                    "UPDATE events_raw SET wp_post_id_as=?, published_as_date=datetime('now') "
                    "WHERE id=?", (wp_id, ev["id"]))
                conn.commit()

        # Signal Slack UNIQUEMENT si l'état a changé (anti-spam).
        if not args.no_slack and state != prev:
            if publishable:
                slack.notify_ready(ev, wp_id or ev.get("wp_post_id_as"), wp_as_base)
            elif now_complete and not upcoming:
                slack.notify_incomplete(
                    ev, [f"Date à vérifier — semble PASSÉE ({end_date})"])
            else:
                slack.notify_incomplete(ev, comp.missing_labels(ev))

        conn.execute(
            "UPDATE events_raw SET autocomplete_at=datetime('now'), autocomplete_state=? "
            "WHERE id=?", (state, ev["id"]))
        conn.commit()

        if publishable:
            ready += 1
        elif now_complete and not upcoming:
            still += 1
            log.info("id=%s complet mais date PASSÉE (%s) — non poussé, à vérifier",
                     ev["id"], end_date)
        else:
            still += 1
            log.info("id=%s encore incomplet : manque %s", ev["id"],
                     ", ".join(comp.missing_labels(ev)))
        if args.delay and i < len(incomplete):
            time.sleep(args.delay)

    conn.close()
    log.info("=== Auto-complétion : %d complété(s)→brouillon, %d encore à compléter ===",
             ready, still)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
