#!/usr/bin/env python3
"""Extraction du LIEU (nom + ville) d'un événement, pour remplir `lieu` / `ville`.

Le scraper ne remplit PAS ces colonnes : l'adresse ne vit souvent que dans la prose
de l'article. Or l'agenda a besoin d'un lieu structuré (Venue TEC : carte, ville,
schema.org location). On l'extrait comme les dates (voir dates.py), du plus sûr au
dernier recours :
  1. PAGE structurée — JSON-LD schema.org « location » (name + addressLocality),
     le standard des sites d'événements (déterministe, gratuit) ;
  2. LLM — jugement de langue (FR/IT) sur la prose de la page, quand le JSON-LD manque.
     Économique, borné, idempotent ; désactivable par VENUES_LLM=0.

Sortie stockée : lieu / ville + venue_source
('page' | 'llm' | 'novenue' | 'none' | 'llm_none') + venue_checked_at (DATE de la
dernière tentative). Cron : après la datation.

AUCUN ÉCHEC N'EST DÉFINITIF (depuis le 2026-08-03). Une fiche dont le lieu n'a pas été
trouvé est automatiquement re-tentée après VENUE_COOLDOWN_DAYS (défaut 7, aligné sur
WEB_COOLDOWN_DAYS de scraper_events). Avant, la sortie de l'impasse existait mais exigeait
qu'un humain tape `--retry` en ayant deviné qu'il fallait le faire : 823 fiches y ont
dormi jusqu'au 2026-08-02, où on les a trouvées en cherchant autre chose. Un garde-fou
qui dépend d'un geste manuel n'est pas un garde-fou, c'est une note.
"""
from __future__ import annotations
import argparse
import html as htmlmod
import json
import os
import re
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.scraper_events import init_db
from scripts.dates import fetch_page_text, _sans_script, signale_annulation_page
from dotenv import load_dotenv

log = get_logger("venues")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
FETCH_CAP = int(os.getenv("VENUES_FETCH_CAP", "200"))
VENUES_LLM = os.getenv("VENUES_LLM", "1") not in ("0", "false", "False", "")
VENUES_LLM_CAP = int(os.getenv("VENUES_LLM_CAP", "150"))
VENUES_LLM_MODEL = os.getenv("VENUES_LLM_MODEL") or os.getenv("ANTHROPIC_MODEL_EXTRACT",
                                                             "claude-haiku-4-5-20251001")


def _clean(s: str) -> str:
    """Déséchappe un fragment de chaîne JSON/HTML et normalise les espaces."""
    s = (s or "").strip()
    if not s:
        return ""
    try:                     # gère les é, \/ … d'un littéral JSON
        s = json.loads(f'"{s}"')
    except (ValueError, TypeError):
        pass
    s = htmlmod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()[:160]


def venue_from_page(html: str) -> tuple[str, str, str]:
    """(lieu, ville, source) depuis le JSON-LD schema.org « location ». ('','','') si rien.

    Gère « location » en OBJET (Place : name + address.addressLocality) et en CHAÎNE.

    ⚠️ ÉLARGI le 2026-08-11, comme dates.dates_from_page et pour la même raison : on
    cherchait la chaîne `"location"` dans le HTML, donc on ratait le `@graph` de Yoast,
    les tableaux, les guillemets échappés et les microdata. utils/jsonld.py parse le
    document ; la recherche de motif reste derrière, en filet.
    Ne devine JAMAIS depuis le texte libre (trop de faux positifs) — c'est le rôle du LLM.
    """
    from utils import jsonld as _jsonld
    _c = _jsonld.champs(html)
    if _c.get("lieu"):
        return (_c["lieu"], _c.get("ville", ""), "page")
    _m = _jsonld.champs_microdata(html)
    if _m.get("lieu"):
        return (_m["lieu"], _m.get("ville", ""), "page")
    idx = html.find('"location"')
    if idx != -1:
        window = html[idx:idx + 900]
        # location : { "name": "...", "address": { "addressLocality": "..." } }
        name = re.search(r'"name"\s*:\s*"([^"]{2,120})"', window)
        city = re.search(r'"addressLocality"\s*:\s*"([^"]{2,80})"', window)
        lieu = _clean(name.group(1)) if name else ""
        ville = _clean(city.group(1)) if city else ""
        if lieu or ville:
            return (lieu, ville, "page")
        # location : "Nom du lieu" (chaîne simple)
        strv = re.search(r'"location"\s*:\s*"([^"]{2,120})"', html[idx:idx + 200])
        if strv:
            return (_clean(strv.group(1)), "", "page")
    return ("", "", "")


def fetch_event_venue(url: str, _capture: dict | None = None) -> tuple[str, str, str]:
    """Télécharge la page et en extrait le lieu (JSON-LD). ('','','novenue') si rien.

    `_capture` (optionnel) : même mécanique que `scripts.dates.fetch_event_dates` —
    reçoit sous la clé "text" le texte de la page réellement téléchargée (script/
    style retirés), pour le canal 3 (`signale_annulation_page`) sans second
    téléchargement. Additif : les appelants qui l'ignorent ne changent pas de
    comportement."""
    if not url or url.startswith("gmail:") or "news.google.com" in url:
        return ("", "", "none")
    from scripts.dates import _robust_get
    r = _robust_get(url)
    if r is None:
        return ("", "", "novenue")
    if _capture is not None:
        _capture["text"] = _sans_script(r.text)
    lieu, ville, src = venue_from_page(r.text)
    return (lieu, ville, "page") if src == "page" else ("", "", "novenue")


def llm_venue(material: str, client, model: str) -> tuple[str, str, str]:
    """Le LLM lit la matière et rend (lieu, ville). ('','','llm_none') si rien.

    Dernier recours uniquement (le JSON-LD a échoué). Jugement de langue FR/IT.
    """
    material = (material or "").strip()
    if not material:
        return ("", "", "llm_none")
    prompt = (
        "Tu extrais le LIEU d'un événement culturel à partir du texte fourni "
        "(français ou italien). Donne le NOM du lieu précis (musée, théâtre, salle, "
        "château, place, église…) et la VILLE. Ignore les adresses d'organisateurs "
        "ou de billetterie : ce qui compte, c'est OÙ se déroule l'événement. Si le "
        "lieu n'est pas clairement identifiable, found=false.\n\n"
        f"TEXTE :\n{material[:4000]}\n\n"
        'Réponds en JSON STRICT et rien d\'autre : '
        '{"lieu": "…" ou "", "ville": "…" ou "", "found": true|false}'
    )
    try:
        msg = client.messages.create(
            model=model, max_tokens=150,
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:
        # PLAFOND API ≠ échec de fiche — même garde que scripts/dates.py, même jour, même
        # motif : 152 occurrences le 08/07, chaque fiche tentée parquée VENUE_COOLDOWN_DAYS
        # parce que la facturation avait dit stop. On remonte, la boucle décide.
        from utils.api_limite import PlafondAPI, est_plafond
        if est_plafond(exc):
            raise PlafondAPI(str(exc)) from exc
        log.warning("Extraction lieu LLM échouée : %s", exc)
        return ("", "", "llm_none")
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text").strip()
    # MESURÉ (2026-08-11) : ce poste n'était pas compté du tout. Franck, 2026-08-10 :
    # « je consomme beaucoup trop de token API pour le résultat médiocre » — on ne peut
    # ni le lui confirmer ni le lui infirmer tant que la moitié des appels sont
    # invisibles. Voir scripts/audit_couts.py pour la répartition par poste.
    from utils import usage
    usage.record_message(model, msg, label="lieu")
    blob = raw[raw.find("{"):raw.rfind("}") + 1] if "{" in raw else ""
    try:
        data = json.loads(blob or raw)
    except (ValueError, TypeError):
        return ("", "", "llm_none")
    if not data.get("found"):
        return ("", "", "llm_none")
    lieu, ville = _clean(data.get("lieu", "")), _clean(data.get("ville", ""))
    return (lieu, ville, "llm") if (lieu or ville) else ("", "", "llm_none")


def apply_source_venues(conn: sqlite3.Connection) -> int:
    """Passe 0 — LIEU DE LA SOURCE (déterministe, gratuit, le plus fiable).

    Pour une source « officielle » (un lieu précis : théâtre, musée, festival…),
    le lieu EST la source : un événement de flowersfestival.it se passe au Flowers
    Festival, à Collegno. On applique le lieu/ville par défaut de la source (champs
    optionnels de config/sources.txt) AVANT d'aller chercher par page/LLM/web.
    On ne pose venue_source='source' que si on a rempli un LIEU (sinon on laisse les
    passes suivantes trouver le lieu)."""
    from scripts.scraper_events import load_sources
    defaults = {s["name"]: (s.get("lieu", ""), s.get("ville", ""))
                for s in load_sources() if (s.get("lieu") or s.get("ville"))}
    filled = 0
    for name, (lieu, ville) in defaults.items():
        rows = conn.execute(
            "SELECT id, lieu, ville FROM events_raw WHERE source_name = ? "
            "AND statut != 'merged' AND (COALESCE(lieu,'')='' OR COALESCE(ville,'')='')",
            (name,)).fetchall()
        for r in rows:
            updates: dict = {}
            if lieu and not (r["lieu"] or "").strip():
                updates["lieu"] = lieu
                updates["venue_source"] = "source"
            if ville and not (r["ville"] or "").strip():
                updates["ville"] = ville
            if not updates:
                continue
            sets = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE events_raw SET {sets} WHERE id=?",
                         [*updates.values(), r["id"]])
            filled += 1
        conn.commit()
    return filled


# Délai avant de re-tenter une fiche dont le lieu n'a PAS été trouvé. Même convention et
# même variable d'environnement que scripts/scraper_events.py (WEB_COOLDOWN_DAYS, défaut 7)
# — deux délais différents pour la même idée seraient un piège de réglage.
VENUE_COOLDOWN_DAYS = int(os.getenv("VENUE_COOLDOWN_DAYS",
                                    os.getenv("WEB_COOLDOWN_DAYS", "7")))


def ensure_columns(conn: sqlite3.Connection) -> None:
    # `venue_checked_at` (ajoutée le 2026-08-03) : DATE de la dernière tentative, pas son
    # résultat — `venue_source` dit ce qu'on a trouvé, cette colonne dit quand on a cherché.
    # Sans elle, un ré-armement automatique ne peut pas exister : il re-tenterait les 800+
    # fiches sans lieu à CHAQUE run, donc paierait tous les jours pour les mêmes échecs.
    for col, decl in (("lieu", "TEXT"), ("ville", "TEXT"), ("venue_source", "TEXT"),
                      ("venue_checked_at", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extraction du lieu des événements (page + LLM).")
    parser.add_argument("--fetch-cap", type=int, default=FETCH_CAP,
                        help="Nombre max de pages à télécharger sur ce run.")
    parser.add_argument("--no-llm", action="store_true",
                        help="Ne pas utiliser l'extraction LLM de dernier recours.")
    parser.add_argument("--llm-cap", type=int, default=VENUES_LLM_CAP,
                        help="Nombre max d'événements traités par LLM sur ce run.")
    parser.add_argument("--retry", action="store_true",
                        help=f"Ré-armer TOUT DE SUITE les événements marqués « lieu "
                             f"introuvable », sans attendre le délai. Depuis le "
                             f"2026-08-03 ce ré-armement est AUTOMATIQUE à chaque run "
                             f"après {VENUE_COOLDOWN_DAYS} jours (VENUE_COOLDOWN_DAYS) : "
                             f"cette option ne sert plus qu'à forcer la reprise "
                             f"immédiatement. Ne touche JAMAIS un événement qui a un lieu.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    ensure_columns(conn)
    # Canal 3 (docs/EVENEMENTS_ANNULES.md) : mêmes colonnes, même migration que le
    # canal 2 — pas de schéma parallèle. `scripts.dedupe` ne dépend pas de venues.py,
    # aucun cycle d'import.
    from scripts.dedupe import ensure_annulation_columns
    from utils.annulation import load_annulation_filter
    ensure_annulation_columns(conn)
    annulation_re = load_annulation_filter()

    # --- Ré-armement (--retry) : sortir les fiches du cul-de-sac 'llm_none' ---
    # ⚠️ IMPASSE STRUCTURELLE, mesurée le 2026-08-02. Les deux passes ci-dessous
    # sélectionnent sur `venue_source` : la passe page sur NULL/'', la passe LLM sur
    # ('novenue','none'). `llm_none` — posé quand le LLM a cherché et n'a rien trouvé —
    # n'est dans AUCUNE des deux. Une fiche qui a échoué une seule fois est donc exclue
    # DÉFINITIVEMENT, alors que le lieu peut très bien devenir trouvable ensuite (page
    # source mise à jour, programme publié plus tard, meilleur modèle).
    # Effet observé : le premier run après branchement au cron a posé 22 lieux… et les
    # 20 fiches qui bloquaient TOUTE la file de publication sont restées bloquées,
    # parce qu'elles étaient déjà en 'llm_none'. Le pipeline tournait à vide.
    # `dates.py` porte exactement le même garde-fou (--retry sur 'nodate'/'llm_none')
    # depuis toujours ; cette asymétrie entre deux scripts jumeaux était le défaut.
    #
    # ⚠️ CE RÉ-ARMEMENT EST DEVENU AUTOMATIQUE LE 2026-08-03. Il ne l'était pas, et c'est
    # le même défaut que celui qu'il corrige, d'un cran plus haut : la sortie de l'impasse
    # existait, mais elle exigeait qu'un humain tape `--retry` en ayant deviné qu'il fallait
    # le faire. Personne ne tape une commande dont il ignore l'existence — les 823 fiches
    # bloquées du 2026-08-02 n'ont été libérées que parce qu'on cherchait autre chose.
    # Un garde-fou qui dépend d'un geste manuel n'est pas un garde-fou, c'est une note.
    #
    # POURQUOI UN DÉLAI et pas un ré-armement à chaque run : re-tenter tous les jours les
    # 800+ fiches sans lieu paierait tous les jours pour les mêmes échecs (la passe LLM est
    # facturée). Une page qui n'avait pas de lieu hier n'en a pas davantage aujourd'hui ;
    # elle peut en avoir dans une semaine (programme publié, page mise à jour). D'où
    # VENUE_COOLDOWN_DAYS, aligné sur la convention déjà en place dans scraper_events.
    #
    # POURQUOI 'none' ET PAS '' : les fiches ré-armées repartent vers la passe LLM, pas vers
    # la passe page — celle-ci a son propre plafond de téléchargements (--fetch-cap) qu'on
    # réserve aux fiches JAMAIS examinées. Une reprise ne doit pas prendre la place d'une
    # nouveauté. `--retry` conserve exactement ce comportement, il ignore seulement le délai.
    if args.retry:
        n = conn.execute(
            "UPDATE events_raw SET venue_source='none' "
            "WHERE venue_source IN ('llm_none','novenue') "
            "  AND COALESCE(lieu,'') = '' AND statut != 'merged'").rowcount
        conn.commit()
        log.info("Retry : %d événement(s) sans lieu ré-armé(s) pour une nouvelle tentative "
                 "(délai ignoré, --retry)", n)
    else:
        n = conn.execute(
            "UPDATE events_raw SET venue_source='none' "
            "WHERE venue_source IN ('llm_none','novenue') "
            "  AND COALESCE(lieu,'') = '' AND statut != 'merged' "
            # NULL = tentative antérieure à cette colonne : on la traite comme ancienne,
            # sinon les fiches déjà bloquées AVANT ce correctif ne sortiraient jamais —
            # c'est-à-dire précisément celles pour lesquelles il est écrit.
            "  AND (venue_checked_at IS NULL OR venue_checked_at < datetime('now', ?))",
            (f"-{VENUE_COOLDOWN_DAYS} days",)).rowcount
        conn.commit()
        if n:
            log.info("Ré-armement automatique : %d fiche(s) sans lieu re-tentée(s) "
                     "(dernier essai il y a plus de %d jours)", n, VENUE_COOLDOWN_DAYS)

    # --- Passe 0 : LIEU DE LA SOURCE (le lieu = la source pour les « officielle ») ---
    from_source = apply_source_venues(conn)
    log.info("Passe source : %d lieu/ville posé(s) depuis la source", from_source)

    # --- Passe 1 : page structurée (JSON-LD location), déterministe ---
    todo = conn.execute(
        "SELECT id, title, url_source, wp_post_id_as, annulation_detectee_at "
        "FROM events_raw "
        "WHERE COALESCE(lieu,'') = '' AND (venue_source IS NULL OR venue_source = '') "
        "  AND statut != 'merged' "
        "  AND url_source NOT LIKE 'gmail:%' AND url_source NOT LIKE '%news.google.com%' "
        "LIMIT ?", (args.fetch_cap,)).fetchall()
    log.info("Passe page : %d page(s) à lire (cap %d)", len(todo), args.fetch_cap)
    from_page = 0
    for r in todo:
        capture: dict = {}
        lieu, ville, src = fetch_event_venue(r["url_source"], _capture=capture)
        # Canal 3 : la page vient d'être RÉELLEMENT téléchargée (capture non vide) —
        # on cherche un marqueur d'annulation dessus, quel que soit le lieu trouvé :
        # le signal est un ajout, jamais un blocage du reste du traitement.
        if capture.get("text"):
            signale_annulation_page(conn, dict(r), capture["text"], annulation_re,
                                    source="page (venues.py, passe JSON-LD)")
        conn.execute(
            "UPDATE events_raw SET lieu=?, ville=?, venue_source=?, "
            "venue_checked_at=datetime('now') WHERE id=?",
            (lieu, ville, src, r["id"]))
        conn.commit()
        if src == "page":
            from_page += 1
    log.info("Passe page : %d lieu(x) via la page", from_page)

    # --- Passe 2 : LLM (dernier recours) sur les restants ---
    from_llm = 0
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if VENUES_LLM and not args.no_llm and api_key:
        todo = conn.execute(
            "SELECT id, title, description, url_source, wp_post_id_as, "
            "  annulation_detectee_at FROM events_raw "
            "WHERE COALESCE(lieu,'') = '' AND venue_source IN ('novenue', 'none') "
            "  AND statut != 'merged' "
            "  AND url_source NOT LIKE 'gmail:%' AND url_source NOT LIKE '%news.google.com%' "
            "LIMIT ?", (args.llm_cap,)).fetchall()
        log.info("Passe LLM : %d événement(s) à situer (modèle %s, cap %d)",
                 len(todo), VENUES_LLM_MODEL, args.llm_cap)
        if todo:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
            from utils.api_limite import PlafondAPI
            for r in todo:
                page_text = fetch_page_text(r["url_source"], title=r["title"] or "")
                material = page_text or f"{r['title']}\n{r['description'] or ''}"
                # Canal 3 : uniquement sur du texte VENANT DE LA PAGE, jamais sur le
                # repli titre+description qui ne relit rien.
                if page_text:
                    signale_annulation_page(conn, dict(r), page_text, annulation_re,
                                            source="page (venues.py, passe LLM)")
                try:
                    lieu, ville, src = llm_venue(material, client, VENUES_LLM_MODEL)
                except PlafondAPI as exc:
                    log.error("PLAFOND API atteint — passe LLM interrompue, %d fiche(s) "
                              "non tentée(s), aucun verdict écrit pour elles : %s",
                              len(todo) - todo.index(r), exc)
                    break
                conn.execute(
                    "UPDATE events_raw SET lieu=?, ville=?, venue_source=?, "
                    "venue_checked_at=datetime('now') WHERE id=?",
                    (lieu, ville, src, r["id"]))
                conn.commit()
                if src == "llm":
                    from_llm += 1
            log.info("Passe LLM : %d lieu(x) via le LLM", from_llm)
    elif VENUES_LLM and not args.no_llm and not api_key:
        log.info("Passe LLM ignorée : ANTHROPIC_API_KEY absente.")

    located = conn.execute(
        "SELECT COUNT(*) n FROM events_raw WHERE COALESCE(lieu,'') <> '' "
        "AND statut != 'merged'").fetchone()["n"]
    conn.close()
    log.info("=== Lieux : +%d page +%d LLM ce run · %d situés au total ===",
             from_page, from_llm, located)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
