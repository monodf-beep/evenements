#!/usr/bin/env python3
"""Gel du TEXTE d'une fiche : poser, lever, lister, lire le journal.

D'OÙ ÇA VIENT — Franck, 2026-09-21 : « si cowork a travaillé le seo, on ne doit pas
pouvoir revenir dessus avec le cron ». L'ordre de travail est :

    création FR + IT  →  cron SEO (seo_batch)  →  reprise à la main / Cowork

et il ne va QUE dans ce sens. Une fiche « gelée » garde le titre, le corps, l'extrait et
les métas Yoast qu'on lui a donnés à la main ; le pipeline continue en revanche d'y
pousser tout le reste — dates, lieu, catégorie, territoire, métas as_*, image. Le gel
n'est donc PAS une mise à l'écart : la fiche reste vivante, seul son texte lui appartient.

QUI DÉCIDE — le SITE, jamais la base. C'est deploy/wordpress/cs-gel-texte.php qui détecte
la retouche (empreinte des six champs éditoriaux) et qui la fait respecter ; les colonnes
`wp_gel_*` d'events_raw n'en sont qu'une COPIE, entretenue par publish_batch_as et par le
`--sync` de ce script. Règle 1 de CLAUDE.md : un champ en base ne prouve rien sur l'état
du site — on interroge donc WordPress.

À QUOI ÇA SERT, CONCRÈTEMENT :
  • `--liste`  : la file des fiches garées, telle que le site la donne (le périmètre est
                 écrit à côté du nombre) ;
  • `--sync`   : recopie cette file dans la base, pour que seo_batch cesse tout de suite
                 de dépenser des appels LLM dessus — sans attendre une republication ;
  • `--gel`    : marque des fiches à la main. C'est le RATTRAPAGE : les fiches reprises
                 AVANT l'installation du mu-plugin n'ont pas d'empreinte de référence,
                 donc rien ne peut deviner qu'on y a touché. Leur liste d'ids est la
                 seule façon honnête de les protéger ;
  • `--degel`  : le rouvreur (CLAUDE.md règle 3) — rend la main au pipeline ;
  • `--journal`: qui a écrit quoi sur cette fiche, et quand.

DRY-RUN PAR DÉFAUT (règle 4) : --gel, --degel et --sync n'écrivent rien sans --apply.
Les ids sont des ids LOCAUX (events_raw) sauf avec --wp, qui prend des numéros de post
WordPress — c'est dans cette monnaie-là que parlent Cowork et l'admin du site.

Exemples :
  .venv/bin/python -m scripts.gel_texte --liste
  .venv/bin/python -m scripts.gel_texte --wp --gel 9378 9412 --motif "SEO Cowork 21/09" --apply
  .venv/bin/python -m scripts.gel_texte --degel 3588 --apply
  .venv/bin/python -m scripts.gel_texte --wp --journal 9378
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger                      # noqa: E402
from scripts.publisher_as import _headers                # noqa: E402

log = get_logger("gel_texte")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _wp():
    """(url, auth) du site Agenda Sabauda, ou (None, None) si la configuration manque."""
    load_dotenv(ROOT / ".env")
    url = os.getenv("WP_AS_URL", "").rstrip("/")
    user = os.getenv("WP_AS_USER", "")
    mdp = os.getenv("WP_AS_APP_PASSWORD", "")
    if not all([url, user, mdp]):
        log.error("WP_AS_URL / WP_AS_USER / WP_AS_APP_PASSWORD manquants dans .env")
        return None, None
    return url, (user, mdp)


def _appel(methode: str, route: str, params=None, corps=None):
    """Un appel REST au site. Renvoie le JSON, ou None — et DIT pourquoi.

    Un 404 sur ces routes-là a une seule cause utile et on l'écrit en toutes lettres :
    le mu-plugin n'est pas en ligne. C'est la règle 1 appliquée au code (un fichier
    poussé ne prouve pas qu'il est déployé) ; sans ce message, la sortie vide se lirait
    comme « aucune fiche gelée »."""
    url, auth = _wp()
    if not url:
        return None
    try:
        r = requests.request(methode, f"{url}/?rest_route={route}", params=params,
                             json=corps, auth=auth, headers=_headers(auth), timeout=60)
        if r.status_code == 404:
            log.error("404 sur %s — cs-gel-texte.php n'est PAS en ligne sur ce site. "
                      "Le contrôle de version : curl -s %s/wp-json/cs/v1/gel/version",
                      route, url)
            return None
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        log.error("Appel %s %s impossible : %s", methode, route, exc)
        return None


def _resoudre(conn, ids: list[int], en_wp: bool) -> list[tuple[int | None, int]]:
    """[(id local | None, wp_post_id)] — le site ne connaît que les seconds.

    Un id local sans `wp_post_id_as` n'est pas une erreur de frappe : c'est une fiche
    jamais publiée, donc rien à geler. On le DIT plutôt que de la laisser disparaître
    silencieusement de la liste (règle 6)."""
    out: list[tuple[int | None, int]] = []
    for i in ids:
        if en_wp:
            row = conn.execute("SELECT id FROM events_raw WHERE wp_post_id_as=?", (i,)).fetchone()
            out.append((row[0] if row else None, i))
            continue
        row = conn.execute("SELECT wp_post_id_as FROM events_raw WHERE id=?", (i,)).fetchone()
        if not row:
            log.warning("id local %s inconnu en base — ignoré.", i)
        elif not row[0]:
            log.warning("Fiche %s jamais publiée (pas de wp_post_id_as) — rien à geler.", i)
        else:
            out.append((i, int(row[0])))
    return out


def _ranger_local(conn, couples, gele: bool, motif: str) -> "tuple[int, list[int]]":
    """Recopie la décision dans events_raw, et REND CE QU'ELLE N'A PAS PU FAIRE.

    Ce n'est qu'un cache : il sert à ce que seo_batch cesse (ou reprenne) TOUT DE SUITE,
    sans attendre une republication.

    ⚠️ La première version se contentait de `continue` sur une fiche sans ligne locale,
    et le bilan annonçait « 48 marquée(s) » pour 49 demandées sans dire laquelle manquait
    (constaté en production le 21/09, au premier `--sync --apply` réel). C'est exactement
    la règle 6 : un état qui sort une fiche d'une file la sort aussi des bilans, et on le
    découvre des semaines plus tard. Les orphelines sont donc RENDUES et NOMMÉES."""
    n = 0
    orphelines: list[int] = []
    for local, wp_id in couples:
        if local is None:
            orphelines.append(wp_id)
            continue
        if gele:
            conn.execute("UPDATE events_raw SET wp_gel_at=datetime('now'), "
                         "wp_gel_champs='title,content,excerpt,seo', wp_gel_motif=? WHERE id=?",
                         (motif, local))
        else:
            conn.execute("UPDATE events_raw SET wp_gel_at=NULL, wp_gel_champs=NULL, "
                         "wp_gel_motif=NULL WHERE id=?", (local,))
        n += 1
    conn.commit()
    return n, orphelines


def cmd_liste(conn, args) -> int:
    data = _appel("GET", "/cs/v1/gel")
    if data is None:
        return 1
    fiches = data.get("fiches") or []
    print(f"{data.get('total', len(fiches))} fiche(s) au texte gelé "
          f"— périmètre : {data.get('perimetre', '?')}")
    for f in fiches:
        row = conn.execute("SELECT id, statut FROM events_raw WHERE wp_post_id_as=?",
                           (f["id"],)).fetchone()
        local = f"#{row[0]}" if row else "— (pas en base)"
        print(f"  WP#{f['id']:<6} {local:<10} {f.get('depuis', ''):<20} "
              f"{(f.get('motif') or '')[:28]:<28} {(f.get('titre') or '')[:50]}")
    if not fiches:
        # Un zéro doit dire d'où il vient (journal des erreurs du 11/08) : ici la route a
        # répondu, la file est donc vraiment vide — ce n'est pas une panne silencieuse.
        print("  (le site a répondu : aucune fiche gelée pour l'instant)")
    return 0


def cmd_sync(conn, args) -> int:
    """Site → base. Sens unique et volontaire : le site décide, la base recopie."""
    data = _appel("GET", "/cs/v1/gel")
    if data is None:
        return 1
    en_ligne = {int(f["id"]) for f in (data.get("fiches") or [])}
    locales = {int(r[1]): int(r[0]) for r in conn.execute(
        "SELECT id, wp_post_id_as FROM events_raw "
        "WHERE COALESCE(wp_gel_at,'') <> '' AND COALESCE(wp_post_id_as,0) > 0")}
    a_poser = en_ligne - set(locales)
    a_lever = set(locales) - en_ligne
    print(f"{len(en_ligne)} gelée(s) sur le site, {len(locales)} marquée(s) en base.")
    print(f"  à marquer en base : {sorted(a_poser) or '—'}")
    print(f"  à démarquer       : {sorted(a_lever) or '—'}")
    if not args.apply:
        print("\n(dry-run — rien écrit. Ajouter --apply.)")
        return 0
    couples_poser = [(conn.execute("SELECT id FROM events_raw WHERE wp_post_id_as=?",
                                   (w,)).fetchone(), w) for w in a_poser]
    n, orphelines = _ranger_local(conn, [(r[0] if r else None, w) for r, w in couples_poser],
                                  True, "recopié du site (--sync)")
    m, _ = _ranger_local(conn, [(locales[w], w) for w in a_lever], False, "")
    # RÈGLE 6 : on recompte en base plutôt que d'annoncer la longueur des listes.
    reste = conn.execute("SELECT COUNT(*) FROM events_raw "
                         "WHERE COALESCE(wp_gel_at,'') <> ''").fetchone()[0]
    print(f"\n{n} marquée(s), {m} démarquée(s) — {reste} gelée(s) en base après écriture.")
    if orphelines:
        # Une fiche EN LIGNE que la base ne connaît pas n'est pas une panne : le pipeline
        # ne la touche jamais (il itère sur events_raw), donc le gel du SITE la protège
        # déjà. Mais ça se DIT — c'est le seul indice qu'un wp_post_id_as a été perdu
        # (corbeille puis relink, adoption d'édition annuelle…), et cet indice-là ne se
        # représente nulle part ailleurs.
        print(f"\n⚠️ {len(orphelines)} fiche(s) gelée(s) sur le site sans ligne en base "
              f"(wp_post_id_as introuvable) : {orphelines}")
        print("   Le site les protège quand même ; le pipeline ne les touche pas. Mais "
              "vérifier qu'aucune n'a perdu son wp_post_id_as :")
        print("   .venv/bin/python -m scripts.audit_wp_ids_local_match")
    return 0


def cmd_gel(conn, args, poser: bool) -> int:
    ids = args.gel if poser else args.degel
    couples = _resoudre(conn, ids, args.wp)
    if not couples:
        print("Aucune fiche exploitable dans cette liste.")
        return 1
    verbe = "GELER" if poser else "DÉGELER"
    participe = "gelée(s)" if poser else "dégelée(s)"
    for local, wp_id in couples:
        titre = ""
        if local:
            row = conn.execute("SELECT title FROM events_raw WHERE id=?", (local,)).fetchone()
            titre = (row[0] or "")[:60] if row else ""
        print(f"  {verbe} WP#{wp_id} (#{local if local else '—'}) {titre}")
    if not args.apply:
        print(f"\n{len(couples)} fiche(s) SERAIENT {participe} (dry-run — ajouter --apply).")
        return 0
    route = "/cs/v1/gel" if poser else "/cs/v1/degel"
    rep = _appel("POST", route, corps={
        "post_ids": [w for _l, w in couples],
        "qui": args.qui,
        "motif": args.motif,
    })
    if rep is None:
        return 1
    # Ce que le SITE a effectivement fait, pas ce qu'on lui a demandé (règle 6).
    faits = rep.get("geles" if poser else "degeles") or []
    _ranger_local(conn, [(l, w) for l, w in couples if w in faits], poser, args.motif)  # noqa: RUF015
    print(f"\n{len(faits)} fiche(s) {participe} sur le site : {faits}")
    if len(faits) != len(couples):
        manquants = [w for _l, w in couples if w not in faits]
        print(f"⚠️ non traitées par le site (post inconnu ou pas un événement) : {manquants}")
    return 0


def cmd_journal(conn, args) -> int:
    couples = _resoudre(conn, [args.journal], args.wp)
    if not couples:
        return 1
    _local, wp_id = couples[0]
    data = _appel("GET", "/cs/v1/journal", params={"post_id": wp_id})
    if data is None:
        return 1
    gel = data.get("gel") or {}
    etat = (f"GELÉ depuis {gel.get('depuis')} ({gel.get('motif')})" if gel.get("gele")
            else "pas de gel — le pipeline réécrit le texte à chaque passage")
    print(f"WP#{wp_id} — {etat}\n")
    for e in data.get("journal") or []:
        print(f"  {e.get('at', ''):<20} {e.get('qui', ''):<12} {e.get('quoi', '')}")
    if not data.get("journal"):
        print("  (aucun passage enregistré — le journal commence à l'installation du "
              "mu-plugin, il ne reconstitue pas le passé)")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Gel du texte d'une fiche (site → base).")
    p.add_argument("--liste", action="store_true", help="La file des fiches gelées, depuis le site.")
    p.add_argument("--sync", action="store_true", help="Recopier cette file dans events_raw.")
    p.add_argument("--gel", type=int, nargs="+", help="Geler ces fiches (rattrapage).")
    p.add_argument("--degel", type=int, nargs="+", help="Rendre la main au pipeline.")
    p.add_argument("--journal", type=int, help="Lire le journal d'une fiche.")
    p.add_argument("--wp", action="store_true",
                   help="Les ids donnés sont des numéros de post WordPress, pas des ids locaux.")
    p.add_argument("--qui", default="franck", help="Qui agit (inscrit au journal).")
    p.add_argument("--motif", default="", help="Pourquoi (inscrit au journal).")
    p.add_argument("--apply", action="store_true", help="Écrire pour de vrai (défaut : dry-run).")
    args = p.parse_args(argv)

    if not any([args.liste, args.sync, args.gel, args.degel, args.journal is not None]):
        p.print_help()
        return 2

    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        if args.liste:
            return cmd_liste(conn, args)
        if args.sync:
            return cmd_sync(conn, args)
        if args.journal is not None:
            return cmd_journal(conn, args)
        if args.gel:
            return cmd_gel(conn, args, poser=True)
        return cmd_gel(conn, args, poser=False)
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
