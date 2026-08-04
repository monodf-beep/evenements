#!/usr/bin/env python3
"""RETIRER UNE SOURCE ET TOUT CE QU'ELLE A PRODUIT — réversiblement.

LA DÉCISION QUI L'A FAIT ÉCRIRE (Franck, 2026-08-04) : « agendaculturel.fr, on supprime
cette source et les fiches en lien. »

CE QUI L'A MOTIVÉE. Le domaine répond **403 à ce serveur sur tous ses sous-domaines**
(`06.`, `73.`, `74.`, `www.`), racine comprise, avec ou sans user-agent de navigateur.
338 fiches en viennent, dont **242 encore devant nous** et 207 sans date. Or dates, lieux,
descriptions et complétion se réparent tous en RELISANT la page d'origine : ces 242 fiches
ne pourront donc jamais être complétées, et chaque cron réessaiera indéfiniment, une fiche
à la fois, sans que la panne commune soit nommée (cf. `scripts/audit_sources_bloquees`).
Une source qu'on ne peut plus lire n'est plus une source.

« SUPPRIMER » SE LIT ICI COMME « RETIRER », et la nuance n'est pas un adoucissement : rien
n'est effacé de la base. `DELETE FROM` est interdit par CLAUDE.md, et pour une bonne
raison — une re-classification se défait, une ligne supprimée non. Concrètement :

  • fiche EN LIGNE  → post mis à la CORBEILLE WordPress (restaurable en un clic, route
    maison `cs/v1/trash`, jamais `force=true` sur `wp/v2/…`) puis `statut='rejected'` ;
  • fiche hors ligne → `statut='rejected'` seulement.

Le lien `wp_post_id_as` est CONSERVÉ : un post corbeillé se restaure, couper le lien
détruirait l'information qui permet de revenir en arrière. C'est la même asymétrie
qu'assume `reconcile_wp_deleted`, et pour le même motif.

CE QU'IL NE FAIT PAS. Il ne touche pas `config/sources.txt` : retirer la ligne de collecte
est un geste séparé, à faire une fois, et le mélanger ici ferait qu'un dry-run laisserait
croire que plus rien n'arrive alors que le scraper continuerait le lendemain.

Il ne distingue pas non plus passé et à-venir. La règle 5 dit de ne pas FABRIQUER du
travail sur le passé ; ici on n'en fabrique pas — on ferme un robinet, et laisser derrière
soi une moitié de stock traitée serait un état bâtard que personne ne saurait relire.

Usage :
    .venv/bin/python -m scripts.retirer_source agendaculturel.fr
    .venv/bin/python -m scripts.retirer_source agendaculturel.fr --apply
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("retirer-source")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _racine(hote: str) -> str:
    bouts = (hote or "").lower().split(".")
    return ".".join(bouts[-2:]) if len(bouts) > 2 else (hote or "").lower()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Retire une source et rejette ses fiches.")
    p.add_argument("domaine", help="Domaine racine, ex. agendaculturel.fr")
    p.add_argument("--apply", action="store_true", help="Écrit (sinon dry-run).")
    args = p.parse_args(argv)
    cible = _racine(args.domaine)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE url_source LIKE 'http%'")]
    concernees = [r for r in rows
                  if _racine(urlparse(r["url_source"]).hostname or "") == cible]
    deja = [r for r in concernees if (r.get("statut") or "") == "rejected"]
    a_faire = [r for r in concernees if r not in deja]
    en_ligne = [r for r in a_faire if (r.get("wp_post_id_as") or 0) > 0]
    auj = date.today().isoformat()
    devant = [r for r in a_faire
              if not (r.get("date_event_end") or r.get("date_event_start") or "")[:10]
              or (r.get("date_event_end") or r.get("date_event_start") or "")[:10] >= auj]

    print(f"\nSource « {cible} » — {len(concernees)} fiche(s) au total.")
    print(f"  {len(deja)} déjà rejetée(s), rien à y faire.")
    print(f"  {len(a_faire)} à rejeter, dont {len(devant)} encore devant nous "
          f"et {len(en_ligne)} EN LIGNE (à corbeiller).\n")
    for r in en_ligne[:20]:
        d = (r.get("date_event_end") or r.get("date_event_start") or "—")[:10]
        print(f"  WP#{r['wp_post_id_as']:<6} [{r['id']:>5}] {d}  {(r.get('title') or '')[:52]}")
    if len(en_ligne) > 20:
        print(f"  … {len(en_ligne) - 20} autre(s) en ligne.")

    if not args.apply:
        print(f"\nDry-run — rien n'a été écrit. Ajouter --apply.")
        print(f"⚠️  Penser AUSSI à retirer les lignes « {cible} » de config/sources.txt : "
              f"sans ça,\n    le scraper en ramènera de nouvelles demain matin.\n")
        conn.close()
        return 0

    load_dotenv(ROOT / ".env")
    wp_url = (os.getenv("WP_AS_URL", "") or "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    corbeillees, echecs = 0, []
    if en_ligne:
        if not all([wp_url, auth[0], auth[1]]):
            log.error("Identifiants WordPress absents — aucune corbeille possible.")
            echecs = [r["id"] for r in en_ligne]
        else:
            from scripts.cleanup_as_trash import trash_one
            for r in en_ligne:
                # force=True : route MAISON cs/v1/trash — autorise la corbeille sur un post
                # déjà publié. Rien à voir avec le `force=true` de wp/v2 (suppression
                # définitive), qui est interdit. Ce chemin-ci est réversible en un clic.
                if trash_one(wp_url, auth, int(r["wp_post_id_as"]), force=True):
                    corbeillees += 1
                else:
                    echecs.append(r["id"])

    quand = datetime.now().isoformat(timespec="seconds")
    for r in a_faire:
        conn.execute("UPDATE events_raw SET statut='rejected' WHERE id=?", (r["id"],))
    conn.commit()

    # RECOMPTER EN BASE (règle 6) plutôt qu'annoncer la longueur d'une liste.
    ids = [r["id"] for r in a_faire]
    faites = 0
    if ids:
        m = ",".join("?" * len(ids))
        faites = conn.execute(f"SELECT COUNT(*) FROM events_raw WHERE id IN ({m}) "
                              f"AND statut='rejected'", ids).fetchone()[0]
    conn.close()

    print(f"\n✅ {faites}/{len(a_faire)} fiche(s) rejetée(s), {corbeillees}/{len(en_ligne)} "
          f"post(s) mis à la corbeille.")
    if echecs:
        print(f"⚠️  {len(echecs)} corbeille(s) en échec : {echecs[:12]}"
              + (" …" if len(echecs) > 12 else "")
              + "\n    Leur statut est quand même passé à 'rejected' — les posts sont "
                "donc encore\n    EN LIGNE alors que la base les écarte. À reprendre "
                "(scripts/trash_wp_ids).")
    print(f"\n⚠️  Retirer maintenant les lignes « {cible} » de config/sources.txt, sinon "
          f"le scraper\n    en ramènera de nouvelles demain matin. Rien ici ne le fait — "
          f"c'est volontaire.\n")
    log.info("Source %s retirée : %d rejetée(s), %d corbeillée(s), %d échec(s) le %s",
             cible, faites, corbeillees, len(echecs), quand)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
