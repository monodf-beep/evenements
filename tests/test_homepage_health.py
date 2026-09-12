#!/usr/bin/env python3
"""Fixture : la surveillance de la home ne doit plus crier sur une page saine.

⚠️ AUCUN RÉSEAU : on donne à `_section_counts` un HTML fabriqué, calqué sur la structure
RÉELLE de la home relevée le 2026-08-13.

D'OÙ ÇA VIENT. Ce jour-là à 13h, l'alerte disait :

    🔴 Home Agenda Sabauda — section(s) vide(s) ou quasi :
    • « À la une » : 0 carte(s) · « En évidence » : 0 · « Les 7 prochains jours » : 0
    • « Ça vaut le déplacement » : 0 carte(s)

La page servait CINQUANTE liens de fiches. En la téléchargeant : dix sous « À la une »,
six sous le week-end, quatre sous le jour, trois sous « En évidence », quatre sous
« Ça vaut le déplacement ».

Trois causes empilées, et la fixture prend les trois :

  ① les titres cherchés ne sont PAS dans le HTML rendu — leurs seules occurrences sont
     dans le blob de configuration Elementor en tête de page, à 130 000 caractères des
     cartes. « Ça vaut le déplacement » n'y figure nulle part ;
  ② le compteur ADDITIONNAIT les occurrences d'un même titre au lieu d'en prendre le
     maximum : cinq occurrences de menu → cinq fenêtres vides → cinq zéros additionnés ;
  ③ les deux familles de marqueurs — `id=` de section (bloc continu) et classe de carte
     (dispersée) — se fragmentaient mutuellement les fenêtres.

Le fond du défaut est celui de toute la journée du 13/08 : le code faisait ce qui était
écrit, et c'est la SORTIE qui laissait croire autre chose. Ici elle a fait croire à une
panne du site.

Lancer : .venv/bin/python -m tests.test_homepage_health
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.homepage_health as hh  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


def _carte(slug: str) -> str:
    """Une carte réelle porte DEUX fois le même lien : l'image et le titre."""
    lien = f"https://agendasabauda.eu/evenement/{slug}/"
    return (f'<article class="cs-card"><a href="{lien}"><img></a>'
            f'<h3><a href="{lien}">{slug}</a></h3></article>')


def _page(sections: dict[str, int], cvld: int = 4, config_titres: bool = True) -> str:
    """HTML calqué sur la home réelle : un blob de configuration en tête où les TITRES
    apparaissent plusieurs fois, puis très loin les sections ancrées par `id=`."""
    tete = ""
    if config_titres:
        # ① et ② : les titres, cinq fois, uniquement dans la configuration.
        tete = ('<script>{"settings":{"title":"À la une","_element_id":"ala-une"}}</script>'
                '<!-- À la une --><!-- À la une --><!-- À la une --><!-- À la une -->'
                '<!-- En évidence --><!-- En évidence -->')
    tete += "<div>" + ("x" * 40000) + "</div>"      # les 130 000 caractères d'écart
    corps = []
    for anc, n in sections.items():
        corps.append(f'<section id="{anc}">')
        corps += [_carte(f"{anc}-fiche-{i}") for i in range(n)]
        corps.append("</section>" + ("y" * 2000))
    # ③ les cartes « Ça vaut le déplacement », DISPERSÉES : une au début, les autres loin.
    bloc_cvld = ""
    for i in range(cvld):
        bloc_cvld += (f'<div class="cs-cvld-card">{_carte(f"cvld-{i}")}</div>'
                      + ("z" * 5000))
    # une carte CVLD AVANT les sections, comme sur la vraie page (position 77 681)
    return tete + bloc_cvld[:6000] + "".join(corps) + bloc_cvld + \
        '<section id="cat-concerts">' + _carte("hors-perimetre") + "</section>"


print("──── 1. LE CAS QUI DOIT PASSER : une home saine ne déclenche rien ────")
html = _page({"ala-une": 10, "weekend": 6, "jour": 4, "evidence": 3, "venir": 4})
c = hh._section_counts(html)
for lib, anc, seuil in hh._SECTIONS:
    n = c.get(lib)
    _check(f"« {lib} » comptée peuplée ({n})", n is not None and n >= seuil, f"{n} < {seuil}")
_check("« Ça vaut le déplacement » comptée peuplée",
       (c.get("Ça vaut le déplacement") or 0) >= 2, str(c.get("Ça vaut le déplacement")))

print("\n──── 2. les titres du blob de configuration ne comptent pas ────")
_check("« À la une » rend bien 10 et non 0 — le titre du menu ne masque plus la section",
       c.get("À la une") == 10, str(c.get("À la une")))
_check("   et une carte compte UNE fois, pas deux (image + titre portent le même lien)",
       c.get("weekend") is None and c.get("Le week-end") == 6, str(c))

print("\n──── 3. les cartes dispersées ne fragmentent pas les sections à `id` ────")
_check("« Les 7 prochains jours » n'est pas retombée à 0 à cause des cartes CVLD",
       c.get("Les 7 prochains jours") == 4, str(c.get("Les 7 prochains jours")))

print("\n──── 4. une VRAIE section vide est toujours vue ────")
# C'est l'incident du 2026-07-31 : « À la une » affichait « Aucun événement ». Sans ce
# cas, la fixture ne prouverait que notre capacité à ne plus crier.
vide = _page({"ala-une": 0, "weekend": 6, "jour": 4, "evidence": 3, "venir": 4})
cv = hh._section_counts(vide)
_check("une section réellement vide rend 0", cv.get("À la une") == 0, str(cv.get("À la une")))
_check("   et les autres restent peuplées — l'alerte désigne la bonne",
       cv.get("Le week-end") == 6, str(cv))

print("\n──── 5. un marqueur ABSENT n'est pas une section vide ────")
sans = _page({"ala-une": 10, "weekend": 6, "jour": 4, "venir": 4})   # plus d'`evidence`
cs_ = hh._section_counts(sans)
_check("la section disparue rend None, pas 0", cs_.get("En évidence") is None,
       str(cs_.get("En évidence")))
_check("   (0 = vivier vide, None = le thème a changé : deux gestes différents)",
       cs_.get("À la une") == 10)
sans_cvld = _page({"ala-une": 10, "weekend": 6, "jour": 4, "evidence": 3, "venir": 4},
                  cvld=0)
_check("idem pour les cartes : classe absente → None",
       hh._section_counts(sans_cvld).get("Ça vaut le déplacement") is None)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
