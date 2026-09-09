#!/usr/bin/env python3
"""Génération SEO EN LOT (agent).

Lance utils.seo.optimize_seo() sur les événements retenus, datés, à venir, qui n'ont pas
encore de SEO (seo_at IS NULL) : TOUTE fiche déjà EN LIGNE, et les autres à partir du
score `--min-score`. Rédigé dans la LANGUE de la fiche (fr/it), langue du résultat
contrôlée avant écriture. Stocke seo_* + seo_at. Ces champs sont ensuite poussés vers
Yoast au (re)publish (publish_batch_as).

Jusqu'au 2026-09-09 ce lot ne servait que « le haut du panier » (score ≥ 7, cap 10) et
excluait les traductions : le back-office affichait alors une colonne Yoast presque
entièrement rouge, et grise sur toutes les fiches italiennes. Détail dans `_select`.

Le run reprend aussi les fiches dont le SEO avait été calculé mais dont la republication
a ÉCHOUÉ (site injoignable, verrou de publication) : `seo_pushed_at` marque le moment où
le SEO a réellement atteint le site, et tout écart avec `seo_at` remet la fiche dans la
file. Sans ça, `seo_at IS NULL` seul les écartait pour toujours — c'est arrivé pendant la
panne du 8 au 10 août 2026.

⚠️ Coût LLM : chaque événement = un appel (Haiku). Borné (--cap), seuil (--min-score,
défaut 7, qui ne s'applique qu'aux fiches PAS ENCORE en ligne), --dry-run. Le dry-run et
le message Slack donnent la file entière (en ligne, devant nous, sans SEO), hors cap.

Exemples :
  .venv/bin/python3 -m scripts.seo_batch --dry-run
  .venv/bin/python3 -m scripts.seo_batch --cap 30            # score >= 7 par défaut
  .venv/bin/python3 -m scripts.seo_batch --min-score 8 --cap 50
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import seo as seo_mod
from utils.api_limite import est_plafond

log = get_logger("seo_batch")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _select(conn, args, today: str):
    where = [
        "statut IN ('evaluated','published_cs','published_sub')",
        "duplicate_of IS NULL",
        "COALESCE(date_event_start,'') <> ''",              # daté
        # EN LIGNE ⇒ SEO, quel que soit le score (2026-09-09). Le seuil « score ≥ 7 »
        # datait du 30/07 : « le SEO se joue sur les hubs, pas sur les fiches de masse ».
        # Mesuré sur la colonne Yoast du back-office ce jour-là : à peu près tout en
        # rouge, un seul vert sur vingt — parce qu'une fiche notée 6 publiée en juillet
        # n'entrait JAMAIS ici (règle 3 : personne ne la rouvrait). Une page publique
        # sans expression clé est une perte sèche, son score n'y change rien ; le seuil
        # ne garde donc son sens que pour ce qui n'est PAS encore en ligne. Franck :
        # « toutes les fiches doivent être traitées SEO non ? ». Coût : Haiku, ~150
        # fiches de retard, moins d'un euro en une fois.
        "(COALESCE(llm_score,0) >= ? OR COALESCE(wp_post_id_as,0) > 0)",
        # TRADUCTIONS RÉINTÉGRÉES (2026-09-09). Exclues le 02/08 parce que le prompt
        # écrivait « en français » en dur et poussait des métas françaises sur des fiches
        # italiennes en ligne ; le commentaire promettait « on rédigera en italien
        # ensuite ». Cinq semaines plus tard, les 34 fiches IT devant nous n'avaient
        # aucune expression clé (points GRIS de la colonne Yoast). utils/seo.py rédige
        # désormais dans la langue de la fiche, et la boucle ci-dessous VÉRIFIE la
        # langue de ce qui revient avant d'écrire — c'est la garantie qui manquait pour
        # lever l'exclusion.
        # ANNULÉ EXCLU (docs/EVENEMENTS_ANNULES.md, « effets de bord » du canal 1) :
        # « ne pas optimiser une annulation ». Générer un title/méta SEO pour une fiche
        # qui ne se déplacera plus n'a aucun public — et ça coûte un appel LLM pour rien.
        "annule_le IS NULL",
    ]
    params: list = [args.min_score]
    if not args.redo:
        where.append("seo_at IS NULL")                      # pas déjà fait
    if not args.include_past:
        where.append("COALESCE(date_event_end, date_event_start) >= ?")
        params.append(today)
    # Les fiches EN LIGNE d'abord (c'est là que le rouge Yoast est public), puis le
    # score, puis la date la plus proche.
    sql = (f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
           f"ORDER BY (COALESCE(wp_post_id_as,0) > 0) DESC, COALESCE(llm_score,0) DESC, "
           f"date_event_start ASC LIMIT ?")
    params.append(args.cap)
    return conn.execute(sql, params).fetchall()


def _retard(conn, today: str) -> dict:
    """Ce qui attend encore un SEO, sans cap — le PÉRIMÈTRE à côté du nombre (règle 6) :
    fiches en ligne, devant nous, sans `seo_at`, par langue. Même requête de fond que
    `_select` (statut, doublon, daté, annulé), volontairement SANS le seuil de score ni le
    cap, pour que le compteur dise la file entière et pas le lot du jour."""
    rows = conn.execute(
        "SELECT COALESCE(translated_lang,'fr') AS lang, COUNT(*) AS n FROM events_raw "
        "WHERE statut IN ('evaluated','published_cs','published_sub') AND duplicate_of IS NULL "
        "  AND COALESCE(date_event_start,'') <> '' AND annule_le IS NULL AND seo_at IS NULL "
        "  AND COALESCE(wp_post_id_as,0) > 0 "
        "  AND COALESCE(date_event_end, date_event_start) >= ? GROUP BY lang", (today,)).fetchall()
    # Indices positionnels : la seconde connexion de main() n'a pas de row_factory.
    return {r[0]: r[1] for r in rows}


# ── Le SEO calculé mais jamais arrivé sur le site ───────────────────────────────
# TROUVÉ le 2026-08-10, en conséquence directe de la panne du 8 au 10 août : pendant
# ces deux jours, WordPress répondait 500 à TOUT. Le cron de 10h30 a quand même tourné :
# l'appel LLM (Anthropic, indépendant du site) réussissait, `seo_at` était écrit, puis la
# republication échouait. Or `_select` écarte tout ce qui a `seo_at IS NOT NULL`. Résultat :
# ces fiches portent un SEO en base que Yoast n'a JAMAIS reçu, et rien ne les repêche —
# le cul-de-sac de la règle 3, fabriqué par une panne plutôt que par un refus.
#
# `seo_pushed_at` enregistre la dernière fois où le SEO a effectivement ATTEINT le site.
# La preuve retenue n'est pas la valeur de retour de publish_batch_as (qui ne rend qu'un
# code global 0/1), mais le fait que `published_as_date` de la fiche ait BOUGÉ : c'est ce
# que la publication écrit elle-même quand elle réussit, fiche par fiche.
_SEO_PUSH_CAP = 20   # bornage d'un run ; le reste repasse au run suivant


def _ensure_seo_pushed_col(conn) -> None:
    """Crée `seo_pushed_at` et fait le rattrapage initial.

    Au premier passage, toutes les lignes seraient « jamais poussées » — ce qui
    republierait des centaines de fiches d'un coup pour rien. On considère donc comme
    DÉJÀ poussé tout ce dont la dernière publication réussie est postérieure au calcul
    du SEO ; seul le reste (dont les fiches de la panne) part en rattrapage.

    ⚠️ Les deux dates ne sont pas écrites dans le même format : `datetime('now')` côté
    SQL (« 2026-08-10 08:30:00 », UTC) et `datetime.now().isoformat()` côté
    translate_events (« 2026-08-10T10:45:00 », heure locale). D'où le `replace('T',' ')`,
    et l'acceptation d'un flou de quelques heures SUR CE SEUL RATTRAPAGE : se tromper y
    coûte une republication de texte en trop, jamais une perte. Après quoi la colonne
    est écrite par ce script seul, dans un format unique."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
    if "seo_pushed_at" in cols:
        return
    conn.execute("ALTER TABLE events_raw ADD COLUMN seo_pushed_at TEXT")
    conn.execute(
        "UPDATE events_raw SET seo_pushed_at = seo_at "
        "WHERE seo_at IS NOT NULL AND published_as_date IS NOT NULL "
        "  AND replace(published_as_date,'T',' ') >= replace(seo_at,'T',' ')")
    conn.commit()
    log.info("Colonne seo_pushed_at créée (rattrapage initial appliqué).")


# La seconde condition de date fait doublon avec `seo_pushed_at` — volontairement. Une
# fiche publiée pour la PREMIÈRE fois après le calcul de son SEO a reçu ce SEO au passage
# (cs-publish.php lit `seo_*` à chaque publication), mais son `seo_pushed_at` est resté
# vide : sans ce garde-fou elle serait republiée une fois pour rien le lendemain. Vu en
# production le 2026-08-10 sur 5 fiches (4621, 4702, 3089, 4734, 1445), toutes calculées
# pendant la panne et pas encore publiées.
# Les deux dates sont comparables SANS normalisation ici : le seul format « T » de la
# base vient de translate_events, qui l'écrit sur la fiche TRADUITE — or `_select` exclut
# les traductions (translation_of), donc elles n'entrent jamais dans cette file.
_SQL_RETARD = (
    "SELECT id FROM events_raw "
    "WHERE seo_at IS NOT NULL AND wp_post_id_as IS NOT NULL "
    "  AND (seo_pushed_at IS NULL OR seo_pushed_at < seo_at) "
    "  AND (published_as_date IS NULL OR published_as_date < seo_at) "
    "  AND COALESCE(translation_of,0) = 0 "
    "  AND annule_le IS NULL AND duplicate_of IS NULL "
    "  AND COALESCE(NULLIF(date_event_end,''), NULLIF(date_event_start,''), '9999') >= ?")


def _a_repousser(conn, today: str, cap: int) -> list[int]:
    """Fiches EN LIGNE dont le SEO n'a jamais atteint le site. Règle 5 : rien de passé —
    une fiche sans date n'est pas « passée », c'est une donnée manquante, elle reste."""
    return [r[0] for r in conn.execute(
        _SQL_RETARD + " ORDER BY COALESCE(llm_score,0) DESC LIMIT ?",
        (today, cap)).fetchall()]


def _dates_publication(conn, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    return {r[0]: (r[1] or "") for r in conn.execute(
        f"SELECT id, published_as_date FROM events_raw WHERE id IN ({ph})", ids)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Génération SEO en lot (agent).")
    parser.add_argument("--cap", type=int, default=30, help="Nombre max d'événements par run.")
    parser.add_argument("--min-score", type=int, default=7, help="Score minimum (défaut 7).")
    parser.add_argument("--delay", type=float, default=1.0, help="Pause (s) entre deux appels.")
    parser.add_argument("--redo", action="store_true", help="Régénérer même si déjà fait.")
    parser.add_argument("--include-past", action="store_true", help="Inclure les événements passés.")
    parser.add_argument("--dry-run", action="store_true", help="Lister la sélection sans appeler le LLM.")
    parser.add_argument("--push-cap", type=int, default=_SEO_PUSH_CAP,
                        help=f"Nb max de SEO en retard repoussés par run (défaut {_SEO_PUSH_CAP}).")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    model = (os.getenv("ANTHROPIC_MODEL_SEO") or os.getenv("ANTHROPIC_MODEL_VISUALS")
             or "claude-haiku-4-5")
    today = date.today().isoformat()

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    _ensure_seo_pushed_col(conn)
    a_repousser = _a_repousser(conn, today, args.push_cap)
    rows = _select(conn, args, today)
    log.info("Sélection : %d événement(s) (cap %d, min-score %d, modèle %s)",
             len(rows), args.cap, args.min_score, model)

    retard = _retard(conn, today)
    if args.dry_run:
        for r in rows:
            en_ligne = f"WP#{r['wp_post_id_as']}" if r["wp_post_id_as"] else "—"
            print(f"  [{r['id']:>5} {en_ligne:>7}] score={r['llm_score']} · "
                  f"{seo_mod.langue_seo(dict(r))} · {(r['title'] or '')[:60]}")
        print(f"\n{len(rows)} événement(s) SERAIENT optimisés (dry-run — aucun appel LLM).")
        print(f"File entière (en ligne, devant nous, sans SEO, hors cap) : "
              f"{sum(retard.values())} — " + ", ".join(f"{k} {v}" for k, v in sorted(retard.items())))
        for i in a_repousser:
            print(f"  [{i}] SEO déjà calculé mais jamais arrivé sur le site → republication")
        print(f"{len(a_repousser)} fiche(s) SERAIENT republiées (texte seul, aucun appel LLM).")
        conn.close()
        return 0

    # Clé absente : plus de génération, mais on NE SORT PAS. Les retardataires n'ont
    # besoin d'aucun LLM — leur SEO est déjà en base, il ne lui manque que le trajet
    # jusqu'au site. Sortir ici les garerait pour toute la durée de la panne de clé.
    sans_cle = not api_key
    if sans_cle:
        log.error("ANTHROPIC_API_KEY absente — aucune génération SEO ce run. Les SEO "
                  "déjà calculés et non poussés le seront quand même.")
        rows = []

    client = None
    if rows:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    ok = fail = mauvaise_langue = 0
    plafonne = False
    republish_ids = []  # déjà EN LIGNE : le nouveau SEO doit être repoussé pour être visible
    from utils.lang import detect_lang
    for i, r in enumerate(rows, 1):
        ev = dict(r)
        lang = seo_mod.langue_seo(ev)
        try:
            result = seo_mod.optimize_seo(ev, client, model, lang=lang)
        except Exception as exc:
            # UN PLAFOND N'EST PAS UNE ERREUR DE FICHE (2026-08-05, trouvé en prod : 16
            # erreurs identiques « credit balance is too low », martelées une par fiche
            # en 13 secondes — le même trou que translate_events.py avait avant sa
            # garde du matin même, jamais bouché ici). utils.seo.optimize_seo laisse
            # VOLONTAIREMENT remonter les exceptions API (sa docstring : sa seconde
            # appelante, la route Flask, les gère elle-même) — mais ce lot-ci doit
            # s'ARRÊTER sur un plafond, pas continuer à essayer les 9 fiches suivantes
            # pour rien.
            if est_plafond(exc):
                log.error("PLAFOND API atteint sur la fiche %s — lot arrêté, %d "
                         "fiche(s) non tentée(s) : %s", r["id"], len(rows) - i + 1, exc)
                plafonne = True
                break
            log.warning("SEO échoué id=%s : %s", r["id"], exc)  # jamais bloquant pour une fiche
            result = None
        # CONTRÔLE DE LANGUE avant d'écrire — la garantie qui a permis de lever
        # l'exclusion des traductions (cf. _select). Même détecteur que la publication
        # (utils.lang.detect_lang), titre pesé ×3. Une méta dans la mauvaise langue ne
        # part ni en base ni sur Yoast : c'est exactement le dégât du 02/08.
        # ⚠️ Ce refus se rejoue sur la MÊME fiche au run suivant (règle 3) : il est donc
        # COMPTÉ et affiché dans le message Slack. S'il revient deux jours de suite sur
        # la même fiche, c'est le prompt qu'il faut corriger, pas attendre.
        if result and detect_lang(result["seo_title"],
                                  f"{result['seo_meta']} {result['seo_answer']}") != lang:
            log.warning("SEO id=%s rédigé dans la mauvaise langue (attendu %s) — ignoré : « %s »",
                        r["id"], lang, result["seo_title"][:60])
            mauvaise_langue += 1
            result = None
        if result:
            log.info("SEO id=%s [%s] « %s » · %s", r["id"], lang,
                     result["seo_title"][:60], result["seo_meta"][:80])
            conn.execute(
                "UPDATE events_raw SET seo_title=?, seo_meta=?, seo_answer=?, seo_faq=?, "
                "seo_keyphrase=?, seo_slug=?, seo_tags=?, seo_model=?, seo_at=datetime('now') "
                "WHERE id=?",
                (result["seo_title"], result["seo_meta"], result["seo_answer"],
                 json.dumps(result["seo_faq"], ensure_ascii=False),
                 result["seo_keyphrase"], result["seo_slug"],
                 json.dumps(result["seo_tags"], ensure_ascii=False), model, r["id"]))
            conn.commit()
            ok += 1
            if r["wp_post_id_as"]:
                republish_ids.append(r["id"])
        else:
            fail += 1
        if i % 10 == 0 or i == len(rows):
            log.info("Progression : %d/%d (%d ok, %d échec)", i, len(rows), ok, fail)
        if args.delay and i < len(rows):
            time.sleep(args.delay)

    # Le SEO stocké en base ne sert à rien tant qu'il n'est pas repoussé (cs-publish.php
    # ne lit `seo_*` qu'au (re)publish) : sans ça, "optimisé" en base mais invisible sur
    # Yoast jusqu'au prochain republish, potentiellement jamais si l'événement est déjà en
    # ligne et ne bouge plus. --skip-media : texte/méta seuls, on ne retouche pas la photo.
    #
    # On y joint les RETARDATAIRES (SEO calculé lors d'un run précédent dont la
    # republication a échoué — cf. _ensure_seo_pushed_col). Aucun appel LLM : ces fiches
    # ont déjà leur SEO en base, il ne leur manque que le trajet jusqu'au site.
    a_pousser = list(dict.fromkeys(republish_ids + a_repousser))
    avant = _dates_publication(conn, a_pousser)
    conn.close()

    if a_pousser:
        from scripts.publish_batch_as import main as publish_main
        publish_main(["--ids", *[str(i) for i in a_pousser], "--skip-media"])

    # RÈGLE 6 : ne pas compter ce qu'on a demandé, recompter ce qui s'est produit. Preuve
    # fiche par fiche : `published_as_date` n'est réécrit que par une publication RÉUSSIE.
    # Ce qui n'a pas bougé garde son `seo_pushed_at` en retard et se represente au run
    # suivant — c'est le rouvreur, et il ne dépend de personne.
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apres = _dates_publication(conn, a_pousser)
    arrives = [i for i in a_pousser if apres.get(i) and apres.get(i) != avant.get(i)]
    if arrives:
        ph = ",".join("?" * len(arrives))
        conn.execute(f"UPDATE events_raw SET seo_pushed_at = seo_at WHERE id IN ({ph})",
                     arrives)
        conn.commit()
    # Le retard qui subsiste, cap compris : une file qu'on ne compte pas est une file
    # qu'on découvre des semaines plus tard. On la recompte avec la MÊME requête que la
    # sélection — deux formulations divergent tôt ou tard, et c'est le compteur qui ment.
    reste = [r[0] for r in conn.execute(_SQL_RETARD, (today,)).fetchall()]
    retard = _retard(conn, today)
    conn.close()

    from utils import slack
    from utils import pipeline_status
    msg = (f"🔍 *SEO quotidien* — {ok} optimisé(s) "
           f"({len(arrives)} arrivé(s) sur le site), {fail} échec(s)")
    if mauvaise_langue:
        msg += (f"\n🔴 {mauvaise_langue} SEO rédigé(s) dans la mauvaise langue, NON écrits "
                f"(ils repassent demain ; si ça se répète, c'est le prompt de utils/seo.py).")
    if retard:
        # Le périmètre à côté du nombre : en ligne, devant nous, sans SEO, hors cap.
        msg += (f"\n📋 Encore sans SEO (en ligne, devant nous) : {sum(retard.values())} — "
                + ", ".join(f"{k} {v}" for k, v in sorted(retard.items())))
    if a_repousser:
        msg += f"\n↩️ {len(a_repousser)} SEO en retard repoussé(s) (aucun appel LLM)."
    if reste:
        # Une alerte qui ne dit pas QUOI FAIRE ne sert à rien (Franck, 2026-08-09 : « soit
        # elle est compréhensible et je fais quelque chose, soit on l'enlève »). Une fiche
        # qui reste ici a été refusée par un portillon de publication, pas par le réseau :
        # la commande ci-dessous en donne la raison, fiche par fiche.
        ids = " ".join(str(i) for i in reste[:10])
        msg += (f"\n⏳ {len(reste)} fiche(s) ont un SEO que le site n'a pas reçu. Elles "
                f"repassent demain, mais si ça dure c'est un portillon qui les retient. "
                f"La raison :\n`.venv/bin/python -m scripts.publish_batch_as --ids {ids} "
                f"--skip-media --dry-run`")
    if plafonne:
        msg += "\n🔴 Plafond API atteint — lot arrêté, fiches restantes non tentées."
    slack.notify(msg)
    pipeline_status.record_run("seo_batch", ok=ok, error=fail, summary=msg)
    log.info("=== Lot SEO : %d optimisé(s), %d échec(s), %d mauvaise langue, %d arrivé(s) "
             "sur le site, %d encore en retard, %d en ligne sans SEO ===",
             ok, fail, mauvaise_langue, len(arrives), len(reste), sum(retard.values()))
    if plafonne:
        log.error("Le lot s'est arrêté sur un plafond API. Relever le plafond ou "
                  "recharger le crédit (console Anthropic), puis relancer.")
        return 3
    return 0 if (fail == 0 and not sans_cle) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
