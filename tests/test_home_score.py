#!/usr/bin/env python3
"""Fixture : la formule du score de rendu, déplacée d'enrich vers utils/home_score, rend
EXACTEMENT ce qu'enrich rendait — et rescore_home ne calcule que ce qu'il peut.

LE CAS QUI DOIT PASSER vient de la production : WP#8193, journal d'enrich du 10/09 —
« score home=8.1 (panel=4.0, source=True, affiches=photo officielle) ». Si la fonction
déplacée ne rend pas 8.1 sur ces entrées, c'est qu'elle a bougé en déménageant.

Lancer : .venv/bin/python -m tests.test_home_score
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.home_score import calculer, photo_officielle  # noqa: E402
from scripts.rescore_home import evaluer                 # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# ── LE CAS RÉEL (journal d'enrich, WP#8193) ────────────────────────────────────────
h = calculer(4.0, True, False, False, True)
verifier("WP#8193 : panel 4.0 + source + photo officielle → 8.1, comme le journal",
         h["score"] == 8.1 and h["affiches"] == "photo officielle", str(h))
verifier("… et son placement dit « photo du site officiel »", "photo du site officiel" in h["placement"])

# ── La frontière du seuil 6 ─────────────────────────────────────────────────────────
verifier("panel 2.5 + source + photo → 6.25 : passe le seuil",
         calculer(2.5, True, False, False, True)["score"] == 6.2 or calculer(2.5, True, False, False, True)["score"] == 6.3,
         str(calculer(2.5, True, False, False, True)["score"]))
verifier("panel 2.5 + source, SANS visuel → 5.5 : sous le seuil",
         calculer(2.5, True, False, False, False)["score"] == 5.5)
verifier("deux affiches + panel 5 + source → 10, plafonné", calculer(5.0, True, True, True, False)["score"] == 10.0)
verifier("hero réservé au combo d'affiches : 8+ avec une seule affiche n'est PAS hero",
         "hero" not in calculer(5.0, True, True, False, False)["placement"])
verifier("panel None compte 0 dans la formule (mais rescore refuse AVANT, voir plus bas)",
         calculer(None, True, False, False, False)["score"] == 2.5)

# ── Photo officielle : domaines, www ignoré, URL nue acceptée ─────────────────────
verifier("photo sur le domaine officiel (www ignoré) → officielle",
         photo_officielle("https://www.fortedibard.it/x.jpg", ["https://fortedibard.it/eventi/"]))
verifier("hôte donné sans schéma (url_officiel nu) → reconnu",
         photo_officielle("https://fortedibard.it/x.jpg", ["fortedibard.it"]))
verifier("photo d'un autre domaine → pas officielle",
         not photo_officielle("https://cdn.exemple.fr/x.jpg", ["https://fortedibard.it/"]))
verifier("sans image → pas officielle", not photo_officielle("", ["https://fortedibard.it/"]))

# ── rescore_home.evaluer : relit enrich_data, traite les affiches comme absentes ───
ev = {"enrich_data": json.dumps({"reader_panel": {"mean": 4.0},
                                 "source": {"officielle": True, "pages": ["https://www.fortedibard.it/eventi/pinocchio/"]}}),
      "url_image": "https://fortedibard.it/img/pinocchio.jpg", "url_officiel": ""}
h, motif = evaluer(ev)
verifier("Pinocchio (panel 4.0, source, photo du site) → 8.1 recalculé sans LLM", h and h["score"] == 8.1, str(h))
verifier("le bloc dit qu'il est un PLANCHER (affiches non conservées)", h and "plancher" in h["affiches_note"])
verifier("SANS panel → None, motif → enrich (on n'invente pas 6 points sur 10)",
         evaluer({"enrich_data": json.dumps({"source": {"officielle": True}}), "url_image": ""})[0] is None)
verifier("enrich_data illisible → None, pas d'exception",
         evaluer({"enrich_data": "{pas du json", "url_image": ""})[0] is None)

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
