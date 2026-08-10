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
  3. CELLES OÙ UN CRON A DÉJÀ CHERCHÉ, ET ÉCHOUÉ (venue_source='llm_none', verdict de
     date posé…). Elles ne sont PAS bloquées — dates.py et venues.py les re-tentent
     d'eux-mêmes après leur délai de carence, rouvreur ajouté après l'incident des 823
     fiches endormies. Le problème est l'inverse : l'appel se repaie tous les sept jours
     pour aboutir au même échec. Une matière qui ne contient pas la date ne la contiendra
     pas davantage la semaine prochaine.

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

    # ── 3. Celles où un cron a déjà tranché — et ce que ça coûte ────────────────
    #
    # ⚠️ CORRIGÉ le 2026-08-11, le jour même de l'écriture : la première version titrait
    # « fiches qu'AUCUN cron ne reprendra tout seul » et conseillait `--retry`. C'était
    # FAUX. dates.py comme venues.py re-tentent d'eux-mêmes après leur délai de carence
    # (DATE_COOLDOWN_DAYS / VENUE_COOLDOWN_DAYS, 7 jours par défaut) — ce rouvreur
    # automatique a justement été ajouté après l'incident des 823 fiches endormies dans
    # venue_source='llm_none'. Annoncer un cul-de-sac là où il n'y en a plus aurait fait
    # taper une commande inutile, et surtout masqué le vrai problème, qui est l'inverse :
    # ces fiches sont re-tentées indéfiniment et échouent à chaque fois. Ce n'est pas une
    # file bloquée, c'est une dépense qui se répète sans jamais aboutir.
    verdicts = defaultdict(list)
    for e, manq in incomplets:
        if ("lieu" in manq or "ville" in manq) and (e.get("venue_source") or "") == "llm_none":
            verdicts["lieu — venues.py a cherché et n'a rien trouvé"].append(e["id"])
        if "date_event_start" in manq and (e.get("date_source") or ""):
            verdicts["date — dates.py a cherché et n'a rien trouvé"].append(e["id"])
        if (e.get("enrich_status") or "") in ("error", "api_error"):
            verdicts[f"enrichissement en échec ({e.get('enrich_status')})"].append(e["id"])
    if verdicts:
        print("═══ Fiches où un cron a déjà cherché… et échoué ═══\n")
        print("Elles sont re-tentées toutes seules après le délai de carence (7 jours par")
        print("défaut). Ce n'est donc pas une file bloquée : c'est un appel LLM qui se")
        print("repaie tous les sept jours pour aboutir au même résultat.\n")
        for motif, ids in sorted(verdicts.items(), key=lambda kv: -len(kv[1])):
            apercu = " ".join(str(i) for i in ids[:12])
            suite = " …" if len(ids) > 12 else ""
            print(f"  {len(ids):4} — {motif}\n         {apercu}{suite}")
        print()
    else:
        print("Aucune fiche n'a encore reçu de verdict de cron : tout ce qui manque est "
              "simplement en attente du prochain passage.\n")

    # ── Détail à la demande ─────────────────────────────────────────────────────
    if args.detail:
        cible = args.detail if args.detail in dict(comp.MANDATORY) else {
            "date": "date_event_start", "image": "url_image", "categorie": "llm_categorie",
        }.get(args.detail, args.detail)
        sel = [e for e, m in incomplets if cible in m][:args.limite]
        print(f"═══ {len(sel)} fiche(s) à qui manque « {cible} » ═══\n")
        # url_source affichée : c'est elle qui décide si la réparation est POSSIBLE. Une
        # fiche née d'une newsletter dont le lien pointe sur la page de l'événement peut
        # être datée en allant la lire ; une fiche dont le lien pointe sur la newsletter
        # elle-même (ou sur rien) ne le sera jamais, et la re-tenter chaque semaine ne
        # fera que repayer le même échec.
        for e in sel:
            print(f"  [{e['id']:>5}] {(e.get('title') or '')[:52]:52} · "
                  f"{(e.get('source_name') or '?')[:20]:20} · "
                  f"{(e.get('url_source') or '—')[:46]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
