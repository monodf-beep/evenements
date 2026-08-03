#!/usr/bin/env python3
"""RAFRAÎCHIR `as_deplacement_now` — le score de tri de « Ça vaut le déplacement »
n'est pas une valeur, c'est une valeur DATÉE.

LE DÉFAUT QU'IL CORRIGE, et c'en était un de conception. `utils.deplacement.deplacement_now`
relève le score intrinsèque (0-8) par le TEMPS QUI RESTE pour y aller. Ce bonus dépend donc
du calendrier, pas de la fiche. Or `publisher_as` le calcule **au moment de la publication**
et l'écrit dans une méta WordPress, où il reste GELÉ. Conséquences, toutes silencieuses :

  • une fiche publiée aujourd'hui avec le bonus « dans 4 jours » (+3) garde 11 en octobre,
    alors qu'elle est terminée depuis des semaines — et elle trône en tête de la section ;
  • une fiche publiée en juin pour un festival de septembre a été figée à +0 : le jour où
    elle devient imminente, RIEN ne le lui dit, et elle reste au fond ;
  • un événement PASSÉ doit sortir de la section (deplacement_now renvoie None, règle 5),
    mais sa méta gelée continue de le classer.

Autrement dit : le classement dérive tout seul, dans les deux sens, et personne ne le voit.
C'est exactement le motif de `docs/ETATS_TERMINAUX.md` sous une autre forme — non pas « un
état que personne ne rouvre », mais « une valeur que personne ne recalcule ». La question de
la règle 3 vaut aussi pour les valeurs vivantes : QUI la remet à jour ?

Réponse : ce script, tous les jours, à 11h.

CE QU'IL NE REPUBLIE PAS. Republier 120 fiches par jour pour en changer deux serait
coûteux et illisible. La colonne `deplacement_now_publie` retient ce qui a RÉELLEMENT été
envoyé à WordPress ; on ne republie que les fiches dont la valeur a changé. En régime
normal, ce sont les seules qui franchissent une marche (45, 21, 7 jours restants) ou qui
viennent de passer — une poignée par jour. La première exécution, elle, rattrape tout le
stock : c'est le prix d'entrée, une seule fois.

IL VÉRIFIE AVANT D'ÉCRIRE (règle 1). Un `wp_post_id_as` renseigné ne prouve pas que le post
est en ligne. Le constat du 2026-08-03 est sans appel : sur les 123 fiches republiées à la
main ce jour-là, **16 étaient à la corbeille** alors que la base les croyait publiées.
Republier un post corbeillé le ferait remonter d'entre les morts. Donc, pour chaque fiche
dont la valeur change : interrogation REST **par son numéro** (jamais une collection —
règle 2, TEC masque les événements passés de ses listes, or ce sont précisément ceux-là que
ce script doit faire sortir de la section). Un post non public est SIGNALÉ, jamais poussé.

LES TRADUCTIONS, ET POURQUOI ELLES SONT TRAITÉES ICI. Le score dérive de
`llm_score_detail`, que l'évaluateur écrit sur la fiche d'ORIGINE et jamais sur sa
traduction — `translate_events` ne copiait pas cette colonne. Résultat mesuré le
2026-08-03 : les 14 fiches Savoie + Comté de Nice traduites en italien avaient toutes un
score VIDE, et la section italienne retombait sur `as_score`, c'est-à-dire exactement le
tri qu'on venait de quitter. La copie est désormais faite à la création (cf.
`translate_events`), mais ça ne répare pas les traductions déjà en base : la propagation
ci-dessous s'en charge, et reste en place comme filet — c'est une réponse à « qui rouvre ? »
plutôt qu'une commande que personne ne lancera.

Usage :
    .venv/bin/python -m scripts.refresh_deplacement            # dry-run (défaut)
    .venv/bin/python -m scripts.refresh_deplacement --apply
    .venv/bin/python -m scripts.refresh_deplacement --apply --cap 30
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.deplacement import deplacement_now
from utils.logger import get_logger

log = get_logger("refresh-deplacement")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
UA = {"User-Agent": "Mozilla/5.0 (compatible; CulturaSabaudaRefresh/1.0)"}


def _ensure_col(conn: sqlite3.Connection) -> None:
    """`deplacement_now_publie` : ce qui a été RÉELLEMENT envoyé à WordPress.

    Sans elle, on ne saurait pas distinguer « la valeur n'a pas bougé » de « on ne sait
    pas », et il faudrait tout republier chaque jour. NULL compte comme « jamais publié »,
    donc la fiche sera poussée au premier passage — le rattrapage est voulu, pas subi.
    """
    try:
        conn.execute("ALTER TABLE events_raw ADD COLUMN deplacement_now_publie TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass


def _propager_score_detail(conn: sqlite3.Connection, apply: bool) -> list[tuple[int, str]]:
    """Donne aux traductions le `llm_score_detail` de leur fiche d'origine.

    L'évaluateur ne tourne jamais sur une traduction (et ne doit pas : ce serait re-payer
    un appel LLM pour re-juger le même événement dans une autre langue). Sans copie, la
    version italienne d'un événement n'a donc AUCUN score de déplacement — pas « zéro »,
    mais « pas mesuré », ce qui la fait sortir de la section par la porte de service.

    Copie, et non recalcul : c'est le MÊME événement. La justification reste rédigée en
    français, ce qui ne gêne pas — seul le champ `points` est lu pour le tri, et le
    back-office affiche ces notes à un lecteur francophone.
    """
    manquantes = conn.execute(
        "SELECT t.id, o.llm_score_detail FROM events_raw t "
        "JOIN events_raw o ON o.id = t.translation_of "
        "WHERE t.translation_of IS NOT NULL "
        "  AND (t.llm_score_detail IS NULL OR t.llm_score_detail = '') "
        "  AND o.llm_score_detail IS NOT NULL AND o.llm_score_detail != ''"
    ).fetchall()
    if apply:
        for tid, detail in manquantes:
            conn.execute("UPDATE events_raw SET llm_score_detail=? WHERE id=?", (detail, tid))
        conn.commit()
    return [(int(t), d) for t, d in manquantes]


def _etat(wp_url: str, post_id: int) -> str:
    """'public' | 'non_public' | 'inexistant' | 'indetermine' — cf. reconcile_wp_deleted.

    Interrogation PAR NUMÉRO, jamais par collection : The Events Calendar exclut les
    événements passés de ses listes REST, et ce script travaille justement sur des fiches
    qui viennent de passer. Une liste ne prouverait donc rien (règle 2).
    """
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


def _valeur(ev: dict, auj: date) -> str:
    """La méta telle qu'elle sera écrite : chaîne du score, ou '' si la fiche n'a plus sa
    place dans la section. '' et non '0' — un événement passé doit SORTIR du classement,
    pas s'y ranger dernier (c'est la même distinction que None ≠ 0 dans deplacement_now).
    """
    v = deplacement_now(ev, aujourdhui=auj)
    return "" if v is None else str(v)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Recalcule as_deplacement_now et republie les fiches dont il a changé.")
    p.add_argument("--apply", action="store_true", help="Écrit et republie (sinon dry-run).")
    p.add_argument("--cap", type=int, default=200,
                   help="Nombre maximum de republications par passage (défaut 200).")
    p.add_argument("--ids", nargs="*", type=int, help="Restreint à ces ids locaux.")
    args = p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    if not wp_url:
        log.error("WP_AS_URL manquant — impossible de vérifier l'état des posts.")
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_col(conn)

    heritees = _propager_score_detail(conn, args.apply)
    if heritees:
        verbe = "reçoivent" if args.apply else "recevraient"
        print(f"\n{len(heritees)} traduction(s) {verbe} le llm_score_detail de leur original.")

    sql = ("SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as, 0) > 0 "
           "AND wp_deleted_at IS NULL")
    params: list = []
    if args.ids:
        sql += f" AND id IN ({','.join('?' * len(args.ids))})"
        params = list(args.ids)
    lignes = [dict(r) for r in conn.execute(sql, params)]

    # En dry-run, l'héritage n'a pas été ÉCRIT : sans cette reprise en mémoire, l'aperçu
    # annoncerait « hors section » pour des traductions qui vaudront 11 dès l'application.
    # Un aperçu faux est pire qu'un aperçu absent — c'est sur sa foi qu'on lance --apply.
    if not args.apply and heritees:
        détails = dict(heritees)
        for ev in lignes:
            if ev["id"] in détails:
                ev["llm_score_detail"] = détails[ev["id"]]

    auj = date.today()
    changees = []
    for ev in lignes:
        avant = ev.get("deplacement_now_publie")
        apres = _valeur(ev, auj)
        # NULL ≠ '' : « jamais publié » n'est pas « publié vide ». Sans cette distinction,
        # le rattrapage du premier passage n'aurait pas lieu pour les fiches hors section.
        if avant is not None and avant == apres:
            continue
        changees.append({"ev": ev, "avant": avant, "apres": apres})

    print(f"\n{len(lignes)} fiche(s) liées à un post, {len(changees)} dont la valeur a changé.\n")
    for c in changees[:args.cap]:
        av = "—" if c["avant"] is None else (c["avant"] or "(hors section)")
        ap = c["apres"] or "(hors section)"
        print(f"  [{c['ev']['id']:>5}] WP#{c['ev']['wp_post_id_as']:<6} {av:>14} → {ap:<14} "
              f"{(c['ev'].get('title') or '')[:45]}")
    if len(changees) > args.cap:
        # Un plafond qui tronque en silence se lit comme « tout est traité » (règle 6).
        print(f"\n  … {len(changees) - args.cap} au-delà du plafond --cap, reportées au "
              f"prochain passage.")

    if not args.apply:
        print("\nDry-run — rien n'a été écrit. Ajouter --apply pour appliquer.\n")
        conn.close()
        return 0

    from scripts.publisher_as import publish_to_as  # import tardif : le dry-run n'a pas
                                                    # besoin des identifiants WordPress.
    pousse = 0
    par_etat: dict[str, list[int]] = {}
    for c in changees[:args.cap]:
        ev = c["ev"]
        etat = _etat(wp_url, int(ev["wp_post_id_as"]))
        if etat != "public":
            # RÈGLE 1 : la base croyait ces posts publiés. Republier un post corbeillé le
            # ressusciterait — on le signale et on n'y touche pas. On n'enregistre pas non
            # plus la valeur : la fiche restera candidate tant que son post n'est pas
            # revenu en ligne, et c'est ce qu'on veut.
            par_etat.setdefault(etat, []).append(ev["id"])
            continue
        wp_id, _, _ = publish_to_as(ev, skip_media=True)
        if not wp_id:
            par_etat.setdefault("echec_publication", []).append(ev["id"])
            continue
        conn.execute("UPDATE events_raw SET deplacement_now_publie=? WHERE id=?",
                     (c["apres"], ev["id"]))
        pousse += 1
    conn.commit()

    # RECOMPTER EN BASE plutôt qu'annoncer la longueur d'une liste (règle 6).
    restant = 0
    for ev in [dict(r) for r in conn.execute(sql, params)]:
        if (ev.get("deplacement_now_publie")) != _valeur(ev, auj):
            restant += 1
    conn.close()

    print(f"\n✅ {pousse} fiche(s) republiée(s), {restant} encore à jour à faire.")
    for etat, ids in sorted(par_etat.items()):
        print(f"   ⚠️  {len(ids)} en état '{etat}' — non poussées : {ids[:12]}"
              + (" …" if len(ids) > 12 else ""))
    if par_etat.get("non_public"):
        print("   → ces posts sont à la CORBEILLE alors que la base les croit publiés "
              "(règle 1).\n     Voir scripts/reconcile_wp_deleted.")
    log.info("Rafraîchissement : %d republiée(s), %d restantes, %s le %s",
             pousse, restant, {k: len(v) for k, v in par_etat.items()},
             datetime.now().isoformat(timespec="seconds"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
