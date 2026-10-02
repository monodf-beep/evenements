#!/usr/bin/env python3
"""Note les fiches publiées comme l'éditeur de Yoast le ferait — sans ouvrir l'éditeur.

D'OÙ ÇA VIENT — Franck, 16/09/2026 : « pourquoi ça peut pas recalculer direct
automatiquement Yoast ? ». Parce que Yoast calcule en JavaScript, dans le navigateur,
à l'ouverture de la fiche, et nulle part ailleurs. Mesuré ce jour-là sur le site :
20 articles sur 24, 305 pages sur 306, 353 événements sur 364 sans aucune note — tout
ce que le pipeline publie par API. La colonne « Score SEO » du back-office, que Franck
lit comme un tableau de bord, disait « Non disponible » sur 678 fiches sur 694.

CE QUE ÇA FAIT, en trois pas, et rien d'autre :
  1. GET  cs/v1/yoast-papers  → les fiches à noter, servies par WordPress avec ce que
     l'éditeur donnerait au moteur (date au format de Yoast, titre rendu, locale) ;
  2. node scripts/yoast_score.js → le moteur de Yoast lui-même (paquet npm `yoastseo`),
     sur le VPS, sans réseau ;
  3. POST cs/v1/yoast-scores  → WordPress écrit les deux métas ET reconstruit
     l'indexable, la table que la colonne lit réellement.

Ne recalcule que ce qui a changé : `cs_score_at` (posé par la route) est comparé à
`post_modified_gmt` côté WordPress. Une fiche ouverte dans l'éditeur par Franck se
fait renoter par Yoast lui-même — ce script ne l'écrase que si elle change ensuite.

RÉVERSIBLE : Yoast réécrit ces champs à la prochaine ouverture. Dry-run par défaut.

Usage (VPS) :
    .venv/bin/python -m scripts.yoast_scores                    # dry-run : montre les notes
    .venv/bin/python -m scripts.yoast_scores --apply --cap 300  # écrit (cron, 12h00)
    .venv/bin/python -m scripts.yoast_scores --ids 8236 8231 --tout --apply
Prérequis, une fois : `npm install` dans /root/evenements (node ≥ 20, présent).
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger          # noqa: E402
from scripts.publisher import _headers       # noqa: E402 — même en-tête X-CS-Auth que la publication

log = get_logger("yoast-scores")
MOTEUR = ROOT / "scripts" / "yoast_score.js"
LOT = 50   # fiches par POST : assez petit pour qu'un échec nomme peu de fiches


def papiers(wp_url: str, auth, types: list[str], cap: int, ids: list[int], tout: bool) -> dict:
    params = {"types": ",".join(types), "limit": cap}
    if ids:
        params["ids"] = ",".join(str(i) for i in ids)
    if tout:
        params["tout"] = "1"
    r = requests.get(f"{wp_url}/?rest_route=/cs/v1/yoast-papers", params=params,
                     auth=auth, headers=_headers(auth), timeout=120)
    r.raise_for_status()
    return r.json()


def noter(entrees: list[dict]) -> list[dict]:
    """Fait tourner le moteur. Une panne de Node est une panne, jamais un « 0 noté »."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("`node` introuvable — Node ≥ 20 est requis sur cette machine.")
    if not (ROOT / "node_modules" / "yoastseo").exists():
        raise RuntimeError("Le paquet `yoastseo` n'est pas installé : lancer `npm install` "
                           f"dans {ROOT} (une fois).")
    proc = subprocess.run([node, str(MOTEUR)], input=json.dumps(entrees, ensure_ascii=False),
                          capture_output=True, text=True, cwd=str(ROOT), timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"le moteur a échoué : {proc.stderr.strip()[:500]}")
    return json.loads(proc.stdout)


def ecrire(wp_url: str, auth, notes: list[dict]) -> dict:
    total = {"ecrits": 0, "erreurs": [], "recompte": {}}
    for i in range(0, len(notes), LOT):
        lot = [{"id": n["id"], "seo": n["seo"], "readability": n["lisibilite"]} for n in notes[i:i + LOT]]
        r = requests.post(f"{wp_url}/?rest_route=/cs/v1/yoast-scores", json={"scores": lot},
                          auth=auth, headers=_headers(auth), timeout=300)
        r.raise_for_status()
        rep = r.json()
        total["ecrits"] += int(rep.get("ecrits") or 0)
        total["erreurs"] += list(rep.get("erreurs") or [])
        total["recompte"] = rep.get("recompte") or total["recompte"]
    return total


# --------------------------------------------------------------------------- #
# POURQUOI c'est rouge — le détail était calculé puis JETÉ
# --------------------------------------------------------------------------- #
# Franck, 21/09/2026 : « apparemment ce qu'on fait ne résout pas tout le temps le SEO ».
# En allant lire : `scripts/yoast_score.js` produit depuis toujours `seo_detail` et
# `lis_detail` — le score de CHAQUE critère de Yoast, fiche par fiche — et `ecrire()`
# n'envoyait que deux nombres agrégés. Le détail était donc calculé tous les jours à midi
# sur 300 fiches, puis jeté. Conséquence : personne ne pouvait dire QUEL critère était
# rouge sur combien de fiches, et la seule méthode qui restait était de rouvrir les
# articles un par un. C'est le défaut du 18/08 (« le chiffre attendu depuis le matin était
# calculé puis jeté par un [:2000] »), reproduit ici pendant des semaines.
#
# LE SEUIL EST À NOUS, PAS À YOAST. Yoast rend un score par critère ; l'appeler « mauvais »
# en dessous de 5 est une convention de ce dépôt, pas une règle du moteur. Elle se déplace
# (--seuil) et se contrôle : la note MOYENNE est affichée à côté du compte, donc un seuil
# mal placé se voit tout de suite au lieu de fabriquer un classement faux.
SEUIL_MAUVAIS = 5

# Libellés en français pour les critères vus en production. Un identifiant inconnu n'est
# JAMAIS masqué : il s'affiche tel quel. Une liste de correspondance incomplète qui
# cacherait les critères qu'elle ne connaît pas serait exactement la file tronquée du
# 18/08 — celle qui fabrique de fausses causes.
LIBELLES = {
    "subheadingsTooLongText": "texte trop long sans sous-titre (H2)",
    "textLength": "texte trop court",
    "sentenceLengthInText": "phrases trop longues",
    "passiveVoice": "voix passive",
    "textParagraphTooLong": "paragraphes trop longs",
    "transitionWords": "mots de liaison",
    "sentenceBeginnings": "débuts de phrase répétitifs",
    "fleschReadingEase": "difficulté de lecture",
    "keyphraseInTitle": "expression clé absente du titre",
    "keyphraseInIntroduction": "expression clé absente du chapô",
    "keyphraseDensity": "densité de l'expression clé",
    "metaDescriptionLength": "longueur de la méta-description",
    "metaDescriptionKeyword": "expression clé absente de la méta-description",
    "titleWidth": "longueur du titre SEO",
    "textImages": "images",
    "internalLinks": "liens internes",
    "externalLinks": "liens externes",
    "subheadingsKeyword": "expression clé absente des sous-titres",
}


def causes(notes: list[dict], seuil: int = SEUIL_MAUVAIS) -> list[dict]:
    """Classement des critères qui coincent, du plus répandu au moins répandu.

    Chaque entrée : critere, libelle, famille (SEO/lisibilité), mauvais, concernees,
    moyenne. `concernees` est le PÉRIMÈTRE : Yoast n'applique pas tous ses critères à
    toutes les fiches (`getValidResults`), donc « 187 mauvais » ne veut rien dire sans
    « sur 190 fiches où le critère s'applique ». Deux critères comptés sur deux
    populations différentes se contrediraient un jour, et c'est le plus gros qu'on
    croirait (règle 6)."""
    par_critere: dict = {}
    for n in notes:
        for famille, clef in (("SEO", "seo_detail"), ("lisibilité", "lis_detail")):
            for r in (n.get(clef) or []):
                cid = r.get("id") or "?"
                e = par_critere.setdefault((famille, cid),
                                           {"critere": cid, "famille": famille,
                                            "libelle": LIBELLES.get(cid, cid),
                                            "mauvais": 0, "concernees": 0, "_somme": 0})
                score = r.get("score") or 0
                e["concernees"] += 1
                e["_somme"] += score
                if score <= seuil:
                    e["mauvais"] += 1
    out = []
    for e in par_critere.values():
        e["moyenne"] = round(e["_somme"] / e["concernees"], 1) if e["concernees"] else 0
        del e["_somme"]
        if e["mauvais"]:                       # un critère vert partout n'est pas une cause
            out.append(e)
    out.sort(key=lambda e: (-e["mauvais"], e["moyenne"], e["critere"]))
    return out


def afficher_causes(notes: list[dict], seuil: int = SEUIL_MAUVAIS) -> list[dict]:
    """Imprime le classement et le renvoie (pour Slack). Dit combien de fiches l'ont
    nourri : un classement sans sa population ne se relit pas trois semaines plus tard."""
    rangs = causes(notes, seuil)
    print(f"\n=== POURQUOI c'est rouge — {len(notes)} fiche(s) notée(s), "
          f"critère « mauvais » = note ≤ {seuil} ===")
    if not rangs:
        print("  Aucun critère sous le seuil. Si la colonne Yoast est rouge malgré ça, "
              "c'est le seuil qui est mal placé : relancer avec --seuil 7.")
        return rangs
    for e in rangs:
        print(f"  {e['mauvais']:>4}/{e['concernees']:<4} {e['famille']:<11} "
              f"{e['libelle']}  (note moyenne {e['moyenne']}, critère {e['critere']})")
    return rangs


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--apply", action="store_true", help="Écrit les notes (sinon simulation).")
    p.add_argument("--types", default="post,page,tribe_events")
    p.add_argument("--cap", type=int, default=200, help="Fiches par run (max 500).")
    p.add_argument("--ids", nargs="*", type=int, default=[])
    p.add_argument("--tout", action="store_true", help="Ignore cs_score_at : renote même l'inchangé.")
    p.add_argument("--seuil", type=int, default=SEUIL_MAUVAIS,
                   help=f"Note en dessous de laquelle un critère compte comme mauvais "
                        f"(défaut {SEUIL_MAUVAIS}). Le seuil est une convention de ce dépôt.")
    args = p.parse_args(argv)

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    if not all([wp_url, auth[0], auth[1]]):
        log.error("WP_AS_URL / WP_AS_USER / WP_AS_APP_PASSWORD manquants dans .env")
        return 2

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    rep = papiers(wp_url, auth, types, args.cap, args.ids, args.tout)
    fiches = rep.get("papers") or []
    # Un zéro doit dire d'où il vient : combien sont publiées, combien présentées.
    log.info("%d fiche(s) à noter sur %d publiée(s) (%s)%s", len(fiches), rep.get("publiees", "?"),
             ", ".join(rep.get("types") or types), "" if fiches else " — rien n'a changé depuis le dernier passage")
    if not fiches:
        return 0

    notes = noter(fiches)
    par_id = {f["id"]: f for f in fiches}
    sans_cle = [n for n in notes if n["seo"] is None]
    for n in notes:
        f = par_id.get(n["id"], {})
        seo = "—" if n["seo"] is None else n["seo"]
        print(f"{n['id']:>6} {f.get('type', '?'):<13} SEO {seo:>3}  lisibilité {n['lisibilite']:>3}"
              f"  (avant : {f.get('linkdex') or '—'} / {f.get('content_score') or '—'})  {f.get('post_title', '')[:50]}")
    if sans_cle:
        # Le périmètre à côté du nombre : ces fiches-là n'ont pas de note SEO parce
        # qu'elles n'ont pas encore d'expression clé, pas parce que le moteur a échoué.
        # Pour un événement, la clé arrive avec seo_batch (après publication) ; la fiche
        # se représentera ici toute seule ce jour-là.
        print(f"\n{len(sans_cle)} fiche(s) sans expression clé : lisibilité seule, la colonne SEO "
              f"reste « Aucune expression clé » jusqu'à ce que seo_batch en pose une.")

    rangs = afficher_causes(notes, args.seuil)

    if not args.apply:
        print(f"\nDRY-RUN — {len(notes)} note(s) calculée(s), rien d'écrit. Relancer avec --apply.")
        return 0

    res = ecrire(wp_url, auth, notes)
    rc = res["recompte"]
    # Deux compteurs, deux périmètres : « sans note » = jamais passées ici ni dans
    # l'éditeur ; « sans clé » = notées en lisibilité seulement, SEO impossible tant
    # que seo_batch n'a pas posé d'expression clé.
    resume = " · ".join(f"{t} : {v['sans_score']}/{v['publiees']} sans note, {v['sans_cle']} sans clé"
                        for t, v in rc.items())
    log.info("=== Scores Yoast : %d écrite(s) sur %d calculée(s) (dont %d en lisibilité seule, sans clé), "
             "%d erreur(s). Reste %s ===", res["ecrits"], len(notes), len(sans_cle), len(res["erreurs"]), resume)
    for e in res["erreurs"][:10]:
        log.warning("  %s", e)
    from utils import pipeline_status, slack
    msg = (f"📐 *Scores Yoast* — {res['ecrits']} fiche(s) notée(s) avec le moteur de Yoast "
           f"(hors éditeur), dont {len(sans_cle)} en lisibilité seule faute d'expression clé. "
           f"Reste : {resume}")
    if rangs:
        # Les trois causes en tête, avec leur périmètre : c'est ce qui désigne le
        # correctif à faire UNE fois (prompt, gabarit), au lieu de N réécritures à la main.
        msg += "\n🔎 Ce qui coince : " + " · ".join(
            f"{e['libelle']} ({e['mauvais']}/{e['concernees']})" for e in rangs[:3])
    if res["erreurs"]:
        msg += f"\n⚠️ {len(res['erreurs'])} erreur(s) : " + " · ".join(res["erreurs"][:3])
    slack.notify(msg)
    pipeline_status.record_run("yoast_scores", ok=res["ecrits"], error=len(res["erreurs"]), summary=msg[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
