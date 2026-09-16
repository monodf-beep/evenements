#!/usr/bin/env python3
"""Fixture : le moteur de Yoast hors navigateur (scripts/yoast_score.js) reproduit la note
que l'ÉDITEUR a donnée — sur une fiche réelle, pas sur un cas construit.

LE TÉMOIN : WP#7490, « La Filarmonica della Scala en concert au Lingotto de Turin »,
notée 67 (SEO) et 90 (lisibilité) par Yoast dans le navigateur, contenu et métas copiés
tels quels le 16/09/2026 (tests/fixtures/yoast_temoin_7490.json). C'est la seule des
seize fiches notées du site dont la note stockée n'était pas périmée ; le moteur doit la
retrouver à l'unité près. S'il ne la retrouve plus, ce n'est pas la fixture qu'il faut
ajuster, c'est le moteur (version du paquet, estimation de la largeur du titre).

Le moteur italien doit se charger aussi, et une mauvaise clé doit faire baisser la note :
un moteur qui rendrait la même note quelle que soit la clé ne mesurerait rien.

Prérequis : node ≥ 20 et `npm install` (paquet `yoastseo`). Sans eux la fixture ÉCHOUE —
un témoin qui se déclare vert faute d'outil est un témoin qui ne prouve rien.

Lancer : .venv/bin/python -m tests.test_yoast_scores
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOTEUR = ROOT / "scripts" / "yoast_score.js"
echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


def noter(entrees):
    node = shutil.which("node")
    if not node:
        raise SystemExit("ÉCHEC : `node` introuvable — Node ≥ 20 est requis.")
    proc = subprocess.run([node, str(MOTEUR)], input=json.dumps(entrees, ensure_ascii=False),
                          capture_output=True, text=True, cwd=str(ROOT), timeout=120)
    if proc.returncode != 0:
        raise SystemExit("ÉCHEC : le moteur a échoué — " + proc.stderr.strip()[:400]
                         + "\n(`npm install` a-t-il été lancé dans le dépôt ?)")
    return json.loads(proc.stdout)


temoin = json.loads((ROOT / "tests" / "fixtures" / "yoast_temoin_7490.json").read_text(encoding="utf-8"))
attendu_seo, attendu_lis = int(temoin["linkdex"]), int(temoin["content_score"])

[r] = noter([temoin])
verifier(f"témoin WP#7490 : SEO {attendu_seo} retrouvé à l'unité", r["seo"] == attendu_seo, f"obtenu {r['seo']}")
verifier(f"témoin WP#7490 : lisibilité {attendu_lis} retrouvée", r["lisibilite"] == attendu_lis, f"obtenu {r['lisibilite']}")
verifier("le détail nomme les assesseurs (pour lire un écart, pas seulement le constater)",
         any(d["id"] == "keyphraseDensity" for d in r["seo_detail"]))

# Contre-épreuve : une clé absente du texte doit faire baisser la note SEO.
[faux] = noter([{**temoin, "keyword": "carnaval de Venise"}])
verifier("clé absente du texte : la note SEO baisse", faux["seo"] < r["seo"], f"{faux['seo']} vs {r['seo']}")

# L'italien : le moteur se charge, note dans les bornes, et la clé compte aussi.
it = {"id": 1, "locale": "it_IT", "keyword": "curiosità di Torino",
      "title": "Sei curiosità di Torino che i torinesi stessi dimenticano",
      "description": "Sei curiosità di Torino, da Piazza San Carlo a Collegno: duemila anni sotto il selciato.",
      "slug": "curiosita-torino", "permalink": "https://agendasabauda.eu/it/curiosita-torino/",
      "date": "Sep 6, 2026", "post_title": "Sei curiosità di Torino",
      "content": "<p>Torino nasconde sei curiosità di Torino che vanno oltre il centro barocco. "
                 "Alcune dormono sotto il selciato da duemila anni.</p><h2>Sotto la piazza</h2>"
                 "<p>Piazza San Carlo fa da salotto alla città dal Seicento. Nessuno si aspettava di trovare granché.</p>"}
[ri] = noter([it])
verifier("italien : le moteur rend une note SEO entre 0 et 100", 0 <= ri["seo"] <= 100, str(ri["seo"]))
verifier("italien : lisibilité dans les paliers de Yoast", ri["lisibilite"] in (0, 30, 60, 90), str(ri["lisibilite"]))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
