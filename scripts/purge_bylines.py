#!/usr/bin/env python3
"""Retire des fiches le nom du JOURNALISTE écrit dans la colonne `organisateur`.

LE ROUVREUR DE L'INCIDENT DU 2026-08-11 (règle 3 de CLAUDE.md : tout état posé par un
script doit avoir quelqu'un qui le défait). `scripts/scraper_events.py` recopiait
`entry.author` du flux RSS dans `organisateur` ; c'est l'auteur de l'ARTICLE. Le correctif
posé dans le scraper (utils/bylines.py) protège les collectes FUTURES et ne touche pas une
seule des fiches déjà en base — dont plusieurs sont publiées avec le nom d'une journaliste
présenté comme organisatrice. Ce script est la moitié qui manque.

CE QU'IL FAIT, ET CE QU'IL NE FAIT PAS
  • il VIDE `organisateur` quand la valeur est une signature (utils.bylines.verdict) —
    et l'ancienne valeur part dans `organisateur_byline`, donc rien n'est perdu et un
    UPDATE la remet ;
  • il ne DEVINE jamais le vrai organisateur : vide, `scripts/enrich.py` retombe sur
    `source_name`, c'est-à-dire l'institution qui publie le flux. C'est déjà mieux ;
  • il ne touche PAS au texte des articles déjà écrits. Une fiche publiée continue
    d'afficher le nom dans son corps tant qu'elle n'est pas réenrichie — le dire est le
    seul moyen de ne pas croire le site réparé (règle 1). D'où `--reenrichir`, qui remet
    ces fiches dans la file de rédaction, et qui n'est PAS le défaut : cela consomme de
    l'API, et le plafond court jusqu'au 2026-09-01.

PÉRIMÈTRE (règle 5, et règle 6 : un chiffre s'écrit avec son périmètre à côté). Par
défaut : les fiches encore devant nous — à venir, en cours (c'est `date_event_end` qui
décide) ou récurrentes. `--tout` ajoute le passé : ces fiches ne reviendront dans aucune
file, mais celles qui sont restées en ligne portent la même erreur, et la corriger ne
coûte qu'un UPDATE. Les deux nombres sont toujours affichés, jamais fondus en un seul.

  .venv/bin/python -m scripts.purge_bylines             # simulation (défaut)
  .venv/bin/python -m scripts.purge_bylines --apply
  .venv/bin/python -m scripts.purge_bylines --apply --tout
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.bylines import verdict  # noqa: E402
from utils.logger import get_logger  # noqa: E402

log = get_logger("purge_bylines")
DB = ROOT / "data" / "events.db"

# Fiches réellement candidates : ni doublon, ni traduction (la traduction recopie le
# champ de sa source, la corriger deux fois n'apporte rien et masquerait un écart).
_VIVANTES = ("duplicate_of IS NULL AND COALESCE(translation_of,0)=0 "
             "AND COALESCE(organisateur,'') <> ''")
# Encore devant nous : à venir, en cours (date de FIN), ou récurrent (pas de date unique).
_DEVANT = ("(COALESCE(recurring,0)=1 OR COALESCE(NULLIF(date_event_end,''), "
           "NULLIF(date_event_start,''), '9999') >= ?)")


def _ensure_colonne_memoire(conn: sqlite3.Connection) -> None:
    """`organisateur_byline` : la valeur retirée, gardée telle quelle.

    Sans elle l'opération serait irréversible — et CLAUDE.md n'autorise l'autonomie que
    sur ce qui se défait. Idempotent : appelé aussi par la simulation, pour que le
    dry-run échoue au même endroit que l'application s'il doit échouer."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
    if "organisateur_byline" not in cols:
        conn.execute("ALTER TABLE events_raw ADD COLUMN organisateur_byline TEXT")
        conn.commit()


def _candidates(conn: sqlite3.Connection, today: str, tout: bool) -> list[dict]:
    sql = f"SELECT * FROM events_raw WHERE {_VIVANTES}"
    params: tuple = ()
    if not tout:
        sql += f" AND {_DEVANT}"
        params = (today,)
    return [dict(r) for r in conn.execute(sql + " ORDER BY id", params)]


def _a_vider(ev: dict) -> tuple[bool, str]:
    """La matière lue est celle de la fiche : titre + description. C'est exactement ce
    que le modèle a eu sous les yeux pour écrire l'article — donc si la preuve n'y est
    pas, elle n'y était pas non plus au moment de la rédaction."""
    matiere = f"{ev.get('title') or ''}\n{ev.get('description') or ''}"
    v, raison = verdict(ev.get("organisateur") or "", matiere)
    return v == "vider", raison


def _checks_du_nom(conn: sqlite3.Connection, event_id: int, nom: str) -> list[sqlite3.Row]:
    """Points « À vérifier » EN ATTENTE qui parlent de ce nom-là.

    C'est le lien qui ferme la boucle : « Fonction exacte de Denis Falconieri » n'a plus
    d'objet une fois le nom retiré de la fiche. On ne les ferme que pour les fiches NON
    publiées — voir plus bas : sur une fiche en ligne, le nom est encore dans le texte."""
    from utils.bylines import _norm  # même normalisation que le verdict
    cible = _norm(nom)
    return [r for r in conn.execute(
        "SELECT id, label FROM checks WHERE event_id=? AND status='pending'", (event_id,))
        if cible and cible in _norm(r["label"])]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="écrit (défaut : simulation)")
    ap.add_argument("--tout", action="store_true",
                    help="inclut les événements passés (par défaut : ce qui est devant nous)")
    ap.add_argument("--reenrichir", action="store_true",
                    help="remet les fiches PUBLIÉES concernées dans la file de rédaction "
                         "(consomme de l'API ; le plafond court jusqu'au 2026-09-01)")
    args = ap.parse_args(argv)

    if not DB.exists():
        log.error("Base introuvable : %s", DB)
        return 1
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    _ensure_colonne_memoire(conn)
    today = date.today().isoformat()

    lignes, publiees, checks_fermables = [], [], 0
    for ev in _candidates(conn, today, args.tout):
        vider, raison = _a_vider(ev)
        if not vider:
            continue
        nom = (ev.get("organisateur") or "").strip()
        en_ligne = bool(ev.get("wp_post_id_as"))
        pts = _checks_du_nom(conn, ev["id"], nom)
        if not en_ligne:
            checks_fermables += len(pts)
        lignes.append((ev["id"], nom, en_ligne, len(pts), raison,
                       (ev.get("article_title") or ev.get("title") or "")[:58]))
        if en_ligne:
            publiees.append(ev["id"])

    if not lignes:
        print("Aucune signature à retirer.")
        conn.close()
        return 0

    print(f"═══ {len(lignes)} fiche(s) dont `organisateur` est une signature ═══\n")
    for eid, nom, en_ligne, npts, raison, titre in lignes:
        marque = "EN LIGNE" if en_ligne else "hors ligne"
        pts = f" · {npts} point(s) « À vérifier »" if npts else ""
        print(f"  [{eid:5}] {marque:10} « {nom} »{pts}\n"
              f"          {titre}\n          → {raison}")

    perimetre = ("toutes les fiches, passé compris" if args.tout
                 else "événements à venir, en cours ou récurrents uniquement")
    if not args.apply:
        print("\nSimulation — RIEN n'a été écrit. Ajouter --apply pour enregistrer.")
        print(f"Périmètre : {perimetre}.")
        print(f"Points « À vérifier » qui se fermeraient d'eux-mêmes : {checks_fermables} "
              f"(uniquement sur les fiches hors ligne).")
        conn.close()
        return 0

    for eid, nom, *_ in lignes:
        conn.execute("UPDATE events_raw SET organisateur_byline=organisateur, "
                     "organisateur='' WHERE id=?", (eid,))
    # Points « À vérifier » : fermés UNIQUEMENT sur les fiches hors ligne. Sur une fiche
    # publiée, le nom reste écrit dans le corps de l'article tant qu'elle n'est pas
    # réécrite — fermer la tâche donnerait à croire que le site est réparé alors qu'il
    # affiche toujours la journaliste comme organisatrice (règle 1).
    for eid, nom, en_ligne, npts, *_ in lignes:
        if en_ligne or not npts:
            continue
        for r in _checks_du_nom(conn, eid, nom):
            conn.execute("UPDATE checks SET status='done', resolved_at=datetime('now') "
                         "WHERE id=?", (r["id"],))
    if args.reenrichir and publiees:
        marques = ",".join("?" * len(publiees))
        conn.execute(f"UPDATE events_raw SET enrich_status='' WHERE id IN ({marques})",
                     publiees)
    conn.commit()

    # RECOMPTER EN BASE (règle 6) : on ne rapporte pas la longueur de la liste qu'on
    # vient de parcourir, on redemande à SQLite ce qu'il reste.
    restant = conn.execute(
        f"SELECT COUNT(*) FROM events_raw WHERE {_VIVANTES}"
        + ("" if args.tout else f" AND {_DEVANT}"),
        () if args.tout else (today,)).fetchone()[0]
    vides = conn.execute(
        "SELECT COUNT(*) FROM events_raw WHERE COALESCE(organisateur_byline,'') <> '' "
        "AND COALESCE(organisateur,'') = ''").fetchone()[0]
    pendants = conn.execute(
        "SELECT COUNT(*) FROM checks WHERE status='pending'").fetchone()[0]
    conn.close()

    print(f"\n✅ {vides} fiche(s) portent désormais une colonne `organisateur` vide et "
          f"leur ancienne valeur dans `organisateur_byline` (recompté en base).")
    print(f"   Il reste {restant} fiche(s) avec un `organisateur` non vide dans ce "
          f"périmètre ({perimetre}) — ce sont celles jugées légitimes.")
    print(f"   Points « À vérifier » encore en attente, toutes familles confondues : {pendants}.")
    if publiees:
        print(f"\n⚠️  {len(publiees)} fiche(s) sont EN LIGNE : la colonne est corrigée, mais "
              f"le nom reste écrit dans le corps de l'article publié.")
        print(f"   Fiches : {', '.join(str(i) for i in publiees)}")
        if args.reenrichir:
            print("   Elles sont remises dans la file de rédaction (enrich_status vidé).")
        else:
            print("   Leur point « À vérifier » est laissé OUVERT exprès. Pour les faire "
                  "réécrire : --reenrichir (après le 2026-09-01, plafond API).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
