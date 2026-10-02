#!/usr/bin/env python3
"""Où le vocabulaire interdit est-il DÉJÀ publié ?

LECTURE SEULE. Aucun réseau, aucun appel LLM, aucune écriture.

D'OÙ ÇA VIENT. Franck, 2026-08-21, en lisant une page en ligne :
« de l'ancienne capitale du royaume de Sardaigne […] ne jamais mettre "royaume de
Sardaigne" mais mettre "les États de Savoie" ».

POURQUOI UN AUDIT EN PLUS DES PROMPTS. « Venise des Alpes » était interdit dans QUATRE
prompts de rédaction — et il a quand même été écrit, généré, publié, puis trouvé en ligne
le 2026-08-18. Une consigne de prompt agit sur ce qu'on écrira demain ; elle ne dit rien
de ce qui est déjà en ligne. Il faut les deux.

⚠️ CE RELEVÉ NE REMPLACE RIEN, ET NE DOIT PAS. Une expression interdite peut être le titre
officiel d'une exposition ou une citation : « Il Regno di Sardegna » sur l'affiche d'un
musée n'est pas notre prose. C'est pourquoi chaque ligne montre LA PHRASE — sans elle,
personne ne peut distinguer les deux, et une réécriture automatique abîmerait un nom propre.

PÉRIMÈTRE : les fiches liées à un post, TOUTES DATES. Contrairement aux files de travail,
celle-ci ignore la règle 5 exprès — une page publiée reste lisible et indexée des années
après l'événement, et c'est le TEXTE qu'on corrige, pas l'annonce.

CE PÉRIMÈTRE A UN TROU, COMBLÉ LE 2026-09-06. Ce script ne lisait QUE `events_raw` — les
guides et les curiosités (des posts WordPress autonomes, publiés directement via
`wp_insert_post`, sans ligne correspondante dans `events_raw`) n'étaient jamais examinés.
Trouvé en corrigeant à la main « royaume de Sardaigne » dans le guide WP#2420 (« Expositions
à Turin 2026 ») : le terme y vivait depuis la création du guide, invisible pour ce script.
Le zéro qu'il annonçait n'était donc pas « rien à corriger », il était « rien cherché à cet
endroit » — exactement la faute que ce script existe pour éviter côté événements. Les guides
et les curiosités sont maintenant lus en plus, par l'API REST publique (lecture seule, sans
identifiant), et RAPPORTÉS SÉPARÉMENT du compte events_raw : un compteur doit dire ce qu'il
compte (règle 6), fusionner les deux aurait produit un total qui ne correspond à rien qu'on
puisse corriger d'un même geste.

Usage :
    .venv/bin/python -m scripts.audit_vocabulaire
    .venv/bin/python -m scripts.audit_vocabulaire --slack
"""
from __future__ import annotations
import argparse
import html
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.vocabulaire import interdits, remplacement, trouver
from scripts.panel_site import GUIDES_SLUGS, LANGUES

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
BASE_URL = "https://agendasabauda.eu"
FETCH_TIMEOUT = 20
_UA = {"User-Agent": "Mozilla/5.0 (compatible; AgendaSabaudaBot/1.0)"}

# Slugs VÉRIFIÉS le 2026-09-06 (création réelle des catégories dans cette même session,
# id 715 fr « curiosites » / id 717 it « curiosita », liés comme traductions Polylang) —
# jamais devinés, cf. l'avertissement de GUIDES_SLUGS sur la moitié perdue silencieusement
# quand un slug italien suffixé n'est pas cherché explicitement.
CURIOSITES_SLUGS = ("curiosites", "curiosita")

# (libellé affiché, slugs de la catégorie) — une entrée par famille d'articles hors agenda,
# chacune comptée et rapportée à part.
ARTICLE_CATEGORIES = (
    ("guides", GUIDES_SLUGS),
    ("curiosités", CURIOSITES_SLUGS),
)


def _articles_depuis_payload(posts: list[dict]) -> list[dict]:
    """Transforme la réponse REST (title.rendered, content.rendered) en {id, link, texte}.

    Fonction PURE, testable sans réseau — même contrat que
    `scripts.panel_site.guides_depuis_payload`, mais garde aussi le CORPS, pas seulement
    le titre : c'est le corps qui porte le vocabulaire interdit.
    """
    out, vus = [], set()
    for p in posts:
        pid = p.get("id")
        if pid is None or pid in vus:
            continue
        vus.add(pid)
        link = p.get("link") or ""
        if not link:
            continue
        titre_brut = (p.get("title") or {}).get("rendered") or ""
        corps_brut = (p.get("content") or {}).get("rendered") or ""
        titre = html.unescape(re.sub(r"<[^>]+>", "", titre_brut)).strip()
        corps = html.unescape(re.sub(r"<[^>]+>", " ", corps_brut))
        corps = re.sub(r"\s+", " ", corps).strip()
        # Même précaution que _texte() plus bas pour events_raw : chaque morceau CLOS
        # par un point avant collage, sinon le titre bave sur le corps dans l'extrait.
        morceaux = [m if m.endswith((".", "!", "?", "…")) else m + "."
                    for m in (titre, corps) if m]
        out.append({"id": pid, "link": link, "titre": titre, "texte": " ".join(morceaux)})
    return out


def _articles_wp(slugs: tuple[str, ...], base: str = BASE_URL) -> tuple[list[dict], list[str]]:
    """Les articles publiés d'une catégorie (identifiée par ses slugs), toutes langues.

    Lecture PUBLIQUE (status=publish), aucun identifiant nécessaire — même mécanisme que
    `scripts.panel_site.guides_publies`, étendu pour ramener aussi `content`. Rend
    (articles, langues_en_échec) : une langue en échec n'est PAS un zéro silencieux, elle
    est nommée, pour ne pas rejouer la faute du 17/08 (moitié de liste perdue sans le dire).
    """
    import requests
    posts, vus, langues_echec = [], set(), []
    for langue in LANGUES:
        try:
            cats = requests.get(f"{base}/wp-json/wp/v2/categories",
                                 params={"slug": ",".join(slugs), "per_page": 20,
                                         "lang": langue},
                                 timeout=FETCH_TIMEOUT, headers=_UA)
            cats.raise_for_status()
            ids = [c["id"] for c in cats.json() or []]
        except (requests.RequestException, ValueError, KeyError, TypeError):
            langues_echec.append(langue)
            continue
        if not ids:
            continue
        try:
            r = requests.get(f"{base}/wp-json/wp/v2/posts",
                              params={"categories": ",".join(map(str, ids)), "per_page": 100,
                                      "status": "publish", "lang": langue,
                                      "_fields": "id,link,title,content"},
                              timeout=FETCH_TIMEOUT, headers=_UA)
            r.raise_for_status()
            for p in r.json() or []:
                if p.get("id") not in vus:
                    vus.add(p.get("id"))
                    posts.append(p)
        except (requests.RequestException, ValueError):
            langues_echec.append(langue)
    return _articles_depuis_payload(posts), langues_echec


def _texte(ev: dict) -> str:
    parts = [ev.get("article_title") or ev.get("title") or ""]
    if ev.get("enrich_data"):
        try:
            art = (json.loads(ev["enrich_data"]) or {}).get("article") or {}
            parts += [art.get("chapo") or "", art.get("corps") or ""]
        except (ValueError, TypeError):
            pass
    # Chaque morceau est CLOS par un point avant d'être collé au suivant. Sans ça, le
    # titre bave sur le chapô et l'extrait rendu commence par le titre — « Palazzo Madama
    # Vestige de la capitale du royaume de Sardaigne. » Trouvé en écrivant la fixture :
    # l'extrait doit montrer LA phrase fautive, pas son voisinage.
    clos = [p.strip() if p.strip().endswith((".", "!", "?", "…")) else p.strip() + "."
            for p in parts if p and p.strip()]
    return " ".join(clos)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Vocabulaire interdit déjà publié. Lecture seule.")
    p.add_argument("--slack", action="store_true", help="Verdict dans la boîte du jour.")
    p.add_argument("--exemples", type=int, default=12)
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n(lancer ce script sur le VPS.)")
        return 1

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL AND wp_deleted_at IS NULL")]
    conn.close()

    trouvailles: list[tuple[dict, str, str]] = []
    par_expression: Counter = Counter()
    for ev in rows:
        for expression, phrase in trouver(_texte(ev)):
            trouvailles.append((ev, expression, phrase))
            par_expression[expression] += 1

    print("=" * 78)
    print("VOCABULAIRE INTERDIT — ce qui est déjà en ligne")
    print("=" * 78)
    print(f"Fiches liées à un post : {len(rows)} (toutes dates — une page publiée reste "
          f"lisible\n                         des années après l'événement)")
    print(f"Expressions surveillées : {len(interdits())} — "
          f"{', '.join(e['expression'] for e in interdits())}")
    print(f"FICHES CONCERNÉES       : {len(trouvailles)}")
    print()

    if not trouvailles:
        print(f"Aucune occurrence sur les {len(rows)} fiches examinées.")
        print("Ce zéro dit son dénominateur : il vient d'un corpus lu, pas d'une requête")
        print("vide. Il ne couvre que les fiches liées à un événement — les guides et")
        print("curiosités sont examinés séparément ci-dessous.")
    else:
        for expression, n in par_expression.most_common():
            rempl = remplacement(expression)
            quoi = f" → « {rempl} »" if rempl else " → à supprimer, on nomme la chose"
            print(f"### « {expression} » — {n} fiche(s){quoi}\n")
            lot = [(e, ph) for e, ex, ph in trouvailles if ex == expression]
            for ev, phrase in lot[:args.exemples]:
                print(f"- WP#{ev['wp_post_id_as']:<6} {(ev.get('article_title') or ev.get('title') or '')[:44]}")
                print(f"    « …{phrase}… »")
            if len(lot) > args.exemples:
                print(f"- …et {len(lot) - args.exemples} autre(s).")
            print()
        print("⚠️ LIRE LA PHRASE AVANT DE CORRIGER. Une expression interdite peut être le")
        print("   titre officiel d'une exposition ou une citation — ce n'est alors pas")
        print("   notre prose, et la réécrire abîmerait un nom propre.")

    # ── Guides et curiosités : hors agenda, hors events_raw, comptés À PART ─────────
    # Un compteur doit dire ce qu'il compte (règle 6) : fusionner ce total avec celui
    # des fiches événements produirait un chiffre qu'aucun geste unique ne corrige — les
    # deux familles vivent dans des tables et des interfaces différentes.
    resume_articles: list[tuple[str, int, int]] = []  # (label, examinés, concernés)
    for label, slugs in ARTICLE_CATEGORIES:
        print("-" * 78)
        try:
            articles, langues_echec = _articles_wp(slugs)
        except Exception as exc:  # noqa: BLE001 — un souci réseau ne doit jamais ressembler à un zéro
            print(f"NON VÉRIFIÉ — {label} : API WordPress injoignable ({exc}).")
            print("Ce silence ne veut PAS dire « aucune occurrence » : c'est un échec de")
            print("lecture, pas une absence de cas — à relancer.")
            continue
        if langues_echec:
            print(f"⚠️ {label} : langue(s) non interrogée(s) ({', '.join(langues_echec)}) "
                  f"— liste probablement INCOMPLÈTE.")
        trouvailles_art: list[tuple[dict, str, str]] = []
        par_expression_art: Counter = Counter()
        for art in articles:
            for expression, phrase in trouver(art["texte"]):
                trouvailles_art.append((art, expression, phrase))
                par_expression_art[expression] += 1
        resume_articles.append((label, len(articles), len(trouvailles_art)))
        print(f"{label.capitalize()} publié(e)s (hors agenda) : {len(articles)} examiné(e)s "
              f"— {len(trouvailles_art)} concerné(e)(s)")
        if not articles:
            print("(0 examiné — vérifier que le slug de catégorie n'a pas changé avant de")
            print(" lire ce zéro comme « rien à signaler ».)")
        for expression, n in par_expression_art.most_common():
            rempl = remplacement(expression)
            quoi = f" → « {rempl} »" if rempl else " → à supprimer, on nomme la chose"
            print(f"  ### « {expression} » — {n} article(s){quoi}")
            lot = [(a, ph) for a, ex, ph in trouvailles_art if ex == expression]
            for art, phrase in lot[:args.exemples]:
                print(f"  - {art['link']}")
                print(f"      « …{phrase}… »")
            if len(lot) > args.exemples:
                print(f"  - …et {len(lot) - args.exemples} autre(s).")
        print()

    if args.slack:
        from utils import slack
        detail = " · ".join(f"{e} : {n}" for e, n in par_expression.most_common(3))
        detail_articles = " · ".join(
            f"{label} : {concernes}/{examines}" for label, examines, concernes in resume_articles)
        slack.notify(
            f"🗣 *Vocabulaire interdit* — sur {len(rows)} fiches publiées :\n"
            f"{'🔴' if trouvailles else '·'} {len(trouvailles)} fiche(s) concernée(s)"
            + (f"\n   {detail}" if detail else "")
            + (f"\nHors agenda (guides/curiosités) : {detail_articles}" if resume_articles else "")
            + "\n_Chaque cas se lit avec sa phrase : ça peut être le titre officiel d'une "
              "exposition, pas notre prose._")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
