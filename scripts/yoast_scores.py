#!/usr/bin/env python3
"""Note les fiches publiées comme l'éditeur de Yoast le ferait — sans ouvrir l'éditeur.

D'OÙ ÇA VIENT — Franck, 16/09/2026 : « pourquoi ça peut pas recalculer direct
automatiquement Yoast ? ». Parce que Yoast calcule en JavaScript, dans le navigateur,
à l'ouverture de la fiche, et nulle part ailleurs. Mesuré ce jour-là sur le site :
20 articles sur 24, 305 pages sur 306, 353 événements sur 364 sans aucune note — tout
ce que le pipeline publie par API. La colonne « Score SEO » du back-office, que Franck
lit comme un tableau de bord, disait « Non disponible » sur 678 fiches sur 694.

CE QUE ÇA FAIT, en trois pas, et rien d'autre :
  1. GET  cs/v1/yoast-papers  → les fiches à noter, servies par WordPress avec ce que
     l'éditeur donnerait au moteur (date au format de Yoast, titre rendu, locale) ;
  2. node scripts/yoast_score.js → le moteur de Yoast lui-même (paquet npm `yoastseo`),
     sur le VPS, sans réseau ;
  3. POST cs/v1/yoast-scores  → WordPress écrit les deux métas ET reconstruit
     l'indexable, la table que la colonne lit réellement.

Ne recalcule que ce qui a changé : `cs_score_at` (posé par la route) est comparé à
`post_modified_gmt` côté WordPress. Une fiche ouverte dans l'éditeur par Franck se
fait renoter par Yoast lui-même — ce script ne l'écrase que si elle change ensuite.

RÉVERSIBLE : Yoast réécrit ces champs à la prochaine ouverture. Dry-run par défaut.

Usage (VPS) :
    .venv/bin/python -m scripts.yoast_scores                    # dry-run : montre les notes
    .venv/bin/python -m scripts.yoast_scores --apply --cap 300  # écrit (cron, 12h00)
    .venv/bin/python -m scripts.yoast_scores --ids 8236 8231 --tout --apply
Prérequis, une fois : `npm install` dans /root/evenements (node ≥ 20, présent).
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger          # noqa: E402
from scripts.publisher import _headers       # noqa: E402 — même en-tête X-CS-Auth que la publication

log = get_logger("yoast-scores")
MOTEUR = ROOT / "scripts" / "yoast_score.js"
LOT = 50   # fiches par POST : assez petit pour qu'un échec nomme peu de fiches


def papiers(wp_url: str, auth, types: list[str], cap: int, ids: list[int], tout: bool) -> dict:
    params = {"types": ",".join(types), "limit": cap}
    if ids:
        params["ids"] = ",".join(str(i) for i in ids)
    if tout:
        params["tout"] = "1"
    r = requests.get(f"{wp_url}/?rest_route=/cs/v1/yoast-papers", params=params,
                     auth=auth, headers=_headers(auth), timeout=120)
    r.raise_for_status()
    return r.json()


def noter(entrees: list[dict]) -> list[dict]:
    """Fait tourner le moteur. Une panne de Node est une panne, jamais un « 0 noté »."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("`node` introuvable — Node ≥ 20 est requis sur cette machine.")
    if not (ROOT / "node_modules" / "yoastseo").exists():
        raise RuntimeError("Le paquet `yoastseo` n'est pas installé : lancer `npm install` "
                           f"dans {ROOT} (une fois).")
    proc = subprocess.run([node, str(MOTEUR)], input=json.dumps(entrees, ensure_ascii=False),
                          capture_output=True, text=True, cwd=str(ROOT), timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"le moteur a échoué : {proc.stderr.strip()[:500]}")
    return json.loads(proc.stdout)


def ecrire(wp_url: str, auth, notes: list[dict]) -> dict:
    total = {"ecrits": 0, "erreurs": [], "recompte": {}}
    for i in range(0, len(notes), LOT):
        lot = [{"id": n["id"], "seo": n["seo"], "readability": n["lisibilite"]} for n in notes[i:i + LOT]]
        r = requests.post(f"{wp_url}/?rest_route=/cs/v1/yoast-scores", json={"scores": lot},
                          auth=auth, headers=_headers(auth), timeout=300)
        r.raise_for_status()
        rep = r.json()
        total["ecrits"] += int(rep.get("ecrits") or 0)
        total["erreurs"] += list(rep.get("erreurs") or [])
        total["recompte"] = rep.get("recompte") or total["recompte"]
    return total


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--apply", action="store_true", help="Écrit les notes (sinon simulation).")
    p.add_argument("--types", default="post,page,tribe_events")
    p.add_argument("--cap", type=int, default=200, help="Fiches par run (max 500).")
    p.add_argument("--ids", nargs="*", type=int, default=[])
    p.add_argument("--tout", action="store_true", help="Ignore cs_score_at : renote même l'inchangé.")
    args = p.parse_args(argv)

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    if not all([wp_url, auth[0], auth[1]]):
        log.error("WP_AS_URL / WP_AS_USER / WP_AS_APP_PASSWORD manquants dans .env")
        return 2

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    rep = papiers(wp_url, auth, types, args.cap, args.ids, args.tout)
    fiches = rep.get("papers") or []
    # Un zéro doit dire d'où il vient : combien sont publiées, combien présentées.
    log.info("%d fiche(s) à noter sur %d publiée(s) (%s)%s", len(fiches), rep.get("publiees", "?"),
             ", ".join(rep.get("types") or types), "" if fiches else " — rien n'a changé depuis le dernier passage")
    if not fiches:
        return 0

    notes = noter(fiches)
    par_id = {f["id"]: f for f in fiches}
    for n in notes:
        f = par_id.get(n["id"], {})
        print(f"{n['id']:>6} {f.get('type', '?'):<13} SEO {n['seo']:>3}  lisibilité {n['lisibilite']:>3}"
              f"  (avant : {f.get('linkdex') or '—'} / {f.get('content_score') or '—'})  {f.get('post_title', '')[:50]}")

    if not args.apply:
        print(f"\nDRY-RUN — {len(notes)} note(s) calculée(s), rien d'écrit. Relancer avec --apply.")
        return 0

    res = ecrire(wp_url, auth, notes)
    rc = res["recompte"]
    resume = " · ".join(f"{t} : {v['sans_score']}/{v['publiees']} sans note" for t, v in rc.items())
    log.info("=== Scores Yoast : %d écrite(s) sur %d calculée(s), %d erreur(s). Reste %s ===",
             res["ecrits"], len(notes), len(res["erreurs"]), resume)
    for e in res["erreurs"][:10]:
        log.warning("  %s", e)
    from utils import pipeline_status, slack
    msg = (f"📐 *Scores Yoast* — {res['ecrits']} fiche(s) notée(s) avec le moteur de Yoast "
           f"(hors éditeur). Reste sans note : {resume}")
    if res["erreurs"]:
        msg += f"\n⚠️ {len(res['erreurs'])} erreur(s) : " + " · ".join(res["erreurs"][:3])
    slack.notify(msg)
    pipeline_status.record_run("yoast_scores", ok=res["ecrits"], error=len(res["erreurs"]), summary=msg[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
