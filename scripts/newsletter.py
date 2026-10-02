#!/usr/bin/env python3
"""Crée un BROUILLON de newsletter « Agenda Sabauda » à partir des événements de la semaine.

Reprend le gabarit « magazine » de l'Observatoire (héros « À la une », sommaire
« Aussi cette semaine », cartes « Le tour des territoires », favicons, pied
éditorial) via utils.newsletter_variants.variant_magazine, et la mécanique Brevo
(utils.brevo, création de BROUILLON — jamais d'envoi). Sélection déterministe
(pas de LLM) : les événements retenus d'un territoire qui chevauchent la fenêtre
(par défaut les 7 prochains jours), triés par importance.

Config (.env) :
    BREVO_API_KEY          clé API Brevo (même que l'Observatoire)
    BREVO_SENDER_NAME      défaut « Agenda Sabauda »
    BREVO_SENDER_EMAIL     email expéditeur VALIDÉ dans Brevo
    BREVO_LIST_ID          id de la liste (Agenda Sabauda — Newsletter, ex. 12)
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
from utils.sources import load_territory_category_images, pick_banner_image

log = get_logger("newsletter")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
_MONTHS_FR = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
              "août", "septembre", "octobre", "novembre", "décembre"]
# Nb de cartes détaillées (« Le tour des territoires ») ; au-delà, le reste passe
# en sommaire numéroté (« Aussi cette semaine »).
MAX_CARDS = 6
# Borne déterministe du seau « ça continue » (événements longs déjà annoncés), APRÈS
# retrait de ceux déjà listés lors d'éditions passées (anti-répétition persistante,
# cf. _seen_continue_ids). Limite le nombre pour ne pas alourdir le sommaire.
MAX_CONTINUE = 6


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
    """Résumé de carte : chapô rédigé, à défaut description nettoyée.

    On n'utilise JAMAIS `llm_justification` : c'est la justification de SCORING, écrite
    pour le back-office, pas pour un lecteur (charte §11 « pas de fuite de texte
    interne »). La cascade est donc : chapô rédigé (enrich_data.article.chapo) → sinon
    description brute nettoyée."""
    if ev.get("enrich_data"):
        try:
            chapo = (json.loads(ev["enrich_data"]).get("article") or {}).get("chapo", "").strip()
            if chapo:
                return chapo
        except (ValueError, TypeError):
            pass
    return _clean(ev.get("description"))[:220]


def _is_radar(ev: dict) -> bool:
    return ev.get("source_type") == "radar" or "(radar)" in (ev.get("source_name") or "")


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except ValueError:
        return ""


def build_item(ev: dict, cat_banners: dict | None = None) -> dict:
    """Transforme un enregistrement événement en item de gabarit.

    Image : celle en base ; à défaut, repli sur la bannière territoire × catégorie
    (aucune carte n'est jamais vide). Le crédit (photo licenciable Wikimedia
    Commons) est affiché quand il existe."""
    radar = _is_radar(ev)
    url = "" if radar else (ev.get("url_source") or "")
    image = ev.get("url_image") or ""
    if not image and cat_banners is not None:
        image = pick_banner_image(ev.get("territoire", ""), ev.get("llm_categorie", ""),
                                  str(ev.get("id", "")), cat_banners)
    return {
        # `_id` : privé, ignoré par le gabarit ; sert à tracer ce qui est parti en
        # newsletter (anti-répétition persistante, cf. _record_sent).
        "_id": ev.get("id"),
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
    """Événements RETENUS du territoire qui chevauchent la fenêtre, par importance.

    Pool de candidats (toutes dates confondues qui touchent la fenêtre) ; la
    répartition en seaux temporels (ouvre / dernière chance / continue) est faite
    ensuite par `_split_temporal`. Le tri llm_score DESC est conservé pour que chaque
    seau hérite d'un ordre d'importance stable et déterministe."""
    rows = conn.execute(
        "SELECT * FROM events_raw WHERE territoire = ? "
        "AND statut IN ('evaluated','published_cs','published_sub') AND duplicate_of IS NULL "
        "AND COALESCE(date_event_start,'') <= ? AND COALESCE(date_event_end,'') >= ? "
        "ORDER BY llm_score DESC, date_event_start ASC LIMIT ?",
        (territoire, pto, pfrom, limit)).fetchall()
    return [dict(r) for r in rows]


def _split_temporal(rows: list[dict], pfrom: str, pto: str
                    ) -> tuple[list[dict], list[dict], list[dict]]:
    """Range les événements (déjà triés par importance) en 3 seaux TEMPORELS (charte §11).

    Fenêtre [pfrom, pto], comparaison lexicographique sur dates ISO (déterministe,
    sans LLM) :
    - « ouvre »          : `date_event_start` DANS la fenêtre (pfrom ≤ start ≤ pto).
                           C'est le NEUF → héros + cartes détaillées.
    - « dernière chance » : commencé AVANT (start < pfrom) et se termine DANS la
                           fenêtre (pfrom ≤ end ≤ pto) → service factuel (pas d'urgence
                           inventée, §7).
    - « continue »        : commencé AVANT (start < pfrom) et se poursuit APRÈS la
                           fenêtre → liste compacte « ça continue », JAMAIS héros.

    « dernière chance » PRIME sur « continue » : un événement en cours qui ferme cette
    semaine est signalé comme fermeture, pas comme simple continuité (les deux
    conditions se chevauchent, l'ordre des `elif` tranche). Un événement long
    n'apparaît donc qu'à son OUVERTURE (une fois), puis en « continue », puis à sa
    FERMETURE. L'ordre llm_score DESC issu de select_events est préservé (tri stable)."""
    ouvre: list[dict] = []
    derniere: list[dict] = []
    continue_: list[dict] = []
    for ev in rows:
        start = ev.get("date_event_start") or ""
        end = ev.get("date_event_end") or ""
        if not start:
            continue  # sans date de début, pas de statut temporel (déjà filtré en SQL)
        if pfrom <= start <= pto:
            ouvre.append(ev)
        elif start < pfrom and end and pfrom <= end <= pto:
            derniere.append(ev)
        elif start < pfrom:
            continue_.append(ev)
    return ouvre, derniere, continue_


def _ensure_sent_table(conn: sqlite3.Connection) -> None:
    """Historique des événements réellement mis en NEWSLETTER (canal automatique).
    Sert l'anti-répétition PERSISTANTE (§11). Volontairement DISTINCT de
    `newsletter_editions` (compositions manuelles côté app, clé de territoire groupée)
    pour éviter tout conflit de clé. Simple CREATE IF NOT EXISTS — même schéma d'appoint
    que le reste du pipeline, pas de migration lourde."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS newsletter_sent ("
        "territoire TEXT NOT NULL, edition TEXT NOT NULL, event_id INTEGER NOT NULL, "
        "slot TEXT, sent_at TEXT, PRIMARY KEY (territoire, edition, event_id))")


def _seen_continue_ids(conn: sqlite3.Connection, territoire: str, edition: str) -> set:
    """Ids déjà listés en SOMMAIRE compact (slot 'signal') lors d'éditions ANTÉRIEURES du
    même territoire. Un événement long n'a droit qu'à UNE apparition en « ça continue » :
    au-delà, on le retire (il reste au catalogue). Le héros, lui, ne se répète pas par
    construction (keying par date d'ouverture)."""
    _ensure_sent_table(conn)
    rows = conn.execute(
        "SELECT DISTINCT event_id FROM newsletter_sent "
        "WHERE territoire=? AND slot='signal' AND edition < ?",
        (territoire, edition)).fetchall()
    return {r["event_id"] for r in rows}


def _record_sent(conn: sqlite3.Connection, territoire: str, edition: str, data: dict) -> None:
    """Trace ce qui vient d'être mis dans la newsletter (héros/carte/sommaire), pour
    l'anti-répétition des éditions suivantes. Idempotent (upsert sur la clé)."""
    _ensure_sent_table(conn)
    entries: list[tuple[dict, str]] = []
    if data.get("hero"):
        entries.append((data["hero"], "hero"))
    entries += [(it, "card") for it in data.get("items") or []]
    entries += [(it, "signal") for it in data.get("signaux") or []]
    for item, slot in entries:
        eid = item.get("_id")
        if eid is None:
            continue
        conn.execute(
            "INSERT INTO newsletter_sent (territoire, edition, event_id, slot, sent_at) "
            "VALUES (?,?,?,?,datetime('now','localtime')) "
            "ON CONFLICT(territoire, edition, event_id) DO UPDATE SET "
            "slot=excluded.slot, sent_at=excluded.sent_at",
            (territoire, edition, eid, slot))
    conn.commit()


def build_data(rows: list[dict], *, week_label: str, tagline: str,
               pfrom: str = "", pto: str = "", temporal: bool = True,
               seen: set | None = None) -> dict:
    """Répartit les événements sur le gabarit magazine.

    Deux modes :
    - `temporal=True` (défaut, canal AUTOMATIQUE, charte §11) : range par AXE TEMPOREL
      (ouvre / dernière chance / continue) — nécessite `pfrom`/`pto`. C'est ce mode qui
      empêche un événement long de squatter le héros chaque semaine.
    - `temporal=False` (composition MANUELLE) : respecte l'ordre d'entrée des `rows`
      (l'humain a déjà choisi et ordonné la sélection). On ne re-range PAS : héros = 1er,
      cartes = suivants, sommaire = le reste.

    Mapping seaux → gabarit `variant_magazine` (mode temporel) :
    - « ouvre » (le neuf) → héros (1er, le plus important) + cartes détaillées
      (« Le tour des territoires », jusqu'à MAX_CARDS), triés par importance ;
    - « dernière chance » + « ça continue » → sommaire compact « Aussi cette semaine ».

    Choix de mapping du sommaire (documenté) : le gabarit n'expose qu'UNE liste
    compacte numérotée, sans libellé de statut ni sous-titre par item (`_signaux_block`
    ne lit que title/url/territory). On ne peut donc PAS y afficher deux sous-listes
    étiquetées « Ça continue » / « Dernière chance ». On retient l'ordre le plus
    actionnable pour l'abonné : « dernière chance » d'ABORD (ça ferme, service factuel),
    puis le surplus d'ouvertures qui n'a pas tenu en cartes (fraîcheur), puis
    « ça continue ».

    Anti-répétition : le keying par date d'OUVERTURE fait qu'un événement long n'est héros
    qu'une seule fois. En plus, `seen` (ids déjà listés en sommaire lors d'éditions
    passées, cf. _seen_continue_ids) est retiré du seau « continue » → un événement long
    n'y figure qu'UNE fois sur toute sa durée. Reste le bornage déterministe MAX_CONTINUE
    (tri stable par importance)."""
    cat_banners = load_territory_category_images()

    # Composition manuelle : l'humain a ordonné la sélection → on n'en change pas l'ordre.
    if not temporal or not (pfrom and pto):
        items = [build_item(ev, cat_banners) for ev in rows]
        hero = items[0] if items else None
        rest = items[1:]
        return _pack_data(week_label, tagline, hero, rest[:MAX_CARDS], rest[MAX_CARDS:])

    ouvre_rows, derniere_rows, continue_rows = _split_temporal(rows, pfrom, pto)

    # Le NEUF alimente le héros puis les cartes détaillées ; l'éventuel surplus repart
    # en sommaire compact (voir plus bas).
    ouvre = [build_item(ev, cat_banners) for ev in ouvre_rows]
    hero = ouvre[0] if ouvre else None
    cards = ouvre[1:1 + MAX_CARDS]
    ouvre_overflow = ouvre[1 + MAX_CARDS:]

    derniere = [build_item(ev, cat_banners) for ev in derniere_rows]
    # « continue » : anti-répétition PERSISTANTE — on retire les événements déjà listés en
    # sommaire lors d'une édition précédente (ils ont eu leur apparition, ils restent au
    # catalogue), puis bornage déterministe (MAX_CONTINUE, tri stable par score).
    seen = seen or set()
    fresh_continue = [ev for ev in continue_rows if ev.get("id") not in seen]
    continue_ = [build_item(ev, cat_banners) for ev in fresh_continue[:MAX_CONTINUE]]

    # Sommaire « Aussi cette semaine » : dernière chance → surplus d'ouvertures → continue.
    signaux = derniere + ouvre_overflow + continue_
    return _pack_data(week_label, tagline, hero, cards, signaux)


def _pack_data(week_label: str, tagline: str, hero: dict | None,
               cards: list[dict], signaux: list[dict]) -> dict:
    """Assemble le dict attendu par `variant_magazine` (forme unique, deux modes)."""
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
    parser = argparse.ArgumentParser(description="Brouillon de newsletter Agenda Sabauda.")
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

    sender_name = os.getenv("BREVO_SENDER_NAME", "Agenda Sabauda")
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
    # Anti-répétition persistante : ce qui a déjà été listé en sommaire les semaines passées.
    seen = _seen_continue_ids(conn, territoire, pfrom)
    log.info("%d événement(s) %s du %s au %s", len(rows), territoire, pfrom, pto)
    if not rows:
        conn.close()
        log.warning("Aucun événement retenu sur la période — brouillon non créé.")
        return 1

    week_label = f"Du {_fmt_day(pfrom)} au {_fmt_day(pto)}"
    subject = f"Agenda Sabauda — {territoire}, à l'affiche cette semaine"
    tagline = f"Les sorties à vivre en {territoire}"
    data = build_data(rows, week_label=week_label, tagline=tagline,
                      pfrom=pfrom, pto=pto, seen=seen)
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
            api_key=api_key, name=f"Agenda Sabauda — {territoire} — {week_label}",
            subject=subject, sender_name=sender_name, sender_email=sender_email,
            list_ids=list_ids, html_content=html)
    except BrevoError as exc:
        conn.close()
        log.error("Création du brouillon Brevo échouée : %s", exc)
        return 1

    # Le brouillon existe : on trace ce qui a été mis en avant (anti-répétition future).
    _record_sent(conn, territoire, pfrom, data)
    conn.close()
    log.info("=== Brouillon Brevo créé (id=%s) — objet : %s ===", cid, subject)
    log.info("À relire/envoyer ici : %s", campaign_edit_url(cid))
    log.info("⚠ Aucun envoi automatique — validation et envoi manuels par toi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
