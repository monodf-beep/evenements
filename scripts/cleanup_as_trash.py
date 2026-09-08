#!/usr/bin/env python3
"""Ménage Agenda Sabauda : met à la CORBEILLE WordPress (RÉVERSIBLE) le déchet.

S'appuie sur l'audit (scripts/cleanup_as_audit) et sur la route WordPress
cs/v1/trash (deploy/wordpress/cs-trash.php, à installer d'abord). Rien n'est
supprimé définitivement : tout part à la corbeille et reste restaurable.

Catégories (cf. audit) :
  - passes        : date de fin révolue ;
  - doublons      : fusionnés mais restés sur l'agenda ;
  - incomplets    : il manque un champ obligatoire.
    → les incomplets qui NE manquent QUE l'image sont récupérables (un run visuels
      leur pose une image) : PROTÉGÉS par défaut. --image-only pour les inclure.

Défaut (sans option) = ménage RECOMMANDÉ : passes + doublons + incomplets
« vrai déchet » (hors image-seule). --tout inclut aussi les image-seule.

Sécurité : DRY-RUN par défaut (liste sans rien faire). Il faut --execute pour agir.
Après mise à la corbeille, on efface wp_post_id_as/published_as_date en base (l'événement
n'est plus « sur l'agenda » ; s'il est complété un jour, il pourra repartir proprement).

Exemples :
  .venv/bin/python3 -m scripts.cleanup_as_trash                    # dry-run, set recommandé
  .venv/bin/python3 -m scripts.cleanup_as_trash --execute --cap 20
  .venv/bin/python3 -m scripts.cleanup_as_trash --tout --execute   # tout, y compris image-seule
  .venv/bin/python3 -m scripts.cleanup_as_trash --passes --execute # seulement les passés
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import completeness as comp
from scripts.cleanup_as_audit import audit
from scripts.publisher_as import _headers

log = get_logger("cleanup_as_trash")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _is_image_only(reason: str) -> bool:
    """True si le manque se limite à l'image (événement récupérable)."""
    return reason.strip() == "manque : Image"


def _select(res: dict, args) -> list[dict]:
    """Construit la liste finale d'événements à mettre à la corbeille."""
    chosen: list[dict] = []
    want_passes = args.passes or args.tout or args.default_set
    want_doublons = args.doublons or args.tout or args.default_set
    want_incomplets = args.incomplets or args.tout or args.default_set
    if want_passes:
        chosen += res["passes"]
    if want_doublons:
        chosen += res["doublons"]
    if want_incomplets:
        for r in res["incomplets"]:
            if _is_image_only(r["reason"]) and not (args.tout or args.image_only):
                continue  # protégé : récupérable par un run visuels
            chosen += [r]
    # Dédoublonne par wp id (au cas où).
    seen, out = set(), []
    for r in chosen:
        if r["wp"] and r["wp"] not in seen:
            seen.add(r["wp"])
            out.append(r)
    return out


def trash_one(wp_url: str, auth, wp_id: int, force: bool = False) -> bool:
    """Met un événement à la corbeille. force=True autorise aussi un post PUBLIÉ
    (nécessaire pour retirer un non-événement publié par erreur ; réservé à un appel
    délibéré comme scripts.audit_non_events)."""
    endpoint = f"{wp_url}/?rest_route=/cs/v1/trash"
    payload = {"id": wp_id}
    if force:
        payload["force"] = True
    try:
        resp = requests.post(endpoint, json=payload, auth=auth,
                             headers=_headers(auth), timeout=45)
        resp.raise_for_status()
        return bool(resp.json().get("trashed"))
    except requests.HTTPError as exc:
        log.error("Corbeille WP#%s échec (%s) : %s", wp_id,
                  exc.response.status_code, exc.response.text[:200])
        return False
    except (requests.RequestException, ValueError) as exc:
        log.error("Corbeille WP#%s injoignable : %s", wp_id, exc)
        return False


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Ménage Agenda Sabauda (corbeille WP, réversible).")
    p.add_argument("--passes", action="store_true", help="Cibler les passés.")
    p.add_argument("--doublons", action="store_true", help="Cibler les doublons.")
    p.add_argument("--incomplets", action="store_true", help="Cibler les incomplets (hors image-seule).")
    p.add_argument("--image-only", dest="image_only", action="store_true",
                   help="Inclure aussi les incomplets qui ne manquent QUE l'image.")
    p.add_argument("--tout", action="store_true", help="Tout (passés + doublons + incomplets + image-seule).")
    p.add_argument("--execute", action="store_true", help="Agir réellement (sinon DRY-RUN).")
    p.add_argument("--cap", type=int, default=100, help="Nombre max par run.")
    p.add_argument("--delay", type=float, default=0.5, help="Pause (s) entre deux appels.")
    p.add_argument("--limit", type=int, default=1000, help="Événements poussés à examiner.")
    args = p.parse_args(argv)

    # Aucune catégorie précisée → set RECOMMANDÉ (passes+doublons+incomplets déchet).
    args.default_set = not (args.passes or args.doublons or args.incomplets
                            or args.image_only or args.tout)

    load_dotenv(ROOT / ".env")
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    today = date.today().isoformat()

    conn = sqlite3.connect(DB_PATH)
    res = audit(conn, today, wp_url, args.limit)
    targets = _select(res, args)[:args.cap]

    mode = "EXÉCUTION" if args.execute else "DRY-RUN (rien ne bouge)"
    scope = "TOUT" if args.tout else ("recommandé" if args.default_set else "sélection")
    print(f"\nMénage Agenda Sabauda — {mode} · cible : {scope} · {len(targets)} événement(s)\n")
    for r in targets:
        print(f"  WP#{r['wp']:>5} · {r['date']:>10} · {r['title']:<60} · {r['reason']}")
    if not args.execute:
        print(f"\nDRY-RUN : {len(targets)} seraient mis à la corbeille. "
              "Relance avec --execute pour agir.")
        conn.close()
        return 0

    if not all([wp_url, auth[0], auth[1]]):
        log.error("WP_AS_URL/USER/APP_PASSWORD manquants — impossible d'agir.")
        conn.close()
        return 1

    ok = fail = 0
    for i, r in enumerate(targets, 1):
        if trash_one(wp_url, auth, r["wp"]):
            conn.execute("UPDATE events_raw SET wp_post_id_as=NULL, published_as_date=NULL "
                         "WHERE id=?", (r["id"],))
            conn.commit()
            ok += 1
            log.info("Corbeille WP#%s (DB#%s) : %s", r["wp"], r["id"], r["title"][:50])
        else:
            fail += 1
        if args.delay and i < len(targets):
            time.sleep(args.delay)
    conn.close()
    print(f"\n=== Ménage terminé : {ok} à la corbeille, {fail} échec(s) ===")
    print("Réversible : Événements → Corbeille dans WordPress pour restaurer.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
