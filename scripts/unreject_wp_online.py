#!/usr/bin/env python3
"""RE-CLASSE une fiche REJETÉE en base alors que son post est TOUJOURS EN LIGNE.

LE TROU QUE ÇA FERME. `scripts/audit_wp_ghosts.py` sait DÉTECTER l'écart « en ligne sur
le site, rejeté en base », et il imprime une commande `scripts.trash_wp_ids` toute prête
pour le refermer *dans un sens* : retirer le post. Il n'existait rien pour l'autre sens.
Or l'audit lui-même le dit dans son épilogue :

    « Réparer la BASE plutôt que le site est parfois le bon geste : une fiche rejetée à
      tort se répare en la re-classant, et elle redevient alors légitimement en ligne —
      sans rien toucher côté WordPress. »

…et ce geste n'existait pas en ligne de commande. C'est le motif récurrent de ce dépôt :
un ÉTAT TERMINAL qu'un script pose (`statut='rejected'` chez evaluator, purge_out_of_zone,
dedupe, le bouton « rejeter » du dashboard) et qu'aucun autre ne sait rouvrir. Faute
d'outil, la seule issue proposée était la destructive.

CE QUE FAIT CE SCRIPT, et RIEN D'AUTRE :
  • il VÉRIFIE, via l'API REST, que le post est réellement PUBLIC (pas corbeille, pas
    supprimé — la distinction est celle de reconcile_wp_deleted._etat, et elle compte :
    re-classer « publiée » une fiche dont le post est à la corbeille produirait le mensonge
    exactement inverse de celui qu'on répare) ;
  • il VÉRIFIE que le titre du post correspond à celui de la fiche, sinon il refuse ;
  • il repose `statut` (défaut `published_sub`, le catalogue) et efface `wp_deleted_at` ;
  • il RÉÉCRIT `llm_justification` pour porter la trace de la décision humaine et sa date.

Il n'appelle JAMAIS WordPress en écriture. Le post est déjà en ligne : il n'y a rien à y
faire, c'est la base qui a tort.

⚠️ LE SCORE EST PERDU, ET CE SCRIPT NE L'INVENTE PAS. Tous les chemins de rejet posent
`llm_score = 0` en même temps que `statut='rejected'` (evaluator.py, purge_out_of_zone.py).
Le score d'origine n'est enregistré nulle part : re-classer ne le ressuscite pas. Or un
score à 0 a une conséquence CONCRÈTE et silencieuse — `scripts/enrich.py` sélectionne sur
`llm_score >= ENRICH_MIN_SCORE` (défaut 1), donc une fiche re-classée à 0 ne sera JAMAIS
rédigée : elle restera en ligne avec son texte de scraping brut. C'est précisément le
défaut « n'est pas rédigé » constaté sur WP#2340 le 2026-08-03.
Le script ne choisit pas à la place de l'humain : sans `--score`, il laisse le 0 en place
et le DIT en toutes lettres. Avec `--score N`, il pose la note demandée. Repères, lus dans
le code et pas devinés :
    `--score 1` … suffit à rendre la fiche éligible à la rédaction (catalogue) ;
    `--score 7` … RETAIN_MIN_SCORE : au-dessus, la fiche prétend à la mise en avant.

Usage (sur le VPS) :
    .venv/bin/python -m scripts.unreject_wp_online 2257 2269           # dry-run
    .venv/bin/python -m scripts.unreject_wp_online 2257 2269 --score 5 --apply
"""
from __future__ import annotations
import argparse
import html
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("unreject-wp")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
UA = {"User-Agent": "AgendaSabauda-unreject/1.0"}

# Seuil au-dessus duquel une fiche prétend à la mise en avant (home). Lu au même endroit
# que scripts/evaluator.py pour qu'un réglage d'environnement vaille pour les deux.
RETAIN_MIN_SCORE = int(os.getenv("RETAIN_MIN_SCORE", os.getenv("ENRICH_MIN_SCORE", "7")))
# Plancher de sélection de scripts/enrich.py : en dessous, la fiche n'est jamais rédigée.
ENRICH_MIN_SCORE = int(os.getenv("ENRICH_MIN_SCORE", "1"))
# Les deux seuls statuts « retenu » du pipeline : catalogue et mise en avant.
STATUTS_VALIDES = ("published_sub", "evaluated")
# Titre : au-dessous de ce recouvrement, on considère que le lien pointe ailleurs.
SEUIL_TITRE = 0.55


def _norm(s: str) -> str:
    """Titre normalisé (mêmes règles que relink_wp_ids_as/_norm et audit_wp_ghosts)."""
    t = html.unescape(s or "")
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def _etat(wp_url: str, post_id: int) -> tuple[str, str]:
    """('public'|'non_public'|'inexistant'|'indetermine', titre rendu).

    ⚠️ NE JAMAIS interroger le front-end pour ça : `/?p=<id>` renvoie 404 pour TOUT
    tribe_events de cette installation, vivant ou mort, et un post en corbeille répond
    404 exactement comme un post supprimé. C'est ce qui a produit la fausse alerte
    « 61 posts supprimés » du 2026-08-02 — aucun ne l'était. Seule l'API REST sépare les
    trois états, et cette distinction commande TOUT ce que fait ce script.
    """
    try:
        r = requests.get(f"{wp_url}/wp-json/wp/v2/tribe_events/{post_id}",
                         params={"_fields": "id,title,status,link"}, timeout=20, headers=UA)
    except requests.RequestException as exc:
        log.warning("WP#%s : appel REST impossible (%s).", post_id, exc)
        return "indetermine", ""
    if r.status_code == 200:
        try:
            data = r.json() or {}
        except ValueError:
            return "indetermine", ""
        return "public", (data.get("title") or {}).get("rendered", "")
    code = ""
    try:
        code = str((r.json() or {}).get("code") or "")
    except ValueError:
        pass
    if code == "rest_post_invalid_id":
        return "inexistant", ""
    if code == "rest_forbidden" or r.status_code in (401, 403):
        return "non_public", ""
    return "indetermine", ""


def _titres_locaux(row: dict) -> list[str]:
    """Les titres qu'une fiche a PU envoyer à WordPress, dans l'ordre où
    `scripts/publisher.build_post()` les choisit : article_title, puis le `titre` de
    enrich_data.article, puis `title` brut. Comparer au seul `title` inventerait une
    divergence sur toute fiche enrichie — c'est la leçon d'audit_wp_ghosts."""
    out = [row.get("article_title") or ""]
    try:
        art = (json.loads(row.get("enrich_data") or "{}") or {}).get("article") or {}
        out.append(art.get("titre") or "")
    except (ValueError, TypeError):
        pass
    out.append(row.get("title") or "")
    return [t for t in out if t.strip()]


def _similarite(titre_wp: str, row: dict) -> float:
    """Meilleur recouvrement de mots entre le titre du post et les titres possibles de la
    fiche. Volontairement grossier : il ne sert qu'à REFUSER un lien manifestement faux,
    jamais à départager deux candidats."""
    a = set(_norm(titre_wp).split())
    if not a:
        return 0.0
    best = 0.0
    for t in _titres_locaux(row):
        b = set(_norm(t).split())
        if b:
            best = max(best, len(a & b) / max(len(a), len(b)))
    return best


def _ensure_col(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("ALTER TABLE events_raw ADD COLUMN wp_deleted_at TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Re-classe une fiche rejetée en base dont le post est toujours en ligne.")
    p.add_argument("wp_ids", type=int, nargs="+",
                   help="Identifiants des posts WordPress (ceux qu'affiche audit_wp_ghosts).")
    p.add_argument("--apply", action="store_true", help="Écrit en base (sinon dry-run).")
    p.add_argument("--statut", default="published_sub", choices=STATUTS_VALIDES,
                   help="Statut à reposer (défaut : published_sub, le catalogue).")
    p.add_argument("--score", type=int, default=None,
                   help="Note à reposer. Sans cette option, le 0 du rejet est CONSERVÉ "
                        "et la fiche ne sera jamais rédigée par enrich.py.")
    p.add_argument("--motif", default="",
                   help="Phrase à consigner dans llm_justification (trace de la décision).")
    p.add_argument("--seuil-titre", type=float, default=SEUIL_TITRE,
                   help=f"Recouvrement de titre minimal (défaut {SEUIL_TITRE}).")
    p.add_argument("--delay", type=float, default=0.5, help="Pause entre deux appels REST.")
    args = p.parse_args(argv)

    if args.score is not None and args.score < 0:
        log.error("--score doit être positif ou nul.")
        return 2

    load_dotenv(ROOT / ".env")
    wp_url = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_col(conn)

    marks = ",".join("?" * len(args.wp_ids))
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM events_raw WHERE wp_post_id_as IN ({marks}) ORDER BY id",
        args.wp_ids).fetchall()]
    par_post: dict[int, list[dict]] = {}
    for r in rows:
        par_post.setdefault(int(r["wp_post_id_as"]), []).append(r)

    a_faire, refuses = [], []
    for i, wp_id in enumerate(args.wp_ids, 1):
        lignes = par_post.get(wp_id, [])
        if not lignes:
            refuses.append((wp_id, "aucune ligne de la base ne pointe ce post "
                                   "(c'est un ORPHELIN : voir audit_wp_ghosts ③)"))
            continue
        if len(lignes) > 1:
            # Deux lignes sur un même post, c'est l'anomalie que audit_wp_ghosts signale.
            # En re-classer une « publiée » sans savoir laquelle est la bonne aggraverait
            # le désordre. On ne tranche pas.
            refuses.append((wp_id, "PLUSIEURS lignes locales le revendiquent (%s) — "
                                   "départager demande de comparer dates et lieu"
                            % ", ".join(str(l["id"]) for l in lignes)))
            continue
        ev = lignes[0]
        if (ev.get("statut") or "") != "rejected":
            refuses.append((wp_id, f"la ligne {ev['id']} n'est pas 'rejected' mais "
                                   f"'{ev.get('statut')}' — rien à rouvrir"))
            continue
        if ev.get("duplicate_of") is not None:
            refuses.append((wp_id, f"la ligne {ev['id']} est un DOUBLON de "
                                   f"{ev['duplicate_of']} — c'est la fusion qu'il faut "
                                   f"défaire, pas le statut"))
            continue

        etat, titre_wp = _etat(wp_url, wp_id)
        if args.delay and i < len(args.wp_ids):
            time.sleep(args.delay)
        if etat != "public":
            # « non_public » = corbeille ou brouillon ; « inexistant » = supprimé.
            # Re-classer « publiée » une fiche dont le post n'est pas visible fabriquerait
            # le mensonge exactement symétrique de celui qu'on répare.
            refuses.append((wp_id, f"le post n'est PAS public côté WordPress "
                                   f"(état : {etat}) — rien à re-classer"))
            continue
        sim = _similarite(titre_wp, ev)
        if sim < args.seuil_titre:
            refuses.append((wp_id, f"titre divergent (recouvrement {sim:.2f} < "
                                   f"{args.seuil_titre}) : « {titre_wp[:45]} » côté site, "
                                   f"« {(ev.get('title') or '')[:45]} » en base — le lien "
                                   f"wp_post_id_as pointe probablement ailleurs "
                                   f"(cf. relink_wp_ids_as)"))
            continue
        a_faire.append((wp_id, ev, titre_wp, sim))

    print(f"\n{len(a_faire)} fiche(s) à re-classer, {len(refuses)} refusée(s).\n")
    for wp_id, ev, titre_wp, sim in a_faire:
        score_txt = (f"llm_score {ev.get('llm_score')} → {args.score}"
                     if args.score is not None
                     else f"llm_score {ev.get('llm_score')} INCHANGÉ")
        print(f"  WP#{wp_id} ↔ ligne {ev['id']} · titre {sim:.2f}")
        print(f"      « {titre_wp[:70]} »")
        print(f"      statut 'rejected' → '{args.statut}' · {score_txt}")
        ancienne = (ev.get("llm_justification") or "").strip()
        if ancienne:
            print(f"      motif du rejet effacé : « {ancienne[:90]} »")
    for wp_id, motif in refuses:
        print(f"  ⛔ WP#{wp_id} — {motif}")

    # L'avertissement le plus important du script : sans score, la fiche reste en ligne
    # avec son texte brut, et AUCUN cron ne viendra jamais la rédiger. Le dire au moment
    # où la décision se prend, pas dans un fichier que personne ne relit.
    if a_faire and args.score is None:
        muettes = [w for w, e, _, _ in a_faire if int(e.get("llm_score") or 0) < ENRICH_MIN_SCORE]
        if muettes:
            print(f"\n⚠️  {len(muettes)} fiche(s) gardent un llm_score sous {ENRICH_MIN_SCORE} : "
                  f"{', '.join('WP#%d' % w for w in muettes)}")
            print(f"    scripts/enrich.py sélectionne sur `llm_score >= {ENRICH_MIN_SCORE}` — "
                  f"elles resteront donc EN LIGNE mais JAMAIS RÉDIGÉES, avec le texte brut")
            print(f"    du scraping. Le rejet avait mis le score à 0 et la note d'origine")
            print(f"    n'est enregistrée nulle part : ce script ne l'invente pas.")
            print(f"    → ajouter --score N pour en reposer une "
                  f"(≥ {ENRICH_MIN_SCORE} : rédigeable ; ≥ {RETAIN_MIN_SCORE} : mise en avant).")

    if not args.apply:
        print("\nDry-run — rien n'a été écrit. Ajouter --apply pour appliquer.")
        conn.close()
        return 0
    if not a_faire:
        conn.close()
        return 0

    jour = date.today().isoformat()
    motif = args.motif.strip() or "relue et validée à la main"
    for wp_id, ev, _t, _s in a_faire:
        justif = (f"Re-classée le {jour} — le post WP#{wp_id} était en ligne alors que la "
                  f"base l'avait rejetée ; {motif}.")
        champs = ["statut=?", "llm_justification=?", "wp_deleted_at=NULL"]
        params: list = [args.statut, justif]
        if args.score is not None:
            champs.insert(1, "llm_score=?")
            params.insert(1, args.score)
        params.append(ev["id"])
        conn.execute(f"UPDATE events_raw SET {', '.join(champs)} WHERE id=?", params)
        log.info("[%s] WP#%s re-classée '%s'%s", ev["id"], wp_id, args.statut,
                 f" (score {args.score})" if args.score is not None else "")
    conn.commit()
    conn.close()
    print(f"\n✅ {len(a_faire)} fiche(s) re-classée(s) en '{args.statut}'. "
          f"Rien n'a été touché côté WordPress — les posts étaient déjà en ligne.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
