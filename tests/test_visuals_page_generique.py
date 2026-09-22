#!/usr/bin/env python3
"""Fixture : depuis une page GÉNÉRIQUE, l'agent vision devient obligatoire.

2026-09-21. Une page d'accueil montre la programmation DU MOMENT : elle illustre bien
l'événement en cours et mal tous les autres. Mesuré le même jour dans les deux sens —
sur les 22 racines servant de source à des fiches à venir, les neuf og:image trouvées
étaient toutes de l'habillage (fond de page admin, affiche de saison périmée, logo,
façade) ; mais sur les cinq fiches publiées concernées, trois avaient une BONNE image,
dont l'affiche exacte de l'exposition prise sur la home de la mairie de Villefranche.

La règle n'est donc pas « jamais », c'est « pas sans que quelqu'un REGARDE » :
  • avec un agent vision, `resolve_image` lit la page générique et l'agent tranche ;
  • sans agent vision, il s'abstient — mieux vaut la bannière qu'un pari.

Aucun réseau, aucun appel de modèle : les accès extérieurs sont remplacés ici même.
Lancer : .venv/bin/python -m tests.test_visuals_page_generique
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.visuals as vz  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


OG = "https://www.villefranche-sur-mer.fr/uploads/affiche-artistes-villefranchois.jpg"

# ── Tout ce qui sort du process est remplacé ────────────────────────────────────────
vz.fetch_og_image = lambda url, *a, **k: OG
vz.fetch_content_image = lambda url, *a, **k: ""
vz.remote_dims = lambda url, *a, **k: (1200, 800)      # ni bandeau, ni carré, ≥ MIN_DIM
vz._verified = lambda url, ev, vc, vm, subject="": (True, 0.5, 0.5)
vz.image_verify.load_blocked_patterns = lambda: []


def _resoudre(url_source: str, titre: str, verify_client):
    ev = {"id": 1, "title": titre, "url_source": url_source, "url_image": "",
          "image_source": "", "territoire": "", "llm_categorie": ""}
    # client=None : pas de Commons ni d'agent web. cat_banners={} : pas de bannière non
    # plus, donc une source vide signifie « la chaîne n'a RIEN retenu », sans ambiguïté.
    return vz.resolve_image(ev, None, set(), verify_client=verify_client, cat_banners={})


print("──── page d'ÉVÉNEMENT : rien ne change ────")
url, _, src, _, _ = _resoudre("https://www.villefranche-sur-mer.fr/evenement/les-artistes/",
                              "Exposition des Artistes villefranchois", None)
_check("og:image retenue, même sans agent vision", src == "og" and url == OG, f"{src!r}")

print("\n──── page GÉNÉRIQUE (racine de la mairie) ────")
url, _, src, _, _ = _resoudre("https://www.villefranche-sur-mer.fr/",
                              "Exposition des Artistes villefranchois", None)
_check("sans agent vision → on s'abstient (pas d'image posée au hasard)",
       src == "" and url == "", f"{src!r} {url!r}")

url, _, src, _, _ = _resoudre("https://www.villefranche-sur-mer.fr/",
                              "Exposition des Artistes villefranchois", verify_client=object())
_check("avec agent vision → la page est lue, l'agent tranche, l'affiche est retenue",
       src == "og" and url == OG, f"{src!r}")

print("\n──── rubrique presse : même règle ────")
url, _, src, _, _ = _resoudre("https://www.malrauxchambery.fr/ressources/presse",
                              "Charcot Antartica, un concert-récit", None)
_check("sans agent vision → abstention", src == "", f"{src!r}")

print("\n──── le site EST l'événement : sa racine reste une page d'événement ────")
url, _, src, _, _ = _resoudre("https://beercult.it/", "BeerCult 2026", None)
_check("og:image retenue sans agent vision", src == "og", f"{src!r}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
