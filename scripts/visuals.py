#!/usr/bin/env python3
"""Complète les VISUELS des événements d'une période (bouton « Compléter les visuels »).

Quand le flux RSS ne fournit pas d'image, on va chercher une photo — chaîne en 4
étages, du meilleur au repli (aucune carte n'est jamais vide) :

    1. image du flux RSS ......................... (déjà en base, on ne touche pas)
    2. og:image de la page officielle ............ déterministe (institutionnel)
    3. photo licenciable Wikimedia Commons ....... le LLM rédige la requête, le
       code cherche/filtre (JPEG/PNG, taille, pas de logo) + crédit ; JAMAIS une
       image de presse (charte : source licenciable uniquement)
    4. bannière de marque du territoire .......... repli garanti (Observatoire)

Léger et idempotent : ne traite QUE les événements retenus de la période SANS
image. Rejouable sans surcoût (une fois l'image posée, l'événement est ignoré).

LLM ? OUI pour la seule requête visuelle (jugement : « quoi photographier »).
La recherche, le filtrage et le repli restent déterministes. Voir docs/LLM_OU_CODE.md.

Usage :
    python scripts/visuals.py                       # 7 prochains jours
    python scripts/visuals.py --from 2026-07-01 --to 2026-07-31
    python scripts/visuals.py 12 15 18              # ces id précis
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.images import commons_search, fetch_og_image
from utils.sources import (is_blocked_image, is_logo_image, load_blocked_image_domains,
                           load_territory_images, pick_image)
from scripts.scraper_events import init_db

log = get_logger("visuals")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
# Modèle de la requête visuelle : tâche simple → économique par défaut.
MODEL = os.getenv("ANTHROPIC_MODEL_VISUALS") or os.getenv("ANTHROPIC_MODEL_EXTRACT", "claude-haiku-4-5-20251001")
# Plafond d'événements traités par lancement (garde-fou coût/temps).
CAP = int(os.getenv("VISUALS_CAP", "80"))
STATUTS = ("evaluated", "published_cs", "published_sub")


def _is_radar(ev: dict) -> bool:
    return ev.get("source_type") == "radar" or "(radar)" in (ev.get("source_name") or "")


def _final_text(message) -> str:
    return "".join(getattr(b, "text", "") for b in message.content
                   if getattr(b, "type", None) == "text").strip()


def visual_query(ev: dict, client, model: str) -> str:
    """Le LLM propose une requête de photo Wikimedia Commons. '' si rien de visuel."""
    prompt = (
        "Tu aides à illustrer un événement culturel par une PHOTO réutilisable "
        "(Wikimedia Commons). Donne une requête de recherche COURTE (2 à 5 mots), "
        "visant une vraie photographie : le lieu emblématique, le monument, la ville, "
        "ou le thème. Évite les noms de personnes, les affiches, les logos, le texte.\n\n"
        f"Titre : {ev.get('title','')}\n"
        f"Ville : {ev.get('ville','')}\n"
        f"Territoire : {ev.get('territoire','')}\n"
        f"Catégorie : {ev.get('llm_categorie','')}\n"
        f"Description : {(ev.get('description') or '')[:400]}\n\n"
        'Réponds en JSON strict : {"query": "…", "ok": true} '
        '(ok=false si aucune photo générique ne conviendrait).'
    )
    try:
        msg = client.messages.create(
            model=model, max_tokens=200,
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:  # jamais bloquant : on retombera sur la bannière
        log.warning("[%s] requête visuelle LLM échouée : %s", ev.get("id"), exc)
        return ""
    raw = _final_text(msg)
    m = raw[raw.find("{"):raw.rfind("}") + 1] if "{" in raw else ""
    try:
        data = json.loads(m or raw)
    except (ValueError, TypeError):
        return ""
    return (data.get("query") or "").strip() if data.get("ok") else ""


def resolve_image(ev: dict, client, blocked: set[str], banners: dict) -> tuple[str, str, str]:
    """Renvoie (url, credit, source) selon la chaîne 4 étages. url='' seulement si
    aucune bannière n'est configurée pour le territoire."""
    # Étage 2 — og:image de la page officielle (jamais pour un radar : image de presse).
    if not _is_radar(ev):
        og = fetch_og_image(ev.get("url_source", ""))
        if og and not is_blocked_image(og, blocked) and not is_logo_image(og):
            return og, "", "og"
    # Étage 3 — photo licenciable Wikimedia Commons (LLM = requête, code = fetch).
    if client is not None:
        q = visual_query(ev, client, MODEL)
        if q:
            url, credit = commons_search(q)
            if url:
                log.info("[%s] Commons « %s » → %s", ev["id"], q, url[:70])
                return url, credit, "commons"
    # Étage 4 — bannière de marque du territoire (repli garanti).
    banner = pick_image(ev.get("territoire", ""), key=str(ev["id"]), images=banners)
    if banner:
        return banner, "", "banner"
    return "", "", ""


def select_events(conn: sqlite3.Connection, ids, dfrom, dto) -> list[dict]:
    base = (f"SELECT * FROM events_raw WHERE statut IN ({','.join('?' * len(STATUTS))}) "
            "AND duplicate_of IS NULL AND COALESCE(url_image,'') = '' ")
    params = list(STATUTS)
    if ids:
        base += f"AND id IN ({','.join('?' * len(ids))}) "
        params += list(ids)
    elif dfrom and dto:
        base += "AND COALESCE(date_event_start,'') <= ? AND COALESCE(date_event_end,'') >= ? "
        params += [dto, dfrom]
    base += "ORDER BY llm_score DESC LIMIT ?"
    params.append(CAP)
    return [dict(r) for r in conn.execute(base, params).fetchall()]


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Complète les visuels d'une période.")
    parser.add_argument("ids", nargs="*", type=int)
    parser.add_argument("--from", dest="dfrom", default="")
    parser.add_argument("--to", dest="dto", default="")
    args = parser.parse_args(argv)

    conn = init_db(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = select_events(conn, args.ids, args.dfrom, args.dto)
    scope = (f"ids {args.ids}" if args.ids
             else f"{args.dfrom or '…'} → {args.dto or '…'}")
    log.info("%d événement(s) sans image (%s)", len(rows), scope)
    if not rows:
        log.info("Rien à compléter — tous les événements retenus ont déjà un visuel.")
        return 0

    # Le LLM (étage 3) est optionnel : sans clé, on fait og:image + bannière.
    client = None
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
    else:
        log.warning("ANTHROPIC_API_KEY absente : pas de recherche Commons, og:image + bannière seulement.")

    banners = load_territory_images()
    blocked = load_blocked_image_domains()
    counts = {"og": 0, "commons": 0, "banner": 0, "none": 0}
    for ev in rows:
        url, credit, source = resolve_image(ev, client, blocked, banners)
        if not url:
            counts["none"] += 1
            log.warning("[%s] aucun visuel (pas de bannière pour %s)", ev["id"], ev.get("territoire"))
            continue
        conn.execute(
            "UPDATE events_raw SET url_image=?, image_credit=?, image_source=? WHERE id=?",
            (url, credit, source, ev["id"]))
        conn.commit()
        counts[source] += 1
    log.info("Visuels posés — og:image=%d · Commons=%d · bannière=%d · échec=%d",
             counts["og"], counts["commons"], counts["banner"], counts["none"])
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
