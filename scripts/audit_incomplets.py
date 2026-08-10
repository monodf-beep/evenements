#!/usr/bin/env python3
"""Pourquoi reste-t-il autant d'événements incomplets — champ par champ, source par source.

Franck, 2026-08-11 : « on a trop d'événements incomplets alors qu'on va maintenant
chercher des sources officielles ». La question suppose que les sources officielles
devraient suffire. Ce rapport dit si c'est vrai, et surtout OÙ ça coince.

Le back-office affiche un compteur unique (« À compléter : 96 »). Un compteur ne dit pas
quoi réparer : il manque une date ? une image ? le lieu ? Et les trois ne se réparent pas
du tout de la même façon — la date et le lieu ont chacun leur cron (dates.py, venues.py),
l'image en a un autre (visuals.py), la catégorie vient de l'évaluateur. Un chiffre unique
mélange donc quatre chaînes de réparation distinctes, dont certaines sont peut-être à
l'arrêt sans que personne ne le voie.

Trois angles :
  1. PAR CHAMP MANQUANT — quelle chaîne de réparation est en panne ;
  2. PAR SOURCE — quelles sources livrent de la matière inexploitable (c'est la réponse
     directe à « on va pourtant chercher des sources officielles ») ;
  3. LES BLOQUÉES — fiches déjà passées par un cron qui a échoué et posé son verdict
     (venue_source='llm_none', date_source vide après tentative…). Ce sont elles qui
     dorment : le cron ne les reprendra pas, il croit avoir fait son travail.

RÈGLE 5 : uniquement les événements À VENIR, EN COURS, RÉCURRENTS ou SANS DATE. Une fiche
incomplète dont l'événement a eu lieu ne sera jamais réparée ni republiée — la compter
fabriquerait du travail au lieu d'en désigner.

LECTURE SEULE : aucune écriture, ni en base ni sur le site.

Exemples :
  .venv/bin/python -m scripts.audit_incomplets
  .venv/bin/python -m scripts.audit_incomplets --detail date     # les 30 premières fiches
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import completeness as comp  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Qui répare quoi — pour que le tableau se lise sans connaître le pipeline.
REPARATEUR = {
    "date_event_start": "scripts/dates.py (8h25 et 8h45)",
    "lieu": "scripts/venues.py (8h50)",
    "ville": "scripts/venues.py (8h50)",
    "territoire": "déduit de la source (config/sources.txt)",
    "llm_categorie": "scripts/evaluator.py (9h00)",
    "url_image": "scripts/visuals.py (dans daily_batch, 9h30)",
}


def _manquants(ev: dict) -> list[str]:
    """Champs obligatoires vides, avec les mêmes dérogations que utils.completeness :
    un récurrent n'a pas besoin de date, un événement multi-lieux n'a ni lieu ni ville."""
    recurring = bool(ev.get("recurring"))
    multi = bool(ev.get("multi_lieux"))
    out = []
    for cle, _lib in comp.MANDATORY:
        if str(ev.get(cle) or "").strip():
            continue
        if recurring and cle == "date_event_start":
            continue
        if multi and cle in ("lieu", "ville"):
            continue
        out.append(cle)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Où coincent les fiches incomplètes (lecture seule).")
    p.add_argument("--detail", default="", help="Lister les fiches à qui manque CE champ.")
    p.add_argument("--limite", type=int, default=30, help="Nb de fiches listées (défaut 30).")
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    today = date.today().isoformat()
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE statut IN ('evaluated','published_cs','published_sub') "
        "AND duplicate_of IS NULL AND COALESCE(translation_of,0)=0 "
        # Règle 5 : à venir, en cours, récurrent, ou sans date (donnée manquante).
        "AND (COALESCE(date_event_end, date_event_start, '')='' "
        "     OR COALESCE(date_event_end, date_event_start) >= ?)", (today,))]
    conn.close()

    incomplets = [(e, _manquants(e)) for e in rows]
    incomplets = [(e, m) for e, m in incomplets if m]
    if not incomplets:
        print("Aucune fiche incomplète encore devant nous. 🎉")
        return 0

    print(f"═══ {len(incomplets)} fiche(s) incomplète(s) encore devant nous "
          f"(sur {len(rows)} retenues) ═══\n")

    # ── 1. Par champ manquant ───────────────────────────────────────────────────
    par_champ = Counter()
    for _e, manq in incomplets:
        par_champ.update(manq)
    print(f"{'champ manquant':22} {'fiches':>7}   qui est censé le remplir")
    print("─" * 88)
    for cle, _lib in comp.MANDATORY:
        n = par_champ.get(cle, 0)
        if n:
            print(f"{cle:22} {n:7}   {REPARATEUR.get(cle, '?')}")
    print()

    # ── 2. Par source ───────────────────────────────────────────────────────────
    # Une source qui livre 30 fiches dont 28 incomplètes n'est pas une bonne source,
    # même officielle : elle coûte du scraping, du stockage et des appels LLM pour rien.
    total_src, incomp_src = Counter(), Counter()
    for e in rows:
        total_src[(e.get("source_name") or "?")[:38]] += 1
    for e, _m in incomplets:
        incomp_src[(e.get("source_name") or "?")[:38]] += 1
    print(f"{'source':40} {'incomplètes':>12} {'/ total':>8} {'part':>6}")
    print("─" * 88)
    for src, n in incomp_src.most_common(15):
        tot = total_src[src] or 1
        print(f"{src:40} {n:12} {tot:8} {100*n/tot:5.0f}%")
    print()

    # ── 3. Les bloquées : un cron a déjà tranché et ne repassera pas ─────────────
    # C'est la vraie question de la règle 3 : qui les rouvre ? Un compteur global les
    # noie avec les fiches simplement pas encore traitées, qui, elles, partiront demain.
    bloquees = defaultdict(list)
    for e, manq in incomplets:
        if "lieu" in manq or "ville" in manq:
            if (e.get("venue_source") or "") == "llm_none":
                bloquees["lieu introuvable, venues.py a déjà renoncé "
                         "(--retry pour le rouvrir)"].append(e["id"])
        if "date_event_start" in manq and (e.get("date_source") or ""):
            bloquees["date introuvable, dates.py a déjà tranché "
                     "(--retry pour le rouvrir)"].append(e["id"])
        if (e.get("enrich_status") or "") in ("error", "api_error"):
            bloquees[f"enrichissement en échec ({e.get('enrich_status')})"].append(e["id"])
    if bloquees:
        print("═══ Fiches qu'AUCUN cron ne reprendra tout seul ═══\n")
        for motif, ids in sorted(bloquees.items(), key=lambda kv: -len(kv[1])):
            apercu = " ".join(str(i) for i in ids[:12])
            suite = " …" if len(ids) > 12 else ""
            print(f"  {len(ids):4} — {motif}\n         {apercu}{suite}")
        print()
    else:
        print("Aucune fiche garée par un verdict de cron : tout ce qui manque est "
              "simplement en attente du prochain passage.\n")

    # ── Détail à la demande ─────────────────────────────────────────────────────
    if args.detail:
        cible = args.detail if args.detail in dict(comp.MANDATORY) else {
            "date": "date_event_start", "image": "url_image", "categorie": "llm_categorie",
        }.get(args.detail, args.detail)
        sel = [e for e, m in incomplets if cible in m][:args.limite]
        print(f"═══ {len(sel)} fiche(s) à qui manque « {cible} » ═══\n")
        for e in sel:
            print(f"  [{e['id']:>5}] {(e.get('title') or '')[:58]:58} · "
                  f"{(e.get('source_name') or '?')[:24]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
