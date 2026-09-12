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

CE QUI REND LE RETRAIT RÉVERSIBLE POUR DE BON (ajouté le 2026-08-04, après revue). Dire
« rien n'est effacé » ne suffisait pas : `statut='rejected'` écrasait 'evaluated',
'published_sub' ou 'pending' sans les noter, et plus rien ne disait laquelle était
laquelle. Le statut d'avant est donc empilé dans `unmerge_data` — le même magasin que
dedupe —, et `--annuler` le repose. Qui rouvre ? Cette option-là, nommément (règle 3).

Usage :
    .venv/bin/python -m scripts.retirer_source agendaculturel.fr
    .venv/bin/python -m scripts.retirer_source agendaculturel.fr --apply
    .venv/bin/python -m scripts.retirer_source agendaculturel.fr --annuler          # dry-run
    .venv/bin/python -m scripts.retirer_source agendaculturel.fr --annuler --apply
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.dedupe import _empile, ensure_unmerge_column
from utils.logger import get_logger

log = get_logger("retirer-source")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
# Rôle de l'instantané empilé dans `unmerge_data` (le même magasin que dedupe et
# resolve_wp_collision ; `unmerge.py` ne lit que 'perdant'/'gagnant', aucun croisement).
ROLE = "source_retiree"


def _racine(hote: str) -> str:
    """Domaine racine, sous-domaines repliés dessus (agendaculturel.fr sert depuis `06.`,
    `73.`, `74.` et `www.`). Deux étiquettes : suffisant pour du .fr et du .it, qui sont
    tout ce que couvre cet agenda — un `.co.uk` serait mal replié, et le repli s'applique
    AUSSI à l'argument de la ligne de commande."""
    bouts = (hote or "").lower().split(".")
    return ".".join(bouts[-2:]) if len(bouts) > 2 else (hote or "").lower()


def _statut_avant(row: dict, cible: str) -> str | None:
    """Le statut d'avant retrait, lu dans la pile `unmerge_data` — le plus récent pour ce
    domaine. Rien si la fiche n'a pas été retirée par ce script."""
    try:
        pile = json.loads(row.get("unmerge_data") or "[]")
    except (ValueError, TypeError):
        return None
    if not isinstance(pile, list):
        return None
    for e in reversed(pile):
        if (isinstance(e, dict) and e.get("role") == ROLE and e.get("domaine") == cible
                and e.get("statut_avant")):
            return str(e["statut_avant"])
    return None


def _annuler(conn: sqlite3.Connection, cible: str, concernees: list[dict],
             apply: bool) -> int:
    """LE CHEMIN DE RETOUR, sans lequel le mot « réversiblement » du titre était creux.

    AJOUTÉ LE 2026-08-04 (revue) : la première version écrasait `statut` sans le noter
    nulle part. Mesuré sur fixture — trois fiches en 'evaluated', 'published_sub' et
    'pending' ressortaient toutes en 'rejected', et plus rien en base ne disait laquelle
    était laquelle. `unreject_wp_online` ne rattrape pas ce cas : il exige que le post soit
    PUBLIC (or ce script vient de le corbeiller) et il repose un statut par DÉFAUT, donc il
    inventerait « publiée » une fiche qui n'était que 'pending'. C'était donc, en pratique,
    une opération de masse irréversible présentée comme réversible — exactement ce que la
    règle 3 interdit d'ajouter.

    Ce qu'il ne fait pas : ressortir les posts de la corbeille WordPress. C'est un clic
    dans l'admin, et surtout un geste dont un script ne peut pas décider à la place d'un
    humain. Les numéros sont donc imprimés.

    ⚠️ ET LA RESTAURATION WORDPRESS NE REND PAS UN POST « EN LIGNE » — constaté en
    production le 2026-08-04 sur WP#2211 : sortir un post de la corbeille le rend en
    `draft`, jamais en `publish`. Un `--annuler` qui annoncerait « tout est remis en ligne »
    mentirait donc deux fois : le statut en base serait restauré, le post resterait
    invisible du public, et la base croirait le contraire — exactement l'incohérence que ce
    dépôt passe ses journées à réparer. D'où l'énumération des numéros plutôt qu'une
    promesse : ce qui reste à faire est nommé, et il reste à faire."""
    restaurables = [(r, s) for r in concernees
                    if (r.get("statut") or "") == "rejected"
                    and (s := _statut_avant(r, cible))]
    print(f"\nAnnulation du retrait de « {cible} » — {len(restaurables)} fiche(s) "
          f"restaurable(s) sur {len(concernees)}.")
    if not restaurables:
        print("  Aucun instantané pour ce domaine : soit le retrait est antérieur au "
              "2026-08-04,\n  soit il n'a jamais eu lieu. Rien à faire ici.\n")
        conn.close()
        return 0
    par_statut: dict[str, int] = {}
    for _r, s in restaurables:
        par_statut[s] = par_statut.get(s, 0) + 1
    print("  vers : " + ", ".join(f"{n}×'{s}'" for s, n in sorted(par_statut.items())))
    posts = [r["wp_post_id_as"] for r, _s in restaurables if (r.get("wp_post_id_as") or 0) > 0]
    if posts:
        print(f"  {len(posts)} post(s) à ressortir de la corbeille À LA MAIN dans "
              f"l'admin WordPress :\n    {posts[:20]}")
    if not apply:
        print("\nDry-run — rien n'a été écrit. Ajouter --apply.\n")
        conn.close()
        return 0
    for r, s in restaurables:
        conn.execute("UPDATE events_raw SET statut=? WHERE id=?", (s, r["id"]))
    conn.commit()
    # RECOMPTER EN BASE (règle 6).
    ids = [r["id"] for r, _s in restaurables]
    m = ",".join("?" * len(ids))
    reste = conn.execute(f"SELECT COUNT(*) FROM events_raw WHERE id IN ({m}) "
                         f"AND statut='rejected'", ids).fetchone()[0]
    conn.close()
    print(f"\n✅ {len(ids) - reste}/{len(ids)} fiche(s) rendues à leur statut d'avant.\n")
    log.info("Retrait de %s annulé : %d/%d restaurées", cible, len(ids) - reste, len(ids))
    return 0


def _reconstituer(conn: sqlite3.Connection, cible: str, concernees: list[dict],
                  sauvegarde: str, apply: bool) -> int:
    """RETROUVER LE STATUT D'AVANT DANS UNE SAUVEGARDE, pour les retraits appliqués AVANT
    que l'instantané n'existe.

    POURQUOI IL FAUT ÇA. `--annuler` lit `unmerge_data`, empilé depuis la revue du
    2026-08-04 au soir. Or le retrait d'`agendaculturel.fr` a été appliqué le même jour à
    14h — **338 fiches passées en 'rejected' sans que rien ne note d'où elles venaient**.
    Elles étaient donc, en pratique, irrécupérables : très exactement le passif que
    `docs/ETATS_TERMINAUX.md` décrit pour les fusions d'avant le 2026-08-03, et qu'on
    venait de refabriquer le jour même en écrivant « réversiblement » dans un titre.

    SAUF QUE CETTE FOIS L'INFORMATION EXISTE ENCORE. `scripts/backup_db.py` copie la base
    chaque nuit à 3h et garde les quatorze dernières ; une sauvegarde manuelle a de plus
    été prise à 10h53. Toutes deux précèdent le retrait : elles portent le statut EXACT des
    338 fiches. On ne devine rien, on relit.

    LE GARDE-FOU QUI COMPTE : on refuse d'enregistrer `statut_avant='rejected'`. C'est le
    signe que la sauvegarde est POSTÉRIEURE au retrait — elle rendrait alors « rejeté » le
    statut qu'on cherche justement à retrouver, et `--annuler` croirait avoir restauré
    quelque chose. Une réversibilité qui repose l'état actuel n'est pas une réversibilité,
    c'est un mensonge poli.

    La sauvegarde est ouverte en LECTURE SEULE et n'est jamais modifiée."""
    src = Path(sauvegarde)
    if not src.exists():
        print("\n⛔ Sauvegarde introuvable : %s" % src)
        print("   Les sauvegardes vivent dans data/backups/events-*.db "
              "(backup_db.py, 3h, 14 gardées).\n")
        return 2
    try:
        vieille = sqlite3.connect("file:%s?mode=ro" % src, uri=True)
        vieille.row_factory = sqlite3.Row
        avant = {int(r["id"]): (r["statut"] or "") for r in
                 vieille.execute("SELECT id, statut FROM events_raw")}
        vieille.close()
    except sqlite3.Error as exc:
        print("\n⛔ Sauvegarde illisible (%s).\n" % exc)
        return 2

    # Seulement les fiches ACTUELLEMENT rejetées et SANS instantané pour ce domaine : on ne
    # recouvre jamais un instantané existant, forcément plus fiable qu'une relecture.
    cand = [r for r in concernees
            if (r.get("statut") or "") == "rejected" and not _statut_avant(r, cible)]
    trouvees, absentes, deja_rejetees = [], 0, 0
    for r in cand:
        st = avant.get(int(r["id"]))
        if st is None:
            absentes += 1                 # créée APRÈS la sauvegarde : rien à retrouver
        elif st == "rejected":
            deja_rejetees += 1            # sauvegarde postérieure, ou rejet antérieur
        else:
            trouvees.append((r, st))

    print("\nReconstitution depuis %s — source « %s »." % (src.name, cible))
    print("  %d fiche(s) rejetée(s) sans instantané." % len(cand))
    print("  %d retrouvée(s) avec un statut d'avant exploitable." % len(trouvees))
    if deja_rejetees:
        print("  %d déjà 'rejected' DANS la sauvegarde — soit elle est postérieure au"
              % deja_rejetees)
        print("    retrait, soit ces fiches étaient rejetées avant. Écartées : les rendre")
        print("    à 'rejected' ne restaurerait rien.")
    if absentes:
        print("  %d absente(s) de la sauvegarde (créées depuis) — rien à retrouver."
              % absentes)
    par_statut: dict[str, int] = {}
    for _r, st in trouvees:
        par_statut[st] = par_statut.get(st, 0) + 1
    if par_statut:
        print("  détail : " + ", ".join("%d×'%s'" % (n, s)
                                        for s, n in sorted(par_statut.items())))

    if not apply:
        print("\nDry-run — rien n'a été écrit. Ajouter --apply pour poser les instantanés,")
        print("puis --annuler pour restaurer.\n")
        conn.close()
        return 0
    if not trouvees:
        conn.close()
        return 0

    quand = datetime.now().isoformat(timespec="seconds")
    for r, st in trouvees:
        _empile(conn, r["id"], {"role": ROLE, "at": quand, "domaine": cible,
                                "statut_avant": st,
                                # PROVENANCE DITE : cet instantané n'a pas été pris au
                                # moment du retrait, il a été relu dans une sauvegarde. La
                                # nuance comptera le jour où quelqu'un se demandera
                                # pourquoi sa date ne colle pas avec celle du retrait.
                                "origine": "sauvegarde %s" % src.name})
    conn.commit()
    # RECOMPTER EN BASE (règle 6) : on relit les instantanés réellement posés.
    ids = [r["id"] for r, _s in trouvees]
    marks = ",".join("?" * len(ids))
    poses = sum(1 for r in conn.execute(
        "SELECT * FROM events_raw WHERE id IN (%s)" % marks, ids)
        if _statut_avant(dict(r), cible))
    conn.close()
    print("\n✅ %d/%d instantané(s) posé(s). `--annuler` peut désormais restaurer "
          "ces fiches.\n" % (poses, len(trouvees)))
    log.info("Reconstitution %s depuis %s : %d/%d", cible, src.name, poses, len(trouvees))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Retire une source et rejette ses fiches.")
    p.add_argument("domaine", help="Domaine racine, ex. agendaculturel.fr")
    p.add_argument("--apply", action="store_true", help="Écrit (sinon dry-run).")
    p.add_argument("--annuler", action="store_true",
                   help="REMET les fiches de ce domaine dans le statut qu'elles avaient "
                        "avant le retrait (lu dans l'instantané).")
    p.add_argument("--reconstituer", metavar="SAUVEGARDE.db",
                   help="Retrouve le statut d'avant dans une sauvegarde de la base et pose "
                        "l'instantané manquant — pour les retraits appliqués AVANT que "
                        "l'instantané n'existe (agendaculturel.fr, 2026-08-04 14h).")
    args = p.parse_args(argv)
    cible = _racine(args.domaine)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_unmerge_column(conn)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE url_source LIKE 'http%'")]
    concernees = [r for r in rows
                  if _racine(urlparse(r["url_source"]).hostname or "") == cible]

    if args.reconstituer:
        return _reconstituer(conn, cible, concernees, args.reconstituer, args.apply)
    if args.annuler:
        return _annuler(conn, cible, concernees, args.apply)
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
        # L'INSTANTANÉ D'ABORD, comme dedupe et resolve_wp_collision. Sans lui, 'evaluated',
        # 'published_sub' et 'pending' deviennent trois fois 'rejected' et rien ne dit plus
        # laquelle était laquelle : le retrait serait irréversible malgré le titre de ce
        # script. Une ligne ici, contre un statut perdu pour des centaines de fiches.
        _empile(conn, r["id"], {"role": ROLE, "at": quand, "origine": "retirer_source",
                                "domaine": cible, "statut_avant": r.get("statut"),
                                "wp_post_id_as": r.get("wp_post_id_as")})
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
