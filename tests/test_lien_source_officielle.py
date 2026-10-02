#!/usr/bin/env python3
"""Fixture : `scripts.publisher_as.lien_source_officielle` — UN lien externe en fin de
corps vers la source officielle (décision de Franck du 2026-09-09, tableau Yoast/doctrine
ligne 5), jamais une liste, jamais sans URL publiable.

Cas :
  ① URL publiable, FR    → lien, libellé « Site officiel : <domaine> » ;
  ② même URL, IT         → « Sito ufficiale » ;
  ③ URL vide             → '' (une fiche radar sans page officielle n'a pas de lien : la
                            charte §8 tient parce que l'URL vient de _source_publiable) ;
  ④ LE CAS QUI DOIT PASSER : le domaine affiché retire « https://www. » mais garde un
     sous-domaine réel (« agenda.ville.fr »), et le lien pointe vers l'URL complète ;
  ⑤ langue inattendue    → repli FR, pas d'exception.

Aucun réseau, fonction pure. Lancer : .venv/bin/python -m tests.test_lien_source_officielle
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publisher_as import lien_source_officielle  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


u = "https://www.museoauto.com/eventi/vespa-icona-italiana/"
out = lien_source_officielle(u, "fr")
_check("① FR : lien vers l'URL complète", f'href="{u}"' in out, out)
_check("① FR : libellé avec le domaine", "Site officiel : museoauto.com" in out, out)
_check("② IT : libellé italien", "Sito ufficiale : museoauto.com" in lien_source_officielle(u, "it"))
_check("③ URL vide → aucun lien", lien_source_officielle("", "fr") == "")
_check("③ URL None → aucun lien", lien_source_officielle(None, "fr") == "")
out = lien_source_officielle("http://agenda.ville-thonon.fr/spectacles/2026", "fr")
_check("④ sous-domaine réel conservé dans le libellé", "agenda.ville-thonon.fr" in out, out)
_check("④ … et le lien reste l'URL complète", 'href="http://agenda.ville-thonon.fr/spectacles/2026"' in out)
_check("⑤ langue inattendue → repli FR", "Site officiel" in lien_source_officielle(u, "de"))
_check("un seul <a> par lien (pas une liste)", out.count("<a ") == 1)

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
