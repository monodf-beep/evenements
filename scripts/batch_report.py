#!/usr/bin/env python3
"""Rapport de complétude ET DE JUSTESSE d'un LOT d'événements — le « portillon » entre
les étapes du protocole par lot (cf. docs/BACKLOG.md, journal 2026-07-31 : Franck refuse
le rattrapage au compte-gouttes qui répare un aspect — l'image — sans vérifier le reste :
score, rédaction, panel lecteurs, placement home).

Ne modifie RIEN. Pour chaque id demandé, affiche l'état RÉEL de chaque étage du
pipeline et un verdict COMPLET/INCOMPLET — pour décider si un lot est prêt à publier
(après enrich.py) ou prêt à clore (après publish_batch_as.py), au lieu de supposer que
"0 échec" au log veut dire "tout est fait".

DEUX FAMILLES DE CONTRÔLES, et il a fallu les quatre bugs du 2026-08-01 pour comprendre
qu'une seule ne suffisait pas :

1. COMPLÉTUDE — « la case est-elle remplie ? » : score, article, panel lecteurs, date
   ISO, image réelle. C'est le contrôle historique.
2. JUSTESSE — « ce qui est rempli est-il VRAI ? ». Les quatre bugs du 2026-08-01 ont
   TOUS franchi le portillon en se déclarant « ok », parce qu'ils produisaient du
   contenu complet mais faux :
     • fiche IT publiée « Festa del Lago 2026 » alors qu'elle décrit un spectacle à
       La Comédie des Alpes, Chambéry (description polluée par une fusion à tort) ;
     • dates de traductions fausses de plusieurs semaines (Jazz Art 2 mois, Matisse
       1 mois — dates.py re-parsait le texte italien au lieu de copier l'original) ;
     • description réelle remplacée par un lien Google News sans contenu ;
     • articles de presse publiés comme s'ils étaient des événements.
   Chaque contrôle de justesse indique en commentaire QUEL bug réel il aurait attrapé.

Bloquant (✗) vs avertissement (⚠) : un ✗ met `complet=False` et EMPÊCHE la publication
(scripts/daily_batch.py filtre sur ce booléen). On ne réserve donc le ✗ qu'aux
anomalies CERTAINES (contradiction factuelle, coquille vide) ; tout ce qui repose sur
une heuristique de langue (cohérence lexicale d'un titre, lieu traduit) reste en ⚠ :
un faux positif récurrent ferait ignorer l'alerte — et, pire, bloquerait en silence
des fiches parfaitement saines.

Usage (VPS) :
    .venv/bin/python -m scripts.batch_report 834 840 843 1155 1447 2128 3506 3512
"""
from __future__ import annotations
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.eventness import non_event_reason
# Réutilisés TELS QUELS depuis dedupe : une seule définition dans le dépôt de ce qu'est
# un « token significatif » et une « longueur de texte visible ». Les redéfinir ici,
# c'est se condamner à ce que les deux versions divergent — or c'est précisément la
# divergence entre volume BRUT et substance VISIBLE qui a causé le bug de fusion.
from scripts.dedupe import _sig_tokens, _text_len

log = get_logger("batch_report")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

LONG_MIN_SCORE = int(os.getenv("ENRICH_LONG_MIN_SCORE", "7"))

# Description « coquille vide » : texte visible quasi nul alors que le brut est long.
# Calibré sur le cas réel (item Google News RSS = un seul <a href> dont l'URL encodée
# pèse des centaines de caractères pour ~28 caractères de texte visible, cf.
# dedupe._text_len). Les deux seuils DOIVENT être franchis ensemble : une description
# courte mais honnête (brut ≈ visible) n'est pas une coquille vide, juste laconique.
# Même signature que scripts/repair_polluted_descriptions.motif_pollution (120/200) ;
# on est volontairement PLUS STRICT sur le brut ici (300), parce que ce contrôle-ci
# BLOQUE une publication au lieu de proposer une réparation : une description faite
# d'un titre et d'un lien (~200 car. bruts) ne doit pas coûter une fiche saine.
DESC_VISIBLE_MIN = int(os.getenv("REPORT_DESC_VISIBLE_MIN", "120"))
DESC_BRUT_MIN = int(os.getenv("REPORT_DESC_BRUT_MIN", "300"))


def _panel(enrich_data: str) -> dict:
    try:
        data = json.loads(enrich_data or "") or {}
    except (ValueError, TypeError):
        return {}
    return data.get("reader_panel") or {}


def _titre_publie(r: dict) -> str:
    """Le titre qui part RÉELLEMENT sur WordPress, dans l'ordre de repli exact de
    scripts/publisher.build_post : article_title, puis enrich_data.article.titre, puis
    le titre brut de l'événement. On contrôle ce qui sera EN LIGNE, pas un champ voisin
    (WP#6798 s'affichait « Festa del Lago 2026 » via ce champ-là)."""
    titre = (r.get("article_title") or "").strip()
    if titre:
        return titre
    try:
        data = json.loads(r.get("enrich_data") or "") or {}
    except (ValueError, TypeError):
        return ""
    return ((data.get("article") or {}).get("titre") or "").strip()


def _meme_racine(a: str, b: str) -> bool:
    """Deux tokens désignent-ils le même mot ? Égalité, ou même préfixe de 5 lettres
    (tolère pluriels et dérivations : « spettacolo »/« spettacoli », « chambery »/
    « chamberien »). Tolérance VOLONTAIREMENT généreuse : chaque rapprochement admis
    en plus est une alerte de moins, et on préfère rater un cas douteux."""
    if a == b:
        return True
    if a.isdigit() or b.isdigit():
        return False           # une année ne se rapproche jamais par préfixe (2025/2026)
    return len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5]


def _partagent_un_mot(a: set[str], b: set[str]) -> bool:
    return any(_meme_racine(x, y) for x in a for y in b)


def _jour_iso(valeur) -> str:
    """Jour (AAAA-MM-JJ) d'une date stockée, ou '' si illisible. On compare des JOURS et
    pas des chaînes : « 2026-08-12 » et « 2026-08-12T21:00 » désignent la même date, un
    écart de format ne doit pas passer pour une incohérence."""
    s = str(valeur or "").strip()
    return s[:10] if re.match(r"\d{4}-\d{2}-\d{2}", s) else ""


def _charge_original(oid: int) -> dict | None:
    """Ligne de l'événement ORIGINAL d'une traduction, lue en base EN LECTURE SEULE.

    _row_report ne reçoit qu'une ligne isolée : sans cette lecture, aucune traduction ne
    pourrait être comparée à son original. On la fait ici plutôt que d'imposer le travail
    à chaque appelant — daily_batch.py appelle `_row_report(ev)` avec un seul argument et
    doit continuer de fonctionner tel quel. Toute erreur d'accès est avalée : le contrôle
    se dégrade alors en « non vérifiée », il ne casse jamais le rapport."""
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM events_raw WHERE id=?", (int(oid),)).fetchone()
        conn.close()
        return dict(row) if row else None
    except (sqlite3.Error, ValueError, TypeError):
        return None


def _row_report(r: dict, original: dict | None = None) -> tuple[bool, list[str]]:
    """(complet, lignes de détail) pour un événement.

    `original` : la ligne de l'événement D'ORIGINE quand `r` est une TRADUCTION
    (colonne translation_of). Facultatif — non fourni, il est lu en base. Le paramètre
    reste optionnel pour ne casser aucun appelant existant : daily_batch.py appelle
    `_row_report(ev)` avec un seul argument et filtre sur le booléen renvoyé.
    """
    ok = True
    lines = []

    score = r.get("llm_score")
    if score is None:
        ok = False
        lines.append("  ✗ score        : ABSENT (jamais enrichi)")
    else:
        lines.append(f"  · score        : {score} "
                     f"({'long' if int(score) >= LONG_MIN_SCORE else 'court'} attendu)")

    words = len((r.get("article_md") or "").split())
    # Plancher ABSOLU (20 mots) : attrape aussi un article « techniquement non vide »
    # mais réduit à peu près au titre (matière trouvée insuffisante malgré la matière
    # dite « officielle » — cas vécu id 843 : page officielle non pertinente détectée
    # trop tard, article réduit à 6 mots). Le seuil RELATIF (< 250 mots) ne s'applique
    # qu'aux événements qui visaient un article long (score élevé) — un article court
    # (catalogue) n'a pas vocation à être long.
    if words < 20:
        ok = False
        lines.append(f"  ✗ article      : {'VIDE' if words == 0 else f'{words} mots — quasi-vide'}")
    else:
        expect_long = (score or 0) >= LONG_MIN_SCORE
        thin = expect_long and words < 250
        marker = "⚠" if thin else "·"
        lines.append(f"  {marker} article      : {words} mots"
                     + (" (COURT alors que le score visait un long)" if thin else ""))

    # Panel lecteurs : seulement attendu pour un palier LONG (score ≥ LONG_MIN_SCORE) —
    # un événement court/catalogue ne passe JAMAIS par le panel (cf. enrich.py, appelé
    # seulement `if not court`). L'exiger pour un événement court serait un faux négatif.
    panel = _panel(r.get("enrich_data") or "")
    expect_panel = (score or 0) >= LONG_MIN_SCORE
    if expect_panel and not panel:
        ok = False
        lines.append("  ✗ panel lecteurs : jamais passé (attendu, score ≥ seuil long)")
    elif panel:
        lines.append(f"  · panel lecteurs : verdict={panel.get('verdict', '?')} "
                     f"mean={panel.get('mean', '?')} votes={panel.get('votes', '?')}")
    else:
        lines.append("  · panel lecteurs : — (non attendu, palier court)")

    home_score = r.get("home_score")
    lines.append(f"  · home_score   : {home_score if home_score is not None else '— (non calculé)'}"
                 f"  override={r.get('home_override') or '—'}")

    # Date ISO exploitable : sans elle, cs-publish.php (TEC) date l'événement du JOUR DE
    # LA PUBLICATION au lieu de sa vraie date (constaté sur l'id 3512, 2026-08-01 — la
    # fiche est partie "COMPLET" sur tout le reste mais sans date exploitable).
    if not (r.get("date_event_start") or "").strip():
        ok = False
        lines.append("  ✗ date         : AUCUNE date ISO exploitable "
                     "(TEC affichera la date du jour de publication)")
    else:
        lines.append(f"  · date         : {r.get('date_event_start')} → "
                     f"{r.get('date_event_end') or r.get('date_event_start')}")

    # ----------------------------------------------------------------- #
    # CONTRÔLES DE JUSTESSE — « ce qui est rempli est-il VRAI ? »
    # (les quatre bugs du 2026-08-01 passaient tous les contrôles ci-dessus)
    # ----------------------------------------------------------------- #

    # 1. SUBSTANCE DE LA DESCRIPTION — bug « description remplacée par un lien Google
    # News sans contenu ». merge_group choisissait autrefois la description la plus
    # LONGUE du groupe de doublons : un item Google News RSS (un <a href> dont l'URL
    # encodée pèse des centaines de caractères pour zéro mot) écrasait donc la vraie
    # description, y compris sur des fusions parfaitement correctes. Ensuite enrich.py
    # rédige à partir de cette matière → article écrit sur le mauvais sujet.
    # BLOQUANT : le diagnostic est certain et purement mécanique (texte visible quasi
    # nul MAIS brut long = du balisage et une URL, rien d'autre) ; aucune interprétation
    # de langue n'intervient. Et une fiche sans la moindre matière n'a rien à faire en
    # ligne. Une description courte mais honnête (brut ≈ visible) ne déclenche que ⚠.
    desc = r.get("description") or ""
    brut, visible = len(desc.strip()), _text_len(desc)
    gnews = "news.google.com" in desc
    if visible < DESC_VISIBLE_MIN and brut >= DESC_BRUT_MIN:
        ok = False
        lines.append(f"  ✗ description  : COQUILLE VIDE — {visible} car. de texte visible "
                     f"pour {brut} car. bruts"
                     + (" (lien Google News)" if gnews else " (balisage/URL sans contenu)"))
    elif gnews:
        # Lien Google News DANS une description par ailleurs fournie : pas une coquille
        # vide, mais la signature d'une fusion de doublons — à relire avant publication.
        lines.append(f"  ⚠ description  : contient un lien Google News "
                     f"({visible} car. visibles) — vérifier qu'elle décrit bien CET événement")
    elif visible < DESC_VISIBLE_MIN:
        lines.append(f"  ⚠ description  : très courte ({visible} car. visibles) — "
                     f"matière de rédaction maigre")
    else:
        lines.append(f"  · description  : {visible} car. de texte visible")

    # 2. NON-ÉVÉNEMENT — bug « articles de presse publiés comme des événements »
    # (compte-rendu institutionnel, logistique « où se garer », anniversaire d'attentat).
    # Le même garde-fou tourne déjà dans evaluator.py et enrich.py ; s'il déclenche ICI,
    # c'est que la fiche l'a contourné : enrichissement forcé par id (les ids explicites
    # court-circuitent le pré-filtre) ou description remplacée APRÈS l'évaluation par une
    # fusion de doublons.
    #
    # AVERTISSEMENT ET NON BLOQUANT — arbitrage revu le 2026-08-02 après un test sur un cas
    # réel : « Tour de l'Avenir 2026 - Strambino » (course cycliste, WP#6380, DÉJÀ EN LIGNE)
    # déclenche le motif « voirie / mobilité », parce qu'une course annonce légitimement des
    # fermetures de routes et un plan de circulation. Bloquer aurait retenu un événement
    # sain. L'argument « ces fiches sont déjà rejetées en amont » ne protège pas : cette
    # fiche-là est publiée, donc elle a franchi evaluator ET enrich sans être rejetée.
    # `utils/eventness` a été calibré comme PRÉ-FILTRE sur des articles de presse scrapés,
    # pas comme portillon de publication sur des fiches déjà rédigées et validées — les deux
    # populations n'ont pas le même profil et le seuil de précision requis n'est pas le même.
    raison = non_event_reason(r.get("title") or "", desc)
    if raison:
        lines.append(f"  ⚠ nature       : ressemble à un non-événement — {raison}")

    # 3. COHÉRENCE TITRE ↔ CONTENU — bug « Festa del Lago 2026 » (WP#6798) : titre publié
    # parlant d'une fête à Annecy sur une fiche dont le lieu est La Comédie des Alpes à
    # Chambéry. On exige que le titre RÉELLEMENT publié partage au moins un mot
    # significatif avec l'ancrage FACTUEL de la fiche (titre d'origine, lieu, ville,
    # organisateur). On ne compare SURTOUT PAS au corps de l'article ni à la description :
    # dans ce bug, c'est justement la matière rédactionnelle qui était contaminée — elle
    # aurait confirmé le faux titre.
    # AVERTISSEMENT SEULEMENT : un titre journalistique légitime peut être reformulé sans
    # reprendre un seul mot de la fiche (« Le huis clos qui fait rire la Savoie »). Bloquer
    # là-dessus empêcherait de publier des fiches saines et, à force de fausses alertes,
    # l'alerte finirait ignorée. On reste conservateur : partage d'un mot par racine
    # (préfixe 5) et abstention dès que l'un des deux côtés est trop pauvre pour juger.
    titre_pub = _titre_publie(r)
    toks_titre = _sig_tokens(titre_pub)
    toks_ancrage = (_sig_tokens(r.get("title") or "") | _sig_tokens(r.get("lieu") or "")
                    | _sig_tokens(r.get("ville") or "") | _sig_tokens(r.get("organisateur") or ""))
    if len(toks_titre) >= 2 and len(toks_ancrage) >= 2:
        if _partagent_un_mot(toks_titre, toks_ancrage):
            lines.append(f"  · titre publié : « {titre_pub[:70]} » (cohérent avec la fiche)")
        else:
            lines.append(f"  ⚠ titre publié : « {titre_pub[:70]} » — AUCUN mot commun avec "
                         f"le titre/lieu/ville/organisateur de la fiche "
                         f"(« {(r.get('title') or '')[:40]} » · "
                         f"{(r.get('lieu') or '—')[:30]}, {(r.get('ville') or '—')[:20]}) "
                         f"— contamination possible, à relire")
    elif titre_pub:
        # Trop peu de mots significatifs d'un côté ou de l'autre : on s'abstient, une
        # alerte sur un titre de deux mots serait du bruit.
        lines.append(f"  · titre publié : « {titre_pub[:70]} » (trop court pour être recoupé)")

    # 4. COHÉRENCE D'UNE TRADUCTION AVEC SON ORIGINAL — bug « dates fausses de plusieurs
    # semaines » (Jazz Art 2 mois, Matisse 1 mois) : translate_events.py COPIE les dates
    # et le lieu de l'original, mais dates.py repassait derrière et re-parsait le texte
    # ITALIEN avec un parseur français, écrasant la copie. Une traduction n'a donc aucune
    # donnée factuelle propre : toute divergence avec l'original est une corruption.
    tof = r.get("translation_of") or 0
    if tof:
        orig = original if original is not None else _charge_original(tof)
        if not orig:
            lines.append(f"  ⚠ traduction   : original id={tof} INTROUVABLE — "
                         f"cohérence dates/lieu non vérifiable")
        else:
            lines.append(f"  · traduction   : de l'id {tof} "
                         f"(langue={r.get('translated_lang') or '?'})")
            # DATES — BLOQUANT quand les deux côtés sont renseignés et diffèrent : c'est
            # une contradiction factuelle certaine, sans interprétation possible, et
            # publier une date fausse est exactement le dommage constaté en ligne.
            for champ, libelle in (("date_event_start", "début"), ("date_event_end", "fin")):
                a, b = _jour_iso(r.get(champ)), _jour_iso(orig.get(champ))
                if a and b and a != b:
                    ok = False
                    lines.append(f"  ✗ date {libelle:<8}: {a} ≠ {b} chez l'original "
                                 f"(la traduction doit COPIER les dates, jamais les dériver)")
                elif bool(a) != bool(b):
                    # Un seul des deux côtés a la date : désynchronisation (l'original a
                    # été redaté après coup, ou la passe de datation a vidé la copie).
                    # ⚠ seulement : rien ne prouve laquelle des deux fiches a raison, et
                    # une date de FIN absente est bénigne (repli sur la date de début).
                    lines.append(f"  ⚠ date {libelle:<8}: « {a or '—'} » côté traduction vs "
                                 f"« {b or '—'} » côté original — désynchronisées")
            # LIEU / VILLE — AVERTISSEMENT SEULEMENT : le lieu est copié tel quel à
            # l'insertion, mais un toponyme peut légitimement être traduit (Turin/Torino,
            # Aoste/Aosta) ou reformulé, et aucune comparaison lexicale ne distingue de
            # façon fiable un exonyme d'une contamination. Bloquer produirait des faux
            # positifs sur des traductions correctes.
            for champ, libelle in (("lieu", "lieu"), ("ville", "ville")):
                a, b = (r.get(champ) or "").strip(), (orig.get(champ) or "").strip()
                ta, tb = _sig_tokens(a), _sig_tokens(b)
                if ta and tb and not _partagent_un_mot(ta, tb):
                    lines.append(f"  ⚠ {libelle:<13}: « {a[:35]} » vs « {b[:35]} » chez "
                                 f"l'original — aucun mot commun (exonyme ou contamination ?)")

    wp_id = r.get("wp_post_id_as")
    if not wp_id:
        lines.append("  · publication AS : PAS ENCORE publié")
    else:
        img_src = r.get("image_source") or "?"
        # `and img_src != ""` figurait ici : condition MORTE (le `or "?"` ci-dessus rend
        # la chaîne vide impossible). La seule question qui vaille est « y a-t-il une
        # image ? » — `image_source` dit d'OÙ elle vient, pas si elle existe, et 'banner'
        # (notre visuel de repli territorial) est une image parfaitement légitime.
        real_img = bool((r.get("url_image") or "").strip())
        lines.append(f"  · publication AS : WP#{wp_id} · image_source={img_src}"
                     f" ({'ok, vraie image' if real_img else 'AUCUNE image'})")
        if not real_img:
            ok = False

    return ok, lines


def main(argv: list[str]) -> int:
    ids = [int(a) for a in argv if a.isdigit()]
    if not ids:
        print("Usage : batch_report <id> [<id> ...]")
        return 1

    load_dotenv(ROOT / ".env")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ph = ",".join("?" * len(ids))
    rows = {r["id"]: dict(r) for r in
            conn.execute(f"SELECT * FROM events_raw WHERE id IN ({ph})", ids).fetchall()}
    # Originaux des traductions du lot, lus en UNE fois (contrôle de cohérence dates/lieu).
    orig_ids = sorted({int(r["translation_of"]) for r in rows.values() if r.get("translation_of")})
    originaux = {}
    if orig_ids:
        ph2 = ",".join("?" * len(orig_ids))
        originaux = {r["id"]: dict(r) for r in
                     conn.execute(f"SELECT * FROM events_raw WHERE id IN ({ph2})",
                                  orig_ids).fetchall()}
    conn.close()

    n_complete = 0
    n_avert = 0
    for i in ids:
        r = rows.get(i)
        print(f"\n[{i}] {(r.get('title') if r else None) or '— INTROUVABLE EN BASE —'}")
        if not r:
            continue
        complete, lines = _row_report(r, originaux.get(int(r.get("translation_of") or 0)))
        for line in lines:
            print(line)
        avert = [l for l in lines if l.lstrip().startswith("⚠")]
        n_avert += bool(avert)
        print(f"  => {'COMPLET' if complete else 'INCOMPLET'}"
              + (f" · {len(avert)} point(s) à vérifier" if avert else ""))
        n_complete += complete

    print(f"\n=== Lot : {n_complete}/{len(ids)} complet(s) "
          f"(score + article + panel + date + image réelle + justesse : description, "
          f"nature, dates de traduction) ===")
    if n_avert:
        print(f"=== {n_avert} fiche(s) avec au moins un ⚠ à VÉRIFIER À LA MAIN "
              f"(non bloquant : titre publié, lieu traduit, description maigre) ===")
    return 0 if n_complete == len(ids) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
