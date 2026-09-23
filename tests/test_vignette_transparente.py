#!/usr/bin/env python3
"""Fixture : une image transparente ne devient pas un aplat noir, et le repli « page
source » de la publication respecte utils.pages comme les deux autres lecteurs.

23/09/2026, page /plaisirs-de-culture-vallee-d-aoste/ : 22 fiches publiées avec la même
vignette en aplats noirs. Deux défauts en chaîne : `publisher_as._recover_image` prenait
une image sur la page-programme partagée (ancre `#…`, que visuals et la moisson refusaient
déjà), et `card_image._load` aplatissait sa transparence en noir.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_vignette_transparente
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402
from utils.card_image import _load  # noqa: E402
import scripts.publisher_as as pas  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


def _png(img):
    b = io.BytesIO(); img.save(b, "PNG"); return b.getvalue()


print("──── transparence ────")
# Graphisme blanc sur fond TRANSPARENT : pixels (0,0,0,0) autour d'un carré blanc opaque.
g = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
g.paste((255, 255, 255, 255), (10, 10, 30, 30))
out = _load(_png(g))
_check("le fond transparent devient BLANC, pas noir", out.getpixel((2, 2)) == (255, 255, 255),
       str(out.getpixel((2, 2))))
_check("… et le motif opaque est conservé", out.getpixel((20, 20)) == (255, 255, 255))
d = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
d.paste((200, 30, 30, 255), (10, 10, 30, 30))
out = _load(_png(d))
_check("un motif coloré opaque garde sa couleur", out.getpixel((20, 20)) == (200, 30, 30),
       str(out.getpixel((20, 20))))
p = Image.new("P", (20, 20), 0); p.info["transparency"] = 0
out = _load(_png(p))
_check("palette avec couleur transparente → blanc", out.getpixel((1, 1)) == (255, 255, 255),
       str(out.getpixel((1, 1))))
photo = Image.new("RGB", (20, 20), (12, 34, 56))
_check("FRONTIÈRE : une photo sans transparence est inchangée (le noir d'une photo reste noir)",
       _load(_png(photo)).getpixel((5, 5)) == (12, 34, 56)
       and _load(_png(Image.new("RGB", (5, 5), (0, 0, 0)))).getpixel((1, 1)) == (0, 0, 0))

print("\n──── repli « page source » ────")
appels = []
import utils.images as ui  # noqa: E402
ui.fetch_content_image = lambda url, *a, **k: appels.append(url) or "https://x.org/photo.jpg"
PDC = "https://valledaostaheritage.com/events/plaisirs-de-culture-2026/"
r = pas._recover_image({"url_source": PDC + "#dal-segno-al-gioco-laboratorio-per-famiglie",
                        "title": "Dal segno al gioco", "source_type": "institutionnel"})
_check("ancre dans une page-programme → rien, et la page n'est même pas lue",
       r == "" and not appels, f"{r!r} {appels}")
r = pas._recover_image({"url_source": "https://theatre.fr/spectacle-x/", "title": "Spectacle X",
                        "source_type": "institutionnel"})
_check("FRONTIÈRE : la page d'un événement reste lue", r == "https://x.org/photo.jpg", repr(r))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
