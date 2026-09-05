#!/usr/bin/env python3
"""DÉFAIRE une fusion de doublons — le dernier chemin de retour qui manquait.

CE QUE ÇA FERME. `docs/ETATS_TERMINAUX.md` recense onze états terminaux ; dix ont
quelqu'un qui les rouvre. Le onzième, `statut='merged'` + `duplicate_of`, n'en avait
aucun : `dedupe.merge_group` absorbait une fiche dans une autre et rien, nulle part, ne
savait l'en sortir. `audit_dedupe_damage` compte 94 fusions suspectes parmi les fiches
publiées — toutes constatables, aucune réparable autrement qu'en SQL à la main.

DEUX CAS, ET ILS NE SE VALENT PAS. C'est toute la difficulté de ce script, et il ne la
cache pas :

  • FUSION RÉCENTE (depuis le 2026-08-03) — `dedupe` enregistre dans `unmerge_data` ce
    qu'il écrase : le statut d'avant de la perdante, et les champs remplacés chez la
    gagnante. On RESTAURE, à l'identique, sans rien deviner.

  • FUSION ANCIENNE — rien n'a été enregistré. Le statut d'avant ('pending', 'evaluated'
    ou 'published_sub' ?) n'existe nulle part et ne se déduit pas. On ne peut donc que
    RECONSTITUER : couper le lien et remettre la fiche en 'pending', c'est-à-dire la
    rendre à la file d'évaluation. Elle sera re-jugée — ce qui coûte un appel LLM et peut
    rendre un verdict différent de celui qu'un humain avait validé à l'époque.
    Le script DIT lequel des deux il fait, pour chaque fiche, avant d'agir.

CE QU'IL NE FAIT PAS, ET POURQUOI. Il ne décide jamais QUELLES fusions défaire. Départager
deux fiches homonymes demande de regarder les dates, le lieu et le contenu — c'est un
arbitrage éditorial, pas une règle. `audit_dedupe_damage` liste les candidates ; un humain
choisit ; ce script exécute. Le mettre en cron serait l'erreur inverse de toutes celles
corrigées le 2026-08-03.

Usage :
    .venv/bin/python -m scripts.unmerge 2762 1153            # dry-run (ids des PERDANTES)
    .venv/bin/python -m scripts.unmerge 2762 --apply
    .venv/bin/python -m scripts.unmerge 2762 --apply --rendre-description
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("unmerge")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Statut donné à une fiche dont on n'a PAS l'instantané : elle repart au début de la
# chaîne. 'pending' et pas 'evaluated' — prétendre qu'elle était retenue serait inventer
# une décision que personne n'a prise.
STATUT_RECONSTITUE = "pending"

# Les seuls statuts que la chaîne sait relire. Un statut inconnu ne fait pas d'erreur en
# SQLite : il RANGE la fiche là où plus aucune file ne la voit — ni publish_batch_as
# (evaluated/published_*), ni l'évaluateur (pending), ni les rapports de rejet. C'est un
# état terminal fabriqué par une faute de frappe, et personne ne le découvrirait avant des
# semaines (règle 3). Vérifié le 2026-08-04 (revue) : `--statut rejeted` était accepté,
# écrit, et le bilan répondait « ✅ 1/1 fusion(s) défaite(s) ».
STATUTS_CONNUS = ("pending", "evaluated", "published_cs", "published_sub", "rejected")


def _pile(row: dict) -> list:
    try:
        pile = json.loads(row.get("unmerge_data") or "[]")
    except (ValueError, TypeError):
        return []
    return pile if isinstance(pile, list) else []


def _snapshot(row: dict, role: str) -> dict | None:
    """Dernière entrée de `unmerge_data` pour ce rôle ('perdant' ou 'gagnant')."""
    for e in reversed(_pile(row)):
        if isinstance(e, dict) and e.get("role") == role:
            return e
    return None


def _snapshot_gagnant_de(row: dict, perdant_id: int) -> dict | None:
    """L'instantané de la gagnante correspondant À CETTE perdante-là.

    ⚠️ CORRECTIF DU 2026-08-04 (revue). On prenait la DERNIÈRE entrée 'gagnant' de la pile,
    puis on vérifiait que la perdante y figurait — sinon on ne rendait rien, EN SILENCE.
    Or `_empile` empile justement parce qu'une fiche absorbe plusieurs groupes au fil des
    jours (dedupe tourne chaque matin) : dès qu'une seconde fusion s'ajoute, la description
    écrasée par la PREMIÈRE devient irrécupérable, et `--rendre-description` répond
    « ✅ 1/1 fusion(s) défaite(s) » sans un mot. Reproduit sur fixture : deux entrées
    'gagnant', la perdante dans la première — la description n'était pas rendue.
    On cherche donc dans TOUTE la pile, la plus récente d'abord."""
    for e in reversed(_pile(row)):
        if (isinstance(e, dict) and e.get("role") == "gagnant"
                and perdant_id in (e.get("perdants") or [])):
            return e
    return None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Défait une fusion de doublons (ids des perdantes).")
    p.add_argument("ids", nargs="+", type=int, help="Ids LOCAUX des fiches ABSORBÉES.")
    p.add_argument("--apply", action="store_true", help="Écrit (sinon dry-run).")
    p.add_argument("--rendre-description", action="store_true",
                   help="Rend aussi à la GAGNANTE la description que cette fusion lui "
                        "avait écrasée (seulement si l'instantané existe).")
    p.add_argument("--statut", default=None,
                   help=f"Statut à donner aux fiches SANS instantané, au lieu de "
                        f"'{STATUT_RECONSTITUE}'. Sert quand on SAIT que la fiche n'a rien "
                        f"à faire dans la file : une fiche radar (source_type='radar') est "
                        f"un signal de détection Google News, jamais un événement "
                        f"publiable — la rendre à l'évaluation, c'est payer un appel LLM "
                        f"pour se faire dire ce qu'on savait déjà.")
    args = p.parse_args(argv)

    if args.statut and args.statut not in STATUTS_CONNUS:
        # Refus AVANT toute lecture : un statut inconnu ne lève aucune erreur SQL, il gare
        # simplement la fiche hors de toutes les files et de tous les comptages.
        print(f"\n⛔ statut inconnu : '{args.statut}'. Aucune file ne relit cette valeur — "
              f"la fiche\n   y serait garée sans que rien ne la signale. Attendus : "
              f"{', '.join(STATUTS_CONNUS)}.\n")
        return 2

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    marks = ",".join("?" * len(args.ids))
    rows = {r["id"]: dict(r) for r in conn.execute(
        f"SELECT * FROM events_raw WHERE id IN ({marks})", args.ids)}

    plan, refus = [], []
    for i in args.ids:
        ev = rows.get(i)
        if not ev:
            refus.append((i, "introuvable en base"))
            continue
        gagnant = ev.get("duplicate_of")
        if (ev.get("statut") or "") != "merged" and not gagnant:
            refus.append((i, f"n'est pas fusionnée (statut='{ev.get('statut')}')"))
            continue
        if (ev.get("wp_post_id_as") or 0) > 0:
            # Une fiche fusionnée QUI EST EN LIGNE est une anomalie à part (audit_wp_ghosts
            # ②). La défusionner sans traiter le post laisserait deux fiches revendiquer
            # la même page — on ne répare pas un désordre en en créant un autre.
            refus.append((i, f"porte encore WP#{ev['wp_post_id_as']} — voir "
                             f"audit_wp_ghosts avant de défusionner"))
            continue
        snap = _snapshot(ev, "perdant")
        radar = (ev.get("source_type") == "radar"
                 or "(radar)" in (ev.get("source_name") or ""))
        plan.append({
            "id": i, "titre": (ev.get("title") or "")[:55], "gagnant": gagnant,
            "statut_cible": ((snap or {}).get("statut_avant")
                             or args.statut or STATUT_RECONSTITUE),
            "restaure": bool(snap and snap.get("statut_avant")),
            "quand": (snap or {}).get("at", ""), "radar": radar,
        })

    print(f"\n{len(plan)} fusion(s) à défaire, {len(refus)} refusée(s).\n")
    for c in plan:
        mode = "RESTAURE" if c["restaure"] else "reconstitue"
        note = ""
        if not c["restaure"]:
            note = ("  ⚠️ aucun instantané — sera RE-ÉVALUÉE (coût LLM)" if not args.statut
                    else "  aucun instantané — statut imposé, pas de ré-évaluation")
        if c["radar"] and not c["restaure"] and not args.statut:
            # Une fiche RADAR est un signal de détection Google News, pas un événement :
            # la rendre à la file d'évaluation fait payer un appel LLM pour un verdict
            # connu d'avance. Le dire ici plutôt que de le laisser découvrir sur la facture.
            note = ("  ⚠️ fiche RADAR (signal Google News, jamais publiable) — "
                    "envisager --statut rejected")
        print(f"  [{c['id']:>5}] {mode:<11} statut → '{c['statut_cible']}' "
              f"(absorbée par {c['gagnant']}) · {c['titre']}{note}")
    for i, motif in refus:
        print(f"  ⛔ [{i:>5}] {motif}")

    anciennes = [c for c in plan if not c["restaure"]]
    if anciennes:
        print(f"\n  {len(anciennes)} fiche(s) sans instantané : la fusion est antérieure au "
              f"2026-08-03,\n  date à laquelle dedupe a commencé à enregistrer ce qu'il "
              f"écrase. Leur statut\n  d'avant n'existe nulle part — "
              + (f"on ne peut que les rendre à la file d'évaluation."
                 if not args.statut else
                 f"elles reçoivent le statut imposé '{args.statut}'."))
        if args.rendre_description:
            # LE PIÈGE À DIRE AVANT, PAS APRÈS. --rendre-description ne peut rendre que ce
            # que l'instantané contient ; sur une fusion ancienne il n'y a rien, donc
            # l'option ne fait RIEN — sans un mot, on croirait la description réparée.
            # C'est repair_polluted_descriptions qu'il faut alors (il re-télécharge la
            # page source), et c'est un geste séparé.
            print("\n  ⚠️ --rendre-description est SANS EFFET sur ces fiches-là : aucun "
                  "instantané\n     n'existe. Pour rendre à la gagnante sa vraie "
                  "description, passer par\n     scripts/repair_polluted_descriptions "
                  "(il re-télécharge la page source).")

    if not args.apply:
        print("\nDry-run — rien n'a été écrit. Ajouter --apply pour appliquer.\n")
        conn.close()
        return 0
    if not plan:
        conn.close()
        return 0

    quand = datetime.now().isoformat(timespec="seconds")
    rendues = 0
    sans_description: list[tuple[int, int]] = []
    for c in plan:
        conn.execute("UPDATE events_raw SET statut=?, duplicate_of=NULL WHERE id=?",
                     (c["statut_cible"], c["id"]))
        if args.rendre_description and c["gagnant"]:
            g = dict(conn.execute("SELECT * FROM events_raw WHERE id=?",
                                  (c["gagnant"],)).fetchone() or {})
            # On ne rend la description que si CETTE fusion-là est bien celle qui l'a
            # écrasée : rendre l'instantané d'une AUTRE fusion remplacerait un texte juste
            # par un texte périmé. D'où la recherche par perdante et non « la dernière ».
            snap = _snapshot_gagnant_de(g, c["id"])
            ancienne = ((snap or {}).get("champs_ecrases") or {}).get("description")
            if ancienne:
                conn.execute("UPDATE events_raw SET description=? WHERE id=?",
                             (ancienne, c["gagnant"]))
                rendues += 1
                log.info("[%s] description d'avant-fusion rendue à la gagnante", c["gagnant"])
            else:
                # DIRE CE QUI NE S'EST PAS PRODUIT (règle 6) : l'option a été demandée,
                # elle n'a rien rendu. Le silence laissait croire à une réparation.
                sans_description.append((c["id"], c["gagnant"]))
    conn.commit()

    # RECOMPTER PLUTÔT QUE CROIRE (règle 6) : on relit l'état réel au lieu d'annoncer le
    # nombre demandé.
    ids = [c["id"] for c in plan]
    m = ",".join("?" * len(ids))
    faites = conn.execute(f"SELECT COUNT(*) FROM events_raw WHERE id IN ({m}) "
                          f"AND duplicate_of IS NULL AND statut != 'merged'", ids).fetchone()[0]
    conn.close()
    print(f"\n✅ {faites}/{len(plan)} fusion(s) défaite(s)"
          + (f", {rendues} description(s) rendue(s) à la gagnante." if rendues else ".")
          + (f"\n⚠️  {len(plan) - faites} n'ont PAS été modifiées — vérifier les logs."
             if faites < len(plan) else ""))
    if sans_description:
        print(f"⚠️  --rendre-description n'a RIEN rendu pour {len(sans_description)} "
              f"fusion(s) : {sans_description[:8]}\n"
              f"    (aucun instantané de la gagnante ne mentionne cette perdante — soit la "
              f"fusion n'a\n"
              f"    écrasé aucune description, soit elle est antérieure au 2026-08-03.) "
              f"Pour rendre à la\n"
              f"    gagnante sa vraie description : scripts/repair_polluted_descriptions, "
              f"qui re-télécharge\n"
              f"    la page source.")
    # Ne l'annoncer que si c'est vrai : une fusion RESTAURÉE reprend son statut d'avant et
    # ne repasse par rien. Écrire la phrase dans tous les cas ferait attendre une
    # ré-évaluation qui n'aura pas lieu (règle 6 — dire ce qui s'est produit).
    if anciennes:
        cible = args.statut or STATUT_RECONSTITUE
        if cible == STATUT_RECONSTITUE:
            print(f"   Les {len(anciennes)} fiche(s) remises en '{cible}' repasseront par "
                  f"l'évaluation de 9h.\n")
        else:
            print(f"   Les {len(anciennes)} fiche(s) sans instantané ont été mises en "
                  f"'{cible}' — elles ne\n   repasseront donc PAS par l'évaluation.\n")
    log.info("Défusion : %d/%d appliquée(s) le %s", faites, len(plan), quand)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
