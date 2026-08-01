#!/usr/bin/env python3
"""Déduplication multi-sources des événements.

Un même événement arrive souvent par plusieurs flux (officiel + radar + office de
tourisme). On regroupe les doublons, on garde une fiche CANONIQUE (la source la
plus autoritaire/riche) et on FUSIONNE sans rien perdre :

- socle canonique = meilleur score (tier curé puis richesse) → lien officiel,
  attribution, statut ;
- MATIÈRE préservée : on complète les champs manquants du gagnant depuis les autres,
  on garde le texte le PLUS LONG du groupe (même venu d'un radar gratuit), et on NE
  SUPPRIME PAS les doublons (statut='merged', duplicate_of=gagnant) → la rédaction
  pourra puiser dans toute la matière du groupe.

LLM ? NON — 100 % déterministe (heuristique same_story + score). Voir docs/LLM_OU_CODE.md.
Cron : 0 8 * * * (après scraping/gmail, avant l'évaluation de 9h) — évite aussi de
payer l'évaluation LLM sur des doublons.
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.sources import same_story, is_logo_image
from scripts.scraper_events import init_db
from dotenv import load_dotenv

log = get_logger("dedupe")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Priorité de source (tier curé dans config/sources.txt).
TIER_RANK = {"officielle": 3, "institution": 2, "institutionnel": 2, "tourisme": 1, "radar": 0}
_FIELDS = ("date_start", "lieu", "ville", "organisateur")

# --- Déduplication INTER-LANGUE (FR/IT) -----------------------------------
# same_story compare les titres → rate « Festa del Jambon de Bosses » vs « Fête du
# Jambon de Bosses » (langues différentes). On rapproche ces paires par les TOKENS
# SIGNIFICATIFS (noms propres, années), invariants d'une langue à l'autre — on
# retire les mots-outils ET les mots génériques d'événement FR/IT (festa/fête,
# sagra, concerto/concert…) qui, eux, diffèrent selon la langue.
_STOP = {
    # articles / prépositions / conjonctions FR + IT
    "le", "la", "les", "un", "une", "des", "du", "de", "au", "aux", "et", "en",
    "dans", "sur", "pour", "par", "avec", "ce", "cette", "il", "lo", "gli", "dei",
    "degli", "delle", "del", "della", "dello", "di", "da", "al", "alla", "allo",
    "con", "per", "the", "of", "and",
    # ADVERBES / PRONOMS / VERBES COURANTS — ajoutés le 2026-08-02 après une fusion à
    # tort bien réelle : « Une semaine pas plus » (théâtre, Chambéry) apparié à « Fête du
    # lac 2026 : les spectateurs qui n'habitent PAS Annecy paieront PLUS cher » (article
    # Google News). Tokens communs = {pas, plus}, soit 2 mots strictement grammaticaux —
    # assez pour passer le seuil de 2, et comme le recouvrement se mesure sur le PLUS
    # COURT des deux titres (3 tokens ici), le ratio atteignait 0,67 > 0,5. Un titre bref
    # composé de mots-outils s'appariait ainsi avec presque n'importe quoi. Conséquence en
    # cascade : la description Google News passait dans l'événement gagnant, puis nourrissait
    # la rédaction (enrich.py agrège la matière des doublons) et la traduction — d'où une
    # fiche IT publiée sous le titre « Festa del Lago 2026 » sur un spectacle de théâtre.
    "pas", "plus", "qui", "que", "quoi", "dont", "tout", "tous", "toute", "toutes",
    "sans", "sous", "entre", "chez", "mais", "donc", "non", "ans", "son", "ses",
    "est", "sont", "ete", "leur", "leurs", "cher", "chere", "moins", "tres", "bien",
    "piu", "che", "chi", "cui", "tutto", "tutti", "tutta", "tutte", "senza", "sotto",
    "tra", "fra", "sono", "suo", "sua", "suoi", "anni", "anno", "meno", "molto",
    # mots génériques d'événement (diffèrent selon la langue → non distinctifs)
    "fete", "festa", "feste", "sagra", "sagre", "fiera", "foire", "marche",
    "mercato", "concert", "concerto", "spectacle", "spettacolo", "expo",
    "esposizione", "mostra", "festival", "edizione", "edition", "rassegna",
    "salon", "salone", "notte", "nuit", "giornata", "journee",
}


def _sig_tokens(title: str) -> set[str]:
    """Tokens SIGNIFICATIFS d'un titre (sans accents, sans mots-outils/génériques).
    Garde les mots de 3+ lettres et les nombres (années)."""
    s = unicodedata.normalize("NFD", (title or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    toks = re.findall(r"[a-z0-9]+", s)
    return {t for t in toks if len(t) >= 3 and t not in _STOP}


def _text_len(html: str | None) -> int:
    """Longueur du TEXTE VISIBLE d'une description (balises et URLs retirées).

    Sert à comparer la SUBSTANCE de deux descriptions, jamais leur volume brut : un item
    Google News RSS se réduit à un `<a href="https://news.google.com/rss/articles/CBMi…">`
    dont l'URL encodée pèse des centaines de caractères pour zéro mot de contenu. Comparé
    en longueur brute, il écrase n'importe quelle vraie description (cf. merge_group).
    """
    import html as _html
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", html or "")
    s = re.sub(r"<[^>]+>", " ", s)                  # balises
    s = _html.unescape(s)
    s = re.sub(r"https?://\S+", " ", s)             # URLs nues restantes
    return len(re.sub(r"\s+", " ", s).strip())


def _title_years(title: str) -> set[str]:
    """Années (nombres à 4 chiffres) présentes dans un titre, via les tokens
    significatifs — exactement l'extraction utilisée par cross_lang_same."""
    return {t for t in _sig_tokens(title) if t.isdigit() and len(t) == 4}


def _years_incompatible(a: str, b: str) -> bool:
    """True si les DEUX titres portent une année et qu'elles sont DISJOINTES
    (deux éditions d'années différentes → NE PAS fusionner). Règle identique à
    cross_lang_same. Conservateur : si au moins un titre n'a pas d'année, on ne
    bloque pas (renvoie False) — en cas de doute on ne prive pas d'une fusion
    légitime, on ajoute seulement une garde contre les fusions à tort."""
    ya, yb = _title_years(a), _title_years(b)
    return bool(ya and yb and ya.isdisjoint(yb))


def cross_lang_same(a: str, b: str) -> bool:
    """True si deux titres décrivent le MÊME événement malgré des langues différentes.

    Signal robuste : forte intersection de tokens significatifs (noms propres/années).
    Conservateur pour éviter les fusions à tort : ≥ 2 tokens communs, Jaccard ≥ 0,5,
    et années compatibles (deux éditions d'années différentes ne fusionnent pas)."""
    ta, tb = _sig_tokens(a), _sig_tokens(b)
    if len(ta) < 2 or len(tb) < 2:
        return False
    shared = ta & tb
    if _years_incompatible(a, b):
        return False                      # éditions d'années différentes
    # Il faut ≥ 2 tokens communs qui NE SOIENT PAS des années : deux vrais mots
    # distinctifs partagés (noms propres). L'année seule (+ un genre comme « jazz »)
    # ne suffit pas → évite de fusionner deux événements différents de la même année.
    shared_words = {t for t in shared if not (t.isdigit() and len(t) == 4)}
    if len(shared_words) < 2:
        return False
    # Recouvrement suffisant par rapport au plus court des deux titres.
    if len(shared) / min(len(ta), len(tb)) < 0.5:
        return False
    return True


def richness(ev: dict) -> int:
    """Score objectif de richesse d'un exemplaire (mesurable, sans LLM)."""
    s = 0
    if (ev.get("url_image") or "").strip():
        s += 25
    s += min(len(ev.get("description") or ""), 2000) // 50
    for f in _FIELDS:
        if (ev.get(f) or "").strip():
            s += 5
    url = ev.get("url_source") or ""
    if url and "news.google.com" not in url:
        s += 15
    return s


def score(ev: dict) -> tuple[int, int]:
    """(priorité de tier, richesse). Le tier prime ; la richesse départage."""
    return (TIER_RANK.get((ev.get("source_type") or "").lower(), 1), richness(ev))


def _groups(events: list[dict], cross_lang: bool = False) -> list[list[dict]]:
    """Regroupe par territoire + same_story (union-find simple).

    cross_lang=False (défaut) : on ne dédoublonne QU'EN MÊME LANGUE. Sur un site
    bilingue, les versions FR et IT d'un même événement ne sont PAS des doublons —
    ce sont deux traductions à lier via Polylang (+ hreflang), pas à fusionner. On
    n'active la fusion inter-langue (cross_lang_same) que si explicitement demandé."""
    parent = list(range(len(events)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    # ne comparer qu'à l'intérieur d'un même territoire (perf + sens)
    by_terr: dict[str, list[int]] = {}
    for idx, ev in enumerate(events):
        by_terr.setdefault(ev.get("territoire") or "", []).append(idx)
    for idxs in by_terr.values():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                ti, tj = events[i].get("title", ""), events[j].get("title", "")
                # même histoire (titres proches) — et, SI demandé, même événement
                # inter-langue FR/IT (désactivé par défaut : bilingue = à lier, pas
                # à fusionner).
                # Garde années : same_story compare les titres SANS regarder les
                # dates → deux éditions successives (« Festival X 2025 » vs « … 2026 »)
                # se ressemblent. On applique la MÊME règle que cross_lang_same :
                # années présentes des deux côtés et disjointes ⇒ pas de fusion.
                # (cross_lang_same porte déjà cette garde en interne.)
                if (same_story(ti, tj) and not _years_incompatible(ti, tj)) \
                        or (cross_lang and cross_lang_same(ti, tj)):
                    union(i, j)

    buckets: dict[int, list[dict]] = {}
    for idx, ev in enumerate(events):
        buckets.setdefault(find(idx), []).append(ev)
    return list(buckets.values())


def merge_group(conn: sqlite3.Connection, group: list[dict]) -> int:
    """Fusionne un groupe de doublons. Retourne le nb d'événements marqués 'merged'."""
    winner = max(group, key=score)
    losers = [e for e in group if e["id"] != winner["id"]]

    updates: dict[str, str] = {}
    # 1) compléter les champs STRUCTURÉS manquants du gagnant
    if not (winner.get("url_image") or "").strip():
        for e in sorted(losers, key=score, reverse=True):
            img = (e.get("url_image") or "").strip()
            if img and not is_logo_image(img):
                updates["url_image"] = img
                break
    for f in _FIELDS:
        if not (winner.get(f) or "").strip():
            for e in sorted(losers, key=score, reverse=True):
                if (e.get(f) or "").strip():
                    updates[f] = e[f]
                    break
    # 2) MATIÈRE : garder le texte le plus SUBSTANTIEL du groupe (même venu d'un radar
    # gratuit). On mesure le TEXTE VISIBLE, pas la longueur brute — bug corrigé le
    # 2026-08-02 : une description Google News RSS n'est qu'un `<a href="…">` dont l'URL
    # encodée fait plusieurs centaines de caractères sans un mot de contenu. Elle gagnait
    # donc systématiquement au « plus long » et écrasait la vraie description du gagnant,
    # y compris lors de fusions PARFAITEMENT CORRECTES (« Charlie Winston ■ 7 juillet »
    # fusionné dans « Charlie Winston » : bon appariement, description détruite). Cette
    # matière polluée alimentait ensuite la rédaction (enrich.py agrège les doublons) et
    # la traduction — d'où des articles écrits sur le mauvais sujet.
    richest = max(group, key=lambda e: _text_len(e.get("description")))
    if _text_len(richest.get("description")) > _text_len(winner.get("description")):
        updates["description"] = richest["description"]

    if updates:
        cols = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE events_raw SET {cols} WHERE id=?",
                     (*updates.values(), winner["id"]))
    merged_n = 0
    for e in losers:
        # Un doublon DÉJÀ poussé sur l'agenda : on ne le fusionne pas ici (ça
        # laisserait un brouillon WordPress orphelin) — le ménage WP s'en charge.
        if e.get("wp_post_id_as"):
            log.warning("id=%d déjà sur l'agenda (WP#%s) — non fusionné "
                        "(nettoie côté WP avec scripts.cleanup_as_dupes)",
                        e["id"], e["wp_post_id_as"])
            continue
        conn.execute(
            "UPDATE events_raw SET statut='merged', duplicate_of=? WHERE id=?",
            (winner["id"], e["id"]))
        merged_n += 1
    log.info("Groupe « %s » : %d sources → garde id=%d (%s), %d fusionnée(s)",
             winner.get("title", "")[:50], len(group), winner["id"],
             winner.get("source_type"), merged_n)
    return merged_n


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Déduplication multi-sources (dont inter-langue FR/IT).")
    parser.add_argument("--rescan", action="store_true",
                        help="Inclure aussi les événements RETENUS (nettoie le stock "
                             "existant en MÊME LANGUE).")
    parser.add_argument("--cross-lang", action="store_true",
                        help="FUSIONNER aussi les paires FR/IT (⚠️ à éviter sur un site "
                             "bilingue : les traductions sont à LIER via Polylang, pas à "
                             "fusionner). Désactivé par défaut.")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    where = ("statut='pending' OR (statut IN ('evaluated','published_cs','published_sub') "
             "AND duplicate_of IS NULL)") if args.rescan else "statut='pending'"
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM events_raw WHERE {where}").fetchall()]
    log.info("%d événement(s) à dédupliquer%s", len(rows),
             " (rescan du stock retenu)" if args.rescan else "")

    merged = 0
    groups = _groups(rows, cross_lang=args.cross_lang)
    dups = [g for g in groups if len(g) > 1]
    for g in dups:
        merged += merge_group(conn, g)
    conn.commit()
    conn.close()
    log.info("=== Dédup terminée : %d groupe(s) de doublons, %d événement(s) fusionné(s) ===",
             len(dups), merged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
