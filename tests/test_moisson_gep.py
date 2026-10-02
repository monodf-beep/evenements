#!/usr/bin/env python3
"""Fixture de scripts/moisson_gep.py — le tri par région, et ce qu'il ne doit PAS prendre.

Règle 3 du CLAUDE.md : un portillon dont la fixture ne contient que des cas qui
confirment le design ne prouve rien. Celle-ci contient donc les deux bords :

  • un bloc Piémont qui DOIT passer, avec tous ses champs ;
  • un bloc d'une AUTRE région dont le résumé cite « Piemonte » — c'est le cas qui piège
    un filtre textuel, et il existe pour de vrai dans le listing du ministère (des
    résumés du Molise ou de Lombardie nomment d'autres régions). Il DOIT être refusé ;
  • un bloc Piémont sans date, qui doit être lu mais ressortir incomplet, pour que le
    script l'écarte au lieu d'insérer une fiche sans date.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.moisson_gep import parse_listing  # noqa: E402

BLOC = '''<div class="col-12 col-view px-0 big-event-element" data-region="{region}" data-city="{ville}">
  <div class="img-responsive-wrapper position-relative">
    <img src="https://cultura.gov.it/media/{img}.jpg" alt="">
    <time datetime="2026-09-10 11:46:00" class="card-calendar">
      <span class="card-year h6"><span class="line-1 small">2026</span></span>
      {date}
      <span class="card-day text-uppercase mb-auto">set</span>
    </time>
  </div>
  <h3 class="h5 font-weight-bold card-title mb-2 line-1">
    <a class="text-secondary" href="https://cultura.gov.it/evento/{slug}">{titre}</a>
  </h3>
  <div class="extra-text ml-0 mb-3">
    <strong class="small d-block line-1 font-italic">{lieu}</strong>
    <small class="d-block neutral-2-color-b4">{ville} ({prov})</small>
  </div>
  <div class="card-text"><span class="text-secondary">{resume}</span></div>
</div>'''


def bloc(region, ville, prov, titre, lieu, resume, slug, img="x", date='<span class="card-date mt-auto">26</span>'):
    return BLOC.format(region=region, ville=ville, prov=prov, titre=titre, lieu=lieu,
                       resume=resume, slug=slug, img=img, date=date)


PAGE = "<html><body>" + "".join([
    bloc("Piemonte", "Gavi", "AL", "Visita al Forte di Gavi", "Forte",
         "Il Forte di Gavi potrà essere visitato...", "visita-al-forte-di-gavi"),
    # le piège : région Molise, mais « Piemonte » dans le résumé
    bloc("Molise", "Campobasso", "CB", "GEP 2026 in Molise", "Museo",
         "Come in Piemonte, anche in Molise le GEP...", "gep-2026-in-molise"),
    # Piémont sans date : lu, mais incomplet
    bloc("Piemonte", "Asti", "AT", "Archivio di Stato di Asti", "Archivio",
         "Apertura straordinaria", "archivio-asti", date=""),
]) + "</body></html>"


def main() -> int:
    echecs = []

    trouves = parse_listing(PAGE, "Piemonte", "journee")

    if len(trouves) != 2:
        echecs.append(f"2 blocs piémontais attendus, {len(trouves)} trouvé(s)")

    urls = [e["url"] for e in trouves]
    if any("molise" in u for u in urls):
        echecs.append("le bloc du Molise a été pris : le filtre lit le résumé, pas data-region")
    else:
        print("OK    le bloc d'une autre région citant « Piemonte » est refusé")

    gavi = next((e for e in trouves if "gavi" in e["url"]), None)
    if not gavi:
        echecs.append("le bloc piémontais complet n'est pas ressorti")
    else:
        attendu = {"titre": "Visita al Forte di Gavi", "date_start": "2026-09-26",
                   "lieu": "Forte", "ville": "Gavi", "province": "AL", "type": "journee"}
        for cle, val in attendu.items():
            if gavi.get(cle) != val:
                echecs.append(f"{cle} : attendu {val!r}, obtenu {gavi.get(cle)!r}")
        if not gavi["image"].endswith(".jpg"):
            echecs.append(f"image non récoltée : {gavi['image']!r}")
        if not echecs:
            print("OK    le bloc piémontais rend titre, date, lieu, ville, province, image")

    asti = next((e for e in trouves if "asti" in e["url"]), None)
    if asti is None:
        echecs.append("le bloc sans date n'a pas été lu du tout")
    elif asti["date_start"]:
        echecs.append(f"le bloc sans date a reçu une date : {asti['date_start']!r}")
    else:
        print("OK    un bloc sans date ressort sans date (le script l'écartera)")

    # contre-épreuve : une région demandée qui n'est pas dans la page rend zéro,
    # et ce zéro-là vient d'une absence, pas d'une panne de lecture.
    if parse_listing(PAGE, "Valle d'Aosta", "journee"):
        echecs.append("une région absente de la page a rendu des résultats")
    else:
        print("OK    une région absente rend zéro")

    print()
    if echecs:
        for e in echecs:
            print("ÉCHEC", e)
        print(f"\nÉCHEC — {len(echecs)} problème(s).")
        return 1
    print("SUCCÈS — 0 problème(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
