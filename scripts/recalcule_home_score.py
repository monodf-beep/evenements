#!/usr/bin/env python3
"""LE ROUVREUR de `home_score` — recalcule la note de RENDU des fiches qui n'en ont pas.

D'OÙ ÇA VIENT (2026-09-15). Franck, devant le hub de la Vallée d'Aoste : « toujours un
problème à la une pour aoste ». Mesuré : 11 fiches publiées encore devant nous, 2 seulement
en « À la une ». Les motifs rendus par `utils.une.une_etat` désignaient quatre fiches en
« score de rendu NON CALCULÉ » — dont Pinocchio, qui se joue dans quatre jours avec un
intérêt de 9, et le parc archéologique d'Aoste.

`scripts/backfill_home_score.py` existait déjà pour ça… mais il ne sait que RECOPIER un
score déjà présent dans `enrich_data["home"]["score"]`. Lancé ce jour-là : **0 fiche
remplie sur 95 candidates**, deux fois. Ces 95 fiches ont été enrichies par une version du
code ANTÉRIEURE au bloc qui calcule le score : il n'y a rien à recopier. Un zéro qui ne
disait pas s'il venait d'un échec ou d'une absence de cas — il venait des deux à la fois.

C'EST LE DÉFAUT STRUCTUREL DE LA RÈGLE 3, à l'identique : `home_score IS NULL` écarte la
fiche d'« À la une » ET d'« En évidence », définitivement, et personne ne l'en sort. Le
seul « rouvreur » disponible était de re-rédiger la fiche — un appel LLM complet pour
récupérer une addition de trois termes.

CE QU'IL CALCULE, et c'est la FORMULE DU DÉPÔT, pas une nouvelle (cf. enrich.py, bloc
« SCORE HOME ») — la recopier ailleurs aurait fabriqué le « deuxième détecteur pour la
même chose » du 08/09 :

    q   = panel de lecture (0-5) ramené sur 6      ← qualité éditoriale
    src = 2,5 si une source officielle est établie
    aff = 1,5 si affiche portrait ET paysage, 0,75 si l'une des deux ou une photo
          du site officiel, 0 sinon
    score = min(10, q + src + aff), arrondi au dixième

Tout vient de la base : `enrich_data` porte le panel et la source, les colonnes
`url_image_portrait` / `url_image_wide` portent les visuels, et la photo officielle se
reconnaît en comparant le domaine de `url_image` à celui de `url_officiel`. Aucun réseau,
aucun appel LLM, aucune écriture sur WordPress.

CE QU'IL NE PROMET PAS. Recalculer n'est pas remonter : une fiche courte n'a pas de panel
de lecture, donc q vaut 0 et le total plafonne à 4 — sous le plancher de 6 d'« À la une ».
Le dry-run affiche le score obtenu ET s'il franchit ce plancher, pour que personne ne
croie que la commande « débloque la une ». Elle rend une note juste ; ce que la note
autorise ne dépend plus d'elle.

DRY-RUN PAR DÉFAUT (règle 4). Lire la sortie avant `--apply`.

    .venv/bin/python -m scripts.recalcule_home_score            # dry-run
    .venv/bin/python -m scripts.recalcule_home_score --apply
    .venv/bin/python -m scripts.publish_batch_as --update --skip-media   # pour le site

Le score n'atteint WordPress qu'à la republication : tant qu'elle n'a pas eu lieu, la
colonne est juste en base et le site n'en sait rien (règle 1).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.logger import get_logger

log = get_logger("recalcule-home-score")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Plancher d'« À la une », lu chez lui plutôt que recopié (utils/une.py).
try:
    from utils.une import UNE_RENDU_MIN
except Exception:          # pragma: no cover - utils.une importe la config Obsidian
    UNE_RENDU_MIN = 6.0


def _hote(url: str) -> str:
    """Domaine d'une URL, `www.` retiré. '' si l'URL est vide ou illisible."""
    try:
        h = (urlparse(url or "").netloc or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def score_rendu(ev: dict) -> "tuple[float, str]":
    """(score, MOTIF lisible) — la formule d'enrich.py, appliquée à une ligne de base.

    Le motif est rendu pour être AFFICHÉ : une note qu'on ne peut pas contester se
    subit. Même exigence que `une_etat`, et pour la même raison.
    """
    try:
        ed = json.loads(ev.get("enrich_data") or "{}")
    except (ValueError, TypeError):
        ed = {}
    if not isinstance(ed, dict):
        ed = {}

    panel = (ed.get("reader_panel") or {}).get("mean") if isinstance(ed.get("reader_panel"), dict) else None
    q = (panel or 0) / 5 * 6

    # Source officielle : ce que l'enrichissement a CONSTATÉ prime sur la colonne, parce
    # qu'il a lu les pages ; `url_officiel` sert de repli pour les fiches d'avant.
    src_bloc = ed.get("source") if isinstance(ed.get("source"), dict) else {}
    has_official = bool(src_bloc.get("officielle")) or bool((ev.get("url_officiel") or "").strip())

    has_p = bool((ev.get("url_image_portrait") or "").strip())
    has_w = bool((ev.get("url_image_wide") or "").strip())

    # Photo du site officiel : même domaine que l'URL officielle ou qu'une page lue.
    img_h = _hote(ev.get("url_image") or "")
    off_hosts = {_hote(p) for p in (src_bloc.get("pages") or []) if isinstance(p, str)}
    off_hosts.add(_hote(ev.get("url_officiel") or ""))
    photo_off = bool(img_h) and img_h in {h for h in off_hosts if h}

    aff = 1.5 if (has_p and has_w) else (0.75 if (has_p or has_w or photo_off) else 0.0)
    score = round(min(10.0, q + 2.5 * has_official + aff), 1)

    motif = (f"panel {panel if panel is not None else '—'}/5 → {q:.1f}"
             f" + {'2.5 source officielle' if has_official else '0 pas de source officielle'}"
             f" + {aff} visuels"
             f" ({'deux affiches' if (has_p and has_w) else 'une affiche' if (has_p or has_w) else 'photo officielle' if photo_off else 'aucun'})")
    return score, motif


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Recalcule home_score pour les fiches enrichies qui n'en ont pas.")
    p.add_argument("--apply", action="store_true", help="Écrit (sinon dry-run).")
    p.add_argument("--ids", nargs="*", type=int, help="Restreint à ces ids locaux.")
    p.add_argument("--tout", action="store_true",
                   help="Inclut les fiches passées (par défaut : ce qui est encore devant nous, règle 5).")
    args = p.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    where = ["enrich_status = 'enriched'", "home_score IS NULL"]
    params: list = []
    if args.ids:
        where.append("id IN (%s)" % ",".join("?" * len(args.ids)))
        params += args.ids
    elif not args.tout:
        # Règle 5 : on ne travaille que sur ce qui est encore devant nous. Une fiche sans
        # date n'est PAS passée — c'est une donnée manquante, elle reste dans le lot.
        where.append("(COALESCE(date_event_end, date_event_start) >= date('now') "
                     "OR (date_event_start IS NULL AND date_event_end IS NULL))")
    rows = conn.execute("SELECT * FROM events_raw WHERE " + " AND ".join(where),
                        params).fetchall()

    franchit = 0
    for r in rows:
        ev = dict(r)
        score, motif = score_rendu(ev)
        ok = score >= UNE_RENDU_MIN
        franchit += ok
        print("%-6s %-42s %4.1f  %-3s %s" % (
            ev["id"], (ev.get("title") or "")[:42], score,
            "OUI" if ok else "non", motif))
        if args.apply:
            conn.execute("UPDATE events_raw SET home_score=? WHERE id=?", (score, ev["id"]))

    if args.apply:
        conn.commit()

    # RECOMPTE en base après écriture — jamais la longueur d'une liste (règle 6).
    restant = conn.execute(
        "SELECT COUNT(*) FROM events_raw WHERE enrich_status='enriched' AND home_score IS NULL"
    ).fetchone()[0]
    conn.close()

    print()
    print(f"{len(rows)} fiche(s) examinée(s) — périmètre : enrichies, sans note de rendu"
          + ("" if args.ids or args.tout else ", encore devant nous"))
    print(f"{franchit} atteindrai(en)t le plancher d'« À la une » ({UNE_RENDU_MIN}) ; "
          f"{len(rows) - franchit} resteraient dessous.")
    if args.apply:
        print(f"Écrit. Il reste {restant} fiche(s) enrichies sans note (toutes dates confondues).")
        print("Le site n'en sait rien tant que : "
              ".venv/bin/python -m scripts.publish_batch_as --update --skip-media")
    else:
        print("DRY-RUN — rien n'a été écrit. Relancer avec --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
