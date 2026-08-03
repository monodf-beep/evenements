#!/usr/bin/env python3
"""Répare les DESCRIPTIONS détruites par la fusion de doublons (bug `merge_group`).

POURQUOI ce script existe
-------------------------
Jusqu'au correctif du 2026-08-02 (commit 40de3bf), `scripts/dedupe.py::merge_group`
gardait, pour le gagnant d'un groupe de doublons, la description LA PLUS LONGUE du
groupe — longueur mesurée en caractères BRUTS. Or une description issue d'un flux
Google News RSS n'est qu'un `<a href="https://news.google.com/rss/articles/CBMi…">`
dont l'URL encodée pèse plusieurs CENTAINES de caractères pour ZÉRO mot de contenu.
Elle gagnait donc systématiquement le « plus long » et ÉCRASAIT la vraie description
de l'événement — y compris lors de fusions PARFAITEMENT CORRECTES (« Charlie Winston
■ 7 juillet » fusionné dans « Charlie Winston » : bon appariement, description
détruite). Sur le cas réel : 286 caractères bruts contre 178, mais 28 caractères de
texte visible contre 171.

Le correctif a introduit `dedupe._text_len()` (texte visible, balises et URLs
retirées) : la casse ne se reproduit plus. Mais il ne RÉPARE RIEN de l'existant — la
vraie description est perdue en base, et elle n'est pas cosmétique : `enrich.py`
agrège la description des doublons dans la matière de rédaction, `publisher_as.py`
en fait l'extrait WordPress à défaut de `seo_answer`. Une vingtaine de fiches déjà
publiées sont concernées (Charlie Winston, Nice Jazz Fest, expo Vespa au MAUTO,
LEVITATION, Nice Classic Festival…).

Ce script re-télécharge la description depuis la VRAIE page de l'événement
(`url_source`) et ne la réécrit que si elle a strictement plus de substance. Il est le
pendant ÉCRIVAIN de `scripts/audit_dedupe_damage.py` (lecture seule), qui inventorie
l'ensemble des dégâts de ces fusions — dont ceux, plus graves, où c'est l'APPARIEMENT
lui-même qui était faux : ceux-là ne se réparent pas en re-téléchargeant une page et
restent à trancher à la main.

CE QU'IL NE TOUCHE JAMAIS
-------------------------
Les items RADAR (presse / Google News, `source_type='radar'`, ~1294 en base, jamais
publiés) ont LÉGITIMEMENT un lien pour description : c'est la nature du flux, pas un
dégât. Les réparer n'aurait aucun sens et les ferait ressembler à des fiches réelles.
Sont donc exclus : `source_type='radar'`, les `url_source` contenant news.google.com,
et les `url_source` synthétiques (`gmail:` = collecte Gmail, `translated:` = fiche
fabriquée par translate_events) qui ne désignent aucune page téléchargeable.
Une description VIDE n'est pas non plus notre bug (rien n'a été écrasé, il n'y avait
rien) : on ne la touche pas — ce serait une autre campagne, sur des milliers de fiches.

Ordre d'extraction, du plus fiable au moins fiable (on s'arrête au premier qui a de
la substance) : JSON-LD schema.org `description` (idéalement d'un nœud `Event`), puis
`og:description` / `twitter:description` / `<meta name="description">`, puis le texte
de la zone `<article>`/`<main>`. On NE retombe JAMAIS sur le texte de la page entière :
sur un site d'institution ce serait un énorme menu de navigation — mieux vaut laisser
la description cassée et la signaler que d'y écrire du menu.

SÛR : dry-run par défaut, --apply pour écrire. AUCUN appel LLM. Le dry-run télécharge
quand même les pages (lecture seule) afin de montrer le remplacement EXACT qu'il ferait.

Usage (VPS) :
    .venv/bin/python -m scripts.repair_polluted_descriptions            # liste
    .venv/bin/python -m scripts.repair_polluted_descriptions --apply    # répare
    .venv/bin/python -m scripts.repair_polluted_descriptions --ids 2153 --apply
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.clean_text import strip_boilerplate
from scripts.scraper_events import init_db
# _text_len est la MESURE DE RÉFÉRENCE du correctif dedupe : on l'importe au lieu de la
# redéfinir, pour que « avoir de la substance » veuille dire ici exactement ce qu'il
# veut dire là-bas (si le seuil de dedupe évolue, ce script suit sans divergence).
from scripts.dedupe import _text_len, _sig_tokens
from scripts.batch_report import _partagent_un_mot
# Téléchargement + réduction HTML→texte : helpers déjà éprouvés d'enrich.py (User-Agent
# de vrai navigateur — beaucoup de sites refusent un UA « …Bot » —, timeout, refus des
# url_source synthétiques gmail:/news.google.com). Privés, mais on les prend tels quels
# plutôt que d'en réécrire une version divergente ; `_get_html` nous rend le HTML BRUT,
# indispensable pour lire le JSON-LD et les <meta> (fetch_official_page, lui, a déjà
# tout aplati en texte). Un seul GET par fiche.
from scripts.enrich import _get_html, _html_to_text

log = get_logger("repair_polluted_descriptions")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# --- Seuils de détection ---------------------------------------------------
# En dessous de ce nombre de caractères VISIBLES, une description n'a plus de contenu
# réel (le blob Google News du cas type mesurait 28 caractères visibles).
SEUIL_TEXTE = 120
# … mais seulement si la description PRÉTEND être fournie : au-delà de ce volume brut,
# l'écart entre le brut et le visible est la signature du blob (URL encodée géante).
# Ce garde-fou évite de rafler toutes les fiches simplement peu bavardes.
SEUIL_BRUT = 200
# Substance minimale exigée d'une description re-téléchargée : en dessous, ce qu'on a
# récupéré est un fil d'Ariane ou un titre de page, pas une description.
SEUIL_NOUVELLE = 80
# Plafond de la description réécrite (les descriptions scrapées font typiquement
# quelques centaines de caractères ; au-delà on recopierait la page).
MAX_DESC = 1500

_RX_GNEWS = re.compile(r"news\.google\.com/rss", re.I)
_RX_LDJSON = re.compile(
    r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>')
_RX_META = re.compile(r"(?is)<meta\b[^>]*>")
_RX_META_CLE = re.compile(r'(?is)\b(?:name|property)\s*=\s*["\']([^"\']+)["\']')
_RX_META_VAL = re.compile(r'(?is)\bcontent\s*=\s*["\']([^"\']*)["\']')
_RX_REGION = re.compile(r"(?is)<(article|main)\b[^>]*>(.*?)</\1>")


# --------------------------------------------------------------------------- #
# Détection
# --------------------------------------------------------------------------- #
def motif_pollution(description: str | None) -> str:
    """Motif (non vide) si la description manque de SUBSTANCE réelle, "" sinon.

    Deux signatures, celles du bug :
      1. un lien Google News RSS survit dans la description d'une vraie fiche — il n'a
         rien à y faire, il vient d'un item radar fusionné ;
      2. texte visible ridicule pour un volume brut important — c'est le blob.
    Une description vide ou simplement courte n'est PAS concernée (rien n'a été écrasé).
    """
    d = description or ""
    if not d.strip():
        return ""
    if _RX_GNEWS.search(d):
        return "lien Google News RSS dans la description"
    visible, brut = _text_len(d), len(d)
    if visible < SEUIL_TEXTE and brut >= SEUIL_BRUT:
        return f"{visible} car. visibles pour {brut} car. bruts"
    return ""


def url_reparable(url_source: str | None, source_type: str | None) -> str:
    """L'URL renvoie-t-elle vers une VRAIE page d'événement re-téléchargeable ? "" sinon.

    Exclut les items radar (leur description EST un lien, par nature) et les url_source
    synthétiques `gmail:` / `translated:` qui ne désignent aucune page.
    """
    u = (url_source or "").strip()
    if (source_type or "").strip().lower() == "radar":
        return ""
    if u.startswith(("gmail:", "translated:")):
        return ""
    if not u.startswith(("http://", "https://")):
        return ""          # filet : tout autre schéma synthétique ajouté plus tard
    if "news.google.com" in u.lower():
        return ""
    return u


# --------------------------------------------------------------------------- #
# Extraction de la description depuis la page
# --------------------------------------------------------------------------- #
def _jsonld_noeud(noeud, event_seul: bool) -> str:
    """Première `description` non vide trouvée dans un arbre JSON-LD.
    `event_seul` : ne retient que les nœuds dont le @type parle d'Event (la description
    du site entier — souvent une baseline — traîne dans le même bloc)."""
    if isinstance(noeud, list):
        for n in noeud:
            trouve = _jsonld_noeud(n, event_seul)
            if trouve:
                return trouve
        return ""
    if isinstance(noeud, dict):
        types = noeud.get("@type") or ""
        types = " ".join(types) if isinstance(types, list) else str(types)
        desc = noeud.get("description")
        if isinstance(desc, str) and desc.strip() and (
                not event_seul or "event" in types.lower()):
            return desc.strip()
        for valeur in noeud.values():
            trouve = _jsonld_noeud(valeur, event_seul)
            if trouve:
                return trouve
    return ""


def depuis_jsonld(html: str) -> str:
    """`description` du schema.org de la page — la plus fiable : c'est le site lui-même
    qui déclare « voici la description de CET événement »."""
    blocs = []
    for brut in _RX_LDJSON.findall(html or ""):
        try:
            blocs.append(json.loads(brut.strip()))
        except (ValueError, TypeError):
            continue        # JSON-LD malformé : fréquent, non bloquant
    for event_seul in (True, False):
        for bloc in blocs:
            trouve = _jsonld_noeud(bloc, event_seul)
            if trouve:
                return trouve
    return ""


def depuis_meta(html: str) -> str:
    """og:description / twitter:description / <meta name="description">.
    C'est le résumé que le site sert aux partages et aux flux — donc, très souvent,
    exactement le texte que le flux RSS nous avait donné à l'origine."""
    metas: dict[str, str] = {}
    for m in _RX_META.finditer(html or ""):
        cle, val = _RX_META_CLE.search(m.group(0)), _RX_META_VAL.search(m.group(0))
        if cle and val:
            metas.setdefault(cle.group(1).strip().lower(), val.group(1))
    for cle in ("og:description", "twitter:description", "description"):
        if (metas.get(cle) or "").strip():
            return metas[cle]
    return ""


def depuis_corps(html: str) -> str:
    """Texte de la zone de contenu (<article>/<main>), en dernier recours.
    On se limite VOLONTAIREMENT à ces balises : le texte de la page entière serait,
    sur un site d'institution, un menu de navigation de plusieurs milliers de
    caractères — écrire ça dans une description serait pire que le blob qu'on répare."""
    blocs = [m.group(2) for m in _RX_REGION.finditer(html or "")]
    return max(blocs, key=len) if blocs else ""


def recuperer_description(url: str, timeout: int = 8) -> tuple[str, str]:
    """(description_propre, provenance). ("", motif_echec) si rien d'exploitable."""
    html = _get_html(url, timeout)
    if not html:
        return "", "page inaccessible"
    for libelle, brut in (("JSON-LD", depuis_jsonld(html)),
                          ("meta", depuis_meta(html)),
                          ("<article>/<main>", depuis_corps(html))):
        if not brut:
            continue
        # Même nettoyage qu'à l'ingestion : on retire les pieds de flux RSS et les
        # artefacts de page-builder (utils/clean_text), en gardant les faits.
        propre = strip_boilerplate(_html_to_text(brut))[:MAX_DESC].strip()
        if _text_len(propre) >= SEUIL_NOUVELLE:
            return propre, libelle
    return "", "aucune description exploitable sur la page"


def _debris_navigation(texte: str) -> bool:
    """La « description » récupérée n'est-elle qu'un fil de navigation / d'étiquettes ?

    Signature relevée sur le dry-run du 2026-08-02 (gpff.it, rubrique « rassegna
    stampa ») : « … 1 Luglio 2026 Rassegna , Rassegna , Stampa , Stampa ». Ce sont les
    catégories WordPress de l'article, rendues deux fois par le thème et aspirées comme
    du texte. Une vraie description ne répète jamais à l'identique plusieurs de ses
    fragments séparés par des virgules — c'est ce qui rend le test sûr sans jugement
    sémantique."""
    tous = [f.strip().lower() for f in _html_to_text(texte or "").split(",")]
    if len(tous) < 3:
        return False
    # On ne compare que les fragments COURTS : une étiquette est brève, et le premier
    # fragment d'un texte réel (souvent long, il porte le titre et la date collés)
    # ne se répétera jamais à l'identique. UNE répétition suffit : dans le sens
    # conservateur, se tromper ici ne fait que renoncer à réparer une description
    # déjà cassée — jamais écraser une bonne.
    courts = [f for f in tous if 2 <= len(f) <= 40]
    return len(courts) - len(set(courts)) >= 1


def _titre_incoherent(titre: str, texte: str) -> bool:
    """La nouvelle description ne partage AUCUN mot significatif avec le titre.

    Cas réel du dry-run : la fiche « Charlie Winston » (mal-thonon.org) se voyait
    proposer « Une nouvelle création de Raphaël, avec ce concert-spectacle… » — la page
    servait la description d'un AUTRE spectacle. Appliqué en silence, c'était réécrire
    une fiche sur le mauvais artiste, exactement le dommage qu'on cherche à réparer.

    ⚠️ Ce contrôle SEUL produit des faux positifs légitimes : « Festival de musique
    sacrée » vs « Les artistes du Chœur et de l'Orchestre Philharmonique de Nice… » ne
    partagent aucun mot alors que la description est la bonne. Il ne rejette donc pas —
    il ROUTE vers un bac « à valider » que --apply ne touche pas."""
    ta, tb = _sig_tokens(titre or ""), _sig_tokens(_html_to_text(texte or "")[:400])
    if len(ta) < 2 or len(tb) < 2:
        return False                      # trop pauvre pour juger : on s'abstient
    return not _partagent_un_mot(ta, tb)


def _apercu(texte: str, n: int = 110) -> str:
    """Aperçu en TEXTE VISIBLE (c'est la seule vue honnête d'un blob : en brut il
    remplirait l'écran d'URL encodée)."""
    vu = _html_to_text(texte or "")
    return (vu[:n] + "…") if len(vu) > n else (vu or "(vide)")


# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Répare les descriptions écrasées par un blob Google News (bug merge_group).")
    parser.add_argument("--apply", action="store_true", help="Écrit (sinon dry-run).")
    parser.add_argument("--force-douteux", action="store_true",
                        help="Applique AUSSI les fiches du bac « à valider à la main » "
                             "(texte récupéré sans aucun mot commun avec le titre). "
                             "À n'utiliser qu'avec --ids, après avoir regardé la page.")
    parser.add_argument("--ids", type=int, nargs="+", default=None,
                        help="N'examine que ces ids (sinon toute la base).")
    parser.add_argument("--cap", type=int, default=100,
                        help="Nombre max de fiches traitées par run (défaut 100).")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Pause entre deux téléchargements, en secondes (défaut 1).")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)          # repose busy_timeout : la base est écrite par plusieurs process

    sql = ("SELECT id, title, description, url_source, source_type, wp_post_id_as, "
           "duplicate_of, article_md FROM events_raw")
    params: list = []
    if args.ids:
        sql += f" WHERE id IN ({','.join('?' * len(args.ids))})"
        params = args.ids
    rows = [dict(r) for r in conn.execute(sql + " ORDER BY id", params).fetchall()]

    # duplicate_of renseigné = doublon FUSIONNÉ (statut 'merged') : sa description est
    # sa matière d'origine, elle n'a pas été écrasée (merge_group n'écrit que sur le
    # gagnant) et elle n'est jamais publiée telle quelle. Hors périmètre.
    candidats, ecartes_radar = [], 0
    for r in rows:
        motif = motif_pollution(r["description"])
        if not motif or r["duplicate_of"]:
            continue
        url = url_reparable(r["url_source"], r["source_type"])
        if not url:
            ecartes_radar += 1
            continue
        r["_motif"], r["_url"] = motif, url
        candidats.append(r)

    print(f"\n{len(rows)} fiche(s) examinée(s) — {len(candidats)} description(s) sans "
          f"substance ET rattachée(s) à une vraie page")
    print(f"{ecartes_radar} écartée(s) volontairement (radar / Google News / gmail: / "
          f"translated: — leur description EST un lien, c'est normal)\n")
    if not candidats:
        conn.close()
        return 0

    if len(candidats) > args.cap:
        print(f"(cap {args.cap} : {len(candidats) - args.cap} fiche(s) remises au "
              f"prochain run)\n")
        candidats = candidats[:args.cap]

    remplacements, sans_gain, echecs = [], [], []
    for i, r in enumerate(candidats, 1):
        nouvelle, provenance = recuperer_description(r["_url"])
        if not nouvelle:
            echecs.append((r, provenance))
        elif _text_len(nouvelle) > _text_len(r["description"] or ""):
            r["_nouvelle"], r["_provenance"] = nouvelle, provenance
            remplacements.append(r)
        else:
            # JAMAIS de régression : on garde ce qui est en base, même cassé.
            sans_gain.append((r, nouvelle))
        if args.delay and i < len(candidats):
            time.sleep(args.delay)

    # ------------------------------------------------------------------ #
    # TRIAGE DES REMPLACEMENTS — « plus long » ne veut pas dire « meilleur ».
    # Le premier dry-run (2026-08-02) proposait 50 réparations dont une bonne moitié
    # aurait DÉGRADÉ la base. Trois défauts, trois filtres, chacun purement mécanique.
    # ------------------------------------------------------------------ #
    # 1. BOILERPLATE DE SITE — huit fiches de malrauxchambery.fr recevaient TOUTES le
    # même texte (« Malraux scène nationale Chambéry Savoie est un établissement de
    # création… ») : la description meta générique du site, servie à l'identique sur
    # chaque page. Remplacer un non-texte par un autre non-texte n'est pas un gain, et
    # donner la MÊME description à huit événements différents nourrit la rédaction et le
    # SEO de contenu dupliqué. Détection sans jugement : un texte proposé pour PLUSIEURS
    # fiches n'est, par construction, pas la description de l'une d'elles.
    from collections import Counter
    freq = Counter(_html_to_text(r["_nouvelle"]).strip().lower()[:300] for r in remplacements)
    partages = {t for t, n in freq.items() if n >= 2}

    retenus, douteux, rejetes = [], [], []
    for r in remplacements:
        cle = _html_to_text(r["_nouvelle"]).strip().lower()[:300]
        if cle in partages:
            r["_rejet"] = (f"description GÉNÉRIQUE du site — proposée à l'identique pour "
                           f"{freq[cle]} fiches")
            rejetes.append(r)
        elif _debris_navigation(r["_nouvelle"]):
            r["_rejet"] = "fil d'étiquettes / navigation, pas une description"
            rejetes.append(r)
        elif _titre_incoherent(r["title"] or "", r["_nouvelle"]) and not args.force_douteux:
            r["_rejet"] = "aucun mot commun avec le titre — la page décrit peut-être autre chose"
            douteux.append(r)
        else:
            retenus.append(r)
    remplacements = retenus

    if remplacements:
        print(f"--- {len(remplacements)} à RÉPARER ---")
        for r in remplacements:
            print(f"  [{r['id']}] WP#{r['wp_post_id_as']} {(r['title'] or '')[:52]}")
            print(f"        motif   : {r['_motif']}")
            print(f"        source  : {r['_provenance']} · {r['_url'][:70]}")
            print(f"        AVANT ({_text_len(r['description'] or ''):>4} car.) : "
                  f"{_apercu(r['description'])}")
            print(f"        APRÈS ({_text_len(r['_nouvelle']):>4} car.) : "
                  f"{_apercu(r['_nouvelle'])}")

    if rejetes:
        print(f"\n--- {len(rejetes)} ÉCARTÉE(S) — la page ne donne pas une description ---")
        for r in rejetes:
            print(f"  [{r['id']}] {(r['title'] or '')[:52]} — {r['_rejet']}")
            print(f"        proposé : {_apercu(r['_nouvelle'], 90)}")

    if douteux:
        print(f"\n--- {len(douteux)} À VALIDER À LA MAIN — non appliquée(s) par --apply ---")
        print("    (le texte récupéré ne partage aucun mot avec le titre : soit la page "
              "décrit\n     un AUTRE événement, soit la description est simplement "
              "reformulée. À trancher à l'œil.)")
        for r in douteux:
            print(f"  [{r['id']}] WP#{r['wp_post_id_as']} {(r['title'] or '')[:52]}")
            print(f"        source  : {r['_provenance']} · {r['_url'][:70]}")
            print(f"        AVANT ({_text_len(r['description'] or ''):>4} car.) : "
                  f"{_apercu(r['description'])}")
            print(f"        APRÈS ({_text_len(r['_nouvelle']):>4} car.) : "
                  f"{_apercu(r['_nouvelle'])}")
        print(f"    → pour en appliquer une après vérification : "
              f"--apply --ids {' '.join(str(r['id']) for r in douteux[:5])} --force-douteux")

    if sans_gain:
        print(f"\n--- {len(sans_gain)} SANS GAIN — non touchée(s) (la page ne donne pas "
              f"mieux que ce qu'on a) ---")
        for r, nouvelle in sans_gain:
            print(f"  [{r['id']}] {(r['title'] or '')[:52]} "
                  f"({_text_len(r['description'] or '')} → {_text_len(nouvelle)} car.)")

    if echecs:
        print(f"\n--- {len(echecs)} ÉCHEC(S) — description toujours cassée, à reprendre "
              f"à la main ---")
        for r, motif in echecs:
            print(f"  [{r['id']}] WP#{r['wp_post_id_as']} {(r['title'] or '')[:46]} : {motif}")
            print(f"        {r['_url'][:88]}")

    if not args.apply:
        print(f"\n(dry-run : rien écrit — relance avec --apply pour réparer les "
              f"{len(remplacements)}.)")
        conn.close()
        return 0

    for r in remplacements:
        # ⚠️ ON EFFACE AUSSI enrich_status='matiere_polluee' (ajouté le 2026-08-03, le jour
        # même où ce statut a été créé). `scripts/enrich.py` refuse désormais de rédiger une
        # fiche dont la description est un item Google News et dont aucune autre matière
        # n'est lisible — refus juste, mais sa sélection ne retient que les fiches à
        # `enrich_status` VIDE. Sans cette ligne, réparer la description ne servirait à
        # rien : la fiche resterait exclue de la file de rédaction pour toujours, avec
        # désormais une bonne description et aucune raison de ne pas l'utiliser.
        # C'est LE motif récurrent de ce dépôt — un état terminal qu'un script pose et
        # qu'aucun autre ne sait rouvrir. Il se referme ici, au seul endroit qui sait que
        # la CAUSE a disparu : celui qui vient de la faire disparaître.
        # On ne touche à aucun autre `enrich_status` : 'error', 'api_error' ou un
        # enrichissement réussi relèvent d'autre chose et ne nous regardent pas.
        conn.execute("UPDATE events_raw SET description=?, enrich_status="
                     "CASE WHEN enrich_status='matiere_polluee' THEN NULL ELSE enrich_status END "
                     "WHERE id=?", (r["_nouvelle"], r["id"]))
        log.info("[%s] description réparée (%s) : %d → %d car. visibles | AVANT « %s » | "
                 "APRÈS « %s »", r["id"], r["_provenance"],
                 _text_len(r["description"] or ""), _text_len(r["_nouvelle"]),
                 _apercu(r["description"], 80), _apercu(r["_nouvelle"], 80))
    conn.commit()
    conn.close()

    log.info("%d description(s) réparée(s) depuis leur page source.", len(remplacements))
    print(f"\n✅ {len(remplacements)} description(s) réparée(s) en base.")

    # La commande de republication ne doit contenir QUE des fiches DÉJÀ en ligne.
    # `publish_batch_as --ids` ignore les filtres habituels (statut, date, complétude,
    # cf. _select) et publie même ce qui ne l'a jamais été : y glisser une fiche sans
    # wp_post_id_as la CRÉERAIT sur le site. Piège vérifié en conditions réelles, même
    # traitement que dans scripts/repair_translation_dates.py.
    en_ligne = [r for r in remplacements if r["wp_post_id_as"]]
    jamais_publiees = [r for r in remplacements if not r["wp_post_id_as"]]

    if jamais_publiees:
        print(f"\n⚠️  {len(jamais_publiees)} JAMAIS publiée(s) — volontairement EXCLUE(S) "
              f"de la commande ci-dessous (les republier les CRÉERAIT sur le site) :")
        for r in jamais_publiees:
            print(f"     [{r['id']}] {(r['title'] or '')[:52]}")
        print("     Elles repasseront par le lot quotidien normal, quand elles le mériteront.")

    if en_ligne:
        ids = " ".join(str(r["id"]) for r in en_ligne)
        print(f"\nRepublie les {len(en_ligne)} déjà en ligne pour propager la correction :")
        print(f"   .venv/bin/python -m scripts.publish_batch_as --ids {ids} --skip-media")

    # La description polluée a aussi servi de MATIÈRE à la rédaction : republier remet la
    # bonne description (extrait WP) mais laisse l'article tel qu'il a été écrit.
    a_rerediger = [r for r in remplacements if (r.get("article_md") or "").strip()]
    if a_rerediger:
        print(f"\nℹ️  {len(a_rerediger)} de ces fiches ont un ARTICLE déjà rédigé à partir de "
              f"la description polluée (enrich.py agrège la matière des doublons). La "
              f"republication ne le réécrit pas : à relire, et à ré-enrichir au cas par cas "
              f"(coût API) si le texte parle du mauvais sujet :")
        print("     " + " ".join(str(r["id"]) for r in a_rerediger))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
