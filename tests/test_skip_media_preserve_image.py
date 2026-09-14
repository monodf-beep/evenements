#!/usr/bin/env python3
"""Fixture : `--skip-media` ne touche à AUCUNE image — pas même le méta qui en désigne une.

D'OÙ ÇA VIENT — 2026-09-10. Avant de republier 165 fiches en ligne pour leur poser les
liens interne/externe, j'ai demandé à Franck s'il avait édité des articles à la main dans
WordPress. Réponse : « non, juste les photos ». C'est exactement ce que la passe aurait
défait à moitié :

  • la VIGNETTE est protégée côté WordPress — sans `featured_media_id`, cs-publish.php
    n'entre dans son repli que si la fiche n'a PAS déjà d'image (`!has_post_thumbnail`) ;
  • mais `as_image_original`, le GRAND VISUEL de la fiche, partait quand même avec l'URL
    de la BASE, parce que `_build_payload` le posait inconditionnellement (l.608) et que
    le bloc qui le recalcule (l.825) ne s'exécute pas sous skip_media.

Résultat qu'on a évité : vignette corrigée à la main d'un côté, ancien grand visuel de
l'autre, sur la même fiche.

LE CAS QUI DOIT PASSER est le second : une passe NORMALE doit continuer à poser le méta,
sinon le correctif casserait la publication ordinaire.

Aucun réseau : on n'appelle que `_build_payload`, qui ne parle à personne.

Lancer : .venv/bin/python -m tests.test_skip_media_preserve_image
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publisher_as import _build_payload  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


EV = {
    "id": 1, "title": "Vespa. Icona italiana",
    "description": "Une exposition au MAUTO.",
    "url_source": "https://www.museoauto.com/vespa/",
    "url_image": "https://www.museoauto.com/wp-content/uploads/affiche-vespa.jpg",
    "ville": "Torino", "territoire": "Piemonte", "lieu": "MAUTO",
    "date_event_start": "2099-10-01", "date_event_end": "2099-12-31",
    "llm_categorie": "Expositions & Patrimoine", "llm_score": 8,
    "wp_post_id_as": 3433,
}

# ── skip_media : le méta d'image ne doit PAS partir ────────────────────────────────
p = _build_payload(EV, skip_media=True)
verifier("skip_media : as_image_original ABSENT du payload",
         "as_image_original" not in p["meta"], str(list(p["meta"].keys())[-6:]))
verifier("skip_media : le reste du payload est bien là (texte, titre)",
         p.get("title") and p.get("content") is not None)
verifier("skip_media : les métas qui ne portent pas d'image sont conservées",
         "as_tarif" in p["meta"] and "as_lieu" in p["meta"])

# ── LE CAS QUI DOIT PASSER : passe normale, le méta est posé ───────────────────────
p2 = _build_payload(EV, skip_media=False)
verifier("passe normale : as_image_original PRÉSENT (rien n'est cassé)",
         p2["meta"].get("as_image_original") == EV["url_image"],
         str(p2["meta"].get("as_image_original")))
verifier("défaut sans argument = passe normale (compatibilité des appelants)",
         "as_image_original" in _build_payload(EV)["meta"])

# ── Contre-épreuve : une image qui est un LOGO reste vidée, pas absente ────────────
EV_LOGO = {**EV, "url_image": "https://exemple.fr/logo.png"}
p3 = _build_payload(EV_LOGO, skip_media=False)
verifier("passe normale sur un logo : méta présent mais vide (comportement d'origine)",
         p3["meta"].get("as_image_original") == "", repr(p3["meta"].get("as_image_original")))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
