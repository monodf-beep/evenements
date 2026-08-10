#!/usr/bin/env python3
"""UNE page officielle téléchargée UNE fois, et TOUS ses champs récoltés d'un coup.

Franck, 2026-08-11 : « je comprends que la génération du texte soit obligatoire avec
l'api mais la complétion des informations grâce aux infos officielles devrait se faire,
alors qu'actuellement ce n'est pas le cas ». C'est exact, et c'est un défaut de
construction, pas un manque de moyens.

CE QUI NE VA PAS AUJOURD'HUI
Trois crons savent lire une page officielle, et chacun n'y prend qu'un seul champ :
  • dates.py       → `dates_from_page`  : JSON-LD startDate/endDate ;
  • venues.py      → `venue_from_page`  : JSON-LD location (name + addressLocality) ;
  • visuals.py     → `fetch_og_image`   : og:image.
Ils tournent à des heures différentes, téléchargent la MÊME page séparément, et surtout
chacun porte SON PROPRE délai de carence. Une fiche qui a épuisé son quota côté date
n'est plus téléchargée par dates.py — donc son lieu et son image, qui sont dans la même
page et qui n'ont rien demandé à personne, ne sont pas récoltés non plus. Trois horloges
indépendantes sur une seule ressource : il suffit que l'une soit fermée pour que le reste
attende.

Vérifié en production le 2026-08-11 : un run complet du mode sans-API a affiché
« Passe page : 0 page(s) à lire » côté dates ET côté lieux, alors que 79 fiches
attendaient une date et 31 un lieu. Aucune page n'a été lue de la soirée.

CE QUE FAIT CE SCRIPT
Un seul téléchargement par fiche, et on en tire tout ce qui s'y trouve : date de début,
date de fin, lieu, ville, image de partage. Aucun modèle — du JSON-LD et des balises
meta, c'est-à-dire de l'analyse syntaxique. Les fonctions d'extraction sont celles qui
existent déjà (dates.dates_from_page, venues.venue_from_page, images.fetch_og_image) :
rien n'est réécrit, on cesse seulement de les appeler chacune dans son coin.

CE QU'IL NE FAIT JAMAIS
  • il n'écrase RIEN : seuls les champs VIDES sont remplis. Une date posée à la main, un
    lieu corrigé au back-office, une image que Franck a remplacée par une vraie — tout
    cela est intouchable. C'est la leçon du 2026-08-09 (« pourquoi ça a retouché à
    l'image alors que je venais de la changer pour une vraie ? ») ;
  • il ne pose pas de verdict d'échec : ne rien trouver ne ferme aucune porte, ne
    consomme aucun délai de carence, et n'empêche pas dates.py ou venues.py de faire
    leur propre travail plus tard. Ce script AJOUTE, il ne décide pas ;
  • il ne touche pas aux fiches dont l'URL n'est pas une page (« gmail:… », Google News) :
    il n'y a rien à télécharger.

RÈGLE 5 : uniquement ce qui est encore devant nous. RÈGLE 4 : dry-run par défaut.
RÈGLE 6 : le bilan est recompté en base, champ par champ, après écriture.

Exemples :
  .venv/bin/python -m scripts.moisson_officielle                 # simulation
  .venv/bin/python -m scripts.moisson_officielle --apply --cap 100
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger  # noqa: E402
from utils.images import fetch_og_image  # noqa: E402
from scripts.dates import dates_from_page, ensure_columns, _robust_get  # noqa: E402
from scripts.venues import venue_from_page  # noqa: E402

log = get_logger("moisson")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

CHAMPS = ("date_event_start", "date_event_end", "lieu", "ville", "url_image")
# Écrit UNE fois : la sélection et le recompte final doivent porter sur le même
# critère, sinon le bilan diverge de ce qui a été tenté.
_MANQUE = " OR ".join(f"COALESCE({c},'')=''" for c in CHAMPS)


# Marqueurs qu'on sait lire aujourd'hui, et ceux qu'on ne lit PAS encore. Le mode
# --diagnostic les compte sur les pages qui n'ont rien donné : 53 pages muettes sur 58
# au premier run, et il faut savoir si c'est parce que la donnée est ABSENTE ou parce
# qu'elle est écrite dans une forme que l'extracteur ignore. Étendre l'extraction sans
# cette mesure, ce serait coder à l'aveugle contre une hypothèse.
_MARQUEURS = (
    ("json-ld startDate", r'"startDate"\s*:\s*"'),
    ("json-ld aux guillemets échappés", r'\\"startDate\\"'),
    ("balise <time datetime>", r'<time[^>]+datetime='),
    ("microdata itemprop=startDate", r'itemprop=["\']startDate'),
    ("meta event:start_time", r'event:start_time'),
    ("json-ld location", r'"location"\s*:'),
    ("microdata itemprop=location", r'itemprop=["\']location'),
    ("og:image", r'property=["\']og:image'),
    ("un bloc JSON-LD est bien présent", r'application/ld\+json'),
)


def _diagnostic(html: str) -> list[str]:
    import re as _re
    return [nom for nom, motif in _MARQUEURS if _re.search(motif, html, _re.I)]


def _url_telechargeable(ev: dict) -> str:
    """L'adresse à lire. `url_officiel` d'abord — c'est la page de l'événement chez
    l'organisateur, la plus riche en données structurées ; `url_source` sinon. Les
    pseudo-adresses (« gmail:… ») et Google News ne sont pas des pages."""
    for cle in ("url_officiel", "url_source"):
        u = (ev.get(cle) or "").strip()
        if u.startswith(("http://", "https://")) and "news.google.com" not in u:
            return u
    return ""


def _a_moissonner(conn, today: str, cap: int) -> list[dict]:
    """Fiches encore devant nous à qui il manque au moins un champ récoltable."""
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM events_raw WHERE "
        "statut IN ('evaluated','published_cs','published_sub') "
        "AND duplicate_of IS NULL AND COALESCE(translation_of,0)=0 "
        "AND (COALESCE(recurring,0)=1 OR COALESCE(NULLIF(date_event_end,''), "
        "     NULLIF(date_event_start,''), '9999') >= ?) "
        f"AND ({_MANQUE}) "
        "ORDER BY COALESCE(llm_score,0) DESC LIMIT ?", (today, cap * 3))]
    return [ev for ev in rows if _url_telechargeable(ev)][:cap]


def _recolte(ev: dict, marqueurs=None) -> dict:
    """Champs VIDES que la page permet de remplir. {} si la page est illisible.
    `marqueurs` (Counter, optionnel) : reçoit ce que porte une page qui n'a rien donné."""
    url = _url_telechargeable(ev)
    r = _robust_get(url)
    if r is None:
        if marqueurs is not None:
            marqueurs["PAGE INJOIGNABLE"] += 1
        return {}
    html = r.text
    trouve: dict = {}
    if not (ev.get("date_event_start") or "").strip():
        debut, fin, _src = dates_from_page(html)
        if debut:
            trouve["date_event_start"] = debut
            # La date de fin ne se pose QUE si le début vient d'être trouvé ici : poser
            # une fin sur un début venu d'ailleurs mélangerait deux sources sur un même
            # intervalle, et c'est ainsi qu'on obtient des fiches qui se terminent avant
            # de commencer.
            if fin:
                trouve["date_event_end"] = fin
    if not (ev.get("lieu") or "").strip() or not (ev.get("ville") or "").strip():
        lieu, ville, _src = venue_from_page(html)
        if lieu and not (ev.get("lieu") or "").strip():
            trouve["lieu"] = lieu
        if ville and not (ev.get("ville") or "").strip():
            trouve["ville"] = ville
    if not (ev.get("url_image") or "").strip():
        og = fetch_og_image(url)
        if og:
            trouve["url_image"] = og
    if not trouve and marqueurs is not None:
        for nom in _diagnostic(html) or ["AUCUN marqueur connu"]:
            marqueurs[nom] += 1
    return trouve


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Récolte date, lieu, ville et image sur la page officielle (sans LLM).")
    p.add_argument("--apply", action="store_true", help="Exécute (sinon simulation).")
    p.add_argument("--cap", type=int, default=100, help="Nb max de pages lues (défaut 100).")
    p.add_argument("--diagnostic", action="store_true",
                   help="Sur les pages qui ne donnent RIEN, dire quels marqueurs elles "
                        "portent — pour savoir si la donnée est absente ou seulement "
                        "écrite dans une forme qu'on ne lit pas encore.")
    p.add_argument("ids", nargs="*", type=int, help="Se limiter à ces fiches.")
    args = p.parse_args(argv)

    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # NE PAS SUPPOSER QU'UN AUTRE SCRIPT A DÉJÀ CRÉÉ SES COLONNES. Même famille de panne
    # que audit_annulations le 2026-08-09 (« no such column: annulation_marqueur ») :
    # ce script écrit date_source et date_checked_at, qui appartiennent à dates.py. Sur
    # une base neuve — ou si moisson tourne avant dates.py — la colonne n'existe pas.
    ensure_columns(conn)
    if args.ids:
        ph = ",".join("?" * len(args.ids))
        cibles = [dict(r) for r in conn.execute(
            f"SELECT * FROM events_raw WHERE id IN ({ph})", args.ids)]
        cibles = [ev for ev in cibles if _url_telechargeable(ev)]
    else:
        cibles = _a_moissonner(conn, today, args.cap)

    print(f"═══ {len(cibles)} page(s) officielle(s) à lire ═══\n")
    if not cibles:
        print("Aucune fiche incomplète ne dispose d'une page téléchargeable.")
        conn.close()
        return 0

    gagnes = {c: 0 for c in CHAMPS}
    lues = vides = 0
    from collections import Counter
    marqueurs_vides = Counter()
    for ev in cibles:
        trouve = _recolte(ev, marqueurs_vides if args.diagnostic else None)
        lues += 1
        if not trouve:
            vides += 1
            continue
        for c in trouve:
            gagnes[c] += 1
        detail = " · ".join(f"{c.replace('date_event_', '')}={v}"[:46]
                            for c, v in trouve.items())
        print(f"  [{ev['id']:>5}] {detail}")
        if args.apply:
            sets = ", ".join(f"{c}=?" for c in trouve)
            conn.execute(f"UPDATE events_raw SET {sets} WHERE id=?",
                         (*trouve.values(), ev["id"]))
            # date_source/venue_source renseignés SEULEMENT quand on a trouvé : un
            # échec ici ne doit poser aucun verdict, sinon on garerait la fiche pour
            # un délai de carence alors qu'on n'a même pas essayé le LLM (règle 3).
            if "date_event_start" in trouve:
                conn.execute("UPDATE events_raw SET date_source='page', "
                             "date_checked_at=datetime('now') WHERE id=?", (ev["id"],))
            if "lieu" in trouve or "ville" in trouve:
                conn.execute("UPDATE events_raw SET venue_source='page' WHERE id=?",
                             (ev["id"],))
            conn.commit()

    print(f"\n{lues} page(s) lue(s), dont {vides} sans aucune donnée exploitable.\n")
    if args.diagnostic and marqueurs_vides:
        print("Ce que portent les pages MUETTES (une page peut compter plusieurs fois) :")
        for nom, n in marqueurs_vides.most_common():
            print(f"  {n:4} {nom}")
        print()
    for c in CHAMPS:
        print(f"  {gagnes[c]:4} {c}")

    if not args.apply:
        print("\nSimulation — RIEN n'a été écrit. Ajouter --apply pour enregistrer.")
        conn.close()
        return 0

    # RÈGLE 6 : recompter en base plutôt que faire confiance à la boucle ci-dessus.
    reste = conn.execute(
        "SELECT COUNT(*) FROM events_raw WHERE "
        "statut IN ('evaluated','published_cs','published_sub') AND duplicate_of IS NULL "
        "AND COALESCE(translation_of,0)=0 "
        "AND (COALESCE(recurring,0)=1 OR COALESCE(NULLIF(date_event_end,''), "
        "     NULLIF(date_event_start,''), '9999') >= ?) "
        f"AND ({_MANQUE})",
        (today,)).fetchone()[0]
    conn.close()
    print(f"\nIl reste {reste} fiche(s) incomplète(s) devant nous.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
