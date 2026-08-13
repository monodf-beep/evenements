#!/usr/bin/env python3
"""Orchestre EN UN SEUL CRON HEBDO tout le nettoyage RÉVERSIBLE et DÉTERMINISTE du
catalogue — pour que Franck n'ait plus à lancer chaque script de nettoyage à la main.

Chaque étape ci-dessous répond aux deux critères qui la rendent sûre à automatiser :
  1. RÉVERSIBLE — corbeille WordPress (jamais suppression définitive) ou statut →
     'rejected' (une re-classification, pas une perte de donnée). AUCUN `--hard` ici.
  2. DÉTERMINISTE — règles fixes (regex, dates, domaines listés), zéro jugement LLM
     ambigu. Les scripts qui font appel à un LLM pour DÉCIDER (pas juste détecter) sont
     volontairement absents de cette liste.

Étapes (dans cet ordre — les purges de bruit d'abord, pour ne pas polluer les audits
plus fins qui suivent) :
  1. purge_out_of_zone   --apply           (hors zone / passés, statut→rejected)
  2. purge_past          --execute         (retenus devenus passés, statut→rejected)
  3. purge_uncompletable --execute         (radar/sans-page incomplétables, statut→rejected)
  4. discard_uncompletable --apply         (même famille, critère complémentaire)
  5. audit_non_events    --apply           (articles de presse publiés à tort → corbeille)
  6. cleanup_as_dupes    --execute         (doublons NÉS dans WordPress → corbeille)
  6b. reconcile_catalogue --apply          (AJOUTÉ 2026-08-03 — les deux réparations que
                                            Franck a dû faire à la main ce jour-là :
                                            fiches hors périmètre restées EN LIGNE →
                                            corbeille + statut d'un seul geste ; et
                                            archivages « passé » posés sur des dates
                                            devenues à venir → statut rouvert)
  6c. reconcile_wp_deleted --apply         (AJOUTÉ 2026-08-03 — liens vers des posts
                                            disparus : horodate le constat SANS couper le
                                            lien d'un post seulement corbeillé, donc
                                            réversible ; ferme la boucle des identifiants
                                            périmés qu'aucun cron ne nettoyait)
  6d. audit_wp_ghosts                      (AJOUTÉ 2026-08-03 — LECTURE SEULE, après les
                                            réparations : ce qu'il signale encore est ce
                                            qu'aucune règle déterministe ne sait traiter,
                                            donc ce qui mérite l'œil de Franck)
  7. audit_bad_sources                     (lecture seule + republication UNE FOIS des
                                             fiches concernées, sans média et plafonnée —
                                             cf. _etape_bad_sources : le scan ne se vide
                                             jamais tout seul)
  8. image_audit                           (LLM vision, borné --limit — son propre digest
                                             Slack existe déjà, on ne le double pas)

TOUTES les étapes passent par _run_captured : une étape qui plante est signalée dans le
digest et comptée en `error`, elle n'interrompt plus la chaîne (les étapes 7 et 8 étaient
hors filet — leur échec supprimait purement et simplement le digest Slack ET l'entrée
dans l'historique pipeline_runs, donc le seul signal que le nettoyage a eu lieu).

Un seul digest Slack consolidé à la fin (sauf image_audit, qui envoie le sien).

Usage (cron) :
    .venv/bin/python -m scripts.weekly_audits
"""
from __future__ import annotations
import contextlib
import hashlib
import io
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import slack
from utils import pipeline_status

log = get_logger("weekly_audits")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _run_captured(fn, argv, logger_name: str | None = None) -> tuple[int, str]:
    """Exécute `fn(argv)` en capturant à la fois print() et le logger nommé (les scripts
    de ce dépôt utilisent l'un OU l'autre selon leur âge) — pour extraire un résumé sans
    reparser logs/*.log après coup."""
    buf = io.StringIO()
    handler = None
    if logger_name:
        handler = logging.StreamHandler(buf)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger(logger_name).addHandler(handler)
    try:
        with contextlib.redirect_stdout(buf):
            rc = fn(argv) or 0
    except Exception as exc:  # noqa: BLE001 — une étape en échec ne doit pas arrêter les autres
        log.error("Étape en échec (%s) : %s", logger_name or fn, exc)
        rc = 1
    finally:
        if handler:
            logging.getLogger(logger_name).removeHandler(handler)
    return rc, buf.getvalue()


def _tail(text: str, n: int = 3) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return " / ".join(lines[-n:]) if lines else "(rien à signaler)"


# Mémoire des republications de l'étape 7. NON versionné (état d'exécution, pas du code) :
# data/ est déjà le répertoire des données locales du VPS.
_ETAT = Path(os.getenv("WEEKLY_AUDITS_STATE", ROOT / "data" / "weekly_audits_state.json"))
# Plafond par run : borne le temps d'exécution et le martèlement de l'hébergement mutualisé
# le premier dimanche (l'arriéré peut être important). Le reste passe la semaine suivante.
BAD_SOURCES_CAP = int(os.getenv("WEEKLY_BAD_SOURCES_CAP", "25"))


def _charge_etat() -> dict:
    try:
        return json.loads(_ETAT.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return {}


def _ecrit_etat(etat: dict) -> None:
    try:
        _ETAT.parent.mkdir(parents=True, exist_ok=True)
        _ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as exc:
        log.warning("État weekly_audits non sauvegardé (%s) — republication possible en double", exc)


def _empreinte(dropped) -> str:
    """Signature des sources fautives d'une fiche : republier ne change PAS enrich_data,
    donc l'empreinte ne bouge que si une NOUVELLE mauvaise source apparaît (ré-enrichissement)."""
    return hashlib.sha1("|".join(sorted(str(d) for d in dropped)).encode("utf-8")).hexdigest()[:12]


def _etape_bad_sources(_argv=None) -> int:
    """Étape 7 — audit_bad_sources, en lecture seule, + republication des fiches concernées.

    ⚠️ CETTE ÉTAPE NE CONVERGE PAS TOUTE SEULE. `audit_bad_sources._scan` classe une fiche
    d'après `enrich_data.sources` ; la republication, elle, ne fait que RE-RENDRE le post
    (publisher.build_post re-filtre les sources à l'affichage) sans jamais toucher à
    `enrich_data`. La fiche reste donc signalée pour toujours : telle quelle, l'étape
    republiait chaque dimanche la TOTALITÉ des fiches jamais signalées, images réelles
    reversées à chaque fois dans la médiathèque — indéfiniment.

    D'où les trois bornes ici :
      • un état sur disque (id → empreinte des sources fautives) : une fiche n'est
        republiée qu'UNE fois, et à nouveau seulement si de nouvelles sources fautives
        apparaissent (ré-enrichissement) ;
      • `--skip-media` : le correctif est purement textuel, la photo en ligne est déjà
        la bonne — rien à re-téléverser ;
      • un plafond par run (BAD_SOURCES_CAP), l'arriéré s'écoulant sur plusieurs semaines.
    """
    from scripts.audit_bad_sources import _scan as scan_bad_sources
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, wp_post_id_as, url_officiel, url_source, enrich_data "
        "FROM events_raw WHERE enrich_data IS NOT NULL AND enrich_data != ''").fetchall()]
    conn.close()

    flagged = scan_bad_sources(rows)
    etat = _charge_etat()
    deja = etat.get("bad_sources_republies") or {}
    a_faire = [(f["id"], _empreinte(f.get("dropped") or []))
               for f in flagged if f.get("wp_post_id_as")]
    restants = [(i, emp) for i, emp in a_faire if deja.get(str(i)) != emp]
    lot = restants[:BAD_SOURCES_CAP]

    if not lot:
        print(f"{len(flagged)} fiche(s) repérée(s), 0 à republier "
              f"(déjà republiées lors d'un run précédent)")
        return 0

    from scripts.publish_batch_as import main as publish_main
    publish_main(["--ids", *[str(i) for i, _ in lot], "--skip-media"])
    for i, emp in lot:
        deja[str(i)] = emp
    etat["bad_sources_republies"] = deja
    _ecrit_etat(etat)

    reste = len(restants) - len(lot)
    print(f"{len(flagged)} fiche(s) repérée(s), {len(lot)} republiée(s) sans média"
          + (f", {reste} reportée(s) au run suivant (plafond {BAD_SOURCES_CAP})" if reste else ""))
    return 0


def _annules_encore_affiches(conn: sqlite3.Connection) -> list[dict]:
    """Fiches ANNULÉES (canal 1, `annule_le` posé) et encore EN LIGNE (`wp_post_id_as`).

    docs/EVENEMENTS_ANNULES.md, § « Où se voit le compte » : le digest comptait déjà les
    SUSPICIONS en attente (canaux 2/3, via audit_annulations) mais rien pour les
    annulations CONFIRMÉES par le bouton du back-office — laissé « à faire » le
    2026-08-05. LECTURE SEULE : la doctrine veut qu'une annulation reste affichée
    jusqu'à sa date, ce compte ne déclenche donc rien, il garde juste le nombre sous
    les yeux (règle 3, CLAUDE.md : tout ce qui sort une fiche d'une file doit se
    recompter quelque part).

    Uniquement les fiches encore DEVANT NOUS (règle 5, CLAUDE.md) : une annulation dont
    la date est passée relève de l'archivage normal, pas d'un compte à surveiller — même
    filtre que `scripts.reconcile_hors_ligne._devant_nous` (récurrent, ou sans date, ou
    date_event_end pas encore passée)."""
    from datetime import date as _date
    from utils.completeness import is_recurring
    today = _date.today().isoformat()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, date_event_start, date_event_end FROM events_raw "
        "WHERE annule_le IS NOT NULL AND wp_post_id_as IS NOT NULL "
        "AND duplicate_of IS NULL").fetchall()]

    def _devant_nous(ev: dict) -> bool:
        if is_recurring(ev):
            return True
        fin = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()
        return not fin or fin[:10] >= today

    return [r for r in rows if _devant_nous(r)]


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    sections: list[str] = []
    echecs: list[str] = []

    from scripts.purge_out_of_zone import main as purge_zone_main
    from scripts.purge_past import main as purge_past_main
    from scripts.purge_uncompletable import main as purge_unc_main
    from scripts.discard_uncompletable import main as discard_unc_main
    from scripts.audit_non_events import main as audit_ne_main
    from scripts.cleanup_as_dupes import main as cleanup_dupes_main
    from scripts.reconcile_catalogue import main as reconcile_cat_main
    from scripts.reconcile_wp_deleted import main as reconcile_del_main
    from scripts.audit_wp_ghosts import main as audit_ghosts_main

    # (libellé, fonction, argv, nom du logger à capturer — None = le script utilise print())
    etapes = [
        ("Hors zone / passés (purge_out_of_zone)", purge_zone_main, ["--apply"], "purge_zone"),
        ("Retenus devenus passés (purge_past)", purge_past_main, ["--execute"], "purge_past"),
        ("Incomplétables radar/sans-page (purge_uncompletable)", purge_unc_main,
         ["--execute"], "purge_uncompletable"),
        ("Incomplétables (discard_uncompletable)", discard_unc_main, ["--apply"], None),
        ("Articles de presse publiés à tort (audit_non_events)", audit_ne_main,
         ["--apply"], "audit-non-events"),
        ("Doublons nés dans WordPress (cleanup_as_dupes)", cleanup_dupes_main,
         ["--execute"], "cleanup_as_dupes"),
        # ── AJOUTÉES LE 2026-08-03 ────────────────────────────────────────────────────
        # La journée du 2026-08-03 a été faite ENTIÈREMENT À LA MAIN : 28 fiches hors
        # périmètre retirées une par une, deux archivages faux rouverts, des liens périmés
        # inventoriés. Quatre de ces cinq opérations remplissaient déjà les deux critères
        # d'automatisation posés en tête de ce fichier — réversibles et déterministes.
        # Elles n'y étaient pas pour une raison sans rapport avec la technique : chaque
        # script avait été écrit le jour d'un incident, comme réparation ponctuelle, et
        # personne ne l'avait promu ici. Le rangement existait, on n'y avait rien rangé.
        #
        # ORDRE VOULU : reconcile_catalogue AGIT (il retire des pages, il rouvre des
        # statuts), reconcile_wp_deleted CONSTATE derrière lui ce qui reste — un post
        # corbeillé par l'étape précédente a déjà perdu son wp_post_id_as, il ne sera donc
        # pas recompté. L'inverse ferait horodater des liens qu'on s'apprête à couper.
        ("Périmètre en ligne + archivages faux (reconcile_catalogue)", reconcile_cat_main,
         ["--apply"], "reconcile-catalogue"),
        # Réversible par construction : pose un HORODATAGE (« à cette date ce post n'était
        # plus public ») et GARDE wp_post_id_as, pour qu'un post restauré à la main soit
        # déshorodaté au run suivant. Ne coupe le lien que sur un post RÉELLEMENT supprimé.
        ("Liens vers des posts disparus (reconcile_wp_deleted)", reconcile_del_main,
         ["--apply"], "reconcile_wp_deleted"),
    ]
    for libelle, fn, etape_argv, logger_name in etapes:
        # `rc` était calculé puis JETÉ : une étape qui plantait (rc=1 posé par
        # _run_captured) apparaissait dans le digest comme n'importe quelle autre, avec
        # « (rien à signaler) » pour tout message. Un nettoyage hebdomadaire silencieux
        # qui ne nettoie plus est exactement le genre de panne qu'on ne découvre qu'en
        # constatant les dégâts, un mois plus tard.
        rc, out = _run_captured(fn, etape_argv, logger_name)
        marque = "" if not rc else "⚠️ ÉCHEC — "
        sections.append(f"• {libelle} : {marque}{_tail(out)}")
        if rc:
            echecs.append(libelle.split(" (")[0])

    # LECTURE SEULE, et volontairement APRÈS les réparations : ce qu'il signale encore est
    # ce qu'aucune règle déterministe ne sait traiter — donc exactement ce qui mérite le
    # coup d'œil de Franck. Placé avant les corrections, il crierait sur des écarts que la
    # chaîne s'apprête à refermer, et on apprendrait à ne plus le lire.
    rc, out = _run_captured(audit_ghosts_main, [], None)
    # PAS `_tail` ici : il prend les DERNIÈRES lignes, et celles de cet audit sont son
    # épilogue explicatif (« Réparer la BASE plutôt que le site est parfois… »). Slack
    # aurait reçu de la prose au lieu des compteurs. On va chercher les lignes de bilan,
    # qui sont au milieu et commencent toutes par un symbole de rubrique.
    compteurs = [l.strip() for l in out.splitlines()
                 if l.strip()[:1] in ("①", "②", "③", "④", "⚠")]
    sections.append("• Fiches fantômes (audit_wp_ghosts) : "
                    + (" / ".join(compteurs) if compteurs else _tail(out, 2)))
    if rc:
        echecs.append("audit_wp_ghosts")

    rc, out = _run_captured(_etape_bad_sources, [], "publish_batch_as")
    sections.append(f"• Sources non institutionnelles (audit_bad_sources) : {_tail(out, 1)}")
    if rc:
        echecs.append("audit_bad_sources")

    # Doublons EN LIGNE que la déduplication n'a jamais regardés (ajouté le 2026-08-13).
    # `dedupe` tourne à 8h sur `statut='pending'` : il trie ce qui ARRIVE. Rien ne relisait
    # le stock DÉJÀ publié, et sept titres en double dormaient dans la « bande maigre » de
    # audit_substance_published — dont « Tour de l'Avenir 2026 - Strambino Lago Serrù »,
    # deux pages à un tiret près. Lecture seule et SANS --apply, volontairement : trancher
    # entre deux pages est un arbitrage éditorial, au même titre que défusionner (CLAUDE.md).
    from scripts.verifier_doublons_publies import main as doublons_main
    rc, out = _run_captured(doublons_main, [], "verifier_doublons_publies")
    ligne = next((l.strip() for l in out.splitlines() if l.startswith("SUSPECTS")),
                 _tail(out, 1))
    sections.append(f"• Doublons EN LIGNE (verifier_doublons_publies) : {ligne}")
    if rc:
        echecs.append("verifier_doublons_publies")

    # Réparation des descriptions polluées — LE ROUVREUR QUI N'ÉTAIT BRANCHÉ NULLE PART.
    # Trouvé par le recensement du 2026-08-04 : `enrich` gare une fiche en
    # `matiere_polluee`, le tableau d'ETATS_TERMINAUX.md répond « rouvert par
    # repair_polluted_descriptions »… et ce script n'était ni dans crontab.txt ni ici.
    # « Un humain qui tape une commande n'est pas une réponse » — c'était pourtant, en
    # pratique, la seule voie. Quatrième question du recensement : un rouvreur existant
    # mais jamais lancé ne rouvre rien.
    # --apply est défendable ici parce que le script trie lui-même : il ne remplace que
    # les descriptions PROUVÉES polluées (coquille Google News), re-téléchargées depuis la
    # page source, et route les cas douteux vers un bac « à valider » que --apply ne
    # touche pas (sa ligne 274). Déterministe, borné (--cap), zéro LLM.
    from scripts.repair_polluted_descriptions import main as repair_polluted_main
    rc, out = _run_captured(repair_polluted_main, ["--apply", "--cap", "25"],
                            "repair_polluted_descriptions")
    sections.append(f"• Descriptions polluées réparées (repair_polluted) : {_tail(out, 2)}")
    if rc:
        echecs.append("repair_polluted_descriptions")

    # ── DEUX SCRIPTS ÉCRITS LE 2026-08-11 QUE PERSONNE NE LANÇAIT ──────────────────────
    # Franck, le soir : « est-ce qu'il y a des choses qu'on n'a pas terminées ? ». Le
    # recensement a trouvé quatre scripts nés dans la journée et branchés nulle part.
    # C'est l'erreur 11 du journal, refaite le jour même où je l'y inscrivais : un
    # correctif juste, testé, poussé — et jamais exécuté. Il MARCHE quand on le lance à la
    # main, donc rien ne signale qu'il ne tourne pas.
    #
    # 1) LES TRADUCTIONS ORPHELINES. `translate_events` pose deux marques d'origine ; il
    # arrive qu'une fiche n'ait plus que la seconde, et TOUS les garde-fous interrogent la
    # première. Ces fiches n'héritent donc pas des dates de leur original et peuvent
    # recevoir un article dans la mauvaise langue. Le script relit l'identifiant dans
    # l'adresse « translated:<id>:<langue> » et repose la colonne : rien d'inventé, le
    # numéro est écrit dans la fiche depuis sa création. --apply est défendable — il refuse
    # un original introuvable et refuse de fabriquer un cycle.
    from scripts.repair_lien_traduction import main as relien_main
    rc, out = _run_captured(relien_main, ["--apply"], "repair_lien_traduction")
    sections.append(f"• Traductions rebranchées sur leur original : {_tail(out, 2)}")
    if rc:
        echecs.append("repair_lien_traduction")

    # 2) LES ARTICLES QUI PARLENT AU PASSÉ. Franck, 2026-08-11 : « il faut toujours parler
    # au futur puisqu'on propose des événements qui se passent dans le futur ; là c'est
    # plutôt du journalisme, on dit ce qui s'est fait ». LECTURE SEULE, volontairement :
    # l'audit assume un faux positif sur vingt-cinq et le dit dans sa sortie. Réécrire
    # demande un jugement, et un signalement hebdomadaire suffit à ce que ça se voie.
    from scripts.audit_temps_recit import main as temps_main
    rc, out = _run_captured(temps_main, [], "audit_temps_recit")
    sections.append(f"• Articles au passé (signalement, pas verdict) : {_tail(out, 2)}")
    if rc:
        echecs.append("audit_temps_recit")

    # 3) LES LIENS OFFICIELS MORTS. Le dernier fait qu'une fiche affirme au public :
    # « voici la page de cet événement ». Signalé le 2026-08-12 sur la fiche 909, dont le
    # lien vers opera-nice.org répondait 404 — un lecteur qui veut réserver tombe sur rien.
    #
    # ICI, ET PAS EN QUOTIDIEN : une page ne meurt pas tous les matins, et c'est le seul
    # de nos contrôles qui sorte sur le réseau une fois par adresse. Lecture seule, aucun
    # LLM. Il ne compte comme tâche QUE les 404/410 : un 403 est notre serveur qu'on
    # écarte, pas une page disparue, et en faire une file enverrait réparer des liens qui
    # marchent — agendaculturel.fr refuse ce serveur et porte 338 fiches.
    # 3 bis) LA SOURCE DES TRADUCTIONS, avant de compter les liens — sinon on mesure un
    # manque qu'on sait réparer. `translate_events` créait la fiche traduite sans copier
    # `url_officiel` (corrigé le 2026-08-05) : la jumelle italienne d'une fiche
    # parfaitement sourcée s'affichait sans source. Le réparateur a été écrit le jour même
    # et N'A JAMAIS EU D'APPELANT — c'est l'erreur 11, et la quatrième question de
    # docs/ETATS_TERMINAUX.md : « le rouvreur est-il BRANCHÉ ? ».
    #
    # Constaté le 2026-08-12 dans la sortie de verifier_liens : treize fiches publiées
    # n'ont pour source que « translated:<id>:<langue> », donc aucun lien. --apply est
    # défendable — il recopie une valeur déjà vérifiée par enrich.py sur l'original,
    # n'écrase jamais une valeur existante et ne touche pas WordPress.
    from scripts.backfill_url_officiel_traductions import main as backfill_main
    rc, out = _run_captured(backfill_main, ["--apply"], "backfill_url_officiel_traductions")
    sections.append(f"• Sources recopiées sur les traductions : {_tail(out, 2)}")
    if rc:
        echecs.append("backfill_url_officiel_traductions")

    from scripts.verifier_liens import main as liens_main
    rc, out = _run_captured(liens_main, [], "verifier_liens")
    sections.append(f"• Liens officiels morts (404/410 seulement) : {_tail(out, 2)}")
    if rc:
        echecs.append("verifier_liens")

    # Fiches liées à un post NON PUBLIC — état des lieux hebdomadaire, LECTURE SEULE.
    # L'outil sait aussi réparer (--apply + options par famille), mais l'ambiguïté de la
    # corbeille est un arbitrage : ici on ne fait que COMPTER et NOMMER, pour que le
    # digest du dimanche porte enfin ce chiffre — 85 fiches le 2026-08-04, dont 28 devant
    # nous, qu'aucun bilan ne comptait. Le geste reste humain, la visibilité devient
    # automatique.
    from scripts.reconcile_hors_ligne import main as hors_ligne_main
    rc, out = _run_captured(hors_ligne_main, [], "reconcile-hors-ligne")
    sections.append(f"• Fiches liées à un post non public (reconcile_hors_ligne) : {_tail(out, 3)}")
    if rc:
        echecs.append("reconcile_hors_ligne")

    # Cohérence des descriptions. Ne bloque rien : il COMPTE. Le portillon de
    # utils/coherence n'est en refus que dans translate_events, où un faux refus ne coûte
    # rien (la fiche se represente au run suivant). Savoir combien de fiches il attrape sur
    # tout le stock est la condition pour décider s'il a sa place ailleurs — poser un
    # blocage sans ce chiffre fabriquerait un état terminal de plus.
    from scripts.audit_coherence import main as coherence_main
    rc, out = _run_captured(coherence_main, [], "audit_coherence")
    sections.append(f"• Descriptions qui ne parlent pas de leur fiche : {_tail(out, 3)}")
    if rc:
        echecs.append("audit_coherence")

    # Règles éditoriales d'exclusion (BCA, vocabulaire B2B), LECTURE SEULE. Ajouté le
    # 2026-08-05 : sans ce passage, une règle ne protégeait que le jour où on pensait à
    # relancer l'audit à la main — or c'est le motif exact des 823 fiches endormies dans
    # `venue_source='llm_none'` alors que --retry existait depuis le premier jour
    # (CLAUDE.md règle 3). Le retrait reste un geste humain (--apply) ; c'est la
    # DÉTECTION qui devient automatique, y compris pour les fiches pas encore en ligne.
    from scripts.audit_excluded_events import main as excluded_main
    rc, out = _run_captured(excluded_main, [], "audit_excluded_events")
    sections.append(f"• Événements exclus par règle éditoriale : {_tail(out, 2)}")
    if rc:
        echecs.append("audit_excluded_events")

    # Apprentissage Slack — LECTURE SEULE, zéro LLM (2026-08-05, demande de Franck :
    # « l'autonomie c'est l'apprentissage par soi-même »). Regroupe les messages
    # « À compléter » de la semaine par source × champ manquant : un motif qui dépasse
    # le seuil signe une cause SYSTÉMIQUE (une source sans image exploitable), pas une
    # série de fiches malchanceuses — voir scripts/slack_learning.py pour le détail.
    from scripts.slack_learning import main as slack_learning_main
    rc, out = _run_captured(slack_learning_main, [], "slack-learning")
    sections.append(f"• Apprentissage Slack (motifs récurrents) : {_tail(out, 2)}")
    if rc:
        echecs.append("slack_learning")

    # Suspicions d'annulation, LECTURE SEULE (2026-08-05 : scripts.dedupe bloque la
    # fusion et alerte sur Slack une fois — sans ce passage, une suspicion non traitée
    # deviendrait invisible dès qu'elle sort du fil Slack de la semaine).
    from scripts.audit_annulations import main as annulations_main
    rc, out = _run_captured(annulations_main, [], "audit-annulations")
    sections.append(f"• Suspicions d'annulation en attente : {_tail(out, 1)}")
    if rc:
        echecs.append("audit_annulations")

    # Annulations CONFIRMÉES (canal 1) encore en ligne — cf. _annules_encore_affiches.
    # Séparé des « suspicions » ci-dessus : ici, l'annulation est un FAIT posé par
    # Franck lui-même, pas une détection à vérifier.
    try:
        conn_annules = sqlite3.connect(DB_PATH)
        conn_annules.row_factory = sqlite3.Row
        annules = _annules_encore_affiches(conn_annules)
        conn_annules.close()
        sections.append(f"• Annulés encore affichés (jusqu'à leur date) : {len(annules)}")
    except Exception as exc:  # noqa: BLE001 — un comptage qui échoue ne doit pas priver du reste du digest
        sections.append("• Annulés encore affichés : ⚠️ ÉCHEC du comptage, voir les logs")
        log.warning("Comptage des annulés encore en ligne échoué : %s", exc)
        echecs.append("annules_encore_affiches")

    # Domaines sources qui REFUSENT le serveur. Ajouté le 2026-08-04 : agendaculturel.fr
    # répondait 403 sur ses quatre sous-domaines, et 242 fiches encore devant nous en
    # dépendent. Chaque tentative de réparation (dates web, venues, autocomplete,
    # repair_polluted_descriptions) échouait fiche par fiche, dans les journaux, sans que
    # la panne commune soit jamais nommée une seule fois. Une requête par domaine, ici,
    # remplace des centaines d'échecs muets ailleurs.
    from scripts.audit_sources_bloquees import main as sources_bloquees_main
    rc, out = _run_captured(sources_bloquees_main, [], "audit_sources_bloquees")
    sections.append(f"• Sources qui refusent le serveur : {_tail(out, 1)}")
    if rc:
        echecs.append("audit_sources_bloquees")

    # image_audit : coût LLM (vision) réel — borné, et il envoie DÉJÀ son propre digest
    # Slack détaillé (liens vers le back-office) : pas la peine de le dupliquer ici.
    from scripts.image_audit import main as image_audit_main
    rc, _ = _run_captured(image_audit_main, ["--limit", "100"], "image_audit")
    sections.append("• Audit visuel (image_audit) : "
                    + ("digest Slack séparé" if not rc else "⚠️ ÉCHEC, voir les logs"))
    if rc:
        echecs.append("image_audit")

    entete = "🧹 *Nettoyage hebdomadaire*"
    if echecs:
        entete = f"⚠️ *Nettoyage hebdomadaire — {len(echecs)} étape(s) en échec* " \
                 f"({', '.join(echecs)})"
    msg = entete + " :\n" + "\n".join(sections)
    slack.notify(msg)
    pipeline_status.record_run("weekly_audits", ok=len(sections) - len(echecs),
                               error=len(echecs), summary=msg[:1900])
    log.info("=== Nettoyage hebdomadaire terminé (%d étape(s) en échec) ===", len(echecs))
    return 1 if echecs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
