#!/usr/bin/env python3
"""Recalcule le score de RENDU (`home_score`, méta `as_home_score`) des fiches enrichies
qui n'en ont pas — SANS réécrire leur article, sans appel LLM.

D'OÙ ÇA VIENT — 2026-09-15. « Toujours que 2 articles dans À la une » (Vallée d'Aoste).
Le relevé de Franck donnait le motif fiche par fiche, et pour Pinocchio au Forte di Bard
(19-20/09, 582 mots, panel noté) : « score de rendu non calculé ». `backfill_home_score`
n'y pouvait rien — il recopie un score déjà présent dans enrich_data, et ces fiches n'en
ont pas : elles ont été enrichies AVANT que la formule existe. Mesuré : 21 fiches en
ligne et à venir dans ce cas, dont 19 avec un panel déjà noté.

La formule (utils/home_score.py, la MÊME qu'enrich) ne demande que trois choses, toutes
déjà en base : la moyenne du panel (enrich_data.reader_panel.mean), la source officielle
(enrich_data.source.officielle) et les visuels. Les deux premières se relisent ; les
AFFICHES, non — enrich ne conserve pas si une affiche portrait/paysage a été trouvée,
seulement l'étiquette finale, qui manque justement ici. On les traite donc comme
ABSENTES : le score recalculé est un PLANCHER. Une fiche qui avait deux affiches perd
au plus 1,5 point ; elle ne gagne jamais un point qu'elle n'aurait pas eu. La photo
officielle, elle, se recalcule depuis url_image et les pages officielles lues.

SANS PANEL, on ne calcule pas : la qualité éditoriale pèse 6 points sur 10, et « pas
mesuré » n'est pas « zéro » (même règle que utils.une.interet). Ces fiches sont comptées
à part avec la commande qui les répare (`enrich`, qui réécrit — c'est le prix).

Écrit la colonne home_score ET enrich_data["home"], pour que le publisher (qui lit la
colonne pour as_home_score et le bloc pour as_affiches/as_placement) ne voie qu'une
seule vérité. Le site ne change qu'à la republication, geste séparé.

DRY-RUN PAR DÉFAUT.
  .venv/bin/python -m scripts.rescore_home             # en ligne + à venir (défaut)
  .venv/bin/python -m scripts.rescore_home --apply
  .venv/bin/python -m scripts.rescore_home --tous      # y compris hors ligne / passées
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger                       # noqa: E402
from utils.home_score import calculer, photo_officielle   # noqa: E402

log = get_logger("rescore_home")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def evaluer(ev: dict) -> tuple[dict | None, str]:
    """(bloc home recalculé, motif). Fonction pure — c'est elle que la fixture éprouve.
    None quand on NE PEUT PAS calculer, avec le motif qui dit ce qu'il faudrait."""
    try:
        data = json.loads(ev.get("enrich_data") or "") or {}
    except (ValueError, TypeError):
        return None, "enrich_data illisible"
    pm = (data.get("reader_panel") or {}).get("mean")
    if pm is None:
        return None, "sans panel — la qualité éditoriale pèse 6 points, on ne l'invente pas → enrich"
    # SANS BLOC `source`, ON NE CALCULE PAS NON PLUS (ajouté le 15/09, après le premier
    # dry-run en production). Les 19 fiches calculables sortaient TOUTES « source non ·
    # aucune » : enrichies avant que le bloc source existe, elles n'ont ni l'information
    # « matière officielle lue » (+2,5) ni la liste des pages officielles qui permet de
    # reconnaître une photo du site (+0,75). Deux entrées sur trois manquent : ce n'est
    # plus un plancher à 1,5 point près, c'est 3,25 points d'inconnu sur 10. Écrire 4,8
    # pour Pinocchio (dont le doublon 8193, enrichi avec le bloc, valait 8,1) figerait la
    # fiche sous le seuil avec un chiffre qui a l'air mesuré — NULL dit « non calculé »,
    # 4,8 dirait « calculé, mauvais ». Un compteur doit dire ce qu'il compte (règle 6).
    if "source" not in data:
        return None, ("sans bloc source — enrichie avant que la source et la photo "
                      "officielle soient tracées : 3,25 points d'inconnu → enrich")
    src = data.get("source") or {}
    officielle = bool(src.get("officielle"))
    hotes = list(src.get("pages") or [])
    if ev.get("url_officiel"):
        hotes.append(ev["url_officiel"])
    photo_off = photo_officielle(ev.get("url_image") or "", hotes)
    h = calculer(pm, officielle, False, False, photo_off)   # affiches inconnues → absentes
    h["panel"] = pm
    h["source_officielle"] = officielle
    h["recalcule_le"] = date.today().isoformat()
    h["affiches_note"] = "affiches non conservées par enrich : traitées comme absentes (plancher)"
    return h, "ok"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tous", action="store_true",
                    help="toutes les fiches enrichies sans score (défaut : en ligne ET à venir)")
    ap.add_argument("--db", default=str(DB_PATH))
    args = ap.parse_args(argv)
    today = date.today().isoformat()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    where = ["home_score IS NULL", "COALESCE(enrich_data,'') <> ''", "duplicate_of IS NULL"]
    params: list = []
    if not args.tous:
        where += ["COALESCE(wp_post_id_as,0) > 0",
                  "(COALESCE(date_event_end, date_event_start, '') = '' "
                  " OR COALESCE(date_event_end, date_event_start) >= ?)"]
        params.append(today)
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM events_raw WHERE {' AND '.join(where)} ORDER BY date_event_start", params)]

    calculables, sans = [], []
    for ev in rows:
        h, motif = evaluer(ev)
        (calculables if h else sans).append((ev, h, motif))

    perim = "toutes les fiches enrichies" if args.tous else f"en ligne et à venir au {today}"
    print(f"\nRECALCUL DU SCORE DE RENDU — périmètre : {perim}")
    print(f"  sans score : {len(rows)} · calculables : {len(calculables)} · sans panel : {len(sans)}\n")
    au_dessus = 0
    for ev, h, _ in calculables:
        flag = " ≥ 6 → éligible à la une" if h["score"] >= 6 else ""
        au_dessus += h["score"] >= 6
        print(f"  [{ev['id']:>5} WP#{ev.get('wp_post_id_as') or '—':>5}] {h['score']:>4}  "
              f"panel {h['panel']} · source {'oui' if h['source_officielle'] else 'non'} · "
              f"{h['affiches']:<16} {(ev.get('title') or '')[:40]}{flag}")
    print(f"\n  → {au_dessus} fiche(s) passeraient le seuil de rendu (6) — PLANCHER, affiches non comptées.")
    if sans:
        ids = " ".join(str(ev["id"]) for ev, _, _ in sans)
        print(f"\n  NON CALCULABLES ({len(sans)}) — à ré-enrichir (réécrit l'article) :")
        for ev, _, motif in sans:
            print(f"    [{ev['id']:>5}] {(ev.get('title') or '')[:44]:<44} {motif.split(' — ')[0]}")
        print(f"    .venv/bin/python -m scripts.enrich {ids}")

    if not args.apply:
        print("\nDRY-RUN — rien écrit. --apply pour poser les scores.")
        return 0

    for ev, h, _ in calculables:
        data = json.loads(ev["enrich_data"]) or {}
        data["home"] = h
        conn.execute("UPDATE events_raw SET home_score=?, enrich_data=? WHERE id=?",
                     (h["score"], json.dumps(data, ensure_ascii=False), ev["id"]))
    conn.commit()
    relus = conn.execute(
        f"SELECT COUNT(*) FROM events_raw WHERE id IN ({','.join('?'*len(calculables))}) "
        "AND home_score IS NOT NULL", [ev["id"] for ev, _, _ in calculables]).fetchone()[0] if calculables else 0
    print(f"\nAPPLIQUÉ — {relus} score(s) relu(s) en base sur {len(calculables)} calculé(s).")
    if calculables:
        ids = " ".join(str(ev["id"]) for ev, _, _ in calculables)
        print("Le site ne change qu'après republication :")
        print(f"  .venv/bin/python -m scripts.publish_batch_as --ids {ids}")
    log.info("rescore_home : %d score(s) posés (%s)", relus, perim)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
