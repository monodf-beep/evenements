#!/usr/bin/env python3
"""Fixture : `scripts.publisher_as.lien_hub_territoire` pose un lien interne vers la
page hub du territoire, dans la langue de la fiche — le second symptôme des captures
Yoast du 2026-09-08 (« aucun lien interne dans cette page », WP#7490 et WP#7518).

Cinq cas, chacun décidant seul :
  1. territoire + langue reconnus (FR)                → lien FR vers le bon hub ;
  2. même territoire, langue IT                        → lien IT (URL et libellé changent) ;
  3. territoire NON reconnu (valeur brute imprévue)     → '' (aucun lien cassé) ;
  4. langue absente/inattendue                          → repli sur FR, pas d'exception ;
  5. LE CAS QUI DOIT PASSER : les 8 URLs sont celles vérifiées en ligne le 2026-09-08 —
     un slug mal orthographié dans la table ne serait pas détecté par un test qui ne
     vérifierait que la PRÉSENCE d'un lien, donc on compare l'URL exacte.

Aucun réseau, fonction pure. Lancer : .venv/bin/python -m tests.test_lien_hub_territoire
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publisher_as import lien_hub_territoire  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# 1. Territoire + langue reconnus (FR).
out = lien_hub_territoire("piemont", "fr")
_check("① Piémont FR : URL exacte vérifiée en ligne",
       'href="https://agendasabauda.eu/que-faire-dans-le-piemont/"' in out, out)
_check("① Piémont FR : libellé en français", "Voir tous les événements" in out, out)

# 2. Même territoire, langue IT.
out_it = lien_hub_territoire("piemont", "it")
_check("② Piémont IT : URL /it/ exacte", out_it ==
       '<p><a href="https://agendasabauda.eu/it/cosa-fare-in-piemonte/">'
       'Vedi tutti gli eventi in Piemonte</a></p>', out_it)
_check("② FR et IT ne renvoient pas la même URL", out != out_it)

# 3. Territoire non reconnu.
_check("③ territoire inconnu → aucun lien", lien_hub_territoire("hors-perimetre", "fr") == "")
_check("③ territoire vide → aucun lien", lien_hub_territoire("", "fr") == "")

# 4. Langue absente/inattendue → repli FR, jamais d'exception.
out_repli = lien_hub_territoire("savoie", "")
_check("④ langue vide : repli FR, pas d'exception", "que-faire-en-savoie" in out_repli, out_repli)
out_repli2 = lien_hub_territoire("savoie", "de")
_check("④ langue inattendue (de) : repli FR", "que-faire-en-savoie" in out_repli2, out_repli2)

# 5. Les 8 combinaisons donnent bien 8 URLs DISTINCTES (aucun doublon de copier-coller).
combos = [(t, l) for t in ("savoie", "piemont", "vallee-d-aoste", "comte-de-nice")
          for l in ("fr", "it")]
urls = [lien_hub_territoire(t, l) for t, l in combos]
_check("⑤ les 8 hubs (4 territoires × FR/IT) sont tous non vides", all(urls))
_check("⑤ les 8 URLs sont distinctes (aucun doublon)", len(set(urls)) == 8, urls)

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
