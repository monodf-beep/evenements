#!/usr/bin/env python3
"""AUDIT (LECTURE SEULE) — les fiches FANTÔMES : en ligne sur le site, retirées du catalogue.

LE TROU QUE ÇA FERME. Toute la surveillance existante part de la BASE et va vers le
site : `scripts/site_audit.py` (cron 14h) relit ce que la base croit publié et vérifie
que le site est d'accord ; `scripts/reconcile_wp_deleted.py` cherche les posts DISPARUS
côté WordPress. Le sens inverse n'était couvert par rien : un post TOUJOURS EN LIGNE que
la base a écarté (`statut='rejected'`), fusionné (`duplicate_of` / `statut='merged'`), ou
qu'elle ne connaît pas du tout. Le visiteur voit alors une fiche que le catalogue
considère comme retirée, et aucune alarme ne sonne — au contraire :

  • `site_audit._publiees()` filtre explicitement `statut NOT IN ('merged','rejected')` :
    une fiche rejetée mais restée en ligne est INVISIBLE pour lui, par construction ;
  • `reconcile_wp_deleted` lit bien ces lignes, mais un post PUBLIC ne déclenche chez lui
    aucun signalement (il ne cherche que ce qui a disparu) ;
  • `scripts/evaluator.py`, `scripts/dedupe.py`, `scripts/purge_*.py`, le bouton « rejeter »
    du dashboard (app/app.py) posent `statut='rejected'`/`'merged'` SANS toucher au post
    WordPress ni à `wp_post_id_as` — le seul geste qui les corbeille est manuel. C'est
    exactement l'écart constaté le 2026-08-03 sur WP#6266 et WP#6268, tous deux
    `rejected` en base et pourtant en ligne.

CE QUE CE SCRIPT NE FAIT PAS. Il ne supprime rien, ne dépublie rien, n'écrit pas une
ligne : la base est ouverte en `mode=ro` (garantie SQLite, pas discipline du code) et
seules des requêtes GET partent vers WordPress. Il imprime, à la fin, une commande
`scripts.trash_wp_ids` TOUTE PRÊTE que Franck lance lui-même après relecture — et
`trash_wp_ids` est lui-même en dry-run tant qu'on n'ajoute pas `--apply`.

QUATRE CAS, distingués nettement :
  ① REJETÉ    — post en ligne ↔ ligne locale `statut='rejected'`   (écarté éditorialement)
  ② FUSIONNÉ  — post en ligne ↔ `duplicate_of` renseigné ou `statut='merged'`  (doublon)
  ③ ORPHELIN  — post en ligne ↔ AUCUNE ligne locale ne le pointe   (plus rien ne le pilote)
  ④ SAIN      — le cas normal : compté, jamais signalé.

GARDE-FOU CONTRE LA FAUSSE ALERTE (la leçon de la soirée du 2026-08-02). Un
`wp_post_id_as` peut pointer sur le MAUVAIS post : c'est précisément la raison d'être de
`scripts/relink_wp_ids_as.py` (site reconstruit → ids réattribués). Corbeiller sur la foi
d'un lien périmé retirerait un post innocent. Donc chaque paire (post en ligne ↔ ligne
rejetée/fusionnée) est confrontée SUR LE TITRE avant d'entrer dans la commande proposée.
La comparaison porte sur les trois titres possibles — `article_title`, le `titre` de
`enrich_data.article`, puis `title` brut — parce que c'est dans cet ordre que
`scripts/publisher.build_post()` choisit le titre RÉELLEMENT envoyé à WordPress :
comparer au seul `title` brut inventerait des divergences sur toute fiche enrichie. Une
paire au titre divergent est listée à part, JAMAIS dans la commande.

ACCÈS À WORDPRESS. Deux voies, la seconde en repli automatique :
  1. `cs/v1/list` (deploy/wordpress/cs-trash.php) — un seul appel, renvoie id/titre/
     statut/date/lieu/image pour les statuts draft|pending|future|publish|private. Ne
     renvoie JAMAIS la corbeille : parfait ici, on ne cherche que ce qui est visible.
  2. `wp-json/wp/v2/tribe_events` paginé (route WP core, le CPT est `show_in_rest`), si
     le snippet maison n'est pas installé ou répond mal.
Le front-end n'est PAS interrogé : il répond 404 pour un `tribe_events` vivant comme pour
un mort (cf. `reconcile_wp_deleted._etat`), il ne prouve rien.

Usage (sur le VPS, où .env est renseigné) :
    .venv/bin/python -m scripts.audit_wp_ghosts
    .venv/bin/python -m scripts.audit_wp_ghosts --tous-statuts    # + brouillons/planifiés
    .venv/bin/python -m scripts.audit_wp_ghosts --no-fuzzy        # sans rapprochement de titre
"""
from __future__ import annotations

import argparse
import difflib
import html
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger  # noqa: E402
from scripts.publisher_as import _headers  # noqa: E402

log = get_logger("audit_wp_ghosts")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Statuts WordPress réellement VISIBLES par un visiteur anonyme. 'private' n'en fait pas
# partie (réservé aux connectés) et 'future' est planifié : ni l'un ni l'autre ne sont
# « en ligne » au sens de la mission — ils n'entrent dans l'audit qu'avec --tous-statuts.
STATUTS_EN_LIGNE = ("publish",)
# En dessous, le lien base↔post est jugé SUSPECT et la paire sort de la commande proposée.
SEUIL_TITRE = 0.50
# Similarité minimale pour proposer une ligne locale comme candidate d'un orphelin.
SEUIL_CANDIDAT = 0.55


# --------------------------------------------------------------------------- #
# Lecture
# --------------------------------------------------------------------------- #
def _connect_ro(path: Path) -> sqlite3.Connection:
    """Connexion STRICTEMENT en lecture (URI `mode=ro`) : garantie par SQLite lui-même,
    pas par la discipline du code — ce script tourne sur la base de production.

    Repli : la base est en mode WAL (posé par scripts/scraper_events.init_db), et
    SQLite refuse parfois d'ouvrir un WAL en `mode=ro` quand le fichier `-shm`
    d'accompagnement n'existe pas encore (aucun autre processus connecté). Plutôt que
    de planter, on rouvre normalement AVEC `PRAGMA query_only=ON` : la protection reste
    posée par SQLite, au niveau de la connexion, pas par la bonne volonté du code."""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")   # force l'ouverture réelle
    except sqlite3.Error as exc:
        log.warning("Ouverture en mode=ro impossible (%s) — repli sur query_only=ON.", exc)
        conn = sqlite3.connect(str(path))
        conn.execute("PRAGMA query_only=ON")
    conn.row_factory = sqlite3.Row
    return conn


def _norm(s: str) -> str:
    """Titre normalisé : entités décodées, sans accents, minuscules, ponctuation aplatie.
    (Même recette que relink_wp_ids_as/_norm et diag_wp_orphans/_norm_title.)"""
    t = html.unescape(s or "")
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def fetch_cs_list(wp_url: str, auth) -> list[dict]:
    """Inventaire via la route maison cs/v1/list — un seul appel, hors corbeille."""
    resp = requests.get(f"{wp_url}/?rest_route=/cs/v1/list", auth=auth,
                        headers=_headers(auth), timeout=90)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError(f"réponse inattendue (type {type(data).__name__})")
    # html.unescape : get_the_title() renvoie les entités telles quelles (« F&ecirc;te »).
    # Sans ça, le rapport affiche du HTML brut là où Franck attend un titre lisible.
    return [{"id": int(e["id"]), "title": html.unescape(e.get("title") or ""),
             "status": e.get("status") or "", "start": (e.get("start") or "")[:10]}
            for e in data if str(e.get("id") or "").isdigit()]


def fetch_rest(wp_url: str, auth, tous_statuts: bool) -> list[dict]:
    """Repli : wp/v2/tribe_events PAGINÉ. La pagination est obligatoire — la route
    plafonne à 100 par page, et un `per_page=100` sans boucle (comme dans
    relink_wp_ids_as.fetch_wp_events) tronque silencieusement l'inventaire au-delà."""
    out: list[dict] = []
    statut = "any" if tous_statuts else "publish"
    for page in range(1, 51):          # garde-fou : 50 pages = 5 000 événements
        resp = requests.get(f"{wp_url}/wp-json/wp/v2/tribe_events",
                            params={"per_page": 100, "page": page, "status": statut,
                                    "_fields": "id,title,status,date"},
                            auth=auth, headers=_headers(auth), timeout=60)
        if resp.status_code == 400 and page > 1:
            break                      # « rest_post_invalid_page_number » = fin normale
        resp.raise_for_status()
        lot = resp.json()
        if not isinstance(lot, list) or not lot:
            break
        for it in lot:
            # `start` reste VIDE en repli : le champ `date` de wp/v2 est la date de
            # PUBLICATION du post, pas `_EventStartDate` (méta TEC, absente du payload
            # REST par défaut). L'afficher comme date d'événement serait un mensonge
            # d'affichage — mieux vaut un « — » assumé.
            out.append({"id": int(it["id"]),
                        "title": html.unescape((it.get("title") or {}).get("rendered") or ""),
                        "status": it.get("status") or "",
                        "start": ""})
        if len(lot) < 100:
            break
    return out


def inventaire(wp_url: str, auth, tous_statuts: bool) -> tuple[list[dict], str]:
    """(événements, libellé de la source utilisée). cs/v1/list d'abord, REST en repli."""
    try:
        return fetch_cs_list(wp_url, auth), "cs/v1/list (snippet maison)"
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        log.warning("cs/v1/list indisponible (%s) — repli sur wp/v2/tribe_events paginé.", exc)
    try:
        return fetch_rest(wp_url, auth, tous_statuts), "wp/v2/tribe_events (REST standard, paginé)"
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        log.error("wp/v2/tribe_events indisponible aussi (%s) — aucun inventaire possible.", exc)
        return [], ""


# --------------------------------------------------------------------------- #
# Rapprochement base ↔ site
# --------------------------------------------------------------------------- #
def titres_locaux(row: dict) -> list[str]:
    """Les titres qu'une ligne locale a pu donner au post WordPress, DANS L'ORDRE de
    scripts.publisher.build_post() : article_title, puis enrich_data.article.titre, puis
    title brut. Ignorer les deux premiers ferait passer toute fiche enrichie (donc la
    quasi-totalité du catalogue) pour un lien cassé."""
    cands = [(row.get("article_title") or "").strip()]
    if row.get("enrich_data"):
        try:
            art = (json.loads(row["enrich_data"]) or {}).get("article") or {}
            cands.append(str(art.get("titre") or "").strip())
        except (ValueError, TypeError):
            pass
    cands.append((row.get("title") or "").strip())
    return [c for c in cands if c]


def similarite(wp_title: str, row: dict) -> float:
    """Meilleure similarité entre le titre affiché sur WordPress et les titres possibles
    de la ligne locale. 1.0 = identique après normalisation."""
    cible = _norm(wp_title)
    if not cible:
        return 0.0
    return max((difflib.SequenceMatcher(None, cible, _norm(t)).ratio()
                for t in titres_locaux(row)), default=0.0)


def classe(row: dict) -> tuple[str, str] | None:
    """(catégorie, motif) pour une ligne locale, ou None si elle est saine.

    L'ordre compte : une ligne peut être à la fois rejetée et marquée doublon ; on
    annonce le rejet (décision éditoriale explicite) et on mentionne l'autre marque."""
    statut = (row.get("statut") or "").strip()
    dup = row.get("duplicate_of") or 0
    if statut == "rejected":
        return "REJETE", "statut='rejected'" + (f" + doublon de #{dup}" if dup else "")
    if statut == "merged" or dup:
        return "FUSIONNE", (f"statut='merged', doublon de #{dup}" if statut == "merged" and dup
                            else f"doublon de #{dup}" if dup else "statut='merged'")
    return None


def candidats(wp_title: str, rows: list[dict], normes: dict[int, str],
              top_n: int = 3) -> list[tuple[float, dict]]:
    """Lignes locales dont le titre ressemble à celui d'un post orphelin — pour trancher
    entre « post à corbeiller » et « lien wp_post_id_as à réparer » (relink_wp_ids_as)."""
    cible = _norm(wp_title)
    if not cible:
        return []
    # Un SEUL SequenceMatcher, la CIBLE en seq2 (le seul côté dont l'index interne est
    # mis en cache) + les bornes supérieures real_quick_ratio/quick_ratio en pré-filtre :
    # elles ne peuvent que SURESTIMER la similarité, donc écarter dessus ne perd aucun
    # candidat. Sans ça, 40 orphelins × quelques milliers de lignes = plusieurs secondes.
    sm = difflib.SequenceMatcher()
    sm.set_seq2(cible)
    scored: list[tuple[float, dict]] = []
    for r in rows:
        n = normes.get(r["id"])
        if not n:
            continue
        sm.set_seq1(n)
        if sm.real_quick_ratio() < SEUIL_CANDIDAT or sm.quick_ratio() < SEUIL_CANDIDAT:
            continue
        ratio = sm.ratio()
        if ratio >= SEUIL_CANDIDAT:
            scored.append((ratio, r))
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[:top_n]


# --------------------------------------------------------------------------- #
# Sortie
# --------------------------------------------------------------------------- #
def _ligne(post: dict, row: dict | None, motif: str, sim: float | None) -> str:
    titre = (post.get("title") or "")[:52]
    base = f"  WP#{post['id']:<6} {post.get('start') or '—':<10} « {titre:<52} »"
    if row is not None:
        base += f"  ↔ id local {row['id']:<6} · {motif}"
        if sim is not None:
            base += f" · titre {sim:.2f}"
    return base


def _cmd(ids: list[int]) -> str:
    return ".venv/bin/python -m scripts.trash_wp_ids " + " ".join(str(i) for i in ids)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Audit LECTURE SEULE : posts en ligne que la base a rejetés, fusionnés "
                    "ou qu'elle ne connaît pas.")
    p.add_argument("--tous-statuts", action="store_true",
                   help="Inclure aussi brouillons/planifiés/privés (défaut : seulement "
                        "les posts publiés, ceux qu'un visiteur voit).")
    p.add_argument("--limit", type=int, default=60,
                   help="Nombre de lignes détaillées par catégorie (défaut 60).")
    p.add_argument("--no-fuzzy", action="store_true",
                   help="Ne pas chercher de ligne locale ressemblante pour les orphelins.")
    p.add_argument("--fuzzy-cap", type=int, default=40,
                   help="Nombre d'orphelins pour lesquels on cherche des candidats (défaut 40).")
    p.add_argument("--seuil-titre", type=float, default=SEUIL_TITRE,
                   help=f"En dessous, le lien base↔post est jugé suspect (défaut {SEUIL_TITRE}).")
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n"
              f"(data/ est hors dépôt Git — lancer ce script sur le VPS.)")
        return 1

    load_dotenv(ROOT / ".env")
    wp_url = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    if not all(auth):
        log.error("WP_AS_USER / WP_AS_APP_PASSWORD manquants dans .env — cs/v1/list exige "
                  "une authentification et le repli REST ne verrait pas les non-publics.")
        return 1

    events, source = inventaire(wp_url, auth, args.tous_statuts)
    if not events:
        log.error("Inventaire WordPress vide ou inaccessible — aucune conclusion possible. "
                  "RIEN n'est affirmé plutôt que d'affirmer à tort.")
        return 1

    # cs/v1/list ne renvoie déjà pas la corbeille ; on écarte quand même trash/auto-draft
    # et les statuts vides, au cas où l'inventaire vienne du repli REST.
    retenus = (set(STATUTS_EN_LIGNE) if not args.tous_statuts
               else {e.get("status") or "" for e in events} - {"trash", "auto-draft", ""})
    en_ligne = [e for e in events if (e.get("status") or "") in retenus]

    conn = _connect_ro(DB_PATH)
    rows = [dict(r) for r in conn.execute("SELECT * FROM events_raw")]
    conn.close()

    # Index wp_post_id_as → lignes locales. Une LISTE, pas un dict : plusieurs lignes
    # peuvent pointer le même post (traduction mal liée, relink partiel) — l'écraser
    # silencieusement masquerait justement l'anomalie.
    par_wp: dict[int, list[dict]] = {}
    for r in rows:
        wp = r.get("wp_post_id_as") or 0
        if wp:
            par_wp.setdefault(int(wp), []).append(r)

    rejetes, fusionnes, orphelins, suspects, sains, multiples = [], [], [], [], [], []
    for post in en_ligne:
        liees = par_wp.get(post["id"], [])
        if not liees:
            orphelins.append(post)
            continue
        if len(liees) > 1:
            multiples.append((post, liees))
        verdicts = [(r, classe(r)) for r in liees]
        anormaux = [(r, v) for r, v in verdicts if v]
        if not anormaux or len(anormaux) < len(verdicts):
            # Au moins une ligne SAINE pointe ce post : le catalogue le pilote toujours.
            # On ne signale pas — signaler ici, ce serait proposer de retirer une fiche
            # vivante parce qu'un doublon fusionné partage son lien.
            sains.append(post)
            continue
        row, (cat, motif) = anormaux[0]
        sim = similarite(post.get("title") or "", row)
        if sim < args.seuil_titre:
            suspects.append((post, row, f"{motif} — mais titre divergent", sim))
        elif cat == "REJETE":
            rejetes.append((post, row, motif, sim))
        else:
            fusionnes.append((post, row, motif, sim))

    # --- SECONDE PASSE : L'ANGLE MORT DE L'INVENTAIRE ---------------------- #
    # ⚠️ AJOUTÉE LE 2026-08-03, APRÈS QUE CET AUDIT A ANNONCÉ « 0 » À TORT.
    # Le matin même il affichait « ① REJETÉS : 0 — rien à retirer 🎉 ». Onze fiches
    # étaient pourtant `rejected` en base ET `publish` sur le site. Mesuré :
    #   WP#617 « Beach Sport Festival 2026 » → HTTP 200, status=publish, titre identique
    #   au titre local ; et absent de TOUS les inventaires (cs/v1/list comme wp/v2).
    # CAUSE : The Events Calendar exclut les événements PASSÉS de ses collections. WP#617
    # s'est terminé le 2026-07-26 ; sa page reste publiée et accessible, mais elle
    # n'apparaît plus dans aucune liste. Tout audit qui part d'un INVENTAIRE est donc
    # structurellement aveugle aux fiches passées restées en ligne — et ce sont
    # justement celles qui traînent le plus longtemps, puisque personne ne les croise.
    #
    # On complète donc par l'autre bout : partir des lignes LOCALES anormales qui
    # revendiquent un post, et interroger chacune PAR SON NUMÉRO — la seule requête que
    # le filtre de date n'atteint pas. Périmètre étroit (rejetées/fusionnées non déjà
    # appariées), donc quelques dizaines d'appels, pas des centaines.
    deja_vus = {p["id"] for p in en_ligne}
    a_sonder = [r for r in rows
                if (r.get("wp_post_id_as") or 0)
                and int(r["wp_post_id_as"]) not in deja_vus
                and classe(r) is not None]
    if a_sonder:
        log.info("Angle mort de l'inventaire : %d ligne(s) rejetée(s)/fusionnée(s) "
                 "revendiquent un post absent des listes — vérification une par une.",
                 len(a_sonder))
    for i, row in enumerate(a_sonder, 1):
        wp_id = int(row["wp_post_id_as"])
        try:
            rep = requests.get(f"{wp_url}/wp-json/wp/v2/tribe_events/{wp_id}",
                               params={"_fields": "id,title,status,link"},
                               auth=auth, headers=_headers(auth), timeout=20)
        except requests.RequestException:
            continue                       # panne réseau : on n'affirme rien
        if rep.status_code != 200:
            continue                       # corbeille ou supprimé : pas notre sujet
        try:
            post = rep.json() or {}
        except ValueError:
            continue
        if (post.get("status") or "") not in STATUTS_EN_LIGNE:
            continue
        post = {"id": wp_id, "title": (post.get("title") or {}).get("rendered", ""),
                "link": post.get("link", ""), "status": post.get("status", ""),
                "date": "", "_hors_inventaire": True}
        cat, motif = classe(row)
        sim = similarite(post["title"], row)
        motif += " · PASSÉ, absent des listes"
        if sim < args.seuil_titre:
            suspects.append((post, row, f"{motif} — mais titre divergent", sim))
        elif cat == "REJETE":
            rejetes.append((post, row, motif, sim))
        else:
            fusionnes.append((post, row, motif, sim))
        if i < len(a_sonder):
            time.sleep(0.3)     # courtoisie envers l'hébergement mutualisé

    # --- Rapport ---------------------------------------------------------- #
    print("=" * 92)
    print("FICHES FANTÔMES — en ligne sur le site, retirées du catalogue (LECTURE SEULE)")
    print("=" * 92)
    print(f"Site                                     : {wp_url}")
    print(f"Inventaire WordPress                     : {source}")
    if source.startswith("wp/v2"):
        print("  ⚠ repli REST : la date d'ÉVÉNEMENT (_EventStartDate) n'est pas exposée")
        print("    par cette route — la colonne date restera « — ». Installer/réparer")
        print("    deploy/wordpress/cs-trash.php la rétablit.")
    print(f"Base (ouverte en mode=ro)                : {DB_PATH}")
    print(f"Événements inventoriés (hors corbeille)  : {len(events)}")
    print(f"  · retenus comme « en ligne »           : {len(en_ligne)}  "
          f"(statuts : {', '.join(sorted(retenus))})")
    print(f"Lignes locales pointant un post          : {len(par_wp)}")
    print()
    print(f"① REJETÉS   (écartés éditorialement, toujours visibles) : {len(rejetes)}")
    print(f"② FUSIONNÉS (doublons fusionnés, toujours visibles)     : {len(fusionnes)}")
    print(f"③ ORPHELINS (aucune ligne locale ne les pilote)         : {len(orphelins)}")
    print(f"④ SAINS     (cas normal, non signalés)                  : {len(sains)}")
    if suspects:
        print(f"⚠  LIEN SUSPECT (base anormale MAIS titre divergent)    : {len(suspects)}")
    print()

    def _bloc(titre: str, lot: list, avec_lien: bool = True) -> None:
        print(f"--- {titre} ({len(lot)}) ---")
        if not lot:
            print("  (aucun)")
            print()
            return
        for item in lot[:args.limit]:
            if avec_lien:
                post, row, motif, sim = item
                print(_ligne(post, row, motif, sim))
            else:
                print(_ligne(item, None, "", None))
        if len(lot) > args.limit:
            print(f"  … et {len(lot) - args.limit} autre(s) (--limit pour en voir plus)")
        print()

    _bloc("① EN LIGNE mais REJETÉ en base", rejetes)
    _bloc("② EN LIGNE mais FUSIONNÉ en base", fusionnes)

    print(f"--- ③ EN LIGNE et ORPHELIN — aucun wp_post_id_as ne pointe dessus "
          f"({len(orphelins)}) ---")
    if not orphelins:
        print("  (aucun)")
    else:
        normes = {r["id"]: _norm((r.get("title") or "")) for r in rows}
        for i, post in enumerate(orphelins[:args.limit]):
            print(_ligne(post, None, "", None))
            if args.no_fuzzy or i >= args.fuzzy_cap:
                continue
            for ratio, r in candidats(post.get("title") or "", rows, normes):
                lien = (f"wp_post_id_as={r['wp_post_id_as']}" if (r.get("wp_post_id_as") or 0)
                        else "wp_post_id_as=NULL")
                print(f"        ↳ candidat local id={r['id']} ({lien}, statut={r.get('statut')}) "
                      f"similarité={ratio:.2f} « {(r.get('title') or '')[:56]} »")
        if len(orphelins) > args.limit:
            print(f"  … et {len(orphelins) - args.limit} autre(s) (--limit pour en voir plus)")
    print()

    if suspects:
        print(f"--- ⚠ LIEN SUSPECT — la ligne locale est rejetée/fusionnée, MAIS son titre ne "
              f"correspond pas au post ({len(suspects)}) ---")
        print("    Le lien wp_post_id_as pointe probablement sur le MAUVAIS post (ids")
        print("    réattribués : c'est le cas que scripts/relink_wp_ids_as.py répare).")
        print("    VOLONTAIREMENT EXCLUS de la commande ci-dessous : corbeiller sur la foi")
        print("    d'un lien périmé retirerait un post innocent.")
        for post, row, motif, sim in suspects[:args.limit]:
            print(_ligne(post, row, motif, sim))
        print()

    if multiples:
        print(f"--- ℹ PLUSIEURS lignes locales pointent le même post ({len(multiples)}) ---")
        print("    Information, pas alerte : à vérifier avec scripts/relink_wp_ids_as.py.")
        for post, liees in multiples[:args.limit]:
            ids = ", ".join(f"{r['id']}({r.get('statut')})" for r in liees)
            print(_ligne(post, None, "", None) + f"  ↔ ids locaux : {ids}")
        print()

    # --- Suite à donner ---------------------------------------------------- #
    print("=" * 92)
    print("RIEN N'A ÉTÉ SUPPRIMÉ NI DÉPUBLIÉ — aucune écriture, ni en base (mode=ro), ni sur")
    print("WordPress (requêtes GET uniquement). Les commandes ci-dessous sont À LANCER À LA")
    print("MAIN, après relecture ; scripts.trash_wp_ids est lui-même en DRY-RUN tant qu'on")
    print("n'ajoute pas --apply, et la corbeille WordPress reste réversible.")
    print()
    sûrs = [p["id"] for p, _r, _m, _s in rejetes] + [p["id"] for p, _r, _m, _s in fusionnes]
    if sûrs:
        print(f"① + ② — {len(sûrs)} post(s) que la base a écartés et dont le titre confirme le "
              f"lien :")
        print(f"      {_cmd(sûrs)}")
        if len(sûrs) > 50:
            print("      (liste longue : la découper en plusieurs appels si le shell rechigne)")
        print()
    else:
        print("① + ② — aucune fiche écartée n'a été trouvée en ligne.")
        print("    (dit sobrement : le 2026-08-03 ce même message s'affichait alors que")
        print("     ONZE fiches rejetées étaient publiées — l'inventaire de WordPress")
        print("     omet les événements PASSÉS. La seconde passe par numéro corrige cet")
        print("     angle mort, mais un audit ne prouve jamais une absence.)")
        print()
    if orphelins:
        print(f"③ — {len(orphelins)} orphelin(s). NE PAS corbeiller en bloc : un orphelin peut")
        print("    être un post créé à la main dans WordPress (parfaitement légitime), ou une")
        print("    fiche dont le lien wp_post_id_as a sauté — auquel cas c'est le LIEN qu'il")
        print("    faut réparer, pas le post qu'il faut retirer :")
        print("      .venv/bin/python -m scripts.relink_wp_ids_as          # diagnostic (dry-run)")
        print("    Après relecture un par un, pour ceux qu'on décide vraiment de retirer :")
        print(f"      {_cmd([p['id'] for p in orphelins[:args.limit]])}")
        print()
    print("Réparer la BASE plutôt que le site est parfois le bon geste : une fiche rejetée à")
    print("tort se répare en la re-classant depuis le dashboard, et elle redevient alors")
    print("légitimement en ligne — sans rien toucher côté WordPress.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
