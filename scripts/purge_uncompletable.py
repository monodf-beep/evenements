#!/usr/bin/env python3
"""Écarte le BRUIT STRUCTUREL de « À compléter » : les incomplétables par nature.

Le diagnostic (scripts.diagnose_backlog) le montre : une grande part des incomplets
sont des événements RADAR (presse — détection seule, charte §8) ou SANS PAGE
exploitable (Google News, ou aucune URL) auxquels il MANQUE la date ou le lieu. Il
n'existe AUCUNE page officielle à lire → ils ne seront jamais complétés
automatiquement. On les passe en 'rejected' (réversible) pour qu'ils quittent la file.

⚠️ Les NEWSLETTERS (« gmail:… ») ne sont PAS visées ici : elles ont bien une page
d'article — on la rattrape d'abord avec scripts.gmail_relink. Ne les écarter à la
main que si le rattrapage n'a rien donné.

On ne touche PAS les événements qui ont une vraie page officielle (le « gisement »
récupérable) ni ceux déjà complets.

FUSIONNÉ avec `discard_uncompletable` le 2026-09-04 (audit du 31/08, §2.1 — décision
de Franck : « fais ce qui te semble le plus adéquat »). Les deux scripts tournaient
l'un après l'autre dans le hebdo du dimanche avec la MÊME requête de sélection et le
MÊME prédicat radar ; leur seule branche vraiment distincte était « année révolue
dans le titre » (`discard_uncompletable --past`), reprise ci-dessous. Sa branche
« sans page » était déjà entièrement absorbée par celle-ci — mesuré en production :
`discard_uncompletable --no-page` rendait 0, purge_uncompletable étant lancé avant
dans la même chaîne. `discard_uncompletable.py` reste dans le dépôt (utilisable à la
main), mais n'est plus appelé par `weekly_audits.py`.

Exemples :
  .venv/bin/python3 -m scripts.purge_uncompletable                 # dry-run
  .venv/bin/python3 -m scripts.purge_uncompletable --execute
  .venv/bin/python3 -m scripts.purge_uncompletable --radar-only    # seulement le radar
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import completeness as comp

log = get_logger("purge_uncompletable")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _is_radar(e: dict) -> bool:
    return e.get("source_type") == "radar" or "(radar)" in (e.get("source_name") or "")


def _no_page(e: dict) -> bool:
    """Vraiment SANS page exploitable. ⚠️ Les newsletters (« gmail:… ») en sont
    EXCLUES : elles ont bien une page d'article — on la rattrape avec
    scripts.gmail_relink AVANT d'envisager de les écarter. Ici, seuls les agrégateurs
    à mur de redirection (Google News) et l'absence totale d'URL comptent."""
    u = e.get("url_source") or ""
    return (not u) or "news.google.com" in u


def _is_newsletter(e: dict) -> bool:
    return (e.get("url_source") or "").startswith("gmail:")


def _is_past_year(e: dict) -> bool:
    """Une année RÉVOLUE apparaît dans le titre (ou la date brute) — signe d'une
    fiche recopiée d'une édition passée d'un événement récurrent, jamais mise à jour.
    Repris de `discard_uncompletable.is_past` lors de la fusion du 04/09 : ne
    s'applique qu'aux fiches SANS DATE (une vraie date passée est déjà le travail de
    `purge_past`, pas celui-ci)."""
    year = date.today().year
    past_years = "|".join(str(y) for y in range(2015, year))
    blob = f"{e.get('title', '')} {e.get('date_start', '')}"
    return bool(re.search(rf"(?<!\d)({past_years})(?!\d)", blob))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Écarte le bruit incomplétable (radar / sans page / année révolue).")
    p.add_argument("--execute", action="store_true", help="Agir (sinon DRY-RUN).")
    p.add_argument("--radar-only", action="store_true",
                   help="Ne viser que le radar presse (laisser sans-page et année révolue).")
    args = p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE statut IN ('evaluated','published_cs','published_sub') "
        "AND duplicate_of IS NULL "
        "AND (COALESCE(date_event_end, date_event_start, '')='' "
        "     OR COALESCE(date_event_end, date_event_start) >= ?)", (today,)).fetchall()]

    targets = []
    for e in rows:
        if comp.is_complete(e):
            continue
        # Incomplétable = source sans page officielle ET il manque un champ STRUCTUREL
        # (date ou lieu) qu'aucune page ne pourra fournir.
        radar, nopage = _is_radar(e), _no_page(e)
        source_bad = radar if args.radar_only else (radar or nopage)
        missing = {lbl for _k, lbl in comp.missing_fields(e)}
        if source_bad and (missing & {"Date", "Lieu"}):
            reason = "radar (presse)" if radar else "sans page (Google News)"
            targets.append((e, reason))
        elif (not args.radar_only and "Date" in missing
              and comp._empty(e.get("date_event_start")) and not _is_newsletter(e)
              and _is_past_year(e)):
            # Repris de discard_uncompletable --past (fusion du 04/09) : aucune date,
            # une année révolue dans le titre — jamais une newsletter (rattrapable
            # via gmail_relink), jamais couvert par la branche radar/sans-page ci-dessus.
            targets.append((e, "année révolue dans le titre"))

    mode = "EXÉCUTION" if args.execute else "DRY-RUN (rien ne bouge)"
    scope = "radar uniquement" if args.radar_only else "radar + sans-page + année révolue"
    print(f"\nBruit incomplétable à écarter ({scope}) — {mode} · {len(targets)}\n")
    for e, why in targets[:60]:
        print(f"  [{e['id']}] {(e.get('title') or '')[:58]:58} · {why}")
    if len(targets) > 60:
        print(f"  … et {len(targets) - 60} autres.")
    if not targets:
        print("Rien à écarter. 🎉")
        conn.close()
        return 0
    if not args.execute:
        print(f"\nDRY-RUN : {len(targets)} seraient écartés. Relance avec --execute.")
        conn.close()
        return 0

    # Motif écrit sur la fiche propre à CHAQUE raison — pas un texte générique unique
    # (le premier écrivait « source sans page officielle » même sur le cas « année
    # révolue », qui n'a rien à voir avec la page de la source).
    justifs = {
        "radar (presse)": "Incomplétable (source radar, presse — détection seule) — écarté.",
        "sans page (Google News)": "Incomplétable (source sans page officielle) — écarté.",
        "année révolue dans le titre":
            "Incomplétable (année révolue dans le titre, sans date) — écarté.",
    }
    conn.executemany(
        "UPDATE events_raw SET statut='rejected', llm_justification=? WHERE id=?",
        [(justifs[why], e["id"]) for e, why in targets])
    conn.commit()
    conn.close()
    print(f"\n=== {len(targets)} événement(s) incomplétable(s) écarté(s) (réversible). ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
