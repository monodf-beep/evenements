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
from utils.deplacement import (_CRITERES, DEPLACEMENT_MIN, HORIZON_JOURS, LANGUE_MAX,
                               MAX_SCORE, accessibilite_langue, deplacement_raisons,
                               deplacement_score)

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
# TOUS les seuils possibles, pas une sélection. La première version s'arrêtait à 6 — soit
# exactement AVANT la valeur sur laquelle Franck hésitait (« 6 ou 7 »). Un tableau qui
# s'arrête juste avant la question oblige à refaire le calcul à côté, donc à sortir de
# l'outil pour décider, donc à décider sans lui. Les huit lignes ne coûtent rien.
SEUILS = tuple(range(3, 9))


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


# PONDÉRATION PROPOSÉE — pas appliquée, seulement simulée (--simuler).
#
# CE QU'ELLE CORRIGE. La mesure du 2026-08-03 sur le stock réel : `notoriete_lieu` pèse
# 44 % des points distribués, contre 24 % au rayonnement et 13 % à la spécificité. Le
# critère qui note LA SALLE pèse donc plus lourd que les deux qui disent pourquoi on se
# déplacerait — et l'exemple le montre crûment : « Visite guidée du Stade Allianz Riviera »
# obtient 6/8, dont 3 points pour le stade emblématique. Une visite de stade au même rang
# qu'un festival international.
#
# LE PRINCIPE : ce qui fait qu'on FAIT LA ROUTE, c'est de ne pas pouvoir le voir ailleurs
# (spécificité) et que ça dépasse le voisinage (rayonnement). La salle compte — le Castello
# di Rivoli est une destination — mais elle ne doit plus pouvoir porter une fiche à elle
# seule. D'où un plafond à 1 point : « lieu remarquable, oui ou non », plutôt qu'une échelle
# qui lui donne trois fois le poids de l'ancrage identitaire.
#
# Échelle 0-12 et non 0-8 : le plancher se re-décide alors forcément — le garder à 6 par
# inertie appliquerait une exigence différente sans qu'on s'en aperçoive (6/8 vaut 75 %,
# 6/12 en vaut 50).
#
# ET UN CINQUIÈME CRITÈRE, LA BARRIÈRE DE LA LANGUE (Franck, 2026-08-03) : sur un agenda
# transfrontalier, `rayonnement` dit que l'événement porte au-delà de la frontière, jamais
# qu'un visiteur d'en face pourra en profiter. Une pièce de théâtre en italien rayonne
# autant qu'une foire gastronomique et vaut infiniment moins le déplacement à un
# francophone. Dérivé de la catégorie (utils/deplacement.accessibilite_langue) : gratuit,
# rétroactif sur tout le stock, auditable — et il ne chasse RIEN du site, il ne joue que
# sur le classement de cette section.
PONDERATION_PROPOSEE = {
    "rayonnement":              (2, None),   # 0-2 ×2 → 0-4  (33 %)
    "specificite_territoriale": (3, None),   # 0-1 ×3 → 0-3  (25 %)
    "edition_tradition":        (1, None),   # 0-2 ×1 → 0-2  (17 %)
    "notoriete_lieu":           (1, 1),      # plafonné à 1  ( 8 %)
}
POIDS_LANGUE = 1                             # 0-2 ×1 → 0-2  (17 %)
MAX_PROPOSE = 12


def _note_proposee(ev: dict) -> int | None:
    """Note sur 12 avec la pondération proposée. Prend l'ÉVÉNEMENT et non le seul JSON :
    la barrière de la langue se lit sur `llm_categorie`, pas dans le détail du score."""
    try:
        d = json.loads(ev.get("llm_score_detail") or "{}")
    except (ValueError, TypeError):
        return None
    if not isinstance(d, dict) or not d:
        return None
    total, trouve = 0, False
    for cle, (poids, plafond) in PONDERATION_PROPOSEE.items():
        bloc = d.get(cle)
        pts = bloc.get("points") if isinstance(bloc, dict) else bloc
        if isinstance(pts, (int, float)):
            p = int(pts)
            total += min(p, plafond) * poids if plafond is not None else p * poids
            trouve = True
    if not trouve:
        return None
    return total + accessibilite_langue(ev) * POIDS_LANGUE


def _simuler(vivants: list[dict], notes: dict, args) -> None:
    """Le classement ACTUEL contre le classement PROPOSÉ, territoire par territoire.

    Par territoire et pas globalement, parce que c'est ainsi que la section choisit : une
    repondération qui améliore la moyenne mais laisse le même événement en tête de chaque
    colonne n'aurait rien changé pour le visiteur. C'est le HAUT de chaque colonne qu'il
    faut regarder — c'est tout ce qui s'affiche."""
    print("\n## Simulation : ce que la pondération proposée changerait\n")
    print("| Critère | Poids | Plafond | Part du maximum |")
    print("|---|---:|---:|---:|")
    for cle, (poids, plafond) in PONDERATION_PROPOSEE.items():
        maxi = (plafond if plafond is not None else {"rayonnement": 2, "edition_tradition": 2,
                "specificite_territoriale": 1, "notoriete_lieu": 3}[cle]) * poids
        print(f"| `{cle}` | ×{poids} | {plafond if plafond is not None else '—'} | "
              f"{maxi}/{MAX_PROPOSE} |")
    print(f"| `accessibilite_langue` (NOUVEAU, déduit de la catégorie) | ×{POIDS_LANGUE} | — "
          f"| {LANGUE_MAX * POIDS_LANGUE}/{MAX_PROPOSE} |")

    par_t: dict[str, list[dict]] = {}
    for lot in notes.values():
        for e in lot:
            par_t.setdefault(e.get("territoire") or "—", []).append(e)

    print("\n### Le haut de chaque territoire — avant / après\n")
    for t, lot in sorted(par_t.items()):
        av = sorted(lot, key=lambda e: deplacement_score(e["llm_score_detail"]) or 0,
                    reverse=True)[:args.exemples]
        ap = sorted(lot, key=lambda e: _note_proposee(e) or 0,
                    reverse=True)[:args.exemples]
        bouge = "" if [e["id"] for e in av] == [e["id"] for e in ap] else "  ← l'ordre CHANGE"
        print(f"\n**{t}**{bouge}\n")
        print(f"| rang | actuel (/{MAX_SCORE}) | proposé (/{MAX_PROPOSE}) |")
        print("|---:|---|---|")
        for i in range(max(len(av), len(ap))):
            g = (f"{deplacement_score(av[i]['llm_score_detail'])} · "
                 f"{(av[i].get('title') or '')[:38]}") if i < len(av) else ""
            d = (f"{_note_proposee(ap[i])} · "
                 f"{(ap[i].get('title') or '')[:38]}") if i < len(ap) else ""
            print(f"| {i + 1} | {g} | {d} |")

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
    print("\n### Combien de fiches touchent le plafond\n")
    print(f"| Territoire | À {MAX_PROPOSE}/{MAX_PROPOSE} | Candidates | Lecture |")
    print("|---|---:|---:|---|")
    for t, lot in sorted(par_t.items()):
        au_max = sum(1 for e in lot if _note_proposee(e) == MAX_PROPOSE)
        lecture = ("le barème trie encore" if au_max <= 1
                   else f"{au_max} ex æquo — c'est l'IMMINENCE qui choisit la carte")
        print(f"| {t} | {au_max} | {len(lot)} | {lecture} |")

    print("\n### Où se placerait le plancher\n")
    print(f"| Plancher /{MAX_PROPOSE} | Fiches retenues |")
    print("|---:|---:|")
    for s in range(4, MAX_PROPOSE + 1):  # tous les seuils, cf. SEUILS
        n = sum(1 for e in vivants if (_note_proposee(e) or -1) >= s)
        print(f"| **{s}** | {n} |")
    print(f"\n> Le plancher ne se transpose PAS : 6/{MAX_SCORE} et 6/{MAX_PROPOSE} n'expriment pas la même\n"
          "> exigence, et la distribution change aussi. À re-décider sur ce tableau.\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Distribution des notes de déplacement, par territoire.")
    p.add_argument("--exemples", type=int, default=3,
                   help="Nombre d'exemples à montrer par note (défaut 3).")
    p.add_argument("--simuler", action="store_true",
                   help="Compare le classement actuel à celui de la pondération proposée. "
                        "N'écrit RIEN et ne change pas la formule en service.")
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
        n = deplacement_score(ev.get("llm_score_detail"))
        if n is None:
            sans_note += 1        # « pas mesuré » ≠ 0 : ces fiches ne sont PAS classées
            continue              # dernières, elles sont hors section (utils/deplacement)
        notes.setdefault(n, []).append(ev)

    print(f"# Plancher de « Ça vaut le déplacement » — {auj.isoformat()}\n")
    print(f"{len(rows)} fiche(s) en ligne, dont **{len(vivants)} encore devant nous** "
          f"(à venir, en cours, récurrentes — règle 5).")
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

    if args.simuler:
        _simuler(vivants, notes, args)

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
        for e in sorted(perdus, key=lambda x: deplacement_score(x["llm_score_detail"]) or 0,
                        reverse=True)[:20]:
            n = deplacement_score(e["llm_score_detail"])
            print(f"- **{n}/8** · {(e.get('territoire') or '—')} · {(e.get('title') or '')[:60]}")
            for r in deplacement_raisons(e.get("llm_score_detail"))[:2]:
                print(f"    - {r[:118]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
