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
import re
import sqlite3
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urlparse

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.lang import (detect_lang, effective_lang, paragraphes_mauvaise_langue,
                        titre_reecrit_mauvaise_langue, titre_semble_intraduit)
from utils.coherence import incoherence_description
from utils import acronymes
from utils import vocabulaire
from utils import verrou
from scripts.scraper_events import init_db
from scripts.publisher_as import (publish_to_as, wp_original_est_en_ligne,
                                  wp_site_joignable)
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
                      ("translated_lang", "TEXT"),
                      # Le couple compteur + empreinte qui ferme le martèlement des
                      # portillons — voir _rearme_traductions plus bas.
                      ("traduction_tentatives", "INTEGER DEFAULT 0"),
                      ("traduction_matiere", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass


# ══ LE MARTÈLEMENT DES PORTILLONS, ET SON ROUVREUR ═══════════════════════════════════
#
# MESURÉ EN PRODUCTION dans la nuit du 2026-08-17 : le portillon de langue a refusé CINQ
# FOIS la même fiche [473] « La Saint-Ours 2026 — Rendez Vous en Vallée d'Aoste », puis
# [4702] « Glaciers, enquête sur une disparition ». Deux appels API par passage, toutes
# les nuits, pour un résultat identique.
#
# CE QUE ÇA DÉMENT, ET C'ÉTAIT ÉCRIT DANS CE FICHIER : « le LLM étant stochastique un
# titre correctement ancré passera ». C'est l'hypothèse que CLAUDE.md (règle 3) interdit
# de poser sans la tester — « si la réponse repose sur le LLM est stochastique, c'est une
# hypothèse : la tester ou renoncer ». La production l'a testée : cinq fois le même refus.
#
# ET LE VERDICT N'EST PAS FORCÉMENT FAUX. « Rendez Vous en Vallée d'Aoste » est le NOM
# PROPRE de l'événement : sa version italienne lui ressemblera toujours, donc le portillon
# refusera toujours. Aucune heuristique plus fine ne réglera ce cas — c'est la RÉPÉTITION
# qu'il faut arrêter, pas le verdict.
#
# D'où le mécanisme éprouvé de dates.py : un compteur, une empreinte de la matière jugée,
# et un rouvreur qui ne dépend de personne. Après MAX_REFUS refus sur une matière
# INCHANGÉE, la fiche est garée — elle cesse de consommer un créneau de --cap et des
# appels API. Dès que sa matière bouge (titre corrigé, description réparée, article
# ré-enrichi), elle repart d'elle-même le lendemain.
MAX_REFUS = int(os.getenv("TRADUCTION_MAX_REFUS", "3"))


def _empreinte_traduction(ev: dict) -> str:
    """Résumé stable de ce sur quoi les portillons se prononcent. S'il change, un nouvel
    essai peut légitimement donner un AUTRE résultat — c'est ce qui autorise à rouvrir."""
    import hashlib
    brut = "|".join(str(ev.get(c) or "") for c in
                    ("title", "description", "lieu", "ville", "organisateur", "enrich_data"))
    return hashlib.sha1(brut.encode("utf-8", "replace")).hexdigest()[:16]


def _rearme_traductions(conn) -> int:
    """C'EST LE ROUVREUR. Il ne dépend d'aucune commande ni d'aucun humain : une fiche
    garée dont la matière a changé redevient candidate dès le lendemain."""
    lignes = conn.execute(
        "SELECT id, title, description, lieu, ville, organisateur, enrich_data, "
        "       traduction_matiere FROM events_raw "
        "WHERE COALESCE(traduction_tentatives,0) >= ?", (MAX_REFUS,)).fetchall()
    rouverts = [r["id"] for r in lignes
                if r["traduction_matiere"]
                and _empreinte_traduction(dict(r)) != r["traduction_matiere"]]
    if rouverts:
        ph = ",".join("?" * len(rouverts))
        conn.execute(f"UPDATE events_raw SET traduction_tentatives=0 "
                     f"WHERE id IN ({ph})", rouverts)
        conn.commit()
        log.info("Ré-ouverture : %d fiche(s) dont la matière a changé depuis leur dernier "
                 "refus de traduction — elles repassent : %s", len(rouverts),
                 " ".join(str(i) for i in rouverts[:12]))
    return len(rouverts)


def _rearme_traductions_orphelines(conn) -> int:
    """LE DEUXIÈME ROUVREUR, écrit le 2026-09-15. Il rouvre les fiches que `translated_at`
    avait garées POUR TOUJOURS alors que leur jumelle n'existe plus.

    D'OÙ ÇA VIENT — Franck : « encore des événements sans traduction ! », puis « ça doit
    suivre un processus ». Mesuré le jour même sur le site : 202 fiches françaises
    publiées, 117 sans jumelle italienne, dont 63 encore devant nous. Or le cron en
    traduit 25 par jour : cette file aurait dû être vide. Elle ne l'est pas parce que
    `translated_at` est un état TERMINAL sans rouvreur (règle 3) — il est posé au succès
    et rien ne l'efface ensuite, sauf `scripts/repair_translation.py`, c'est-à-dire un
    humain qui tape une commande, ce que ce dépôt ne compte pas comme une réponse.

    Conséquence : dès qu'une jumelle disparaît — publication annulée, fiche défusionnée,
    ligne supprimée — l'original n'est JAMAIS repris. Il reste seul, en français, sur un
    site bilingue, et aucun compteur ne le dit.

    LE GARDE-FOU, et c'est lui qui rend la chose sûre : on ne rouvre que si la jumelle est
    introuvable des DEUX façons. `translation_of` ne suffit pas — `unlink_bad_translations`
    l'efface justement sur une paire mal appariée, et la jumelle continue d'exister. Le
    marqueur `url_source = 'translated:<id>:<lang>'` est posé à l'insertion et la colonne
    est UNIQUE : il survit au déliage. Une fiche seulement DÉLIÉE garde donc son marqueur,
    n'est pas rouverte, et on ne fabrique pas une troisième fiche.

    Les fiches rouvertes sont NOMMÉES : une file qui grossit sans le dire est le symétrique
    exact du défaut qu'on corrige ici."""
    lignes = conn.execute(
        "SELECT id, title, article_title, translated_at FROM events_raw "
        "WHERE COALESCE(translated_at,'')<>'' AND COALESCE(translation_of,0)=0 "
        "AND COALESCE(wp_post_id_as,0)>0 AND duplicate_of IS NULL "
        "AND id NOT IN (SELECT translation_of FROM events_raw "
        "               WHERE COALESCE(translation_of,0)!=0)").fetchall()
    marqueurs = {r[0] for r in conn.execute(
        "SELECT url_source FROM events_raw WHERE COALESCE(url_source,'') LIKE 'translated:%'")}
    orphelins = [dict(r) for r in lignes
                 if not any(str(m).startswith(f"translated:{r['id']}:") for m in marqueurs)]
    if orphelins:
        ph = ",".join("?" * len(orphelins))
        conn.execute(f"UPDATE events_raw SET translated_at=NULL WHERE id IN ({ph})",
                     [o["id"] for o in orphelins])
        conn.commit()
        log.warning("Ré-ouverture : %d fiche(s) marquées traduites dont la jumelle "
                    "n'existe plus — elles repassent en file : %s", len(orphelins),
                    ", ".join(f"[{o['id']}] {(o.get('article_title') or o.get('title') or '')[:34]}"
                              for o in orphelins[:8]))
    return len(orphelins)


def bandeau_plafond(non_tentees: int) -> str:
    """L'en-tête de bilan quand le lot s'est arrêté sur le plafond API. Fonction pure,
    éprouvée par tests/test_traduction_orphelines.py — parce qu'un défaut de FORME ne se
    voit pas dans le code, il se voit dans le message qui part.

    MESURÉ LE 2026-09-15, en lisant logs/translate.log : du 10 au 14/09, cinq runs
    d'affilée ont posté « 0 traduit(s) sur 10 candidat(s), 2 ignoré(s) ». Ça se lit comme
    une matinée calme. La vraie phrase, elle, n'est jamais sortie du journal :
    « Your credit balance is too low to access the Anthropic API ». Cinq jours de
    traduction perdus parce que le bilan donnait le NOMBRE sans la CAUSE, alors que le
    script la tenait.

    Trois choses, donc, et dans cet ordre : que c'est bloqué, que rien n'est perdu, et le
    geste exact qui débloque."""
    return ("🔴 *Crédit API épuisé — traduction à l'arrêt*\n"
            f"{non_tentees} fiche(s) non tentée(s) ce matin, et rien ne repartira tant "
            "que le solde n'est pas rechargé : console Anthropic → *Plans & Billing*. "
            "Aucune fiche n'a été marquée, aucune n'est perdue — elles repartent toutes "
            "seules au run suivant.\n")


def garees(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """(candidates encore actives, fiches garées). Fonction pure, éprouvée par
    tests/test_traduction_garage.py."""
    actives = [r for r in rows if (r.get("traduction_tentatives") or 0) < MAX_REFUS]
    return actives, [r for r in rows if (r.get("traduction_tentatives") or 0) >= MAX_REFUS]


def marquer_refus(conn, ev: dict) -> None:
    """Compte le refus ET fige la matière jugée. C'est le COUPLE qui ferme le martèlement :
    le compteur seul garerait pour toujours, l'empreinte seule ne compterait rien."""
    conn.execute("UPDATE events_raw SET traduction_tentatives=COALESCE(traduction_tentatives,0)+1, "
                 "traduction_matiere=? WHERE id=?",
                 (_empreinte_traduction(ev), ev["id"]))
    conn.commit()


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
        superl = ('« incontournable », « magique », « à ne pas manquer », « événement phare »')
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
        f"Tu produis la version {tgt} d'un événement culturel de l'espace sabaud "
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
        f"VOCABULAIRE INTERDIT en {tgt} :\n{vocabulaire.consigne_prompt(target)}\n\n"
        f"DARK PATTERNS INTERDITS en {tgt} (le lecteur d'abord, jamais le clic) : {darkp}.\n\n"
        f"TOPONYMES dans la langue cible : {topo}. Garde la chaîne ville → province → "
        f"territoire. Conserve les NOMS PROPRES réels (lieux, artistes, festivals, œuvres) "
        f"et n'invente pas d'exonyme pour une ville qui n'en a pas de courant.\n\n"
        f"FAITS PRÉSERVÉS (les faits ne changent pas d'une langue à l'autre) : dates, "
        f"programme, line-up, lieu, horaires, tarifs, chiffres IDENTIQUES à la source. "
        f"Seule l'EXPRESSION est réécrite. Un programme / une liste se traduit LIGNE À "
        f"LIGNE, sans en perdre ni en fusionner aucune.\n\n"
        f"REGISTRE : soutenu mais accessible, pas de jargon gratuit. Phrases COURTES : une "
        f"idée par phrase, 20 mots au plus, jamais plus d'une subordonnée — une phrase "
        f"source trop longue se COUPE en deux au point, sans rien perdre. Voix ACTIVE de "
        f"préférence (« due curatori firmano la mostra », pas « la mostra è curata da »). "
        f"CONNECTEURS : garde ceux de la source, ne les efface pas en traduisant, et "
        f"rends-les par leur équivalent simple (poi, quindi, ma, perché, infine, prima, "
        f"dopo, anche, soprattutto) — jamais par un connecteur scolaire (« d'altronde », « in effetti »). "
        f"Mesuré le 21/09 avec le moteur de Yoast : « mots de liaison » est le premier "
        f"motif de rouge du site, et une traduction qui les rabote ferait retomber en "
        f"italien ce que le français vient de corriger. "
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
        resp = None
        # 4000 (relevé de 3000 le 2026-07-29), puis 7000 en second essai (2026-08-05,
        # incident en production : fiche 4161, description de 1213 caractères SEULEMENT
        # — bien sous la limite de 2000 — mais dont le titre source était déjà en
        # italien, gonflant probablement la sortie attendue. Sans second essai, une
        # fiche comme celle-ci redevient un CUL-DE-SAC SILENCIEUX : resélectionnée
        # chaque jour (translated_at reste vide, c'est voulu), elle échoue pour la
        # MÊME raison technique à chaque fois, sans jamais qu'un budget plus large soit
        # tenté. À la différence du portillon C2 plus bas (refus répété = signal éditorial
        # VOULU, cf. sa docstring), un dépassement de token est un problème de RESSOURCE,
        # pas de matière — retenter avec plus de budget est le bon réflexe avant de
        # renoncer pour la journée.
        for tentative, budget in ((1, 4000), (2, 7000)):
            resp = client.messages.create(
                model=model, max_tokens=budget,
                messages=[{"role": "user", "content": prompt}])
            # MESURÉ (2026-08-11) — et mesuré À CHAQUE TENTATIVE, y compris tronquée :
            # un essai coupé par max_tokens est facturé comme les autres. C'est même le
            # seul endroit où le gaspillage se voit (deux appels pour zéro traduction).
            from utils import usage
            usage.record_message(model, resp, label="traduction_titre")
            if getattr(resp, "stop_reason", None) != "max_tokens":
                break
            log.warning("Traduction titre/description tronquée (max_tokens=%d, essai %d/2).",
                       budget, tentative)
        else:
            return None  # les deux essais ont tronqué : on renonce pour aujourd'hui
        txt = _extract_json(resp)
        # strict=False : le modèle laisse parfois un caractère de contrôle brut (saut de
        # ligne non échappé) dans une valeur JSON — le parseur strict rejette sinon un texte
        # par ailleurs valide (« Invalid control character »).
        data = json.loads(txt[txt.find("{"): txt.rfind("}") + 1], strict=False)
        t, d = (data.get("title") or "").strip(), (data.get("description") or "").strip()
        return {"title": t, "description": d} if t else None
    except (anthropic.APIError, ValueError, KeyError, TypeError) as exc:
        # PLAFOND API ≠ échec de fiche (2026-08-04) : avaler ce cas-là faisait marteler la
        # boucle — 13 occurrences le 30/07, 15 le 31/07, une par fiche jusqu'au bout du
        # cap. Aucune corruption (rien n'était publié), mais du bruit qui noie le vrai
        # signal et des créneaux de --cap brûlés pour rien. On remonte, le lot s'arrête.
        from utils.api_limite import PlafondAPI, est_plafond
        if est_plafond(exc):
            raise PlafondAPI(str(exc)) from exc
        log.warning("Traduction échouée : %s", exc)
        return None


_SEP_PARAGRAPHE = re.compile(r"(\n\s*\n|(?<=[.!?])\n)")


def _paragraphes_restes(art: dict, target: str) -> list:
    """Paragraphes de chapô / corps / encadré restés dans l'autre langue que `target`."""
    out = []
    for champ in ("chapo", "corps", "encadre"):
        v = art.get(champ)
        if isinstance(v, str) and v.strip():
            out += paragraphes_mauvaise_langue(v, target)
    return out


def _retraduire_paragraphes(client, model, art: dict, suspects: list, target: str,
                            voix: str = "") -> dict | None:
    """Retraduit les SEULS paragraphes de `suspects` et les remet à leur place dans une
    copie de `art`. Même découpage que `utils.lang.paragraphes_mauvaise_langue`, pour
    retrouver chaque paragraphe là où il a été signalé. None si l'appel échoue ou si la
    réponse n'a pas autant d'entrées qu'envoyées — l'appelant refuse alors comme avant."""
    vises = {p for _, p in suspects}
    # (champ, index du morceau) de chaque paragraphe visé, dans l'ordre de lecture.
    morceaux: dict[str, list[str]] = {}
    places: list[tuple[str, int]] = []
    for champ in ("chapo", "corps", "encadre"):
        v = art.get(champ)
        if not (isinstance(v, str) and v.strip()):
            continue
        parts = _SEP_PARAGRAPHE.split(v)
        morceaux[champ] = parts
        for i in range(0, len(parts), 2):          # indices pairs : le texte ; impairs : séparateurs
            if re.sub(r"\s+", " ", parts[i]).strip() in vises:
                places.append((champ, i))
    if not places:
        return None
    textes = [morceaux[c][i].strip() for c, i in places]
    tgt = _LANG_NAME[target]
    prompt = (
        _charte_prompt(target, voix) +
        f"Voici des paragraphes d'un article, restés dans la mauvaise langue. Traduis "
        f"CHACUN intégralement en {tgt}. Garde tels quels les noms propres (personnes, "
        f"œuvres, NOM OFFICIEL de l'événement) et les marqueurs markdown (**, *, ##). "
        f"Réponds UNIQUEMENT par une liste JSON de chaînes, EXACTEMENT {len(textes)} "
        f"entrée(s), dans le même ordre :\n{json.dumps(textes, ensure_ascii=False)}")
    try:
        resp = client.messages.create(model=model, max_tokens=4000,
                                      messages=[{"role": "user", "content": prompt}])
        from utils import usage
        usage.record_message(model, resp, label="traduction_paragraphes")
        txt = _extract_json(resp)
        out = json.loads(txt[txt.find("["): txt.rfind("]") + 1], strict=False)
    except (anthropic.APIError, ValueError, KeyError, TypeError) as exc:
        from utils.api_limite import PlafondAPI, est_plafond
        if est_plafond(exc):
            raise PlafondAPI(str(exc)) from exc
        log.warning("Seconde passe (paragraphes) échouée : %s", exc)
        return None
    if not (isinstance(out, list) and len(out) == len(textes)
            and all(isinstance(x, str) and x.strip() for x in out)):
        log.warning("Seconde passe : %s entrée(s) rendue(s) pour %d envoyée(s) — ignorée.",
                    len(out) if isinstance(out, list) else "?", len(textes))
        return None
    for (champ, i), neuf in zip(places, out):
        morceaux[champ][i] = neuf.strip()
    corrige = dict(art)
    for champ, parts in morceaux.items():
        corrige[champ] = "".join(parts)
    log.info("Seconde passe : %d paragraphe(s) retraduit(s) à part.", len(textes))
    return corrige


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
    # 8000, ET C'EST LARGE — vérifié, pas supposé (2026-09-15). Ce plafond a été soupçonné
    # après un « Traduction de l'article tronquée (max_tokens) » sur ESTATE REALE, et la
    # mesure l'a disculpé : l'article de cette fiche fait 1 523 caractères, soit ~476
    # jetons, et la PLUS LONGUE fiche du site en fait 8 009, soit ~2 500. Aucun article ne
    # s'approche de 8 000 jetons de SORTIE.
    #
    # Une troncature ici ne dit donc pas « pas assez de place » : elle dit que le modèle
    # s'est emballé sur une matière courte. Le relancer à l'identique serait un refus qui
    # se rejoue sur la même entrée (règle 3) ; c'est `MAX_REFUS` qui s'en charge, sur
    # plusieurs jours et avec une matière qui a pu bouger entre-temps.
    #
    # Ce qui MANQUAIT, c'était de pouvoir trancher : le message ne disait ni le plafond ni
    # la taille de la source, donc le prochain lecteur refera l'enquête. Il les dit
    # désormais.
    _source_tokens = len(json.dumps(payload, ensure_ascii=False)) / 3.2
    _plafond = 8000
    try:
        resp = client.messages.create(
            model=model, max_tokens=_plafond,
            messages=[{"role": "user", "content": prompt}])
        from utils import usage
        usage.record_message(model, resp, label="traduction_article")
        if getattr(resp, "stop_reason", None) == "max_tokens":
            # Dire les DEUX nombres : sans eux, le lecteur du journal ne peut pas savoir
            # s'il manquait de la place ou si le modèle s'est emballé. C'est exactement
            # l'enquête que j'ai refaite le 15/09 faute de les avoir.
            log.warning("Traduction de l'article tronquée : plafond %d jetons pour une "
                        "source estimée à %d — article ignoré, fiche laissée intacte.",
                        _plafond, int(_source_tokens))
            return None
        txt = _extract_json(resp)
        out = json.loads(txt[txt.find("{"): txt.rfind("}") + 1], strict=False)
        if not isinstance(out, dict):
            return None
    except (anthropic.APIError, ValueError, KeyError, TypeError) as exc:
        # Même garde de plafond que translate_title_desc — cf. utils/api_limite.
        from utils.api_limite import PlafondAPI, est_plafond
        if est_plafond(exc):
            raise PlafondAPI(str(exc)) from exc
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
    # SIGLES développés à leur première mention, VERSION ITALIENNE (Franck, 2026-08-18
    # puis 31/08). Même mécanisme déterministe qu'à la rédaction FR (scripts/enrich.py) :
    # un contexte PARTAGÉ dans l'ordre de lecture, pour qu'un sigle du titre ET du corps
    # ne soit pas développé deux fois. N'agit que sur les champs RETRADUITS ci-dessus —
    # un champ non touché par cette traduction garde ce que la rédaction FR y a déjà mis.
    _sigles_vus_it: set = set()
    for _champ in ("titre", "chapo", "corps", "encadre"):
        if isinstance(new_art.get(_champ), str) and new_art[_champ]:
            new_art[_champ] = acronymes.developper(new_art[_champ], "it", _sigles_vus_it)
    if isinstance(new_art.get("programme"), list):
        new_art["programme"] = [
            acronymes.developper(str(p), "it", _sigles_vus_it) if isinstance(p, str) else p
            for p in new_art["programme"]]
    # ── PORTILLON DE LANGUE SUR LE CORPS (2026-09-15) ────────────────────────────────
    # Franck, devant WP#8324 en ligne : « problème de traduction (comment c'est encore
    # possible !?!?) ». Fiche italienne — URL /it/, territoire « Piemonte », langue
    # Polylang `it` — titre et premier paragraphe en italien, TROIS paragraphes du corps
    # en français. Mesuré ensuite sur tout le site : DIX fiches publiées dans ce cas,
    # 33 paragraphes.
    #
    # Trois portillons existaient déjà, TOUS sur le titre (`titre_semble_intraduit`,
    # `titre_reecrit_mauvaise_langue`, cohérence avec l'original) ; le corps était accepté
    # dès qu'il était une chaîne non vide. Le défaut était pourtant CONNU — voir le
    # commentaire de DEFAULT_MODEL en tête de ce fichier : « Haiku traduisait les champs
    # courts mais recopiait le long "corps" en français ». La parade avait été de changer
    # de modèle, pas de poser un détecteur : quand le modèle rate à son tour, rien ne voit.
    #
    # Renvoyer None laisse l'article NON traduit (les appelants font `if ea:`), donc la
    # fiche paraît avec son titre et sa description traduits, sans corps — dégradé, mais
    # jamais un paragraphe français sur une page italienne. La matière n'ayant pas changé,
    # la fiche revient au prochain passage et le compteur MAX_REFUS l'arrête au bout de
    # trois (cf. `garees` / `_rearme_traductions`).
    _suspects = _paragraphes_restes(new_art, target)
    if _suspects:
        # SECONDE PASSE, CIBLÉE (23/09/2026). Sept jumelles de Plaisirs de Culture ont
        # été refusées ici, toutes pour la même raison : des phrases françaises entières
        # (« Cette initiative s'inscrit dans la quatorzième édition… ») recopiées au milieu
        # d'un corps italien. Rejouer l'appel complet serait un refus qui se rejoue sur la
        # MÊME entrée (règle 3). Ce qui change ici, c'est l'ENTRÉE : on n'envoie plus que
        # les paragraphes restés en français, sans le long corps que le modèle recopie
        # (défaut déjà décrit à DEFAULT_MODEL). C'est une hypothèse, pas une certitude :
        # le journal dit « seconde passe : N paragraphe(s) », et le portillon ci-dessous
        # reste le juge — s'il en reste un seul, refus comme avant.
        _corrige = _retraduire_paragraphes(client, model, new_art, _suspects, target, voix)
        if _corrige is not None:
            new_art = _corrige
            _suspects = _paragraphes_restes(new_art, target)
            log.info("Seconde passe : %s", "tous les paragraphes sont traduits"
                     if not _suspects else f"{len(_suspects)} paragraphe(s) encore dans "
                                           f"l'autre langue")
    if _suspects:
        _suspects.sort(key=lambda x: -x[0])
        log.error("REFUS — %d paragraphe(s) du corps sont restés dans l'autre langue "
                  "(cible %s, écart %d) : « %s… ». Article laissé NON traduit.",
                  len(_suspects), target, _suspects[0][0], _suspects[0][1][:90])
        return None

    new_data = dict(data)
    new_data["article"] = new_art
    return json.dumps(new_data, ensure_ascii=False)


def cibler_ids(rows: list, ids: list) -> tuple[list, list]:
    """Restreint la file du jour aux ids demandés, dans l'ordre de la file ; rend aussi
    les ids demandés qui n'y sont PAS (à dire, jamais à taire)."""
    voulus = set(ids)
    gardes = [r for r in rows if r["id"] in voulus]
    trouves = {r["id"] for r in gardes}
    return gardes, [i for i in ids if i not in trouves]


def cible_retraduction(orig: dict, tw: dict) -> str:
    """La langue dans laquelle ré-écrire le jumeau : l'INVERSE de la langue actuelle de
    l'original, lue sur son article (effective_lang) — pas celle mémorisée à la création.

    23/09/2026, Plaisirs de Culture : des fiches publiées en italien (texte brut de la
    brochure) avaient reçu une jumelle FRANÇAISE (translated_lang='fr'). La rédaction a
    ensuite réécrit les originaux, en français comme toujours. `--retranslate` a relu
    translated_lang='fr' et a ré-écrit les jumelles… en français : une vingtaine
    d'événements avec DEUX fiches françaises, et plus aucune italienne. La langue
    mémorisée disait ce qui était vrai au moment de la création, pas ce qui l'est."""
    src = effective_lang(orig)
    if src in ("fr", "it"):
        return _target(src)
    return ((tw.get("translated_lang") or "").strip()
            or _target(detect_lang(orig.get("title", ""), orig.get("description", ""),
                                   orig.get("territoire", ""))))


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
        tgt = cible_retraduction(orig, tw)
        if tgt != (tw.get("translated_lang") or "").strip():
            log.warning("[jumeau %s] langue cible corrigée : %s → %s (l'original est "
                        "aujourd'hui en %s)", tw["id"], tw.get("translated_lang") or "?",
                        tgt, _target(tgt))
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
        # PORTILLON DE LANGUE — même garde que _translate_one_interne, même raison
        # (WP#2174, 2026-08-06) : un titre recopié tel quel passerait le portillon de
        # justesse ci-dessous sans broncher (il partage trivialement tous ses mots
        # avec l'original), donc il faut le vérifier ICI, séparément.
        if titre_semble_intraduit(tr["title"], tgt, orig.get("title", "")):
            log.error("[jumeau %s] REFUS — le titre re-\"traduit\" est resté dans "
                      "l'autre langue (cible %s) : « %s ». Fiche laissée intacte.",
                      tw["id"], tgt, tr["title"][:70])
            return "refus"
        if titre_reecrit_mauvaise_langue(tr["title"], tgt, orig.get("title", "")):
            log.error("[jumeau %s] REFUS — le titre re-traduit a été réécrit mais reste "
                      "dans l'autre langue (cible %s) : « %s ». Fiche laissée intacte.",
                      tw["id"], tgt, tr["title"][:70])
            return "refus"
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
        # L'ARTICLE A ÉTÉ REFUSÉ OU A ÉCHOUÉ → ne rien écrire (2026-09-15).
        # L'UPDATE ci-dessous pose `enrich_data=?` avec `tr_enrich`, qui vaut CHAÎNE VIDE
        # dans ce cas : sans ce garde-fou, une re-traduction refusée EFFACE l'article du
        # jumeau au lieu de le laisser tel quel. Trouvé en relisant ce chemin avant de
        # faire lancer la réparation des neuf fiches au corps mélangé — le portillon de
        # langue posé le même jour aurait donc vidé neuf fiches en ligne.
        #
        # Le commentaire ci-dessous promettait déjà « le jumeau existant reste EN L'ÉTAT » :
        # c'était vrai des refus de TITRE, qui sortent avant l'écriture, et faux du seul
        # chemin qui passe par l'article. Une promesse tenue par trois chemins sur quatre.
        if src_enrich and not tr_enrich:
            log.error("[jumeau %s] REFUS — l'article re-traduit n'a pas passé le contrôle "
                      "(voir la ligne REFUS ci-dessus). Fiche laissée INTACTE : mieux vaut "
                      "un corps mélangé qu'un corps effacé.", tw["id"])
            return "refus"

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
            "translated_lang=?, translated_at=datetime('now') WHERE id=?",
            (tr["title"], tr["description"], tr_art_title, tr_enrich, tgt, tw["id"]))
        conn.commit()
        # Met à jour la fiche WP traduite EXISTANTE (garde wp_post_id_as → update, pas de doublon).
        # skip_media=True : incident réel du 2026-08-06 — cet appel repoussait `url_image`
        # SANS le demander, écrasant une vraie photo posée à la main par Franck (côté
        # WordPress, jamais remontée dans `events_raw.url_image`) par la bannière de repli
        # restée en base. Une re-traduction ne change QUE le texte (titre/description/
        # article) — même motif que app.py:4025/4321 pour toute republication texte-seule.
        upd = dict(tw)
        upd.update({"title": tr["title"], "description": tr["description"],
                    "article_title": tr_art_title, "enrich_data": tr_enrich, "force_lang": tgt})
        publish_to_as(upd, skip_media=True)
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
    # ⚠️ NE JAMAIS RÉÉCRIRE LA PAGE DE L'ORIGINAL — garde-fou posé le 2026-09-21 au soir.
    #
    # MESURÉ CE JOUR-LÀ : la fiche 3491 est enregistrée comme la traduction de 2507 et
    # porte le MÊME `wp_post_id_as` qu'elle (WP#2190) — une ligne abîmée en base, pas une
    # traduction. Or `_retranslate_one` réécrit le jumeau EN PLACE, à son
    # `wp_post_id_as` : retraduire 2507 aurait réécrit la page FRANÇAISE de 2507 en
    # italien. (Sa vraie jumelle italienne existe par ailleurs : 5223 → WP#8132.)
    #
    # ICI ET PAS SEULEMENT DANS L'APPELANT, parce que `audit_langue_polylang` IMPRIME
    # cette commande pour qu'un humain la tape, et parce que `repair_lien_polylang
    # --retraduire` l'appelle tout seul depuis le cron hebdomadaire. Un garde-fou qui ne
    # vit que chez un appelant protège cet appelant-là, pas la fonction.
    postes_originaux = {r["id"]: (r["wp_post_id_as"] or 0) for r in conn.execute(
        f"SELECT id, wp_post_id_as FROM events_raw WHERE id IN ({ph})", args.ids)}
    sains = []
    for tw in twins:
        po = postes_originaux.get(tw.get("translation_of") or 0) or 0
        if po and (tw.get("wp_post_id_as") or 0) == po:
            log.error("[%s] REFUS de retraduction : ce jumeau porte le MÊME post que son "
                      "original (WP#%s). Le retraduire réécrirait la page de l'original "
                      "dans l'autre langue. La ligne est à trancher en base, pas à "
                      "retraduire.", tw["id"], po)
            continue
        sains.append(tw)
    twins = sains
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
    log.info("Re-traduction terminée — %d jumeau(x) mis à jour, %d refusé(s)%s.", done,
             results.count("refus"), "" if args.apply else "  (simulation : rien écrit)")
    return 0


def _est_visuel_de_secours(img: str, source) -> bool:
    return (source or "") == "banner" or "/fallback-" in (img or "")


def index_affiches(rows: list[dict]) -> dict:
    """Les affiches qui IDENTIFIENT un événement, rangées par langue — plus, sous la clé
    `_partagees`, celles qui n'identifient rien.

    LE DÉFAUT CORRIGÉ LE 2026-09-23. Le dédoublonnage « même affiche = même événement
    bilingue » prenait TOUTE image pour une identité. Or deux familles d'images sont
    partagées par construction : les 48 visuels de secours du site (une par territoire et
    catégorie), et l'affiche d'un festival posée sur chacun de ses rendez-vous (celle de
    Plaisirs de Culture sur 19 fiches). Une fiche française en visuel de secours voyait
    donc « sa jumelle italienne déjà présente » dès qu'une AUTRE fiche italienne portait
    le même visuel — et renvoyait `skip`, sans rien marquer : le même refus rejoué chaque
    jour sur la même entrée (règle 3). Mesuré ce jour-là : 81 fiches à venir sur 381
    publiées sans jumelle ; sur Plaisirs de Culture, 33 fiches, pas une seule traduite.

    Une image n'identifie un événement que si, dans sa langue, UNE SEULE fiche la porte,
    et si ce n'est pas un visuel de secours. La vraie paire (une fiche française et sa
    jumelle italienne native, même affiche) reste reconnue : une fiche par langue."""
    from collections import Counter
    compte = Counter()
    partagees = set()
    for r in rows:
        img = r.get("url_image") or ""
        if not img:
            continue
        if _est_visuel_de_secours(img, r.get("image_source")):
            partagees.add(img)
            continue
        compte[(effective_lang(r), img)] += 1
    partagees |= {img for (_l, img), n in compte.items() if n > 1}
    index: dict = {"fr": set(), "it": set(), "_partagees": partagees}
    for (lang, img), n in compte.items():
        if img not in partagees:
            index.setdefault(lang, set()).add(img)
    return index


def image_identifiante(img: str, source, index: dict) -> bool:
    """Vrai si cette image peut servir à reconnaître une jumelle (voir index_affiches)."""
    return bool(img) and not _est_visuel_de_secours(img, source) \
        and img not in index.get("_partagees", set())


def _translate_one(ev: dict, args, client, api_key: str, voix: str, wp_url: str,
                   auth: tuple, img_lang: dict, img_lang_lock: threading.Lock) -> str:
    """Traduit UN événement de bout en bout (titre/description + article + publication WP
    + liaison Polylang), avec sa PROPRE connexion SQLite (WAL) — permet l'appel en parallèle
    sur plusieurs événements (cf. main(), ThreadPoolExecutor). Renvoie 'done' | 'skip' |
    'refus' | 'lien_absent' | 'plafond' | 'error' — 'lien_absent' veut dire que la
    traduction est EN LIGNE mais que Polylang ne relie pas la paire : rien à retraduire,
    le geste est `scripts/repair_lien_polylang.py` (ajouté le 21/09, voir le commentaire
    du liage plus bas). La réservation de `img_lang` (dédup affiche) se fait ICI, sous verrou, AVANT
    tout travail — jamais après coup : sinon deux threads pourraient tous deux voir
    l'affiche « libre » avant que l'un des deux ne l'ait marquée prise."""
    from utils.api_limite import PlafondAPI
    try:
        return _translate_one_interne(ev, args, client, api_key, voix, wp_url,
                                      auth, img_lang, img_lang_lock)
    except PlafondAPI as exc:
        # Verdict DÉDIÉ : le lot doit distinguer « cette fiche a échoué » de « l'API
        # refuse tout le monde ». Le premier se compte, le second s'ARRÊTE — cf. main().
        log.error("[%s] PLAFOND API — rien publié, rien écrit : %s", ev["id"], exc)
        return "plafond"


def _translate_one_interne(ev, args, client, api_key, voix, wp_url,
                           auth, img_lang, img_lang_lock) -> str:
    # Langue RÉELLE = celle de l'article déjà rédigé s'il existe (jamais le seul
    # titre brut) : scripts.enrich écrit TOUJOURS en français par défaut, un titre
    # italien à la source peut donc déjà porter un article français. Sans ce
    # contrôle, on traduirait un article déjà français « vers » le français —
    # produisant un quasi-doublon au lieu d'une vraie traduction (constaté : id 4122).
    # PORTILLON DE COHÉRENCE DE LA DESCRIPTION — arbitrage de Franck, 2026-08-04 :
    # « je veux qu'il puisse juger la description, et ce, partout ».
    #
    # POURQUOI ICI ET AVANT TOUT. Le portillon C2, plus bas, compare le TITRE produit à
    # l'identité de l'original ; il ne regarde jamais la description, qui est précisément
    # le canal par lequel WP#6798 a été contaminé. On avait donc un filet posé APRÈS la
    # dépense, sur le seul symptôme, et une relecture humaine quotidienne pour compenser
    # le reste — un humain qui rattrape ce qu'un `if` sait voir.
    #
    # Or la contradiction de WP#6798 était détectable SANS IA : la fiche disait « Une
    # semaine pas plus · La Comédie des Alpes · Chambéry » et sa description parlait
    # d'Annecy et du lac. Aucun mot commun, une autre commune nommée. Rien à comprendre,
    # seulement à comparer (cf. utils/coherence).
    #
    # AVANT l'appel au LLM, et pas après : refuser une fois la traduction payée coûterait
    # l'appel pour rien, alors que la description source est connue dès le départ.
    #
    # Ce refus n'est PAS un état terminal : `translated_at` reste vide, la fiche se
    # represente au run suivant, et elle repartira d'elle-même le jour où sa description
    # est réparée (repair_polluted_descriptions, autocomplete, ou une nouvelle passe de
    # scraping). C'est la condition pour qu'un blocage soit acceptable ici.
    motif = incoherence_description(ev, bloquant=True)
    if motif:
        log.error("[%s] REFUS AVANT TRADUCTION — la description ne parle pas de cette "
                  "fiche : %s. Titre « %s » · %s, %s. Rien n'a été appelé ni publié.",
                  ev["id"], motif, (ev.get("title") or "")[:45],
                  (ev.get("lieu") or "—")[:28], (ev.get("ville") or "—")[:20])
        return "refus"

    src = effective_lang(ev)
    tgt = _target(src)
    img = ev.get("url_image") or ""
    if img and image_identifiante(img, ev.get("image_source"), img_lang):
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
    # PORTILLON DE LANGUE — trouvé le 2026-08-06 (WP#2174, « La Saint-Ours 2026 -
    # Rendez Vous en Vallée d'Aoste » publié comme fiche ITALIENNE avec un titre resté
    # en français, sa description ayant elle bien été traduite). AVANT l'article
    # (économise le second appel LLM quand le titre a déjà manifestement échoué) et
    # AVANT le portillon de justesse plus bas, qui compare l'IDENTITÉ du titre à
    # l'original mais ne vérifie jamais sa LANGUE — un titre recopié tel quel « partage »
    # trivialement tous ses mots avec l'original, donc passait ce contrôle-là sans
    # broncher. Même non-terminalité que les autres refus de cette fonction :
    # translated_at reste vide, la fiche se représente au run suivant.
    if titre_semble_intraduit(tr["title"], tgt, ev.get("title", "")):
        log.error("[%s] REFUS — le titre \"traduit\" est resté en %s (cible %s) : "
                  "« %s ». Rien n'a été publié.", ev["id"], src, tgt, tr["title"][:70])
        return "refus"
    # Second portillon, complémentaire — trouvé le 31/08 (voir docstring de la fonction) :
    # celui du dessus ne voit rien quand le titre a été RÉÉCRIT (pas recopié) mais dans
    # la mauvaise langue. 16 fiches en production dans ce cas, jamais interceptées.
    if titre_reecrit_mauvaise_langue(tr["title"], tgt, ev.get("title", "")):
        log.error("[%s] REFUS — le titre a été réécrit mais reste en %s (cible %s) : "
                  "« %s ». Rien n'a été publié.", ev["id"], src, tgt, tr["title"][:70])
        return "refus"
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

    # PORTILLON — l'original doit être PUBLIC sur WordPress au moment où on crée sa
    # traduction (incident WP#7286, 2026-08-06) : WP#6355 était à la corbeille depuis
    # deux jours, en attente d'une décision, quand le run du matin a quand même publié
    # son jumeau italien — un original absent avec une traduction bien visible.
    # Même asymétrie que le portillon de justesse au-dessus : le coût d'un faux refus
    # est un jour de retard (translated_at reste vide, nouvelle tentative au run
    # suivant, y compris si Franck restaure l'original entre-temps) ; le coût d'un
    # faux passage est une fiche orpheline en ligne, exactement l'incident ci-dessus.
    # Ne s'applique QUE si l'original a déjà un wp_post_id_as : un original jamais
    # publié est une autre situation, hors de ce qui a été cassé ici.
    orig_wp_id = ev.get("wp_post_id_as")
    if orig_wp_id and not wp_original_est_en_ligne(orig_wp_id):
        log.warning("[%s] REFUS — l'original WP#%s n'est plus 'publish' sur WordPress "
                   "(corbeille, dépublié, ou injoignable) : créer sa traduction "
                   "produirait un jumeau public d'un original absent. Rien n'a été "
                   "publié ; translated_at reste vide, nouvelle tentative au run "
                   "suivant.", ev["id"], orig_wp_id)
        return "refus"

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
            "enrich_status, date_source, llm_score_detail, url_officiel, home_score) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
             "copie-traduction",
             # MÊME OUBLI, MÊME FORME, découvert le 2026-08-03 : le détail du score par
             # critère n'était pas copié. Or c'est LUI, et non `llm_score`, dont dérive
             # `as_deplacement_now` (utils/deplacement.py). Les 14 fiches Savoie + Comté de
             # Nice traduites en italien avaient donc un score de déplacement VIDE, et la
             # section « Ça vaut le déplacement » italienne retombait sur `as_score` —
             # exactement le tri chronologique-par-défaut qu'on venait de quitter.
             # Copie et non recalcul : c'est le même événement, le re-noter coûterait un
             # appel LLM pour aboutir aux mêmes points. La justification reste en français,
             # ce qui ne gêne pas — seul `points` sert au tri.
             ev.get("llm_score_detail"),
             # TROISIÈME OUBLI DE LA MÊME FAMILLE, découvert le 2026-08-05. Sans cette
             # copie, `utils.radar.official_anchor()` ne trouve aucune ancre sur la
             # traduction : le verrou de publication la croit non résolue, et surtout
             # `publisher_as._source_publiable()` la publie SANS source officielle. La
             # jumelle italienne d'une fiche parfaitement sourcée affichait donc une page
             # muette — WP#2174 (Saint-Ours) montrait lasaintours.it en français et rien
             # en italien. Le contournement existait déjà côté verrou (l'argument `parent`
             # de publication_block_reason, qui remonte à l'original), preuve que l'oubli
             # était connu et compensé au lieu d'être corrigé à la source.
             # Copie et non re-résolution : c'est le même événement, la même page.
             ev.get("url_officiel"),
             # QUATRIÈME OUBLI DE LA MÊME FAMILLE, découvert le 2026-09-06 en creusant
             # pourquoi 36 fiches « à venir » n'avaient pas de home_score (audit_une.py) :
             # `enrich_data` traduit (tr_enrich, ci-dessus) contient bien `home.score`
             # (translate_article() part de `dict(data)`, seul `article` est réécrit), mais
             # la COLONNE home_score, elle, n'a jamais figuré dans cet INSERT. Or c'est la
             # colonne, pas le JSON, que lit `utils/une.py` (rendu = event.get("home_score"))
             # — la fiche traduite était donc structurellement invisible à « À la une »,
             # depuis la création de cette colonne. Copie et non recalcul, même raison que
             # les trois oublis ci-dessus : c'est le même événement, le renoter coûterait un
             # appel LLM pour retrouver les mêmes points.
             ev.get("home_score")))
        # Lie les deux fiches (Polylang) via l'endpoint.
        #
        # ET ON LIT SON VERDICT — corrigé le 2026-09-21. `_post_link` rend True/False
        # (il rend False sur toute erreur HTTP ou réseau) et personne ne le lisait :
        # `translated_at` partait à la ligne suivante quoi qu'il arrive. Après quoi plus
        # aucun script ne repassait — `translate_events` exclut la fiche (translated_at
        # posé, et la jumelle EXISTE donc `_rearme_traductions_orphelines` ne se
        # déclenche pas), `link_translations_as` exclut explicitement les paires dont
        # `translation_of` est renseigné, et `repair_lien_traduction` répare la COLONNE
        # en base, pas le lien WordPress. Un état terminal sans rouvreur (règle 3).
        #
        # MESURÉ CE JOUR-LÀ, depuis l'extérieur : sur 107 pages publiées au versant
        # français encore devant nous, 68 seulement portaient un `hreflang="it"` vers
        # leur jumelle. WP#8137 « Carla With Love » et WP#8175, sa traduction italienne
        # publiée une heure après, étaient toutes deux publiques, chacune du bon versant,
        # et la page française n'annonçait aucune version italienne.
        #
        # ⚠️ ET ON N'EFFACE PAS `translated_at` POUR AUTANT. C'est la fausse bonne idée :
        # la fiche repasserait dans la file du lendemain et une TROISIÈME page naîtrait,
        # alors que le texte italien est écrit, payé et EN LIGNE. Il ne manque qu'un
        # lien, et c'est `scripts/repair_lien_polylang.py` qui le repose (endpoint
        # idempotent). Le verdict remonte ici seulement pour être COMPTÉ : un défaut qui
        # ne sort pas dans le bilan se découvre des semaines plus tard (règle 6).
        lien_ok = False
        if all([wp_url, auth[0], auth[1]]):
            lien_ok = _post_link(wp_url, auth,
                                 {src: int(ev["wp_post_id_as"]), tgt: int(wp_id)})
        else:
            log.error("[%s] identifiants WordPress absents — la paire WP#%s/WP#%s est "
                      "publiée mais NON LIÉE.", ev["id"], ev["wp_post_id_as"], wp_id)
        conn.execute("UPDATE events_raw SET translated_at=? WHERE id=?",
                     (datetime.now().isoformat(timespec="seconds"), ev["id"]))
        conn.commit()
    finally:
        conn.close()
    if not lien_ok:
        log.error("[%s] traduit → WP#%s (%s) mais LIEN POLYLANG NON POSÉ : les deux pages "
                  "sont en ligne et le lecteur ne verra aucune traduction. Rien à "
                  "retraduire — reposer le lien : "
                  ".venv/bin/python -m scripts.repair_lien_polylang --ids %s --apply",
                  ev["id"], wp_id, tgt, ev["id"])
        return "lien_absent"
    log.info("[%s] traduit → WP#%s (%s), lié.", ev["id"], wp_id, tgt)
    return "done"


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Traduit les événements à bon score (FR↔IT).")
    parser.add_argument("--apply", action="store_true", help="Exécute (sinon simulation).")
    parser.add_argument("--min-score", type=int, default=6, help="Score minimum (défaut 6).")
    parser.add_argument("--cap", type=int, default=10, help="Nb max par run (défaut 10).")
    parser.add_argument("--include-past", action="store_true",
                        help="Inclut les événements TERMINÉS (par défaut ils sont écartés, "
                             "règle 5). Sortie de secours si l'on veut un jour compléter "
                             "l'archive : la file normale, elle, ne doit contenir que ce "
                             "qui sert encore à quelqu'un.")
    parser.add_argument("--territoire", default="",
                        help="Filtre territoire (slug : %s)." % ", ".join(_TERR_KEYS))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("ids", nargs="*", type=int,
                        help="Ids d'événements ORIGINAUX. Avec --retranslate : on RE-TRADUIT leur "
                             "jumeau existant. Sans : on ne traduit QUE ces fiches (première "
                             "traduction), sans plancher de score.")
    parser.add_argument("--retranslate", action="store_true",
                        help="RE-TRADUIT le jumeau EXISTANT des ids donnés (met à jour la fiche "
                             "traduite en place avec les règles courantes : article complet, voix, "
                             "toponymes) au lieu de créer une nouvelle traduction.")
    args = parser.parse_args(argv)

    # ── UN SEUL --apply À LA FOIS (2026-09-22) ──────────────────────────────────────────
    # Ce soir-là, deux `--apply` ont tourné EN MÊME TEMPS (PID 54609 et 57330). Chacun a
    # calculé sa file au démarrage, les deux files se recouvraient, et chaque fiche commune
    # a été traduite deux fois : 11 fiches italiennes en double publiées (WP#11010 à
    # 22:23:55, WP#11011 à 22:23:56, une seule liée par Polylang), corbeillées à la main.
    # `img_lang_lock`, plus bas, protège les THREADS d'un même run ; rien ne protégeait deux
    # PROCESSUS. Et le cron de 10:45 lance ce script : un lancement manuel à ce moment-là
    # recrée l'accident.
    #
    # Pris ICI, avant la sonde réseau et surtout avant la SÉLECTION : c'est la sélection
    # qui crée le recouvrement. Un verrou posé après elle laisserait deux runs calculer la
    # même file puis publier l'un après l'autre les mêmes fiches.
    #
    # `--retranslate` est couvert aussi : il réécrit des fiches en ligne, et deux runs
    # concurrents se disputeraient la même. La simulation, elle, reste libre — elle ne
    # publie ni ne marque rien (utils/verrou.exclusif_si).
    #
    # flock et non un fichier PID : le noyau relâche le verrou quand le processus meurt,
    # même au SIGKILL — aucun état garé qu'un humain devrait effacer (règle 3).
    # `_verrou` doit rester référencé jusqu'au `return` : c'est lui qui tient la place.
    _verrou = verrou.exclusif_si(args.apply, ROOT / "data" / "translate_events.lock")
    if _verrou is not None and not _verrou.obtenu:
        log.error("Une traduction --apply tourne DÉJÀ (%s) — celle-ci s'arrête sans rien "
                  "traduire ni publier, pour ne pas créer de doublons. Verrou : %s. "
                  "Attendre la fin de l'autre (ps -p <pid>) puis relancer.",
                  _verrou.detenteur or "détenteur inconnu", _verrou.chemin)
        return verrou.CODE_DEJA_EN_COURS

    # ── SONDE AVANT DÉPENSE (2026-08-18) ────────────────────────────────────────────────
    # `wp_original_est_en_ligne` refuse toute fiche quand le site est injoignable — bon
    # choix pour UNE fiche, mais ce contrôle a lieu APRÈS `translate_title_desc`. Pendant
    # la panne réseau du 18/08, chaque passage traduisait donc intégralement jusqu'à dix
    # fiches (deux appels chacune) avant de les refuser, tous les jours, pour une cause qui
    # ne bougeait pas. C'est le cul-de-sac de la règle 3, et il se paie en appels API.
    #
    # On demande donc d'abord « puis-je parler au site ? », une seule fois pour tout le
    # lot. Si non, rien n'est tenté : les fiches restent candidates et repasseront telles
    # quelles au retour du réseau — aucune n'est marquée, aucun état terminal n'est posé.
    if args.apply and not wp_site_joignable():
        log.error("Site injoignable depuis cette machine — AUCUNE traduction tentée, "
                  "AUCUN appel API dépensé. Les fiches restent candidates et repasseront "
                  "au prochain run une fois le site joignable. "
                  "(Ce n'est pas un refus éditorial : voir docs/PANNE_OVH_2026-08-18.md.)")
        return 0

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _ensure_cols(conn)

    # Index des affiches par langue (dédup : ne pas re-traduire un événement dont la
    # jumelle dans la langue cible existe déjà — même image = même événement bilingue).
    # effective_lang, PAS detect_lang sur le seul titre : sinon un événement au titre
    # italien mais à l'article déjà français se classe lui-même en « it » et se retrouve
    # à bloquer SA PROPRE traduction (sa propre image « existe déjà » côté it — lui).
    img_lang = index_affiches([dict(r) for r in conn.execute(
        "SELECT title, description, territoire, url_image, image_source, article_title, "
        "enrich_data FROM events_raw WHERE COALESCE(url_image,'')<>'' "
        "AND COALESCE(wp_post_id_as,0)>0 AND duplicate_of IS NULL")])

    terr_keys = None
    if args.territoire:
        terr_keys = _TERR_KEYS.get(args.territoire.strip().lower())
        if not terr_keys:
            log.error("Territoire inconnu : %s (attendus : %s)",
                      args.territoire, ", ".join(_TERR_KEYS))
            conn.close()
            return 2

    # AVANT la sélection, et pas après comme `_rearme_traductions` : une fiche dont la
    # jumelle a disparu doit repasser DÈS CE RUN. Rouvrir après la requête, c'est un jour
    # de retard par fiche — sur 63 fiches à venir constatées le 15/09, deux mois et demi.
    _rearme_traductions_orphelines(conn)

    # IDS DÉSIGNÉS (23/09/2026) : sans --retranslate, les ids donnés restreignent la file
    # à ces fiches, et le plancher de score ne s'applique pas — les avoir nommées EST la
    # décision. Mesuré ce soir-là : deux fiches piémontaises des Giornate (WP#10411 Alto
    # Forte di Gavi, WP#10964 Musei Reali) notées 5 n'avaient aucune version italienne, et
    # ne pouvaient en recevoir aucune : le plancher par défaut est 6, et les ids n'étaient
    # lus qu'en mode --retranslate. Toutes les autres gardes (en ligne, pas déjà traduit,
    # pas une traduction, pas terminé) restent en place.
    cibles = [] if args.retranslate else list(args.ids or [])
    plancher = 0 if cibles else args.min_score
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
        # RÈGLE 5, AJOUTÉE LE 2026-09-14 — cette file n'avait AUCUN filtre de date.
        #
        # Mesuré ce jour-là sur le site : 138 fiches publiées encore devant nous, dont
        # 110 SANS jumelle traduite (95 françaises qui attendent leur italienne). Or le
        # cron traduit 10 fiches par jour depuis des semaines : à ce rythme la file
        # aurait dû être vidée plusieurs fois. Elle ne l'est pas, parce qu'elle est
        # triée par SCORE et remplie d'événements TERMINÉS — le site compte environ
        # 155 fiches publiées passées, et une fiche passée garde son score.
        #
        # Traduire un événement fini ne sert personne : la fiche ne sera pas republiée,
        # plus aucun visiteur ne la cherche, et surtout elle consomme un des dix
        # créneaux du jour au détriment d'une fiche à venir. C'est le motif du dépôt
        # dans sa forme la plus coûteuse : le dispositif TOURNE, le journal se remplit,
        # et le vivier italien des événements à venir reste vide.
        #
        # Une fiche SANS DATE n'est pas du passé (donnée manquante, `dates.py` la
        # remplira peut-être demain) : elle reste candidate. Idem pour les récurrentes,
        # qui n'ont pas de date unique — `date_event_end` vide les couvre déjà ici.
        + ("" if args.include_past else
           "AND (COALESCE(date_event_end, date_event_start, '') = '' "
           "     OR COALESCE(date_event_end, date_event_start) >= ?) ") +
        "ORDER BY COALESCE(user_score, llm_score, 0) DESC, id ASC",
        ([plancher] if args.include_past
         else [plancher, date.today().isoformat()])).fetchall()]
    if cibles:
        rows, absents = cibler_ids(rows, cibles)
        for i in absents:
            log.warning("[%s] demandé mais pas candidat à une PREMIÈRE traduction (déjà "
                        "traduit, lui-même une traduction, pas en ligne ou terminé) — "
                        "pour réécrire une jumelle existante : --retranslate %s", i, i)
    if terr_keys:                                       # filtre territoire AVANT le plafond
        rows = [r for r in rows if any(k in _norm(r.get("territoire", "")) for k in terr_keys)]

    # ÉCARTER LES DESCRIPTIONS INCOHÉRENTES **AVANT** LE PLAFOND — et c'est tout l'objet de
    # ce bloc, ajouté le 2026-08-04 quelques heures après le portillon lui-même.
    #
    # LE CUL-DE-SAC QU'IL FERME, démontré sur base jetable par la revue du jour : le refus
    # posé dans `_translate_one` arrive APRÈS la sélection, donc la fiche refusée a déjà
    # consommé un créneau de `--cap`. Elle n'est marquée nulle part (`translated_at` reste
    # vide — c'est voulu, pour qu'elle reparte quand elle sera réparée), donc elle revient
    # le lendemain. Et elle revient EN TÊTE, parce que la file est triée par score et que
    # la pollution FAIT MONTER le score : c'est précisément le mécanisme de WP#6798, où une
    # description d'Annecy a valu 10 à un spectacle de Chambéry.
    #
    # Résultat mesuré : trois fiches polluées suffisent à saturer `--cap 3` indéfiniment,
    # et aucune fiche saine n'est jamais atteinte. La traduction paraît tourner — le cron
    # passe, le journal se remplit de refus — pendant que le vivier italien reste vide.
    # C'est la troisième forme du motif du dépôt : non pas « personne ne rouvre », ni
    # « personne ne recalcule », mais **un refus qui ne marque rien revient occuper la
    # place**.
    #
    # Filtrer ici plutôt que refuser plus bas ne relâche AUCUNE garde : le portillon de
    # `_translate_one` reste en place comme seconde ceinture. Il change seulement qui paie
    # le refus — la fiche polluée au lieu de la file entière.
    # LES ROUVREURS D'ABORD : une fiche dont la matière a changé depuis son dernier refus
    # redevient candidate avant même la sélection du jour.
    _rearme_traductions(conn)
    rows_avant_garage = len(rows)
    rows, rows_garees = garees(rows)
    if rows_garees:
        # LES NOMMER, jamais les faire disparaître : une file qui rétrécit sans le dire est
        # le défaut que ce dépôt corrige depuis le 11/08. Ces fiches ne repartiront que si
        # leur matière change — c'est écrit, et c'est vérifiable.
        log.warning("%d fiche(s) garée(s) après %d refus sur une matière inchangée "
                    "(elles ne consomment plus ni créneau ni appel API ; elles repartent "
                    "dès que leur matière change) : %s", len(rows_garees), MAX_REFUS,
                    ", ".join(f"[{r['id']}] {(r.get('title') or '')[:34]}"
                              for r in rows_garees[:8]))
    ecartees = [r for r in rows if incoherence_description(r, bloquant=True)]
    if ecartees:
        rows = [r for r in rows if r not in ecartees]
        log.warning("%d fiche(s) écartée(s) AVANT le plafond — description incohérente "
                    "avec la fiche : %s", len(ecartees),
                    ", ".join(f"[{r['id']}] {(r.get('title') or '')[:34]}"
                              for r in ecartees[:8]))
        # Les NOMMER, sinon on répare une file bloquée en fabriquant un silence : ces
        # fiches ne seront jamais traduites tant que leur description n'est pas réparée
        # (repair_polluted_descriptions, autocomplete, ou un nouveau passage de scraping),
        # et rien d'autre ne les compte. `scripts/audit_coherence` en tient le registre.
        #
        # ⚠️ CE RENVOI ÉTAIT FAUX JUSQU'AU 2026-08-13, et il l'était depuis le premier
        # jour. `repair_polluted_descriptions` ne sélectionnait pas sur CE motif-ci mais
        # sur `motif_pollution` — « description sans substance ». Une description longue
        # et riche qui raconte un AUTRE événement (le cas exact de WP#6798) n'y entrait
        # pas : le rouvreur nommé ici répondait à une autre question que le portillon.
        # [4420] [3739] [4576] ont été écartées à l'identique tous les jours du 05/08 au
        # 13/08 sans que rien ne les reprenne. Le script sélectionne désormais AUSSI sur
        # `incoherence_description` — la fonction même qu'on appelle deux lignes plus
        # haut, donc la même question des deux côtés — et il NOMME celles qu'il ne peut
        # pas réparer (page non re-téléchargeable), qui restent à trancher à la main.
        # Leçon générale, écrite dans docs/ETATS_TERMINAUX.md : nommer un rouvreur ne
        # ferme rien tant qu'on n'a pas vérifié qu'il sélectionne sur le MÊME critère.
    rows = rows[:args.cap]
    # Le périmètre écrit à côté du nombre DOIT être celui qui a servi (règle 6) : le
    # 24/09 à 0h10, ce message annonçait « score ≥ 6 » pour trois fiches notées 5 et 8,
    # choisies par leurs ids sans plancher.
    log.info("%d événement(s) candidat(s) (%s, en ligne, non traduits%s)",
             len(rows), f"ids demandés : {' '.join(map(str, cibles))}, sans plancher de score"
             if cibles else f"score ≥ {args.min_score}",
             ", territoire=" + args.territoire if args.territoire else "")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key) if (api_key and args.apply) else None
    voix = voix_block()  # règles éditoriales (bilingues via le lexique) injectées à la traduction
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))

    # 2026-09-08 : la connexion se fermait ICI, avant la boucle — et `marquer_refus`
    # (plus bas, en --apply) écrivait dans une connexion fermée : `Cannot operate on a
    # closed database`, constaté en production sur le refus de la fiche 3797. Le lot avait
    # traduit, mais le compteur de refus n'était pas écrit, donc les refus se rejouaient à
    # l'identique le lendemain (règle 3). La connexion se ferme désormais après le marquage.
    if args.retranslate:
        conn.close()
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
    plafonne = False          # défini hors du `if rows` : le bilan le lit toujours
    if rows:
        # SOUMISSION PAR PETITS TRAINS (taille = workers) et non tout d'un coup : c'est ce
        # qui permet d'ARRÊTER au premier plafond. Avec une soumission en bloc, les 10
        # workers seraient déjà lancés quand le premier verdict « plafond » revient — on
        # aurait 10 refus au lieu d'un, exactement le martèlement qu'on corrige (13 puis
        # 15 occurrences dans les journaux des 30 et 31/07).
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="translate") as ex:
            for i in range(0, len(rows), workers):
                if plafonne:
                    break
                train = rows[i:i + workers]
                futures = [ex.submit(_translate_one, ev, args, client, api_key, voix,
                                     wp_url, auth, img_lang, img_lang_lock) for ev in train]
                for fut in futures:
                    try:
                        results.append(fut.result())
                    except Exception as exc:  # noqa: BLE001 — un worker ne doit jamais planter le lot
                        log.warning("worker en échec (exception non gérée) : %s", exc)
                        results.append("error")
                if "plafond" in results:
                    plafonne = True
        if plafonne:
            restantes = len(rows) - len(results)
            log.error("=== PLAFOND API : lot interrompu, %d fiche(s) non tentée(s) — se "
                      "lève dans la console Anthropic, les fiches se representeront "
                      "d'elles-mêmes ===", restantes)

    done, skipped, errors = results.count("done"), results.count("skip"), results.count("error")
    # PUBLIÉE MAIS NON LIÉE — compté à part, et JAMAIS dans `done`. La traduction est en
    # ligne, donc ce n'est pas une erreur ; le lecteur ne la voit pas, donc ce n'est pas
    # un succès. Deux compteurs qui portent le même nom et comptent deux choses se
    # contredisent un jour, et c'est le plus gros qu'on croira (règle 6).
    sans_lien = [rows[i] for i, v in enumerate(results) if v == "lien_absent"]
    # `results` est rempli dans l'ORDRE de soumission des futures, donc dans l'ordre de
    # `rows` : on peut renommer les refus sans plomberie supplémentaire.
    refus = [rows[i] for i, v in enumerate(results) if v == "refus"]
    # COMPTER LE REFUS, sinon il se rejoue à l'identique demain (règle 3). On ne marque
    # qu'en --apply : une simulation ne doit pas garer une fiche.
    if args.apply:
        for ev in refus:
            marquer_refus(conn, ev)
    conn.close()
    log.info("=== Traduction terminée : %d traduit(s) et lié(s), %d publiée(s) SANS LIEN, "
             "%d ignoré(s), %d refusé(s)%s ===", done, len(sans_lien), skipped, len(refus),
             "" if args.apply else "  (simulation : rien écrit)")
    if args.apply:
        # Rapport uniquement quand on a vraiment agi (une simulation quotidienne en cron
        # inonderait Slack pour rien) — cf. utils.pipeline_status pour le lot quotidien.
        from utils import slack
        from utils import pipeline_status
        msg = (f"🌍 *Traduction quotidienne* — {done} traduit(s) sur {len(rows)} "
               f"candidat(s), {skipped} ignoré(s)")
        if plafonne:
            # La cause était connue du script et ne sortait que dans le journal.
            msg = bandeau_plafond(len(rows) - len(results)) + msg
        if rows_garees:
            # RÈGLE 6 : un état qui sort une fiche de la file la sort aussi des bilans.
            # On le compte explicitement, sinon on le découvre des semaines plus tard.
            msg += (f"\n🅿️ {len(rows_garees)} fiche(s) garée(s) après {MAX_REFUS} refus "
                    f"sur une matière inchangée (sur {rows_avant_garage} candidates) — "
                    f"elles ne brûlent plus d'appels et repartent dès que leur matière "
                    f"change : "
                    + " · ".join(f"[{e['id']}] « {(e.get('title') or '')[:32]} »"
                                 for e in rows_garees[:4]))
        if errors:
            msg += f", {errors} erreur(s)"
        if refus:
            # NOMMER les refus, sinon le portillon bloque en silence : c'est exactement le
            # reproche fait aux contrôles qui « se déclarent ok ». Un refus demande une
            # décision humaine (réparer la description de l'original, ou constater un faux
            # positif) — et tant qu'il dure, cet original occupe un créneau de --cap.
            msg += (f"\n⛔ {len(refus)} refusée(s) — titre traduit incohérent avec "
                    f"l'original, RIEN publié : "
                    + " · ".join(f"id {e['id']} « {(e.get('title') or '')[:40]} »"
                                 for e in refus[:5]))
        if sans_lien:
            # LE DÉFAUT QUE FRANCK A VU LE 21/09 : « pourquoi j'ai des articles sans
            # traduction ? ». La paire était publiée des deux côtés et Polylang ne les
            # reliait pas — invisible dans tous les compteurs, qui demandent tous « une
            # jumelle existe-t-elle ? » et jamais « sont-elles reliées ? ». Il sort
            # désormais le jour même, avec son geste, qui ne coûte aucun appel LLM.
            msg += (f"\n🔗 {len(sans_lien)} traduction(s) EN LIGNE mais NON LIÉE(S) — le "
                    f"lecteur ne verra aucune version italienne ; rien à retraduire, le "
                    f"texte existe. Reposer le lien : "
                    f"`.venv/bin/python -m scripts.repair_lien_polylang --ids "
                    + " ".join(str(e["id"]) for e in sans_lien[:8]) + " --apply` : "
                    + " · ".join(f"id {e['id']} « {(e.get('title') or '')[:34]} »"
                                 for e in sans_lien[:5]))
        slack.notify(msg)
        # Les refus comptent en `warn` et non en `error` : rien n'a cassé, un garde-fou a
        # tenu — mais ils demandent une décision humaine, ils ne doivent pas disparaître.
        # Le plafond compte comme une ERREUR de run : `watchdog_crons` lit `error_count`
        # et ne regarde que ça pour distinguer « a tourné » de « a tourné et échoué ».
        # Sans cette ligne, cinq jours d'arrêt complet se sont enregistrés comme cinq runs
        # parfaitement sains.
        # Les paires non liées comptent en `warn` avec les refus, et pas en `ok` : la
        # page italienne est en ligne, mais aucun lecteur n'y accède depuis la française.
        # Les compter en succès, c'est exactement le compteur qui ferme la question au
        # lieu de l'ouvrir (règle 6).
        pipeline_status.record_run("translate_events", ok=done,
                                   warn=skipped + len(refus) + len(sans_lien),
                                   error=errors + (1 if plafonne else 0), summary=msg[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
