#!/usr/bin/env python3
"""QUEL PLANCHER pour « Ça vaut le déplacement » ? — le tableau avant la décision.

POURQUOI CE SCRIPT EXISTE. Le seuil d'entrée de la section (`DEPLACEMENT_MIN`) a été posé
à 3 sur 8 le 2026-08-03, au jugé, faute de savoir ce que valait le stock. Franck a
constaté le soir même, en regardant la home, que la section affichait « au diapason » —
non pas parce qu'il vaut le déplacement, mais parce qu'il lui suffisait de ne pas être
nul pour occuper la carte de la Savoie.

Le relever se décide sur un chiffre, pas sur une impression. Or ce chiffre a une forme
particulière ici, et c'est tout l'objet de ce script : **la section affiche UN événement
par territoire** (choix de Franck, confirmé le 2026-08-03). La question n'est donc pas
« combien de fiches restent au-dessus du seuil ? » mais **« chaque territoire a-t-il
encore une carte ? »**. Un plancher qui laisse 40 fiches dont zéro en Vallée d'Aoste vide
une colonne de la home — et c'est exactement le genre d'effet qu'un total global masque.

CE QU'IL COMPTE, ET CE QU'IL ÉCARTE. Uniquement ce qui est encore devant nous (règle 5) :
événements à venir, en cours (`date_event_end` décide, jamais `date_event_start` seule) et
récurrents. Compter le passé gonflerait chaque colonne d'un stock qui n'a aucune chance de
s'afficher, et ferait croire un seuil tenable alors qu'il ne l'est pas.

Il applique aussi l'HORIZON (`HORIZON_JOURS`), sans quoi le tableau promettrait des cartes
que la section refuse déjà.

AUCUNE ÉCRITURE — lecture seule, base ouverte en mode ro, aucun appel réseau, aucun LLM.

Usage :
    .venv/bin/python -m scripts.audit_deplacement
    .venv/bin/python -m scripts.audit_deplacement > rapports/2026-08-03-plancher.md
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.completeness import is_recurring
from utils.deplacement import (_CRITERES, DEPLACEMENT_MIN, HORIZON_JOURS, MAX_SCORE,
                               deplacement_raisons, deplacement_score)


def _par_territoire(notes: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for lot in notes.values():
        for e in lot:
            out.setdefault(e.get("territoire") or "—", []).append(e)
    return out

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
# TOUS les seuils possibles, pas une sélection. La première version s'arrêtait à 6 — soit
# exactement AVANT la valeur sur laquelle Franck hésitait (« 6 ou 7 »). Un tableau qui
# s'arrête juste avant la question oblige à refaire le calcul à côté, donc à sortir de
# l'outil pour décider, donc à décider sans lui. Les huit lignes ne coûtent rien.
# Barème adopté le 2026-08-04 : plancher à 10/12. Les seuils listés encadrent la décision
# (8 → 81 fiches, 10 → 31, 11 → 18 mais le vivier italien rompt) plutôt que de s'arrêter
# juste avant elle, comme la première version qui montait à 6 quand la question portait
# sur 7.
SEUILS = tuple(range(6, MAX_SCORE + 1))


def _jour(v):
    try:
        return date.fromisoformat(str(v or "").strip()[:10])
    except ValueError:
        return None


def _vivant(ev: dict, auj: date) -> bool:
    """Règle 5 : à venir, en cours, ou récurrent. Une fiche SANS date reste comptée —
    c'est une donnée manquante, pas un événement terminé."""
    if is_recurring(ev):
        return True
    debut, fin = _jour(ev.get("date_event_start")), _jour(ev.get("date_event_end"))
    derniere = fin or debut
    if derniere is None:
        return True
    if derniere < auj:
        return False
    # Horizon : au-delà, la section refuse déjà — l'inclure ici promettrait une carte
    # qui ne s'affichera pas.
    return not (debut and (debut - auj).days > HORIZON_JOURS)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Distribution des notes de déplacement, par territoire.")
    p.add_argument("--exemples", type=int, default=3,
                   help="Nombre d'exemples à montrer par note (défaut 3).")
    args = p.parse_args(argv)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as, 0) > 0 "
        "AND wp_deleted_at IS NULL AND translation_of IS NULL")]
    conn.close()

    auj = date.today()
    vivants = [r for r in rows if _vivant(r, auj)]
    notes: dict[int, list[dict]] = {}
    sans_note = 0
    for ev in vivants:
        n = deplacement_score(ev)
        if n is None:
            sans_note += 1        # « pas mesuré » ≠ 0 : ces fiches ne sont PAS classées
            continue              # dernières, elles sont hors section (utils/deplacement)
        notes.setdefault(n, []).append(ev)

    print(f"# Plancher de « Ça vaut le déplacement » — {auj.isoformat()}\n")
    # « liées à un post » et non « en ligne » : ce script lit la BASE, et un
    # `wp_post_id_as` renseigné survit à une mise à la corbeille (règle 1 — 16 des 123
    # fiches republiées le 2026-08-03 étaient corbeillées alors que la base les croyait
    # publiées). Le décompte reste bon pour arbitrer un plancher ; le mot, lui, ne doit
    # pas affirmer un état du site que personne n'a vérifié ici.
    print(f"{len(rows)} fiche(s) liées à un post WordPress, dont **{len(vivants)} encore "
          f"devant nous** (à venir, en cours, récurrentes — règle 5).")
    print(f"{sans_note} sans note mesurable : hors section quoi qu'on décide, elles ne "
          f"sont pas « nulles » mais « pas mesurées ».\n")
    print(f"Seuil actuel : **{DEPLACEMENT_MIN}** sur {MAX_SCORE}. "
          f"Horizon : {HORIZON_JOURS} jours.\n")

    print("## Combien de fiches à chaque note\n")
    print("| Note | Fiches | Exemples |")
    print("|---:|---:|---|")
    for n in range(MAX_SCORE, -1, -1):
        lot = notes.get(n, [])
        ex = " · ".join((e.get("title") or "")[:34] for e in lot[:args.exemples])
        print(f"| {n} | {len(lot)} | {ex} |")

    # D'OÙ VIENNENT LES POINTS — la question posée par le cas « au diapason » (id 931,
    # Thonon, 3/8) le 2026-08-03. Deux de ses trois points venaient de `notoriete_lieu`,
    # qui note LA SALLE et non l'événement : un concert générique dans une salle connue
    # empoche 2 points, pendant que les deux critères qui disent vraiment « ça vaut le
    # déplacement » — le rayonnement et l'ancrage identitaire — donnaient 1 et 0.
    #
    # Les quatre critères pèsent 1 dans la formule, mais leurs MAXIMA diffèrent (3, 2, 2,
    # 1) : `notoriete_lieu` peut donc à lui seul apporter 3 des 8 points. Le poids réel
    # n'est pas le poids déclaré, et personne ne l'avait mesuré.
    #
    # Ce tableau dit si le cas est isolé ou systémique. On mesure AVANT de repondérer :
    # changer les poids sur un seul exemple, c'est calibrer sur le bruit.
    print("\n## D'où viennent les points (part de chaque critère)\n")
    total_pts = {c: 0 for c in _CRITERES}
    plafonds = {c: 0 for c in _CRITERES}
    for lot in notes.values():
        for e in lot:
            try:
                d = json.loads(e.get("llm_score_detail") or "{}")
            except (ValueError, TypeError):
                continue
            for c in _CRITERES:
                bloc = d.get(c)
                pts = bloc.get("points") if isinstance(bloc, dict) else bloc
                if isinstance(pts, (int, float)):
                    total_pts[c] += int(pts)
                    plafonds[c] = max(plafonds[c], int(pts))
    somme = sum(total_pts.values()) or 1
    print("| Critère | Points donnés | Part du total | Max observé |")
    print("|---|---:|---:|---:|")
    for c in _CRITERES:
        print(f"| `{c}` | {total_pts[c]} | {100 * total_pts[c] / somme:.0f} % | {plafonds[c]} |")
    print("\n> `notoriete_lieu` note LA SALLE, pas l'événement. S'il pèse le plus lourd,\n"
          "> la note récompense la réputation du lieu plutôt que la raison de s'y rendre —\n"
          "> et un plancher plus haut ne corrigerait pas ça, il ne ferait que retenir les\n"
          "> événements des grandes salles. C'est la PONDÉRATION qu'il faudrait revoir.\n")

    # SATURATION EN HAUT — objection soulevée à la première simulation (2026-08-04) : les
    # trois premières du Piémont étaient toutes à 12/12. Un barème qui met plusieurs fiches
    # au maximum ne départage plus rien là où c'est le plus visible, puisque la section
    # n'affiche qu'UNE carte par territoire.
    #
    # Ce n'est pas réparable en ajoutant un critère : un événement vraiment majeur est
    # majeur sur TOUS les critères, c'est même la définition. Ce qui départage alors, c'est
    # le bonus d'urgence de deplacement_now (0-4) — donc l'imminence. Et pour CETTE
    # section-là, c'est défendable : entre deux événements également remarquables, celui
    # pour lequel il faut partir bientôt est celui qui vaut le déplacement MAINTENANT.
    #
    # Reste que ça doit se voir plutôt que se découvrir. Un plafond atteint par la moitié
    # d'un territoire dit que le barème a cessé d'y trier.
    # ⚠️ CORRIGÉ LE 2026-08-04 (revue) : la colonne « À 12/12 » ne répondait pas à la
    # question posée. Ce qui décide la carte d'un territoire, ce n'est pas le plafond
    # ABSOLU du barème, c'est le SOMMET DE SA COLONNE — la section n'affiche qu'un
    # événement par territoire, et elle le prend en haut de ce qu'elle a sous la main.
    # Cas mesuré sur fixture : deux fiches de Savoie à 11/12, aucune à 12 ; la table
    # annonçait « le barème trie encore » alors qu'il ne tranchait plus du tout entre
    # les deux prétendantes. Le plafond absolu reste affiché (il dit si le barème sature
    # globalement), mais la LECTURE se fait désormais sur les ex æquo de tête.
    print("\n### Combien de fiches se disputent la carte du territoire\n")
    print(f"| Territoire | Au sommet de sa colonne | dont à {MAX_SCORE}/{MAX_SCORE} "
          f"| Candidates | Lecture |")
    print("|---|---:|---:|---:|---|")
    for t, lot in sorted(_par_territoire(notes).items()):
        au_max = sum(1 for e in lot if deplacement_score(e) == MAX_SCORE)
        sommet = max((deplacement_score(e) or 0) for e in lot) if lot else 0
        ex_aequo = sum(1 for e in lot if (deplacement_score(e) or 0) == sommet)
        lecture = ("le barème trie encore" if ex_aequo <= 1
                   else f"{ex_aequo} ex æquo à {sommet}/{MAX_SCORE} — c'est l'IMMINENCE "
                        f"qui choisit la carte")
        print(f"| {t} | {ex_aequo} (à {sommet}/{MAX_SCORE}) | {au_max} | {len(lot)} | {lecture} |")


    # LE TABLEAU QUI DÉCIDE. La section affichant UN événement par territoire, un seuil ne
    # se juge pas au total mais à sa colonne la plus pauvre : c'est elle qui se videra.
    print("\n## Ce que chaque plancher laisse, PAR TERRITOIRE\n")
    territoires = sorted({(e.get("territoire") or "—") for e in vivants})
    print("| Plancher | Total | " + " | ".join(territoires) + " |")
    print("|---:|---:|" + "---:|" * len(territoires))
    for s in SEUILS:
        retenus = [e for n, lot in notes.items() if n >= s for e in lot]
        par_t = {t: sum(1 for e in retenus if (e.get("territoire") or "—") == t)
                 for t in territoires}
        alerte = " ⚠️ colonne vide" if any(v == 0 for v in par_t.values()) else ""
        marque = " ← actuel" if s == DEPLACEMENT_MIN else ""
        print(f"| **{s}** | {len(retenus)} | "
              + " | ".join(str(par_t[t]) for t in territoires) + f" |{marque}{alerte}")

    print("\n> Un zéro dans une colonne = cette carte de la home reste VIDE. C'est le seul\n"
          "> chiffre qui compte ici : le total global peut rester confortable pendant qu'un\n"
          "> territoire disparaît de la section.\n")

    # LE VIVIER ITALIEN, plus étroit que tous les autres — et c'est lui qui casse en
    # premier. La home italienne ne puise que dans les fiches TRADUITES, or seules
    # Savoie et Comté de Nice le sont. Un plancher qui laisse 30 fiches au total peut
    # n'en laisser que deux de ce côté-là : le tableau ci-dessus, lu par colonne, ne le
    # montre pas, parce qu'il compte les fiches françaises. Constat du 2026-08-03, en
    # arbitrant entre 6 et 7.
    IT = ("Savoie", "Nice")
    print("## Le versant ITALIEN, qui casse en premier\n")
    print("La home italienne ne puise que dans les fiches traduites — Savoie et Comté de "
          "Nice.\nDeux places à remplir, et ce vivier-là seul pour les remplir.\n")
    print("| Plancher | Candidates traduisibles (Savoie + Nice) |")
    print("|---:|---:|")
    for s in SEUILS:
        n = sum(1 for note, lot in notes.items() if note >= s
                for e in lot if any(t in (e.get("territoire") or "") for t in IT))
        alerte = "  ⚠️ moins de 2 par place" if n < 4 else ""
        print(f"| **{s}** | {n} |{alerte}")
    print("\n> Sous quatre candidates, il n'y a plus de marge : deux arrivent à terme et la\n"
          "> section italienne se vide. Plus d'exigence se gagne alors en TRADUISANT et en\n"
          "> ÉVALUANT davantage, pas en relevant le plancher.\n")

    # Ce qu'on perdrait en montant d'un cran — nommément, pas en volume.
    perdus = [e for n, lot in notes.items()
              if DEPLACEMENT_MIN <= n < max(SEUILS) for e in lot]
    if perdus:
        print(f"## Les {len(perdus)} fiche(s) entre {DEPLACEMENT_MIN} et {max(SEUILS) - 1}\n")
        print("Ce sont elles qui sortiraient. Lire quelques justifications vaut mieux que "
              "lire un total — c'est là qu'on voit si le score dit vrai.\n")
        for e in sorted(perdus, key=lambda x: deplacement_score(x) or 0,
                        reverse=True)[:20]:
            n = deplacement_score(e)
            # /{MAX_SCORE} et non « /8 » écrit en dur : le barème est passé de 0-8 à 0-12
            # le 2026-08-04 et cette ligne affichait « 11/8 » — une note au-dessus de son
            # propre dénominateur, dans le tableau même qui sert à décider du plancher.
            print(f"- **{n}/{MAX_SCORE}** · {(e.get('territoire') or '—')} · "
                  f"{(e.get('title') or '')[:60]}")
            for r in deplacement_raisons(e.get("llm_score_detail"))[:2]:
                print(f"    - {r[:118]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
