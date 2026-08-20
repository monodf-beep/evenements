#!/usr/bin/env python3
"""Publication EN LOT vers Agenda Sabauda (mode « masse »).

Boucle publish_to_as() sur les événements RETENUS, DATÉS et À VENIR. ⚠️ CORRIGÉ
2026-07-31 : contrairement à ce que disait cette docstring, le payload envoyé ne fixe
PAS de "status" → cs-publish.php applique son défaut (`'publish'`, cf. deploy/wordpress/
cs-publish.php) : les événements partent EN LIGNE PUBLIQUE immédiatement, PAS en
brouillon. Aucune relecture humaine n'a lieu entre l'écriture (enrich.py) et la mise en
ligne dans ce chemin — s'appuie entièrement sur les garde-fous en amont (eventness,
complétude, panel de relecture dans enrich.py) pour la qualité.

Principes :
  - RETENU      : statut IN ('evaluated','published_cs','published_sub'), non-doublon.
  - DATÉ        : date_event_start non vide (sinon TEC daterait « aujourd'hui »).
  - À VENIR     : fin (ou début) >= aujourd'hui — on n'inonde pas l'agenda de passé.
  - RADAR       : une fiche d'origine radar (presse / Google News) n'est publiée QUE si
                  une page officielle a été résolue pour elle (cf. utils/radar.py). Sinon
                  elle est RETENUE — jamais supprimée, jamais rejetée — et repartira dès
                  qu'un run d'enrichissement aura trouvé sa page. Levier : --allow-radar.
  - IDEMPOTENT  : on saute ceux déjà sur l'agenda (wp_post_id_as), sauf --update.
  - BORNÉ       : --cap limite le nombre par run ; --delay espace les envois (OVH mutualisé).
  - On enregistre wp_post_id_as + published_as_date, SANS toucher au statut éditorial
    (la présence sur l'agenda est tracée par wp_post_id_as, pas par le statut).

Exemples :
  .venv/bin/python3 -m scripts.publish_batch_as --dry-run              # voir la sélection
  .venv/bin/python3 -m scripts.publish_batch_as --cap 30               # publier 30 brouillons
  .venv/bin/python3 -m scripts.publish_batch_as --min-score 5 --cap 100
"""
from __future__ import annotations
import argparse
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
from utils import completeness as comp
from utils import radar
from utils.sources import is_excluded_event, load_excluded_events_filter
from utils import saison
from utils import substance
from scripts.perimetre import ville_hors_perimetre
from scripts.publisher import build_post
from scripts.publisher_as import publish_to_as, wp_site_joignable

log = get_logger("publish_batch_as")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _select(conn, args, today: str):
    if args.ids:
        # Ciblage PRÉCIS (ex. republier après un correctif de contenu, cf.
        # scripts/audit_bad_sources.py) : ignore les filtres de sélection habituels,
        # republie ces ids tels quels (déjà publiés ou non).
        ph = ",".join("?" * len(args.ids))
        return conn.execute(
            f"SELECT * FROM events_raw WHERE id IN ({ph})", args.ids).fetchall()
    where = [
        "statut IN ('evaluated','published_cs','published_sub')",
        "duplicate_of IS NULL",
        "COALESCE(date_event_start,'') <> ''",                 # daté
    ]
    params: list = []
    if not args.include_past:
        where.append("COALESCE(date_event_end, date_event_start) >= ?")
        params.append(today)
    if not args.update:
        where.append("COALESCE(wp_post_id_as,0) = 0")          # pas déjà sur l'agenda
    if args.min_score is not None:
        where.append("COALESCE(llm_score,0) >= ?")
        params.append(args.min_score)
    sql = (f"SELECT * FROM events_raw WHERE {' AND '.join(where)} "
           f"ORDER BY date_event_start ASC LIMIT ?")
    params.append(args.cap)
    return conn.execute(sql, params).fetchall()


def _porte_radar(conn, rows: list[dict], allow_radar: bool) -> tuple[list[dict], list[tuple]]:
    """VERROU « radar = DÉTECTION seule » (config/sources.txt, en-tête du tier radar).

    POURQUOI ICI, ET NULLE PART AILLEURS
    ------------------------------------
    Le contrat est déclaré depuis toujours et n'était appliqué QUE côté crédit/lien
    (publisher_as l.148-150 : on ne cite pas le journal). Rien n'empêchait une fiche
    née d'un article de presse de devenir un événement publié : « Chambéry. Cirque,
    danse, théâtre, déambulations : ce qu'il faut savoir » → WP#1097, « Annecy.
    Défilé, concert, feu d'artifice, animations » → WP#1105, plus des faits divers
    du Dauphiné (collisions, incendies), des comptes-rendus de conseil municipal et
    des revues de presse.

    Le verrou porte sur la PUBLICATION, jamais sur la collecte : on continue de
    scraper les radars, c'est toute leur utilité (détecter, puis dédoublonner vers
    la fiche officielle — dedupe.py:TIER_RANK met radar à 0, il ne gagne jamais un
    groupe contre une source officielle). Il ne peut pas non plus vivre dans
    enrich.py : c'est justement enrich qui TENTE la résolution vers la page
    officielle (fetch_official_material) — avant lui, on ne sait pas encore si elle
    aboutira.

    RIEN N'EST SUPPRIMÉ NI REJETÉ : la fiche reste en base, telle quelle, avec son
    statut. Réversible d'un flag : --allow-radar.

    ⚠️ MAIS LA RÉTENTION EST DÉFINITIVE SANS GESTE — et il faut le dire, parce que
    l'inverse serait rassurant et faux. Une fiche retenue ici est DÉJÀ enrichie, or
    `scripts/enrich.py::select_events` (l.1155) n'auto-sélectionne que les fiches dont
    `enrich_status` est vide. Aucun run automatique ne la reprendra donc JAMAIS : elle
    ne « repartira » pas toute seule le jour où sa page officielle deviendrait
    trouvable. Le seul chemin de sortie est un ré-enrichissement PAR ID EXPLICITE :

        .venv/bin/python -m scripts.enrich <id> [<id> …]

    C'est ce que doit faire Franck pour les fiches retenues qui sont de VRAIS
    événements — l'audit du 2026-08-02 en a compté 9 en file, dont plusieurs
    manifestement légitimes (Aosta Pride, Raggamuffin Festival, Risò, un spectacle à
    La Giettaz). Le verrou dit « pas de page officielle », pas « pas un événement » :
    il ne remplace pas le jugement éditorial, il empêche de publier sans matière.

    NE S'APPLIQUE QU'AUX CRÉATIONS (`wp_post_id_as` vide). Une fiche radar DÉJÀ en
    ligne n'est pas retenue ici : bloquer sa republication ne la retirerait pas du
    site, ça y figerait seulement une version plus ancienne — on la signale, et son
    retrait éventuel reste une décision explicite (voir scripts/audit_radar_published.py).
    """
    if allow_radar:
        return rows, []
    kept, blocked = [], []
    for ev in rows:
        # Traduction : source_type/source_name sont hérités, mais pas url_officiel
        # (translate_events l.476-486) → on juge sur l'ancre de l'ORIGINAL.
        parent = None
        tof = ev.get("translation_of") or 0
        if tof and radar.is_radar(ev):
            row = conn.execute("SELECT * FROM events_raw WHERE id=?", (tof,)).fetchone()
            parent = dict(row) if row else None
        reason = radar.publication_block_reason(ev, parent)
        if reason and (ev.get("wp_post_id_as") or 0) > 0:
            log.warning("[%s] fiche RADAR non résolue DÉJÀ en ligne (WP#%s) — republiée "
                        "quand même (bloquer figerait une version plus ancienne) : %s",
                        ev.get("id"), ev.get("wp_post_id_as"), (ev.get("title") or "")[:60])
            reason = None
        (blocked if reason else kept).append((ev, reason) if reason else ev)
    return kept, blocked


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Publication en lot vers Agenda Sabauda.")
    parser.add_argument("--cap", type=int, default=50, help="Nombre max d'événements par run.")
    parser.add_argument("--ids", type=int, nargs="+", default=None,
                        help="Ne republie que ces ids précis (ignore statut/date/score, "
                             "republie même si déjà publiés). Ex. après un correctif de "
                             "contenu — cf. scripts/audit_bad_sources.py.")
    parser.add_argument("--min-score", type=int, default=None,
                        help="Score minimum (défaut : aucun seuil — toute la masse retenue).")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Pause (s) entre deux envois, pour ménager l'hébergement.")
    parser.add_argument("--update", action="store_true",
                        help="Réactualiser aussi les événements déjà sur l'agenda.")
    parser.add_argument("--include-past", action="store_true",
                        help="Inclure les événements déjà terminés (déconseillé).")
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="Publier MÊME les événements incomplets (contourne la porte "
                             "qualité). Par défaut, seuls les événements COMPLETS partent.")
    parser.add_argument("--allow-radar", action="store_true",
                        help="Publier MÊME les fiches d'origine radar (presse / Google News) "
                             "dont aucune page officielle n'a été résolue. Par défaut elles "
                             "sont RETENUES (jamais supprimées) : le radar sert à DÉTECTER, "
                             "pas à publier (config/sources.txt, tier radar).")
    parser.add_argument("--allow-early", action="store_true",
                        help="Publier MÊME les événements hors de leur fenêtre de "
                             "publication (docs/TEMPS_FORTS.md). Par défaut, un "
                             "événement à plus de 90 jours (150 pour un temps fort "
                             "nommé, config/temps_forts.json) est RETENU — le "
                             "calendrier le reproposera de lui-même en approchant.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Lister la sélection sans rien publier.")
    parser.add_argument("--skip-media", action="store_true",
                        help="Ne retéléverse AUCUNE image (texte + méta seuls). Utile pour "
                             "une passe --update en masse qui ne fait que resynchroniser les "
                             "méta as_* (ex. as_enrich_status, ajouté après coup) sur des "
                             "événements déjà publiés, sans marteler la médiathèque.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")

    # ── SONDE AVANT LE LOT (2026-08-18) ─────────────────────────────────────────────────
    # Pendant la panne réseau, chaque fiche attendait 60 s avant d'abandonner : sur 173
    # fiches, presque trois heures de timeouts, plus des vignettes générées et téléversées
    # dans le vide. Le lot annonçait ensuite des « échecs » un par un, ce qui se lit comme
    # un problème de données alors que c'est un problème de tuyau.
    # Une seule question, posée une seule fois : le site répond-il ? Sinon on ne tente
    # rien. Aucune fiche n'est marquée, aucun état n'est posé — elles repassent au lot
    # suivant exactement comme elles sont.
    if not args.dry_run and not wp_site_joignable():
        log.error("Site injoignable depuis cette machine — AUCUNE publication tentée. "
                  "Rien n'a été marqué : le lot repassera à l'identique une fois le site "
                  "joignable. (Voir docs/PANNE_OVH_2026-08-18.md.)")
        return 0
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in _select(conn, args, today)]

    # PORTE QUALITÉ : seuls les événements COMPLETS partent en brouillon (les
    # incomplets restent dans le dashboard, à charge de l'agent d'auto-complétion).
    # cf. utils/completeness.py + scripts/autocomplete.py. Ids EXPLICITES (--ids) : la
    # décision de republier est déjà prise (ex. correctif de contenu), on ne re-filtre pas.
    skipped = []
    if not args.allow_incomplete and not args.ids:
        kept = []
        for ev in rows:
            (kept if comp.is_complete(ev) else skipped).append(ev)
        rows = kept

    # VERROU RADAR — s'applique AUSSI aux --ids, contrairement à la porte qualité
    # ci-dessus. Raison : --ids est passé sans aucun humain dans la boucle par
    # scripts/daily_batch.py (seul chemin non supervisé qui met des fiches EN LIGNE,
    # cf. sa docstring _porte_publication). L'exception « la décision est déjà prise
    # par un humain » ne tient donc pas ici ; l'humain qui republie sciemment une
    # fiche radar a --allow-radar pour le dire.
    rows, radar_blocked = _porte_radar(conn, rows, args.allow_radar)

    # PORTILLON ÉDITORIAL — dernier filet avant la mise en ligne (2026-08-05).
    # L'évaluateur applique déjà config/excluded_event_keywords.txt, mais SEULEMENT aux
    # fiches encore `pending` : une règle ajoutée aujourd'hui ne dit rien des milliers de
    # fiches DÉJÀ évaluées, dont certaines sont en file de publication. Le 2026-08-05,
    # quatre salons/afterworks B2B étaient concernés, deux en ligne et deux en file —
    # dont un que le premier audit n'avait pas vu. audit_excluded_events les rattrape,
    # mais il ne tourne que le dimanche : entre deux passages, une fiche redevenue
    # publiable partirait en ligne et attendrait cinq jours. Ici, elle ne part pas.
    # S'applique AUSSI aux --ids, pour la même raison que le verrou radar : daily_batch
    # les passe sans humain dans la boucle. Coût nul (aucun appel LLM), et RIEN n'est
    # écrit : la fiche est seulement retenue, son statut ne bouge pas.
    exclusions = load_excluded_events_filter()
    exclus = [ev for ev in rows
              if is_excluded_event(ev.get("title", ""), ev.get("description", ""), exclusions,
                                   url=ev.get("url_source", ""))]
    if exclus:
        ids_exclus = {ev.get("id") for ev in exclus}
        rows = [ev for ev in rows if ev.get("id") not in ids_exclus]
        for ev in exclus:
            log.warning("[%s] RETENU : exclu par règle éditoriale (config/"
                        "excluded_event_keywords.txt) — « %s »",
                        ev.get("id"), (ev.get("title") or "")[:60])
        log.warning("%d fiche(s) retenue(s) par règle éditoriale. Pour les SORTIR de la "
                    "file (statut rejected) : .venv/bin/python -m "
                    "scripts.audit_excluded_events --apply", len(exclus))

    # PORTILLON DE SUBSTANCE (2026-08-05, le soir du refus AdSense « contenu à faible
    # valeur informative »). 59 fiches publiées portaient moins de cent mots à elles.
    # Une fiche de cent mots ne dit rien qu'un annuaire ne dise déjà : elle coûte une URL
    # indexable et n'offre rien au lecteur.
    #
    # NE BLOQUE QUE LES CRÉATIONS, exactement comme le verrou radar et pour la même
    # raison, écrite plus haut : retenir la republication d'une fiche DÉJÀ en ligne ne la
    # retirerait pas du site, ça y figerait une version plus ancienne. Une fiche maigre
    # déjà publiée qu'on vient d'enrichir DOIT pouvoir repartir — c'est même le seul
    # moyen de la réparer.
    #
    # On mesure l'article rendu par build_post, pas la colonne `description` : c'est ce
    # que le lecteur reçoit. Coût nul, aucun appel LLM, aucune écriture.
    plancher = substance.plancher()
    maigres, sous_surveillance = [], 0
    for ev in rows:
        n = substance.mots_publies(ev, build_post)
        if n < plancher and not (ev.get("wp_post_id_as") or 0):
            maigres.append((ev, n))
        elif n < substance.BANDE_MAIGRE:
            sous_surveillance += 1
    if maigres:
        ids_maigres = {ev.get("id") for ev, _ in maigres}
        rows = [ev for ev in rows if ev.get("id") not in ids_maigres]
        for ev, n in maigres:
            log.warning("[%s] RETENU : %d mot(s) publiés, plancher %d — « %s »",
                        ev.get("id"), n, plancher, (ev.get("title") or "")[:55])
        log.warning("%d fiche(s) retenue(s) faute de substance. Les enrichir (scripts."
                    "enrich <ids>) puis relancer ; ou remonter le plancher avec "
                    "PUBLISH_MIN_MOTS.", len(maigres))
    if sous_surveillance:
        # Pas un blocage : une traîne qu'on veut voir plutôt que d'ignorer.
        log.info("%d fiche(s) entre %d et %d mots — publiables, mais maigres.",
                 sous_surveillance, plancher, substance.BANDE_MAIGRE)

    # PORTILLON PÉRIMÈTRE — même famille de trou, même jour. L'arrondissement de Grasse
    # est hors catalogue (charte §2), et purge_out_of_zone le fait respecter… le
    # dimanche. Or sa propre docstring nomme le cas qui lui échappe : la `ville` est
    # souvent renseignée APRÈS l'évaluation, par venues.py ou l'auto-complétion du
    # back-office. Une fiche de Cannes datée mardi part donc en ligne mercredi et attend
    # la purge suivante. Le contrôle coûte une comparaison de chaînes sur le seul champ
    # `ville` (jamais le texte libre : « Vence » ⊂ « Provence », cf. perimetre.py).
    hors = [ev for ev in rows if ville_hors_perimetre(ev.get("ville", ""))]
    if hors:
        ids_hors = {ev.get("id") for ev in hors}
        rows = [ev for ev in rows if ev.get("id") not in ids_hors]
        for ev in hors:
            log.warning("[%s] RETENU : %s est dans l'arrondissement de Grasse, hors "
                        "périmètre (charte §2) — « %s »",
                        ev.get("id"), ev.get("ville"), (ev.get("title") or "")[:60])
        log.warning("%d fiche(s) retenue(s) hors périmètre. Pour les SORTIR de la file : "
                    ".venv/bin/python scripts/purge_out_of_zone.py --apply", len(hors))

    # PORTILLON « LE JUSTE TEMPS » (2026-08-05, docs/TEMPS_FORTS.md). CORRIGÉ le
    # jour même : la première version imposait une fenêtre de 90 jours à TOUT
    # événement daté — faux. Franck : « je n'ai pas demandé les 90 jours pour Nice
    # Jazz, Carnaval de Nice… ça peut être plus loin. » Le vrai problème n'est pas
    # la distance dans le temps, c'est le DÉCALAGE THÉMATIQUE (Noël en plein été) —
    # AUCUN plafond par défaut, seuls les temps forts NOMMÉS de config/
    # temps_forts.json (Noël, Halloween pour l'instant) ont une fenêtre.
    # Ce n'est PAS un état : rien n'est écrit, la fiche reste dans son statut, le
    # calendrier la rouvre tout seul en se rapprochant (docs/ETATS_TERMINAUX.md).
    # S'applique AUSSI aux --ids par défaut (même raison que les portillons
    # ci-dessus) — --allow-early dit explicitement qu'un humain a choisi de publier
    # en avance (ex. republication après correctif d'une fiche déjà passée par ce
    # portillon la veille).
    trop_tot = []
    if not args.allow_early:
        aujourdhui = date.fromisoformat(today)
        temps_forts = saison._charger_temps_forts()
        for ev in rows:
            debut = (ev.get("date_event_start") or "").strip()
            if not debut:
                continue  # pas de date = pas concerné, cf. règle 5 de CLAUDE.md
            fenetre = saison.fenetre_publication_jours(ev, temps_forts)
            if fenetre is None:
                continue  # pas un temps fort nommé : aucune fenêtre, jamais retenu ici
            try:
                ecart = (date.fromisoformat(debut[:10]) - aujourdhui).days
            except ValueError:
                continue
            if ecart > fenetre:
                trop_tot.append((ev, fenetre))
    if trop_tot:
        ids_trop_tot = {ev.get("id") for ev, _ in trop_tot}
        rows = [ev for ev in rows if ev.get("id") not in ids_trop_tot]
        for ev, fenetre in trop_tot:
            log.info("[%s] RETENU : pas encore sa saison (fenêtre %dj) — « %s » (%s)",
                     ev.get("id"), fenetre, (ev.get("title") or "")[:60],
                     ev.get("date_event_start"))
        log.warning("%d fiche(s) en attente de leur saison (le calendrier les "
                    "reproposera de lui-même — rien à faire).", len(trop_tot))

    log.info("Sélection : %d complet(s) à publier, %d incomplet(s) écarté(s), "
             "%d radar non résolu(s) retenu(s), %d exclu(s) par règle éditoriale, "
             "%d hors périmètre, %d en attente de leur saison (cap %d, min-score %s, %s)",
             len(rows), len(skipped), len(radar_blocked), len(exclus), len(hors),
             len(trop_tot), args.cap, args.min_score,
             "MAJ incluse" if args.update else "création seule")
    for ev, reason in radar_blocked:
        log.info("[%s] RETENU (non publié, rien supprimé) : %s | %s",
                 ev.get("id"), reason, (ev.get("title") or "")[:60])
    if radar_blocked:
        # La sortie de rétention n'est PAS automatique (cf. _porte_radar) : on donne la
        # commande, sinon ces fiches restent bloquées en silence pour toujours.
        log.info("Pour en débloquer une qui est un VRAI événement, ré-enrichir par id "
                 "(résout la page officielle) : .venv/bin/python -m scripts.enrich %s",
                 " ".join(str(ev.get("id")) for ev, _ in radar_blocked))

    if args.dry_run:
        for r in rows:
            lieu = r.get("lieu") or "—"
            print(f"  [{r['id']}] {r['date_event_start']} · {(r['title'] or '')[:60]:60} "
                  f"· score={r['llm_score']} · lieu={lieu}")
        for ev in skipped:
            print(f"  ⤷ ÉCARTÉ [{ev['id']}] {(ev.get('title') or '')[:55]:55} "
                  f"· manque : {', '.join(comp.missing_labels(ev))}")
        for ev, reason in radar_blocked:
            print(f"  ⤷ RADAR   [{ev['id']}] {(ev.get('title') or '')[:55]:55} · {reason}")
        print(f"\n{len(rows)} publié(s) / {len(skipped)} incomplet(s) / "
              f"{len(radar_blocked)} radar retenu(s) (dry-run — rien envoyé).")
        conn.close()
        return 0

    ok = fail = 0
    refuses = 0
    for i, r in enumerate(rows, 1):
        event = dict(r)
        # ══ GARDE-FOU ULTIME : jamais de CRÉATION sans date ══════════════════════
        # Incident du 2026-08-02, 22h24. Une republication ciblée par --ids a CRÉÉ le
        # post WP#6959 « Peluches, textes, photos… » avec start='' end='' venue=None
        # img=False. publisher_as a bien écrit « Événement sans date ISO exploitable »
        # dans le log… puis l'a publié quand même. Sans date, The Events Calendar date
        # l'événement du JOUR DE PUBLICATION : la fiche annonçait une exposition à la
        # mauvaise date, nue, sur le site public.
        #
        # `--ids` désactive délibérément la porte de complétude — c'est légitime pour
        # REPUBLIER une fiche déjà en ligne après un correctif de contenu, où la
        # décision est prise par un humain. Ça ne l'est JAMAIS pour créer un post
        # public neuf : personne ne décide sciemment de publier un événement sans date.
        # Le contournement est donc restreint à ce qu'il devait couvrir.
        #
        # Exception maintenue : un événement RÉCURRENT n'a légitimement pas de date
        # unique (utils/completeness.is_recurring) — sa date est une note renvoyant à
        # la source. Il continue de passer.
        cree = not (event.get("wp_post_id_as") or 0) > 0
        sans_date = not (event.get("date_event_start") or "").strip()
        if cree and sans_date and not comp.is_recurring(event):
            refuses += 1
            log.warning("[%s] CRÉATION REFUSÉE — aucune date : TEC la daterait du jour "
                        "de publication. Datez-la (scripts/dates.py) puis relancez. « %s »",
                        event.get("id"), (event.get("title") or "")[:60])
            continue
        # --skip-media ne doit JAMAIS priver une CRÉATION de sa photo (contrairement à un
        # --update sur un post déjà en ligne, où l'image existante est de toute façon
        # conservée) : une fiche encore jamais publiée n'a rien à "conserver". Bug
        # 2026-07-31 : une passe --update --skip-media en masse (sans --ids) a élargi la
        # sélection à des événements jamais publiés, créés sans photo (repli bannière
        # générique côté WP, pas cassé — mais pas voulu).
        skip = args.skip_media and (event.get("wp_post_id_as") or 0) > 0
        wp_id, permalink, raw_url = publish_to_as(event, skip_media=skip)
        if wp_id:
            conn.execute(
                # `wp_deleted_at=NULL` : la fiche vient d'être (re)mise en ligne, le
                # constat « post plus public » posé par reconcile_wp_deleted ne vaut
                # plus. Sans cet effacement, une fiche republiée restait marquée hors
                # ligne et scripts/site_audit.py cessait DÉFINITIVEMENT de la relire
                # (il exclut wp_deleted_at) — en ligne, mais plus jamais surveillée.
                # Seul reconcile savait déshorodater, et aucun cron ne le lance.
                "UPDATE events_raw SET wp_post_id_as=?, wp_permalink_as=?, "
                "wp_raw_image_url_as=?, published_as_date=datetime('now'), "
                "wp_deleted_at=NULL WHERE id=?",
                (wp_id, permalink, raw_url, event["id"]))
            conn.commit()
            ok += 1
        else:
            fail += 1
            log.warning("Échec pour id=%s : %s", event["id"], (event.get("title") or "")[:60])
        if i % 10 == 0 or i == len(rows):
            log.info("Progression : %d/%d (%d ok, %d échec)", i, len(rows), ok, fail)
        if args.delay and i < len(rows):
            time.sleep(args.delay)

    conn.close()
    log.info("=== Lot Agenda Sabauda : %d publié(s), %d échec(s), %d création(s) refusée(s) "
             "faute de date ===", ok, fail, refuses)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
