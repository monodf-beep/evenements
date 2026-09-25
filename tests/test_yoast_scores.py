#!/usr/bin/env python3
"""Fixture : le moteur de Yoast hors navigateur (scripts/yoast_score.js) reproduit la note
que l'ÉDITEUR a donnée — sur des fiches réelles, pas sur des cas construits.

LES TÉMOINS (tests/fixtures/yoast_temoins.json, contenu et métas copiés tels quels par la
route cs/v1/yoast-papers le 16/09/2026) :

  - WP#8236 (Nice) et WP#8231 (Aoste) : notes LUES DANS L'ÉDITEUR le jour même, par un
    agent qui a ouvert les deux fiches et recopié le panneau ligne par ligne — 86 / 60 et
    85 / 30. Ce sont les seuls témoins dont la note vient du navigateur et non d'une méta
    stockée qui pourrait être périmée ;
  - WP#2418, 2420, 8249 : notes stockées par l'éditeur, fiches non modifiées depuis.

Le premier témoin (WP#7490, 67 / 90) a été retiré le 16/09 au soir : sa note stockée datait
d'AVANT sa dernière modification (09/09), et le moteur rendait 71 — un témoin périmé qui
aurait fait ajuster le moteur sur une note fausse.

Trois écarts trouvés en calibrant, que ces témoins verrouillent (détail dans l'en-tête de
scripts/yoast_score.js) : l'éditeur analyse avec la locale du SITE (fr_FR) même un texte
italien ; il ajoute l'image mise en avant au texte analysé ; et « Expression clé utilisée
précédemment » est un greffon qui compte dans la note. Retirer l'un des trois fait
retomber un témoin à côté — c'est le but : si le moteur ne retrouve plus une note, ce n'est
pas la fixture qu'il faut ajuster, c'est le moteur (version du paquet, largeur du titre).

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


temoins = json.loads((ROOT / "tests" / "fixtures" / "yoast_temoins.json").read_text(encoding="utf-8"))
notes = {r["id"]: r for r in noter(temoins)}

for t in temoins:
    r = notes[t["id"]]
    if t.get("attendu_detail"):
        # Témoin par le DÉTAIL : l'éditeur n'affiche pas la note globale d'une page, mais
        # ses lignes. WP#2595 n'est qu'un shortcode ; l'éditeur le voit VIDE (« 0 mot »).
        detail = {d["id"]: d["score"] for d in r["seo_detail"]}
        for cle, attendu in t["attendu_detail"].items():
            verifier(f"WP#{t['id']} : {cle} = {attendu} comme dans l'éditeur", detail.get(cle) == attendu,
                     f"obtenu {detail.get(cle)}")
        continue
    verifier(f"WP#{t['id']} : SEO {t['attendu_seo']} retrouvé à l'unité",
             r["seo"] == t["attendu_seo"], f"obtenu {r['seo']}")
    verifier(f"WP#{t['id']} : lisibilité {t['attendu_lisibilite']} retrouvée",
             r["lisibilite"] == t["attendu_lisibilite"], f"obtenu {r['lisibilite']}")

nice = next(t for t in temoins if t["id"] == 8236)
r_nice = notes[8236]
verifier("le détail nomme les assesseurs (pour lire un écart, pas seulement le constater)",
         any(d["id"] == "keyphraseDensity" for d in r_nice["seo_detail"]))

# Contre-épreuves : chaque chose que le moteur prend en compte doit peser sur la note.
[faux] = noter([{**nice, "keyword": "carnaval de Venise"}])
verifier("clé absente du texte : la note SEO baisse", faux["seo"] < r_nice["seo"], f"{faux['seo']} vs {r_nice['seo']}")

[sans_image] = noter([{**nice, "featured_html": ""}])
verifier("sans image mise en avant : l'assesseur images ne dit plus « bon travail »",
         any(d["id"] == "images" and d["score"] < 9 for d in sans_image["seo_detail"]),
         str([(d["id"], d["score"]) for d in sans_image["seo_detail"] if d["id"] == "images"]))

[deja] = noter([{**nice, "kw_utilisee_ailleurs": 2}])
verifier("clé déjà utilisée sur deux autres fiches : la note SEO baisse", deja["seo"] < r_nice["seo"],
         f"{deja['seo']} vs {r_nice['seo']}")

# Cas qui doit PASSER près de la frontière : WP#8236 est un texte ITALIEN (« Tre curiosità
# di Nizza »), que l'éditeur note 60 en lisibilité parce qu'il le juge avec les règles
# françaises (aucun mot de transition français dedans). Jugé en italien, le même texte
# monte à 90 : c'est la preuve que la locale servie est bien ce qui fait la note, et que
# le moteur italien se charge. Si un jour Yoast se met à analyser dans la langue du post,
# c'est ce témoin qui tombera le premier — et il faudra alors servir post_locale.
[ri] = noter([{**nice, "locale": "it_IT"}])
verifier("locale it_IT : le moteur italien se charge et rend une note SEO entre 0 et 100", 0 <= ri["seo"] <= 100, str(ri["seo"]))
verifier("locale it_IT : lisibilité dans les paliers de Yoast", ri["lisibilite"] in (0, 30, 60, 90), str(ri["lisibilite"]))
verifier("locale it_IT : le texte italien de Nice passe de 60 (règles françaises) à 90 (règles italiennes)",
         ri["lisibilite"] == 90 and r_nice["lisibilite"] == 60, f"{r_nice['lisibilite']} → {ri['lisibilite']}")

# Contre-épreuve du shortcode : SANS la liste, le moteur lit « [cs_hub_ville …] » comme du
# texte et la densité passe à 9 — c'est exactement ce que faisait le moteur avant le 17/09.
page = next(t for t in temoins if t["id"] == 2595)
[sans_liste] = noter([{**page, "shortcodes": []}])
verifier("shortcode non déclaré : la densité n'est plus celle de l'éditeur (contre-épreuve)",
         {d["id"]: d["score"] for d in sans_liste["seo_detail"]}.get("keyphraseDensity") != 4)

# Sans expression clé, pas de note SEO — et surtout pas une note négative. Premier
# passage en vrai (17/09, 00h15) : 107 fiches sur 300 rendaient -637, refusées par la
# route, et se seraient représentées chaque jour à l'identique. Le moteur rend null,
# la lisibilité reste calculée.
[sans_cle] = noter([{**nice, "keyword": ""}])
verifier("sans expression clé : la note SEO vaut null, pas un nombre négatif", sans_cle["seo"] is None, str(sans_cle["seo"]))
verifier("sans expression clé : la lisibilité est quand même notée",
         sans_cle["lisibilite"] == r_nice["lisibilite"], f"{sans_cle['lisibilite']} vs {r_nice['lisibilite']}")

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
