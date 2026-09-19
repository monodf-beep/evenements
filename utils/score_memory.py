#!/usr/bin/env python3
"""Mémoire d'apprentissage des scores — Franck corrige, l'évaluateur apprend.

Chaque fois que Franck ajuste le score d'un événement dans le backoffice, on
enregistre la correction ici (append-only, data/score_feedback.jsonl) AVEC les
traits de l'événement (territoire, catégorie, lieu, titre). L'évaluateur
(scripts/evaluator.py) relit ces corrections récentes et les injecte comme
EXEMPLES DE CALIBRAGE dans son prompt → au fil du temps, il note « comme Franck ».

Format d'une ligne (JSON) :
  {"ts","event_id","title","territoire","categorie","lieu","ville",
   "old_score","new_score","note"}
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEEDBACK_FILE = ROOT / "data" / "score_feedback.jsonl"


def record(event: dict, old_score, new_score, note: str = "") -> None:
    """Ajoute une correction de score à la mémoire (jamais bloquant)."""
    try:
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts":         __import__("datetime").datetime.now().isoformat(timespec="seconds"),
            "event_id":   event.get("id"),
            "title":      (event.get("article_title") or event.get("title") or "")[:160],
            "territoire": event.get("territoire") or "",
            "categorie":  event.get("llm_categorie") or "",
            "lieu":       event.get("lieu") or "",
            "ville":      event.get("ville") or "",
            "old_score":  old_score,
            "new_score":  new_score,
            "note":       (note or "")[:200],
        }
        with FEEDBACK_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # la mémoire ne doit jamais casser une action utilisateur


def load_recent(limit: int = 40) -> list[dict]:
    """Dernières corrections (les plus récentes en dernier). [] si aucune."""
    if not FEEDBACK_FILE.exists():
        return []
    out: list[dict] = []
    try:
        for line in FEEDBACK_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except (ValueError, TypeError):
                continue
    except OSError:
        return []
    return out[-limit:]


def calibration_block(limit: int = 30) -> str:
    """Texte prêt à injecter dans le prompt de l'évaluateur : les ajustements de
    Franck, pour aligner le scoring sur son appréciation. '' si aucune correction."""
    rows = load_recent(limit)
    if not rows:
        return ""
    lines = []
    for r in rows:
        if r.get("new_score") is None:
            continue
        trait = " · ".join(x for x in (r.get("categorie"), r.get("territoire"),
                                       r.get("lieu")) if x)
        lines.append(f"- « {r.get('title','')[:90]} » ({trait}) → Franck a mis "
                     f"{r.get('new_score')}/10"
                     + (f" (l'IA proposait {r.get('old_score')})"
                        if r.get('old_score') is not None else ""))
    if not lines:
        return ""
    return ("\n\nCALIBRAGE — ajustements de score déjà faits par Franck (aligne-toi "
            "sur son appréciation ; ce sont des exemples de SON goût éditorial, pas "
            "des règles absolues) :\n" + "\n".join(lines))
