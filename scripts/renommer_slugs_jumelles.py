#!/usr/bin/env python3
"""Rebaptise les adresses des jumelles italiennes qui portent `-2`, `-3`… — avec une 301.

══ ARBITRAGE DE FRANCK, 30/09/2026 ══ « ça va pas du tout de mettre 2, 3 ». Puis, sur
les deux choix proposés : l'adresse italienne est tirée du TITRE ITALIEN, et les
adresses déjà en ligne sont RENOMMÉES avec redirection 301.

D'OÙ VIENT LE `-2`. De la règle « URL commune à la paire » (28/07) : la jumelle recevait
le slug de l'original, déjà pris, et WordPress le dédoublonnait. Mesuré le 29/09 : les
103 jumelles italiennes à venir étaient toutes dans ce cas, et 29 % seulement étaient
indexées contre 56 % des fiches françaises. Le code qui posait ce slug est corrigé
(`utils.seo.slug_jumelle`, `translate_events`, `link_translations_as`) : ce script ne
s'occupe que de ce qui est DÉJÀ en ligne.

POURQUOI UNE 301 SUFFIT ICI SANS TABLE À ÉCRIRE. `wp_update_post` sur un post publié
enregistre l'ancien slug (`_wp_old_slug`) et WordPress redirige en 301 toute requête
sur l'ancienne adresse (`wp_old_slug_redirect`). C'est CE QUE L'ON CROIT — donc on le
VÉRIFIE après chaque renommage : l'ancienne adresse doit répondre 301 vers la nouvelle,
et la nouvelle 200. Au premier échec, le lot S'ARRÊTE : une adresse indexée qui rend
404 perd ce qu'elle avait accumulé (doctrine du 15/09), et on ne casse pas cent adresses
pour en avoir mal compris une.

PÉRIMÈTRE (règle 5) : fiches EN LIGNE, en italien (/it/), dont la fin n'est pas passée,
lues sur le SITE (règle 1) — pas en base.

LA COLLISION. Un titre qui ne se traduit pas (« Orlando ») redonne un slug déjà pris :
on ajoute la ville. Si ça ne suffit pas, la fiche est listée « à trancher » et n'est
PAS renommée — WordPress y remettrait un `-2`, précisément ce qu'on retire.

Usage (sur le VPS) :
    .venv/bin/python -m scripts.renommer_slugs_jumelles              # simulation
    .venv/bin/python -m scripts.renommer_slugs_jumelles --un 12345 --apply   # UNE fiche
    .venv/bin/python -m scripts.renommer_slugs_jumelles --apply     # tout le lot
"""
from __future__ import annotations

import argparse
import base64
import html
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.seo import a_suffixe_wp, slug_jumelle

log = get_logger("renommer_slugs_jumelles")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
_UA = {"User-Agent": "renommer_slugs_jumelles"}


def _slug(url: str) -> str:
    path = urlparse((url or "").strip()).path.rstrip("/")
    return path.rsplit("/", 1)[-1] if path else ""


def lire_calendrier(base: str) -> tuple[list[dict], int]:
    """Tout le calendrier en ligne, FR et IT, passé compris : les slugs des fiches
    terminées sont PRIS aussi, et une collision avec elles remettrait un `-2`.

    `start_date` lointain : avec la date du jour, l'API écarte les fiches EN COURS
    (mesuré le 29/09, voir gsc_report._fiches_vivantes)."""
    fiches, total, page = [], 0, 1
    while True:
        rep = None
        for _ in range(3):
            try:
                rep = requests.get(f"{base}/wp-json/tribe/events/v1/events", timeout=60,
                                   params={"per_page": 50, "page": page,
                                           "start_date": "2020-01-01"}, headers=_UA)
                break
            except requests.RequestException as exc:
                log.warning("page %d du calendrier : %s", page, exc)
        if rep is None or rep.status_code != 200:
            break
        d = rep.json()
        total = d.get("total", total)
        lot = d.get("events", [])
        if not lot:
            break
        for e in lot:
            venue = e.get("venue") if isinstance(e.get("venue"), dict) else {}
            fiches.append({"id": e["id"], "url": e["url"],
                           "titre": html.unescape(e.get("title") or ""),
                           "ville": venue.get("city") or "",
                           "fin": (e.get("end_date") or e.get("start_date") or "")[:10]})
        print(f"   calendrier : {len(fiches)}/{total} fiche(s) lue(s)…", flush=True)
        if len(fiches) >= total:
            break
        page += 1
    return fiches, total


def planifier(fiches: list[dict], aujourdhui: str) -> tuple[list[dict], list[dict]]:
    """Fonction PURE (pas de réseau) : ce qui sera renommé, et ce qui est à trancher.

    Retenue : jumelle italienne, non terminée, dont le slug finit par `-N`. Le nouveau
    slug ne doit être pris par AUCUNE autre fiche, ni par une autre ligne du plan."""
    pris = {_slug(f["url"]): f["id"] for f in fiches}
    plan, a_trancher = [], []
    for f in fiches:
        actuel = _slug(f["url"])
        if "/it/" not in f["url"] or f["fin"] < aujourdhui or not a_suffixe_wp(actuel):
            continue
        voulu = slug_jumelle(f["titre"], "", f["ville"])
        if pris.get(voulu, f["id"]) != f["id"]:
            # Pris par une autre fiche : slug_jumelle ajoute la ville quand on lui
            # désigne ce slug comme « original ».
            voulu = slug_jumelle(f["titre"], voulu, f["ville"])
        if not voulu or voulu == actuel:
            continue
        if pris.get(voulu, f["id"]) != f["id"]:
            a_trancher.append({**f, "actuel": actuel, "voulu": voulu,
                               "motif": f"« {voulu} » déjà pris par la fiche {pris[voulu]}"})
            continue
        pris[voulu] = f["id"]
        plan.append({**f, "actuel": actuel, "voulu": voulu})
    return plan, a_trancher


def _verifier(base_url_ancienne: str, voulu: str) -> tuple[bool, str]:
    """L'ancienne adresse rend-elle 301 vers la nouvelle, et la nouvelle 200 ?"""
    try:
        r = requests.get(base_url_ancienne, allow_redirects=False, timeout=30, headers=_UA)
        cible = r.headers.get("Location", "")
        if r.status_code != 301 or _slug(cible) != voulu:
            return False, f"ancienne adresse : {r.status_code} → « {cible or 'aucune'} »"
        r2 = requests.get(cible, timeout=30, headers=_UA)
        if r2.status_code != 200:
            return False, f"nouvelle adresse : {r2.status_code}"
        return True, "301 → 200"
    except requests.RequestException as exc:
        return False, f"vérification impossible : {exc}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Renomme les adresses -2/-3 des jumelles "
                                             "italiennes (simulation par défaut).")
    ap.add_argument("--apply", action="store_true", help="Renomme vraiment.")
    ap.add_argument("--un", type=int, metavar="WP_ID",
                    help="Ne traiter que cette fiche (à faire AVANT le lot).")
    args = ap.parse_args(argv)
    load_dotenv(ROOT / ".env")

    base = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
    aujourdhui = date.today().isoformat()
    fiches, total = lire_calendrier(base)
    if len(fiches) < total or not fiches:
        print(f"⚠ LECTURE INCOMPLÈTE : {len(fiches)}/{total} — rien n'est fait sur une "
              f"liste partielle (une collision pourrait passer inaperçue).")
        return 2

    plan, a_trancher = planifier(fiches, aujourdhui)
    it_vivantes = [f for f in fiches if "/it/" in f["url"] and f["fin"] >= aujourdhui]
    fr_suffixe = [f for f in fiches if "/it/" not in f["url"] and f["fin"] >= aujourdhui
                  and a_suffixe_wp(_slug(f["url"]))]
    if args.un:
        plan = [p for p in plan if p["id"] == args.un]
        if not plan:
            print(f"La fiche {args.un} n'est pas dans le plan (voir la simulation).")
            return 1

    print(f"\nPérimètre : {len(it_vivantes)} jumelle(s) italienne(s) non terminée(s) ; "
          f"{len(plan)} à renommer, {len(a_trancher)} à trancher.\n")
    for p in plan:
        print(f"   {p['id']:>6}  {p['actuel']}\n          → {p['voulu']}   ({p['titre'][:60]})")
    for p in a_trancher:
        print(f"   {p['id']:>6}  À TRANCHER, non renommée : {p['motif']}  ({p['titre'][:50]})")
    # Hors périmètre de l'arbitrage, mais même symptôme : on le COMPTE, sans y toucher.
    print(f"\n   Pour information : {len(fr_suffixe)} fiche(s) FRANÇAISE(S) non terminée(s) "
          f"portent aussi un `-N` (souvent deux événements au même titre) — non traitées :")
    for f in fr_suffixe:
        print(f"          {f['id']:>6}  {_slug(f['url'])}")

    if not args.apply:
        print("\nSimulation : rien n'a été modifié. Lire la liste ligne par ligne, puis "
              "commencer par UNE fiche : --un <numéro> --apply")
        return 0

    user, pwd = os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", "")
    if not (user and pwd):
        log.error("WP_AS_USER / WP_AS_APP_PASSWORD manquants dans .env")
        return 2
    jeton = base64.b64encode(f"{user}:{pwd}".encode()).decode("ascii")
    conn = sqlite3.connect(DB_PATH)
    faits = 0
    for n, p in enumerate(plan, 1):
        try:
            r = requests.post(f"{base}/?rest_route=/cs/v1/set-slug", timeout=30,
                              json={"post_id": p["id"], "slug": p["voulu"]}, auth=(user, pwd),
                              headers={**_UA, "X-CS-Auth": jeton})
            r.raise_for_status()
            rep = r.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"   ✗ {p['id']} : renommage refusé ({exc}) — ARRÊT du lot.")
            break
        obtenu = rep.get("new_slug") or ""
        if obtenu != p["voulu"]:
            # WordPress a dédoublonné malgré le plan : un slug pris que l'API publique ne
            # montre pas (brouillon, corbeille). On le DIT et on s'arrête.
            print(f"   ✗ {p['id']} : WordPress a posé « {obtenu} » au lieu de "
                  f"« {p['voulu']} » — ARRÊT du lot.")
            break
        ok, detail = _verifier(p["url"], p["voulu"])
        conn.execute("UPDATE events_raw SET wp_permalink_as=? WHERE wp_post_id_as=?",
                     (rep.get("permalink") or "", p["id"]))
        conn.commit()
        if not ok:
            print(f"   ✗ {p['id']} renommée, mais REDIRECTION NON CONFIRMÉE : {detail} — "
                  f"ARRÊT du lot. L'ancienne adresse était {p['url']}")
            break
        faits += 1
        print(f"   ✓ {n}/{len(plan)}  {p['id']} → {p['voulu']}  ({detail})", flush=True)
    # Règle 6 : le bilan se recompte, il ne se déduit pas de la longueur du plan.
    en_base = conn.execute(
        "SELECT COUNT(*) FROM events_raw WHERE wp_permalink_as LIKE '%/it/%' "
        "AND (wp_permalink_as GLOB '*-[0-9]/' OR wp_permalink_as GLOB '*-[0-9][0-9]/')").fetchone()[0]
    conn.close()
    print(f"\nBILAN : {faits} renommée(s) et vérifiée(s) sur {len(plan)} prévue(s). "
          f"Reste en base {en_base} adresse(s) italienne(s) finissant par -N (toutes "
          f"dates confondues : les fiches terminées ne sont pas renommées).")
    return 0 if faits == len(plan) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
