#!/usr/bin/env python3
"""POURQUOI cette fiche publiée n'a-t-elle pas de jumelle traduite ?

D'OÙ ÇA VIENT — 2026-09-15. Franck, deux messages : « encore des événements sans
traduction ! » (capture de WP#7522, « Riccardo Benassi à la Fondazione Merz », publié le
14/08, case Traductions vide), puis « ça doit suivre un processus, regarde dans nos
automatisations ».

Mesuré le jour même sur WordPress, et c'est bien un processus qui fuit, pas un cas :

    202 fiches françaises publiées, 85 avec jumelle italienne, 117 SANS
    dont 63 encore devant nous (à venir ou en cours) — les 54 autres sont mortes
    côté italien : 119 publiées, 25 brouillons, 24 à la corbeille

Or le cron traduit jusqu'à 25 fiches par jour (crontab.txt, 10h45). Une file de 63 à
25/jour se vide en trois jours. Elle ne se vide pas : quelque chose ÉCARTE ces fiches
sans que rien ne le dise. Le journal de traduction, lui, annonce « N candidat(s) » —
un compteur qui ne dit pas ce qu'il N'A PAS compté (règle 6).

CE SCRIPT NE RÉPARE RIEN. Il répond à une seule question, fiche par fiche : quel
portillon l'écarte, et qui la rouvrira. Chaque famille sort avec SA commande de reprise.

PÉRIMÈTRE (règle 5) : par défaut, uniquement les fiches à venir, en cours, ou sans date
(une date manquante n'est pas un événement terminé). `--include-past` pour tout voir —
mais réparer une fiche dont l'événement a eu lieu ne sert personne.

Zéro coût API LLM. `--wp` interroge WordPress par NUMÉRO pour chaque jumelle (règle 1 :
un identifiant en base ne prouve rien sur le site ; règle 2 : une liste ne prouve jamais
une absence) — un appel par jumelle, quelques dizaines de secondes.

Usage (VPS) :
    .venv/bin/python -m scripts.audit_traduction_manquante
    .venv/bin/python -m scripts.audit_traduction_manquante --wp        # + état réel des jumelles
    .venv/bin/python -m scripts.audit_traduction_manquante --limite 30 # plus d'exemples nommés
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger            # noqa: E402
from utils.coherence import incoherence_description  # noqa: E402
from utils.completeness import is_recurring     # noqa: E402
from scripts.scraper_events import init_db      # noqa: E402
from scripts.translate_events import MAX_REFUS  # noqa: E402

log = get_logger("audit-traduction-manquante")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Le seuil du CRON, pas celui du script. `translate_events` a `--min-score 6` par défaut,
# mais crontab.txt lance `--min-score 1` : c'est cette valeur-là qui décide en production,
# et c'est donc elle que l'audit doit refléter. Deux compteurs qui portent le même nom et
# comptent deux choses se contrediront un jour (règle 6) — status_report.py compte encore
# « à traduire » avec un seuil de 6 et AUCUN filtre de date : il annonce donc autre chose
# que ce que la file fait réellement.
SEUIL_CRON = 1
CAP_CRON = 25

# Les familles, dans l'ordre où elles sont testées. Chaque fiche tombe dans UNE seule —
# sinon les nombres s'additionnent en double et plus personne ne les croit.
FAMILLES = [
    ("jumelle_disparue",
     "traduite un jour, jumelle introuvable en base — CUL-DE-SAC",
     "La fiche porte `translated_at`, donc la file l'exclut DÉFINITIVEMENT, alors que sa "
     "jumelle n'existe plus nulle part. Rien ne la rouvrait avant le 15/09 ; "
     "`_rearme_traductions_orphelines` (translate_events.py) le fait désormais tout seul "
     "au run suivant. Si cette ligne n'est pas vide, c'est que le cron n'est pas repassé."),
    ("jumelle_jamais_publiee",
     "jumelle créée en base mais jamais mise en ligne",
     "La traduction existe, la publication WordPress a échoué. Reprise : "
     "`.venv/bin/python -m scripts.publish_batch_as --apply --ids <ids jumelles>`"),
    ("jumelle_hors_ligne",
     "jumelle en ligne à un moment, plus publique aujourd'hui (corbeille ou supprimée)",
     "Vérifié par NUMÉRO sur l'API REST, pas sur une liste. Une jumelle à la corbeille se "
     "restaure d'un clic ; une jumelle supprimée demande une republication."),
    ("garee",
     f"garée après {MAX_REFUS} refus sur une matière INCHANGÉE",
     "Elle ne consomme plus ni créneau ni appel API, et repart d'elle-même dès que sa "
     "matière change (titre corrigé, description réparée, article ré-enrichi). Pour la "
     "débloquer : réparer la matière, pas relancer la traduction."),
    ("description_incoherente",
     "description incohérente avec la fiche — écartée AVANT le plafond",
     "Reprise : `.venv/bin/python -m scripts.repair_polluted_descriptions --apply`, puis "
     "la traduction la reprend d'elle-même."),
    ("score_insuffisant",
     f"score < {SEUIL_CRON} (le seuil du cron)",
     "Choix éditorial assumé : ces fiches ne sont pas jugées dignes d'une version "
     "italienne. Rien à faire, sauf à relever le score à la main."),
    ("en_file",
     "candidate en règle — elle attend son tour",
     f"Le cron en traduit {CAP_CRON} par jour. Si cette ligne ne diminue pas d'un jour à "
     "l'autre, c'est le cron qui ne passe pas : lire logs/translate.log."),
]


def _a_venir(ev: dict, aujourd_hui: str) -> bool:
    """Règle 5. Une fiche SANS date n'est pas du passé (donnée manquante), et une
    récurrente n'a pas de date unique — les deux restent devant nous."""
    if is_recurring(ev):
        return True
    fin = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()
    return (not fin) or fin >= aujourd_hui


def classe(ev: dict, jumelles_par_origine: dict, marqueurs: set, etat_wp) -> tuple[str, str]:
    """Rend (famille, précision). Fonction pure hors `etat_wp` (qui peut être None)."""
    jum = jumelles_par_origine.get(ev["id"])
    if ev.get("translated_at") and not jum:
        # Le marqueur `translated:<id>:<lang>` survit au déliage (colonne UNIQUE) : s'il
        # est là, la jumelle existe et a seulement été DÉLIÉE — ce n'est pas un cul-de-sac,
        # et surtout il ne faut PAS rouvrir, ça fabriquerait une troisième fiche.
        if any(m.startswith(f"translated:{ev['id']}:") for m in marqueurs):
            return "jumelle_jamais_publiee", "jumelle déliée (marqueur url_source présent)"
        return "jumelle_disparue", f"translated_at={ev['translated_at']}"
    if jum:
        if not (jum.get("wp_post_id_as") or 0):
            return "jumelle_jamais_publiee", f"jumelle locale {jum['id']}, aucun wp_post_id_as"
        if etat_wp is not None:
            etat = etat_wp(int(jum["wp_post_id_as"]))
            if etat in ("non_public", "inexistant"):
                return "jumelle_hors_ligne", f"WP#{jum['wp_post_id_as']} : {etat}"
    if (ev.get("traduction_tentatives") or 0) >= MAX_REFUS:
        return "garee", f"{ev['traduction_tentatives']} refus"
    motif = incoherence_description(ev, bloquant=True)
    if motif:
        return "description_incoherente", motif[:60]
    if (ev.get("user_score") if ev.get("user_score") is not None
            else (ev.get("llm_score") or 0)) < SEUIL_CRON:
        return "score_insuffisant", f"score={ev.get('user_score') or ev.get('llm_score') or 0}"
    return "en_file", ""


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--include-past", action="store_true",
                   help="Inclut les événements terminés (règle 5 : ils ne servent personne).")
    p.add_argument("--wp", action="store_true",
                   help="Interroge WordPress par numéro pour chaque jumelle (état réel).")
    p.add_argument("--limite", type=int, default=8, help="Exemples nommés par famille.")
    args = p.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # Les originaux PUBLIÉS : c'est le seul périmètre où l'absence de jumelle se voit du
    # public. Une fiche non publiée n'a pas à être traduite, la traduction vient après.
    originaux = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0)>0 AND duplicate_of IS NULL "
        "AND COALESCE(translation_of,0)=0 "
        "AND COALESCE(url_source,'') NOT LIKE 'translated:%'").fetchall()]
    jumelles_par_origine = {}
    for r in conn.execute("SELECT * FROM events_raw WHERE COALESCE(translation_of,0)!=0"):
        jumelles_par_origine.setdefault(r["translation_of"], dict(r))
    marqueurs = {r[0] for r in conn.execute(
        "SELECT url_source FROM events_raw WHERE COALESCE(url_source,'') LIKE 'translated:%'")}

    aujourd_hui = date.today().isoformat()
    total_publies = len(originaux)
    if not args.include_past:
        originaux = [e for e in originaux if _a_venir(e, aujourd_hui)]
    perimetre = ("tous les originaux publiés" if args.include_past
                 else "originaux publiés à venir, en cours, récurrents ou sans date")

    etat_wp = None
    if args.wp:
        from scripts.reconcile_wp_deleted import _etat  # même détecteur que la réconciliation
        wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
        if not wp_url:
            log.error("--wp demandé mais WP_AS_URL est vide — j'arrête plutôt que de "
                      "rendre un état inventé.")
            return 2
        cache: dict[int, str] = {}
        def etat_wp(pid: int) -> str:                       # noqa: E306
            if pid not in cache:
                cache[pid] = _etat(wp_url, pid)
            return cache[pid]

    par_famille: dict[str, list] = {}
    avec_jumelle_en_ligne = 0
    for ev in originaux:
        fam, precision = classe(ev, jumelles_par_origine, marqueurs, etat_wp)
        if fam == "en_file" and jumelles_par_origine.get(ev["id"]):
            avec_jumelle_en_ligne += 1                      # jumelle présente ET publiée
            continue
        par_famille.setdefault(fam, []).append((ev, precision))

    print(f"\nPÉRIMÈTRE : {perimetre}")
    print(f"  {total_publies} originaux publiés en base, dont {len(originaux)} dans ce périmètre")
    print(f"  {avec_jumelle_en_ligne} ont déjà leur jumelle publiée")
    manquantes = sum(len(v) for v in par_famille.values())
    print(f"  {manquantes} SANS jumelle en ligne — réparties ci-dessous, une seule famille "
          f"par fiche\n")
    if not args.wp:
        print("  ⚠️  sans --wp, l'état RÉEL des jumelles sur le site n'est pas vérifié : une "
              "jumelle à la corbeille compte ici comme présente (règle 1).\n")

    for cle, titre, quoi_faire in FAMILLES:
        lot = par_famille.get(cle, [])
        print(f"── {len(lot):>3}  {titre}")
        if not lot:
            continue
        print(f"      → {quoi_faire}")
        for ev, precision in lot[:args.limite]:
            nom = (ev.get("article_title") or ev.get("title") or "")[:68]
            print(f"      [{ev['id']}] WP#{ev.get('wp_post_id_as')} {nom}"
                  + (f"  ({precision})" if precision else ""))
        if len(lot) > args.limite:
            # Une liste tronquée annonce son total, sinon elle fabrique de fausses causes.
            print(f"      … et {len(lot) - args.limite} autre(s) — `--limite {len(lot)}` "
                  f"pour les voir toutes")
    print()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
