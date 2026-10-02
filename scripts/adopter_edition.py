#!/usr/bin/env python3
"""ADOPTION D'ÉDITION : la fiche de l'édition N+1 reprend le post WordPress de l'édition N.

D'OÙ ÇA VIENT — décision de Franck (08-09/09, rappelée le 15/09) : « les événements
annuels, il serait bien de les garder d'une année sur l'autre et de les mettre à jour,
pour capitaliser sur les backlinks et le SEO ». Aujourd'hui chaque édition crée une
NOUVELLE fiche, donc un nouveau post, donc une nouvelle URL : la foire de Vicoforte a eu
quatre adresses en un an (docs/ERREURS_2026-09-10_SEO.md, faute 12), et la Search Console
montre que les requêtes qui portent sont justement des éditions annuelles (« la farandole
nice 2026 », docs/AUDIT_SEO_2026-09-08.md).

CE QUE FAIT L'ADOPTION, et rien d'autre :
  1. la NOUVELLE fiche reçoit `wp_post_id_as` et `wp_permalink_as` de l'ancienne — donc
     `publish_batch_as` la publiera comme une MISE À JOUR du post existant (même URL,
     dates et contenu de la nouvelle édition) ;
  2. l'ANCIENNE fiche perd son `wp_post_id_as` (le post ne lui appartient plus — sinon
     deux lignes republieraient le même post à tour de rôle, la collision 2507/3491 →
     WP#2190 déjà vue) et garde la trace dans `edition_suivante` ;
  3. `edition_precedente` / `edition_adoptee_le` sur la nouvelle, pour l'histoire et le
     retour arrière.

Aucun appel à WordPress en ÉCRITURE : l'adoption ne touche que la base. C'est la
republication qui met le post à jour, et c'est un geste séparé, à lancer ensuite.

RETOUR ARRIÈRE : `--defaire NOUVEL_ID` remet les identifiants sur l'ancienne fiche et
efface les trois colonnes. Réversible tant que la nouvelle n'a pas été republiée ; après,
le post porte le contenu de la nouvelle édition — ce qui était le but.

CE QUI EST REFUSÉ, et pourquoi :
  · la nouvelle a DÉJÀ un post → ce n'est pas une adoption, c'est un DOUBLON : deux
    adresses en ligne pour le même événement, qui se REDIRIGE (301, doctrine du 15/09) ;
  · l'ancienne n'a pas de post, ou son post n'est PAS public sur WordPress (règle 1 : on
    interroge l'API REST, jamais la base seule) → rien à adopter ;
  · l'une des deux est un doublon fusionné (`duplicate_of`) ;
  · la nouvelle est déjà PASSÉE (règle 5 : on ne travaille que sur ce qui est devant
    nous) — l'ancienne, elle, est passée par construction ;
  · la paire ne satisfait pas les critères d'`appariement_editions.candidate` (même
    titre sans l'année, même lieu, 10 à 14 mois d'écart) — sauf `--force`, qui est là
    pour l'œil humain qui a lu les deux fiches, pas pour un cron.

DRY-RUN PAR DÉFAUT. Lire chaque paire avant `--apply`, et sauvegarder d'abord :
    .venv/bin/python scripts/backup_db.py

Usage :
  .venv/bin/python -m scripts.adopter_edition --depuis-audit            # dry-run
  .venv/bin/python -m scripts.adopter_edition --paire 2255 8123         # ancienne nouvelle
  .venv/bin/python -m scripts.adopter_edition --paire 2255 8123 --apply
  .venv/bin/python -m scripts.adopter_edition --defaire 8123 --apply
  puis : .venv/bin/python -m scripts.publish_batch_as --ids 8123
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger                      # noqa: E402
from scripts.appariement_editions import candidate, appariements  # noqa: E402

log = get_logger("adopter_edition")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _etat_wp_reel(post_id: int) -> str:
    """'public' | 'non_public' | 'inexistant' | 'indetermine' — la MÊME fonction que
    reconcile_wp_deleted, pour qu'il n'existe qu'une définition de « en ligne »."""
    from scripts.reconcile_wp_deleted import _etat
    wp_url = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
    return _etat(wp_url, int(post_id))


def _devant_nous(ev: dict, today: str) -> bool:
    if ev.get("recurring"):
        return True
    fin = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()[:10]
    return not fin or fin >= today   # sans date = donnée manquante, pas passé


def verifier_paire(ancienne: dict, nouvelle: dict, today: str,
                   etat_wp: Callable[[int], str], force: bool = False) -> list[str]:
    """Liste des REFUS (vide = adoptable). Fonction pure sauf `etat_wp`, injecté pour la
    fixture. Chaque refus dit ce qu'il faudrait pour lever l'objection."""
    refus: list[str] = []
    if ancienne.get("duplicate_of") or nouvelle.get("duplicate_of"):
        refus.append("l'une des deux est un doublon fusionné (duplicate_of)")
    if (nouvelle.get("wp_post_id_as") or 0) > 0:
        refus.append(f"la nouvelle a DÉJÀ un post (WP#{nouvelle['wp_post_id_as']}) : "
                     "c'est un doublon à REDIRIGER en 301, pas une adoption")
    if not (ancienne.get("wp_post_id_as") or 0) > 0:
        refus.append("l'ancienne n'a pas de post WordPress : rien à adopter")
    else:
        etat = etat_wp(int(ancienne["wp_post_id_as"]))
        if etat != "public":
            refus.append(f"le post WP#{ancienne['wp_post_id_as']} de l'ancienne n'est pas "
                         f"public ({etat}) : une URL qu'on ne sert plus ne capitalise rien")
    if not _devant_nous(nouvelle, today):
        refus.append("la nouvelle est déjà passée (règle 5)")
    if nouvelle.get("edition_precedente"):
        refus.append(f"la nouvelle a déjà adopté la fiche {nouvelle['edition_precedente']}")
    if ancienne.get("edition_suivante"):
        refus.append(f"l'ancienne a déjà été adoptée par la fiche {ancienne['edition_suivante']}")
    if not force and not candidate(ancienne, nouvelle):
        refus.append("la paire ne satisfait pas les critères d'appariement "
                     "(titre sans année, lieu, 10-14 mois) — --force si vous avez LU les deux")
    return refus


def adopter(conn: sqlite3.Connection, ancienne: dict, nouvelle: dict) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "UPDATE events_raw SET wp_post_id_as=?, wp_permalink_as=?, edition_precedente=?, "
        "edition_adoptee_le=? WHERE id=?",
        (ancienne["wp_post_id_as"], ancienne.get("wp_permalink_as"), ancienne["id"], now,
         nouvelle["id"]))
    conn.execute(
        "UPDATE events_raw SET wp_post_id_as=NULL, wp_permalink_as=NULL, edition_suivante=? "
        "WHERE id=?", (nouvelle["id"], ancienne["id"]))
    conn.commit()


def defaire(conn: sqlite3.Connection, nouvelle: dict) -> dict | None:
    """Rend le post à l'ancienne fiche. None si la nouvelle n'a rien adopté."""
    old_id = nouvelle.get("edition_precedente")
    if not old_id:
        return None
    ancienne = _row(conn, int(old_id))
    if not ancienne:
        return None
    conn.execute(
        "UPDATE events_raw SET wp_post_id_as=?, wp_permalink_as=?, edition_suivante=NULL "
        "WHERE id=?", (nouvelle["wp_post_id_as"], nouvelle.get("wp_permalink_as"), ancienne["id"]))
    conn.execute(
        "UPDATE events_raw SET wp_post_id_as=NULL, wp_permalink_as=NULL, "
        "edition_precedente=NULL, edition_adoptee_le=NULL WHERE id=?", (nouvelle["id"],))
    conn.commit()
    return ancienne


def _row(conn, eid: int) -> dict | None:
    r = conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone()
    return dict(r) if r else None


def _libelle(ev: dict) -> str:
    wp = f"WP#{ev['wp_post_id_as']}" if ev.get("wp_post_id_as") else "hors ligne"
    return f"[{ev['id']:>5} {wp:>10}] {(ev.get('title') or '')[:52]:<52} · {ev.get('date_event_start') or '?'}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--paire", nargs=2, type=int, metavar=("ANCIENNE", "NOUVELLE"),
                     help="ids events_raw : l'édition publiée, puis la nouvelle")
    src.add_argument("--depuis-audit", action="store_true",
                     help="toutes les paires proposées par appariement_editions")
    src.add_argument("--defaire", type=int, metavar="NOUVELLE",
                     help="rend le post à l'ancienne fiche")
    ap.add_argument("--apply", action="store_true", help="écrit (défaut : dry-run)")
    ap.add_argument("--force", action="store_true",
                    help="ignore les critères d'appariement (paire explicite lue à l'œil)")
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--limit", type=int, default=3000)
    args = ap.parse_args(argv)

    today = date.today().isoformat()
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    if args.defaire:
        nouvelle = _row(conn, args.defaire)
        if not nouvelle or not nouvelle.get("edition_precedente"):
            print(f"Rien à défaire : la fiche {args.defaire} n'a adopté aucune édition.")
            return 1
        print(f"DÉFAIRE : {_libelle(nouvelle)} rend WP#{nouvelle['wp_post_id_as']} "
              f"à la fiche {nouvelle['edition_precedente']}")
        if not args.apply:
            print("DRY-RUN — rien écrit. --apply pour appliquer.")
            return 0
        anc = defaire(conn, nouvelle)
        rel = _row(conn, anc["id"])
        print(f"FAIT — la fiche {rel['id']} porte à nouveau WP#{rel['wp_post_id_as']} (relu en base).")
        return 0

    # ── Constitution des paires ────────────────────────────────────────────────────
    paires: list[tuple[dict, dict]] = []
    if args.paire:
        a, n = _row(conn, args.paire[0]), _row(conn, args.paire[1])
        if not a or not n:
            print("id introuvable en base"); return 1
        paires.append((a, n))
    else:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM events_raw WHERE duplicate_of IS NULL AND title IS NOT NULL "
            "ORDER BY id DESC LIMIT ?", (args.limit,)).fetchall()]
        for a, b, _raison in appariements(rows):
            # l'ANCIENNE est celle qui a le post ; si les deux en ont un, ce n'est pas
            # une adoption (refusé plus bas), on garde l'ordre chronologique.
            da, db_ = (a.get("date_event_start") or ""), (b.get("date_event_start") or "")
            anc, nou = (a, b) if da <= db_ else (b, a)
            paires.append((anc, nou))

    # ── Vérification, paire par paire ──────────────────────────────────────────────
    adoptables, refusees = [], []
    for anc, nou in paires:
        refus = verifier_paire(anc, nou, today, _etat_wp_reel, force=args.force)
        (refusees if refus else adoptables).append((anc, nou, refus))

    print(f"\nADOPTION D'ÉDITIONS — {len(paires)} paire(s) examinée(s) au {today}")
    print(f"  adoptables : {len(adoptables)}   refusées : {len(refusees)}\n")
    for anc, nou, _ in adoptables:
        print("  ADOPTABLE"); print("   ", _libelle(anc)); print("   ", _libelle(nou))
        print(f"    → la fiche {nou['id']} reprend WP#{anc['wp_post_id_as']} "
              f"({(anc.get('wp_permalink_as') or '')[:70]})\n")
    for anc, nou, refus in refusees:
        print("  REFUSÉE"); print("   ", _libelle(anc)); print("   ", _libelle(nou))
        for r in refus: print(f"    ✗ {r}")
        print()

    if not args.apply:
        print("DRY-RUN — rien n'a été écrit. Relancer avec --apply pour adopter les ADOPTABLES.")
        return 0

    # ── Écriture, puis RECOMPTE (règle 6) ──────────────────────────────────────────
    for anc, nou, _ in adoptables:
        adopter(conn, anc, nou)
    ok = 0
    for anc, nou, _ in adoptables:
        n2, a2 = _row(conn, nou["id"]), _row(conn, anc["id"])
        if n2 and a2 and n2.get("wp_post_id_as") == anc["wp_post_id_as"] \
                and not a2.get("wp_post_id_as") and a2.get("edition_suivante") == nou["id"]:
            ok += 1
    print(f"APPLIQUÉ — {ok} adoption(s) relue(s) en base sur {len(adoptables)} proposée(s).")
    if adoptables:
        ids = " ".join(str(n["id"]) for _a, n, _r in adoptables)
        print("Le site ne changera qu'après la republication des nouvelles fiches :")
        print(f"  .venv/bin/python -m scripts.publish_batch_as --ids {ids}")
    log.info("adopter_edition : %d adoption(s)", ok)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
