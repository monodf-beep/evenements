#!/usr/bin/env python3
"""Re-lie le mapping backoffice ↔ WordPress (Agenda Sabauda) quand les IDs ont
divergé (site WordPress reconstruit → IDs réattribués, mais le backoffice a gardé
les anciens `wp_post_id_as`).

Principe : on récupère l'inventaire RÉEL des événements WordPress (id + titre) via
l'API REST, on retrouve chaque événement du backoffice par correspondance de TITRE
normalisé, et on corrige `wp_post_id_as` s'il pointe vers un mauvais/inexistant id.

SÛR : lecture seule par défaut (--dry-run implicite) ; aucune création côté WP ;
n'écrit dans la base que les corrections, et SEULEMENT avec --apply.

Après un --apply, relancer l'imageur :
    .venv/bin/python scripts/refill_images_as.py --wp-ids <ids WP courants>
(ou en défaut, il repoussera les événements sans image proprement liés).

Usage (sur le VPS) :
    .venv/bin/python scripts/relink_wp_ids_as.py                 # diagnostic (dry-run)
    .venv/bin/python scripts/relink_wp_ids_as.py --apply         # applique les corrections
"""
from __future__ import annotations
import argparse
import html
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.scraper_events import init_db

log = get_logger("relink-wp-as")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _norm(title: str) -> str:
    """Titre normalisé pour la comparaison : entités décodées, sans accents,
    minuscules, ponctuation/espaces aplatis."""
    t = html.unescape(title or "")
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def fetch_wp_events(wp_url: str, auth) -> dict[str, list[int]]:
    """Inventaire WP : titre normalisé → [ids] (liste car titres parfois dupliqués)."""
    index: dict[str, list[int]] = {}
    # 1) API WordPress standard (inclut brouillons avec auth), PAGINÉE.
    # ⚠️ Corrigé le 2026-08-03 : un seul appel `per_page=100` sans boucle. WordPress
    # plafonne à 100 par page, or l'agenda compte près de 400 événements publiés (plus
    # les brouillons, inclus ici par `status=any`). L'inventaire était donc TRONQUÉ aux
    # 100 premiers, en silence — et toute fiche au-delà était comptée « introuvable ».
    # Sur un script dont le métier est justement de RÉPARER les `wp_post_id_as` cassés,
    # un inventaire tronqué ne produit pas une erreur visible : il produit de faux
    # diagnostics « pas de correspondance », c'est-à-dire exactement le contraire du
    # service rendu.
    try:
        page = 1
        while page <= 50:                       # borne de sécurité (5 000 événements)
            r = requests.get(f"{wp_url}/wp-json/wp/v2/tribe_events",
                             params={"per_page": 100, "page": page, "status": "any",
                                     "_fields": "id,title"},
                             auth=auth, timeout=30)
            # WordPress renvoie 400 (rest_post_invalid_page_number) quand on dépasse la
            # dernière page : c'est la fin normale de la pagination, pas une panne.
            if r.status_code != 200:
                break
            lot = r.json()
            if not isinstance(lot, list) or not lot:
                break
            for it in lot:
                key = _norm((it.get("title") or {}).get("rendered", ""))
                if key:
                    index.setdefault(key, []).append(int(it["id"]))
            if len(lot) < 100:
                break                            # dernière page
            page += 1
        if index:
            log.info("Inventaire WP : %d titre(s) sur %d page(s).", len(index), page)
            return index
    except (requests.RequestException, ValueError) as exc:
        log.warning("REST /wp/v2/tribe_events indisponible (%s) — repli API TEC.", exc)
    # 2) Repli : API REST de The Events Calendar
    try:
        r = requests.get(f"{wp_url}/wp-json/tribe/events/v1/events",
                         params={"per_page": 50, "status": "publish"}, auth=auth, timeout=30)
        if r.status_code == 200:
            for it in r.json().get("events", []):
                key = _norm(it.get("title", ""))
                if key:
                    index.setdefault(key, []).append(int(it["id"]))
    except (requests.RequestException, ValueError) as exc:
        log.error("API TEC indisponible aussi (%s).", exc)
    return index


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Re-lie wp_post_id_as par correspondance de titre.")
    parser.add_argument("--apply", action="store_true", help="Écrit les corrections (sinon dry-run).")
    args = parser.parse_args(argv)

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    if not all([wp_url, auth[0], auth[1]]):
        log.error("Variables WP_AS_URL / WP_AS_USER / WP_AS_APP_PASSWORD manquantes.")
        return 1

    index = fetch_wp_events(wp_url, auth)
    log.info("Inventaire WordPress : %d titre(s) d'événement récupéré(s).", len(index))
    if not index:
        log.error("Aucun événement WP récupéré — API REST inaccessible. Abandon.")
        return 1

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, wp_post_id_as FROM events_raw "
        "WHERE COALESCE(wp_post_id_as,'') <> '' AND duplicate_of IS NULL").fetchall()]

    # Qui revendique déjà quel post ? Indispensable pour ne pas créer de collision (voir
    # le garde-fou plus bas). Construit AVANT la boucle, sur l'état initial.
    proprietaire: dict[int, list[int]] = {}
    for ev in rows:
        try:
            proprietaire.setdefault(int(ev["wp_post_id_as"]), []).append(ev["id"])
        except (TypeError, ValueError):
            pass

    ok = fixed = ambigu = introuvable = conflit = 0
    for ev in rows:
        cur = str(ev.get("wp_post_id_as") or "").strip()
        matches = index.get(_norm(ev.get("title", "")), [])
        title = (ev.get("title") or "")[:50]
        if not matches:
            introuvable += 1
            log.warning("[bo %s] AUCUN événement WP au titre « %s » (wp_post_id_as=%s).",
                        ev["id"], title, cur)
            continue
        if len(matches) > 1:
            ambigu += 1
            log.warning("[bo %s] titre « %s » → PLUSIEURS ids WP %s (wp_post_id_as=%s) — ignoré (ambigu).",
                        ev["id"], title, matches, cur)
            continue
        wp_id = matches[0]
        if str(wp_id) == cur:
            ok += 1
            continue
        # ⚠️ GARDE-FOU AJOUTÉ LE 2026-08-03 — le script se protégeait d'UN cas (une ligne
        # locale avec PLUSIEURS candidats WP → « ambigu ») et jamais du cas SYMÉTRIQUE :
        # plusieurs lignes locales convergeant vers le MÊME post. Il écrivait sans jamais
        # demander si quelqu'un d'autre revendiquait déjà cet id.
        #
        # Ce n'est pas théorique. Le dry-run du 2026-08-03 proposait six corrections dont
        # au moins trois auraient créé un doublon, parce que la correspondance se fait par
        # TITRE et que le catalogue est BILINGUE : une paire FR/IT porte souvent le même
        # titre, et deux versions d'un même événement aussi.
        #   • bo 528 « Orlando » → 2340, alors que la ligne 3547 pointe déjà 2340 ;
        #   • bo 3517 « Voci riapparse » → 729, déjà revendiqué par la ligne 1148 ;
        #   • bo 3495 « Marisa Merz » → 763, déjà revendiqué par la ligne 959.
        # Deux lignes locales sur un même post, c'est exactement l'anomalie que
        # scripts/audit_wp_ghosts.py signale — on la fabriquerait en croyant réparer.
        #
        # En cas de conflit on NE TRANCHE PAS : départager deux fiches homonymes demande
        # de regarder les dates et le lieu, pas seulement le titre. On signale, on laisse
        # le lien en place, et la décision reste humaine.
        deja = [i for i in proprietaire.get(wp_id, []) if i != ev["id"]]
        if deja:
            conflit += 1
            log.warning("[bo %s] « %s » : WP#%s est DÉJÀ revendiqué par la/les ligne(s) %s "
                        "— non modifié (départager demande de comparer dates et lieu).",
                        ev["id"], title, wp_id, deja)
            continue

        fixed += 1
        log.info("[bo %s] « %s » : wp_post_id_as %s → %s %s",
                 ev["id"], title, cur, wp_id, "" if args.apply else "(dry-run)")
        if args.apply:
            conn.execute("UPDATE events_raw SET wp_post_id_as=? WHERE id=?", (wp_id, ev["id"]))
            conn.commit()
            # L'état de propriété évolue au fil de la boucle : la ligne cède son ancien
            # post et prend le nouveau, sinon deux corrections successives pourraient
            # converger vers le même id sans que la seconde le voie.
            try:
                proprietaire.get(int(cur), []).remove(ev["id"])
            except (TypeError, ValueError):
                pass
            proprietaire.setdefault(wp_id, []).append(ev["id"])

    conn.close()
    # « introuvable » ne veut PAS dire « lien cassé » : l'inventaire WP ne contient pas
    # les posts en CORBEILLE (status=any les exclut). Une ligne dont le post a été
    # corbeillé — il y en a plusieurs dizaines, cf. scripts/reconcile_wp_deleted.py —
    # tombe donc ici sans qu'il y ait rien à réparer. Le dit pour qu'on ne lise pas 283
    # comme 283 avaries.
    log.info("Bilan — déjà bons=%d · corrigés=%d · ambigus=%d · conflits=%d · "
             "sans correspondance=%d%s",
             ok, fixed, ambigu, conflit, introuvable,
             "" if args.apply else "  (dry-run : rien écrit)")
    log.info("Rappel : « sans correspondance » inclut tous les posts en CORBEILLE "
             "(absents de l'inventaire) — ce ne sont pas des liens à réparer.")
    if fixed and not args.apply:
        log.info("→ Relance avec --apply pour écrire, puis scripts/refill_images_as.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
