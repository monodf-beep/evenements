"""Un média déjà en ligne n'est pas redéposé — mais un visuel DIFFÉRENT l'est.

Mesure qui a motivé ces cas (production, 2026-09-12) : 4 158 médias dans la
médiathèque dont **2 016 copies en trop** sur 841 titres, parce que
`_upload_featured_media` POSTait sur `wp/v2/media` sans jamais chercher si
l'image y était déjà. Republier une fiche redéposait ses trois déclinaisons.

Les trois cas ci-dessous, dans cet ordre :
  1. premier dépôt → upload, et le nom porte l'empreinte des octets ;
  2. même image redéposée → AUCUN POST, on réutilise l'id trouvé ;
  3. **cas qui doit PASSER, choisi près de la frontière** : mêmes titre et URL
     source, octets DIFFÉRENTS (c'est ce que produit un changement de point focal
     au back-office) → l'empreinte change, donc un vrai upload a lieu. Sans ce
     cas, une réutilisation trop large figerait le cadrage et le test serait
     quand même vert.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import publisher  # noqa: E402


class _Reponse:
    def __init__(self, payload, status=200, headers=None):
        self._payload = payload
        self.status_code = status
        self.headers = headers or {}
        self.text = ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"statut {self.status_code}")


class _FauxWP:
    """Médiathèque en mémoire : POST crée, GET ?slug= retrouve."""

    def __init__(self, octets: bytes):
        self.octets = octets
        self.medias: dict[str, dict] = {}
        self.posts: list[str] = []   # noms de fichier réellement déposés
        self.suivant = 100

    def get(self, url, **kw):
        params = kw.get("params") or {}
        if "wp/v2/media" in url and "slug" in params:
            m = self.medias.get(params["slug"])
            return _Reponse([m] if m else [])
        # téléchargement de la source
        return _Reponse(None, headers={"Content-Type": "image/jpeg"})

    def post(self, url, **kw):
        if "wp/v2/media" in url and "Content-Disposition" in (kw.get("headers") or {}):
            nom = kw["headers"]["Content-Disposition"].split('filename="')[1].rstrip('"')
            self.posts.append(nom)
            slug = nom.rsplit(".", 1)[0].lower()
            self.suivant += 1
            self.medias[slug] = {"id": self.suivant,
                                 "source_url": f"https://exemple/{nom}"}
            return _Reponse(self.medias[slug])
        return _Reponse({})  # mise à jour alt/légende/titre


@pytest.fixture
def faux(monkeypatch):
    wp = _FauxWP(b"")

    def _fetch(image_url):
        return wp.octets, "image/jpeg"

    monkeypatch.setattr(publisher.requests, "get", wp.get)
    monkeypatch.setattr(publisher.requests, "post", wp.post)
    monkeypatch.setattr(publisher, "_fetch_source_bytes", _fetch)
    return wp


def _depose(image_url="https://source/affiche.jpg", titre="Guitare en scène"):
    return publisher._upload_featured_media(
        "https://site", ("u", "p"), image_url, alt="alt", title=titre)


def test_premier_depot_puis_reutilisation(faux):
    faux.octets = b"des octets d'affiche"
    id1, url1 = _depose()
    assert id1 == 101
    assert len(faux.posts) == 1
    # le nom porte l'empreinte : c'est elle qui rend la reconnaissance possible
    assert faux.posts[0].startswith("guitare-en-scene-")
    assert faux.posts[0].endswith(".jpg")
    assert len(faux.posts[0]) > len("guitare-en-scene.jpg")

    id2, url2 = _depose()
    assert (id2, url2) == (id1, url1)
    assert len(faux.posts) == 1, "le même visuel a été redéposé une seconde fois"


def test_visuel_different_est_bien_redepose(faux):
    """Le cas qui doit PASSER : mêmes titre et URL, autres octets (cadrage changé)."""
    faux.octets = b"des octets d'affiche"
    id1, _ = _depose()
    assert len(faux.posts) == 1

    faux.octets = b"les memes pixels mais recadres autrement"
    id2, _ = _depose()
    assert len(faux.posts) == 2, "un visuel recadré a été confondu avec l'ancien"
    assert id2 != id1
    assert faux.posts[0] != faux.posts[1]


def test_recherche_en_panne_ne_bloque_pas(faux, monkeypatch):
    """Recherche en panne (réseau, 500, JSON tronqué) → on retombe sur l'upload, donc sur
    l'ancien comportement. Jamais une fiche sans vignette parce que la recherche a raté."""
    faux.octets = b"des octets d'affiche"

    def _get_casse(url, **kw):
        if "wp/v2/media" in url and "slug" in (kw.get("params") or {}):
            raise publisher.requests.RequestException("réseau coupé")
        return faux.get(url, **kw)

    monkeypatch.setattr(publisher.requests, "get", _get_casse)
    mid, _ = _depose()
    assert mid == 101
    assert len(faux.posts) == 1
