#!/usr/bin/env python3
"""Fixture : `scripts.publisher_as._lang` décide sur l'ARTICLE effectivement publié,
jamais sur le `title` brut scrapé quand un article existe.

RÉCIDIVE EN PRODUCTION LE JOUR MÊME, 2026-09-04. WP#7472 (« Regine in Scena »,
signalée par Franck) venait d'être corrigée par `scripts.fix_titre_corps_langue` :
`article_title` et le corps de l'article passés en français. La republication qui a
suivi (sans `force_lang` — ce n'est pas une traduction) a fait revenir `_lang()` sur
`detect_lang(event['title'], event['description'], …)` : le `title` BRUT SCRAPÉ,
jamais retouché, restait italien. Polylang a donc réassigné la fiche côté IT — son
adresse s'est retrouvée préfixée `/it/` MALGRÉ un contenu entièrement français. Le
correctif de texte avait fonctionné, la republication qui le portait l'a défait.

`_lang()` délègue maintenant à `utils.lang.effective_lang`, qui préfère l'article
(article_title / enrich_data.article) au `title` brut — la même fonction dont se sert
déjà `scripts.translate_events` pour décider si une fiche a besoin d'être traduite.
Une seule fonction du dépôt tranche « dans quelle langue est cette fiche », pas deux
qui peuvent diverger.

Aucun réseau, fonction pure.

Lancer : .venv/bin/python -m tests.test_publisher_as_lang_effective
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publisher_as import _lang  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"  OK  {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label}" + (f" — {detail}" if detail else ""))


def _enrich_data(chapo, corps, titre):
    return json.dumps({"article": {"titre": titre, "chapo": chapo, "corps": corps}})


# ── 1. Cas réel WP#7472 : title brut IT, article_title/corps déjà FR → 'fr', pas 'it'.
ev_regine = {
    "title": "Regine in scena. L'arte del costume italiano tra cinema e teatro",
    "description": "",
    "territoire": "Piemonte",
    "article_title": "Les reines du costume. Comment le cinéma et le théâtre ont "
                     "construit l'image royale",
    "enrich_data": _enrich_data(
        "Les costumes proviennent d'ateliers de couture italiens qui ont habillé "
        "des actrices dans des films et des pièces de théâtre devenus des classiques.",
        "Cette exposition présente les plus belles créations de la mode italienne "
        "au cinéma et au théâtre, avec des pièces rares venues de plusieurs musées.",
        "Les reines du costume. Comment le cinéma et le théâtre ont construit "
        "l'image royale"),
}
_check("WP#7472 : 'fr' malgré un title brut resté italien", _lang(ev_regine) == "fr",
      _lang(ev_regine))

# ── 2. force_lang IMPOSÉ (traduction) : prime sur tout, même un article incohérent —
#      comportement inchangé, ne doit pas régresser.
ev_force = dict(ev_regine, force_lang="it")
_check("force_lang='it' : toujours imposé, jamais redevinée", _lang(ev_force) == "it")

# ── 3. Pas d'article enrichi (fiche jamais enrichie) : repli sur title/description
#      bruts, comportement historique inchangé.
ev_brut = {"title": "Sagra della Fiera di Vercelli", "description": "",
          "territoire": "Piemonte", "article_title": "", "enrich_data": ""}
_check("sans article : repli sur le title/description bruts (comportement historique)",
      _lang(ev_brut) == "it", _lang(ev_brut))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
