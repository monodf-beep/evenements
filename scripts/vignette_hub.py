#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fabrique la vignette d'une page hub : la photo de la ville + l'encart de période.

POURQUOI CE SCRIPT EXISTE
-------------------------
Mesuré le 2026-09-21 sur les 192 pages hub (64 « aujourd'hui », 64 « week-end »,
64 « cette semaine ») : AUCUNE n'a d'image mise en avant. Les 28 pages « guide de
ville » non plus. Deux conséquences, dans cet ordre :

  1. le visiteur qui arrive sur /que-faire-a-chambery/aujourdhui/ et sur
     .../ce-week-end/ voit exactement la même page — reproche de Franck du 20/09 ;
  2. une image mise en avant vaut +7 points Yoast sur ces pages (mesuré le 19/09),
     donc 192 pages laissent ces 7 points par terre.

L'encart règle le premier point et l'image règle le second, d'un seul geste.

CE QUE L'ENCART NE CONTIENT PAS, ET POURQUOI
--------------------------------------------
Ni date, ni compteur d'événements, ni rien de saisonnier. Arbitrage de Franck du
21/09 : « j'aimerais quelque chose de plus intemporel ». La raison technique tient
en une phrase : une image datée doit être refabriquée chaque matin pour 192 pages,
et alors ou bien elle garde son adresse et Google Images sert une version périmée,
ou bien elle en change et perd à chaque fois tout ce qu'elle avait accumulé — le
404 des redirections (CLAUDE.md), transposé aux images.

La date et le nombre d'événements vivent dans le TITRE et la META, qui eux se
remettent à jour tout seuls à chaque passage du pipeline.

Et un rappel, parce que la question s'est posée : le texte écrit DANS une image
n'est pas un critère de classement Google Images. L'encart travaille pour l'humain
(le clic, le partage, Discover). Le classement, lui, se joue sur le nom de fichier,
l'attribut alt, le titre de la page, le texte autour, et la STABILITÉ de l'adresse.

OÙ IL TOURNE
------------
Dans le conteneur de session, qui embarque Chromium (PLAYWRIGHT_BROWSERS_PATH).
PAS sur le VPS : rien ne garantit qu'un navigateur y soit installé, et personne
ne l'a vérifié. C'est délibéré — la vignette se fabrique EN MÊME TEMPS QUE LA
RÉDACTION (consigne de Franck du 21/09), et la rédaction se fait en session.

USAGE
-----
    python3 scripts/vignette_hub.py --photo <fichier|url> --fenetre weekend \
        --ville "Chambéry" --langue fr --sortie /tmp/chambery-weekend.jpg
"""
from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import pathlib
import random
import re
import subprocess
import sys
import tempfile
import urllib.request

RACINE = pathlib.Path(__file__).resolve().parent.parent
POLICES = RACINE / "config" / "vignettes" / "polices-latin.css"
LOGO = RACINE / "assets" / "brand" / "agenda-sabauda-logo-white.png"

# Chromium fourni par l'environnement d'exécution. Ne JAMAIS lancer
# « playwright install » : le binaire est déjà là, le téléchargement est coupé.
CHROMIUM = pathlib.Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# Le JPEG est encodé par le CANVAS de Chromium, pas par ffmpeg. Vérifié le
# 2026-09-21 : le ffmpeg livré avec Playwright est compilé en
# « --disable-everything » — il DÉCODE le mjpeg mais n'a aucun encodeur JPEG,
# et sort en erreur 183. Et Pillow n'est pas installé (pip install demande
# l'accord de Franck, CLAUDE.md). Le canvas fait le travail sans rien ajouter.

LARGEUR, HAUTEUR = 1200, 630          # le format des vignettes du site
ESPACE = 1200                          # 1200 px de dessin = 100 cqw

# --- charte : wordpress/design-system/tokens.css -----------------------------
BLEU, BEIGE, NOIR = "#18365E", "#F7F1E8", "#1D1D1B"


class PhotoIntrouvable(RuntimeError):
    """La photo de fond n'a pas pu être lue. On n'écrit PAS de vignette sans
    photo : une vignette au fond gris serait pire que pas de vignette du tout."""


# ---------------------------------------------------------------------------
#  Les tracés. Aucune arête n'est d'aplomb : c'est la demande de Franck du
#  21/09 (« les cards ne sont pas droites, c'est ce que j'aimerais »), et ça
#  raccorde les encarts aux tuiles de catégorie du site.
# ---------------------------------------------------------------------------
CADRES = {
    "aujourdhui": "M14 18 C 130 2 300 26 388 9 C 406 126 386 236 392 348 "
                  "C 280 366 132 342 16 356 C 2 238 26 130 14 18 Z",
    "weekend":    "M13 16 C 180 1 382 28 548 8 C 566 110 540 222 552 320 "
                  "C 372 302 176 334 11 314 C 1 214 25 108 13 16 Z",
    "semaine":    "M16 14 C 250 -2 466 24 686 6 C 704 96 680 202 690 290 "
                  "C 448 308 242 280 10 300 C -2 200 28 102 16 14 Z",
}

# Les pictos. Mêmes réglages que les pictos de catégorie relevés sur le site le
# 21/09 : fill="none", stroke="#1D1D1B", linecap/linejoin="round".
# Trois SILHOUETTES volontairement dissemblables — un rond, trois gros blocs,
# sept fins. Trois pictos qui se ressemblent deviennent indiscernables à 150 px ;
# c'est la capture du 21/09 qui l'a montré, pas une intuition.
HORLOGE = ("M22 5.6 C 31.2 5.1 38.6 12.8 38.4 22.1 C 38.6 31.4 30.8 38.7 21.6 38.4 "
           "C 12.6 38.6 5.4 31.2 5.6 21.7 C 5.4 12.6 12.9 5.9 22 5.6 Z")
AIGUILLES = "M21.8 12.4 C 22.2 16 21.6 18.8 21.9 21.9 C 25.3 23.4 28.2 25.2 30.8 26.2"
CAL_CORPS = ("M5 11 C 18 8.4 33 12.6 44 9.4 C 46.2 19 43 31 45 40.2 "
             "C 31 42.8 16 38.4 4 41.6 C 6.6 31 2.8 20 5 11 Z")
CAL_ANNEAU = "M15 2.8 C 15.5 5.6 14.7 8.2 15.1 11 M35 2.8 C 35.5 5.6 34.7 8.2 35.1 11"
CAL_FILET = "M5.2 18 C 18 15.4 33 19.6 43.9 16.8"


def _barre(x: float, y: float, lg: float, h: float, alea: random.Random) -> str:
    """Un rectangle plein, légèrement gauchi — jamais deux fois le même."""
    r = lambda a: round(a + alea.uniform(-0.45, 0.45), 2)
    return ("M{} {} C {} {} {} {} {} {} C {} {} {} {} {} {} "
            "C {} {} {} {} {} {} C {} {} {} {} {} {} Z").format(
        r(x), r(y),
        r(x + lg * .35), r(y - .5), r(x + lg * .7), r(y + .5), r(x + lg), r(y),
        r(x + lg + .4), r(y + h * .4), r(x + lg - .3), r(y + h * .7), r(x + lg), r(y + h),
        r(x + lg * .65), r(y + h + .5), r(x + lg * .3), r(y + h - .5), r(x), r(y + h),
        r(x - .4), r(y + h * .65), r(x + .3), r(y + h * .3), r(x), r(y))


def _barres(n: int, x0: float, x1: float, graine: int) -> str:
    """Graine FIXE par fenêtre : la même page regénérée donne le même fichier,
    sinon on croirait l'image modifiée à chaque passage."""
    alea = random.Random(graine)
    ecart = 1.6 if n == 3 else 2.1
    lg = ((x1 - x0) - ecart * (n - 1)) / n
    return "".join(_barre(x0 + i * (lg + ecart), 23.5, lg, 10, alea) for i in range(n))


PICTOS = {
    "aujourdhui": ("0 0 44 44",
                   '<path class="t" d="{}"/><path class="t" d="{}"/>'
                   '<circle class="p" cx="21.9" cy="21.9" r="1.9"/>'.format(HORLOGE, AIGUILLES)),
    "weekend":    ("0 0 48 44",
                   '<path class="t" d="{}"/><path class="t" d="{}"/><path class="t" d="{}"/>'
                   '<path class="p" d="{}"/>'.format(CAL_CORPS, CAL_ANNEAU, CAL_FILET,
                                                     _barres(3, 24, 43, 7))),
    "semaine":    ("0 0 48 44",
                   '<path class="t" d="{}"/><path class="t" d="{}"/><path class="t" d="{}"/>'
                   '<path class="p" d="{}"/>'.format(CAL_CORPS, CAL_ANNEAU, CAL_FILET,
                                                     _barres(7, 6.5, 42.5, 11))),
}

# Géométrie par fenêtre. « vb » garde l'espace de dessin d'ORIGINE du tracé :
# preserveAspectRatio="none" l'étire ensuite vers la boîte réelle (L/H). Sans
# ça, changer la hauteur décollerait le tracé du bas de la carte.
GEOMETRIE = {
    "aujourdhui": dict(L=400, H=384, vbL=400, vbH=360, picto=178, tilt="-1.6deg"),
    "weekend":    dict(L=560, H=352, vbL=560, vbH=330, picto=164, tilt="1.3deg"),
    "semaine":    dict(L=700, H=330, vbL=700, vbH=300, picto=150, tilt="-0.8deg"),
}

LIBELLES = {
    "fr": {"aujourdhui": "Aujourd'hui", "weekend": "Ce week-end",
           "semaine": "Cette semaine"},
    "it": {"aujourdhui": "Oggi", "weekend": "Questo weekend",
           "semaine": "Questa settimana"},
}

# --- La préposition ---------------------------------------------------------
# « à Annecy » marche, « à Savoie » ne marche pas. Les 192 pages hub ne portent
# pas que des villes : 36 visent un TERRITOIRE et 48 une PROVINCE (relevé du
# 2026-09-22). Table EXPLICITE plutôt que règle devinée — une règle
# grammaticale automatique se trompe sur « le Monferrato » comme sur « la Côte
# d'Azur », et une faute de français dans une image est indélébile : elle part
# dans Google Images et dans tous les partages.
PREPOSITIONS = {
    # territoires
    "Savoie":          {"fr": "en Savoie",              "it": "in Savoia"},
    "Savoia":          {"fr": "en Savoie",              "it": "in Savoia"},
    "Piémont":         {"fr": "en Piémont",             "it": "in Piemonte"},
    "Piemonte":        {"fr": "en Piémont",             "it": "in Piemonte"},
    "Vallée d'Aoste":  {"fr": "en Vallée d'Aoste",      "it": "in Valle d'Aosta"},
    "Valle d'Aosta":   {"fr": "en Vallée d'Aoste",      "it": "in Valle d'Aosta"},
    "Comté de Nice":   {"fr": "dans le Comté de Nice",  "it": "nella Contea di Nizza"},
    "Contea di Nizza": {"fr": "dans le Comté de Nice",  "it": "nella Contea di Nizza"},
    "la Côte d'Azur":  {"fr": "sur la Côte d'Azur",     "it": "in Costa Azzurra"},
    "Costa Azzurra":   {"fr": "sur la Côte d'Azur",     "it": "in Costa Azzurra"},
    "le Monferrato":   {"fr": "dans le Monferrato",     "it": "nel Monferrato"},
    "Monferrato":      {"fr": "dans le Monferrato",     "it": "nel Monferrato"},
}


def lieu(label: str, langue: str) -> str:
    """Rend « à Annecy », « ad Annecy », « en Savoie »… — la mention complète.

    Deux pièges, tous deux constatés sur le site lui-même :
      - les libellés arrivent encodés en HTML depuis le shortcode
        (« la province d'Asti » s'y écrit « la province d&#039;Asti ») ;
      - l'italien veut le *d* euphonique devant un mot commençant par *a* :
        les titres du site disent déjà « Cosa fare AD Annecy ». La règle
        moderne le limite à la voyelle IDENTIQUE, donc « ad Aosta » mais
        « a Ivrea » — c'est ce que fait le code ci-dessous.
    """
    label = html.unescape(label).strip()
    if label in PREPOSITIONS:
        return PREPOSITIONS[label][langue]
    bas = label.lower()
    if bas.startswith("la province") or bas.startswith("provincia"):
        # Chaque langue a SON libellé en base : « la province de Turin » côté FR,
        # « provincia di Torino » côté IT. On ne colle donc jamais une préposition
        # italienne sur un libellé français (« in la province de Turin »).
        if bas.startswith("provincia"):
            return "in " + label
        if langue == "fr":
            return "dans " + label
        raise ValueError(
            "libellé français « {} » avec langue=it : la page italienne doit "
            "porter son propre libellé (« provincia di … »)".format(label))
    if langue == "it":
        return ("ad " if label[:1].lower() == "a" else "a ") + label
    return "à " + label

FENETRES = tuple(GEOMETRIE)
LANGUES = tuple(LIBELLES)


def cqw(px: float) -> str:
    return "{:.4f}cqw".format(px * 100.0 / ESPACE)


def _data_uri(octets: bytes, type_mime: str) -> str:
    return "data:{};base64,{}".format(type_mime, base64.b64encode(octets).decode())


def charger_photo(source: str) -> str:
    """Lit la photo de fond, fichier local ou URL, et la rend en data-URI."""
    try:
        if re.match(r"^https?://", source):
            requete = urllib.request.Request(
                source, headers={"User-Agent": "AgendaSabauda/vignette_hub"})
            with urllib.request.urlopen(requete, timeout=30) as reponse:
                octets = reponse.read()
                type_mime = reponse.headers.get_content_type() or "image/jpeg"
        else:
            chemin = pathlib.Path(source)
            octets = chemin.read_bytes()
            type_mime = mimetypes.guess_type(chemin.name)[0] or "image/jpeg"
    except Exception as exc:                       # noqa: BLE001 — on re-lève typé
        raise PhotoIntrouvable("{} : {}".format(source, exc)) from exc
    if len(octets) < 2000:
        raise PhotoIntrouvable(
            "{} : {} octets, c'est trop peu pour une photo".format(source, len(octets)))
    return _data_uri(octets, type_mime)


def construire_html(photo_uri: str, fenetre: str, ville: str, langue: str) -> str:
    geo = GEOMETRIE[fenetre]
    mots = LIBELLES[langue]
    vue, picto = PICTOS[fenetre]
    logo_uri = _data_uri(LOGO.read_bytes(), "image/png")
    polices = POLICES.read_text(encoding="utf-8")
    mention = lieu(ville, langue)
    return """<!doctype html><html lang="{langue}"><head><meta charset="utf-8"><style>
{polices}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:#fff}}
.vignette{{position:relative;width:{L}px;height:{H}px;overflow:hidden;container-type:inline-size}}
.fond{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.voile{{position:absolute;inset:0;background:linear-gradient(to bottom,
  rgba(29,29,27,.26),rgba(29,29,27,.06) 42%,rgba(29,29,27,.40))}}
.encart{{position:absolute;left:50%;top:50%;width:{eL};height:{eH};
  transform:translate(-50%,-50%) rotate({tilt})}}
.cadre{{position:absolute;inset:0;width:100%;height:100%;overflow:visible}}
.cadre path{{fill:{beige};stroke:{noir};stroke-width:3.4;
  stroke-linejoin:round;stroke-linecap:round}}
.dedans{{position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  padding:1.5cqw 3.3333cqw 3.6667cqw;text-align:center}}
.pic{{display:block;width:{picto};height:auto;overflow:visible}}
.pic .t{{fill:none;stroke:{noir};stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}}
.pic .p{{fill:{noir};stroke:none}}
.titre{{font-family:'Saira Condensed',sans-serif;font-weight:700;color:{bleu};
  text-transform:uppercase;letter-spacing:.05em;line-height:.98;
  font-size:4.3333cqw;margin-top:1.6667cqw;white-space:nowrap}}
.ville{{font-family:'Saira Condensed',sans-serif;font-weight:600;color:{noir};
  text-transform:uppercase;letter-spacing:.14em;font-size:2.0833cqw;
  margin-top:.6667cqw;white-space:nowrap}}
.languette{{position:absolute;left:50%;bottom:0;
  transform:translate(-50%,50%) rotate(.8deg);background:{noir};
  padding:.9167cqw 2cqw;display:flex;align-items:center}}
.languette img{{height:3cqw;width:auto;display:block}}
</style></head><body>
<div class="vignette">
  <img class="fond" src="{photo}" alt="">
  <div class="voile"></div>
  <div class="encart">
    <svg class="cadre" viewBox="0 0 {vbL} {vbH}" preserveAspectRatio="none">
      <path d="{cadre}"/></svg>
    <div class="dedans">
      <svg class="pic" viewBox="{vue}">{picto_svg}</svg>
      <div class="titre">{titre}</div>
      <div class="ville">{mention}</div>
    </div>
    <div class="languette"><img src="{logo}" alt="Agenda Sabauda"></div>
  </div>
</div></body></html>""".format(
        langue=langue, polices=polices, L=LARGEUR, H=HAUTEUR,
        eL=cqw(geo["L"]), eH=cqw(geo["H"]), tilt=geo["tilt"],
        picto=cqw(geo["picto"]), vbL=geo["vbL"], vbH=geo["vbH"],
        cadre=CADRES[fenetre], vue=vue, picto_svg=picto,
        titre=mots[fenetre], mention=mention,
        photo=photo_uri, logo=logo_uri,
        bleu=BLEU, beige=BEIGE, noir=NOIR)


def rendre(html: str, sortie: pathlib.Path, qualite: float = 0.86) -> pathlib.Path:
    """HTML -> PNG (capture Chromium) -> JPEG (canvas Chromium). Chemin écrit.

    Deux passes, parce qu'aucune des deux ne sait faire le travail de l'autre :
    le canvas ne rastérise pas du HTML, et « --screenshot » ne sort que du PNG.
    Le PNG transite en data-URI et non en file:// — une image file:// TEINTE le
    canvas et « toDataURL » lève alors une erreur de sécurité.
    """
    if not CHROMIUM.exists():
        raise RuntimeError("Chromium absent : {}".format(CHROMIUM))

    with tempfile.TemporaryDirectory() as dossier:
        tmp = pathlib.Path(dossier)
        page, png = tmp / "vignette.html", tmp / "vignette.png"
        page.write_text(html, encoding="utf-8")
        subprocess.run(
            [str(CHROMIUM), "--headless", "--disable-gpu", "--no-sandbox",
             "--hide-scrollbars", "--force-device-scale-factor=1",
             "--virtual-time-budget=5000",
             "--window-size={},{}".format(LARGEUR, HAUTEUR),
             "--screenshot={}".format(png), page.as_uri()],
            check=True, capture_output=True, timeout=120)
        if not png.exists():
            raise RuntimeError("Chromium n'a produit aucune image")

        convertisseur = tmp / "jpeg.html"
        convertisseur.write_text(
            '<body><img id="p" src="{uri}">\n'
            '<div id="sortie"></div><script>\n'
            'const i=document.getElementById("p");\n'
            'function encoder(){{\n'
            '  const c=document.createElement("canvas");\n'
            '  c.width={L}; c.height={H};\n'
            '  const x=c.getContext("2d");\n'
            '  x.fillStyle="#ffffff"; x.fillRect(0,0,{L},{H});\n'
            '  x.drawImage(i,0,0,{L},{H});\n'
            '  document.getElementById("sortie").textContent =\n'
            '    c.toDataURL("image/jpeg",{q});\n'
            '}}\n'
            'if (i.complete) {{ encoder(); }} else {{ i.onload = encoder; }}\n'
            '</script></body>'.format(
                uri=_data_uri(png.read_bytes(), "image/png"),
                L=LARGEUR, H=HAUTEUR, q=qualite),
            encoding="utf-8")
        dom = subprocess.run(
            [str(CHROMIUM), "--headless", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=5000", "--dump-dom", convertisseur.as_uri()],
            check=True, capture_output=True, timeout=120).stdout.decode(
                "utf-8", "replace")

    trouve = re.search(r"data:image/jpeg;base64,([A-Za-z0-9+/=]+)", dom)
    if not trouve:
        raise RuntimeError("le canvas n'a rendu aucun JPEG "
                           "(DOM de {} octets)".format(len(dom)))
    octets = base64.b64decode(trouve.group(1))
    if octets[:2] != b"\xff\xd8":
        raise RuntimeError("l'entête n'est pas celle d'un JPEG")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_bytes(octets)
    return sortie


def nom_fichier(ville: str, fenetre: str, langue: str) -> str:
    """Le nom de fichier EST un critère de classement Google Images — c'est
    l'un des rares leviers réels sur une vignette, alors autant qu'il parle."""
    base = re.sub(r"[^a-z0-9]+", "-",
                  html.unescape(ville).lower()
                  .replace("é", "e").replace("è", "e").replace("ê", "e")
                  .replace("à", "a").replace("â", "a").replace("ô", "o")
                  .replace("î", "i").replace("ï", "i").replace("ç", "c")
                  .replace("ù", "u").replace("û", "u")).strip("-")
    suffixe = {"aujourdhui": "aujourdhui", "weekend": "ce-week-end",
               "semaine": "cette-semaine"}[fenetre]
    if langue == "it":
        suffixe = {"aujourdhui": "oggi", "weekend": "questo-weekend",
                   "semaine": "questa-settimana"}[fenetre]
    return "agenda-sabauda-{}-{}.jpg".format(base, suffixe)


def texte_alt(ville: str, fenetre: str, langue: str) -> str:
    """L'attribut alt, lui, compte vraiment pour Google Images."""
    mots = LIBELLES[langue]
    mention = lieu(ville, langue)
    if langue == "it":
        return "Cosa fare {} {}".format(mention, mots[fenetre].lower())
    return "Que faire {} {}".format(mention, mots[fenetre].lower())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--photo", required=True,
                    help="photo de fond : chemin local ou URL")
    ap.add_argument("--fenetre", required=True, choices=FENETRES)
    ap.add_argument("--ville", required=True)
    ap.add_argument("--langue", default="fr", choices=LANGUES)
    ap.add_argument("--sortie", help="chemin du JPEG ; par défaut, le nom parlant "
                                     "dans le dossier courant")
    args = ap.parse_args(argv)

    try:
        photo = charger_photo(args.photo)
    except PhotoIntrouvable as exc:
        print("ÉCHEC — photo illisible : {}".format(exc), file=sys.stderr)
        return 2

    sortie = pathlib.Path(args.sortie) if args.sortie else pathlib.Path(
        nom_fichier(args.ville, args.fenetre, args.langue))
    html = construire_html(photo, args.fenetre, args.ville, args.langue)
    rendre(html, sortie)

    # Règle 6 de CLAUDE.md : rapporter le RÉSULTAT, pas l'intention.
    print("écrit    : {} ({} octets)".format(sortie, sortie.stat().st_size))
    print("nom voulu: {}".format(nom_fichier(args.ville, args.fenetre, args.langue)))
    print("alt      : {}".format(texte_alt(args.ville, args.fenetre, args.langue)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
