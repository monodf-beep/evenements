#!/usr/bin/env python3
"""RÉCONCILIATION — répare tout seul les deux écarts que Franck a dû corriger à la main
le 2026-08-03. Réversible et déterministe, donc éligible au cron hebdomadaire
(cf. la doctrine en tête de scripts/weekly_audits.py).

POURQUOI CE SCRIPT EXISTE. La journée du 2026-08-03 a été faite entièrement à la main :
28 fiches hors périmètre retirées une par une, deux archivages faux rouverts, des liens
périmés inventoriés. Or quatre des cinq opérations étaient RÉVERSIBLES et DÉTERMINISTES —
elles remplissaient déjà les critères d'automatisation du dépôt. Elles n'étaient pas
automatisées pour une raison sans rapport avec la technique : chaque script avait été
écrit le jour d'un incident, comme réparation ponctuelle, et personne ne l'avait promu
dans le cron. Le rangement existait, on n'y avait rien rangé.

DEUX RÉPARATIONS, et rien d'autre :

  A. HORS PÉRIMÈTRE RESTÉ EN LIGNE. `scripts/purge_out_of_zone.py` refuse — à raison — de
     toucher une fiche publiée : y poser 'rejected' laisserait un orphelin visible du
     public. Ce refus n'avait pas d'issue tant qu'aucun outil ne savait retirer la page ET
     fermer le statut d'un seul geste. `scripts/trash_by_ids.py --statut rejected` le fait
     depuis le 2026-08-03, dans une seule transaction. L'obstacle est levé.
     ⚠️ ON VÉRIFIE AUPRÈS DE WORDPRESS AVANT D'AGIR. Le 2026-08-03, 21 fiches portaient un
     `wp_post_id_as` sans être en ligne : leurs posts avaient été corbeillés plus tôt et la
     base avait gardé l'identifiant. Un identifiant n'est PAS une preuve de publication —
     c'est l'erreur qui a produit la fausse alerte « 61 posts supprimés » du 2026-08-02.
     Les fiches dont le post n'est plus public sont laissées à `reconcile_wp_deleted.py`.
     ⚠️ LES JUMEAUX FR/IT PARTENT ENSEMBLE. Retirer le français seul laisse l'italien en
     ligne, orphelin — et l'inverse. On étend donc la sélection aux traductions.

  B. ARCHIVAGE « PASSÉ » SUR UN ÉVÉNEMENT À VENIR. Le bouton « archiver les passés » du
     back-office (app/app.py, action=archive_past) pose statut='rejected' sur
     `COALESCE(NULLIF(date_event_end,''), date_event_start) < today`. La règle est juste ;
     ce qui ne l'est pas, c'est qu'elle a pu s'appliquer sur des dates FAUSSES, corrigées
     depuis — l'incident connu où `dates.py` re-parsait le texte italien d'une traduction
     avec un analyseur français. Les dates ont été réparées, le statut jamais rouvert.
     C'est LE motif récurrent de ce dépôt : un état terminal qu'un script pose et qu'aucun
     autre ne sait rouvrir.
     L'inverse est exact, et c'est ce qui rend la réparation sûre : le bouton ne frappe
     QUE des fiches 'evaluated' avec llm_score >= 7 (sa clause WHERE le dit), et il ne
     touche pas au score. Restaurer 'evaluated' rend donc précisément l'état d'avant —
     on ne devine rien.

CE QU'IL NE FAIT PAS. Aucun jugement éditorial. Il ne décide jamais qu'une fiche est
bonne ou mauvaise : il applique une liste de communes et une comparaison de dates. Les
arbitrages (celle-ci est-elle un vrai événement ?) restent humains — c'est la frontière
que trace scripts/weekly_audits.py et on ne la déplace pas.

Usage :
    .venv/bin/python -m scripts.reconcile_catalogue            # dry-run
    .venv/bin/python -m scripts.reconcile_catalogue --apply
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.perimetre import ville_hors_perimetre

log = get_logger("reconcile-catalogue")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
UA = {"User-Agent": "AgendaSabauda-reconcile/1.0"}

MOTIF_PERIMETRE = ("Hors périmètre — commune de l'arrondissement de Grasse ; le Comté de "
                   "Nice couvre l'arrondissement de Nice (charte §2).")
# Empreinte du message posé par le bouton « archiver les passés » (app/app.py). On ne
# rouvre QUE ce qu'il a fermé : un rejet éditorial ou un rejet de l'évaluateur porte un
# autre motif et n'est jamais touché ici.
MOTIF_ARCHIVE = "Passé — archivé depuis À valider."


def _post_public(wp_url: str, post_id: int) -> bool | None:
    """True = public · False = corbeille/brouillon/supprimé · None = indéterminé.

    ⚠️ NE JAMAIS interroger le front-end : `/?p=<id>` renvoie 404 pour tout tribe_events
    de cette installation, vivant ou mort, et un post en corbeille est indistinguable d'un
    post supprimé. Seule l'API REST sépare les états (cf. reconcile_wp_deleted._etat).
    Un `None` ne déclenche AUCUNE action : on ne retire pas une page sur un doute réseau.
    """
    try:
        r = requests.get(f"{wp_url}/wp-json/wp/v2/tribe_events/{post_id}",
                         params={"_fields": "id,status"}, timeout=20, headers=UA)
    except requests.RequestException as exc:
        log.warning("WP#%s : appel REST impossible (%s) — laissée intacte.", post_id, exc)
        return None
    if r.status_code == 200:
        return True
    try:
        code = str((r.json() or {}).get("code") or "")
    except ValueError:
        return None
    if code in ("rest_post_invalid_id", "rest_forbidden") or r.status_code in (401, 403):
        return False
    return None


def _avec_jumeaux(conn: sqlite3.Connection, ids: set[int]) -> set[int]:
    """Étend un ensemble d'ids à leurs jumeaux de traduction, dans les deux sens.

    Une paire FR/IT décrit UN événement : n'en retirer qu'une moitié laisse l'autre seule
    en ligne, sans version dans l'autre langue, et casse l'appariement hreflang. Le
    comptage de scripts/count_grasse.py le signale explicitement (« une purge doit traiter
    les deux jumeaux ensemble »)."""
    if not ids:
        return ids
    out = set(ids)
    marks = ",".join("?" * len(ids))
    for r in conn.execute(
            f"SELECT id, translation_of FROM events_raw WHERE translation_of IN ({marks}) "
            f"OR id IN (SELECT translation_of FROM events_raw WHERE id IN ({marks}) "
            f"          AND COALESCE(translation_of,0) > 0)",
            (*ids, *ids)):
        out.add(r[0])
    return out


def _reparation_perimetre(conn, wp_url, auth, args) -> list[str]:
    """A — fiches hors périmètre encore PUBLIÉES : corbeille + statut, d'un seul geste."""
    lignes: list[str] = []
    candidats = [dict(r) for r in conn.execute(
        "SELECT id, title, ville, statut, wp_post_id_as FROM events_raw "
        "WHERE COALESCE(wp_post_id_as,0) > 0 AND COALESCE(ville,'') <> '' "
        "AND duplicate_of IS NULL")]
    hors = {r["id"]: r for r in candidats if ville_hors_perimetre(r["ville"])}
    if not hors:
        return ["aucune fiche hors périmètre ne porte d'identifiant WordPress"]

    # Jumeaux : une paire FR/IT part ensemble (voir _avec_jumeaux).
    tous = _avec_jumeaux(conn, set(hors))
    manquants = tous - set(hors)
    if manquants:
        marks = ",".join("?" * len(manquants))
        for r in conn.execute(
                f"SELECT id, title, ville, statut, wp_post_id_as FROM events_raw "
                f"WHERE id IN ({marks}) AND COALESCE(wp_post_id_as,0) > 0", tuple(manquants)):
            hors[r[0]] = dict(zip(("id", "title", "ville", "statut", "wp_post_id_as"), r))
        lignes.append(f"{len(manquants)} jumeau(x) de traduction ajouté(s) à la sélection")

    a_retirer, hors_ligne, doutes = [], 0, 0
    for i, ev in enumerate(sorted(hors.values(), key=lambda e: e["id"]), 1):
        etat = _post_public(wp_url, int(ev["wp_post_id_as"]))
        if args.delay and i < len(hors):
            time.sleep(args.delay)
        if etat is True:
            a_retirer.append(ev)
        elif etat is False:
            hors_ligne += 1
        else:
            doutes += 1

    lignes.append(f"{len(hors)} fiche(s) hors périmètre avec un ID WP — {len(a_retirer)} "
                  f"réellement en ligne, {hors_ligne} déjà retirée(s) du site, "
                  f"{doutes} indéterminée(s)")
    if hors_ligne:
        lignes.append(f"  ({hors_ligne} portent un lien périmé — c'est le travail de "
                      f"reconcile_wp_deleted, pas le nôtre)")
    if not a_retirer:
        return lignes

    for ev in a_retirer:
        log.info("  [%s] WP#%s %s « %s »", ev["id"], ev["wp_post_id_as"],
                 (ev["ville"] or "")[:22], (ev["title"] or "")[:50])
    if not args.apply:
        lignes.append(f"  DRY-RUN : {len(a_retirer)} à retirer, rien fait")
        return lignes

    from scripts.trash_by_ids import main as trash_main
    vises = [e["id"] for e in a_retirer]
    rc = trash_main([*[str(i) for i in vises], "--statut", "rejected",
                     "--motif", MOTIF_PERIMETRE, "--apply", "--delay", str(args.delay)])
    # ⚠️ ON RECOMPTE EN BASE PLUTÔT QUE DE CROIRE L'APPEL. Première version de ce bloc :
    # elle annonçait « N retirée(s) » sur la seule foi du nombre DEMANDÉ, et ne dégradait
    # le message qu'en « ⚠️ le retrait a signalé une erreur » — vérifié sur banc d'essai,
    # elle affichait « 4 retirée(s) du site et rejetée(s) en base » alors que zéro l'avait
    # été (identifiants WordPress absents, le script appelé avait refusé d'agir). Un
    # bilan qui rapporte l'INTENTION au lieu du RÉSULTAT est pire qu'un silence : il ferme
    # la question. On relit donc l'état réel.
    marks = ",".join("?" * len(vises))
    faits = conn.execute(
        f"SELECT COUNT(*) FROM events_raw WHERE id IN ({marks}) "
        f"AND statut='rejected' AND COALESCE(wp_post_id_as,0)=0", tuple(vises)).fetchone()[0]
    if faits == len(vises) and not rc:
        lignes.append(f"  {faits} retirée(s) du site et rejetée(s) en base")
    else:
        lignes.append(f"  ⚠️ ÉCHEC PARTIEL — {faits}/{len(vises)} seulement ont été "
                      f"retirée(s) ; les autres sont INCHANGÉES et toujours en ligne. "
                      f"Voir les logs de trash_by_ids.")
    return lignes


def _reparation_archivage(conn, args) -> list[str]:
    """B — archivages « passé » posés sur des événements dont la date est à venir."""
    today = date.today().isoformat()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, wp_post_id_as, date_event_start, date_event_end, llm_score "
        "FROM events_raw WHERE statut='rejected' AND duplicate_of IS NULL "
        "AND llm_justification = ? "
        "AND COALESCE(NULLIF(date_event_end,''), date_event_start) >= ? "
        "ORDER BY date_event_start", (MOTIF_ARCHIVE, today))]
    if not rows:
        return ["aucun archivage « passé » ne porte de date à venir"]

    for r in rows:
        log.info("  [%s] %s → %s « %s »", r["id"], r["date_event_start"],
                 r["date_event_end"] or "?", (r["title"] or "")[:50])
    if not args.apply:
        return [f"{len(rows)} archivage(s) à rouvrir — DRY-RUN, rien fait"]

    justif = (f"Rouverte le {today} — archivée comme passée alors que sa date est à venir "
              f"(la date a été corrigée après l'archivage ; le statut ne l'avait pas été).")
    # 'evaluated' est l'état EXACT d'avant : le bouton d'archivage ne frappe que des
    # fiches 'evaluated' avec llm_score >= 7 et ne touche pas au score (cf. app/app.py,
    # validation_tidy). On restaure, on ne devine pas.
    conn.executemany("UPDATE events_raw SET statut='evaluated', llm_justification=? "
                     "WHERE id=?", [(justif, r["id"]) for r in rows])
    conn.commit()
    return [f"{len(rows)} archivage(s) rouvert(s) → 'evaluated' (score inchangé)"]


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(description="Réconcilie le catalogue avec le site.")
    p.add_argument("--apply", action="store_true", help="Écrit (sinon dry-run).")
    p.add_argument("--delay", type=float, default=0.4, help="Pause entre deux appels REST.")
    p.add_argument("--sans-perimetre", action="store_true", help="Saute la réparation A.")
    p.add_argument("--sans-archivage", action="store_true", help="Saute la réparation B.")
    args = p.parse_args(argv)

    wp_url = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    lignes: list[str] = []
    if not args.sans_perimetre:
        if args.apply and not all([wp_url, auth[0], auth[1]]):
            lignes.append("⚠️ périmètre : identifiants WordPress absents, étape sautée")
        else:
            lignes += _reparation_perimetre(conn, wp_url, auth, args)
    if not args.sans_archivage:
        lignes += _reparation_archivage(conn, args)
    conn.close()

    for l in lignes:
        log.info("%s", l)
    if not args.apply:
        log.info("DRY-RUN — rien n'a été écrit. Ajouter --apply pour appliquer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
