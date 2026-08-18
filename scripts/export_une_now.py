#!/usr/bin/env python3
"""EXPORTER `as_une_now` pour écriture par un autre canal que la publication.

LECTURE SEULE par défaut. Aucun réseau, aucun appel LLM.

D'OÙ ÇA VIENT (2026-08-18). Le VPS ne joint plus `agendasabauda.eu` : `ping`, port 80 et
port 443 sont tous en timeout vers 5.135.23.164, et uniquement vers elle — les paquets
sont jetés à destination. Le déblocage dépend de l'hébergeur, donc d'un délai qu'on ne
maîtrise pas. Or `publish_batch_as` est le SEUL chemin par lequel `as_une_now` atteint
WordPress, et sans elle la section « À la une » n'a rien à trier.

Ce script sépare les deux choses que la publication faisait ensemble : le CALCUL (local,
qui marche) et le TRANSPORT (bloqué). Il rend le calcul sous une forme qu'un autre canal
— la console WordPress, Novamira — peut écrire directement.

CE QU'IL N'EST PAS. Ce n'est pas une republication : il ne touche ni au texte, ni aux
images, ni aux dates. Il ne transporte qu'un nombre par fiche. C'est donc BEAUCOUP moins
risqué qu'un `--update`, qui réécrit le contenu de la page avec ce que dit la base.

POURQUOI IL EXPORTE AUSSI LES VIDES. Une fiche hors une reçoit `""`, pas rien : c'est
`publisher_as` qui fait ça, et la distinction porte du sens — « vide » veut dire « pas sa
place aujourd'hui », alors qu'une clé absente veut dire « jamais calculée ». Les exporter
permet aussi de marquer TOUT le lot ensuite (voir `--marquer`), donc d'éviter que le
rafraîchisseur republie trois cents fiches le jour où le réseau revient.

DEUX TEMPS, ET L'ORDRE COMPTE :

  1. `.venv/bin/python -m scripts.export_une_now`
     → rend le JSON à donner à Novamira. Rien n'est écrit.

  2. `.venv/bin/python -m scripts.export_une_now --apply`
     → APRÈS que Novamira a confirmé l'écriture, enregistre `une_now_publie` en base.
     Sans cette seconde passe, `refresh_deplacement` croira la valeur jamais publiée et
     republiera tout le catalogue au retour du réseau.

⚠️ NE PAS MARQUER AVANT LA CONFIRMATION. Marquer, c'est écrire en base « WordPress a cette
valeur ». Le faire sans preuve, c'est fabriquer exactement le mensonge que la règle 1 de
CLAUDE.md interdit : un identifiant en base ne prouve rien sur le site.
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
from utils.une import une_now

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

SQL = ("SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as, 0) > 0 "
       "AND duplicate_of IS NULL AND wp_deleted_at IS NULL")


def _valeurs(lignes: list[dict], auj: date) -> dict[str, str]:
    """{post_id: valeur} — la valeur EXACTE que `publisher_as` aurait posée aujourd'hui."""
    out: dict[str, str] = {}
    for ev in lignes:
        v = une_now(ev, aujourdhui=auj)
        out[str(int(ev["wp_post_id_as"]))] = "" if v is None else str(v)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Exporte as_une_now pour écriture hors publication. Lecture seule.")
    # `--apply` est la convention de TOUS les scripts d'écriture de ce dépôt, et
    # `tests/test_regles_du_depot.py` la fait respecter — il a refusé ce fichier tant
    # qu'il ne portait que `--marquer`. La règle est bonne : un nom d'option inventé
    # oblige à relire l'aide avant chaque geste, là où `--apply` se tape de mémoire.
    # On garde donc les deux, l'alias disant CE QUE ça écrit.
    p.add_argument("--apply", "--marquer", action="store_true", dest="marquer",
                   help="Enregistre une_now_publie en base. À NE FAIRE QU'APRÈS "
                        "confirmation que WordPress a bien reçu les valeurs.")
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n(lancer ce script sur le VPS.)")
        return 1
    auj = date.today()

    mode = "rw" if args.marquer else "ro"
    conn = sqlite3.connect(f"file:{DB_PATH}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    lignes = [dict(r) for r in conn.execute(SQL)]
    valeurs = _valeurs(lignes, auj)
    non_vides = {k: v for k, v in valeurs.items() if v}

    # Le périmètre s'écrit à côté du nombre, et un zéro dit son dénominateur (règle 6).
    print(f"# Fiches liées à un post WordPress : {len(lignes)} (non doublons, non "
          f"supprimées)")
    print(f"# Dont une place en une aujourd'hui ({auj.isoformat()}) : {len(non_vides)}")
    print(f"# Les {len(valeurs) - len(non_vides)} autres reçoivent une valeur VIDE — "
          f"« pas sa place », qui n'est pas « jamais calculée ».")
    if non_vides:
        tete = sorted(non_vides.items(), key=lambda kv: -int(kv[1]))[:5]
        titres = {str(int(e["wp_post_id_as"])): (e.get("title") or "")[:44] for e in lignes}
        print("# Les cinq plus hautes, pour reconnaître le résultat sur le site :")
        for pid, v in tete:
            print(f"#   WP#{pid:<6} {v:>3}  {titres.get(pid, '')}")
    print()

    if not args.marquer:
        print(json.dumps(valeurs, separators=(",", ":"), sort_keys=True))
        print()
        print("# ↑ à donner à Novamira. Puis, APRÈS sa confirmation seulement :")
        print("#   .venv/bin/python -m scripts.export_une_now --apply")
        conn.close()
        return 0

    # ── MARQUAGE ────────────────────────────────────────────────────────────────────
    for col in ("deplacement_now_publie", "une_now_publie"):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
    for ev in lignes:
        conn.execute("UPDATE events_raw SET une_now_publie=? WHERE id=?",
                     (valeurs[str(int(ev["wp_post_id_as"]))], ev["id"]))
    conn.commit()

    # RECOMPTER EN BASE plutôt que de croire la longueur d'une liste (règle 6).
    relu = [dict(r) for r in conn.execute(SQL)]
    justes = sum(1 for ev in relu
                 if (ev.get("une_now_publie") or "") == valeurs[str(int(ev["wp_post_id_as"]))])
    conn.close()
    print(f"✅ {justes} fiche(s) marquées sur {len(relu)} (recompté en base).")
    print("   Le rafraîchisseur de 10h45 ne les republiera donc pas pour rien.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
