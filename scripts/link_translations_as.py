#!/usr/bin/env python3
"""Lie les traductions FR↔IT sur Agenda Sabauda (Polylang) — site bilingue.

Beaucoup de sources valdôtaines (et parfois transfrontalières) publient le MÊME
événement en français ET en italien. On NE les fusionne PAS (dedupe reste mono-langue) :
ce sont deux fiches à LIER comme traductions l'une de l'autre via Polylang, pour que le
sélecteur de langue et les hreflang fonctionnent.

Appariement CONSERVATEUR (aucun LLM) : deux événements déjà publiés sur l'Agenda
(wp_post_id_as) forment une paire s'ils sont dans le MÊME territoire, de LANGUE
DIFFÉRENTE (utils.lang), et fortement liés par le CONTENU :
  • même image source (signal le plus fort : les versions FR/IT partagent l'affiche), OU
  • titres « même histoire » (noms propres partagés) ET même date de début.
Le liage est envoyé à l'endpoint WordPress cs/v1/link-translations (pll_save_post_
translations). PAR DÉFAUT : simulation (on affiche les paires). --apply pour exécuter.
"""
from __future__ import annotations

import argparse
import base64
import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.lang import detect_lang
from utils.sources import is_logo_image
from scripts.dedupe import cross_lang_same
from scripts.scraper_events import init_db

log = get_logger("link_translations_as")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}


def _norm_image(url: str) -> str:
    """Clé d'image normalisée (hôte+chemin, sans query) — "" si logo/vide/BANNIÈRE DE
    REPLI. Une bannière générique (`fallback-{territoire}-{catégorie}.png`, posée par
    `pick_banner_image` quand aucune vraie photo n'a été trouvée) est PARTAGÉE par tous
    les événements sans image d'un même territoire/catégorie — la traiter comme un signal
    d'affiche commune agrégerait des événements sans rapport (bug constaté : Jamiroquai,
    Candlelight ABBA, Funky Académie… tous « liés » par la même bannière Savoie/concerts)."""
    url = (url or "").strip()
    if not url or is_logo_image(url):
        return ""
    path = urlparse(url.lower()).path
    if path.rsplit("/", 1)[-1].startswith("fallback-"):
        return ""
    p = urlparse(url.lower())
    return f"{p.netloc}{p.path}"


def _lang(ev: dict) -> str:
    return detect_lang(ev.get("title", ""), ev.get("description", ""),
                       ev.get("territoire", ""))


def _match(a: dict, b: dict) -> bool:
    """Deux événements sont-ils une paire de traductions (conservateur) ?"""
    if a["id"] == b["id"]:
        return False
    if (a.get("territoire") or "") != (b.get("territoire") or ""):
        return False
    if _lang(a) == _lang(b):
        return False                                   # même langue → pas une traduction
    img_a, img_b = _norm_image(a.get("url_image")), _norm_image(b.get("url_image"))
    if img_a and img_a == img_b:
        return True                                    # même affiche = signal fort
    # Sinon : titres « même histoire » (noms propres partagés) ET même date de début.
    da = (a.get("date_event_start") or "").strip()
    db = (b.get("date_event_start") or "").strip()
    if da and da == db and cross_lang_same(a.get("title", ""), b.get("title", "")):
        return True
    return False


def _groups(events: list[dict]) -> list[list[dict]]:
    """Union-find sur la relation _match : regroupe les fiches d'un même événement."""
    parent = list(range(len(events)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(events)):
        for j in range(i + 1, len(events)):
            if _match(events[i], events[j]):
                parent[find(i)] = find(j)

    buckets: dict[int, list[dict]] = {}
    for idx, ev in enumerate(events):
        buckets.setdefault(find(idx), []).append(ev)
    return [g for g in buckets.values() if len(g) > 1]


def _article_text(ev: dict) -> str:
    """Texte de l'ARTICLE RÉDIGÉ (titre + chapô + début du corps), pour vérifier sa
    langue RÉELLE — jamais le titre brut scrapé, qui peut être dans une langue et
    l'article rédigé (par notre pipeline, toujours en français par défaut) dans une
    autre. Vide si l'événement n'a pas encore été enrichi."""
    import json as _json
    title = (ev.get("article_title") or "").strip()
    body = ""
    if ev.get("enrich_data"):
        try:
            art = (_json.loads(ev["enrich_data"]) or {}).get("article") or {}
            body = f"{art.get('chapo', '')} {art.get('corps', '')}"[:500]
        except (ValueError, TypeError):
            pass
    return f"{title} {body}".strip()


def _link_map(group: list[dict]) -> dict[str, dict]:
    """Construit {langue: {"id":…, "wp":…, "permalink":…, "article_lang":…}} pour un
    groupe (une fiche par langue). En cas de collision (2 fiches même langue), on garde
    la 1re et on journalise. `article_lang` : langue RÉELLE de l'article déjà rédigé
    (detect_lang sur le texte écrit, pas le titre brut source) — "" si pas encore
    enrichi. Sert à ne jamais jumeler sur la foi du seul titre scrapé (cf. _check_pair_langs)."""
    out: dict[str, dict] = {}
    for ev in sorted(group, key=lambda e: e["id"]):
        lang = _lang(ev)
        pid = int(ev["wp_post_id_as"])
        if lang in out:
            log.warning("Collision de langue %s dans le groupe « %s » : on garde WP#%s, "
                        "on ignore id=%d (WP#%s)", lang,
                        (ev.get("title", "") or "")[:40], out[lang]["wp"], ev["id"], pid)
            continue
        atext = _article_text(ev)
        article_lang = (detect_lang(atext, "", ev.get("territoire", "")) if atext else "")
        out[lang] = {"id": ev["id"], "wp": pid, "permalink": ev.get("wp_permalink_as") or "",
                     "title": ev.get("title", ""), "article_lang": article_lang}
    return out


def _slug_of(permalink: str) -> str:
    path = urlparse((permalink or "").strip()).path.rstrip("/")
    return path.rsplit("/", 1)[-1] if path else ""


def _mark_pair_in_db(conn: sqlite3.Connection, pair: dict[str, dict]) -> None:
    """Écrit translation_of/translated_lang en base sur la fiche SECONDAIRE de la paire,
    pour que le back-office (badge 🇮🇹, fiche liée, liste groupée) la reconnaisse — le lien
    Polylang côté WordPress ne suffit pas, `app.py` lit `events_raw.translation_of`.
    Primaire = FR si présent (le site est français d'abord), sinon la 1re langue triée."""
    langs = sorted(pair, key=lambda l: (l != "fr", l))
    primary, secondaries = langs[0], langs[1:]
    primary_id = pair[primary]["id"]
    for lang in secondaries:
        sec_id = pair[lang]["id"]
        conn.execute("UPDATE events_raw SET translation_of=?, translated_lang=? WHERE id=?",
                    (primary_id, lang, sec_id))
    conn.commit()


def _align_slug(wp_url: str, auth, conn: sqlite3.Connection, pair: dict[str, dict]) -> None:
    """Aligne le slug de la fiche SECONDAIRE sur celui de la PRIMAIRE (même règle que
    _mark_pair_in_db : FR primaire si présent). Retour Franck : « les URL des paires
    doivent avoir du commun sinon c'est impossible de s'y retrouver ». Ne touche RIEN si
    le slug est déjà identique (idempotent, journalise seulement les vrais changements)."""
    langs = sorted(pair, key=lambda l: (l != "fr", l))
    primary, secondaries = langs[0], langs[1:]
    primary_slug = _slug_of(pair[primary]["permalink"])
    if not primary_slug:
        log.warning("Pas de permalien connu pour la primaire WP#%s — alignement de "
                    "slug ignoré pour ce groupe.", pair[primary]["wp"])
        return
    token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode("utf-8")).decode("ascii")
    endpoint = f"{wp_url}/?rest_route=/cs/v1/set-slug"
    for lang in secondaries:
        sec = pair[lang]
        if _slug_of(sec["permalink"]) == primary_slug:
            continue                                   # déjà aligné
        try:
            resp = requests.post(endpoint, json={"post_id": sec["wp"], "slug": primary_slug},
                                 auth=auth, headers={**_UA, "X-CS-Auth": token}, timeout=30)
            resp.raise_for_status()
            new_permalink = resp.json().get("permalink") or ""
            log.info("Slug aligné : WP#%s → « %s » (%s)", sec["wp"], primary_slug,
                     new_permalink or "?")
            if new_permalink:
                conn.execute("UPDATE events_raw SET wp_permalink_as=? WHERE id=?",
                            (new_permalink, sec["id"]))
                conn.commit()
        except requests.HTTPError as exc:
            log.error("Alignement de slug refusé pour WP#%s (%s) : %s", sec["wp"],
                      exc.response.status_code, exc.response.text[:200])
        except requests.RequestException as exc:
            log.error("Alignement de slug impossible pour WP#%s : %s", sec["wp"], exc)


def _flag_lang_mismatch(conn: sqlite3.Connection, event_id: int, expected: str, found: str) -> None:
    """Pousse un point « à vérifier » (même table que enrich.py) — jamais un blocage
    silencieux, un humain doit trancher (vraie erreur de contenu ? faux jumelage ?)."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, label TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', created_at TEXT DEFAULT (datetime('now')),
        resolved_at TEXT)""")
    conn.execute(
        "INSERT INTO checks (event_id, label) VALUES (?, ?)",
        (event_id, f"Jumelage FR/IT écarté : étiqueté « {expected} » mais l'article rédigé "
                   f"semble être en « {found} » — vérifier (mauvais jumelage ? mauvaise langue ?)."))
    conn.commit()


def _check_pair_langs(conn: sqlite3.Connection, pair: dict[str, dict]) -> bool:
    """True si la paire est sûre à jumeler : pour chaque langue dont l'article est DÉJÀ
    rédigé, la langue réelle du texte doit correspondre à la langue assignée. Sinon on
    N'ÉCRIT RIEN (ni Polylang, ni translation_of) et on pousse un point à vérifier —
    mieux vaut rater un jumelage que d'en créer un trompeur (constaté : un événement
    italien à la source, mais rédigé en français par notre pipeline, étiqueté « version
    IT » sur la seule foi de son titre scrapé — l'article affiché ne correspondait pas)."""
    ok = True
    for lang, v in pair.items():
        found = v.get("article_lang") or ""
        if found and found != lang:
            log.warning("[%s] Jumelage écarté : étiqueté « %s » mais l'article rédigé "
                       "semble être en « %s » (%s).", v["id"], lang, found,
                       (v.get("title") or "")[:50])
            _flag_lang_mismatch(conn, v["id"], lang, found)
            ok = False
    return ok


def _post_link(wp_url: str, auth, translations: dict[str, int]) -> bool:
    token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode("utf-8")).decode("ascii")
    endpoint = f"{wp_url}/?rest_route=/cs/v1/link-translations"
    try:
        resp = requests.post(endpoint, json={"translations": translations}, auth=auth,
                             headers={**_UA, "X-CS-Auth": token}, timeout=30)
        resp.raise_for_status()
        return True
    except requests.HTTPError as exc:
        log.error("Liage refusé (%s) : %s", exc.response.status_code, exc.response.text[:200])
    except requests.RequestException as exc:
        log.error("Liage impossible : %s", exc)
    return False


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Lie les traductions FR/IT (Polylang).")
    parser.add_argument("--apply", action="store_true",
                        help="EXÉCUTER le liage (défaut : simulation, on affiche seulement).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE wp_post_id_as IS NOT NULL "
        "AND duplicate_of IS NULL").fetchall()]
    log.info("%d événement(s) publié(s) sur l'Agenda à examiner", len(rows))

    groups = _groups(rows)
    pairs = [_link_map(g) for g in groups]
    pairs = [p for p in pairs if len(p) >= 2]           # au moins 2 langues
    # Contrôle de langue AVANT tout jumelage (même en simulation, pour voir le problème
    # tôt) : une paire dont l'article déjà rédigé ne correspond pas à la langue assignée
    # n'est jamais liée — mieux vaut la rater que jumeler sur la foi du seul titre source.
    safe_pairs = [p for p in pairs if _check_pair_langs(conn, p)]
    skipped = len(pairs) - len(safe_pairs)
    if skipped:
        log.info("%d paire(s) écartée(s) pour incohérence de langue (voir « à vérifier »).",
                 skipped)
    conn.commit()
    conn.close()
    pairs = safe_pairs
    if not pairs:
        log.info("Aucune paire de traductions détectée.")
        return 0

    for p in pairs:
        pretty = ", ".join(f"{lang}=WP#{v['wp']}" for lang, v in sorted(p.items()))
        log.info("%s traductions : %s", "LIER" if args.apply else "(simulation)", pretty)

    if not args.apply:
        log.info("=== %d paire(s) détectée(s). Relance avec --apply pour lier. ===", len(pairs))
        return 0

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    if not all([wp_url, auth[0], auth[1]]):
        log.error("Variables Agenda Sabauda manquantes (WP_AS_URL/USER/APP_PASSWORD).")
        return 1
    conn = sqlite3.connect(DB_PATH)
    ok = 0
    for p in pairs:
        wp_only = {lang: v["wp"] for lang, v in p.items()}
        if _post_link(wp_url, auth, wp_only):
            ok += 1
            # Écrit le lien en base AUSSI : sans ça, le back-office (badge 🇮🇹, fiche
            # groupée) ignore la paire — seul le lien WordPress/Polylang serait à jour.
            _mark_pair_in_db(conn, p)
            # URL commune à la paire (slug de la secondaire aligné sur la primaire).
            _align_slug(wp_url, auth, conn, p)
    conn.close()
    log.info("=== Liage terminé : %d/%d paire(s) liée(s) (WordPress + base). ===", ok, len(pairs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
