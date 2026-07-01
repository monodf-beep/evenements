#!/usr/bin/env python3
"""Crée un BROUILLON de newsletter « Agenda Sabaudo » à partir des événements de la semaine.

Reprend le gabarit « magazine » de l'Observatoire (héros « À la une », sommaire
« Aussi cette semaine », cartes « Le tour des territoires », favicons, pied
éditorial) via utils.newsletter_variants.variant_magazine, et la mécanique Brevo
(utils.brevo, création de BROUILLON — jamais d'envoi). Sélection déterministe
(pas de LLM) : les événements retenus d'un territoire qui chevauchent la fenêtre
(par défaut les 7 prochains jours), triés par importance.

Config (.env) :
    BREVO_API_KEY          clé API Brevo (même que l'Observatoire)
    BREVO_SENDER_NAME      défaut « Agenda Sabaudo »
    BREVO_SENDER_EMAIL     email expéditeur VALIDÉ dans Brevo
    BREVO_LIST_ID          id de la liste (Agenda Sabaudo — Newsletter, ex. 12)
    BREVO_LOGO_URL         (option) URL du logo hébergé (bibliothèque média Brevo)
    NEWSLETTER_TERRITOIRE  défaut « Savoie »
    NEWSLETTER_DASHBOARD_URL (option) lien « voir tout l'agenda » (site/tableau de bord)

Usage :
    python scripts/newsletter.py                         # 7 prochains jours, Savoie
    python scripts/newsletter.py --from 2026-07-03 --to 2026-07-06
    python scripts/newsletter.py --check                 # liste expéditeurs + listes Brevo
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.brevo import (BrevoError, campaign_edit_url, create_draft_campaign,
                         list_contact_lists, list_senders)
from utils.newsletter_variants import variant_magazine
from utils.sources import load_territory_images, pick_image

log = get_logger("newsletter")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
_MONTHS_FR = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
              "août", "septembre", "octobre", "novembre", "décembre"]
# Nb de cartes détaillées (« Le tour des territoires ») ; au-delà, le reste passe
# en sommaire numéroté (« Aussi cette semaine »).
MAX_CARDS = 6


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", text or "")).strip()


def _fmt_day(iso: str) -> str:
    """'2026-07-05' -> '5 juillet'."""
    try:
        d = date.fromisoformat(iso)
        return f"{d.day} {_MONTHS_FR[d.month]}"
    except (ValueError, TypeError):
        return ""


def _fmt_range(start: str, end: str) -> str:
    s, e = _fmt_day(start), _fmt_day(end)
    if s and e and start != end:
        return f"du {s} au {e}"
    return s or (f"jusqu'au {e}" if e else "")


def _summary(ev: dict) -> str:
    """Résumé de carte : chapô rédigé > justification > description brute."""
    if ev.get("enrich_data"):
        try:
            chapo = (json.loads(ev["enrich_data"]).get("article") or {}).get("chapo", "").strip()
            if chapo:
                return chapo
        except (ValueError, TypeError):
            pass
    if (ev.get("llm_justification") or "").strip():
        return ev["llm_justification"].strip()
    return _clean(ev.get("description"))[:220]


def _is_radar(ev: dict) -> bool:
    return ev.get("source_type") == "radar" or "(radar)" in (ev.get("source_name") or "")


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except ValueError:
        return ""


def build_item(ev: dict, banners: dict | None = None) -> dict:
    """Transforme un enregistrement événement en item de gabarit.

    Image : celle en base ; à défaut, repli sur la bannière de marque du
    territoire (aucune carte n'est jamais vide). Le crédit (photo licenciable
    Wikimedia Commons) est affiché quand il existe."""
    radar = _is_radar(ev)
    url = "" if radar else (ev.get("url_source") or "")
    image = ev.get("url_image") or ""
    if not image and banners is not None:
        image = pick_image(ev.get("territoire", ""), key=str(ev.get("id", "")), images=banners)
    return {
        "title": (ev.get("article_title") or ev.get("title") or "").strip(),
        "summary": _summary(ev),
        "image": image,
        "credit": ev.get("image_credit") or "",
        # radar (presse) : jamais crédité ni lié (charte §8)
        "url": url,
        "source": "" if radar else (ev.get("source_name") or ""),
        "domain": None if radar else (_domain(url) or None),
        "territory": ev.get("territoire") or "",
        "date_label": _fmt_range(ev.get("date_event_start") or "", ev.get("date_event_end") or ""),
    }


def select_events(conn: sqlite3.Connection, territoire: str, pfrom: str, pto: str,
                  limit: int) -> list[dict]:
    """Événements RETENUS du territoire qui chevauchent la fenêtre, par importance."""
    rows = conn.execute(
        "SELECT * FROM events_raw WHERE territoire = ? "
        "AND statut IN ('evaluated','published_cs','published_sub') AND duplicate_of IS NULL "
        "AND COALESCE(date_event_start,'') <= ? AND COALESCE(date_event_end,'') >= ? "
        "ORDER BY llm_score DESC, date_event_start ASC LIMIT ?",
        (territoire, pto, pfrom, limit)).fetchall()
    return [dict(r) for r in rows]


def build_data(rows: list[dict], *, week_label: str, tagline: str) -> dict:
    """Répartit les événements en héros / cartes / sommaire pour le gabarit magazine."""
    banners = load_territory_images()
    items = [build_item(ev, banners) for ev in rows]
    hero = items[0] if items else None
    rest = items[1:]
    cards = rest[:MAX_CARDS]
    signaux = rest[MAX_CARDS:]
    preheader = (hero["summary"][:120] if hero else tagline[:120])
    return {
        "week_label": week_label,
        "tagline": tagline,
        "preheader": preheader,
        "hero": hero,
        "items": cards,
        "signaux": signaux,
        "logo_url": os.getenv("BREVO_LOGO_URL") or None,
        "dashboard_url": os.getenv("NEWSLETTER_DASHBOARD_URL", ""),
    }


def _run_check(html: str) -> None:
    """Vérification automatique du HTML exact (non bloquante)."""
    try:
        from scripts.check_newsletter import check as _check_nl
        problems = [(lvl, lbl, ex) for lvl, lbl, ex in _check_nl(html) if lvl == "ERREUR"]
        if problems:
            log.warning("⚠ Vérification newsletter : %d problème(s) bloquant(s) :", len(problems))
            for _lvl, lbl, ex in problems:
                log.warning("   ✗ %s%s", lbl, (" — ex. " + ex[0][:80]) if ex else "")
        else:
            log.info("✓ Vérification newsletter : aucun problème bloquant.")
    except Exception as exc:  # le contrôle ne doit jamais casser la génération
        log.warning("Vérification newsletter non effectuée : %s", exc)


def _check(api_key: str) -> int:
    try:
        senders, lists = list_senders(api_key), list_contact_lists(api_key)
    except BrevoError as exc:
        log.error("Appel Brevo échoué : %s", exc)
        return 1
    log.info("=== Expéditeurs (BREVO_SENDER_EMAIL) ===")
    for s in senders:
        log.info("  %s — %s  %s", s.get("name", "?"), s.get("email", "?"),
                 "✅" if s.get("active") else "⏳ à valider")
    log.info("=== Listes (BREVO_LIST_ID) ===")
    for lst in lists:
        log.info("  id=%s — %s (%s abonnés)", lst.get("id"), lst.get("name", "?"),
                 lst.get("totalSubscribers", "?"))
    return 0


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Brouillon de newsletter Agenda Sabaudo.")
    parser.add_argument("--from", dest="dfrom", default="")
    parser.add_argument("--to", dest="dto", default="")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        log.error("BREVO_API_KEY absente du .env — impossible de créer le brouillon.")
        return 1
    if args.check:
        return _check(api_key)

    sender_name = os.getenv("BREVO_SENDER_NAME", "Agenda Sabaudo")
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "")
    list_ids = [int(x) for x in re.split(r"[,;\s]+", os.getenv("BREVO_LIST_ID", "").strip()) if x.isdigit()]
    territoire = os.getenv("NEWSLETTER_TERRITOIRE", "Savoie")
    if not sender_email or not list_ids:
        log.error("Config Brevo incomplète : BREVO_SENDER_EMAIL et/ou BREVO_LIST_ID manquants.")
        return 1

    today = date.today()
    pfrom = args.dfrom or today.isoformat()
    pto = args.dto or (today + timedelta(days=7)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = select_events(conn, territoire, pfrom, pto, args.limit)
    conn.close()
    log.info("%d événement(s) %s du %s au %s", len(rows), territoire, pfrom, pto)
    if not rows:
        log.warning("Aucun événement retenu sur la période — brouillon non créé.")
        return 1

    week_label = f"Du {_fmt_day(pfrom)} au {_fmt_day(pto)}"
    subject = f"Agenda Sabaudo — {territoire}, à l'affiche cette semaine"
    tagline = f"Les sorties à vivre en {territoire}"
    data = build_data(rows, week_label=week_label, tagline=tagline)
    html = variant_magazine(data)

    # Vérité terrain : on écrit le HTML EXACT localement pour l'inspecter.
    try:
        out = ROOT / "logs" / "derniere_newsletter.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(html, encoding="utf-8")
        log.info("HTML local écrit : %s", out)
    except OSError as exc:
        log.warning("Écriture HTML locale impossible : %s", exc)

    _run_check(html)

    try:
        cid = create_draft_campaign(
            api_key=api_key, name=f"Agenda Sabaudo — {territoire} — {week_label}",
            subject=subject, sender_name=sender_name, sender_email=sender_email,
            list_ids=list_ids, html_content=html)
    except BrevoError as exc:
        log.error("Création du brouillon Brevo échouée : %s", exc)
        return 1

    log.info("=== Brouillon Brevo créé (id=%s) — objet : %s ===", cid, subject)
    log.info("À relire/envoyer ici : %s", campaign_edit_url(cid))
    log.info("⚠ Aucun envoi automatique — validation et envoi manuels par toi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
