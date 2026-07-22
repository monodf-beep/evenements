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
from utils.images import commons_search, fetch_og_image, fetch_content_image
from utils.sources import (is_blocked_image, is_logo_image, load_blocked_image_domains,
                           load_territory_images, pick_image)
from utils import image_verify
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


def _acceptable(url: str, blocked: set[str], patterns: list) -> bool:
    """RÈGLES déterministes : ni domaine proscrit, ni logo, ni motif parasite connu
    (bandeau/pub/slider, voir config/blocked_image_patterns.txt)."""
    return bool(url) and not is_blocked_image(url, blocked) \
        and not is_logo_image(url) and not image_verify.looks_parasitic(url, patterns)


def _verified(url: str, ev: dict, verify_client, verify_model: str, subject: str = "") -> bool:
    """AGENT vision (optionnel) : si un client est fourni, l'image doit correspondre à
    l'événement. Sans client, on fait confiance aux règles déterministes."""
    if verify_client is None:
        return True
    from utils.images import _PAGE_UA, _MAX_CHECK_BYTES  # réutilise le téléchargement borné
    import requests
    try:
        r = requests.get(url, headers=_PAGE_UA, timeout=15, stream=True)
        if r.status_code != 200:
            return True  # injoignable pour la vérif : ne bloque pas (le push refera sa chaîne)
        mime = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        buf = b""
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > _MAX_CHECK_BYTES:
                break
    except requests.RequestException:
        return True
    return image_verify.verify_relevance(buf, mime, ev, verify_client, verify_model, subject)


def resolve_image(ev: dict, client, blocked: set[str], banners: dict,
                  verify_client=None, verify_model: str = "claude-haiku-4-5") -> tuple[str, str, str]:
    """Renvoie (url, credit, source) selon la chaîne 4 étages. url='' seulement si
    aucune bannière n'est configurée pour le territoire.

    RÈGLES (toujours) : chaque candidat passe _acceptable (domaine/logo/parasite).
    AGENT (si verify_client) : og / page / Commons sont vérifiés par vision — une image
    qui ne correspond pas à l'événement est refusée et on descend d'un étage."""
    patterns = image_verify.load_blocked_patterns()
    # Étage 2 — og:image de la page officielle (jamais pour un radar : image de presse).
    if not _is_radar(ev):
        og = fetch_og_image(ev.get("url_source", ""))
        if _acceptable(og, blocked, patterns) and _verified(og, ev, verify_client, verify_model):
            return og, "", "og"
        # Étage 2b — repli : 1re vraie photo de CONTENU (pages sans og:image, ex.
        # offices de tourisme). L'info est sur la page, on la prend au lieu d'abandonner.
        content = fetch_content_image(ev.get("url_source", ""))
        if _acceptable(content, blocked, patterns) and _verified(content, ev, verify_client, verify_model):
            return content, "", "page"
    # Étage 3 — photo licenciable Wikimedia Commons (LLM = requête, code = fetch).
    if client is not None:
        q = visual_query(ev, client, MODEL)
        if q:
            url, credit = commons_search(q)
            if _acceptable(url, blocked, patterns) and _verified(url, ev, verify_client, verify_model, q):
                log.info("[%s] Commons « %s » → %s", ev["id"], q, url[:70])
                return url, credit, "commons"
    # Étage 4 — bannière de marque du territoire (repli garanti, jamais parasite).
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
    parser.add_argument("--verify", action="store_true",
                        help="Active l'AGENT vision (vérifie que chaque image correspond à "
                             "l'événement). Par défaut : règles déterministes seulement (gratuit) "
                             "— la vérification vision se fait surtout au moment de publier.")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
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
    verify_client = client if args.verify else None
    verify_model = os.getenv("ANTHROPIC_MODEL_VISION") or "claude-haiku-4-5"
    counts = {"og": 0, "page": 0, "commons": 0, "banner": 0, "none": 0}
    for ev in rows:
        url, credit, source = resolve_image(ev, client, blocked, banners,
                                            verify_client=verify_client, verify_model=verify_model)
        if not url:
            counts["none"] += 1
            log.warning("[%s] aucun visuel (pas de bannière pour %s)", ev["id"], ev.get("territoire"))
            continue
        conn.execute(
            "UPDATE events_raw SET url_image=?, image_credit=?, image_source=? WHERE id=?",
            (url, credit, source, ev["id"]))
        conn.commit()
        counts[source] += 1
    log.info("Visuels posés — og:image=%d · page=%d · Commons=%d · bannière=%d · échec=%d",
             counts["og"], counts["page"], counts["commons"], counts["banner"], counts["none"])
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
