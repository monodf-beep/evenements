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
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.completeness import is_recurring
from utils.deplacement import (_CRITERES, _PONDERATION, POIDS_LANGUE, DEPLACEMENT_MIN,
                               HORIZON_JOURS, MAX_SCORE, accessibilite_langue,
                               deplacement_raisons, deplacement_score, deplacement_now)


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
    # `--slack` n'envoie QUE le verdict de rotation, jamais le rapport entier : un pavé
    # de trente lignes dans un digest se saute, et ce qu'on veut lire tient en quatre.
    p.add_argument("--slack", action="store_true",
                   help="Dépose le verdict de rotation dans la boîte du jour (digest).")
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
    # ══ CE TABLEAU A MESURÉ L'ANCIENNE FORMULE PENDANT DOUZE JOURS ═══════════════════
    #
    # Il additionnait les points BRUTS de `llm_score_detail`, sans appliquer ni les poids
    # ni le plafond de `_PONDERATION`. Son commentaire d'origine — « les quatre critères
    # pèsent 1 dans la formule, mais leurs MAXIMA diffèrent » — décrivait la formule
    # d'AVANT la repondération du 2026-08-04, et n'a pas été relu quand elle a changé.
    #
    # Conséquence lue le 2026-08-16 : le rapport annonçait « notoriete_lieu 46 %, il pèse
    # le plus lourd » et concluait « c'est la PONDÉRATION qu'il faudrait revoir ». Or
    # `_PONDERATION` PLAFONNE déjà `notoriete_lieu` à 1 point, précisément pour que la
    # réputation de la salle n'écrase pas la raison de s'y rendre. Le rapport réclamait
    # un correctif DÉJÀ APPLIQUÉ, et l'appliquer une seconde fois l'aurait cassé.
    #
    # On mesure donc la contribution RÉELLE — poids et plafond compris, via la même table
    # que le score, jamais une copie — et on ajoute l'accessibilité linguistique, qui vaut
    # deux points sur douze et n'apparaissait nulle part.
    print("\n## D'où viennent les points (contribution RÉELLE à la note sur 12)\n")
    brut = {c: 0 for c in _CRITERES}
    pondere = {c: 0 for c in _CRITERES}
    plafonds = {c: 0 for c in _CRITERES}
    langue = 0
    for lot in notes.values():
        for e in lot:
            langue += accessibilite_langue(e) * POIDS_LANGUE
            try:
                d = json.loads(e.get("llm_score_detail") or "{}")
            except (ValueError, TypeError):
                continue
            for c in _CRITERES:
                bloc = d.get(c)
                pts = bloc.get("points") if isinstance(bloc, dict) else bloc
                if isinstance(pts, (int, float)):
                    poids, plafond = _PONDERATION[c]
                    p = int(pts)
                    brut[c] += p
                    pondere[c] += (min(p, plafond) if plafond is not None else p) * poids
                    plafonds[c] = max(plafonds[c], p)
    somme = sum(pondere.values()) + langue or 1
    print("| Critère | Poids | Plafond | Points bruts | **Contribution réelle** | Part |")
    print("|---|---:|---:|---:|---:|---:|")
    for c in _CRITERES:
        poids, plafond = _PONDERATION[c]
        cap = str(plafond) if plafond is not None else "—"
        print(f"| `{c}` | ×{poids} | {cap} | {brut[c]} | **{pondere[c]}** | "
              f"{100 * pondere[c] / somme:.0f} % |")
    print(f"| `accessibilite_langue` | ×{POIDS_LANGUE} | — | — | **{langue}** | "
          f"{100 * langue / somme:.0f} % |")
    print("\n> La colonne qui compte est la CONTRIBUTION RÉELLE, pas les points bruts :\n"
          "> `notoriete_lieu` est plafonné à 1, donc une salle prestigieuse rapporte\n"
          "> autant qu'une salle simplement connue. C'est voulu — elle note LA SALLE,\n"
          "> pas la raison de s'y rendre.\n")

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

    # ══ CE QUE LA BARRIÈRE DE LA LANGUE ÉCARTERAIT DE LA TRADUCTION ═══════════════════
    #
    # Question de Franck, 2026-08-16 : « si je suis un touriste, j'aimerais avoir la
    # traduction ». Elle déplace le sujet, et à raison — le touriste ne choisit pas entre
    # une page italienne et une page française, il choisit entre une page italienne et
    # RIEN. Le tri par attractivité répond à « faut-il faire la route ? », jamais à « je
    # suis déjà là, qu'est-ce qu'il y a ce soir ? », qui est la question la plus fréquente.
    #
    # Reste un seul motif défendable de ne pas traduire : la LANGUE. Traduire en italien
    # une conférence tenue en français, c'est inviter quelqu'un dans une salle où il ne
    # comprendra rien. `accessibilite_langue` note exactement ça, sans LLM.
    #
    # CE TABLEAU N'EST PAS UNE RÈGLE, C'EST CE QU'ON LIT AVANT D'EN FAIRE UNE. Le
    # 2026-08-13, trois portillons livrés sans avoir été passés sur les données réelles se
    # sont révélés faux ; CLAUDE.md le dit depuis le 11 : « avant de livrer un portillon,
    # le passer sur des données réelles et LIRE ce qu'il refuse ». On imprime donc les
    # fiches à 0 en entier, avec leur catégorie, pour qu'un œil tranche.
    #
    # ⚠️ PÉRIMÈTRE, et il n'est pas celui de la traduction : ce sont les fiches PUBLIÉES
    # encore devant nous, celles que cet audit charge déjà. La file de traduction est
    # plus large. Ce relevé dit donc « à quoi ressemble le verdict », pas « combien de
    # fiches seraient écartées ».
    par_langue: dict[int, list[dict]] = {}
    for lot in notes.values():
        for e in lot:
            par_langue.setdefault(accessibilite_langue(e), []).append(e)
    total_l = sum(len(v) for v in par_langue.values()) or 1
    print(f"\n## Ce que la barrière de la langue écarterait de la traduction\n")
    print(f"Périmètre : les {total_l} fiche(s) publiées encore devant nous — PAS la file "
          f"de traduction,\nqui est plus large. On regarde ici la TÊTE du verdict, pas "
          f"son volume.\n")
    print("| Accessibilité | Fiches | Part | Ce que ça veut dire |")
    print("|---:|---:|---:|---|")
    _SENS = {2: "on en profite sans un mot de la langue",
             1: "la langue aide, elle ne commande pas",
             0: "il faut comprendre ce qui est dit — traduire enverrait dans une "
                "salle incompréhensible"}
    for v in (2, 1, 0):
        lot = par_langue.get(v, [])
        print(f"| {v} | {len(lot)} | {100 * len(lot) / total_l:.0f} % | {_SENS[v]} |")

    zeros = par_langue.get(0, [])
    if zeros:
        print(f"\n### Les {len(zeros)} fiche(s) notées 0 — À LIRE UNE PAR UNE\n")
        print("C'est la seule façon de savoir si le critère dit vrai. Une visite guidée "
              "bilingue\nrangée à 0, une exposition dont tous les cartels sont en "
              "français rangée à 2 : ça se\nvoit ici en dix secondes, et jamais en "
              "relisant le code.\n")
        for e in sorted(zeros, key=lambda x: (x.get("llm_categorie") or ""))[:40]:
            print(f"- _{(e.get('llm_categorie') or '—')}_ · "
                  f"{(e.get('title') or '')[:70]}")
        if len(zeros) > 40:
            print(f"- …et {len(zeros) - 40} autre(s).")
    else:
        print("\n> Aucune fiche à 0 dans ce périmètre — le critère n'écarterait rien ici. "
              "Ce n'est\n> pas une preuve qu'il est juste : c'est une preuve qu'il ne "
              "s'est pas prononcé.\n")
    verdict, hebdo = _rotation(vivants, auj)
    if args.slack:
        _poster(verdict, hebdo)
    return 0


def _semaines_sans_nouveaute(vivants: list[dict], auj: date) -> dict[str, dict]:
    """Combien de SEMAINES D'AFFILÉE la tête ne change pas — la question de Franck,
    2026-08-24 : « il faut qu'il y ait de la nouveauté [...] chaque semaine, je vais aller
    voir, le mardi, mercredi ou jeudi, qu'est-ce que je vais faire ce week-end. »

    ⚠️ CE QUE LE RELEVÉ DU 2026-08-18 NE MESURAIT PAS. Ses jalons (0, 15, 30, 60, 90, 120,
    180) peuvent sauter PAR-DESSUS six semaines d'immobilité sans jamais le montrer — deux
    jalons qui tombent chacun sur une fiche différente ne disent rien de ce qui s'est passé
    ENTRE les deux. La question de Franck est un rendez-vous HEBDOMADAIRE, littéralement :
    il faut donc UN point par semaine, sur tout l'horizon, pas une poignée de jalons épars.

    Renvoie, par territoire : la plus longue série de semaines consécutives avec la MÊME
    tête (`semaines_immobile`), la fiche concernée, et le nombre total de changements sur
    tout l'horizon — le pendant positif du même chiffre.
    """
    jalons = list(range(0, HORIZON_JOURS + 1, 7))
    terrs = sorted({(e.get("territoire") or "—") for e in vivants})
    out: dict[str, dict] = {}
    for t in terrs:
        seq: list[str | None] = []
        for delta in jalons:
            j = auj + timedelta(days=delta)
            lot = [(e, deplacement_now(e, aujourdhui=j)) for e in vivants
                   if (e.get("territoire") or "—") == t]
            lot = [(e, n) for e, n in lot if n is not None]
            lot.sort(key=lambda c: -c[1])
            seq.append((lot[0][0].get("title") or "")[:44] if lot else None)
        # `itertools.groupby` donne la longueur de chaque série de valeurs IDENTIQUES
        # consécutives — exactement une « série de semaines sans rien de nouveau ». None
        # (aucune fiche éligible) n'est jamais compté comme une série immobile : une
        # absence n'est pas une répétition.
        import itertools
        series = [(nom, len(list(g))) for nom, g in itertools.groupby(seq) if nom is not None]
        pire = max(series, key=lambda kv: kv[1], default=(None, 0))
        changements = sum(1 for i in range(1, len(seq))
                          if seq[i] is not None and seq[i] != seq[i - 1])
        out[t] = {"semaines_totales": len(jalons) - 1, "semaines_immobile": pire[1],
                  "tete_figee": pire[0], "changements": changements}
    return out


def _rotation(vivants: list[dict], auj: date) -> list[tuple[str, int, str, str]]:
    """« Est-ce que la rangée CHANGE ? » — la question que Franck a posée le 2026-08-18.

    « On a des événements trop loin dans le temps, il faudrait bien sûr les notes mais
    aussi se préoccuper des dates, sinon on a des homepages identiques sur 6 mois ! »

    LE MÉCANISME EST DANS `utils/deplacement.py`, et il se lit en deux constantes :
    `HORIZON_JOURS = 183` rend éligible tout ce qui commence dans les six mois, et
    `_FENETRES = ((7,3),(21,2),(45,1))` donne un bonus d'imminence dans les 45 derniers
    jours.

    ⚠️ CORRIGÉ le 05/09 (ce relevé, rejoué après la première mesure du même jour) :
    au-delà de 45 jours, le bonus vaut ZÉRO partout — le classement se réduisait alors
    au score intrinsèque, qui ne bouge pas d'un jour à l'autre. Piémont et Vallée
    d'Aoste montraient la même tête 12 et 21 SEMAINES d'affilée sur les 26 mesurées.
    `_bonus_lointain` (même fichier) referme ce trou : décroissance de 1 à 0 entre
    45 et 183 jours, continue avec le dernier palier de `_FENETRES`. Il ne PROMET pas
    l'absence de case figée pour autant — deux fiches à égalité stricte, ou un
    territoire à une seule fiche, restent figés à raison. Ce relevé mesure toujours,
    il ne suppose plus rien du mécanisme corrigé.

    Conséquence attendue AVANT le correctif : une fiche très bien notée et lointaine —
    la Saint-Ours de janvier, le festival du film de novembre — occupait la case de son
    territoire jusqu'à ce qu'elle soit à moins de 45 jours, c'est-à-dire pendant des mois.

    ⚠️ ET LE LEVIER ÉTAIT CONTRAINT (Franck, 2026-08-18) : « on ne doit pas vouloir
    changer les règles du nombre d'éléments affichés, les événements vont arriver, on
    aura assez de contenu. » Raccourcir `HORIZON_JOURS` était donc EXCLU — ça
    rétrécirait le vivier et viderait la Vallée d'Aoste, qui produit peu. C'est
    pourquoi le correctif retenu fait jouer la DATE à vivier constant, plutôt que d'en
    exclure une partie.

    Ce relevé ne DÉCIDE rien : il MESURE. Si les colonnes montrent la même fiche partout,
    la rangée est figée et il faut retoucher les fenêtres ou l'horizon. Si elles changent,
    l'intuition était fausse et il ne faut rien toucher. C'est la même méthode que pour la
    une, où le banc a servi à choisir le plancher au lieu de le poser au jugé.
    """
    print("\n\n## Est-ce que la rangée CHANGE, ou reste-t-elle la même pendant des mois ?\n")
    print("La section montre UNE carte par territoire. On rejoue donc, territoire par")
    print("territoire, la fiche qui serait en tête à plusieurs dates — mêmes règles, même")
    print("base, seule la date change.\n")

    jalons = (0, 15, 30, 60, 90, 120, 180)
    terrs = sorted({(e.get("territoire") or "—") for e in vivants})
    tetes: dict[str, list[str]] = {t: [] for t in terrs}
    for delta in jalons:
        j = auj + timedelta(days=delta)
        for t in terrs:
            lot = [(e, deplacement_now(e, aujourdhui=j)) for e in vivants
                   if (e.get("territoire") or "—") == t]
            lot = [(e, n) for e, n in lot if n is not None]
            lot.sort(key=lambda c: -c[1])
            tetes[t].append(f"{(lot[0][0].get('title') or '')[:24]} ({lot[0][1]})"
                            if lot else "—")

    entete = " | ".join(f"J+{d}" for d in jalons)
    print(f"| Territoire | {entete} |")
    print("|---" * (len(jalons) + 1) + "|")
    for t in terrs:
        print(f"| {t} | " + " | ".join(tetes[t]) + " |")

    # LE CHIFFRE QUI RÉPOND À LA QUESTION, et il dit son dénominateur : combien de fiches
    # DIFFÉRENTES occupent la case sur toute la période. 1 sur 7 relevés = figée.
    print()
    figes = []
    for t in terrs:
        noms = {x.split(" (")[0] for x in tetes[t] if x != "—"}
        etat = ("**FIGÉE**" if len(noms) <= 1 else f"{len(noms)} fiches différentes")
        print(f"- **{t}** : {etat} sur {len(jalons)} relevés.")
        if len(noms) <= 1:
            figes.append(t)
    if figes:
        print(f"\n> {len(figes)} territoire(s) sur {len(terrs)} montrent la MÊME fiche à")
        print(f"> six mois d'intervalle, MALGRÉ le gradient d'imminence (05/09, jusqu'à")
        print(f"> {HORIZON_JOURS} jours). Une seule fiche dans la colonne, ou une égalité")
        print("> stricte de score entre concurrentes, restent figées à raison — lire le")
        print("> détail avant de conclure à un défaut du mécanisme.")
    else:
        print("\n> Aucune case figée : la rangée tourne d'elle-même, il n'y a rien à")
        print("> corriger de ce côté.")

    # LA QUESTION HEBDOMADAIRE, littéralement — pas les jalons épars ci-dessus.
    hebdo = _semaines_sans_nouveaute(vivants, auj)
    print("\n## Si je reviens chaque semaine, est-ce que je vois autre chose ?\n")
    print("Un point par SEMAINE, sur tout l'horizon — les jalons ci-dessus peuvent sauter")
    print("par-dessus une série immobile sans la montrer ; ici, aucune semaine n'est")
    print("sautée.\n")
    for t in terrs:
        h = hebdo[t]
        if h["semaines_immobile"] >= 2:
            print(f"- **{t}** : jusqu'à **{h['semaines_immobile']} semaines d'affilée** "
                  f"sans changement — « {h['tete_figee']} » — et {h['changements']} "
                  f"changement(s) au total sur {h['semaines_totales']} semaines.")
        else:
            print(f"- **{t}** : jamais plus d'une semaine sans changement — "
                  f"{h['changements']} changement(s) sur {h['semaines_totales']} semaines.")
    print("\n> Le nombre qui compte pour un rendez-vous hebdomadaire n'est pas le total de")
    print("> changements sur six mois, c'est la PIRE série immobile : c'est elle qui")
    print("> décide si quelqu'un qui revient chaque mardi finit par ne plus revenir.")

    # (territoire, nb de fiches distinctes, tête à J+0, tête à J+180) — de quoi écrire un
    # verdict ailleurs sans re-parser la sortie affichée.
    verdict = [(t, len({x.split(" (")[0] for x in tetes[t] if x != "—"}),
               tetes[t][0], tetes[t][-1]) for t in terrs]
    return verdict, hebdo


def _poster(verdict: list[tuple[str, int, str, str]], hebdo: dict[str, dict]) -> None:
    """Dépose le verdict dans la boîte du jour — pas un message de plus, quelques lignes
    dans le digest que Franck reçoit déjà.

    POURQUOI CE CHEMIN EXISTE (2026-08-18). Franck est en congés jusqu'au 3 septembre,
    sans accès au VPS, avec son téléphone. La mesure, elle, a besoin de la base — donc du
    VPS. Ce drapeau lui fait traverser le seul canal qui reste ouvert. C'est aussi la
    raison de sa brièveté : ça se lit sur un écran de téléphone, ou ça ne se lit pas.
    """
    from utils import slack
    figes = [v for v in verdict if v[1] <= 1]
    lignes = [f"📐 *Rotation de « Ça vaut le déplacement »* — {len(figes)} case(s) figée(s) "
              f"sur {len(verdict)}."]
    for terr, distinctes, j0, j180 in verdict:
        if distinctes <= 1:
            lignes.append(f"🔴 {terr} : la même fiche sur 6 mois — {j0}")
        else:
            lignes.append(f"· {terr} : {distinctes} fiches différentes "
                          f"({j0} → {j180})")
    if figes:
        lignes.append("_Gradient d'imminence en place jusqu'à l'horizon (05/09) — une case "
                      "figée peut l'être à raison (fiche seule, égalité de score)._")
    # LA QUESTION HEBDOMADAIRE : « je reviens chaque mardi, est-ce que je vois autre
    # chose ? » Un seul chiffre par territoire — la pire série immobile en semaines —
    # parce que c'est lui qui décide si quelqu'un continue de revenir.
    pire_terr, pire_h = max(hebdo.items(), key=lambda kv: kv[1]["semaines_immobile"])
    if pire_h["semaines_immobile"] >= 2:
        lignes.append(f"📅 Pire cas hebdomadaire : {pire_terr} peut rester "
                      f"**{pire_h['semaines_immobile']} semaines** sans rien de nouveau "
                      f"(« {pire_h['tete_figee']} »).")
    else:
        lignes.append("📅 Aucun territoire ne reste plus d'une semaine sans changement.")
    slack.notify("\n".join(lignes))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
