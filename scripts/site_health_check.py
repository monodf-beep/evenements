#!/usr/bin/env python3
"""Veille de santé des liens internes / sitemap — DÉTERMINISTE, zéro coût API.

Parcourt le sitemap XML d'agendasabauda.eu (via l'index puis chaque sous-sitemap),
vérifie que chaque URL listée répond bien en 200 SANS redirection. Attrape exactement
la classe de bug trouvée par l'audit SEO du 2026-07-29 : un sitemap qui référence encore
d'anciennes URLs (« /territoire/piemont/ ») qui redirigent en 301 vers les nouvelles
(« /que-faire-dans-le-piemont/ ») — gaspillage de budget de crawl, signal de qualité
dégradé pour Google.

Les trouvailles alimentent la MÊME table que le tableau de bord SEO (app.py::seo_view,
/seo) — un run de ce script apparaît dans l'historique à côté des audits manuels.

Usage (VPS) :
    .venv/bin/python -m scripts.site_health_check                # simulation (affiche)
    .venv/bin/python -m scripts.site_health_check --apply         # écrit dans /seo
    .venv/bin/python -m scripts.site_health_check --apply --cap 500
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.scraper_events import init_db

log = get_logger("site-health-check")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

_UA = {"User-Agent": "Mozilla/5.0 (compatible; CulturaSabaudaHealthCheck/1.0; "
                     "+https://agendasabauda.eu)"}


def _ensure_seo_tables(conn: sqlite3.Connection) -> None:
    """Même DDL que app.py::_ensure_seo_tables — dupliqué volontairement (le script
    tourne en cron, indépendant du process Flask ; garder les deux en phase si l'un
    des deux schémas évolue)."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS seo_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT DEFAULT (datetime('now')),
        scope TEXT, pages_count INTEGER, agents_used TEXT,
        tokens_used INTEGER, notes TEXT)""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS seo_findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER, page_url TEXT, category TEXT,
        severity TEXT NOT NULL DEFAULT 'medium', title TEXT NOT NULL,
        description TEXT, recommendation TEXT, source_agent TEXT,
        status TEXT NOT NULL DEFAULT 'todo',
        created_at TEXT DEFAULT (datetime('now')), resolved_at TEXT)""")
    conn.commit()


def _get(url: str, timeout: int = 15) -> requests.Response | None:
    try:
        return requests.get(url, headers=_UA, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        log.warning("Requête impossible sur %s : %s", url, exc)
        return None




def _sub_sitemaps(index_url: str) -> list[str]:
    """Sitemap index Yoast → liste des sous-sitemaps (post-sitemap.xml,
    territoire-sitemap.xml, etc.)."""
    resp = _get(index_url)
    if not resp or resp.status_code != 200:
        log.error("Sitemap index inaccessible (%s) : %s", index_url,
                  resp.status_code if resp else "pas de réponse")
        return []
    return re.findall(r"<loc>\s*([^<\s]+\.xml)\s*</loc>", resp.text)


def _urls_in_sitemap(sitemap_url: str) -> list[str]:
    resp = _get(sitemap_url)
    if not resp or resp.status_code != 200:
        log.warning("Sous-sitemap inaccessible (%s) : %s", sitemap_url,
                    resp.status_code if resp else "pas de réponse")
        return []
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", resp.text)


def check_urls(urls: list[str], cap: int, workers: int = 5) -> list[dict]:
    """Vérifie chaque URL (bornée par --cap), EN PARALLÈLE (`workers` requêtes à la
    fois — même valeur par défaut que « Concurrent requests » dans la config de crawl
    documentée par le skill claude-seo). Constaté en conditions réelles : en séquentiel
    (1 à la fois), 721 URLs sur ce site WordPress prenaient 15-20 minutes (~1,3-2 s par
    page, poids/plugins). Renvoie les problèmes trouvés.

    Chaque requête reste bornée par un timeout ABSOLU (20 s, ThreadPoolExecutor.result)
    — le `timeout` de `requests` seul se réinitialise à chaque octet reçu et ne suffit
    PAS à se protéger d'un serveur qui envoie les données au compte-goutte (constaté :
    un run est resté bloqué >9 min sur une seule URL malgré timeout=15 côté requests)."""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FutTimeout
    findings = []
    checked = 0
    batch = urls[:cap]
    total = len(batch)
    ex = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="url-check")
    futures = [ex.submit(_get, url) for url in batch]
    for url, fut in zip(batch, futures):
        try:
            resp = fut.result(timeout=20)
        except _FutTimeout:
            log.warning("Timeout ABSOLU (20s) sur %s — serveur trop lent/qui traîne.", url)
            resp = None
        checked += 1
        # Battement de cœur : sans ça, le script est SILENCIEUX tant qu'il ne trouve
        # rien à signaler — une longue vérification sans problème ressemble alors à un
        # blocage (confusion constatée en conditions réelles, deux fois de suite).
        if checked % 50 == 0 or checked == total:
            log.info("… %d/%d URL(s) vérifiée(s)", checked, total)
        if resp is None:
            findings.append({"page_url": url, "severity": "high",
                            "title": "URL du sitemap injoignable",
                            "description": "Timeout ou erreur réseau lors de la vérification.",
                            "recommendation": "Vérifier manuellement — le serveur a peut-être "
                                              "un problème temporaire, ou l'URL est vraiment morte."})
            continue
        if resp.status_code >= 400:
            findings.append({"page_url": url, "severity": "critical",
                            "title": f"URL du sitemap en erreur ({resp.status_code})",
                            "description": f"Le sitemap référence {url}, qui répond {resp.status_code}.",
                            "recommendation": "Retirer l'URL du sitemap (régénérer) ou corriger "
                                              "ce qui la casse (contenu supprimé/dépublié)."})
            continue
        if resp.history:
            final = resp.url
            hops = len(resp.history)
            findings.append({"page_url": url, "severity": "high" if hops > 1 else "medium",
                            "title": f"URL du sitemap redirige ({hops} saut(s)) au lieu de 200 direct",
                            "description": f"{url} → {final} (code final {resp.status_code}).",
                            "recommendation": "Régénérer le sitemap avec l'URL finale "
                                              f"({final}), et mettre à jour les liens internes "
                                              "en dur qui pointent encore vers l'ancienne."})
    log.info("%d URL(s) vérifiée(s), %d problème(s) trouvé(s)", checked, len(findings))
    ex.shutdown(wait=False)  # jamais attendre un éventuel thread encore bloqué
    return findings


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Vérifie la santé du sitemap/des liens internes (déterministe, zéro coût API).")
    parser.add_argument("--apply", action="store_true",
                        help="Écrit les trouvailles dans /seo (sinon simulation).")
    # Contrairement aux autres --cap du projet (protègent un BUDGET API), celui-ci ne
    # protège rien de coûteux — juste des requêtes HTTP espacées de 0,3 s. Sans état
    # entre les runs, un plafond trop bas revérifierait éternellement les mêmes
    # premières URLs sans jamais couvrir le reste (constaté : 721 URLs, plafond à 300).
    # Défaut large pour couvrir tout le site en un passage (~4 min pour 800 URLs).
    parser.add_argument("--cap", type=int, default=1500,
                        help="Nb max d'URLs vérifiées par run (défaut 1500 — couvre tout le site).")
    parser.add_argument("--base-url", default=os.getenv("WP_AS_URL", "https://agendasabauda.eu"))
    args = parser.parse_args(argv)

    base = args.base_url.rstrip("/")
    sub_sitemaps = _sub_sitemaps(f"{base}/sitemap_index.xml")
    if not sub_sitemaps:
        log.error("Aucun sous-sitemap trouvé — abandon.")
        return 1
    log.info("%d sous-sitemap(s) trouvé(s).", len(sub_sitemaps))

    all_urls: list[str] = []
    seen = set()
    for sm in sub_sitemaps:
        for u in _urls_in_sitemap(sm):
            if u not in seen:
                seen.add(u)
                all_urls.append(u)
    log.info("%d URL(s) unique(s) au total dans le sitemap.", len(all_urls))
    if len(all_urls) > args.cap:
        log.info("Borné à --cap %d (relance pour couvrir le reste).", args.cap)

    findings = check_urls(all_urls, args.cap)

    if not findings:
        log.info("=== Aucun problème trouvé. ===")
        return 0

    for f in findings:
        log.info("[%s] %s — %s", f["severity"], f["title"], f["page_url"])

    if not args.apply:
        log.info("=== %d problème(s) détecté(s) (simulation : rien écrit — relance avec "
                 "--apply). ===", len(findings))
        return 0

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    _ensure_seo_tables(conn)
    cur = conn.execute(
        "INSERT INTO seo_runs (scope, pages_count, agents_used, tokens_used, notes) "
        "VALUES (?, ?, ?, 0, ?)",
        (f"Veille sitemap/liens — {base}", min(len(all_urls), args.cap),
         "site_health_check.py (déterministe, sans LLM)",
         f"{len(all_urls)} URL(s) au sitemap, {min(len(all_urls), args.cap)} vérifiée(s)."))
    run_id = cur.lastrowid
    written = skipped_dup = 0
    for f in findings:
        # Déduplication contre les points DÉJÀ ouverts (todo) : ce script tourne chaque
        # semaine en cron — sans ça, le même problème non résolu se réinsérerait à
        # l'identique à chaque passage (constaté : deux runs manuels le même jour ont
        # bien failli doubler les 31 mêmes trouvailles).
        exists = conn.execute(
            "SELECT 1 FROM seo_findings WHERE page_url=? AND title=? AND status='todo'",
            (f["page_url"], f["title"])).fetchone()
        if exists:
            skipped_dup += 1
            continue
        conn.execute(
            "INSERT INTO seo_findings (run_id, page_url, category, severity, title, "
            "description, recommendation, source_agent) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, f["page_url"], "technique", f["severity"], f["title"],
             f["description"], f["recommendation"], "site_health_check"))
        written += 1
    conn.commit()
    conn.close()
    log.info("=== %d problème(s) écrit(s), %d déjà ouvert(s) (ignoré(s)) — run #%d. ===",
             written, skipped_dup, run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
