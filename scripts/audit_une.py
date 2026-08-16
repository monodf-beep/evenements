#!/usr/bin/env python3
"""Ce que la section « À LA UNE » retiendrait — et ce qu'elle écarterait, nommément.

LECTURE SEULE. Aucun appel LLM, aucune écriture.

POURQUOI CE SCRIPT EXISTE AVANT LA RÈGLE, ET PAS APRÈS. Le plancher de « Ça vaut le
déplacement » a été posé au jugé à 3 le 2026-08-01, « faute de connaître le stock » : il
ne servait à rien, il suffisait de ne pas être nul pour entrer, et « au diapason »
occupait la carte Savoie. Il a fallu COMPTER ce que chaque plancher laissait, territoire
par territoire, pour arriver à 10/12. `utils/une.py` sort avec trois seuils posés au jugé
eux aussi — intérêt 6/10, rendu 6/10, horizon 30 jours. Ce banc est là pour qu'ils ne le
restent pas.

CE QU'IL FAUT LIRE EN PREMIER, ce n'est pas le total : c'est la liste des fiches
ÉCARTÉES avec leur motif. Une règle se juge sur ce qu'elle refuse, pas sur ce qu'elle
laisse passer — c'est la consigne de CLAUDE.md que trois portillons du 2026-08-13 avaient
sautée, au prix de neuf jours de blocage.

Usage (VPS) :
    .venv/bin/python -m scripts.audit_une
    UNE_INTERET_MIN=7 .venv/bin/python -m scripts.audit_une     # essayer un autre seuil
    .venv/bin/python -m scripts.audit_une --jour 2026-09-05     # « et dans trois semaines ? »
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.une import (UNE_HORIZON_JOURS, UNE_INTERET_MIN, UNE_RENDU_MIN,
                       interet, une_etat)
# RÈGLE 5, RENDUE VISIBLE. `une_etat` écarte déjà les événements terminés — mais le
# vérificateur de `tests/test_regles_du_depot.py` ne peut pas le savoir, et il a raison
# d'insister : un filtre de date enfoui dans un appelé est un filtre qu'on croit avoir.
# Le déclarer ici sert aussi le dénominateur, qui comptait le passé et gonflait donc le
# périmètre annoncé (règle 6).
from scripts.audit_substance_published import devant_nous

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
TERRITOIRES = ("Savoie", "Piemonte", "Vallee-Aoste", "Nice")


def _connect_ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Ce que « À la une » retiendrait. Lecture seule.")
    p.add_argument("--jour", default="", help="Se placer à une autre date (AAAA-MM-JJ).")
    p.add_argument("--exemples", type=int, default=25,
                   help="Nombre d'écartées listées par motif (défaut 25).")
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n(lancer ce script sur le VPS.)")
        return 1
    auj = date.fromisoformat(args.jour) if args.jour else date.today()

    conn = _connect_ro(DB_PATH)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL")]
    conn.close()

    vivantes = [ev for ev in rows if devant_nous(ev, auj.isoformat())]

    retenues, ecartees = [], {}
    for ev in vivantes:
        n, motif = une_etat(ev, auj)
        if n is None:
            # On regroupe par FAMILLE de motif, pas par phrase exacte : les motifs portent
            # des chiffres (« intérêt 4 < 6 ») et le comptage éclaterait en autant de
            # lignes que de fiches.
            cle = motif.split("(")[0].split("—")[0].strip()
            ecartees.setdefault(cle, []).append((ev, motif))
        else:
            retenues.append((ev, n, motif))

    print("=" * 78)
    print(f"« À LA UNE » — ce que les règles retiendraient au {auj.isoformat()}")
    print("=" * 78)
    print(f"Base                : {DB_PATH}")
    print(f"Fiches publiées     : {len(rows)}, toutes dates")
    print(f"…encore devant nous : {len(vivantes)}  ← LE PÉRIMÈTRE EXAMINÉ (règle 5)")
    print(f"Seuils              : intérêt ≥ {UNE_INTERET_MIN}/10 · rendu ≥ {UNE_RENDU_MIN}/10 "
          f"· horizon {UNE_HORIZON_JOURS} j")
    print(f"RETENUES            : {len(retenues)}")
    print()

    if not retenues:
        # Un zéro doit dire d'où il vient (journal du 2026-08-11). Ici il a deux causes
        # opposées — des seuils trop hauts, ou un stock vide — et la liste des motifs
        # ci-dessous les sépare.
        print("⚠️  AUCUNE fiche ne passerait. Ce n'est pas forcément le stock : regardez")
        print("    les motifs d'écart ci-dessous, ils disent lequel des trois seuils mord.\n")
    else:
        print("## Ce qui serait en une, dans l'ordre\n")
        # LA LANGUE EST AFFICHÉE, parce que sans elle on lit deux événements là où il y
        # en a un. Sortie du 2026-08-17 : « Brahms / Chostakovitch » et « Brahms /
        # Šostakovič » occupaient les rangs 6 et 7 — c'est la même soirée, dans ses deux
        # versions Polylang. Sur la home FRANÇAISE la version italienne ne s'affiche pas
        # (Polylang filtre), mais ce rapport-ci ne le sait pas : il doit donc le montrer
        # plutôt que de laisser croire à un doublon de vitrine.
        print("_Les deux langues sont mélangées ci-dessous : un visiteur n'en voit "
              "qu'une.\nLa section « Est-ce que ça tourne » plus bas les sépare, "
              "comme le site._\n")
        print("| Rang | Score | Langue | Territoire | Fiche | Pourquoi |")
        print("|---:|---:|---|---|---|---|")
        for i, (ev, n, motif) in enumerate(
                sorted(retenues, key=lambda t: -t[1])[:15], 1):
            lang = "it" if (ev.get("translated_lang") or "") == "it" else (
                   "→it" if ev.get("translation_of") else "fr")
            print(f"| {i} | {n} | {lang} | {(ev.get('territoire') or '—')} | "
                  f"{(ev.get('title') or '')[:42]} | {motif[:52]} |")
        print()
        paires = sum(1 for e, _n, _m in retenues if e.get("translation_of"))
        if paires:
            print(f"> {paires} des {len(retenues)} retenues sont des TRADUCTIONS : elles "
                  f"n'entrent pas en\n> concurrence avec leur original, chacune sert sa "
                  f"langue. Le total ci-dessus\n> compte donc des pages, pas des "
                  f"événements distincts.\n")

        # PAR TERRITOIRE : le total peut rester confortable pendant qu'une colonne se vide.
        # Même leçon que le banc de « Ça vaut le déplacement ».
        print("### Par territoire\n")
        print("| Territoire | Retenues |")
        print("|---|---:|")
        for t in TERRITOIRES:
            print(f"| {t} | {sum(1 for e, _n, _m in retenues if (e.get('territoire') or '') == t)} |")
        print()

    print("## Ce que les règles ÉCARTENT — à lire avant de croire au total\n")
    print("| Motif | Fiches |")
    print("|---|---:|")
    for cle, lot in sorted(ecartees.items(), key=lambda kv: -len(kv[1])):
        print(f"| {cle} | {len(lot)} |")
    print()

    # LE MOTIF QUI COMPTE LE PLUS : celui du plancher d'intérêt. C'est lui qui décide
    # qu'un cours de pilates n'est pas une une, et c'est donc lui qui peut se tromper.
    proches = [(ev, m) for cle, lot in ecartees.items() if "intérêt sous le plancher" in cle
               for ev, m in lot]
    if proches:
        proches.sort(key=lambda t: -(interet(t[0]) or 0))
        print(f"### Les {len(proches)} écartée(s) pour INTÉRÊT INSUFFISANT, la plus haute "
              f"d'abord\n")
        print("C'est la liste qui juge la règle. Si vous y trouvez un événement qui "
              "mériterait\nla une, le plancher est trop haut — et ça se voit ici, jamais "
              "dans un total.\n")
        for ev, _m in proches[:args.exemples]:
            print(f"- **{interet(ev)}/10** · {(ev.get('territoire') or '—')} · "
                  f"{(ev.get('title') or '')[:62]}")
        if len(proches) > args.exemples:
            print(f"- …et {len(proches) - args.exemples} autre(s).")
        print()

    # CE QUE CHAQUE PLANCHER D'INTÉRÊT LAISSERAIT — la mesure qui manquait le 1er août.
    print("## Ce que chaque plancher d'intérêt laisserait\n")
    print("| Plancher | Retenues | Savoie | Piemonte | Vallee-Aoste | Nice |")
    print("|---:|---:|---:|---:|---:|---:|")
    import utils.une as U
    garde = U.UNE_INTERET_MIN
    for seuil in range(4, 11):
        U.UNE_INTERET_MIN = seuil
        lot = [ev for ev in vivantes if une_etat(ev, auj)[0] is not None]
        par_t = {t: sum(1 for e in lot if (e.get("territoire") or "") == t)
                 for t in TERRITOIRES}
        marque = "  ← actuel" if seuil == garde else ""
        vide = "  ⚠️ colonne vide" if any(v == 0 for v in par_t.values()) else ""
        print(f"| **{seuil}** | {len(lot)} | {par_t['Savoie']} | {par_t['Piemonte']} | "
              f"{par_t['Vallee-Aoste']} | {par_t['Nice']} |{marque}{vide}")
    U.UNE_INTERET_MIN = garde
    print("\n> La section affiche TROIS cartes. Un plancher qui n'en laisse que trois n'a")
    print("> aucune marge : deux événements passent et la une se fige à nouveau.\n")

    # ET DEMAIN ? La rotation est la demande de départ — elle doit se VÉRIFIER, pas se
    # postuler. On rejoue les mêmes règles à trois dates et on compare les têtes de liste.
    print("## Est-ce que ça TOURNE vraiment ?\n")
    print("Mêmes règles, trois dates. Si les trois lignes montrent les mêmes fiches, la")
    print("rotation ne marche pas — c'était tout le problème de départ.\n")
    # ⚠️ PAR LANGUE, ET C'EST LA CORRECTION QUI COMPTE (2026-08-17, deuxième relecture).
    # La première version classait toutes les pages ensemble : le Tour de l'Avenir
    # occupait les rangs 1 ET 2, en français puis en italien, et la « tête de liste »
    # affichait donc deux fois le même événement. Or un visiteur ne voit qu'une langue —
    # Polylang filtre. Le rapport montrait une une qui n'existe pour personne.
    #
    # On sépare donc les deux versants, comme le site. Et si la requête JetEngine, elle,
    # NE filtrait pas par langue, ce tableau le dirait aussi : les trois cartes montreraient
    # le même concert deux fois, et ça se verrait ici avant de se voir en ligne.
    for langue, libelle in (("fr", "versant FRANÇAIS"), ("it", "versant ITALIEN")):
        print(f"\n### {libelle}\n")
        for delta in (0, 7, 14, 21):
            j = auj + timedelta(days=delta)
            # On repart de `rows` : à J+21, une fiche « passée » aujourd'hui l'est encore,
            # mais une fiche écartée par l'horizon aujourd'hui peut être entrée depuis.
            cote = [ev for ev in rows
                    if ((ev.get("translated_lang") or "fr") == langue)]
            lot = sorted(((ev, une_etat(ev, j)[0]) for ev in cote),
                         key=lambda t: -(t[1] or -1))
            tete = [f"{(e.get('title') or '')[:26]}" for e, n in lot if n is not None][:3]
            print(f"- **{j.isoformat()}** ({delta:>2} j) : "
                  + (" · ".join(tete) if tete else "_aucune_"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
