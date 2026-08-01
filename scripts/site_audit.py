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
# Mêmes primitives lexicales que le portillon d'avant-publication : une seule définition
# dans le dépôt de « ces deux libellés parlent-ils de la même chose ».
from scripts.batch_report import _partagent_un_mot, _jour_iso
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
        try:
            data = json.loads(_html.unescape(raw.strip()))
        except (ValueError, TypeError):
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
        return [("grave", f"HTTP {resp.status_code} sur {url}")]
    # Une redirection n'est pas une erreur pour le visiteur, mais elle signale un
    # permalien périmé en base : les liens qu'on publie ailleurs (newsletter, réseaux,
    # sitemap) pointent alors vers une URL morte qui ne fait que rebondir.
    anomalies: list[tuple[str, str]] = []
    if resp.history:
        anomalies.append(("avert", f"le permalien redirige ({resp.status_code} après "
                                   f"{len(resp.history)} saut(s)) → {resp.url}"))

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

    # 2. TITRE ↔ ANCRAGE FACTUEL — le bug WP#6798 (titre d'un événement, lieu d'un
    # autre). Même règle qu'avant publication : le titre EN LIGNE doit partager un mot
    # significatif avec le titre/lieu/ville de la fiche. On s'abstient si l'un des deux
    # côtés est trop pauvre pour juger — une alerte sur deux mots serait du bruit.
    nom_site = str(ev.get("name") or "")
    toks_site = _sig_tokens(nom_site)
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
    return [dict(r) for r in conn.execute(
        "SELECT id, title, lieu, ville, territoire, date_event_start, date_event_end, "
        "       wp_post_id_as, wp_permalink_as "
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
    graves, averts, saines = [], [], 0
    for i, row in enumerate(lot, 1):
        anomalies = auditer(row, session)
        titre = (row.get("title") or "")[:55]
        if not anomalies:
            saines += 1
            log.info("[%s] ok — %s", row["id"], titre)
        else:
            for niveau, msg in anomalies:
                ligne = f"[{row['id']}] WP#{row['wp_post_id_as']} {titre} — {msg}"
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
    msg = entete + ("\n" + "\n".join(corps) if corps else "")
    print(msg)

    # Slack UNIQUEMENT s'il y a quelque chose à dire : un rapport quotidien « tout va
    # bien » finit par ne plus être lu, et c'est le jour où il crie que ça compte.
    if not args.quiet and (graves or averts):
        slack.notify(msg[:3500])
    pipeline_status.record_run("site_audit", ok=saines, warn=len(averts),
                               error=len(graves), summary=msg[:1900])
    log.info("=== Relecture terminée : %d conforme(s), %d grave(s), %d avertissement(s) ===",
             saines, len(graves), len(averts))
    return 1 if graves else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
