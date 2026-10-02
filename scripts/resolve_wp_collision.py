#!/usr/bin/env python3
"""DEUX FICHES POUR UNE SEULE PAGE — trancher, et rendre le post à la bonne.

LE TROU QU'IL COMBLE, et il est structurel. `audit_wp_ghosts` sait DÉTECTER qu'un post
est revendiqué par plusieurs lignes locales, et depuis le 2026-08-03 il sait NOMMER le
cas. Mais pour le troisième cas — deux fiches sans lien de parenté — il renvoyait vers
`relink_wp_ids_as`, qui **ne peut pas le voir** : ce script valide chaque ligne locale par
le titre du post qu'elle vise, donc il regarde `ligne → post` et jamais `post → lignes`.
Les deux prétendantes portent le même titre que le post ; chacune, prise isolément, est
« déjà bonne ». Un doublon de lien lui est invisible par construction — vérifié le
2026-08-03 sur WP#6365, dont son dry-run ne mentionne ni le post ni aucune des deux
fiches.

Résultat : le problème était vu, décrit, et personne ne pouvait le refermer. C'est le
motif de `docs/ETATS_TERMINAUX.md` sous sa forme la plus coûteuse — un diagnostic sans
issue, qu'on relit chaque semaine sans jamais rien pouvoir en faire.

LE DOMMAGE EST RÉEL, pas théorique. Sur WP#6365 « Percorso in Rosso 2026 » (Saint-Rhémy-
en-Bosses, 13 août), les deux lignes ont été poussées vers le même post à trois secondes
d'intervalle. La dernière a gagné — et c'était la MOINS complète : le post porte son
score de 4 et n'a pas d'`article_title`, tandis que la fiche mieux notée (5) et pourvue
de son titre d'article a été écrasée. La dernière arrivée gagne, pas la meilleure.

CE QU'IL FAIT. Pour chaque post revendiqué plusieurs fois, il compare les prétendantes
sur des critères OBSERVABLES (article rédigé, lieu, dates, score, richesse du texte),
garde la plus complète, et pour les autres :
  • efface `wp_post_id_as` — elles ne pilotent plus rien ;
  • les passe `merged` + `duplicate_of` vers la gagnante — c'est bien ce qu'elles sont ;
  • enregistre leur statut d'avant dans `unmerge_data`, pour que `scripts/unmerge.py`
    puisse défaire. Poser un `merged` SANS instantané reproduirait exactement le
    cul-de-sac fermé le matin même — un état terminal se crée en une ligne d'inattention.
Il ne touche AUCUN champ de la gagnante : agréger la matière est le geste qui a détruit
des descriptions légitimes (cf. `repair_polluted_descriptions`). Ici on répare un LIEN,
rien d'autre. Le post, lui, n'est jamais ni corbeillé ni supprimé — il change de
propriétaire, c'est tout.

CE QU'IL REFUSE DE TRANCHER, et c'est le plus important :
  • quand les deux fiches ont des DATES INCOMPATIBLES, ce ne sont pas deux copies d'un
    même événement mais deux événements différents poussés sur la même page — cas plus
    grave, qui demande de republier l'un ailleurs ;
  • quand les scores de complétude sont ÉGAUX, il n'y a pas de raison observable de
    préférer l'une. Départager à pile ou face une fiche publiée serait pire que ne rien
    faire.
Dans les deux cas il le dit et passe. `--forcer <id>` permet de désigner la gagnante à la
main, une fois qu'un humain a regardé — et il agit VRAIMENT sur les deux (vérifié sur
fixture le 2026-08-04 : il ne pouvait rien sur le refus « dates incompatibles », qui était
testé avant lui, et il était silencieusement ignoré quand l'id ne revendiquait aucun des
posts sélectionnés ; le script tranchait alors tout seul en affichant « la plus complète »,
et l'humain lisait comme sienne une décision qui ne l'était pas). Deux garde-fous depuis :

  • un `--forcer` qui ne désigne aucune prétendante ARRÊTE le script (rien n'est écrit) ;
  • quand il tranche un cas de DATES INCOMPATIBLES, les autres fiches sont simplement
    DÉTACHÉES — lien coupé, statut conservé — et jamais marquées 'merged'. Deux
    événements différents ne sont pas des doublons ; les déclarer tels écrirait une
    parenté fausse en base. Détachées, elles repartent d'elles-mêmes sur un post neuf au
    prochain `publish_batch_as`.

Usage :
    .venv/bin/python -m scripts.resolve_wp_collision                    # dry-run, tous
    .venv/bin/python -m scripts.resolve_wp_collision --apply
    .venv/bin/python -m scripts.resolve_wp_collision --posts 6365 --apply
    .venv/bin/python -m scripts.resolve_wp_collision --posts 6365 --forcer 3995 --apply
    .venv/bin/python -m scripts.resolve_wp_collision --posts 6365 --apply --republier
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.dedupe import _empile, ensure_unmerge_column
from utils.logger import get_logger

log = get_logger("resolve-wp-collision")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Ce qui fait qu'une fiche mérite de piloter la page, par ordre d'importance. Des signaux
# OBSERVABLES uniquement : on ne demande pas à un LLM de préférer une fiche à une autre,
# la question se tranche sur ce qui est rempli ou vide.
def _completude(ev: dict) -> tuple[int, ...]:
    """Clé de comparaison, du plus décisif au moins décisif. Comparée telle quelle : le
    premier critère qui départage l'emporte, et on n'additionne pas des choses qui ne
    s'additionnent pas."""
    return (
        1 if (ev.get("article_title") or "").strip() else 0,   # l'article a été rédigé
        1 if (ev.get("article_md") or "").strip() else 0,
        1 if (ev.get("lieu") or "").strip() else 0,
        1 if (ev.get("date_event_start") or "").strip() else 0,
        int(ev.get("user_score") or ev.get("llm_score") or 0),
        len((ev.get("description") or "")),                    # à défaut, la plus fournie
    )


def _jour(v):
    try:
        return date.fromisoformat(str(v or "").strip()[:10])
    except ValueError:
        return None


def _dates_incompatibles(lignes: list[dict]) -> bool:
    """Deux fiches datées de jours différents ne sont pas deux copies : ce sont deux
    ÉVÉNEMENTS que l'on a poussés sur la même page. Fusionner les effacerait — c'est
    précisément le geste qui a produit WP#6798 (un titre, et les dates d'un autre)."""
    jours = {d for d in (_jour(e.get("date_event_start")) for e in lignes) if d}
    return len(jours) > 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Rend un post WordPress revendiqué par plusieurs fiches à la plus complète.")
    p.add_argument("--apply", action="store_true", help="Écrit (sinon dry-run).")
    p.add_argument("--posts", nargs="*", type=int, help="Restreint à ces posts WordPress.")
    p.add_argument("--forcer", type=int,
                   help="Id LOCAL de la gagnante, quand un humain a tranché lui-même.")
    p.add_argument("--republier", action="store_true",
                   help="Republie la gagnante après coup, pour que la page porte enfin "
                        "SES données (le post garde sinon celles de la perdante).")
    args = p.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_unmerge_column(conn)

    # L'INDEX INVERSE, post → lignes. C'est lui qui manquait : tout le dépôt indexe dans
    # l'autre sens, et c'est pour ça que le doublon de lien n'était vu par aucun outil.
    par_post: dict[int, list[dict]] = {}
    for r in conn.execute("SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as, 0) > 0"):
        ev = dict(r)
        par_post.setdefault(int(ev["wp_post_id_as"]), []).append(ev)

    collisions = {w: l for w, l in par_post.items() if len(l) > 1}
    if args.posts:
        collisions = {w: l for w, l in collisions.items() if w in set(args.posts)}

    # --forcer DOIT ÊTRE HONORÉ OU REFUSÉ, jamais avalé. Vérifié sur fixture le 2026-08-04
    # (revue) : `--posts 6365 --forcer 3` où 3 ne revendique pas ce post produisait
    # exactement la même sortie que sans l'option — le script tranchait tout seul et
    # écrivait « la plus complète ». Un humain qui croit avoir arbitré lit une décision
    # qui n'est pas la sienne, et sur --apply c'est l'autre fiche qui part en 'merged'.
    if args.forcer is not None and not any(
            e["id"] == args.forcer for lignes in collisions.values() for e in lignes):
        print(f"\n⛔ --forcer {args.forcer} : cet id ne revendique aucun des posts "
              f"sélectionnés.\n"
              f"   Rien n'a été fait — relire le dry-run et reprendre l'id de la fiche "
              f"à garder.\n")
        conn.close()
        return 1

    plan, refus = [], []
    for wp, lignes in sorted(collisions.items()):
        force_ici = args.forcer is not None and any(e["id"] == args.forcer for e in lignes)
        if _dates_incompatibles(lignes) and not force_ici:
            # ⚠️ « and not force_ici » AJOUTÉ LE 2026-08-04 (revue). Le docstring annonce
            # --forcer comme l'issue des DEUX refus ; or ce test passait avant lui, donc
            # sur le cas le plus grave — deux événements différents sur une même page —
            # l'option ne pouvait rien. Un refus dont l'issue documentée ne fonctionne pas
            # est un cul-de-sac (règle 3), et il était ici invisible : la sortie affichait
            # le refus habituel, sans un mot sur le --forcer ignoré.
            refus.append((wp, lignes, "dates INCOMPATIBLES — deux événements différents sur "
                                      "une même page, pas deux copies"))
            continue
        classees = sorted(lignes, key=_completude, reverse=True)
        # DEUX ÉVÉNEMENTS DIFFÉRENTS NE SONT PAS DES DOUBLONS, même quand un humain a
        # tranché à qui revient la page. Les marquer 'merged' + duplicate_of écrirait en
        # base une parenté qui n'existe pas — c'est la fusion abusive qui a donné à
        # WP#6798 la date d'un autre événement (règle 5, seconde précaution). On se
        # contente donc de DÉTACHER la perdante : lien coupé, statut intact. Elle
        # redevient éligible pour publish_batch_as (`statut IN (evaluated, published_cs,
        # published_sub) AND wp_post_id_as = 0`) et se republie d'elle-même sur un post
        # NEUF au lot suivant — c'est littéralement le « republier l'un ailleurs » que le
        # docstring réclame, fait par le pipeline normal plutôt qu'à la main.
        detacher_seulement = force_ici and _dates_incompatibles(lignes)
        if force_ici:
            gagnante = next(e for e in lignes if e["id"] == args.forcer)
            motif = ("désignée à la main (--forcer) — dates incompatibles, les autres sont "
                     "DÉTACHÉES et non fusionnées" if detacher_seulement
                     else "désignée à la main (--forcer)")
        else:
            if _completude(classees[0]) == _completude(classees[1]):
                refus.append((wp, lignes, "complétude ÉGALE — aucune raison observable de "
                                          "préférer l'une ; trancher à l'aveugle serait pire"))
                continue
            gagnante = classees[0]
            motif = "la plus complète"
            detacher_seulement = False
        plan.append({"wp": wp, "gagnante": gagnante,
                     "perdantes": [e for e in lignes if e["id"] != gagnante["id"]],
                     "motif": motif, "detacher": detacher_seulement})

    print(f"\n{len(collisions)} post(s) revendiqué(s) par plusieurs fiches · "
          f"{len(plan)} tranché(s), {len(refus)} laissé(s) à un humain.\n")
    for c in plan:
        g = c["gagnante"]
        print(f"  WP#{c['wp']:<6} → garde [{g['id']}] « {(g.get('title') or '')[:44]} » "
              f"({c['motif']})")
        for e in c["perdantes"]:
            if c["detacher"]:
                print(f"                détache [{e['id']}] — lien coupé, statut "
                      f"'{e.get('statut')}' CONSERVÉ : se republiera sur un post neuf")
            else:
                print(f"                détache [{e['id']}] statut '{e.get('statut')}' → "
                      f"'merged', duplicate_of={g['id']}")
    for wp, lignes, motif in refus:
        ids = ", ".join(f"{e['id']}({e.get('date_event_start') or '—'})" for e in lignes)
        print(f"  ⛔ WP#{wp:<6} {motif}\n                ids : {ids}")

    if not args.apply:
        print("\nDry-run — rien n'a été écrit. Ajouter --apply pour appliquer.\n")
        conn.close()
        return 0

    quand = datetime.now().isoformat(timespec="seconds")
    for c in plan:
        for e in c["perdantes"]:
            # L'INSTANTANÉ D'ABORD. Poser 'merged' sans lui recréerait, en une ligne, le
            # cul-de-sac fermé le matin même : `unmerge` n'aurait plus rien à restaurer et
            # devrait renvoyer la fiche à l'évaluation, donc re-payer un appel LLM.
            _empile(conn, e["id"], {
                "role": "perdant", "at": quand, "statut_avant": e.get("statut"),
                "origine": "resolve_wp_collision",
                "wp_post_id_as_avant": e.get("wp_post_id_as"), "gagnant": c["gagnante"]["id"],
                "detachee_seulement": bool(c["detacher"])})
            if c["detacher"]:
                # Dates incompatibles tranchées à la main : on coupe le lien et on ne
                # touche à RIEN d'autre. Le statut conservé est ce qui la fait repartir.
                conn.execute("UPDATE events_raw SET wp_post_id_as=NULL, "
                             "wp_permalink_as=NULL WHERE id=?", (e["id"],))
            else:
                conn.execute("UPDATE events_raw SET wp_post_id_as=NULL, wp_permalink_as=NULL, "
                             "statut='merged', duplicate_of=? WHERE id=?",
                             (c["gagnante"]["id"], e["id"]))
    conn.commit()

    republiees = 0
    if args.republier and plan:
        from scripts.publisher_as import publish_to_as
        for c in plan:
            # Sans ça, la page continue d'afficher les données de la perdante : c'est elle
            # qui a écrit en dernier, c'est pour ça qu'elle a « gagné » le post.
            ev = dict(conn.execute("SELECT * FROM events_raw WHERE id=?",
                                   (c["gagnante"]["id"],)).fetchone())
            if publish_to_as(ev, skip_media=True)[0]:
                republiees += 1

    # RECOMPTER EN BASE (règle 6) : on relit l'index inverse au lieu d'annoncer le plan.
    reste = {}
    for r in conn.execute("SELECT wp_post_id_as, COUNT(*) n FROM events_raw "
                          "WHERE COALESCE(wp_post_id_as, 0) > 0 GROUP BY wp_post_id_as "
                          "HAVING n > 1"):
        reste[int(r[0])] = int(r[1])
    conn.close()

    traites = len(plan) - sum(1 for c in plan if c["wp"] in reste)
    print(f"\n✅ {traites}/{len(plan)} post(s) rendu(s) à une seule fiche"
          + (f", {republiees} republiée(s)." if args.republier else "."))
    if reste:
        print(f"   {len(reste)} collision(s) restante(s) : {sorted(reste)[:12]}"
              + (" …" if len(reste) > 12 else ""))
    if refus:
        print(f"   ⛔ {len(refus)} laissée(s) à un humain — relire les motifs ci-dessus.")
    if not args.republier:
        print("   ⚠️  Les pages portent encore les données des PERDANTES (elles avaient "
              "écrit en dernier).\n      Relancer avec --republier pour les remettre à jour.")
    log.info("Collisions : %d/%d rendues, %d refusées, %d republiées le %s",
             traites, len(plan), len(refus), republiees, quand)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
