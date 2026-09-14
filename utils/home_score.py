"""Score de RENDU d'une fiche pour la home (`as_home_score`, 0-10) — UNE formule, UN endroit.

Jusqu'au 2026-09-15 elle vivait inline dans scripts/enrich.py (l.2231-2247) et nulle part
ailleurs : une fiche enrichie avant que la formule existe n'avait donc aucun moyen de
recevoir son score sans être RÉÉCRITE. Mesuré ce jour-là : 21 fiches en ligne et à venir
sans score de rendu, dont 19 avec un panel déjà noté — tout ce qu'il faut pour le
calculer, et rien pour le faire. `scripts/rescore_home.py` le fait désormais, avec CETTE
fonction, la même qu'enrich : deux formules pour un score, c'est la racine des seize
fautes du 08/09.

Les entrées, et ce qu'elles pèsent (inchangé) :
  qualité éditoriale  panel local (moyenne 0-5) ramené sur 6      → 0 à 6
  source directe      la matière vient du site officiel          → +2,5
  visuels             deux affiches +1,5 ; une, ou photo du site
                      officiel, +0,75 ; rien, 0
"""
from __future__ import annotations
from urllib.parse import urlparse


def _strip_www(host: str) -> str:
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def photo_officielle(url_image: str, hotes_officiels: set[str] | list[str]) -> bool:
    """La photo vient-elle du SITE OFFICIEL (règle Franck : une photo officielle vaut mise
    en avant même sans affiche) ? Comparaison de domaines, `www.` ignoré."""
    h = _strip_www(urlparse(url_image or "").netloc)
    if not h:
        return False
    return h in {_strip_www(urlparse(u if "://" in u else "https://" + u).netloc)
                 for u in hotes_officiels if u}


def calculer(panel_mean: float | None, source_officielle: bool,
             affiche_portrait: bool, affiche_paysage: bool, photo_off: bool) -> dict:
    """→ {"score": 0-10, "affiches": libellé, "placement": phrase}. Formule d'enrich,
    déplacée à l'identique."""
    has_p, has_w = bool(affiche_portrait), bool(affiche_paysage)
    affiches = ("deux" if (has_p and has_w) else
                "une" if (has_p or has_w) else
                "photo officielle" if photo_off else "aucune")
    q = (panel_mean or 0) / 5 * 6
    src = 2.5 if source_officielle else 0.0
    aff = 1.5 if (has_p and has_w) else 0.75 if (has_p or has_w or photo_off) else 0.0
    hs = round(min(10.0, q + src + aff), 1)
    has_visu = has_p or has_w or photo_off
    if hs >= 8 and has_p and has_w:
        place = "À la une (hero home) · En évidence · newsletter AVEC visuel — combo complet"
    elif hs >= 6 and has_visu:
        place = ("En évidence (home) · sélections · newsletter AVEC visuel"
                 + (" (photo du site officiel)" if (photo_off and not (has_p or has_w)) else ""))
    elif hs >= 6:
        place = ("sélections & listes (texte) · newsletter en brève SANS visuel — "
                 "pas de mise en avant home sans affiche ni photo officielle")
    else:
        place = "catalogue / listes seulement (agenda, archives)"
    return {"score": hs, "affiches": affiches, "placement": place}
