#!/usr/bin/env python3
"""Fixture : l'expression clé doit exister DANS le texte, et un <h2> doit la porter.

D'OÙ ÇA VIENT — 2026-09-10. Franck : « je te dis qu'on a peu de vert pour le SEO des
événements ». Mesuré ce jour-là sur deux fiches en ligne passées toutes deux par
`seo_batch` :

  WP#772  Foire de Saint-Ours     250 mots, 1 sous-titre (« Programme »)  → vert
  WP#2283 Fiera del Bue Grasso    243 mots, 0 sous-titre                  → rouge

Deux causes, aucune stochastique :
  1. la clé rendue par le LLM était « Fiera del Bue Grasso Carrù » alors que le corps
     — écrit AVANT le choix de la clé — dit « Fiera del Bue Grasso DI Carrù ». Une
     préposition d'écart, et Yoast compte ZÉRO occurrence : intro, densité et sous-titre
     rouges d'un coup ;
  2. le corps ne pose un « ## » que « si vraiment nécessaire » (prompt d'enrich), donc la
     plupart des fiches n'ont aucun sous-titre où la clé pourrait figurer.

Aucun réseau : `recale_keyphrase` et `titre_liens` ne parlent à personne.

Lancer : .venv/bin/python -m tests.test_seo_cle_et_soustitre
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.seo import recale_keyphrase, cle_dans_texte  # noqa: E402
from scripts.publisher_as import titre_liens  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# ── LE CAS QUI DOIT PASSER, choisi près de la frontière ────────────────────────────
# Une clé DÉJÀ présente telle quelle ne doit pas bouger d'un caractère : c'est le cas
# ordinaire (la grande majorité des fiches), et le recalage ne doit pas l'abîmer.
TXT_OK = ("La Foire de Saint-Ours se tient les 30 et 31 janvier 2027 dans le centre "
          "historique d'Aoste, entre la Porta Praetoria et l'Arc d'Auguste.")
verifier("clé déjà présente : rendue INCHANGÉE",
         recale_keyphrase("Foire de Saint-Ours", TXT_OK) == "Foire de Saint-Ours",
         repr(recale_keyphrase("Foire de Saint-Ours", TXT_OK)))
verifier("clé déjà présente : accents et casse ne comptent pas",
         cle_dans_texte("foire de saint ours", TXT_OK))

# ── Le cas réel qui a motivé le correctif (WP#2283) ────────────────────────────────
TXT_BUE = ("La Fiera del Bue Grasso di Carrù, foire aux bovins de race piémontaise "
           "organisée par l'office de tourisme de Carrù, est annoncée pour le "
           "17 décembre 2026, au foro boario.")
verifier("préposition manquante : la clé est recalée sur le texte",
         recale_keyphrase("Fiera del Bue Grasso Carrù", TXT_BUE)
         == "Fiera del Bue Grasso di Carrù",
         repr(recale_keyphrase("Fiera del Bue Grasso Carrù", TXT_BUE)))
verifier("après recalage, la clé est bien DANS le texte (ce que Yoast mesure)",
         cle_dans_texte(recale_keyphrase("Fiera del Bue Grasso Carrù", TXT_BUE), TXT_BUE))

# ── Ce que le recalage ne doit PAS faire ───────────────────────────────────────────
# On ne saute JAMAIS un mot porteur de sens : « Foire Saint-Ours » sur un texte qui dit
# « Foire d'hiver de Saint-Ours » désignerait autre chose. Clé rendue inchangée.
verifier("mot plein intercalé : clé inchangée, rien n'est fabriqué",
         recale_keyphrase("Foire Saint-Ours", "La Foire d'hiver de Saint-Ours à Aoste.")
         == "Foire Saint-Ours")
verifier("clé totalement absente : clé inchangée",
         recale_keyphrase("Carnaval de Venise", TXT_OK) == "Carnaval de Venise")
verifier("texte vide : clé inchangée (fiche sans article rédigé)",
         recale_keyphrase("Foire de Saint-Ours", "") == "Foire de Saint-Ours")
verifier("clé vide : rien à recaler", recale_keyphrase("", TXT_OK) == "")

# ── Le sous-titre qui porte la clé ─────────────────────────────────────────────────
h = titre_liens("Fiera del Bue Grasso di Carrù", "it")
verifier("h2 italien : balise h2 et clé dedans",
         h.startswith("<h2>") and "Fiera del Bue Grasso di Carrù" in h, h)
h_fr = titre_liens("Foire de Saint-Ours", "fr")
verifier("h2 français : clé + libellé français",
         "Foire de Saint-Ours : en savoir plus" in h_fr, h_fr)
verifier("langue inconnue : repli français, jamais de balise vide",
         titre_liens("Foire de Saint-Ours", "xx") == h_fr)
verifier("sans clé (fiche pas encore passée par seo_batch) : titre générique quand même",
         titre_liens("", "fr") == "<h2>En savoir plus</h2>"
         and titre_liens("", "it") == "<h2>Per saperne di più</h2>")
verifier("clé contenant un chevron : échappée, jamais de HTML injecté",
         "<b>" not in titre_liens("Foire <b>", "fr"))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
