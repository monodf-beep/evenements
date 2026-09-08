#!/usr/bin/env python3
"""Rattrape l'URL d'article des événements issus de newsletters (backfill « gmail: »).

CONTEXTE (bug corrigé) : jusqu'ici, en analysant les mails, on jetait les liens
(<a href>) avant de les montrer à l'extracteur — celui-ci ne pouvait donc PAS
rattacher d'URL à chaque événement, qui retombait sur le placeholder
« gmail:{message_id}#{idx} ». Résultat : des événements marqués « sans page »
alors que la newsletter contenait bien le lien vers l'article.

Le parseur préserve désormais les liens (scripts.gmail_collect._linkify_html). Ce
script REJOUE les mails déjà collectés pour les événements encore en « gmail:… » :
il ré-ouvre le mail, ré-extrait (liens visibles cette fois), retrouve l'événement
par son titre et RENSEIGNE sa vraie url_source. Les passes date/lieu/image peuvent
ensuite lire la page comme pour n'importe quelle source.

On ne CRÉE aucun événement ; on ne touche qu'aux lignes « gmail:… » retrouvées ;
on ne remplace que par une vraie URL http. Réversible (l'ancienne valeur était un
placeholder sans page). Dry-run par défaut.

Exemples :
  .venv/bin/python3 -m scripts.gmail_relink                 # dry-run (liste)
  .venv/bin/python3 -m scripts.gmail_relink --execute
  .venv/bin/python3 -m scripts.gmail_relink --execute --cap 40
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import usage
from scripts.dedupe import _sig_tokens
from scripts.gmail_collect import (
    API_ERROR, DEFAULT_MODEL, build_service, extract_events, parse_message,
)

log = get_logger("gmail_relink")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# « gmail:{message_id}#{idx} » → message_id
_MID_RE = re.compile(r"^gmail:([^#]+)")


def _message_id(url_source: str) -> str:
    m = _MID_RE.match(url_source or "")
    return m.group(1) if m else ""


def _match_url(title: str, extracted: list[dict]) -> str:
    """Cherche, parmi les événements ré-extraits du mail, celui qui correspond au
    titre `title` et renvoie sa vraie URL http (ou "" si pas de correspondance sûre).

    Correspondance conservatrice : intersection de tokens significatifs ≥ 2 (ou ≥ 1
    quand un titre est très court) ET meilleur candidat unique."""
    want = _sig_tokens(title)
    if not want:
        return ""
    best_url, best_score = "", 0
    for ev in extracted:
        url = (ev.get("url") or "").strip()
        if not url.lower().startswith("http"):
            continue
        have = _sig_tokens(ev.get("titre") or ev.get("title") or "")
        score = len(want & have)
        if score > best_score:
            best_url, best_score = url, score
    threshold = 1 if len(want) <= 2 else 2
    return best_url if best_score >= threshold else ""


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Backfill des URLs d'articles des newsletters.")
    p.add_argument("--execute", action="store_true", help="Agir (sinon DRY-RUN).")
    p.add_argument("--cap", type=int, default=0, help="Limite le nombre de MAILS rejoués (0 = tous).")
    args = p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY non définie")
        return 1
    model = os.getenv("ANTHROPIC_MODEL_EXTRACT") or os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Événements RETENUS/EN ATTENTE encore sur un placeholder « gmail: » (sans page).
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, url_source FROM events_raw "
        "WHERE url_source LIKE 'gmail:%' "
        "  AND statut NOT IN ('rejected','merged') "
        "ORDER BY id").fetchall()]

    # Regroupe par mail : un seul ré-appel LLM par message, N événements rattachés.
    by_mid: dict[str, list[dict]] = {}
    for e in rows:
        mid = _message_id(e["url_source"])
        if mid:
            by_mid.setdefault(mid, []).append(e)

    mids = list(by_mid)
    if args.cap:
        mids = mids[:args.cap]

    mode = "EXÉCUTION" if args.execute else "DRY-RUN (rien ne bouge)"
    print(f"\nRattrapage des URLs de newsletters — {mode}")
    print(f"{len(rows)} événement(s) « gmail:… » · {len(by_mid)} mail(s) "
          f"(on en rejoue {len(mids)})\n")
    if not mids:
        print("Rien à rattraper. 🎉")
        conn.close()
        return 0

    client = anthropic.Anthropic(api_key=api_key)
    try:
        service = build_service()
    except Exception as exc:  # accès Gmail indisponible (token, réseau)
        log.error("Accès Gmail impossible : %s", exc)
        conn.close()
        return 1

    found = 0
    updates: list[tuple[str, int]] = []
    for mid in mids:
        try:
            raw = service.users().messages().get(userId="me", id=mid, format="full").execute()
        except Exception as exc:
            log.warning("Mail %s illisible (%s) — ignoré.", mid[:8], exc)
            continue
        email = parse_message(raw)
        extracted = extract_events(email, client, model)
        if extracted is API_ERROR:
            log.warning("Panne API pendant la ré-extraction — arrêt (reprise au prochain run).")
            break
        for e in by_mid[mid]:
            url = _match_url(e["title"], extracted)
            if url:
                found += 1
                updates.append((url, e["id"]))
                print(f"  [{e['id']}] {(e['title'] or '')[:52]:52} → {url[:60]}")

    print(f"\n{found} URL(s) retrouvée(s) sur {len(rows)} événement(s) « gmail:… ».")
    if not args.execute:
        print("DRY-RUN : rien n'a été modifié. Relance avec --execute.")
        conn.close()
        return 0
    # url_source est UNIQUE : si l'URL retrouvée est DÉJÀ prise (même événement
    # arrivé aussi par RSS), on ne l'écrase pas — c'est un doublon que dedupe gère.
    applied, collided = 0, 0
    for url, eid in updates:
        try:
            # On renseigne l'URL ET on ré-arme la datation (une nouvelle page à lire).
            conn.execute(
                "UPDATE events_raw SET url_source=?, date_source='none' WHERE id=?",
                (url, eid))
            conn.commit()
            applied += 1
        except sqlite3.IntegrityError:
            conn.rollback()
            collided += 1
            log.info("URL déjà présente (doublon probable), on n'écrase pas : [%s] %s", eid, url)
    conn.close()
    tail = f" · {collided} déjà pris (doublon, laissé à dedupe)" if collided else ""
    print(f"\n=== {applied} événement(s) reliés à leur page{tail}. "
          "Relance ensuite : dates → venues → autocomplete. ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
