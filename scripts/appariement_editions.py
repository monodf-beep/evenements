#!/usr/bin/env python3
"""AUDIT (lecture seule) : combien de fiches en base sont l'ÉDITION SUIVANTE d'une fiche
déjà publiée — préalable au chantier « une URL par événement, mise à jour d'édition en
édition » (docs/AUDIT_SEO_2026-09-08.md).

N'ÉCRIT RIEN, n'appelle pas WordPress. Il produit la LISTE des paires proposées, avec la
raison, pour qu'un humain la lise avant qu'un mécanisme d'appariement automatique existe
— exactement le risque du 2026-08-02 (fusion « Une semaine pas plus » / « Fête du lac »)
transposé d'un jour à un an d'écart.

CRITÈRE (conservateur : mieux vaut un faux négatif — l'édition suivante crée une
nouvelle fiche comme aujourd'hui — qu'un faux positif qui écraserait la mauvaise fiche) :
  1. le titre, une fois les ANNÉES retirées, partage au moins 2 tokens significatifs
     avec au moins 60 % de recouvrement sur le plus court des deux titres — mêmes
     tokens et même seuil que `scripts.dedupe._groups`, pour rester cohérent avec ce
     que le dépôt appelle déjà « même événement » ;
  2. le LIEU (`utils.lieux.plie`) est identique quand les deux fiches en ont un — une
     fiche sans lieu ne DÉPARTAGE pas (donnée manquante, pas désaccord) ;
  3. l'écart entre les dates de début est de 300 à 430 jours (10 à 14 mois) — une
     tolérance choisie pour couvrir un festival qui glisse d'un mois d'une année sur
     l'autre, sans confondre deux éditions consécutives de moins d'un an (aucune dans
     ce périmètre) ;
  4. l'une des deux fiches est PUBLIÉE (`wp_post_id_as` posé) — sinon il n'y a pas
     encore d'URL à réutiliser, la question ne se pose pas ;
  5. ni l'une ni l'autre n'est un doublon déjà fusionné (`duplicate_of`).

Usage :
  .venv/bin/python -m scripts.appariement_editions
  .venv/bin/python -m scripts.appariement_editions --limit 5000
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.lieux import plie
from scripts.dedupe import _sig_tokens, _title_years

log = get_logger("appariement_editions")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

GAP_MIN_DAYS = 300
GAP_MAX_DAYS = 430
MIN_TOKENS = 2
MIN_RATIO = 0.6


def titre_sans_annee(title: str) -> frozenset:
    """Tokens significatifs du titre, ANNÉES RETIRÉES (c'est tout l'enjeu : deux
    éditions doivent justement DIFFÉRER par l'année pour être la même chose)."""
    toks = _sig_tokens(title)
    annees = _title_years(title)
    return frozenset(toks - annees)


def _recouvrement(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    commun = a & b
    return len(commun) / min(len(a), len(b))


def _jour(valeur: str | None) -> date | None:
    s = (valeur or "").strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def meme_lieu(a: dict, b: dict) -> bool:
    """True si les deux lieux normalisés coïncident. Un lieu manquant d'un côté ou des
    deux ne DÉPARTAGE PAS (retourne True) : une donnée absente n'est pas un désaccord —
    le critère du titre + de la date reste seul juge dans ce cas."""
    la, lb = plie(a.get("lieu") or ""), plie(b.get("lieu") or "")
    if not la or not lb:
        return True
    return la == lb


def candidate(a: dict, b: dict) -> str | None:
    """Renvoie la RAISON si (a, b) sont proposées comme deux éditions du même
    événement, None sinon. a et b sont interchangeables (comparaison symétrique)."""
    if a["id"] == b["id"] or a.get("duplicate_of") or b.get("duplicate_of"):
        return None
    if not ((a.get("wp_post_id_as") or 0) > 0 or (b.get("wp_post_id_as") or 0) > 0):
        return None

    ta, tb = titre_sans_annee(a.get("title") or ""), titre_sans_annee(b.get("title") or "")
    ratio = _recouvrement(ta, tb)
    if len(ta & tb) < MIN_TOKENS or ratio < MIN_RATIO:
        return None

    if not meme_lieu(a, b):
        return None

    da, db_ = _jour(a.get("date_event_start")), _jour(b.get("date_event_start"))
    if not da or not db_:
        return None
    ecart = abs((da - db_).days)
    if not (GAP_MIN_DAYS <= ecart <= GAP_MAX_DAYS):
        return None

    return (f"titres « {sorted(ta & tb)} » ({ratio:.0%} recouvrement) · "
            f"écart {ecart} j · lieu {plie(a.get('lieu') or '') or '(absent)'}")


def appariements(events: list[dict]) -> list[tuple[dict, dict, str]]:
    """O(n²) sur la base ENTIÈRE serait trop lent : on regroupe d'abord par le premier
    token significatif du titre sans année (un festival garde son premier mot d'une
    édition à l'autre), pour ne comparer qu'à l'intérieur de chaque groupe."""
    groupes: dict[str, list[dict]] = {}
    for ev in events:
        ta = titre_sans_annee(ev.get("title") or "")
        if not ta:
            continue
        cle = sorted(ta)[0]
        groupes.setdefault(cle, []).append(ev)

    out: list[tuple[dict, dict, str]] = []
    vus: set[frozenset] = set()
    for grp in groupes.values():
        if len(grp) < 2:
            continue
        for i, a in enumerate(grp):
            for b in grp[i + 1:]:
                paire = frozenset((a["id"], b["id"]))
                if paire in vus:
                    continue
                raison = candidate(a, b)
                if raison:
                    vus.add(paire)
                    out.append((a, b, raison))
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Audit (lecture seule) : fiches candidates à l'édition suivante d'une fiche publiée.")
    p.add_argument("--limit", type=int, default=3000, help="Nombre max de fiches examinées.")
    args = p.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, lieu, ville, date_event_start, wp_post_id_as, duplicate_of "
        "FROM events_raw WHERE duplicate_of IS NULL AND title IS NOT NULL "
        "ORDER BY id DESC LIMIT ?", (args.limit,)).fetchall()]
    conn.close()

    paires = appariements(rows)
    print(f"\n{'='*72}\nAPPARIEMENT ÉDITIONS — audit lecture seule ({len(rows)} fiche(s) examinées)")
    print(f"{len(paires)} paire(s) candidate(s)\n")
    for a, b, raison in paires:
        pub_a = f"WP#{a['wp_post_id_as']}" if a.get("wp_post_id_as") else "—"
        pub_b = f"WP#{b['wp_post_id_as']}" if b.get("wp_post_id_as") else "—"
        print(f"  [{a['id']:>5} {pub_a:>7}] {(a['title'] or '')[:55]:<55} · {a.get('date_event_start') or '?'}")
        print(f"  [{b['id']:>5} {pub_b:>7}] {(b['title'] or '')[:55]:<55} · {b.get('date_event_start') or '?'}")
        print(f"    → {raison}\n")
    if not paires:
        print("Aucune paire candidate sur ce périmètre.")
    print(f"{'='*72}")
    print("Lecture seule : rien n'a été modifié. Chaque paire est à valider à l'œil "
          "avant qu'un mécanisme automatique n'existe.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
