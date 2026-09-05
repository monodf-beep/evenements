#!/usr/bin/env python3
"""Relit le SITE PUBLIÉ et compare ce qui s'affiche à ce que dit la base.

POURQUOI CE SCRIPT EXISTE. Tout le reste du dépôt vérifie la base : batch_report
contrôle une fiche AVANT publication, weekly_audits nettoie le catalogue, image_audit
regarde les visuels, homepage_health compte les cartes de la home. Personne ne relisait
une fiche DÉJÀ EN LIGNE. Les quatre incidents du 2026-08-01 ont tous ce point commun :
la base était plausible, c'est le SITE qui était faux, et ils ont été découverts par
Franck sur son téléphone.
  • WP#6798 affichait le titre d'un événement avec le lieu et les dates d'un autre ;
  • des traductions portaient des dates fausses de plusieurs semaines EN LIGNE ;
  • la taxonomie territoire a disparu de 125 fiches pendant DIX JOURS sans que rien
    ne le signale ;
  • des fiches sont parties sans image réelle.
Aucun de ces cas n'était détectable en base seule : il fallait aller lire la page.

CE QU'ON COMPARE, ET POURQUOI CE SUPPORT-LÀ. Le JSON-LD `Event` servi dans chaque
fiche (The Events Calendar) est le contrat machine du site : c'est littéralement ce que
Google lit, et il porte le nom, les dates et le lieu sous une forme comparable trait
pour trait à la base. Comparer le HTML rendu serait fragile (la casse des titres vient
du CSS — leçon de homepage_health, qui alertait tous les jours pour rien) ; comparer le
JSON-LD ne l'est pas.

ROTATION. Tout le catalogue ne peut pas être relu chaque jour (une requête par fiche).
Le curseur est mémorisé sur disque : chaque run reprend là où le précédent s'est arrêté
et boucle en fin de liste. Avec le cap par défaut, l'ensemble du catalogue est relu en
quelques jours, indéfiniment — une régression silencieuse a donc une durée de vie
bornée, au lieu des dix jours de la taxonomie.

Ce script NE MODIFIE RIEN, ni en base ni sur le site : il constate et alerte.

Usage :
    .venv/bin/python -m scripts.site_audit                 # lot suivant (SITE_AUDIT_CAP)
    .venv/bin/python -m scripts.site_audit --cap 40
    .venv/bin/python -m scripts.site_audit --ids 3269 4312 # fiches précises
    .venv/bin/python -m scripts.site_audit --all           # tout le catalogue (long)
"""
from __future__ import annotations
import argparse
import html as _html
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import slack
from utils import pipeline_status
from utils import decisions
# Mêmes primitives lexicales que le portillon d'avant-publication : une seule définition
# dans le dépôt de « ces deux libellés parlent-ils de la même chose ».
from scripts.batch_report import _partagent_un_mot, _jour_iso, _titre_publie
from scripts.dedupe import _sig_tokens

log = get_logger("site_audit")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
ETAT = Path(os.getenv("SITE_AUDIT_STATE", ROOT / "data" / "site_audit_state.json"))
CAP = int(os.getenv("SITE_AUDIT_CAP", "40"))
DELAY = float(os.getenv("SITE_AUDIT_DELAY", "0.8"))   # ménage l'hébergement mutualisé
UA = {"User-Agent": "Mozilla/5.0 (compatible; CulturaSabaudaSiteAudit/1.0; "
                    "+https://agendasabauda.eu)"}


# --------------------------------------------------------------------------- #
# Lecture de la page
# --------------------------------------------------------------------------- #
def _jsonld_blocks(html: str) -> list[dict]:
    """Tous les objets JSON-LD de la page, @graph aplati. Un bloc illisible est ignoré
    (une page peut en porter plusieurs, un plugin tiers ne doit pas faire échouer l'audit)."""
    out: list[dict] = []
    for raw in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
                          html, re.S):
        # ⚠️ SURTOUT PAS de html.unescape() d'emblée. Le premier run a signalé « AUCUN
        # JSON-LD Event » sur cinq fiches — c'était faux, et c'était ce script le
        # coupable : WordPress échappe les guillemets DANS les chaînes JSON sous forme
        # d'entités (`"description":"La comédie &quot;Les Monologues du Machin&quot;…"`),
        # parfaitement valide. Les désentiter AVANT de parser réinjecte des guillemets
        # nus au milieu d'une chaîne et casse le JSON. On parse donc le bloc TEL QUEL, et
        # on ne tente le désentitage qu'en second recours, pour les thèmes qui, eux,
        # échappent réellement tout le bloc.
        data = None
        for tentative in (raw.strip(), _html.unescape(raw.strip())):
            try:
                data = json.loads(tentative)
                break
            except (ValueError, TypeError):
                continue
        if data is None:
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict) and "@graph" in it:
                out.extend(x for x in it["@graph"] if isinstance(x, dict))
            elif isinstance(it, dict):
                out.append(it)
    return out


def _event_node(blocks: list[dict]) -> dict | None:
    for b in blocks:
        if "Event" in str(b.get("@type") or ""):
            return b
    return None


def _og_image(html: str) -> str:
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    return m.group(1) if m else ""


def _fil_ariane(blocks: list[dict]) -> list[str]:
    for b in blocks:
        if "BreadcrumbList" in str(b.get("@type") or ""):
            noms = []
            for it in (b.get("itemListElement") or []):
                if not isinstance(it, dict):
                    continue
                # `item` est tantôt un objet {"@id":…, "name":…}, tantôt une simple URL
                # en chaîne (les deux formes sont valides en schema.org, et le thème
                # sert la seconde) : ne pas le prévoir faisait planter tout l'audit.
                item = it.get("item")
                nom = (item.get("name") if isinstance(item, dict) else None) or it.get("name")
                if nom:
                    noms.append(str(nom))
            return noms
    return []


def _lieu_jsonld(ev: dict) -> tuple[str, str]:
    """(nom du lieu, ville) tels que servis dans le JSON-LD."""
    loc = ev.get("location")
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    if not isinstance(loc, dict):
        return "", ""
    adr = loc.get("address")
    if not isinstance(adr, dict):
        adr = {}
    return str(loc.get("name") or ""), str(adr.get("addressLocality") or "")


# --------------------------------------------------------------------------- #
# Contrôles
# --------------------------------------------------------------------------- #
def auditer(row: dict, session: requests.Session) -> list[tuple[str, str]]:
    """Liste de (gravité, message) pour UNE fiche publiée. Gravité : 'grave' (ce que le
    visiteur voit est FAUX) ou 'avert' (suspect, à relire — jamais bloquant)."""
    url = (row.get("wp_permalink_as") or "").strip()
    if not url:
        return [("avert", "pas de permalien en base — page non vérifiable")]

    try:
        resp = session.get(url, timeout=30, headers=UA)
    except requests.RequestException as exc:
        return [("grave", f"page INJOIGNABLE : {exc}")]

    if resp.status_code != 200:
        # 404 sur une fiche que la base croit publiée : le post a été supprimé ou mis à
        # la corbeille côté WordPress sans que `wp_post_id_as` soit remis à zéro. La
        # fiche est donc invisible pour le visiteur ET considérée comme déjà publiée par
        # le pipeline, qui ne la republiera jamais. C'est un mort silencieux.
        # ⚠️ CE MESSAGE DISAIT « vider wp_post_id_as pour qu'il reparte au prochain
        # lot » — CORRIGÉ le 2026-08-08 : c'est le mauvais geste dans le cas
        # MAJORITAIRE, et il fabrique un doublon. Un 404 sur le front-end ne
        # distingue PAS la corbeille de la suppression (règle 1 de CLAUDE.md) ; or le
        # seul relevé complet jamais fait, celui du 2026-08-02, a trouvé 61 fiches
        # dans ce cas et 61 à la CORBEILLE, zéro réellement supprimée. Vider
        # `wp_post_id_as` sur un post corbeillé coupe le seul lien vers le post à
        # restaurer ET fait recréer une fiche neuve au lot suivant : le post
        # corbeillé reste, plus un nouveau à côté.
        # On nomme donc l'outil qui SAIT trancher — il interroge l'API REST, seule à
        # séparer les trois états, et applique le traitement propre à chacun.
        suite = (" — le post ne répond plus alors que la base le croit publié. "
                 "NE PAS vider wp_post_id_as à la main (si le post est seulement à la "
                 "corbeille, ça fabrique un doublon) : lancer "
                 "`.venv/bin/python -m scripts.reconcile_wp_deleted` (dry-run), qui "
                 "distingue corbeille et suppression via l'API REST"
                 if resp.status_code == 404 else "")
        if resp.status_code == 404:
            # ── LE 404 NE DIT PAS CE QU'IL A L'AIR DE DIRE (2026-08-13) ──────────────
            # Ce bloc criait « ce que le VISITEUR voit est FAUX » et sortait un 🔴 par
            # fiche. Le 13/08 au soir il en a produit huit — et les huit étaient des
            # posts simplement À LA CORBEILLE, déjà classés l'heure d'avant par
            # `reconcile_hors_ligne` qui, lui, interroge l'API REST. Cinq d'entre eux
            # venaient même d'être traités : leur lien était vidé depuis 21h34.
            #
            # Trois défauts en un, tous nommés dans CLAUDE.md :
            #   · RÈGLE 1 — le front-end ne distingue pas corbeille et suppression. Ce
            #     commentaire le disait déjà trois lignes plus haut, et l'alerte partait
            #     quand même ;
            #   · RÈGLE 3 — aucune de ces fiches ne se répare ici. L'alerte se rejouait
            #     à l'identique chaque jour à 14h sur les mêmes fiches, sans rouvreur ;
            #   · RÈGLE 6 — « une file ne doit contenir que ce qu'un humain peut faire ».
            #     Le geste est le même pour les huit, et c'est un autre script qui le
            #     fait. Huit 🔴 pour une commande.
            #
            # On interroge donc l'API REST avant de crier. Un post à la corbeille n'est
            # PAS « ce que le visiteur voit de faux » : le visiteur ne voit rien, et
            # c'est déjà géré ailleurs. Seule une VRAIE disparition reste grave.
            from scripts.reconcile_hors_ligne import _etat
            wp_base = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
            e = _etat(wp_base, int(row.get("wp_post_id_as") or 0))
            if e == "non_public":
                return [("corbeille", f"post à la CORBEILLE (404 attendu) — "
                                      f"`reconcile_hors_ligne` le classe déjà")]
            if e == "indetermine":
                return [("avert", f"HTTP 404 sur {url}, et l'API REST n'a pas répondu — "
                                  f"à revérifier, on ne conclut pas sur un aléa réseau")]
        return [("grave", f"HTTP {resp.status_code} sur {url}{suite}")]
    # Une redirection n'est pas une erreur pour le visiteur, mais elle signale un
    # permalien périmé en base : les liens qu'on publie ailleurs (newsletter, réseaux,
    # sitemap) pointent alors vers une URL morte qui ne fait que rebondir.
    anomalies: list[tuple[str, str]] = []
    if resp.history:
        # Cause quasi systématique, relevée le 2026-08-02 : le permalien stocké est resté
        # sous sa forme BRUTE de short-link WordPress (« /?p=601 »,
        # « /it/?post_type=tribe_events&p=601 ») au lieu de l'adresse résolue. On nomme le
        # correctif dans le message — une alerte qui ne dit pas quoi faire finit ignorée.
        brut = "?p=" in url or "post_type=tribe_events" in url
        remede = (" — permalien resté en forme brute : "
                  "scripts/backfill_permalinks_as.py le ré-résout" if brut else "")
        anomalies.append(("avert", f"le permalien redirige ({resp.status_code} après "
                                   f"{len(resp.history)} saut(s)) → {resp.url}{remede}"))

    html = resp.text
    blocks = _jsonld_blocks(html)
    ev = _event_node(blocks)
    if not ev:
        # Sans JSON-LD Event, la fiche n'est plus un événement pour Google : elle sort
        # des résultats enrichis et du calendrier. C'est grave et totalement invisible.
        anomalies.append(("grave", "AUCUN JSON-LD Event servi — la fiche n'est plus "
                                   "un événement pour Google/TEC"))
        return anomalies

    # 1. DATES — le dommage constaté en ligne le 2026-08-01 (traductions décalées de
    # plusieurs semaines). La base fait foi : c'est elle que le pipeline corrige.
    db_debut, db_fin = _jour_iso(row.get("date_event_start")), _jour_iso(row.get("date_event_end"))
    site_debut, site_fin = _jour_iso(ev.get("startDate")), _jour_iso(ev.get("endDate"))
    if db_debut and site_debut and db_debut != site_debut:
        anomalies.append(("grave", f"DATE DE DÉBUT affichée {site_debut} ≠ {db_debut} en base"))
    elif db_debut and not site_debut:
        anomalies.append(("grave", f"aucune date affichée alors que la base dit {db_debut}"))
    if db_fin and site_fin and db_fin != site_fin:
        anomalies.append(("grave", f"DATE DE FIN affichée {site_fin} ≠ {db_fin} en base"))
    # ⚠️ PAS d'alerte quand le JSON-LD ne porte AUCUNE date de fin. La première version
    # en levait une, et le premier run l'a immédiatement démentie : sur « Festival des
    # jardins alpestres », le JSON-LD ne donne que `startDate`, alors que WordPress
    # connaît parfaitement la fin (le lien « ajouter à mon agenda » de la même page
    # porte enddt=2026-10-03, et la meta description dit « jusqu'au 3 octobre »). Ce
    # n'est donc pas une donnée fausse sur le site : c'est le générateur de JSON-LD (le
    # plugin SEO, pas TEC) qui n'émet jamais endDate. L'alerte se serait déclenchée sur
    # TOUS les événements de plusieurs jours — exactement la faute de homepage_health ce
    # matin, une alerte qui crie tous les jours et qu'on finit par ne plus lire.
    # Le manque d'endDate dans les données structurées est un vrai sujet SEO, mais c'est
    # un défaut de GABARIT, pas de fiche : consigné une fois dans docs/site_issues.json.

    # 2. TITRE — le bug WP#6798 (titre d'un événement, lieu d'un autre).
    # La bonne question n'est PAS « le titre en ligne ressemble-t-il au titre source ? »
    # mais « le site affiche-t-il le titre qu'on lui a demandé d'afficher ? ». Le premier
    # run l'a montré : « NOTE D'ARTE » (titre italien de la source) est publié sous
    # « À Turin, la musique entre en dialogue avec les arts décoratifs » — aucun mot
    # commun, et c'est parfaitement NORMAL, c'est la réécriture éditoriale qui fait son
    # travail. Comparer au titre source alertait donc sur toutes les fiches d'origine
    # italienne. On compare d'abord au titre VOULU (article_title / enrich_data), qui est
    # la seule référence légitime ; le rapprochement lexical avec le lieu ne sert plus que
    # de filet quand la base n'a aucun titre rédigé.
    nom_site = str(ev.get("name") or "")
    titre_voulu = _titre_publie(row)
    toks_site = _sig_tokens(nom_site)
    if titre_voulu:
        if not _partagent_un_mot(toks_site, _sig_tokens(titre_voulu)):
            anomalies.append(("grave", f"le site affiche « {nom_site[:55]} » alors que la "
                                       f"base a rédigé « {titre_voulu[:55]} » — republication "
                                       f"perdue ou fiche contaminée"))
    else:
        toks_fiche = (_sig_tokens(row.get("title") or "") | _sig_tokens(row.get("lieu") or "")
                      | _sig_tokens(row.get("ville") or ""))
        if len(toks_site) >= 2 and len(toks_fiche) >= 2 \
                and not _partagent_un_mot(toks_site, toks_fiche):
            anomalies.append(("avert", f"titre en ligne « {nom_site[:60]} » sans aucun mot "
                                       f"commun avec la fiche (« {(row.get('title') or '')[:40]} » · "
                                       f"{(row.get('lieu') or '—')[:25]})"))

    # 3. LIEU / VILLE affichés — avertissement seulement : un toponyme peut légitimement
    # être servi sous sa forme locale (Aoste/Aosta, Turin/Torino).
    lieu_site, ville_site = _lieu_jsonld(ev)
    for valeur_site, valeur_db, libelle in ((lieu_site, row.get("lieu"), "lieu"),
                                            (ville_site, row.get("ville"), "ville")):
        ta, tb = _sig_tokens(valeur_site), _sig_tokens(valeur_db or "")
        if ta and tb and not _partagent_un_mot(ta, tb):
            anomalies.append(("avert", f"{libelle} affiché « {valeur_site[:35]} » vs "
                                       f"« {(valeur_db or '')[:35]} » en base"))

    # 4. VISUEL — une fiche sans og:image part nue sur les réseaux et dans les partages.
    # Notre visuel de repli territorial existe précisément pour que ça n'arrive jamais :
    # s'il manque quand même, c'est que le téléversement a échoué sans le dire.
    if not _og_image(html):
        anomalies.append(("grave", "aucune image de partage (og:image) — fiche nue "
                                   "sur les réseaux"))

    # 5. TERRITOIRE — VOLONTAIREMENT ABSENT DE CET AUDIT, et il faut le dire plutôt que
    # de laisser croire que c'est couvert. La régression de slugs du 2026-07-22 (125
    # fiches sans taxonomie pendant dix jours) est exactement le genre de panne que ce
    # script devrait attraper. Sauf que le territoire n'est servi NULLE PART dans la
    # page d'une fiche : vérifié le 2026-08-02 sur une fiche réelle — pas dans le fil
    # d'Ariane (« Accueil / Évènements / <titre> »), pas dans les classes du <body>, et
    # les liens /territoire/… présents sont ceux du MENU, identiques sur toutes les
    # pages, donc sans rapport avec la fiche. Un contrôle bâti là-dessus alerterait sur
    # 100 % du catalogue — la faute exacte de homepage_health, qui comparait des titres
    # en capitales à un HTML en minuscules et criait tous les jours.
    # Le bon vecteur est ailleurs (API REST WordPress, ou contrôle des pages d'archive
    # par territoire) : à traiter séparément, pas à simuler ici.

    return anomalies


# --------------------------------------------------------------------------- #
# Sélection tournante
# --------------------------------------------------------------------------- #
def _etat() -> dict:
    try:
        return json.loads(ETAT.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return {}


def _ecrit_etat(etat: dict) -> None:
    try:
        ETAT.parent.mkdir(parents=True, exist_ok=True)
        ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as exc:
        log.warning("Curseur non sauvegardé (%s) — le prochain run repartira du début", exc)


def _publiees(conn: sqlite3.Connection) -> list[dict]:
    # `wp_deleted_at` renseigné = post constaté hors ligne (corbeille/brouillon) par
    # scripts/reconcile_wp_deleted. Sans cette exclusion, les 61 fiches corbeillées
    # volontairement le 2026-08-02 (Musilac, le 14 juillet, les récapitulatifs du
    # Dauphiné — du passé et des non-événements) reviendraient en 🔴 à chaque tour de
    # rotation, pour toujours. Une alerte permanente sur une situation voulue, c'est le
    # meilleur moyen de faire ignorer les vraies. La marque est réversible : si le post
    # redevient public, reconcile efface l'horodatage et la fiche revient dans l'audit.
    try:
        return [dict(r) for r in conn.execute(
            "SELECT id, title, lieu, ville, territoire, date_event_start, date_event_end, "
            "       article_title, enrich_data, wp_post_id_as, wp_permalink_as "
            "FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
            "  AND statut NOT IN ('merged','rejected') "
            "  AND COALESCE(wp_deleted_at,'') = '' ORDER BY id").fetchall()]
    except sqlite3.OperationalError:
        # Colonne absente : base jamais passée par reconcile_wp_deleted. On dégrade
        # proprement au lieu de planter le cron.
        return [dict(r) for r in conn.execute(
            "SELECT id, title, lieu, ville, territoire, date_event_start, date_event_end, "
            "       article_title, enrich_data, wp_post_id_as, wp_permalink_as "
            "FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
            "  AND statut NOT IN ('merged','rejected') ORDER BY id").fetchall()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Relit les fiches publiées et compare l'affichage à la base.")
    parser.add_argument("--cap", type=int, default=CAP,
                        help=f"Nombre de fiches relues par run (défaut {CAP}).")
    parser.add_argument("--ids", type=int, nargs="+", default=None,
                        help="Ne relire que ces ids (ignore la rotation).")
    parser.add_argument("--all", action="store_true",
                        help="Relire TOUT le catalogue publié en un run (long).")
    parser.add_argument("--quiet", action="store_true",
                        help="Ne rien poster sur Slack (sortie console seulement).")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    toutes = _publiees(conn)
    conn.close()
    if not toutes:
        log.info("Aucune fiche publiée à relire.")
        return 0

    etat = _etat()
    if args.ids:
        lot = [r for r in toutes if r["id"] in set(args.ids)]
    elif args.all:
        lot = toutes
    else:
        # Rotation par id : on reprend au premier id STRICTEMENT supérieur au dernier
        # relu, et on boucle. Un id supprimé entre deux runs ne bloque donc rien.
        depuis = int(etat.get("dernier_id") or 0)
        suite = [r for r in toutes if r["id"] > depuis]
        lot = (suite or toutes)[:args.cap]

    log.info("Relecture de %d fiche(s) publiée(s) sur %d (curseur : après id %s)",
             len(lot), len(toutes), etat.get("dernier_id") or "—")

    session = requests.Session()

    # LE SITE RÉPOND-IL, AVANT DE JUGER SES PAGES UNE PAR UNE ?
    #
    # `auditer()` rend « page INJOIGNABLE » en gravité GRAVE quand la requête échoue. C'est
    # juste pour UNE page qui tombe alors que le site va bien. Mais quand c'est le site
    # entier qui est hors d'atteinte, ce même code crie une anomalie grave par fiche : un
    # incident réseau devient des centaines de pages « cassées ».
    #
    # Ce n'est pas théorique. Le 2026-08-18 à 09h58, l'hébergement du site a cessé de
    # répondre à l'adresse du VPS — par intermittence, avec un retour vers 13h01 — ping perdu à 100 %, ports 80 et 443 expirés, pendant
    # que le reste du réseau fonctionnait. Le cron de 14h aurait rendu un rapport de
    # plusieurs centaines de lignes graves, toutes fausses, et il aurait fallu le
    # démonter à la main pour s'apercevoir qu'il n'y avait qu'UN problème.
    #
    # C'est la règle 6 de CLAUDE.md : une file ne doit contenir que ce qu'un humain peut
    # faire. Face à un site injoignable, le seul geste utile est d'attendre — pas de relire
    # trois cents fiches. Et c'est aussi « un zéro doit dire d'où il vient », dans l'autre
    # sens : un rapport catastrophique doit dire s'il vient d'une catastrophe ou d'un câble.
    if not args.ids:
        temoin = (os.getenv("WP_AS_URL") or "").rstrip("/")
        if temoin:
            try:
                session.get(temoin + "/", timeout=20, headers=UA)
            except requests.RequestException as exc:
                # AU REGISTRE — ajouté le 2026-08-28. Avant, « injoignable » se
                # re-signalait à l'identique chaque jour, et c'était le bilan de 11h qui
                # recalculait « 3e jour » en relisant les logs de mémoire — fragile, et
                # ce script LUI-MÊME, mécanique et quotidien, est la meilleure source de
                # vérité sur la durée. `signaler()` compte les jours tout seul (vues,
                # première date) ; le site étant hors d'atteinte pour TOUT le pipeline
                # (0 publication tant qu'il dure), on escalade dès le premier jour.
                e = decisions.signaler("site-injoignable",
                                       f"{temoin} injoignable depuis le VPS", "site_audit")
                try:
                    decisions.escalader("site-injoignable",
                                        f"Signalé {e['vues']}× depuis le "
                                        f"{e['premiere_vue'][:10]} — ticket hébergeur ?")
                except ValueError:
                    pass  # déjà escaladée — pas de bruit
                msg = (f"🔴 *Audit du site NON EFFECTUÉ* — {temoin} est injoignable depuis "
                       f"le serveur : {str(exc)[:160]} (signalé {e['vues']}× depuis le "
                       f"{e['premiere_vue'][:10]})\n"
                       f"_Aucune conclusion n'est tirée sur les {len(toutes)} fiches "
                       f"publiées : elles n'ont pas été relues. Un site hors d'atteinte "
                       f"n'est pas un site cassé, et le seul geste utile est d'attendre "
                       f"qu'il réponde._")
                log.error(msg.replace("*", ""))
                if not args.quiet:
                    slack.notify(msg)
                return 1
        # LE SITE RÉPOND : si une panne était au registre, elle se referme ICI, pas au
        # jugement d'un humain qui doit se souvenir de taper une commande. Le prochain
        # `git status` d'un site mort rouvrira la décision tout seul (règle 3).
        if temoin and any(d["cle"] == "site-injoignable" for d in decisions.en_attente()):
            e = decisions.resoudre("site-injoignable",
                                   f"{temoin} répond de nouveau, vérifié par site_audit",
                                   "site_audit")
            slack.notify(f"✅ *Site de nouveau joignable* — {temoin}, après avoir été "
                        f"signalé depuis le {e['premiere_vue'][:10]}")

    graves, averts, saines = [], [], 0
    corbeille: list[str] = []     # posts corbeillés : COMPTÉS, jamais criés un par un
    for i, row in enumerate(lot, 1):
        anomalies = auditer(row, session)
        titre = (row.get("title") or "")[:55]
        if not anomalies:
            saines += 1
            log.info("[%s] ok — %s", row["id"], titre)
        else:
            for niveau, msg in anomalies:
                ligne = f"[{row['id']}] WP#{row['wp_post_id_as']} {titre} — {msg}"
                if niveau == "corbeille":
                    corbeille.append(f"[{row['id']}] WP#{row['wp_post_id_as']} {titre}")
                    log.info("· %s", ligne)
                    continue
                (graves if niveau == "grave" else averts).append(ligne)
                log.warning("%s %s", "🔴" if niveau == "grave" else "⚠️", ligne)
        if i < len(lot):
            time.sleep(DELAY)

    if lot and not args.ids and not args.all:
        etat["dernier_id"] = lot[-1]["id"]
        etat["tour_complet_a"] = lot[-1]["id"] >= toutes[-1]["id"]
        _ecrit_etat(etat)

    # ---- Restitution ----
    entete = (f"🔍 *Relecture du site publié* — {len(lot)} fiche(s) relue(s) "
              f"({saines} conforme(s), {len(graves)} anomalie(s) grave(s), "
              f"{len(averts)} à vérifier)")
    corps = []
    if graves:
        corps.append("*Ce que le visiteur voit est FAUX :*")
        corps += [f"🔴 {l}" for l in graves[:15]]
        if len(graves) > 15:
            corps.append(f"…et {len(graves) - 15} autre(s).")
    if averts:
        corps.append("*À vérifier :*")
        corps += [f"⚠️ {l}" for l in averts[:10]]
        if len(averts) > 10:
            corps.append(f"…et {len(averts) - 10} autre(s).")
    if corbeille:
        # UNE LIGNE, PAS N ALERTES. Le geste est le même pour toutes, et c'est un autre
        # script qui le fait : les énumérer une par une remplissait le message de 🔴 pour
        # une seule commande, tous les jours, sur les mêmes fiches (règle 6).
        corps.append(f"_{len(corbeille)} fiche(s) dont le post est à la CORBEILLE — "
                     f"normal, `reconcile_hors_ligne` les classe. Pas une anomalie du "
                     f"site._")
    msg = entete + ("\n" + "\n".join(corps) if corps else "")
    print(msg)

    # Slack UNIQUEMENT s'il y a quelque chose à dire : un rapport quotidien « tout va
    # bien » finit par ne plus être lu, et c'est le jour où il crie que ça compte.
    # Les corbeillés NE DÉCLENCHENT PAS d'envoi : s'il n'y a qu'eux, il n'y a rien à
    # signaler. C'est la même doctrine que les contradicteurs de 11h30 et 11h35 — un
    # message quotidien qui ne demande aucun geste cesse d'être lu.
    if not args.quiet and (graves or averts):
        slack.notify(msg[:3500])
    pipeline_status.record_run("site_audit", ok=saines, warn=len(averts),
                               error=len(graves), summary=msg[:1900])
    log.info("=== Relecture terminée : %d conforme(s), %d grave(s), %d avertissement(s) ===",
             saines, len(graves), len(averts))
    return 1 if graves else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
