#!/usr/bin/env python3
"""Fixture : une image Commons posée À LA MAIN garde son crédit.

2026-09-21. Le crédit API étant épuisé, Franck : « cherche toi ». J'ai donc cherché
moi-même une photo licenciable pour une fiche (la façade de Palazzo Carignano, par
Zairon, CC BY-SA 4.0) — et en préparant la pose, vu que la seule route qui permet de
remplacer une image à la main (`app.app.cadrage`) écrivait `image_credit=''` quoi qu'il
arrive.

Tant que les images manuelles venaient d'un site officiel, cela ne se voyait pas. Une
image de Wikimedia Commons, elle, part alors EN LIGNE SANS ATTRIBUTION, alors que CC BY
et CC BY-SA l'exigent — et c'est précisément la source que la charte §8 recommande faute
de mieux. L'API de Commons est ouverte : le crédit se retrouve depuis l'URL, sans clé ni
crédit d'API.

Aucun réseau : l'appel HTTP est remplacé ici même. Ce que la fixture vérifie, c'est le
chemin de l'URL au titre de fichier — y compris la forme MINIATURE
(`/thumb/…/3840px-Nom.jpg`), qui est celle que `commons_search` renvoie et donc celle
qu'on colle en pratique.

Lancer : .venv/bin/python -m tests.test_credit_commons
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import utils.images as images  # noqa: E402

echecs = 0
demandes: list = []


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


class _Reponse:
    status_code = 200

    @staticmethod
    def json():
        return {"query": {"pages": {"114210638": {"title": "File:Torino.jpg", "imageinfo": [{
            "extmetadata": {
                "Artist": {"value": '<a href="//commons.wikimedia.org/wiki/User:Zairon">Zairon</a>'},
                "LicenseShortName": {"value": "CC BY-SA 4.0"}}}]}}}}


def _faux_get(url, **kw):
    demandes.append((kw.get("params") or {}).get("titles"))
    return _Reponse()


images.requests.get = _faux_get

THUMB = ("https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/"
         "Torino_Palazzo_Carignano_Esterno_1.jpg/3840px-Torino_Palazzo_Carignano_Esterno_1.jpg")
ORIGINAL = ("https://upload.wikimedia.org/wikipedia/commons/4/41/"
            "Torino_Palazzo_Carignano_Esterno_1.jpg")

print("──── le crédit se retrouve depuis l'URL ────")
_check("miniature : crédit complet", images.credit_commons(THUMB)
       == "Zairon / Wikimedia Commons · CC BY-SA 4.0", images.credit_commons(THUMB))
_check("… et le préfixe de taille est retiré du nom de fichier",
       demandes[-1] == "File:Torino_Palazzo_Carignano_Esterno_1.jpg", str(demandes[-1]))
_check("fichier d'origine : même crédit",
       images.credit_commons(ORIGINAL) == "Zairon / Wikimedia Commons · CC BY-SA 4.0")

print("\n──── ce qui n'est PAS sur Commons ne déclenche aucun appel ────")
avant = len(demandes)
_check("photo d'un site officiel → ''",
       images.credit_commons("https://www.malrauxchambery.fr/uploads/charcot.jpg") == "")
_check("URL vide → ''", images.credit_commons("") == "")
_check("chemin relatif → ''", images.credit_commons("/uploads/photo.jpg") == "")
_check("aucun appel réseau tenté pour ces trois-là", len(demandes) == avant, str(demandes[avant:]))

print("\n──── nom accentué / encodé ────")
images.credit_commons("https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/"
                      "Ch%C3%A2teau_de_Montrottier.jpg/1200px-Ch%C3%A2teau_de_Montrottier.jpg")
_check("l'URL est décodée avant d'interroger l'API",
       demandes[-1] == "File:Château_de_Montrottier.jpg", str(demandes[-1]))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
