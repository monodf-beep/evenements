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
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.completeness import is_recurring
from utils.deplacement import (DEPLACEMENT_MIN, HORIZON_JOURS, MAX_SCORE,
                               deplacement_raisons, deplacement_score)

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
SEUILS = (3, 4, 5, 6)


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
