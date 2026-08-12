#!/usr/bin/env python3
"""Recopie `url_officiel` de l'original vers ses traductions (reprise d'historique).

POURQUOI. `translate_events.py` créait la fiche traduite sans copier `url_officiel`
(corrigé le 2026-08-05, troisième oubli de la même famille après `date_source` et
`llm_score_detail`). Conséquence : `utils.radar.official_anchor()` ne trouvait aucune
ancre sur la traduction, donc `publisher_as` la publiait SANS source officielle. La
jumelle italienne d'une fiche parfaitement sourcée affichait une page muette — WP#2174
(Saint-Ours) montrait lasaintours.it en français et rien en italien.

Le correctif ne vaut que pour les traductions À VENIR. Ce script répare les anciennes.

CE QU'IL NE FAIT PAS. Il ne résout aucune page, ne lit aucun site, n'appelle aucune IA.
Il ne fait que recopier une valeur déjà vérifiée par enrich.py sur l'original. Il
n'écrase JAMAIS une valeur existante sur la traduction, et ne touche pas WordPress :
la republication reste une étape séparée et explicite.

Usage sur le VPS :
    cd ~/evenements && .venv/bin/python -m scripts.backfill_url_officiel_traductions
    cd ~/evenements && .venv/bin/python -m scripts.backfill_url_officiel_traductions --apply
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# La traduction et l'original doivent désigner le même événement : on ne recopie que si
# le parent existe VRAIMENT et porte une URL. Un parent supprimé ou vide ne donne rien.
REQUETE = """
SELECT t.id            AS id_trad,
       t.title         AS titre_trad,
       t.translated_lang AS langue,
       t.wp_post_id_as AS wp_trad,
       p.id            AS id_orig,
       p.url_officiel  AS url
  FROM events_raw t
  JOIN events_raw p ON p.id = t.translation_of
 WHERE t.translation_of IS NOT NULL
   AND COALESCE(t.url_officiel, '') = ''
   AND COALESCE(p.url_officiel, '') <> ''
 ORDER BY t.id
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Recopie url_officiel de l'original vers ses traductions.")
    ap.add_argument("--apply", action="store_true",
                    help="Écrire réellement (par défaut : simulation, rien n'est modifié).")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n"
              f"(data/ est hors dépôt Git — lancer ce script sur le VPS.)")
        return 1

    # En simulation, la base est ouverte en LECTURE SEULE par SQLite lui-même : même une
    # erreur de programmation ici ne peut pas l'écrire.
    if args.apply:
        conn = sqlite3.connect(DB_PATH)
    else:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    lignes = conn.execute(REQUETE).fetchall()

    # L'ENTONNOIR, ET PAS SEULEMENT LE RÉSULTAT. Ajouté le 2026-08-12 après m'être
    # avancé sur son seul chiffre : `verifier_liens` montrait treize fiches traduites
    # publiées sans lien, j'ai annoncé que ce script les réparerait, il en a rendu DEUX.
    # Les onze autres n'ont rien à recopier — leur ORIGINAL n'a pas non plus de source
    # officielle, ce qui est un manque en amont (résolution de source), pas un défaut de
    # propagation. Un « 2 » sans dénominateur laisse croire au premier, et c'est le
    # défaut que docs/ERREURS_2026-08-11.md nomme : un chiffre qui ne dit pas combien de
    # cas se sont présentés.
    sans_source = conn.execute(
        "SELECT COUNT(*) FROM events_raw t WHERE t.translation_of IS NOT NULL "
        "AND COALESCE(t.url_officiel,'') = ''").fetchone()[0]

    print("=" * 78)
    print("Reprise url_officiel sur les traductions — "
          + ("ÉCRITURE" if args.apply else "SIMULATION, rien n'est modifié"))
    print("=" * 78)
    print(f"Base                          : {DB_PATH}")
    print(f"Traductions sans source       : {sans_source}")
    print(f"  · dont l'original en a une  : {len(lignes)}   ← réparables ici")
    print(f"  · dont l'original n'en a pas: {sans_source - len(lignes)}   "
          f"(rien à recopier : le manque est EN AMONT, sur l'original)")
    print(f"Traductions réparables        : {len(lignes)}")
    en_ligne = [r for r in lignes if (r["wp_trad"] or 0) > 0]
    print(f"  · dont déjà publiées sur AS : {len(en_ligne)}"
          "   (à republier ensuite pour que la source apparaisse)")
    print()

    for r in lignes:
        etat = f"WP#{r['wp_trad']}" if (r["wp_trad"] or 0) > 0 else "hors ligne"
        print(f"  [{r['id_trad']:>5}] {r['langue'] or '??'} ← [{r['id_orig']:>5}]  "
              f"{etat:<11} {(r['titre_trad'] or '')[:44]:<44} {r['url'][:46]}")

    if not args.apply:
        print(f"\n(simulation — relancer avec --apply pour écrire les {len(lignes)} valeurs)")
        conn.close()
        return 0

    # Une transaction unique : soit les N copies passent, soit aucune.
    with conn:
        for r in lignes:
            conn.execute("UPDATE events_raw SET url_officiel=? WHERE id=?",
                         (r["url"], r["id_trad"]))
    restants = conn.execute(REQUETE).fetchall()
    conn.close()

    print(f"\n{len(lignes)} valeur(s) copiée(s). Réparables restantes : {len(restants)}.")
    if en_ligne:
        ids = " ".join(str(r["id_trad"]) for r in en_ligne)
        print("\nPour que la source apparaisse sur les fiches DÉJÀ en ligne :")
        print(f"  .venv/bin/python -m scripts.publish_batch_as --ids {ids} "
              f"--skip-media --delay 2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
