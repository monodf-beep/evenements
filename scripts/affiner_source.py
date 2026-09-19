#!/usr/bin/env python3
"""De la RACINE du site à la PAGE de l'événement — le rouvreur des sources « nom de domaine ».

Franck, 2026-09-08, devant montmelian.com/ posé comme source du Festival photo alors que
montmelian.com/festival-photo-de-montmelian/ existe : « quand on a une URL généraliste
nom de domaine, c'est qu'on n'a pas la source de la page qui nous donne l'événement. Donc
la source est aussi très importante. » Mesuré le même jour sur WordPress : 41 des 85
fiches françaises publiées encore devant nous avaient pour source la racine d'un site.
Conséquences en chaîne : pas d'og:image (la racine n'en a souvent pas — Musicastelle),
moisson et images_wide qui lisent une page d'accueil, et un lien « source » qui envoie le
lecteur sur une page d'accueil.

Depuis ce jour, `scripts/enrich.py` mémorise la page de l'événement (`_page_evenement`)
et suit les liens qui portent des mots du titre (`_programme_links(…, title=)`). Ce
script fait la même chose, APRÈS COUP, pour les fiches déjà écrites : il lit la racine
mémorisée, cherche le lien interne qui parle de l'événement, vérifie que la page trouvée
mentionne bien le titre, et remplace `url_officiel`. DRY-RUN par défaut.

Périmètre (règle 5) : fiches publiées, encore devant nous (fin >= aujourd'hui, ou sans
date), dont `url_officiel` est une racine (chemin vide). Après `--apply`, la moisson et le
re-push restent à faire — le script imprime les deux commandes avec les ids.

Exemples :
  .venv/bin/python -m scripts.affiner_source                 # liste ce qui changerait
  .venv/bin/python -m scripts.affiner_source --apply
  .venv/bin/python -m scripts.affiner_source 599 6782 --apply
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from scripts.scraper_events import init_db
from scripts.enrich import _programme_links, _get_html, _html_to_text, _fold, _event_tokens

log = get_logger("affiner_source")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def est_racine(url: str) -> bool:
    """Vrai si l'URL est la racine d'un site (chemin vide ou « / »)."""
    u = (url or "").strip()
    if not u.startswith("http"):
        return False
    return not urlparse(u).path.strip("/")


# Mots-outils que _event_tokens laisse passer (> 3 lettres) et qui ne désignent rien :
# « Concerto della Filarmonica » ne doit pas élire une page parce qu'elle contient « della ».
_STOP_LOCAL = frozenset((
    "della", "delle", "dello", "degli", "nella", "nelle", "sulla", "sulle", "dalla", "alla",
    "avec", "dans", "pour", "sans", "chez", "entre", "vers", "autour", "depuis", "jusqu",
    "cette", "notre", "votre", "leur", "tout", "tous", "toute", "toutes", "come", "anche",
))
# Chemins qui ne sont JAMAIS la page d'un événement : rubrique presse, actualités, appel
# aux dons, galerie. Le premier dry-run (08/09, 37 propositions) en avait élu une douzaine.
_PAGE_SKIP = ("press", "presse", "stampa", "comunicat", "news", "notizie", "actualit",
              "attualita", "blog", "soutenir", "soutien", "sostieni", "sostenere", "donazion",
              "mecenat", "newsletter", "contact", "gallery", "galleria", "/pro/")


def page_evenement_depuis_racine(racine: str, title: str, timeout: int = 10) -> str:
    """Depuis la racine, la page interne qui parle de CET événement. '' si rien de sûr :
    on ne devine pas, la racine reste.

    LEÇON DU PREMIER DRY-RUN (2026-09-08, 37 pages proposées, une bonne moitié fausses) :
    quand le site EST celui de l'événement (stresafestival.eu, filarmonica.it, doujador.it),
    les mots du titre sont dans le NOM DE DOMAINE — donc n'importe quel lien interne
    « contenait le titre », et la page presse (+5 points dans _programme_links) ou une
    actualité sans rapport l'emportait. Trois exigences, donc :
      • les mots du titre comptent dans le CHEMIN de la page, jamais dans l'hôte ;
      • un chemin presse / actualités / dons / galerie est écarté d'office ;
      • il faut la moitié des mots restants du titre (au moins 1, au plus 2) dans le
        chemin — puis le texte de la page doit encore mentionner l'un d'eux."""
    import re as _re
    # Ni mots-outils, ni ordinaux/millésimes (« 9eme », « 2026 », « xxe ») : un chemin ne les
    # porte presque jamais, et les compter fait exiger deux mots là où le titre n'en a qu'un
    # de vrai (« Festival Photo de Montmélian, 9ème édition » → photo).
    toks = [t for t in _event_tokens(title)
            if t not in _STOP_LOCAL and not _re.fullmatch(r"\d+[a-z]{0,4}|[xivl]+e", t)]
    if not toks:
        return ""
    host = _fold(urlparse(racine).netloc)
    non_host = [t for t in toks if t not in host]
    if not non_host:
        return ""                                     # le site EST l'événement : la racine suffit
    # Deux mots dès que le titre en offre deux (second dry-run, 08/09 : « Exposition des
    # Artistes villefranchois » n'avait plus qu'un mot après les stops, et un seul mot élisait
    # la « rencontre des associations villefranchoises »). Un seul mot ne suffit que s'il est
    # le seul — Montmélian : « photo », le reste est dans l'hôte.
    needed = 1 if len(non_host) == 1 else 2
    html = _get_html(racine, timeout)
    if not html:
        return ""
    for link in _programme_links(html, racine, limit=5, title=title):
        if est_racine(link):
            continue
        path = _fold(urlparse(link).path)
        if any(sk in path for sk in _PAGE_SKIP):
            continue
        hits = [t for t in non_host if t in path]
        if len(hits) < needed:
            continue
        page = _get_html(link, timeout)
        if not page:
            continue
        texte = _fold(_html_to_text(page)[:20000])
        if any(t in texte for t in non_host):
            return link
    return ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Remplace une source « racine » par la page de l'événement.")
    parser.add_argument("ids", nargs="*", type=int, help="Ids précis (défaut : sélection auto).")
    parser.add_argument("--apply", action="store_true", help="Écrire (sinon DRY-RUN).")
    parser.add_argument("--cap", type=int, default=60, help="Nb max de fiches (défaut 60).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    conn.row_factory = sqlite3.Row
    today = date.today().isoformat()
    if args.ids:
        qm = ",".join("?" * len(args.ids))
        rows = conn.execute(f"SELECT * FROM events_raw WHERE id IN ({qm})", args.ids).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM events_raw WHERE wp_post_id_as IS NOT NULL AND duplicate_of IS NULL "
            "AND COALESCE(url_officiel,'') <> '' "
            "AND (COALESCE(date_event_end, date_event_start, '') = '' "
            "     OR COALESCE(date_event_end, date_event_start) >= ?) "
            "ORDER BY id DESC", (today,)).fetchall()
    cibles = [dict(r) for r in rows if est_racine(r["url_officiel"])][:args.cap]
    log.info("%d fiche(s) publiées encore devant nous avec une source RACINE (sur %d lues) — %s",
             len(cibles), len(rows), "APPLIQUE" if args.apply else "DRY-RUN")

    trouvees, ecrites = [], 0
    for ev in cibles:
        page = page_evenement_depuis_racine(ev["url_officiel"], ev.get("title") or "")
        if not page:
            log.info("[%s] rien de mieux que la racine — %s", ev["id"], (ev.get("title") or "")[:55])
            continue
        log.info("[%s] %s → %s — %s", ev["id"], ev["url_officiel"], page, (ev.get("title") or "")[:45])
        trouvees.append(ev["id"])
        if args.apply:
            conn.execute("UPDATE events_raw SET url_officiel=? WHERE id=?", (page, ev["id"]))
            conn.commit()
            ecrites += 1
    # Recompte APRÈS écriture, pas sur la longueur de la liste (règle 6).
    restant = sum(1 for r in conn.execute(
        "SELECT url_officiel FROM events_raw WHERE wp_post_id_as IS NOT NULL AND duplicate_of IS NULL "
        "AND (COALESCE(date_event_end, date_event_start, '') = '' "
        "     OR COALESCE(date_event_end, date_event_start) >= ?)", (today,))
        if est_racine(r["url_officiel"]))
    conn.close()
    log.info("Pages trouvées : %d · écrites : %d · sources racine restantes (publiées, à venir) : %d%s",
             len(trouvees), ecrites, restant, "  (dry-run : rien écrit)" if not args.apply else "")
    if trouvees and args.apply:
        ids = " ".join(str(i) for i in trouvees)
        print(f"\nPuis, pour relire ces pages et re-pousser :\n"
              f"  .venv/bin/python -m scripts.moisson_officielle {ids} --apply\n"
              f"  .venv/bin/python -m scripts.publish_batch_as --ids {ids} --update")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
