#!/usr/bin/env python3
"""Fixture : l'illustration de la RUBRIQUE presse n'est pas l'affiche de l'événement.

Incident du 2026-09-05, fiche 5256 « Festival Verismo » (WP#8145) : la page /area-stampa
du Teatro Regio de Turin porte une photo de couverture « press-release-web.jpg » — un
portable affichant PRESS RELEASE, banque d'images. `extract_press_visuals` l'a prise pour
l'affiche (chemin « area-stampa » = dossier de presse, 15 points), mesurée paysage, posée
en url_image ET url_image_wide : le grand visuel 16:9 de la fiche publiée. L'audit visuel
du lendemain l'a signalée ; personne n'a agi dessus.

Deux garde-fous, vérifiés ici SANS réseau (remote_dims remplacé) :
  1. un NOM DE FICHIER qui désigne la rubrique presse est écarté — mais seulement le nom :
     un chemin /comunicato-stampa/8422/…/locandina.jpg reste éligible (cas près de la
     frontière qui DOIT passer, règle 3 de CLAUDE.md) ;
  2. `_affiches_verifiees` fait regarder les affiches par l'agent vision avant écriture
     (vérificateur injecté ici).

Lancer : .venv/bin/python -m tests.test_press_visuals
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import images  # noqa: E402
from scripts.enrich import extract_press_visuals, _affiches_verifiees  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


REGIO = "https://www.teatroregio.torino.it"
PRESS_RELEASE = f"{REGIO}/sites/default/files/styles/full/public/uploads/page/64/cover/press-release-web.jpg"
LOCANDINA_KIT = f"{REGIO}/sites/default/files/uploads/comunicato-stampa/8422/file/festival-verismo-locandina.jpg"
LOCANDINA_STAMPA = f"{REGIO}/sites/default/files/uploads/opera/8187/locandina-stampa.jpg"
COVER_OPERA = f"{REGIO}/sites/default/files/styles/half/public/uploads/opera/8187/cover/VERISMO_0.jpg"
COMUNICATO_IMG = f"{REGIO}/sites/default/files/uploads/page/64/comunicato-stampa.jpg"

# Dimensions « mesurées » sans réseau : la rubrique et la vraie couverture font toutes deux
# 1920×960 (même gabarit Drupal « full ») — la taille ne les distingue pas, seul le nom.
DIMS = {
    PRESS_RELEASE: (1920, 960),
    LOCANDINA_KIT: (800, 1200),
    LOCANDINA_STAMPA: (800, 1200),
    COVER_OPERA: (1920, 960),
    COMUNICATO_IMG: (1920, 960),
}
images.remote_dims = lambda u, *a, **k: DIMS.get(u.split("?")[0], (0, 0))

AREA_STAMPA = f'''<html><body>
<a href="{PRESS_RELEASE}?itok=OVFG2XaS"><img src="{PRESS_RELEASE}?itok=OVFG2XaS"></a>
<h2>Festival Verismo – Inaugurazione della Stagione 2026/2027</h2>
<a href="/sites/default/files/uploads/comunicato-stampa/8422/file/festival-verismo-locandina.jpg">Locandina</a>
<a href="/sites/default/files/uploads/comunicato-stampa/8422/file/comunicato.pdf">Comunicato stampa</a>
</body></html>'''

# ── 1. Le cas de l'incident : la rubrique est écartée, la pièce jointe du communiqué passe
vis = extract_press_visuals([{"url": f"{REGIO}/area-stampa", "html": AREA_STAMPA}],
                            title="Festival Verismo")
_check("press-release-web.jpg n'est plus l'affiche paysage", vis.get("wide") is None, str(vis))
_check("la locandina du communiqué (chemin comunicato-stampa, nom neutre) est retenue",
       vis.get("portrait") == LOCANDINA_KIT, str(vis))
_check("elle vient du dossier de presse → poster + from_kit",
       vis.get("poster") == LOCANDINA_KIT and vis.get("from_kit") is True, str(vis))

# ── 2. Près de la frontière, côté PASSE : « stampa » dans un nom d'affiche = version print
PAGE_STAMPA = f'<a href="{LOCANDINA_STAMPA}">Locandina per la stampa</a>'
vis = extract_press_visuals([{"url": f"{REGIO}/area-stampa", "html": PAGE_STAMPA}],
                            title="Festival Verismo")
_check("locandina-stampa.jpg (version print) reste éligible", vis.get("portrait") == LOCANDINA_STAMPA, str(vis))

# ── 3. La couverture de l'opéra sur la page programme (hors dossier) passe toujours
PAGE_PROG = f'<img src="{COVER_OPERA}?h=2538f4e7&itok=qecySme8" alt="Festival Verismo">'
vis = extract_press_visuals([{"url": f"{REGIO}/programma/festival-verismo", "html": PAGE_PROG}],
                            title="Festival Verismo")
_check("VERISMO_0.jpg (cover, page programme) reste la paysage", vis.get("wide") == COVER_OPERA, str(vis))

# ── 4. Près de la frontière, côté REFUSE : le nom désigne la rubrique
PAGE_COM = f'<img src="{COMUNICATO_IMG}">'
vis = extract_press_visuals([{"url": f"{REGIO}/area-stampa", "html": PAGE_COM}], title="Festival Verismo")
_check("comunicato-stampa.jpg (nom de rubrique) est écarté", vis == {}, str(vis))

# ── 5. L'agent vision avant écriture (vérificateur injecté)
EV = {"id": 5256, "title": "Festival Verismo", "lieu": "Teatro Regio", "ville": "Torino"}
base = {"portrait": LOCANDINA_KIT, "wide": PRESS_RELEASE, "poster": LOCANDINA_KIT, "from_kit": True}
out = _affiches_verifiees(dict(base), EV, client=None, verifier=lambda u: u != PRESS_RELEASE)
_check("paysage refusée par la vision → retirée, portrait conservée",
       out.get("wide") is None and out.get("portrait") == LOCANDINA_KIT, str(out))
_check("poster recalculé sur ce qui reste", out.get("poster") == LOCANDINA_KIT and out.get("from_kit"), str(out))
out = _affiches_verifiees(dict(base), EV, client=None, verifier=lambda u: False)
_check("tout refusé → rien n'est écrit", out == {}, str(out))
out = _affiches_verifiees(dict(base), EV, client=None, verifier=lambda u: True)
_check("tout accepté → inchangé", out == base, str(out))
out = _affiches_verifiees(dict(base), EV, client=None)
_check("sans client ni vérificateur → règles déterministes seules (passe-plat)", out == base, str(out))
appels = []
_affiches_verifiees({"portrait": COVER_OPERA, "wide": COVER_OPERA, "poster": COVER_OPERA, "from_kit": False},
                    EV, client=None, verifier=lambda u: appels.append(u) or True)
_check("une même URL portrait+paysage n'est regardée qu'une fois", appels == [COVER_OPERA], str(appels))

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)")
    sys.exit(1)
print("Tout passe.")
