#!/usr/bin/env python3
"""La paire FR/IT existe, elle est du bon versant — mais Polylang ne les relie pas.

D'OÙ ÇA VIENT — 2026-09-21. Franck : « pourquoi j'ai des articles sans traduction ?
comment c'est possible ? on a pas un garde-fou pour ça ? »

Mesuré le jour même, depuis l'extérieur, sur les 182 fiches publiées non terminées :
107 pages au versant français, dont **68 seulement** portent un `hreflang="it"` vers
leur jumelle. 39 n'en portent AUCUN. Et `audit_traduction_manquante --wp`, lancé la
même heure sur la base, n'en expliquait que 13 : les 26 autres, la base les compte
dans ses « 83 ont déjà leur jumelle publiée ».

LE CAS QUI A TOUT MONTRÉ. WP#8137 « Carla With Love » (français, 05/09 09h42) et
WP#8175 (italien, 05/09 10h49, `/it/…-2`, titre « Martina Arduino interpreta Carla
Fracci ai Musei Reali di Torino »). La traduction a été écrite, payée, publiée, du BON
versant, une heure après l'originale. Et la page française n'annonce aucune version
italienne : le sélecteur de langue ne propose rien, Google voit deux pages sans
rapport. Il ne manquait que le LIEN.

POURQUOI PERSONNE NE LE VOYAIT — trois détecteurs, trois angles morts :
  • `audit_traduction_manquante` demande « une jumelle existe-t-elle et est-elle
    publique ? ». Oui, deux fois oui. Elle compte la paire comme saine ;
  • `audit_langue_polylang` (cron 9h55 depuis aujourd'hui) demande « la jumelle est-elle
    du versant qu'on lui a demandé ? ». Oui : WP#8175 est bien en `/it/`. Il se taît ;
  • `verifier_doublons_publies` écarte les paires de versants OPPOSÉS comme « paire FR/IT
    normale » — c'est justement ce qu'elle est.
Aucun ne demande « sont-elles RELIÉES ? », et c'est la seule question que le lecteur pose.

LA CAUSE, DANS LE CODE. `scripts/translate_events.py` appelle `_post_link(...)`, qui rend
True ou False, puis écrit `translated_at` à la ligne suivante SANS lire ce verdict. Après
quoi plus personne ne repasse : `translate_events` exclut la fiche (`translated_at` est
posé, et la jumelle EXISTE donc `_rearme_traductions_orphelines` ne se déclenche pas),
`link_translations_as` exclut explicitement les paires dont `translation_of` est
renseigné, et `repair_lien_traduction` répare la COLONNE en base, pas le lien WordPress.
Un état terminal sans rouvreur — règle 3. Ce script est le rouvreur.

CE QU'IL NE FAIT PAS, ET C'EST VOLONTAIRE :
  • il ne relie JAMAIS deux pages du même versant. Les relier ne montrerait rien au
    lecteur (Polylang veut deux langues) et masquerait le vrai défaut. Ces paires-là sont
    NOMMÉES et rendues à `audit_langue_polylang` puis `translate_events --retranslate`,
    qui republie du bon côté. Le geste n'est pas le même, le compteur non plus ;
  • il n'efface pas `translated_at` pour « faire retraduire ». Ce serait la fausse bonne
    idée : la fiche repasserait dans la file et une TROISIÈME page naîtrait. Le texte
    italien existe déjà, il est en ligne, il ne manque qu'un lien ;
  • il ne lie pas une jumelle du BON versant dont le TEXTE est resté dans l'autre langue
    (ajouté le 21/09 au soir, deux heures après la première version — c'est la production
    qui l'a montré, pas ma fixture : WP#2340 est passée du versant fr au versant it à
    16h04 en gardant son titre français. La lier aurait certifié une page française comme
    traduction officielle, et l'aurait rendue invisible à `audit_langue_polylang`, qui ne
    compare que le versant à la langue demandée).

LE TÉMOIN. Une paire correctement liée émet, sur la page publique de l'original,
`<link rel="alternate" href="…" hreflang="it">` vers sa jumelle — c'est la raison d'être
du liage, écrite dans `link_translations_as` (« pour que le sélecteur de langue et les
hreflang fonctionnent »). Vérifié le 21/09 sur une paire saine (WP#9366 ↔ WP#9507 : le
hreflang y est) et sur deux paires malades (WP#8137, WP#745 : aucun hreflang du tout).

Règle 1 : on ne conclut pas sur l'état du site depuis la base. Les deux numéros sont donc
interrogés sur l'API REST (public / corbeille / supprimé), l'adresse LIVE de chacun vient
de WordPress et pas de `wp_permalink_as`, et après un `--apply` la page est RELUE pour
dire ce qui s'est produit et non ce qui a été demandé (règle 6).

Usage (VPS) :
    .venv/bin/python -m scripts.repair_lien_polylang              # dry-run, on lit tout
    .venv/bin/python -m scripts.repair_lien_polylang --apply
    .venv/bin/python -m scripts.repair_lien_polylang --ids 8137   # un original précis
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger                          # noqa: E402
from utils.lang import cote_du_permalien, effective_lang     # noqa: E402
from scripts.audit_substance_published import devant_nous    # noqa: E402
from scripts.link_translations_as import _post_link          # noqa: E402
from scripts.reconcile_wp_deleted import _etat               # noqa: E402

log = get_logger("repair-lien-polylang")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}

# Les verdicts, et le geste de chacun. Une paire tombe dans UN seul — sinon les nombres
# s'additionnent en double et plus personne ne les croit (règle 6).
VERDICTS = {
    "lien_absent": "du bon versant, AUCUN hreflang vers la jumelle — à relier ici",
    "lien_ailleurs": "du bon versant, mais le hreflang pointe une AUTRE page",
    "jumelle_mauvaise_langue": "bon versant, mais le TEXTE de la jumelle est dans "
                               "l'autre langue — surtout PAS à lier",
    "meme_versant": "les deux pages du même côté du site — PAS un défaut de lien",
    "versant_muet": "adresse en forme provisoire : le versant ne se lit pas",
    "hors_ligne": "un des deux numéros n'est plus public (corbeille ou supprimé)",
    "deja_lie": "hreflang présent et pointant la jumelle — rien à faire",
    "page_injoignable": "la page publique n'a pas répondu — rien conclu",
}


def alternates(html: str) -> dict[str, str]:
    """Les `rel="alternate" hreflang=…` d'une page, {langue: adresse}.

    Polylang les émet dans les deux ordres d'attributs selon la version et le thème ; on
    accepte les deux plutôt que de dépendre d'un ordre qu'on n'a pas choisi. `x-default`
    est gardé tel quel : il ne prouve aucune traduction, et le verdict ne le lit pas.
    """
    out: dict[str, str] = {}
    for href, lang in re.findall(
            r'rel="alternate"[^>]*?href="([^"]+)"[^>]*?hreflang="([a-zA-Z-]+)"', html):
        out.setdefault(lang.lower(), href)
    for lang, href in re.findall(
            r'rel="alternate"[^>]*?hreflang="([a-zA-Z-]+)"[^>]*?href="([^"]+)"', html):
        out.setdefault(lang.lower(), href)
    return out


def _chemin(url: str) -> str:
    """Le chemin d'une adresse, sans hôte ni barre finale — pour comparer deux
    permaliens sans se faire piéger par http/https ni par le www."""
    u = (url or "").strip().lower()
    u = re.sub(r"^https?://[^/]+", "", u)
    return u.split("?")[0].rstrip("/")


def verdict(cote_orig: str, cote_jum: str, alts: dict, lien_jumelle: str,
            langue_jumelle: str = "") -> str:
    """Le cœur de la décision, PURE — aucun réseau, aucune base : c'est elle qui mérite
    une fixture (tests/test_repair_lien_polylang.py), pas la plomberie HTTP autour.

    `cote_orig` / `cote_jum` viennent de `utils.lang.cote_du_permalien` et
    `langue_jumelle` de `utils.lang.effective_lang` — les MÊMES définitions que
    `audit_langue_polylang`, le dédoublonnage et `translate_events`. Pas de second
    détecteur : deux copies d'une même question se contredisent (21/09)."""
    if not cote_orig or not cote_jum:
        return "versant_muet"
    if cote_orig == cote_jum:
        return "meme_versant"
    # LE VERSANT NE DIT PAS LA LANGUE DU TEXTE — corrigé le 2026-09-21 en fin de journée,
    # deux heures après avoir livré ce script, et c'est la production qui l'a montré.
    #
    # À 14h, WP#2340 (« Orlando de Haendel à l'Opéra Nice Côte d'Azur », la jumelle de
    # WP#745) était servie du versant FRANÇAIS. À 16h04 elle avait été republiée du
    # versant ITALIEN — avec son titre toujours en français. Le versant était devenu
    # juste, le texte non. La première version de ce script aurait donc LIÉ la paire, et
    # le sélecteur de langue aurait proposé aux lecteurs italiens une page française,
    # désormais estampillée traduction officielle. Pire : `audit_langue_polylang` compare
    # le versant servi à `translated_lang`, or les deux disent 'it' — la fiche redevenait
    # invisible à tout le monde, avec un lien de plus pour la certifier.
    #
    # C'est la faute que CLAUDE.md nomme le plus souvent : conclure sur un indice de
    # SURFACE (le préfixe /it/ de l'adresse) au lieu d'aller lire la chose (le texte).
    # Ma fixture ne pouvait pas l'attraper : elle ne contenait que des versants.
    #
    # ON S'ABSTIENT, ON NE LIE PAS. Et le sens de l'erreur est choisi : si `detect_lang`
    # se trompe sur une jumelle saine (l'incident du 17/09 prouve qu'elle peut), on refuse
    # de lier une paire correcte — elle reste dans l'état où elle était, et elle est
    # NOMMÉE. L'inverse cimenterait une page dans la mauvaise langue.
    if langue_jumelle and langue_jumelle != cote_jum:
        return "jumelle_mauvaise_langue"
    autre = cote_jum                      # le versant de la jumelle = la langue attendue
    vu = alts.get(autre) or ""
    if not vu:
        return "lien_absent"
    return "deja_lie" if _chemin(vu) == _chemin(lien_jumelle) else "lien_ailleurs"


def _get(url: str, casse_le_cache: bool = False) -> str:
    """Le HTML d'une page publique, "" si elle ne répond pas.

    `casse_le_cache` ajoute un paramètre inutile : la relecture d'après `--apply` doit
    voir la page REFAITE, or le site pose `Cache-Control: public` (cs-cache-control-home)
    et un proxy pourrait rendre la version d'avant. Un rapport qui lit un cache annonce
    l'intention au lieu du résultat, ce qui est exactement ce que la règle 6 interdit."""
    if casse_le_cache:
        url = f"{url}{'&' if '?' in url else '?'}_lien={int(time.time())}"
    try:
        r = requests.get(url, timeout=30, headers=_UA)
        return r.text if r.status_code == 200 else ""
    except requests.RequestException:
        return ""


def _lien_live(wp_url: str, post_id: int) -> str:
    """L'adresse que WordPress donne AUJOURD'HUI pour ce numéro ("" si muette).

    Pas `wp_permalink_as` : c'est un champ écrit un jour donné, et une republication a pu
    déplacer la page sans que la colonne bouge (règle 1, et l'avertissement que porte
    `cote_du_permalien` elle-même)."""
    try:
        r = requests.get(f"{wp_url}/wp-json/wp/v2/tribe_events/{post_id}",
                         timeout=20, headers=_UA)
        if r.status_code == 200:
            return str((r.json() or {}).get("link") or "")
    except (requests.RequestException, ValueError):
        pass
    return ""


def paires(conn, ids: list[int] | None, tout: bool) -> list[tuple[dict, dict]]:
    """Les paires (original, jumelle) dont les DEUX côtés portent un numéro WordPress.

    Périmètre règle 5 par défaut : à venir, en cours, récurrent ou SANS DATE (une date
    manquante n'est pas un événement terminé). Réparer le lien d'un événement passé ne
    sert personne — la page ne sera pas relue."""
    auj = date.today().isoformat()
    jumelles = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(translation_of,0)!=0 "
        "AND COALESCE(wp_post_id_as,0)>0 AND duplicate_of IS NULL")]
    par_id = {r["id"]: dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0)>0")}
    out = []
    for jum in jumelles:
        orig = par_id.get(jum["translation_of"])
        if not orig:
            continue                      # jumelle orpheline : c'est audit_traduction_manquante
        if ids and orig["id"] not in ids and jum["id"] not in ids:
            continue
        if not tout and not (devant_nous(orig, auj) or devant_nous(jum, auj)):
            continue
        out.append((orig, jum))
    return out


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--apply", action="store_true",
                   help="Repose le lien Polylang (défaut : simulation, on affiche).")
    p.add_argument("--tout", action="store_true",
                   help="Inclure les événements passés (règle 5 : ils ne servent personne).")
    p.add_argument("--ids", type=int, nargs="+", default=None,
                   help="Ne traiter que ces ids (original ou jumelle).")
    p.add_argument("--cap", type=int, default=200, help="Nb max de paires examinées.")
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}  (lancer ce script sur le VPS.)")
        return 1
    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    if not wp_url:
        log.error("WP_AS_URL est vide — j'arrête plutôt que de rendre un état inventé.")
        return 2
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    if args.apply and not all(auth):
        log.error("WP_AS_USER / WP_AS_APP_PASSWORD manquants — le liage est impossible.")
        return 2

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    lot = paires(conn, args.ids, args.tout)
    conn.close()
    perimetre = "toutes dates" if args.tout else "encore devant nous (règle 5)"
    total = len(lot)
    lot = lot[:args.cap]

    par_verdict: dict[str, list] = {}
    reparees, echecs = [], []
    for orig, jum in lot:
        po, pj = int(orig["wp_post_id_as"]), int(jum["wp_post_id_as"])
        # Règle 1 : l'état du site se demande à l'API REST, par NUMÉRO, jamais à la base.
        eo, ej = _etat(wp_url, po), _etat(wp_url, pj)
        if eo != "public" or ej != "public":
            par_verdict.setdefault("hors_ligne", []).append(
                (orig, jum, f"WP#{po}:{eo} WP#{pj}:{ej}"))
            continue
        lo, lj = _lien_live(wp_url, po), _lien_live(wp_url, pj)
        html = _get(lo) if lo else ""
        if lo and not html:
            par_verdict.setdefault("page_injoignable", []).append((orig, jum, lo))
            continue
        # `effective_lang` lit l'ARTICLE rédigé s'il existe, jamais le seul titre brut :
        # c'est la même fonction que translate_events consulte pour DÉCIDER une traduction.
        v = verdict(cote_du_permalien(lo), cote_du_permalien(lj), alternates(html), lj,
                    effective_lang(jum))
        par_verdict.setdefault(v, []).append((orig, jum, f"{lo} ↔ {lj}"))
        if v != "lien_absent" or not args.apply:
            continue
        # LE GESTE. L'endpoint maison cs/v1/link-translations (pll_save_post_translations)
        # est idempotent : reposer un lien déjà bon ne casse rien, ce qui est la raison
        # pour laquelle ce rouvreur peut tourner tous les jours sans précaution.
        co = cote_du_permalien(lo)
        ok = _post_link(wp_url, auth, {co: po, cote_du_permalien(lj): pj})
        if not ok:
            echecs.append((orig, jum, "cs/v1/link-translations a refusé"))
            continue
        # RELIRE, et ne pas croire le 200 : règle 6, on rapporte le résultat. Le cache est
        # cassé exprès, sinon on relit la page d'avant et on se félicite pour rien.
        alts2 = alternates(_get(lo, casse_le_cache=True))
        if verdict(co, cote_du_permalien(lj), alts2, lj,
                   effective_lang(jum)) == "deja_lie":
            reparees.append((orig, jum, lj))
        else:
            echecs.append((orig, jum, "lien posé, mais la page ne l'annonce toujours pas"))

    print("=" * 78)
    print("Lien Polylang des paires FR/IT publiées")
    print("=" * 78)
    print(f"Paires portant deux numéros WordPress : {total}, {perimetre}")
    print(f"EXAMINÉES ici                         : {len(lot)}"
          + (f"  (--cap {args.cap})" if total > len(lot) else ""))
    print(f"Mode                                  : "
          + ("APPLIQUE" if args.apply else "simulation (rien envoyé)"))
    print()
    for cle, libelle in VERDICTS.items():
        lot_v = par_verdict.get(cle, [])
        print(f"── {len(lot_v):>3}  {libelle}")
        for orig, jum, quoi in lot_v[:12]:
            print(f"      [{orig['id']}→{jum['id']}] WP#{orig.get('wp_post_id_as')}→"
                  f"WP#{jum.get('wp_post_id_as')} {(orig.get('title') or '')[:52]}")
            print(f"          {quoi}")
        if len(lot_v) > 12:
            # Une liste tronquée annonce son total, sinon elle fabrique de fausses causes.
            print(f"      … et {len(lot_v) - 12} autre(s) — total {len(lot_v)}")
        if cle == "meme_versant" and lot_v:
            print("      → PAS un défaut de lien : les deux pages sont du même côté. Le geste")
            print("        est `.venv/bin/python -m scripts.audit_langue_polylang` puis")
            print("        `translate_events.py --retranslate <id de l'original>`, qui republie")
            print("        du bon versant. Les relier ici ne montrerait rien au lecteur.")
        if cle == "jumelle_mauvaise_langue" and lot_v:
            print("      → NE PAS LIER : le lecteur italien recevrait une page française,")
            print("        certifiée traduction officielle par le lien. Le versant est juste,")
            print("        le TEXTE non — mesuré sur WP#2340 le 21/09 à 16h04. Le geste est")
            print("        `translate_events.py --retranslate <id de l'original> --apply`,")
            print("        qui réécrit le texte ET relie la paire.")
        if cle == "lien_ailleurs" and lot_v:
            print("      → appariement douteux : le hreflang mène à une TROISIÈME page. À")
            print("        trancher à la main (scripts/unlink_bad_translations.py) — on ne")
            print("        recouvre pas un lien existant sur une supposition.")
    print()

    # LE BILAN, en dernier : `weekly_audits` ne retient que les dernières lignes (_tail),
    # et ce script finissait sinon au milieu d'un listing (leçon de reconcile_wp_deleted,
    # 18/08). Et il PART MÊME À ZÉRO, avec le nombre d'examinées à côté : un zéro sur une
    # file vide et un zéro sur une requête cassée ont exactement la même tête (11/08).
    absents = len(par_verdict.get("lien_absent", []))
    ligne = (f"Lien Polylang : {absents} paire(s) sans hreflang sur {len(lot)} examinée(s) "
             f"({perimetre})")
    if args.apply:
        ligne += f" · {len(reparees)} relié(s) et RELU(s)"
        if echecs:
            ligne += f" · {len(echecs)} échec(s)"
    else:
        ligne += " · simulation : rien envoyé"
    if par_verdict.get("meme_versant"):
        ligne += (f" · {len(par_verdict['meme_versant'])} paire(s) du même versant, "
                  f"rendues à audit_langue_polylang")
    print(ligne)
    for orig, jum, pourquoi in echecs:
        log.error("[%s→%s] %s", orig["id"], jum["id"], pourquoi)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
