#!/usr/bin/env python3
"""Corrige, sur le STOCK déjà publié, les titres d'article restés dans une langue
différente de leur corps — le même bug que `scripts.enrich` corrige désormais À LA
RÉDACTION (voir `titre_corps_langue_desaccord`), mais qui a déjà produit des fiches en
ligne AVANT ce correctif.

INCIDENT RÉEL, 2026-09-04 : WP#7472 « Regine in Scena. L'arte del costume italiano tra
cinema e teatro » — corps français correct, titre resté italien.
`scripts.audit_titre_corps_langue --tout` en a trouvé 29 en production, TOUTES dans le
même sens (titre IT, corps FR) : `scripts.enrich` écrit toujours le corps dans la
langue voulue par défaut, mais n'avait jamais retraduit le titre qui l'accompagne.

CE SCRIPT NE FAIT QU'UNE CHOSE : retraduire le TITRE de l'article pour qu'il rejoigne
la langue de son propre CORPS (déjà bon, jamais touché). Aucun fait n'est modifié,
aucune description, aucun corps.

Périmètre : les mêmes fiches que `scripts.audit_titre_corps_langue` désignerait — on
réutilise directement `titre_corps_langue_desaccord` (scripts.enrich) sur l'article
DÉJÀ enrichi, pas une nouvelle heuristique. « Encore devant nous » par défaut (règle 5) ;
`--tout` pour élargir au passé (rarement utile, gardé pour audit).

SÛR : dry-run par défaut (--execute pour agir, CLAUDE.md règle 4). Persiste
`enrich_data`/`article_title`/`article_md` PUIS re-pousse sur WordPress via
`publisher_as.publish_to_as` (texte seul, `skip_media=True` — même précaution que
`scripts.conform_articles`, pour ne pas marteler la médiathèque pour un simple titre).

Usage (VPS) :
    .venv/bin/python -m scripts.fix_titre_corps_langue                # aperçu
    .venv/bin/python -m scripts.fix_titre_corps_langue --execute --cap 10
    .venv/bin/python -m scripts.fix_titre_corps_langue 3946 --execute # une fiche précise
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.voix import voix_block
from scripts.audit_substance_published import devant_nous
from scripts.enrich import build_article_md, titre_corps_langue_desaccord
from scripts.publisher_as import publish_to_as, wp_site_joignable
from scripts.translate_events import translate_title_desc

log = get_logger("fix-titre-corps-langue")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _select(conn: sqlite3.Connection, ids: list[int], tout: bool) -> list[dict]:
    if ids:
        qm = ",".join("?" * len(ids))
        rows = conn.execute(
            f"SELECT * FROM events_raw WHERE id IN ({qm})", ids).fetchall()
        return [dict(r) for r in rows]
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL AND COALESCE(enrich_data,'') <> ''")]
    auj = date.today().isoformat()
    return [r for r in rows if tout or devant_nous(r, auj)]


def _article_de(ev: dict) -> dict:
    try:
        return (json.loads(ev.get("enrich_data") or "") or {}).get("article") or {}
    except (ValueError, TypeError):
        return {}


def main(argv: list[str]) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Retraduit un titre d'article resté dans une autre langue que son corps.")
    parser.add_argument("ids", nargs="*", type=int)
    parser.add_argument("--execute", action="store_true", help="Agir (sinon DRY-RUN).")
    parser.add_argument("--cap", type=int, default=40, help="Nb max de fiches traitées.")
    parser.add_argument("--tout", action="store_true",
                        help="Inclure le passé (par défaut : encore devant nous, règle 5).")
    args = parser.parse_args(argv)

    if not DB_PATH.exists():
        log.error("Base introuvable : %s (lancer ce script sur le VPS.)", DB_PATH)
        return 1
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY absente.")
        return 1
    if args.execute and not wp_site_joignable():
        log.error("Site injoignable depuis cette machine — AUCUNE écriture tentée. "
                  "Rien n'est marqué : relancer plus tard reprendra les mêmes fiches.")
        return 1

    from utils import settings as pipeline_settings
    model = os.getenv("ANTHROPIC_MODEL_TRANSLATE") or pipeline_settings.model()
    client = anthropic.Anthropic(api_key=api_key, timeout=120.0)
    voix = voix_block()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    events = _select(conn, args.ids, args.tout)[:args.cap]
    log.info("%d fiche(s) à examiner (%s).", len(events),
             "EXÉCUTION" if args.execute else "DRY-RUN")

    candidats = corriges = pushed = echecs = 0
    for ev in events:
        art = _article_de(ev)
        if not art:
            continue
        desaccord = titre_corps_langue_desaccord(art)
        if not desaccord:
            continue
        candidats += 1
        lang_titre, lang_corps, corps_ref = desaccord
        log.info("[%s] titre en %s, corps en %s : « %s »",
                 ev["id"], lang_titre, lang_corps, art["titre"][:60])
        if not args.execute:
            continue
        correction = translate_title_desc(client, model, art["titre"], corps_ref,
                                          lang_corps, voix=voix)
        if not correction or not correction.get("title"):
            echecs += 1
            log.warning("[%s] retraduction ÉCHOUÉE — titre laissé tel quel, "
                        "resélectionné au prochain passage (translated_at non posé).",
                        ev["id"])
            continue
        data = json.loads(ev["enrich_data"])
        data["article"]["titre"] = correction["title"]
        title, md = build_article_md(data)
        conn.execute(
            "UPDATE events_raw SET enrich_data=?, article_title=?, article_md=? WHERE id=?",
            (json.dumps(data, ensure_ascii=False), title, md, ev["id"]))
        conn.commit()
        corriges += 1
        log.info("[%s] titre corrigé en %s : « %s »", ev["id"], lang_corps, title[:60])
        ev.update({"enrich_data": json.dumps(data, ensure_ascii=False),
                   "article_title": title, "article_md": md})
        # skip_media=True : passe de TEXTE seul (même précaution que conform_articles) —
        # on ne retéléverse aucune image pour un simple correctif de titre.
        post_id, _perma, _img = publish_to_as(ev, skip_media=True)
        if post_id:
            pushed += 1
            log.info("[%s] re-poussé sur WordPress (post %s).", ev["id"], post_id)
        else:
            log.warning("[%s] re-push WordPress ÉCHOUÉ — titre corrigé en base mais PAS "
                        "encore visible en ligne (règle 1 : la base ne prouve rien sur "
                        "le site). Relancer ce script reprendra cette fiche.", ev["id"])
    conn.close()

    tail = "" if args.execute else " (dry-run : rien écrit, rien poussé)"
    log.info("=== %d candidat(s), %d corrigé(s), %d repoussé(s) sur WordPress, "
             "%d échec(s) de retraduction, sur %d fiche(s) examinée(s)%s ===",
             candidats, corriges, pushed, echecs, len(events), tail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
