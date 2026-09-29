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


COURT_MAX = 400   # même frontière que panel_rattrapage.a_relire : en dessous, un catalogue


def geste(ev: dict, motif: str) -> tuple[str, str]:
    """(clé, libellé) : ce qu'il faut FAIRE d'une fiche non calculable (2026-09-29).

    Avant, la sortie donnait UNE commande pour les 52 : `enrich <tous les ids>`, qui aurait
    réécrit 52 articles — traductions comprises (on ne réécrit jamais une traduction, on
    retraduit l'original), et fiches sans intérêt pour la une comprises (un article réécrit
    pour rien). Règle 6 : une file ne contient que ce qu'un humain peut faire, et chaque
    ligne doit dire LEQUEL.
    """
    if ev.get("translation_of"):
        return "traduction", ("traduction — reçoit le score de son original dès qu'il en a "
                              "un (copie, ce script)")
    if motif.startswith("sans bloc source"):
        return "enrich", "sans bloc source → ré-enrichir (réécrit l'article)"
    try:
        data = json.loads(ev.get("enrich_data") or "") or {}
    except (ValueError, TypeError):
        data = {}
    corps = ((data.get("article") or {}).get("corps") or "").strip()
    from scripts.enrich import digne_de_la_une
    digne = digne_de_la_une(ev)
    if len(corps) >= COURT_MAX:
        return "panel", ("article développé sans panel → panel_rattrapage (relit, ne "
                         "réécrit rien ; en cron quotidien)")
    if digne:
        return "enrich", ("article COURT d'un événement digne de la une → ré-enrichir : "
                          "enrich écrit désormais un article long pour lui (réécrit)")
    return "rien", "article court, intérêt sous le plancher de la une → rien à faire"


def propager_aux_traductions(conn: sqlite3.Connection, apply: bool) -> list[tuple]:
    """Copie le score de rendu de l'original sur ses traductions qui n'en ont pas.

    `translate_events` le copie À LA CRÉATION de la traduction (« quatrième oubli », 06/09)
    — mais seulement ce jour-là. Un original qui reçoit son score APRÈS (rattrapage du
    panel, re-enrichissement) laissait sa jumelle sans score : invisible dans la une de
    l'autre langue. Copie et non recalcul, pour la raison déjà écrite là-bas : c'est le
    même événement. Ce n'est PAS l'héritage de VERDICT que panel_rattrapage refuse (un
    verdict désigne un geste de réécriture) : un score de rendu ne désigne rien, il ouvre
    ou ferme une vitrine."""
    rows = conn.execute(
        "SELECT t.id, t.title, o.home_score, o.id AS orig FROM events_raw t "
        "JOIN events_raw o ON o.id = t.translation_of "
        "WHERE t.home_score IS NULL AND o.home_score IS NOT NULL").fetchall()
    if apply and rows:
        conn.executemany("UPDATE events_raw SET home_score=? WHERE id=?",
                         [(r["home_score"], r["id"]) for r in rows])
        conn.commit()
    return [tuple(r) for r in rows]


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
        groupes: dict[str, list] = {}
        libelles: dict[str, str] = {}
        for ev, _, motif in sans:
            cle, lib = geste(ev, motif)
            groupes.setdefault(cle, []).append(ev)
            libelles[cle] = lib
        print(f"\n  NON CALCULABLES ({len(sans)}), rangées par geste :")
        for cle in ("enrich", "panel", "traduction", "rien"):
            evs = groupes.get(cle) or []
            if not evs:
                continue
            print(f"\n    {len(evs):>3} · {libelles[cle]}")
            for ev in evs:
                print(f"         [{ev['id']:>5}] {(ev.get('title') or '')[:60]}")
            if cle == "enrich":
                print("         .venv/bin/python -m scripts.enrich "
                      + " ".join(str(ev["id"]) for ev in evs))

    copies = propager_aux_traductions(conn, apply=False)
    print(f"\n  TRADUCTIONS sans score dont l'original en a un : {len(copies)}"
          + (" → copiées avec --apply" if copies else ""))
    for tid, titre, sc, orig in copies[:15]:
        print(f"    [{tid:>5}] ← [{orig:>5}] {sc:>4}  {(titre or '')[:50]}")
    if len(copies) > 15:
        print(f"    … et {len(copies) - 15} autre(s)")

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
    # Les traductions APRÈS les originaux : un original noté à l'instant transmet son score
    # dans le même passage, pas le lendemain.
    copies = propager_aux_traductions(conn, apply=True)
    recopies = conn.execute(
        f"SELECT COUNT(*) FROM events_raw WHERE id IN ({','.join('?'*len(copies))}) "
        "AND home_score IS NOT NULL", [c[0] for c in copies]).fetchone()[0] if copies else 0
    print(f"APPLIQUÉ — {recopies} traduction(s) ont reçu le score de leur original "
          f"(sur {len(copies)} candidate(s)).")
    # Le site suit SANS republication manuelle : `refresh_deplacement` (10h45, juste après
    # ce script) voit la note de une passer de « rien » à une valeur et republie la fiche.
    # (Ce message disait « le site ne change qu'après republication » : vrai le 15/09,
    # périmé depuis que refresh_deplacement pousse as_une_now.)
    log.info("rescore_home : %d score(s) posés, %d traduction(s) (%s)", relus, recopies, perim)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
