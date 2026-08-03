#!/usr/bin/env python3
"""Traduit les événements à BON SCORE dans l'autre langue et publie la fiche traduite
comme TRADUCTION Polylang liée — pour que le site soit bilingue (un événement savoyard
visible côté italien, un événement piémontais côté français) et que les newsletters des
deux côtés aient de la matière.

Sens : FR → IT et IT → FR, selon la langue détectée de l'événement source.

Périmètre volontairement RESSERRÉ (coût API + qualité) :
  • événement déjà EN LIGNE sur l'Agenda (wp_post_id_as renseigné),
  • non-doublon, pas déjà une traduction, pas déjà traduit,
  • score utile (--min-score, défaut 6),
  • pas de jumelle déjà existante dans la langue cible (même affiche = même événement
    bilingue déjà présent → on laisse scripts.link_translations_as le lier).

On traduit TITRE + DESCRIPTION (le contenu de la fiche traduite est bâti sur la
description traduite ; l'article enrichi FR n'est pas recopié). La langue est FORCÉE
(force_lang) à la publication. Puis on LIE les deux fiches via cs/v1/link-translations.

SÛR : dry-run par défaut (--apply pour agir), --cap pour de petits lots.

Usage (VPS) :
    .venv/bin/python -m scripts.translate_events                    # simulation
    .venv/bin/python -m scripts.translate_events --min-score 6 --cap 10 --apply
    # remplir un versant maigre (ex. Piémont côté FR : ses événements IT → FR) :
    .venv/bin/python -m scripts.translate_events --territoire piemont --cap 20 --apply
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.lang import detect_lang, effective_lang
from scripts.scraper_events import init_db
from scripts.publisher_as import publish_to_as
from scripts.link_translations_as import _post_link
# Portillon de justesse du titre traduit (C2 de docs/GO_NOGO_TRADUCTION.md). Défini dans
# batch_report parce que c'est là que vit la doctrine des contrôles de justesse et la
# seule définition du dépôt de « racine commune » — deux copies divergeraient.
from scripts.batch_report import verdict_titre_traduit
from utils.voix import voix_block

log = get_logger("translate-events")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
# La traduction de l'ARTICLE (long markdown « escalier » + voix) demande un modèle
# fiable : Haiku traduisait les champs courts (titre, chapô) mais recopiait le long
# « corps » en français (constaté en test). Défaut Sonnet ; surchargeable par env pour
# revenir à un modèle économique si besoin.
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL_TRANSLATE", "claude-sonnet-5")

_LANG_NAME = {"fr": "français", "it": "italien"}


def _slug_of(permalink: str) -> str:
    """Dernier segment du permalien = le slug WordPress. "" si permalien absent/vide."""
    path = urlparse((permalink or "").strip()).path.rstrip("/")
    return path.rsplit("/", 1)[-1] if path else ""

# Filtre territoire optionnel (--territoire) : slug → mots-clés cherchés dans le champ
# territoire normalisé. Sert à REMPLIR un versant maigre (ex. Piémont côté FR).
_TERR_KEYS = {
    "savoie-haute-savoie": ("savoie", "haute savoie"),
    "piemont": ("piemont", "piemonte", "piedmont"),
    "vallee-d-aoste": ("aoste", "aosta"),
    "nice-alpes-maritimes": ("nice", "alpes maritimes", "azur"),
}


def _norm(s: str) -> str:
    import unicodedata
    s = (s or "").lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    import re as _re
    return _re.sub(r"[^a-z0-9]+", " ", s).strip()


def _ensure_cols(conn):
    for col, decl in (("translation_of", "INTEGER"), ("translated_at", "TEXT"),
                      ("translated_lang", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass


def _target(src_lang: str) -> str:
    return "it" if src_lang == "fr" else "fr"


def _charte_prompt(target: str, voix: str = "") -> str:
    """Bloc de consignes éditoriales (voix + charte de traduction) COMMUN à toutes les
    traductions FR↔IT — titre/description ET article enrichi. Régit ton, casse,
    superlatifs, dark patterns, toponymes et préservation des faits. Factorisé pour que
    `translate_title_desc` et `translate_article` appliquent EXACTEMENT les mêmes règles.

    voix : bloc de voix éditoriale (utils.voix.voix_block()) préfixé au prompt — il
    RÉGIT le ton, le vocabulaire interdit, la doctrine d'appartenance et les patterns,
    en italien comme en français. La traduction RE-VÉRIFIE contre ces règles."""
    tgt = _LANG_NAME[target]
    # Toponymes selon la langue cible (charte §6 bis : on nomme dans la langue du lecteur,
    # en gardant la chaîne ville → province → territoire).
    if target == "it":
        topo = ('Torino (pas "Turin"), Aosta, Nizza, Vercelli ; territoires : Savoia, '
                'Piemonte, Valle d\'Aosta, Contea di Nizza')
        superl = ('« imperdibile », « da non perdere », « evento clou », « magico », '
                  '« unico/straordinario » (quand c\'est vide), « il migliore »')
        darkp = ('fausse urgence (« ultimi posti! », « solo oggi », « affrettati »), '
                 'clickbait (« non crederai… »), confirmshaming')
        casse_lang = ('En italien, MOIS et JOURS en MINUSCULE (« 5 luglio », « domenica »). '
                      'Jamais de title case anglais (Chaque Mot En Majuscule).')
        boussole = 'Boussole de registre : le magazine *Internazionale*. Pas de calque du français.'
    else:
        topo = ('Turin (pas "Torino"), Aoste, Nice, Verceil ; territoires : Savoie, '
                'Piémont, Vallée d\'Aoste, Comté de Nice')
        superl = '« incontournable », « magique », « à ne pas manquer », « événement phare »'
        darkp = ('fausse urgence (« plus que 2 places ! », « dernier jour »), clickbait '
                 '(« vous n\'allez pas croire… »), confirmshaming')
        casse_lang = 'En français, mois et jours en minuscule. Jamais de title case anglais.'
        boussole = 'Registre soutenu mais accessible, comme le média *Internazionale*. Pas de calque de l\'italien.'
    return (
        voix +
        (f"\n\nSi une VOIX ÉDITORIALE est fournie ci-dessus, elle RÉGIT le ton, le style, "
         f"le vocabulaire interdit, la doctrine d'appartenance (gentilés, jamais la "
         f"nationalité ; pas de mots-frontière ni d'irrédentisme) et les patterns — EN {tgt.upper()} "
         f"comme en français. Tu RÉ-APPLIQUES ces règles en {tgt}, tu ne recopies pas un défaut. "
         f"En cas de désaccord, la voix prime sur ce qui suit.\n\n" if voix else "") +
        f"Tu produis la version {tgt} d'un événement culturel de l'espace alpin occidental "
        f"(Savoie · Piémont · Vallée d'Aoste · Nice), pour un média bilingue exigeant "
        f"(esprit *Internazionale* / *Le Monde Diplomatique*).\n\n"
        f"RÈGLE MÈRE — TRADUIRE N'EST PAS RECOPIER : la version {tgt} obéit à la MÊME charte "
        f"éditoriale que la source. Tu RÉ-APPLIQUES la charte, tu ne translittères pas un "
        f"défaut. Si le titre ou le texte source viole une règle (racoleur, TOUT EN "
        f"CAPITALES, superlatif creux, dark pattern), tu le CORRIGES dans la version {tgt} — "
        f"tu ne recopies jamais le défaut. Une mauvaise source ne doit pas produire une "
        f"mauvaise traduction.\n\n"
        f"CASSE : jamais de titre/nom TOUT EN CAPITALES, même si la source l'écrit ainsi "
        f'("COREOGRAFIE DEL POSSIBILE" → "Coreografie del Possibile"). Casse de phrase '
        f"(initiale + noms propres, selon la langue). {casse_lang} "
        f"Préserve les vrais sigles/acronymes (FIAF, MAO, ONU) et la casse voulue d'une "
        f"marque (iMac, PSG).\n\n"
        f"SUPERLATIFS CREUX INTERDITS en {tgt} : {superl}. Reste factuel et incarné.\n\n"
        f"DARK PATTERNS INTERDITS en {tgt} (le lecteur d'abord, jamais le clic) : {darkp}.\n\n"
        f"TOPONYMES dans la langue cible : {topo}. Garde la chaîne ville → province → "
        f"territoire. Conserve les NOMS PROPRES réels (lieux, artistes, festivals, œuvres) "
        f"et n'invente pas d'exonyme pour une ville qui n'en a pas de courant.\n\n"
        f"FAITS PRÉSERVÉS (les faits ne changent pas d'une langue à l'autre) : dates, "
        f"programme, line-up, lieu, horaires, tarifs, chiffres IDENTIQUES à la source. "
        f"Seule l'EXPRESSION est réécrite. Un programme / une liste se traduit LIGNE À "
        f"LIGNE, sans en perdre ni en fusionner aucune.\n\n"
        f"REGISTRE : soutenu mais accessible, phrases claires, pas de jargon gratuit. "
        f"{boussole}\n\n")


def _extract_json(resp) -> str:
    """Extrait le texte d'une réponse Anthropic et retire un éventuel fence ```json."""
    txt = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        txt = txt[4:] if txt.lower().startswith("json") else txt
    return txt


def translate_title_desc(client, model, title: str, desc: str, target: str,
                         voix: str = "") -> dict | None:
    """Renvoie {'title':..., 'description':...} traduits, ou None si échec.

    voix : bloc de voix éditoriale (utils.voix.voix_block()) préfixé au prompt — il
    RÉGIT le ton, le vocabulaire interdit, la doctrine d'appartenance et les patterns,
    en italien comme en français. La traduction RE-VÉRIFIE contre ces règles."""
    tgt = _LANG_NAME[target]
    prompt = (
        _charte_prompt(target, voix) +
        f"Réponds UNIQUEMENT en JSON : "
        f'{{"title": "...", "description": "..."}}.\n\n'
        f"TITRE : {title}\n\nDESCRIPTION : {desc[:2000]}")
    try:
        # 4000 (relevé de 3000 le 2026-07-29 : encore tronqué en vrai sur une description
        # proche de la limite de 2000 caractères) : avec Sonnet une description longue peut
        # dépasser et tronquer le JSON avant l'accolade finale (« Expecting value »).
        resp = client.messages.create(
            model=model, max_tokens=4000,
            messages=[{"role": "user", "content": prompt}])
        if getattr(resp, "stop_reason", None) == "max_tokens":
            log.warning("Traduction titre/description tronquée (max_tokens) — ignorée.")
            return None
        txt = _extract_json(resp)
        # strict=False : le modèle laisse parfois un caractère de contrôle brut (saut de
        # ligne non échappé) dans une valeur JSON — le parseur strict rejette sinon un texte
        # par ailleurs valide (« Invalid control character »).
        data = json.loads(txt[txt.find("{"): txt.rfind("}") + 1], strict=False)
        t, d = (data.get("title") or "").strip(), (data.get("description") or "").strip()
        return {"title": t, "description": d} if t else None
    except (anthropic.APIError, ValueError, KeyError, TypeError) as exc:
        log.warning("Traduction échouée : %s", exc)
        return None


def translate_article(client, model, enrich_json: str, target: str,
                      voix: str = "") -> str | None:
    """Traduit la STRUCTURE `enrich_data` (l'article éditorial « escalier ») vers `target`
    pour donner à la fiche traduite la MÊME matière enrichie que la source.

    On ne traduit QUE les champs TEXTUELS de `article` — titre, chapô, corps (markdown),
    programme (liste ligne à ligne) et encadré — en appliquant EXACTEMENT la même charte
    que `translate_title_desc` (via `_charte_prompt`). Les FAITS (dates, chiffres, noms
    propres, line-up) et tous les champs non textuels (sources, confiance, a_verifier…)
    sont RECOPIÉS tels quels. Renvoie le JSON `enrich_data` traduit (mêmes clés), ou None
    si parse/appel échoue ou s'il n'y a rien de textuel à traduire."""
    try:
        data = json.loads(enrich_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    art = data.get("article")
    if not isinstance(art, dict) or not art:
        return None

    # Champs textuels présents à traduire (on n'envoie que ceux qui existent).
    payload: dict = {}
    for k in ("titre", "chapo", "corps", "encadre"):
        v = art.get(k)
        if isinstance(v, str) and v.strip():
            payload[k] = v
    prog = art.get("programme")
    if isinstance(prog, str):
        prog_src = [prog]
    elif isinstance(prog, list):
        prog_src = [str(p) for p in prog]
    else:
        prog_src = []
    if prog_src:
        payload["programme"] = prog_src
    if not payload:
        return None  # article sans texte traduisible → rien à faire

    tgt = _LANG_NAME[target]
    prompt = (
        _charte_prompt(target, voix) +
        f"Tu traduis en {tgt} l'ARTICLE éditorial enrichi d'un événement culturel "
        f"(structure « escalier » : titre, chapô, corps, programme, encadré). Tu ne "
        f"réécris QUE l'EXPRESSION : les FAITS restent IDENTIQUES (dates, chiffres, noms "
        f"propres, lieux, line-up, horaires, tarifs).\n\n"
        f"IMPÉRATIF — traduis INTÉGRALEMENT la PROSE de CHAQUE champ, en particulier le long "
        f"« corps » (souvent plusieurs paragraphes) : aucune PHRASE ne doit rester dans la "
        f"langue d'origine, ne recopie jamais un champ tel quel. MAIS garde INCHANGÉS les "
        f"NOMS PROPRES — noms de personnes et d'œuvres, NOM OFFICIEL de l'événement — et les "
        f"TOPONYMES : utilise le nom {tgt} usuel quand il existe (Aoste→Aosta, Turin→Torino, "
        f"Nice→Nizza), mais GARDE tel quel un toponyme VALDÔTAIN sans équivalent (la Vallée "
        f"d'Aoste est officiellement bilingue FR/IT : ses noms de lieux français sont "
        f"légitimes, ne les italianise pas de force). « Préserver la structure » ne concerne "
        f"QUE les marqueurs markdown (##, ###, **, *, listes), JAMAIS la prose.\n\n"
        f"MARKDOWN — préserve rigoureusement la STRUCTURE du champ « corps » : sous-titres "
        f"« ## » et « ### » (mêmes niveaux, mêmes emplacements), gras « **…** », italique "
        f"« *…* », listes et sauts de paragraphe. Tu traduis le TEXTE dans les marqueurs, "
        f"jamais les marqueurs eux-mêmes.\n\n"
        f"« programme » est une LISTE : traduis-la LIGNE À LIGNE, en rendant EXACTEMENT le "
        f"même nombre d'entrées, dans le même ordre, sans en perdre, ajouter ni fusionner "
        f"aucune.\n\n"
        f"Réponds UNIQUEMENT en JSON, avec EXACTEMENT les mêmes clés que l'entrée ci-dessous "
        f"(« programme » = liste de MÊME longueur), sans autre commentaire :\n"
        f"{json.dumps(payload, ensure_ascii=False)}")
    try:
        # 8000 : l'article COMPLET traduit (long corps + programme + encadré) dépasse
        # facilement 4000 tokens ; tronquée, la réponse n'a plus d'accolade fermante et le
        # JSON est illisible (« Expecting value » → repli description seule). On garde une
        # marge large, et on détecte une éventuelle troncature pour ne pas publier un
        # article amputé.
        resp = client.messages.create(
            model=model, max_tokens=8000,
            messages=[{"role": "user", "content": prompt}])
        if getattr(resp, "stop_reason", None) == "max_tokens":
            log.warning("Traduction de l'article tronquée (max_tokens) — article ignoré.")
            return None
        txt = _extract_json(resp)
        out = json.loads(txt[txt.find("{"): txt.rfind("}") + 1], strict=False)
        if not isinstance(out, dict):
            return None
    except (anthropic.APIError, ValueError, KeyError, TypeError) as exc:
        log.warning("Traduction de l'article échouée : %s", exc)
        return None

    # Reconstruit l'article : on part de l'original (faits/champs non textuels préservés)
    # et on remplace UNIQUEMENT les champs textuels effectivement retraduits.
    new_art = dict(art)
    for k in ("titre", "chapo", "corps", "encadre"):
        if k in payload:
            v = out.get(k)
            if isinstance(v, str) and v.strip():
                new_art[k] = v
    if "programme" in payload:
        op = out.get("programme")
        if isinstance(op, str):
            op = [op]
        if isinstance(op, list) and len(op) == len(prog_src):
            new_art["programme"] = [str(x) for x in op]
        else:
            # Longueur incohérente → on GARDE le programme source (aucune ligne perdue),
            # quitte à laisser ces faits non traduits plutôt qu'en tronquer.
            log.warning("Programme traduit incohérent (%s≠%s lignes) — original conservé.",
                        len(op) if isinstance(op, list) else "?", len(prog_src))
    new_data = dict(data)
    new_data["article"] = new_art
    return json.dumps(new_data, ensure_ascii=False)


def _retranslate_one(tw: dict, args, client, voix) -> str:
    """RE-TRADUIT un jumeau EXISTANT (voir `_retranslate`), avec sa PROPRE connexion SQLite
    (WAL) — permet l'appel en parallèle sur plusieurs jumeaux (cf. `_retranslate`,
    ThreadPoolExecutor). Renvoie 'done' | 'skip' | 'error'."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        orig = conn.execute("SELECT * FROM events_raw WHERE id=?", (tw["translation_of"],)).fetchone()
        if not orig:
            return "skip"
        orig = dict(orig)
        tgt = (tw.get("translated_lang") or _target(detect_lang(
            orig.get("title", ""), orig.get("description", ""), orig.get("territoire", "")))).strip()
        log.info("[orig %s → jumeau %s] re-traduction %s : %s", orig["id"], tw["id"], tgt,
                 (orig.get("title") or "")[:50])
        if not args.apply:
            return "skip"
        if not client:
            log.error("[jumeau %s] ANTHROPIC_API_KEY absente — impossible de re-traduire.", tw["id"])
            return "error"
        tr = translate_title_desc(client, args.model, orig.get("title", ""),
                                  orig.get("description", "") or "", tgt, voix)
        if not tr:
            return "error"
        tr_enrich = tr_art_title = ""
        src_enrich = (orig.get("enrich_data") or "").strip()
        if src_enrich:
            ea = translate_article(client, args.model, src_enrich, tgt, voix)
            if ea:
                tr_enrich = ea
                try:
                    tr_art_title = ((json.loads(ea).get("article") or {}).get("titre") or "").strip()
                except (ValueError, TypeError):
                    tr_art_title = ""
        # Même portillon que dans `_translate_one` : une re-traduction repart de la même
        # matière et peut dériver de la même façon. Refuser ici ne perd rien — le jumeau
        # existant reste EN L'ÉTAT (ni base ni WP touchés) et la commande est rejouable.
        verdict, motif = verdict_titre_traduit([tr["title"], tr_art_title], orig)
        if verdict == "suspect":
            log.error("[jumeau %s] REFUS — titre re-traduit incohérent avec l'original %s : "
                      "« %s » — %s. Fiche laissée intacte.",
                      tw["id"], orig["id"], (tr_art_title or tr["title"])[:70], motif)
            return "refus"
        conn.execute(
            "UPDATE events_raw SET title=?, description=?, article_title=?, enrich_data=?, "
            "translated_at=datetime('now') WHERE id=?",
            (tr["title"], tr["description"], tr_art_title, tr_enrich, tw["id"]))
        conn.commit()
        # Met à jour la fiche WP traduite EXISTANTE (garde wp_post_id_as → update, pas de doublon).
        upd = dict(tw)
        upd.update({"title": tr["title"], "description": tr["description"],
                    "article_title": tr_art_title, "enrich_data": tr_enrich, "force_lang": tgt})
        publish_to_as(upd)
        log.info("[jumeau %s] re-traduit (%s) : %s", tw["id"], tgt, tr["title"][:50])
        return "done"
    finally:
        conn.close()


def _retranslate(args, client, voix) -> int:
    """RE-TRADUIT le jumeau EXISTANT des ids ORIGINAUX donnés : régénère titre + description
    + article (enrich_data) depuis l'original avec les règles courantes et MET À JOUR la fiche
    traduite en place (garde son id, son wp_post_id_as → update WP, sa liaison Polylang).
    Sert au re-travail rétroactif — ne crée jamais de doublon. EN PARALLÈLE (TRANSLATE_WORKERS,
    déf. 3) : chaque jumeau est indépendant, cf. `_retranslate_one` (sa propre connexion)."""
    if not args.ids:
        log.error("--retranslate nécessite des ids (fiches ORIGINALES dont on re-traduit le jumeau).")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ph = ",".join("?" * len(args.ids))
    twins = [dict(r) for r in conn.execute(
        f"SELECT * FROM events_raw WHERE translation_of IN ({ph}) AND duplicate_of IS NULL",
        args.ids).fetchall()]
    conn.close()
    log.info("%d jumeau(x) à re-traduire%s.", len(twins), "" if args.apply else " (simulation)")
    try:
        workers = max(1, int(os.getenv("TRANSLATE_WORKERS", "3") or 3))
    except ValueError:
        workers = 3
    results: list[str] = []
    if twins:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="retranslate") as ex:
            futures = [ex.submit(_retranslate_one, tw, args, client, voix) for tw in twins]
            for fut in futures:
                try:
                    results.append(fut.result())
                except Exception as exc:  # noqa: BLE001 — un worker ne doit jamais planter le lot
                    log.warning("worker en échec (exception non gérée) : %s", exc)
                    results.append("error")
    done = results.count("done")
    log.info("Re-traduction terminée — %d jumeau(x) mis à jour%s.", done,
             "" if args.apply else "  (simulation : rien écrit)")
    return 0


def _translate_one(ev: dict, args, client, api_key: str, voix: str, wp_url: str,
                   auth: tuple, img_lang: dict, img_lang_lock: threading.Lock) -> str:
    """Traduit UN événement de bout en bout (titre/description + article + publication WP
    + liaison Polylang), avec sa PROPRE connexion SQLite (WAL) — permet l'appel en parallèle
    sur plusieurs événements (cf. main(), ThreadPoolExecutor). Renvoie 'done' | 'skip' |
    'error'. La réservation de `img_lang` (dédup affiche) se fait ICI, sous verrou, AVANT
    tout travail — jamais après coup : sinon deux threads pourraient tous deux voir
    l'affiche « libre » avant que l'un des deux ne l'ait marquée prise."""
    # Langue RÉELLE = celle de l'article déjà rédigé s'il existe (jamais le seul
    # titre brut) : scripts.enrich écrit TOUJOURS en français par défaut, un titre
    # italien à la source peut donc déjà porter un article français. Sans ce
    # contrôle, on traduirait un article déjà français « vers » le français —
    # produisant un quasi-doublon au lieu d'une vraie traduction (constaté : id 4122).
    src = effective_lang(ev)
    tgt = _target(src)
    img = ev.get("url_image") or ""
    if img:
        with img_lang_lock:
            if img in img_lang.get(tgt, set()):
                log.info("[%s] jumelle %s déjà présente (même affiche) — ignoré : %s",
                         ev["id"], tgt, (ev.get("title") or "")[:50])
                return "skip"
            img_lang.setdefault(tgt, set()).add(img)  # réservé — voir docstring
    log.info("[%s] %s→%s (score %s) : %s", ev["id"], src, tgt,
             ev.get("user_score") if ev.get("user_score") is not None else ev.get("llm_score"),
             (ev.get("title") or "")[:60])
    if not args.apply:
        return "skip"
    if not (client and api_key):
        log.error("[%s] ANTHROPIC_API_KEY absente — impossible de traduire.", ev["id"])
        return "error"
    tr = translate_title_desc(client, args.model, ev.get("title", ""),
                              ev.get("description", "") or "", tgt, voix)
    if not tr:
        return "error"
    # Parité éditoriale : si la source porte un article enrichi (enrich_data), on le
    # TRADUIT pour que la fiche cible reçoive le même « escalier » que la version FR
    # (build_post le rend depuis enrich_data). Repli : sans enrich_data, on retombe
    # sur la description traduite seule (comportement historique).
    src_enrich = (ev.get("enrich_data") or "").strip()
    tr_enrich = ""
    tr_art_title = ""
    if src_enrich:
        ea = translate_article(client, args.model, src_enrich, tgt, voix)
        if ea:
            tr_enrich = ea
            try:
                tr_art_title = ((json.loads(ea).get("article") or {}).get("titre") or "").strip()
            except (ValueError, TypeError):
                tr_art_title = ""

    # PORTILLON DE JUSTESSE (C2 de docs/GO_NOGO_TRADUCTION.md) — le SEUL filet sur ce
    # chemin : ce script publie DIRECTEMENT (publish_to_as ci-dessous), sans la porte de
    # complétude de publish_batch_as, et la relecture de site_audit est structurellement
    # aveugle à une contamination cohérente (elle compare le site à la base, or c'est la
    # base qui est fausse). Sans ce contrôle, rien entre le LLM et la mise en ligne.
    #
    # Le verdict compare le titre PRODUIT à l'identité FACTUELLE de l'original (titre
    # scrapé, lieu, ville, organisateur, territoire) — jamais à la description, qui est
    # précisément le canal par lequel WP#6798 a été contaminé, ni au titre de la fiche
    # traduite elle-même, qui se confirmerait tout seul. Il s'ABSTIENT dès que le titre
    # ne nomme rien de vérifiable : la réécriture éditoriale du titre est autorisée par
    # la charte (_charte_prompt), une traduction légitime ne partage souvent aucun mot
    # avec sa source, et une alerte qui crie tous les jours finit ignorée.
    #
    # POURQUOI BLOQUANT ICI, alors que le même verdict n'est qu'un ⚠ dans batch_report :
    # refuser ici, ce n'est pas retenir une fiche, c'est ne pas en CRÉER une. L'original
    # n'est pas marqué (translated_at reste vide), il se represente au run suivant, et le
    # LLM étant stochastique un titre correctement ancré passera. Le coût d'un faux refus
    # est un appel API et un jour de retard ; le coût d'un faux passage est une fiche
    # italienne en ligne portant le titre d'un autre événement — l'incident qui a mis ce
    # cron en pause. À l'inverse, un ✗ dans batch_report retiendrait une fiche déjà
    # produite, sans recours : d'où l'asymétrie, assumée.
    # ⚠ CONSÉQUENCE À CONNAÎTRE : un original systématiquement refusé reste en tête de la
    # file (tri par score) et consomme un créneau de --cap à chaque run. C'est VOULU — un
    # refus répété signale une fiche dont la matière est polluée en base, à réparer
    # (repair_polluted_descriptions / audit_dedupe_damage), pas à traduire — mais avec
    # --cap 2, deux refus persistants arrêtent la traduction. Le message Slack les nomme.
    verdict, motif = verdict_titre_traduit([tr["title"], tr_art_title], ev)
    if verdict == "suspect":
        log.error("[%s] REFUS — titre traduit incohérent avec l'original : « %s » — %s "
                  "(original : « %s » · %s, %s). Rien n'a été publié.",
                  ev["id"], (tr_art_title or tr["title"])[:70], motif,
                  (ev.get("title") or "")[:40], (ev.get("lieu") or "—")[:30],
                  (ev.get("ville") or "—")[:20])
        return "refus"
    log.debug("[%s] titre traduit : %s (%s)", ev["id"], verdict, motif)

    new_ev = dict(ev)
    new_ev.update({
        "title": tr["title"], "description": tr["description"],
        "article_title": tr_art_title, "article_md": "", "enrich_data": tr_enrich,
        "seo_title": "", "seo_meta": "", "seo_slug": "", "seo_keyphrase": "",
        "force_lang": tgt, "force_create": True,
        "wp_post_id_as": None, "wp_post_id_cs": None,
        # URL commune à la paire (retour Franck : sans ça, impossible de s'y
        # retrouver) — la fiche traduite reprend le slug de l'original.
        "slug": _slug_of(ev.get("wp_permalink_as")),
    })
    new_ev.pop("id", None)
    wp_id, permalink, raw_url = publish_to_as(new_ev)
    if not wp_id:
        log.warning("[%s] publication de la traduction échouée.", ev["id"])
        return "error"
    conn = sqlite3.connect(DB_PATH)
    try:
        # Enregistre la fiche traduite (url_source synthétique — la colonne est UNIQUE).
        # enrich_status='enriched' : défense en profondeur (en plus de l'exclusion
        # translation_of dans enrich.select_events) — cette fiche ne doit JAMAIS être
        # reprise par scripts.enrich, qui écrirait un article français par-dessus.
        conn.execute(
            "INSERT INTO events_raw (title, description, date_start, date_event_start, "
            "date_event_end, lieu, ville, territoire, url_source, url_image, organisateur, "
            "source_name, source_type, llm_score, user_score, llm_categorie, statut, "
            "wp_post_id_as, wp_permalink_as, wp_raw_image_url_as, published_as_date, "
            "translation_of, translated_lang, article_title, enrich_data, image_credit, "
            "enrich_status, date_source) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tr["title"], tr["description"], ev.get("date_start"), ev.get("date_event_start"),
             ev.get("date_event_end"), ev.get("lieu"), ev.get("ville"), ev.get("territoire"),
             f"translated:{ev['id']}:{tgt}", ev.get("url_image"), ev.get("organisateur"),
             ev.get("source_name"), ev.get("source_type"), ev.get("llm_score"),
             ev.get("user_score"), ev.get("llm_categorie"), ev.get("statut"), wp_id, permalink,
             raw_url, datetime.now().isoformat(timespec="seconds"), ev["id"], tgt,
             tr_art_title, tr_enrich, ev.get("image_credit"), "enriched",
             # CAUSE RACINE du bug de dates du 2026-08-01 : les dates étaient bien copiées
             # de l'original ci-dessus, mais `date_source` restait NULL — la fiche passait
             # donc pour « jamais datée » et scripts/dates.py la re-datait en re-parsant
             # son texte ITALIEN avec un parseur français (Jazz Art décalé de 2 mois,
             # Matisse d'1 mois, EN LIGNE). Marquer la provenance rend la copie visible et
             # traçable ; l'exclusion des traductions dans dates.py reste la ceinture.
             "copie-traduction"))
        # Lie les deux fiches (Polylang) via l'endpoint.
        if all([wp_url, auth[0], auth[1]]):
            _post_link(wp_url, auth, {src: int(ev["wp_post_id_as"]), tgt: int(wp_id)})
        conn.execute("UPDATE events_raw SET translated_at=? WHERE id=?",
                     (datetime.now().isoformat(timespec="seconds"), ev["id"]))
        conn.commit()
    finally:
        conn.close()
    log.info("[%s] traduit → WP#%s (%s), lié.", ev["id"], wp_id, tgt)
    return "done"


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Traduit les événements à bon score (FR↔IT).")
    parser.add_argument("--apply", action="store_true", help="Exécute (sinon simulation).")
    parser.add_argument("--min-score", type=int, default=6, help="Score minimum (défaut 6).")
    parser.add_argument("--cap", type=int, default=10, help="Nb max par run (défaut 10).")
    parser.add_argument("--territoire", default="",
                        help="Filtre territoire (slug : %s)." % ", ".join(_TERR_KEYS))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("ids", nargs="*", type=int,
                        help="Ids d'événements ORIGINAUX dont on RE-TRADUIT le jumeau existant "
                             "(avec --retranslate) — sert au re-travail rétroactif.")
    parser.add_argument("--retranslate", action="store_true",
                        help="RE-TRADUIT le jumeau EXISTANT des ids donnés (met à jour la fiche "
                             "traduite en place avec les règles courantes : article complet, voix, "
                             "toponymes) au lieu de créer une nouvelle traduction.")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _ensure_cols(conn)

    # Index des affiches par langue (dédup : ne pas re-traduire un événement dont la
    # jumelle dans la langue cible existe déjà — même image = même événement bilingue).
    # effective_lang, PAS detect_lang sur le seul titre : sinon un événement au titre
    # italien mais à l'article déjà français se classe lui-même en « it » et se retrouve
    # à bloquer SA PROPRE traduction (sa propre image « existe déjà » côté it — lui).
    img_lang: dict[str, set] = {"fr": set(), "it": set()}
    for r in conn.execute("SELECT title, description, territoire, url_image, article_title, "
                          "enrich_data FROM events_raw WHERE COALESCE(url_image,'')<>'' "
                          "AND COALESCE(wp_post_id_as,0)>0 AND duplicate_of IS NULL"):
        img_lang[effective_lang(dict(r))].add(r["url_image"])

    terr_keys = None
    if args.territoire:
        terr_keys = _TERR_KEYS.get(args.territoire.strip().lower())
        if not terr_keys:
            log.error("Territoire inconnu : %s (attendus : %s)",
                      args.territoire, ", ".join(_TERR_KEYS))
            conn.close()
            return 2

    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0)>0 AND duplicate_of IS NULL "
        "AND COALESCE(translation_of,0)=0 AND COALESCE(translated_at,'')='' "
        # JAMAIS traduire une fiche que la MACHINE a elle-même produite (C3 de
        # docs/GO_NOGO_TRADUCTION.md). `translation_of` ne suffit pas : c'est justement le
        # rôle de scripts/unlink_bad_translations.py de l'effacer sur une paire mal appariée,
        # et la fiche machine redevient alors candidate — elle serait re-traduite vers sa
        # langue d'origine, produisant une 3e fiche, doublon de l'original, avec la dérive
        # de titre appliquée deux fois. `url_source` est le SEUL marqueur qui survit au
        # déliage : il est posé à l'insertion sous la forme « translated:<id>:<lang> »
        # (voir _translate_one) et la colonne est UNIQUE, donc jamais réécrite.
        "AND COALESCE(url_source,'') NOT LIKE 'translated:%' "
        # Déjà une jumelle NATIVE liée (link_translations_as, mécanisme B — source déjà
        # bilingue) : ne pas retraduire, ce serait une 3e fiche redondante.
        "AND id NOT IN (SELECT translation_of FROM events_raw "
        "               WHERE COALESCE(translation_of,0)!=0) "
        "AND COALESCE(user_score, llm_score, 0) >= ? "
        "ORDER BY COALESCE(user_score, llm_score, 0) DESC, id ASC",
        (args.min_score,)).fetchall()]
    if terr_keys:                                       # filtre territoire AVANT le plafond
        rows = [r for r in rows if any(k in _norm(r.get("territoire", "")) for k in terr_keys)]
    rows = rows[:args.cap]
    log.info("%d événement(s) candidat(s) (score ≥ %d, en ligne, non traduits%s)",
             len(rows), args.min_score,
             ", territoire=" + args.territoire if args.territoire else "")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key) if (api_key and args.apply) else None
    voix = voix_block()  # règles éditoriales (bilingues via le lexique) injectées à la traduction
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))

    conn.close()

    if args.retranslate:
        return _retranslate(args, client, voix)

    # PARALLÉLISATION (TRANSLATE_WORKERS, déf. 3) : chaque événement passe par 1-2 appels
    # LLM (titre/description + article complet) + une publication WP — en séquentiel, un
    # lot de 10 prenait facilement 15-20 min. `img_lang_lock` protège la réservation
    # d'affiche (dédup « même image = même événement bilingue ») : SANS lui, deux threads
    # pourraient chacun voir l'affiche « libre » avant que l'un des deux ne l'ait marquée
    # prise, et produire deux traductions pour le même événement.
    img_lang_lock = threading.Lock()
    try:
        workers = max(1, int(os.getenv("TRANSLATE_WORKERS", "3") or 3))
    except ValueError:
        workers = 3
    results: list[str] = []
    if rows:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="translate") as ex:
            futures = [ex.submit(_translate_one, ev, args, client, api_key, voix, wp_url,
                                 auth, img_lang, img_lang_lock) for ev in rows]
            for fut in futures:
                try:
                    results.append(fut.result())
                except Exception as exc:  # noqa: BLE001 — un worker ne doit jamais planter le lot
                    log.warning("worker en échec (exception non gérée) : %s", exc)
                    results.append("error")

    done, skipped, errors = results.count("done"), results.count("skip"), results.count("error")
    log.info("=== Traduction terminée : %d traduit(s), %d ignoré(s)%s ===",
             done, skipped, "" if args.apply else "  (simulation : rien écrit)")
    if args.apply:
        # Rapport uniquement quand on a vraiment agi (une simulation quotidienne en cron
        # inonderait Slack pour rien) — cf. utils.pipeline_status pour le lot quotidien.
        from utils import slack
        from utils import pipeline_status
        msg = (f"🌍 *Traduction quotidienne* — {done} traduit(s) sur {len(rows)} "
               f"candidat(s), {skipped} ignoré(s)")
        if errors:
            msg += f", {errors} erreur(s)"
        slack.notify(msg)
        pipeline_status.record_run("translate_events", ok=done, warn=skipped, error=errors,
                                   summary=msg[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
