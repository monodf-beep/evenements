#!/usr/bin/env python3
"""COMBIEN DE FICHES ONT UNE DESCRIPTION QUI NE PARLE PAS D'ELLES ?

POURQUOI COMPTER AVANT DE BLOQUER. Franck, 2026-08-04 : « je veux qu'il puisse juger la
description, et ce, partout. On ne doit pas faire des choses automatiques pour faire des
choses automatiques sans réfléchir. » Les deux moitiés de la phrase comptent. Le contrôle
de `utils/coherence` est branché en refus dans `translate_events`, où le coût d'un faux
refus est nul (la fiche se represente au run suivant). Le poser aussi dans l'évaluateur ou
la publication, sans savoir combien de fiches il attrape, ce serait fabriquer un état
terminal de plus — le défaut que `docs/ETATS_TERMINAUX.md` recense depuis trois jours.

Ce script est donc la moitié « réfléchir » : il mesure, il ne bloque nulle part et n'écrit
rien. C'est sur son chiffre qu'on décidera où mettre d'autres portillons.

CE QU'IL FAUT LIRE DANS SA SORTIE. Un taux élevé n'est pas une bonne nouvelle : soit la
base est très polluée, soit le contrôle est trop sévère. Les exemples sont là pour
trancher entre les deux À LA MAIN — un compteur seul ne le dit pas, et le croire sur
parole reviendrait à faire confiance à un contrôle qu'on n'a pas vérifié.

Règle 5 : uniquement ce qui est encore devant nous. Une fiche passée mal décrite ne sera
ni republiée ni traduite ; la compter gonflerait le chiffre sur lequel on décide.

AUCUNE ÉCRITURE — base en lecture seule, aucun réseau, aucun LLM.

Usage :
    .venv/bin/python -m scripts.audit_coherence
    .venv/bin/python -m scripts.audit_coherence --exemples 15
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.coherence import MIN_TEXTE_VISIBLE, incoherence_description
from utils.completeness import is_recurring

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _vivant(ev: dict, auj: date) -> bool:
    if is_recurring(ev):
        return True
    d = ev.get("date_event_end") or ev.get("date_event_start")
    return not d or str(d)[:10] >= auj.isoformat()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Fiches dont la description ne parle pas d'elles.")
    p.add_argument("--exemples", type=int, default=10, help="Exemples à afficher (défaut 10).")
    # LE GESTE QUE J'AVAIS SAUTÉ (2026-08-13). CLAUDE.md dit : « avant de livrer un
    # portillon, le passer sur des données réelles et LIRE ce qu'il refuse ». Le signal ①
    # a bloqué la traduction neuf jours sur deux faux positifs faute de l'avoir fait, et
    # le signal ② — devenu ce jour-là le seul juge habilité à bloquer — s'est révélé
    # capable de prendre « vers 21h » ou « l'isola » pour des noms de communes.
    # `--bloquant` montre EXACTEMENT ce qui serait refusé, et rien d'autre. Une option de
    # lecture, donc, mais c'est celle qui permet de tenir la règle.
    p.add_argument("--bloquant", action="store_true",
                   help="N'afficher que ce qui REFUSE réellement — les DEUX signaux "
                        "réunis, c'est-à-dire ce que translate_events écarte.")
    args = p.parse_args(argv)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(statut,'') NOT IN ('merged','rejected')")]
    conn.close()

    auj = date.today()
    vivants = [r for r in rows if _vivant(r, auj)]
    en_ligne = [r for r in vivants if (r.get("wp_post_id_as") or 0) > 0]
    trouves = [(r, m) for r in vivants
               if (m := incoherence_description(r, bloquant=args.bloquant))]
    publies = [(r, m) for r, m in trouves if (r.get("wp_post_id_as") or 0) > 0]

    # « liées à un post » : ce script lit la base, où un `wp_post_id_as` renseigné survit à
    # une mise à la corbeille (règle 1). Le tri par priorité reste juste — ces fiches sont
    # les plus susceptibles d'être lues —, mais l'affirmation « en ligne » demanderait
    # d'interroger WordPress numéro par numéro, ce qu'un audit hors-ligne ne fait pas.
    print(f"\n{len(rows)} fiche(s) actives, dont {len(vivants)} encore devant nous "
          f"(règle 5) et {len(en_ligne)} liées à un post WordPress.")
    # RÈGLE 6 : le périmètre à côté du nombre. Les deux modes ne comptent pas la même
    # chose, et sans cette ligne deux exécutions du même script se contrediraient.
    print("Mode : " + ("BLOQUANT — uniquement ce qui fait REFUSER une traduction "
                       "(les deux signaux RÉUNIS : nomme une autre commune ET ne "
                       "partage aucun mot avec la fiche)" if args.bloquant else
                       "rapport — les deux signaux séparément, dont AUCUN ne refuse "
                       "seul (--bloquant pour ne voir que les refus)") + "\n")
    pct = 100 * len(trouves) / max(len(vivants), 1)
    print(f"⚠️  {len(trouves)} fiche(s) signalée(s) ({pct:.1f} %), dont "
          f"**{len(publies)} LIÉES À UN POST**.\n")
    if not trouves:
        print("Rien à signaler.\n")
        # UN ZÉRO DOIT DIRE D'OÙ IL VIENT — c'est le premier enseignement du journal du
        # 11 août, et il vaut doublement ici : ce contrôle vient d'être RESSERRÉ le
        # 2026-08-13 (les deux signaux exigés ensemble au lieu d'un seul). Sans cette
        # phrase, « 0 » se lirait comme « le contrôle est éteint » — ou pire, ne se
        # lirait pas du tout, et on le découvrirait des semaines plus tard.
        if args.bloquant:
            print(f"Ce zéro porte sur {len(vivants)} fiche(s) examinée(s), et le refus "
                  f"exige les DEUX signaux\nensemble : la description nomme une autre "
                  f"commune ET ne partage aucun mot avec le\ntitre, le lieu ou la ville. "
                  f"Aucun des deux ne tient seul — vérifié sur cette base\nle 13/08 : ① "
                  f"se trompe sur le bilinguisme et la paraphrase, ② sur le voisinage\n"
                  f"(« à quinze minutes d'Annecy »), l'itinérance, et l'homonymie "
                  f"(« Dullin » est une\ncommune de Savoie ET le théâtre de Chambéry).\n"
                  f"Donc : « aucune fiche de cette forme aujourd'hui », pas « le contrôle "
                  f"est éteint ».\n")
        return 0

    # Par MOTIF : les deux signaux n'ont pas la même fiabilité, et les mélanger dans un
    # total unique masquerait lequel des deux produit le bruit.
    par_motif: dict[str, int] = {}
    for _r, m in trouves:
        cle = "autre commune nommée" if m.startswith("la description nomme") else "aucun mot commun"
        par_motif[cle] = par_motif.get(cle, 0) + 1
    for cle, n in sorted(par_motif.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>4} · {cle}")

    print(f"\nLes fiches PUBLIÉES d'abord — ce sont elles dont le visiteur pâtit :\n")
    # Dédoublonnage par id de fiche, et non par égalité de tuples : `publies` est
    # reconstruit à partir de `trouves`, donc ses tuples ne sont pas les mêmes objets et
    # la comparaison portait sur des dictionnaires entiers, ligne par ligne.
    deja = {r["id"] for r, _m in publies}
    ordre = publies + [(r, m) for r, m in trouves if r["id"] not in deja]
    for r, m in ordre[:args.exemples]:
        marque = f"WP#{r['wp_post_id_as']}" if (r.get("wp_post_id_as") or 0) > 0 else "sans post"
        print(f"  [{r['id']:>5}] {marque:<12} « {(r.get('title') or '')[:44]} » · "
              f"{(r.get('ville') or '—')[:18]}")
        print(f"          → {m}")
    if len(trouves) > args.exemples:
        print(f"\n  … {len(trouves) - args.exemples} autres (--exemples pour en voir plus).")

    # ⚠️ PHRASE CORRIGÉE LE 2026-08-04 (revue). Elle disait « rien n'est examiné en dessous
    # de {MIN} caractères visibles » — ce qui était vrai de la PREMIÈRE version du contrôle
    # et faux depuis le correctif du matin même. Le seuil ne garde plus que le signal ①, et
    # c'est tout l'objet du correctif : un fil Google News fait 110 caractères visibles, il
    # est signalé par le signal ②. Laisser la phrase, c'était inviter le lecteur à écarter
    # comme « non examinées » exactement les fiches pour lesquelles le contrôle existe.
    print(f"\nÀ LIRE AVANT DE CONCLURE. Un taux élevé ne dit pas à lui seul que la base est\n"
          f"polluée : il peut aussi dire que le contrôle est trop sévère. Les exemples\n"
          f"ci-dessus servent à trancher entre les deux à la main. AUCUN de ces deux\n"
          f"signaux ne refuse quoi que ce soit à lui seul — `--bloquant` montre ce qui\n"
          f"refuse vraiment, et il exige les deux ENSEMBLE. « Autre commune nommée »\n"
          f"s'applique à TOUTE longueur de texte (c'est lui qui attrape les fils Google\n"
          f"News, courts par nature) ; « aucun mot commun » n'est évalué qu'au-dessus de\n"
          f"{MIN_TEXTE_VISIBLE} caractères visibles, car sur un texte court l'absence de\n"
          f"recoupement ne prouve rien.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
