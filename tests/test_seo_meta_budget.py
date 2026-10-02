#!/usr/bin/env python3
"""Fixture : `utils.seo._ajuste_meta_seo` fait rentrer une méta description dans le
budget RÉEL de Yoast sans jamais couper un mot en deux — et ce budget n'est PAS 156.

TROUVÉ le 2026-09-16 en lisant le code de Yoast sur le serveur : la longueur mesurée est
`description + date + 3`, la date au format « Sep 6, 2026 », ajoutée sans condition à
tout contenu daté. Le plafond utile est 140 (156 − « Juil 21, 2026 » − 3). Mesuré sur le
site : 202 des 276 fiches événements avec description dépassaient, toutes écrites « dans
le budget » de 156 — c'est le cas de la faute qui se voit dans les RÉSULTATS et pas dans
le code. Et la coupe préfère désormais la fin d'une phrase à la fin d'un mot.

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

from utils.seo import _ajuste_meta_seo, _META_SEO_CIBLE  # noqa: E402
assert _META_SEO_CIBLE == 140, _META_SEO_CIBLE

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
assert len(courte) <= 140
_check("courte, dans le budget", _ajuste_meta_seo(courte), courte)

# 2. Une méta dans la fourchette 150-160 du prompt (donc DÉJÀ possiblement > 156,
#    le cas réel qui a déclenché l'alerte Yoast) → coupée au dernier mot entier.
meta_158 = ("Découvrez la Fiera del Bue Grasso à Carrù : concours bovin, dégustations, "
            "animations et défilé en centre-ville, chaque année en décembre, en Piémont, Italie.")
assert len(meta_158) > 140, f"le cas de test doit dépasser le budget Yoast ({len(meta_158)} car.)"
obtenu = _ajuste_meta_seo(meta_158)
_check("coupée à 140 caractères max", len(obtenu) <= 140, True)
_check("aucun mot coupé (préfixe exact du texte d'origine)",
       meta_158.startswith(obtenu.rstrip(" ,.;:—-")), True)
print(f"      (méta obtenue : {obtenu!r}, {len(obtenu)} caractères)")

# 3. Très longue (repli LLM verbeux) → coupée pareil, jamais d'exception.
tres_longue = ("La Fiera del Bue Grasso de Carrù rassemble chaque année, début décembre, "
               "des dizaines d'éleveurs piémontais venus présenter leurs meilleurs bovins, "
               "dans une ambiance de fête populaire mêlant dégustations, marché et défilé.")
obtenu = _ajuste_meta_seo(tres_longue)
_check("très longue : toujours ≤ 140", len(obtenu) <= 140, True)

# 4. Exactement 140 caractères → inchangé (pas de coupe pour rien).
pile_140 = "x" * 140
_check("exactement 140 caractères, inchangé", _ajuste_meta_seo(pile_140), pile_140)

# 4 bis. LE CAS RÉEL DU 16/09 — WP#14, 144 caractères, « dans le budget » de 156, orange
#        chez Yoast une fois la date comptée. La coupe recule à la fin de la PHRASE, pas
#        au dernier mot : « …28 septembre 2026. Peinture et haute » serait un mot entier
#        et une description qui se lit comme une faute.
wp14 = ("Matisse Yves Saint Laurent Nice : exposition au Musée Matisse de Cimiez, du 17 juin "
        "au 28 septembre 2026. Peinture et haute couture en dialogue.")
assert 140 < len(wp14) <= 156, len(wp14)
_check("144 caractères : coupée à la fin de la phrase",
       _ajuste_meta_seo(wp14),
       "Matisse Yves Saint Laurent Nice : exposition au Musée Matisse de Cimiez, du 17 juin "
       "au 28 septembre 2026.")

# 4 ter. LE CAS QUI DOIT PASSER, près de la frontière : la seule fin de phrase disponible
#        est trop tôt (sous le plancher de 100) — on ne rend pas une description de
#        quarante caractères, on coupe au mot comme avant.
tot = ("Fiera del Bue Grasso à Carrù. Concours bovin de race piémontaise, dégustations, "
       "défilé des bêtes en centre-ville et marché des producteurs, chaque année en décembre.")
assert len(tot) > 140
obtenu = _ajuste_meta_seo(tot)
_check("fin de phrase trop tôt : coupe au mot, pas à 29 caractères", len(obtenu) > 100 and len(obtenu) <= 140, True)
print(f"      (méta obtenue : {obtenu!r}, {len(obtenu)} caractères)")

# 5. Espaces parasites nettoyés avant mesure.
_check("espaces multiples nettoyés",
       _ajuste_meta_seo("La Fiera   del Bue  Grasso"), "La Fiera del Bue Grasso")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
