#!/usr/bin/env python3
"""Fixture : `utils.seo._ajuste_meta_seo` fait rentrer une méta description dans le
budget RÉEL de Yoast (156 caractères) sans jamais couper un mot en deux.

TROUVÉ le 2026-09-08, captures d'écran Yoast de Franck sur WP#7490 et WP#7518 :
« La méta description fait plus de 156 caractères ». Deux défauts en cascade :
  1. `SEO_PROMPT` vise « 150-160 caractères » — sa propre borne haute dépasse déjà
     le seuil Yoast de 156 ;
  2. `optimize_seo` ne faisait que tronquer sec `[:180]` — un filet plus large que
     le défaut qu'il était censé couvrir, et qui peut couper un mot en deux.

Même discipline que `_ajuste_titre_seo` (tests/test_seo_titre_marque.py) : jamais de
mot tronqué, jamais au-delà du budget réel.

Lancer : .venv/bin/python -m tests.test_seo_meta_budget
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.seo import _ajuste_meta_seo  # noqa: E402

echecs = 0


def _check(label, obtenu, attendu):
    global echecs
    if obtenu == attendu:
        print(f"OK    {label} → {obtenu!r}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} : attendu {attendu!r}, obtenu {obtenu!r}")


# 1. Déjà dans le budget → inchangé.
courte = "La Fiera del Bue Grasso réunit éleveurs et visiteurs à Carrù, en Piémont."
assert len(courte) <= 156
_check("courte, dans le budget", _ajuste_meta_seo(courte), courte)

# 2. Une méta dans la fourchette 150-160 du prompt (donc DÉJÀ possiblement > 156,
#    le cas réel qui a déclenché l'alerte Yoast) → coupée au dernier mot entier.
meta_158 = ("Découvrez la Fiera del Bue Grasso à Carrù : concours bovin, dégustations, "
            "animations et défilé en centre-ville, chaque année en décembre, en Piémont, Italie.")
assert len(meta_158) > 156, f"le cas de test doit dépasser le budget Yoast ({len(meta_158)} car.)"
obtenu = _ajuste_meta_seo(meta_158)
_check("coupée à 156 caractères max", len(obtenu) <= 156, True)
_check("aucun mot coupé (préfixe exact du texte d'origine)",
       meta_158.startswith(obtenu.rstrip(" ,.;:—-")), True)
print(f"      (méta obtenue : {obtenu!r}, {len(obtenu)} caractères)")

# 3. Très longue (repli LLM verbeux) → coupée pareil, jamais d'exception.
tres_longue = ("La Fiera del Bue Grasso de Carrù rassemble chaque année, début décembre, "
               "des dizaines d'éleveurs piémontais venus présenter leurs meilleurs bovins, "
               "dans une ambiance de fête populaire mêlant dégustations, marché et défilé.")
obtenu = _ajuste_meta_seo(tres_longue)
_check("très longue : toujours ≤ 156", len(obtenu) <= 156, True)

# 4. Exactement 156 caractères → inchangé (pas de coupe pour rien).
pile_156 = "x" * 156
_check("exactement 156 caractères, inchangé", _ajuste_meta_seo(pile_156), pile_156)

# 5. Espaces parasites nettoyés avant mesure.
_check("espaces multiples nettoyés",
       _ajuste_meta_seo("La Fiera   del Bue  Grasso"), "La Fiera del Bue Grasso")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
