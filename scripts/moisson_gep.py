#!/usr/bin/env python3
"""Le programme officiel des Giornate Europee del Patrimonio, récolté d'un coup.

D'OÙ ÇA VIENT. Franck, 22/09/2026 : « il faudrait scrapper un site comme
musei.cultura.gov.it en triant vallée d'aoste et piemonte non ? pour avoir plus
d'événements ». Mesuré le matin même en base WordPress : **sept** fiches publiées
commençaient le 26 ou 27 septembre, et **une seule** parlait des GEP (la nocturne des
Musei Reali). Le week-end du patrimoine italien, c'est-à-dire l'un des plus gros
rendez-vous culturels de l'année en Piémont, était invisible sur le site. Une page
dédiée n'y aurait rien changé : le problème était la MATIÈRE, pas la vitrine.

CE QUE LISENT CES DEUX PAGES. Le ministère publie son programme national en deux
listings — les événements de journée et les ouvertures nocturnes à 1 €. Chaque
événement y est un bloc `big-event-element` qui porte DÉJÀ tout ce dont le pipeline a
besoin : région, ville, province, date (jour + mois abrégé italien + année), nom du
lieu, titre, résumé, lien. Aucune page de détail à ouvrir, aucun JSON-LD à espérer —
vérifié le 22/09 : les pages de détail de cultura.gov.it n'en portent pas, donc
`dates.dates_from_page` n'y trouverait rien. C'est le listing qui est la bonne source.

CE QU'IL NE FAIT PAS. Il n'écrit que dans `events_raw`, comme le scraper RSS : la suite
du pipeline (évaluation, enrichissement, dates, lieux, traduction, publication) ne change
pas d'un pouce. `url_source` étant UNIQUE, le script est rejouable sans créer de doublon.

LA VALLÉE D'AOSTE N'EST PAS DANS CE LISTING, et ce n'est pas un oubli : mesuré le 22/09,
le programme du ministère couvre DIX-NEUF régions et la Vallée d'Aoste n'en fait pas
partie. Région autonome, elle gère son patrimoine elle-même et publie son propre
rendez-vous — « Plaisirs de Culture en Vallée d'Aoste », du 19 au 27 septembre 2026,
quatorzième édition, thème « Patrimonio a rischio ». Il lui faut donc sa propre moisson,
depuis la source régionale. Ne pas chercher « Valle d'Aosta » ici : on ne la trouvera pas.

USAGE
    python -m scripts.moisson_gep                 # DRY-RUN : lit, trie, affiche, n'écrit rien
    python -m scripts.moisson_gep --apply         # insère dans events_raw
    python -m scripts.moisson_gep --region Piemonte --annee 2026
"""
from __future__ import annotations

import argparse
import html
import re
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

# Les deux listings du ministère. Les URL portent le millésime : elles changeront l'an
# prochain, c'est le seul endroit à mettre à jour.
LISTINGS = (
    ("https://cultura.gov.it/evento/gep-2026-eventi-diurni", "journee"),
    ("https://cultura.gov.it/evento/gep-2026-apertura-serale", "nocturne"),
)

# Mois abrégés italiens, tels qu'ils sortent de `<span class="card-day">`.
MOIS_IT = {"gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
           "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12}

# Valeur de `territoire` en base, telle que l'emploie config/sources.txt.
TERRITOIRE = {"Piemonte": "Piemonte"}

SOURCE_NAME = "Ministero della Cultura — GEP"


def _texte(fragment: str) -> str:
    """Balises retirées, entités décodées, espaces normalisés."""
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", fragment))).strip()


def parse_listing(page: str, region: str, type_evt: str, annee_defaut: int = 2026) -> list[dict]:
    """Les événements d'UNE région dans un listing du ministère.

    Le filtre porte sur l'attribut `data-region` du bloc, pas sur une recherche de texte :
    « Piemonte » apparaît aussi dans le résumé d'événements d'autres régions (« ... in
    Molise ... Piemonte ... »), et un filtre textuel les ramasserait.
    """
    out = []
    for bloc in re.split(r'(?=<div class="col-12 col-view px-0 big-event-element")', page)[1:]:
        m_reg = re.search(r'data-region="([^"]*)"', bloc)
        if not m_reg or html.unescape(m_reg.group(1)).strip() != region:
            continue

        def g(motif: str, defaut: str = "") -> str:
            m = re.search(motif, bloc, re.S)
            return m.group(1) if m else defaut

        jour = g(r'card-date[^>]*>(\d+)<')
        mois = g(r'card-day[^>]*>\s*([A-Za-z]{3})').lower()
        annee = g(r'line-1 small">(\d{4})<', str(annee_defaut))
        date_start = ""
        if jour and mois in MOIS_IT:
            date_start = f"{annee}-{MOIS_IT[mois]:02d}-{int(jour):02d}"

        ville_brute = _texte(g(r'<small class="d-block[^"]*">(.*?)</small>'))
        m_ville = re.match(r"(.*?)\s*\(([A-Z]{2})\)$", ville_brute)

        out.append({
            "titre": _texte(g(r'card-title[^>]*>\s*<a[^>]*>(.*?)</a>')),
            "date_start": date_start,
            "lieu": _texte(g(r'<strong class="small d-block[^"]*">(.*?)</strong>')),
            "ville": (m_ville.group(1).strip() if m_ville else ville_brute),
            "province": (m_ville.group(2) if m_ville else ""),
            "resume": _texte(g(r'card-text"><span[^>]*>(.*?)</span>')),
            "url": g(r'href="(https://cultura\.gov\.it/evento/[^"]+)"'),
            "image": g(r'<img[^>]+src="([^"]+)"'),
            "type": type_evt,
        })
    return out


def _telecharge(url: str) -> str:
    import urllib.request
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="Piemonte", help="région telle que l'écrit le ministère (défaut : Piemonte)")
    ap.add_argument("--annee", type=int, default=2026)
    ap.add_argument("--apply", action="store_true", help="écrit en base (sinon : dry-run)")
    ap.add_argument("--db", default=str(RACINE / "data" / "events.db"))
    args = ap.parse_args()

    evts, lus = [], 0
    for url, type_evt in LISTINGS:
        try:
            page = _telecharge(url)
        except Exception as e:  # le zéro doit dire d'où il vient
            print(f"  ⚠ {url} illisible : {e}")
            continue
        lus += 1
        trouves = parse_listing(page, args.region, type_evt, args.annee)
        print(f"  {url.rsplit('/', 1)[-1]:30} {len(trouves):3} en {args.region}")
        evts.extend(trouves)

    if lus == 0:
        print("\nAUCUN listing n'a pu être lu — c'est un échec de réseau, pas une absence d'événements.")
        return 1

    # Dédoublonnage par URL : un même événement peut figurer dans les deux listings.
    par_url = {}
    for e in evts:
        par_url.setdefault(e["url"], e)
    evts = sorted(par_url.values(), key=lambda e: (e["date_start"], e["ville"]))

    incomplets = [e for e in evts if not e["titre"] or not e["date_start"] or not e["url"]]
    print(f"\n{len(evts)} événement(s) en {args.region} — {len(incomplets)} incomplet(s) (écarté(s))")
    evts = [e for e in evts if e not in incomplets]

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA busy_timeout=30000")
    deja = {r[0] for r in conn.execute(
        "SELECT url_source FROM events_raw WHERE url_source IN (%s)" % ",".join("?" * len(evts)),
        [e["url"] for e in evts]).fetchall()} if evts else set()
    neufs = [e for e in evts if e["url"] not in deja]

    print(f"déjà en base : {len(deja)} · à insérer : {len(neufs)}\n")
    for e in neufs:
        print(f"  {e['date_start']} [{e['type'][:4]}] {e['ville']:<22} {e['titre'][:64]}")

    if not args.apply:
        print(f"\nDRY-RUN — rien n'a été écrit. Relancer avec --apply pour insérer ces {len(neufs)}.")
        conn.close()
        return 0

    pose = 0
    for e in neufs:
        # Le lieu et la ville sont renseignés ici : le pipeline n'aura pas à les deviner.
        description = e["resume"]
        if e["lieu"]:
            description = f"{e['lieu']}, {e['ville']} — {description}".strip(" —")
        # LA DATE VA DANS LES DEUX COLONNES, ET CE N'EST PAS UNE COMMODITÉ.
        # `date_start` est la date de PUBLICATION de la source (le scraper RSS y met
        # `entry.published`). La date de l'ÉVÉNEMENT vit dans `date_event_start` /
        # `date_event_end`, et c'est elle que tout le reste regarde : `publish_batch_as`
        # exige `COALESCE(date_event_start,'') <> ''`, la règle 5 juge sur
        # `date_event_end`. Première version de ce script (22/09) : la date n'allait que
        # dans `date_start`. Les 52 fiches sont donc entrées SANS date d'événement, et
        # `dates.py` n'aurait eu aucun moyen de la retrouver — les pages de détail de
        # cultura.gov.it ne portent pas de JSON-LD (vérifié le même jour). Elles
        # seraient restées indéfiniment invisibles à la publication.
        #
        # Chaque rendez-vous des GEP tient sur UNE journée : début = fin.
        cur = conn.execute("""
            INSERT OR IGNORE INTO events_raw
                (title, description, date_start, date_event_start, date_event_end,
                 lieu, ville, territoire, url_source, url_image, source_name, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (e["titre"], description, e["date_start"], e["date_start"], e["date_start"],
              e["lieu"], e["ville"], TERRITOIRE.get(args.region, args.region),
              e["url"], e["image"], SOURCE_NAME, "institutionnel"))
        pose += cur.rowcount
    conn.commit()

    # Règle 6 : on recompte en base, on n'annonce pas la longueur d'une liste.
    verif = conn.execute(
        "SELECT COUNT(*) FROM events_raw WHERE source_name = ?", (SOURCE_NAME,)).fetchone()[0]
    conn.close()
    print(f"\n{pose} insérée(s). En base pour « {SOURCE_NAME} » : {verif} fiche(s) au total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
