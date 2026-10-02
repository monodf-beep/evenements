#!/usr/bin/env python3
"""Sources et newsletters, triées par PROVINCE — pour voir les manques.

LECTURE SEULE. Aucun réseau, aucune base : ne lit que config/sources.txt et
config/newsletters.txt.

D'OÙ ÇA VIENT — Franck, 2026-08-31 : « ce serait bien de trier les sources par province,
comme ça ça nous permet de voir les manques. » Le territoire éditorial (Savoie | Piemonte
| Vallee-Aoste | Nice) est trop large pour ça : « Savoie » fusionne deux départements,
« Piemonte » fusionne huit provinces. C'est exactement le défaut mesuré le 18/08
(audit_deplacement, GAP « intentions de recherche ») : Torino sur-couverte, six autres
provinces piémontaises à 0-1 événement — invisible tant que le compteur reste agrégé.

CE QUE CE RELEVÉ NE FAIT PAS : il ne classe QUE ce qui est déterminable (utils.provinces,
via la ville de la source ou une commune reconnue dans son nom). Une source réellement
RÉGIONALE (« VisitPiemonte DMO », « Piemonte dal Vivo ») n'a À JUSTE TITRE aucune
province — la compter de force fabriquerait un chiffre faux. Ces sources apparaissent
dans « non classées », comptées, jamais invisibles.

Usage :
    .venv/bin/python -m scripts.audit_sources_provinces
    .venv/bin/python -m scripts.audit_sources_provinces --slack
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.provinces import province_de, provinces_savoie  # noqa: E402

SOURCES_FILE = ROOT / "config" / "sources.txt"
NEWSLETTERS_FILE = ROOT / "config" / "newsletters.txt"

def _provinces_connues() -> dict[str, tuple[str, ...]]:
    """Toutes les provinces connues, même à 0 source — sinon une province absente de
    sources.txt disparaîtrait du tableau au lieu d'afficher son zéro (règle 6 : un zéro
    doit dire son dénominateur).

    ⚠️ LUES, jamais recopiées (audit du 31/08). La première version écrivait les huit noms
    piémontais en dur ici, alors qu'ils sont déjà les clés de
    `config/provinces_piemonte.json` — troisième exemplaire d'un même dénominateur, dans
    un dépôt qui a déjà payé la duplication de config une fois (« Venise des Alpes »).
    Le versant français se déduit du département, comme dans `utils.provinces`."""
    import json
    piemonte = json.loads((ROOT / "config" / "provinces_piemonte.json")
                          .read_text(encoding="utf-8"))
    return {
        "Savoie": provinces_savoie(),
        "Piemonte": tuple(p for p in piemonte if not p.startswith("_")),
        "Vallee-Aoste": ("Vallée d'Aoste",),
        "Nice": ("Comté de Nice",),
    }


_TOUTES_PROVINCES = _provinces_connues()


def lire_sources(chemin: Path, colonne_ville: int | None) -> list[dict]:
    """Lignes utiles d'un fichier `;`-séparé du dépôt, commentaires/vides retirés."""
    if not chemin.exists():
        return []
    lignes = []
    for brut in chemin.read_text(encoding="utf-8").splitlines():
        l = brut.strip()
        if not l or l.startswith("#") or ";" not in l:
            continue
        parts = [p.strip() for p in l.split(";")]
        lignes.append(parts)
    return lignes


def classer(fichier: Path, i_territoire: int, i_nom: int, i_ville: int | None) -> dict:
    """{territoire: {province: [noms]}} + les non-classées, pour un fichier donné."""
    par_territoire: dict[str, dict[str, list[str]]] = {
        t: {p: [] for p in provs} for t, provs in _TOUTES_PROVINCES.items()}
    non_classees: dict[str, list[str]] = {t: [] for t in _TOUTES_PROVINCES}
    for parts in lire_sources(fichier, i_ville):
        if len(parts) <= max(i_territoire, i_nom):
            continue
        territoire, nom = parts[i_territoire], parts[i_nom]
        ville = parts[i_ville] if i_ville is not None and len(parts) > i_ville else ""
        # Le territoire canonique est comparé à nos quatre clés connues ; un territoire
        # inconnu (ligne mal formée, futur territoire) n'est ni classé ni compté ici —
        # scripts/scraper_events.load_sources fait déjà foi sur ce qui est valide.
        cle = next((t for t in _TOUTES_PROVINCES if t.lower() in territoire.lower()
                   or territoire.lower() in t.lower()), None)
        if cle is None:
            continue
        province = province_de(territoire, ville, nom)
        if province:
            par_territoire[cle].setdefault(province, []).append(nom)
        else:
            non_classees[cle].append(nom)
    return {"par_province": par_territoire, "non_classees": non_classees}


def rapport() -> str:
    src = classer(SOURCES_FILE, i_territoire=1, i_nom=2, i_ville=5)
    nl = classer(NEWSLETTERS_FILE, i_territoire=2, i_nom=0, i_ville=None)

    lignes = ["=" * 78, "Sources et newsletters, par province — où sont les manques ?",
             "=" * 78, ""]
    total_gaps = 0
    for territoire, provinces in _TOUTES_PROVINCES.items():
        lignes.append(f"## {territoire}\n")
        lignes.append("| Province | Sources RSS | Newsletters | |")
        lignes.append("|---|---|---|---|")
        for province in provinces:
            n_src = len(src["par_province"][territoire].get(province, []))
            n_nl = len(nl["par_province"][territoire].get(province, []))
            marque = ""
            if n_src == 0 and n_nl == 0:
                marque = "⚠️ AUCUNE source ni newsletter"
                total_gaps += 1
            elif n_src == 0:
                marque = "⚠️ aucune source RSS"
            elif n_nl == 0:
                marque = "aucune newsletter suivie"
            lignes.append(f"| {province} | {n_src} | {n_nl} | {marque} |")
        nc_src = len(src["non_classees"][territoire])
        nc_nl = len(nl["non_classees"][territoire])
        if nc_src or nc_nl:
            lignes.append(f"| _non classées (régionales, sans ville dédiée)_ "
                          f"| {nc_src} | {nc_nl} | _normal, pas un manque_ |")
        lignes.append("")

    lignes.append(f"PÉRIMÈTRE : {sum(len(p) for p in _TOUTES_PROVINCES.values())} "
                  f"provinces connues, {total_gaps} sans aucune source ni newsletter.")
    lignes.append("Classement par la ville de la source, ou une commune reconnue dans "
                  "son nom (utils.provinces) — jamais deviné : une source régionale sans "
                  "ville dédiée reste « non classée », pas forcée dans une province.")
    return "\n".join(lignes)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--slack", action="store_true",
                   help="Dépose le verdict dans la boîte du jour (digest).")
    args = p.parse_args(argv)

    texte = rapport()
    print(texte)
    if args.slack:
        from utils import slack
        gaps = texte.split("provinces connues, ")[1].split(" sans")[0]
        slack.notify(f"🗺️ *Sources par province* — {gaps} province(s) sans aucune "
                    f"source ni newsletter. Détail : `.venv/bin/python -m "
                    f"scripts.audit_sources_provinces`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
