#!/usr/bin/env python3
"""Rattrape wp_permalink_as pour les événements Agenda Sabauda publiés AVANT
l'ajout de cette colonne — nécessaire pour que le DM automatique (webhook
Instagram) puisse donner le lien précis de la fiche (voir app.webhook_instagram).

Utilise le short-link WordPress natif `?p=<id>` (fonctionne pour n'importe quel
post type, sans dépendre du REST API ni de The Events Calendar) et suit la
redirection vers l'URL réelle — lecture seule côté WordPress, aucune écriture,
aucun risque pour le site.

Retry (3 tentatives, backoff court) sur les échecs RÉSEAU/5xx transitoires — sans
ça, un aléa ponctuel se confond avec un post réellement supprimé. Un 404 franc,
lui, n'est jamais retenté (le post n'existe plus côté WordPress, pas la peine
d'insister) — catégorisé séparément dans le résumé final pour distinguer
« à réessayer plus tard » de « probablement supprimé, action éditoriale à toi ».

Usage (sur le VPS) :
    .venv/bin/python scripts/backfill_permalinks_as.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("backfill-permalinks-as")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _resolve(wp_url: str, post_id: int, retries: int = 2) -> tuple[str, str]:
    """(permalien, état) pour un post. État : 'public' | 'non_public' | 'inexistant' |
    'indetermine'.

    ⚠️ RÉÉCRIT LE 2026-08-02 APRÈS UNE FAUSSE ALERTE MASSIVE. La version précédente
    suivait le short-link `/?p=<id>` en affirmant en docstring qu'il « fonctionne pour
    n'importe quel post type ». C'EST FAUX sur cette installation : `/?p=601` renvoie
    404 alors que le post 601 est parfaitement en ligne ; seule la forme
    `/?post_type=tribe_events&p=601` répond 200. Résultat : le script a déclaré
    « 61 posts probablement supprimés » sur 61 testés — dont Musilac, Katy Perry,
    Orelsan, le Nice Jazz Fest. Aucun ne l'était.

    On interroge donc l'API REST de WordPress, qui distingue les trois cas là où le
    front-end répond 404 pour deux d'entre eux (vérifié sur le site) :
      • 200                     → post PUBLIC, et `link` donne le VRAI permalien, préfixe
                                  de langue compris (/it/evenement/… pour l'italien) ;
      • rest_forbidden (401/403) → le post EXISTE mais n'est pas public : corbeille,
                                  brouillon ou privé. Ce n'est PAS une suppression, et
                                  il est restaurable ;
      • rest_post_invalid_id (404) → le post n'existe réellement plus.
    Un aléa réseau reste 'indetermine' et n'autorise jamais aucune conclusion."""
    api = f"{wp_url}/wp-json/wp/v2/tribe_events/{post_id}"
    for attempt in range(retries + 1):
        try:
            resp = requests.get(api, timeout=20)
            if resp.status_code == 200:
                return str((resp.json() or {}).get("link") or ""), "public"
            code = ""
            try:
                code = str((resp.json() or {}).get("code") or "")
            except ValueError:
                pass
            if code == "rest_post_invalid_id" or resp.status_code == 404:
                return "", "inexistant"
            if code == "rest_forbidden" or resp.status_code in (401, 403):
                return "", "non_public"
        except requests.RequestException:
            pass
        if attempt < retries:
            time.sleep(3 * (attempt + 1))
    return "", "indetermine"


def main() -> int:
    load_dotenv(ROOT / ".env")
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    if not wp_url:
        log.error("WP_AS_URL manquant dans .env")
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Deux populations, un seul traitement : le permalien ABSENT (motif d'origine de ce
    # script) et le permalien resté sous sa forme BRUTE de short-link
    # (« /?p=601 », « /it/?post_type=tribe_events&p=601 »). Le second cas a été révélé
    # par scripts/site_audit.py le 2026-08-02 : ces URL fonctionnent, mais elles
    # REDIRIGENT vers la vraie adresse. Tout ce qu'on diffuse avec (newsletter, réseaux,
    # sitemap) pointe donc sur un rebond, et un sitemap qui ne liste que des redirections
    # est précisément le défaut relevé par l'audit SEO du 2026-07-29. Les ré-résoudre est
    # sans risque : on suit le short-link natif de WordPress, en lecture seule.
    rows = conn.execute(
        "SELECT id, wp_post_id_as, title, wp_permalink_as FROM events_raw "
        "WHERE COALESCE(wp_post_id_as,'') <> '' "
        "  AND (COALESCE(wp_permalink_as,'') = '' "
        "       OR wp_permalink_as LIKE '%?p=%' "
        "       OR wp_permalink_as LIKE '%post_type=tribe_events%')"
    ).fetchall()
    a_vide = sum(1 for r in rows if not (r["wp_permalink_as"] or "").strip())
    log.info("%d événement(s) à traiter : %d sans permalien, %d avec un permalien resté "
             "en forme brute (redirige au lieu de pointer).",
             len(rows), a_vide, len(rows) - a_vide)
    if not rows:
        conn.close()
        return 0

    done = 0
    non_public: list[tuple[int, str]] = []   # existe mais corbeille / brouillon / privé
    gone: list[tuple[int, str]] = []         # n'existe réellement plus
    unresolved: list[tuple[int, str]] = []   # réseau : aucune conclusion
    for r in rows:
        title = (r["title"] or "")[:55]
        url, etat = _resolve(wp_url, int(r["wp_post_id_as"]))
        if etat == "public" and url:
            conn.execute("UPDATE events_raw SET wp_permalink_as=? WHERE id=?", (url, r["id"]))
            conn.commit()
            done += 1
            log.info("[%s] wp#%s -> %s — %s", r["id"], r["wp_post_id_as"], url[:70], title)
        elif etat == "non_public":
            non_public.append((r["id"], title))
            log.warning("[%s] wp#%s : EXISTE mais pas public (corbeille/brouillon) — %s",
                        r["id"], r["wp_post_id_as"], title)
        elif etat == "inexistant":
            gone.append((r["id"], title))
            log.warning("[%s] wp#%s : le post n'existe plus côté WordPress — %s",
                        r["id"], r["wp_post_id_as"], title)
        else:
            unresolved.append((r["id"], title))
            log.warning("[%s] wp#%s : état indéterminé après retry (réseau) — %s",
                        r["id"], r["wp_post_id_as"], title)

    log.info("Terminé : %d/%d permaliens récupérés · %d en corbeille/brouillon "
             "(RESTAURABLES, rien n'est perdu) · %d réellement supprimés · %d indéterminés.",
             done, len(rows), len(non_public), len(gone), len(unresolved))
    if non_public:
        log.info("Pas publics — à restaurer OU à réconcilier en base "
                 "(scripts.reconcile_wp_deleted) : %s",
                 ", ".join(str(i) for i, _ in non_public))
    if gone:
        log.info("Réellement supprimés (id backoffice) : %s",
                 ", ".join(str(i) for i, _ in gone))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
