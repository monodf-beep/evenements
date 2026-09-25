#!/usr/bin/env python3
"""Met à la CORBEILLE WordPress (RÉVERSIBLE, cs/v1/trash) des événements ciblés PAR ID
LOCAL — sert au panier « CORBEILLE » du chantier contenu cassé
(scripts.triage_chantier_casse) : des fiches déjà jugées statut='rejected'/'merged' en
local, mais restées PUBLIÉES sur WordPress faute d'avoir été nettoyées à l'époque.

force=True (nécessaire ici : ces posts sont bien publiés sur WP, cs/v1/trash refuse sinon
un post publié par mesure de sécurité). Après corbeille, efface wp_post_id_as/
published_as_date en base (l'événement n'est plus « sur l'agenda »), comme
scripts.cleanup_as_trash. DRY-RUN par défaut.

⚠️ SI LA FICHE N'EST PAS DÉJÀ REJETÉE, IL FAUT `--statut rejected`. Effacer
`wp_post_id_as` sans toucher au statut fabrique, sur une fiche RETENUE, le profil exact
que `scripts/publish_batch_as.py` sélectionne pour une CRÉATION : statut retenu + aucun
post WordPress. La fiche part à la corbeille le matin et revient en ligne au lot de 9h30
le lendemain. Depuis le 2026-08-03 le script REFUSE d'appliquer dans ce cas plutôt que de
produire un aller-retour silencieux.

Usage :
    .venv/bin/python -m scripts.trash_by_ids 1120 2025 975 ...           # liste (dry-run)
    .venv/bin/python -m scripts.trash_by_ids 1120 2025 975 ... --apply
    # fiches encore RETENUES (hors périmètre, doublon éditorial…) :
    .venv/bin/python -m scripts.trash_by_ids 1438 1447 ... --statut rejected \\
        --motif "Hors périmètre — arrondissement de Grasse (charte §2)." --apply
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.cleanup_as_trash import trash_one

# Statuts « retenus » du pipeline : une fiche dans l'un d'eux est candidate à la
# publication. Même liste que scripts/publish_batch_as.py:61 — si elle diverge,
# le garde-fou ci-dessous laisse passer ce qu'il est censé retenir.
RETENUS = ("evaluated", "published_cs", "published_sub")

log = get_logger("trash-by-ids")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(description="Corbeille WordPress (réversible) par id local.")
    p.add_argument("ids", nargs="+", type=int, help="Ids LOCAUX (events_raw.id) à corbeiller.")
    p.add_argument("--apply", action="store_true", help="Exécute (sinon dry-run).")
    p.add_argument("--delay", type=float, default=0.5, help="Pause (s) entre deux appels.")
    p.add_argument("--statut", default="", choices=["", "rejected"],
                   help="Poser ce statut EN MÊME TEMPS que la corbeille. Indispensable dès "
                        "que la fiche n'est pas déjà 'rejected'/'merged' (voir ci-dessous).")
    p.add_argument("--motif", default="",
                   help="Phrase à consigner dans llm_justification avec --statut.")
    p.add_argument("--force-sans-statut", action="store_true",
                   help="Corbeiller une fiche RETENUE sans poser de statut — elle sera "
                        "republiée par le prochain lot quotidien. À n'utiliser que si "
                        "c'est justement ce qu'on veut (republication ailleurs).")
    args = p.parse_args(argv)

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ph = ",".join("?" * len(args.ids))
    rows = [dict(r) for r in conn.execute(
        f"SELECT id, title, statut, wp_post_id_as FROM events_raw WHERE id IN ({ph})",
        args.ids).fetchall()]
    missing = set(args.ids) - {r["id"] for r in rows}
    if missing:
        log.warning("id(s) introuvable(s), ignoré(s) : %s", sorted(missing))
    targets = [r for r in rows if (r.get("wp_post_id_as") or 0) > 0]
    skipped = [r for r in rows if not (r.get("wp_post_id_as") or 0) > 0]
    for r in skipped:
        log.info("id=%s « %s » — pas de wp_post_id_as, rien à corbeiller (déjà hors ligne).",
                 r["id"], (r["title"] or "")[:50])

    mode = "EXÉCUTION" if args.apply else "DRY-RUN (rien ne bouge)"
    log.info("%s — %d événement(s) à corbeiller :", mode, len(targets))
    for r in targets:
        log.info("  id=%s WP#%s statut=%s « %s »", r["id"], r["wp_post_id_as"], r["statut"],
                 (r["title"] or "")[:55])

    # ⚠️ GARDE-FOU AJOUTÉ LE 2026-08-03. Ce script efface `wp_post_id_as` et NE TOUCHE PAS
    # au statut — ce qui est juste pour son usage d'origine (des fiches déjà 'rejected' ou
    # 'merged', restées publiées par oubli, cf. docstring). Mais appliqué à une fiche
    # RETENUE, il fabrique exactement le profil que `scripts/publish_batch_as.py`
    # sélectionne pour une CRÉATION : statut retenu + aucun wp_post_id_as. La fiche est
    # corbeillée le matin et remise en ligne par le lot de 9h30 le lendemain, sans que
    # personne ne comprenne pourquoi elle revient.
    #
    # Le cas réel qui l'a révélé : les 27 fiches de l'arrondissement de Grasse (hors
    # périmètre depuis la charte §2), toutes en 'published_sub'/'evaluated'. Les
    # corbeiller sans poser 'rejected' aurait été un aller-retour.
    #
    # On ne CHOISIT pas à la place de l'humain — un statut est une décision éditoriale —
    # mais on refuse de laisser partir le geste sans qu'il ait vu le piège.
    retenues = [] if args.force_sans_statut else [
        r for r in targets if (r.get("statut") or "") in RETENUS]
    if retenues and not args.statut:
        log.warning("")
        log.warning("⚠️  %d fiche(s) visée(s) sont RETENUES (%s) et non rejetées.",
                    len(retenues), "/".join(sorted({r["statut"] for r in retenues})))
        log.warning("    Les corbeiller SANS --statut les laisse « retenues, sans post WP » :")
        log.warning("    c'est le profil que publish_batch_as republie. Elles reviendraient")
        log.warning("    en ligne au prochain lot quotidien.")
        log.warning("    → ajouter --statut rejected --motif \"…\" pour fermer la porte,")
        log.warning("      ou enchaîner immédiatement le script qui pose le statut.")
        log.warning("")

    if not args.apply:
        log.info("DRY-RUN : relance avec --apply pour agir.")
        conn.close()
        return 0
    if retenues and not args.statut:
        log.error("REFUS — %d fiche(s) retenues sans --statut : voir l'avertissement "
                  "ci-dessus. Relance avec --statut rejected, ou avec --force-sans-statut "
                  "si tu republies volontairement ailleurs.", len(retenues))
        conn.close()
        return 2

    if not all([wp_url, auth[0], auth[1]]):
        log.error("WP_AS_URL/USER/APP_PASSWORD manquants — impossible d'agir.")
        conn.close()
        return 1

    ok = fail = 0
    for i, r in enumerate(targets, 1):
        if trash_one(wp_url, auth, r["wp_post_id_as"], force=True):
            champs = ["wp_post_id_as=NULL", "published_as_date=NULL"]
            params: list = []
            if args.statut:
                champs.append("statut=?")
                params.append(args.statut)
                if args.motif.strip():
                    champs.append("llm_justification=?")
                    params.append(args.motif.strip())
            params.append(r["id"])
            conn.execute(f"UPDATE events_raw SET {', '.join(champs)} WHERE id=?", params)
            conn.commit()
            ok += 1
            log.info("  ✓ id=%s WP#%s corbeillé.", r["id"], r["wp_post_id_as"])
        else:
            fail += 1
        if args.delay and i < len(targets):
            time.sleep(args.delay)

    conn.close()
    log.info("=== %d corbeillé(s), %d échec(s) ===", ok, fail)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
