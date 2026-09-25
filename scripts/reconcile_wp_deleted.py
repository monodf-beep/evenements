#!/usr/bin/env python3
"""Réconcilie la base avec la RÉALITÉ de WordPress : les fiches que la base croit
publiées alors que le post n'existe plus.

CE QUE ÇA RÉPARE. Quand un post est mis à la corbeille côté WordPress — par
cleanup_as_dupes (doublons nés dans WP), audit_non_events (articles de presse publiés à
tort), trash_by_ids (geste manuel) ou par Franck directement dans l'admin — RIEN ne
remet `wp_post_id_as` à zéro en base. Relevé le 2026-08-02 : 61 fiches dans ce cas.

Trois conséquences, toutes silencieuses :
  • scripts/site_audit.py les signalera en 🔴 à chaque tour de rotation, indéfiniment ;
  • publish_batch_as les saute (`COALESCE(wp_post_id_as,0) = 0` dans sa sélection) : une
    fiche corbeillée par erreur ne repartira JAMAIS toute seule ;
  • tous les comptages de « publiées » sont faux.

DEUX TRAITEMENTS, PAS UN. Le premier passage du 2026-08-02 a tranché : sur 61 fiches,
61 sont à la CORBEILLE et zéro réellement supprimée. Les deux cas n'appellent pas la
même réponse.
  • CORBEILLE / BROUILLON — le post existe et se restaure en un clic. On GARDE
    `wp_post_id_as` (l'effacer couperait le seul lien vers le post à restaurer) et on
    pose `wp_deleted_at`, le constat : « à cette date, ce post n'était plus public ».
    site_audit exclut ces fiches, donc plus d'alerte quotidienne sur une situation
    voulue — et c'est réversible : un post redevenu public est déshorodaté au run suivant.
  • RÉELLEMENT INEXISTANT — plus rien à quoi se raccrocher. On coupe le lien
    (`wp_post_id_as`, `wp_permalink_as`) pour que la fiche redevienne publiable si le
    catalogue la juge encore valide. Ce qui se passe alors est décidé par les filtres
    NORMAUX de publish_batch_as, pas par ce script : un événement passé ne repart pas
    (filtre « à venir »), un événement rejeté non plus. Ne repartirait qu'un événement
    À VENIR et toujours RETENU — une fiche que le catalogue juge valide et que
    quelqu'un a supprimée : cette contradiction mérite d'être vue, pas enterrée. Le
    dry-run la liste séparément.

VÉRIFICATION AVANT ÉCRITURE : chaque id est re-testé en direct via l'API REST (lecture
seule). Elle seule distingue corbeille et suppression, là où le front-end répond 404
pour les deux — cf. _etat(). Un aléa réseau reste indéterminé et n'autorise rien.

Usage :
    .venv/bin/python -m scripts.reconcile_wp_deleted           # dry-run (défaut)
    .venv/bin/python -m scripts.reconcile_wp_deleted --apply
    .venv/bin/python -m scripts.reconcile_wp_deleted --ids 956 1169 --apply
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("reconcile-wp-deleted")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
UA = {"User-Agent": "Mozilla/5.0 (compatible; CulturaSabaudaReconcile/1.0)"}
RETENUS = ("evaluated", "published_cs", "published_sub")


def _etat(wp_url: str, post_id: int) -> str:
    """'public' | 'non_public' | 'inexistant' | 'indetermine'.

    ⚠️ NE JAMAIS interroger le front-end pour ça. `/?p=<id>` renvoie 404 pour TOUT post
    de type tribe_events sur cette installation, vivant ou mort (vérifié : le post 601,
    parfaitement en ligne, y répond 404). Et même avec la bonne forme
    `/?post_type=tribe_events&p=<id>`, un post en CORBEILLE répond 404 exactement comme
    un post supprimé — indistinguables. C'est ce qui a produit la fausse alerte
    « 61 posts supprimés » du 2026-08-02 : aucun ne l'était, tous étaient à la corbeille.

    L'API REST, elle, sépare les trois états, et cette distinction commande TOUT ce que
    fait ce script : effacer wp_post_id_as d'un post seulement mis à la corbeille
    détruirait le lien vers un post RESTAURABLE."""
    try:
        r = requests.get(f"{wp_url}/wp-json/wp/v2/tribe_events/{post_id}",
                         timeout=20, headers=UA)
    except requests.RequestException:
        return "indetermine"
    if r.status_code == 200:
        return "public"
    code = ""
    try:
        code = str((r.json() or {}).get("code") or "")
    except ValueError:
        pass
    if code == "rest_post_invalid_id":
        return "inexistant"
    if code == "rest_forbidden" or r.status_code in (401, 403):
        return "non_public"
    return "indetermine"


def _ensure_col(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("ALTER TABLE events_raw ADD COLUMN wp_deleted_at TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass


def bilan(disparus: int, corbeille: int, dormants: int, repartiraient: int,
          revenus: int, indetermines: int) -> str:
    """La DERNIÈRE ligne du script, et donc celle que le digest hebdomadaire retient.

    POURQUOI ELLE EXISTE (2026-08-18). `weekly_audits` résume chaque étape par ses TROIS
    DERNIÈRES lignes (`_tail`). Or ce script finissait sur le milieu d'un listing : le
    message Slack du dimanche montrait deux fiches prises au hasard et « …et 90 autre(s) ».
    Le lecteur y voyait une file de 92 tâches là où il n'y avait, en général, RIEN à faire
    — la plupart de ces lignes sont des constats que `--apply` enregistre tout seul.

    Elle dit donc, dans l'ordre : le PÉRIMÈTRE, puis le seul geste humain, puis le reste.
    C'est la règle 6 — « avant d'ajouter une ligne à une file, se demander ce que le
    lecteur en FERA » : sur ces six catégories, une seule appelle un arbitrage.
    """
    total = disparus + corbeille + dormants + repartiraient + revenus + indetermines
    lignes = [f"=== BILAN — {total} fiche(s) portant un lien WordPress vérifiée(s) une "
              f"par une (périmètre : toutes, passées comprises)."]
    if repartiraient:
        lignes.append(f"⚠️ À TRANCHER À LA MAIN : {repartiraient} — à venir, toujours "
                      f"retenue(s) en base, mais corbeillée(s) sur le site. Elles "
                      f"repartiraient en ligne au prochain lot.")
    else:
        lignes.append("Aucune contradiction à trancher : rien ne repartirait en ligne "
                      "contre une décision prise sur le site.")
    lignes.append(f"Sans geste de votre part : {disparus} lien(s) coupé(s), {corbeille} "
                  f"constat(s) horodaté(s), {dormants} sans effet de bord (passées ou non "
                  f"retenues), {revenus} constat(s) périmé(s) effacé(s), {indetermines} "
                  f"à revérifier au prochain passage.")
    return "\n".join(lignes)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Réconcilie la base avec les posts WordPress supprimés.")
    p.add_argument("--apply", action="store_true", help="Écrit (sinon dry-run).")
    p.add_argument("--ids", type=int, nargs="+", default=None, help="Limiter à ces ids.")
    p.add_argument("--delay", type=float, default=0.8, help="Pause entre deux appels.")
    args = p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    wp_url = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_col(conn)

    sql = ("SELECT id, title, statut, date_event_start, date_event_end, wp_post_id_as, "
           "       wp_deleted_at FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0")
    params: list = []
    if args.ids:
        sql += f" AND id IN ({','.join('?' * len(args.ids))})"
        params = args.ids
    rows = [dict(r) for r in conn.execute(sql + " ORDER BY id", params).fetchall()]
    log.info("%d fiche(s) que la base croit publiées — vérification une par une.", len(rows))

    today = date.today().isoformat()
    disparus, corbeille, indetermines, revenus = [], [], [], []
    for i, r in enumerate(rows, 1):
        etat = _etat(wp_url, int(r["wp_post_id_as"]))
        if etat == "public":
            # Post redevenu public (restauré à la main) : on efface le constat, sinon
            # site_audit continuerait de l'ignorer alors qu'il est de nouveau en ligne.
            if (r.get("wp_deleted_at") or "").strip():
                revenus.append(r)
        elif etat in ("inexistant", "non_public"):
            fin = (r.get("date_event_end") or r.get("date_event_start") or "")[:10]
            r["_repartirait"] = bool(r["statut"] in RETENUS and fin and fin >= today)
            (disparus if etat == "inexistant" else corbeille).append(r)
        else:
            indetermines.append(r)
        if args.delay and i < len(rows):
            time.sleep(args.delay)

    repartiraient = [r for r in disparus if r["_repartirait"]]
    dormants = [r for r in disparus if not r["_repartirait"]]

    print(f"\n{len(rows)} fiche(s) vérifiée(s) — {len(disparus)} réellement supprimée(s), "
          f"{len(corbeille)} en corbeille/brouillon, {len(indetermines)} indéterminée(s).")

    if corbeille:
        # ON GARDE wp_post_id_as. Un post à la corbeille se restaure en un clic dans
        # l'admin : effacer son id couperait le seul lien entre la fiche en base et le
        # post à restaurer — ce serait détruire de l'information, pas la réconcilier.
        # On pose seulement `wp_deleted_at`, c'est-à-dire le CONSTAT : « à cette date, ce
        # post n'était plus public ». Ça suffit à faire taire site_audit (qui exclut ces
        # fiches) sans rien perdre, et c'est réversible : si le post redevient public, le
        # prochain run efface l'horodatage tout seul.
        print(f"\n--- {len(corbeille)} EN CORBEILLE / BROUILLON ---")
        print("    (--apply pose wp_deleted_at et GARDE wp_post_id_as : la fiche cesse")
        print("     d'être relue comme si elle était en ligne, et le post reste")
        print("     restaurable. Réversible : un post redevenu public est déshorodaté.)")
        for r in corbeille[:40]:
            print(f"  [{r['id']}] WP#{r['wp_post_id_as']} {(r['title'] or '')[:50]:52} "
                  f"statut={r['statut']} · {(r.get('date_event_start') or '—')[:10]}")
        if len(corbeille) > 40:
            print(f"  …et {len(corbeille) - 40} autre(s).")

    if dormants:
        print(f"\n--- {len(dormants)} SANS EFFET DE BORD — passées ou non retenues ---")
        print("    (effacer wp_post_id_as remet juste la base d'accord avec le site :")
        print("     les filtres de publish_batch_as ne les reprendront pas.)")
        for r in dormants[:40]:
            print(f"  [{r['id']}] WP#{r['wp_post_id_as']} {(r['title'] or '')[:50]:52} "
                  f"statut={r['statut']} · {(r.get('date_event_start') or '—')[:10]}")
        if len(dormants) > 40:
            print(f"  …et {len(dormants) - 40} autre(s).")

    if repartiraient:
        print(f"\n--- ⚠️  {len(repartiraient)} REPARTIRAIENT EN LIGNE au prochain lot ---")
        print("    (à venir ET toujours retenues : le catalogue les juge valides, mais")
        print("     quelqu'un les a corbeillées. Contradiction à trancher À LA MAIN —")
        print("     soit les rejeter en base, soit les laisser repartir.)")
        for r in repartiraient:
            print(f"  [{r['id']}] WP#{r['wp_post_id_as']} {(r['title'] or '')[:50]:52} "
                  f"statut={r['statut']} · {(r.get('date_event_start') or '—')[:10]}")

    if revenus:
        print(f"\n--- {len(revenus)} REVENUE(S) EN LIGNE — constat périmé, sera effacé ---")
        for r in revenus:
            print(f"  [{r['id']}] WP#{r['wp_post_id_as']} {(r['title'] or '')[:50]}")

    if indetermines:
        print(f"\n--- {len(indetermines)} INDÉTERMINÉE(S) — non touchées, à revérifier ---")
        for r in indetermines[:15]:
            print(f"  [{r['id']}] WP#{r['wp_post_id_as']} {(r['title'] or '')[:50]}")

    if not args.apply:
        print(f"\n(dry-run : rien écrit — --apply couperait {len(disparus)} lien(s), "
              f"horodaterait {len(corbeille)} fiche(s) hors ligne et déshorodaterait "
              f"{len(revenus)} revenue(s).)")
        print("\n" + bilan(len(disparus), len(corbeille), len(dormants),
                           len(repartiraient), len(revenus), len(indetermines)))
        conn.close()
        return 0

    stamp = datetime.now().isoformat(timespec="seconds")
    # RÉELLEMENT INEXISTANT : plus rien à quoi se raccrocher côté WordPress, on coupe le
    # lien pour que la fiche redevienne publiable si le catalogue la juge encore valide.
    for r in disparus:
        conn.execute("UPDATE events_raw SET wp_post_id_as=NULL, wp_permalink_as=NULL, "
                     "wp_deleted_at=? WHERE id=?", (stamp, r["id"]))
        log.info("[%s] WP#%s : post inexistant, lien coupé — %s",
                 r["id"], r["wp_post_id_as"], (r["title"] or "")[:55])
    # CORBEILLE / BROUILLON : on garde l'id (le post est restaurable), on note le constat.
    for r in corbeille:
        conn.execute("UPDATE events_raw SET wp_deleted_at=? WHERE id=?", (stamp, r["id"]))
        log.info("[%s] WP#%s : plus public, constat horodaté (id conservé) — %s",
                 r["id"], r["wp_post_id_as"], (r["title"] or "")[:55])
    # REVENU EN LIGNE : le constat ne vaut plus, on l'efface.
    for r in revenus:
        conn.execute("UPDATE events_raw SET wp_deleted_at=NULL WHERE id=?", (r["id"],))
        log.info("[%s] WP#%s : de nouveau en ligne — %s",
                 r["id"], r["wp_post_id_as"], (r["title"] or "")[:55])
    conn.commit()
    conn.close()
    log.info("=== %d lien(s) coupé(s) · %d horodatée(s) hors ligne · %d revenue(s) · "
             "%d repartiraient au prochain lot ===",
             len(disparus), len(corbeille), len(revenus), len(repartiraient))
    # EN DERNIER, et en `print` : c'est cette ligne que `weekly_audits._tail` retient pour
    # le digest du dimanche. Le journal (log.info ci-dessus) ne lui parvient pas.
    print("\n" + bilan(len(disparus), len(corbeille), len(dormants),
                       len(repartiraient), len(revenus), len(indetermines)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
