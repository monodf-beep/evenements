#!/usr/bin/env python3
"""Fait entrer dans la chaîne un événement SIGNALÉ par un lien — post Instagram, affiche,
message — une fois sa page officielle trouvée.

Né le 26/09/2026. Franck : « j'aimerais pouvoir te donner des liens d'événements et que
tu cherches la source, puis en faire un article événement. » Premier cas : un post
Instagram de @fieradelmarrone (Fiera Nazionale del Marrone, Cuneo, 16-18/10/2026). Aucun
chemin n'existait pour ajouter UNE fiche à la main : la base ne se remplissait que par
les flux RSS (scraper_events) et les newsletters (gmail_collect).

LE PARTAGE DU TRAVAIL :

  • la session Claude LIT le lien signalé, CHERCHE la page officielle, vérifie qu'elle
    parle bien de cet événement et de cette édition, regarde si le site a déjà une fiche,
    puis ajoute une ligne à `config/liens_signales.tsv` ;
  • ce script (cron de 8h10, avant dates 8h25 et dedupe 8h30) insère chaque ligne en
    `pending`, avec la page officielle comme `url_source` ET `url_officiel` ;
  • la suite est la chaîne ordinaire, sans exception : dates, lieux, évaluation,
    rédaction dans la voix de la maison, publication, traduction. Un signalement n'a
    aucun passe-droit éditorial — l'évaluateur peut le rejeter (hors périmètre, pas un
    événement, public professionnel), et c'est voulu. Il a seulement la PRIORITÉ dans la
    file de rédaction (`scripts/enrich.select_events`) : quelqu'un l'a demandé.

Le lien signalé (Instagram…) n'est JAMAIS la source : un réseau social n'est pas une page
officielle (`radar.source_officielle` le refuse), et le lecteur doit être envoyé chez
l'organisateur. Il est gardé dans `source_name` (« signalement : <lien> »), pour qu'on
sache d'où vient la fiche. ⚠️ Ce refus ne connaît que les domaines LISTÉS (réseaux
sociaux, presse de config/non_institutional_sources.txt) : un agrégateur de sagre comme
sagretoday.it passe. Le choix de la page reste le travail de la session, qui l'a LUE.

RÈGLE 3 — qui rouvre, où se voit le nombre ? Ce script ne pose aucun état terminal : il
insère en `pending`, que tout le pipeline sait traiter. Ce que devient chaque signalement
se lit avec `--etat` (en attente / rejeté + motif / rédigé / en ligne + adresse). Un
rejet se rouvre comme n'importe quel rejet, depuis le back-office.

Format du fichier (une ligne par événement, `#` = commentaire) :

    url_officielle<TAB>territoire<TAB>titre<TAB>lien_signalé<TAB>note

`titre` est le NOM de l'événement, établi en lisant la page : le titre HTML d'une page
officielle est souvent celui d'une rubrique (« Programma • Fiera del Marrone », constaté
sur le premier cas), et c'est lui que l'évaluateur, dedupe et la rédaction liraient.

`territoire` ∈ Savoie, Piemonte, Vallee-Aoste, Nice (l'évaluateur peut le corriger).
Une ligne mal formée ARRÊTE tout plutôt que d'être sautée en silence.

Idempotent : une page déjà en base (en `url_source` ou `url_officiel`) n'est pas
réinsérée, et le dry-run dit laquelle la porte déjà. La ligne peut donc rester dans le
fichier après son entrée ; elle ne coûte rien.

Usage :
    .venv/bin/python -m scripts.ajouter_par_lien              # dry-run
    .venv/bin/python -m scripts.ajouter_par_lien --apply      # cron de 8h10
    .venv/bin/python -m scripts.ajouter_par_lien --etat       # où en est chaque signalement
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.scraper_events import init_db  # noqa: E402
from utils import radar  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
LISTE = ROOT / "config" / "liens_signales.tsv"
TERRITOIRES = ("Savoie", "Piemonte", "Vallee-Aoste", "Nice")  # = scripts/evaluator.py
SOURCE_NAME = "signalement"


def lire_liste(chemin: Path) -> list[dict]:
    out = []
    if not chemin.exists():
        return out
    for n, brute in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
        ligne = brute.strip()
        if not ligne or ligne.startswith("#"):
            continue
        parts = [p.strip() for p in brute.split("\t")]
        if len(parts) < 4 or not parts[0].startswith("http") or not parts[2]:
            raise SystemExit(f"{chemin}:{n} : ligne mal formée — {ligne[:80]}")
        if parts[1] not in TERRITOIRES:
            raise SystemExit(f"{chemin}:{n} : territoire « {parts[1]} » inconnu "
                             f"(attendu : {', '.join(TERRITOIRES)})")
        if not radar.source_officielle(parts[0]):
            # Le cas que ce script existe pour empêcher : publier un post Instagram, un
            # article de presse ou un agrégateur comme « source officielle ».
            raise SystemExit(f"{chemin}:{n} : {parts[0]} n'est pas une page officielle "
                             "(réseau social ou presse) — trouver celle de "
                             "l'organisateur")
        out.append({"url": parts[0], "territoire": parts[1], "titre": parts[2],
                    "signale": parts[3], "note": parts[4] if len(parts) > 4 else "",
                    "ligne": n})
    return out


def deja_en_base(conn: sqlite3.Connection, url: str) -> sqlite3.Row | None:
    """La fiche qui porte déjà cette page, en source ou en source officielle. On compare
    sans le schéma ni la barre finale : http/https et `/` final ne font pas deux pages."""
    cle = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
    return conn.execute(
        "SELECT id, statut, title, wp_post_id_as FROM events_raw "
        "WHERE rtrim(replace(replace(replace(url_source,'https://',''),'http://',''),"
        "'www.',''),'/') = ? "
        "   OR rtrim(replace(replace(replace(COALESCE(url_officiel,''),'https://',''),"
        "'http://',''),'www.',''),'/') = ? "
        "ORDER BY duplicate_of IS NOT NULL, id LIMIT 1", (cle, cle)).fetchone()


def lire_page(url: str) -> str:
    """Texte de la page officielle — la matière que l'évaluateur, dates.py et venues.py
    liront. "" si la page ne répond pas : la ligne attend alors le lendemain au lieu
    d'entrer vide."""
    from scripts.enrich import _get_html, _html_to_text
    doc = _get_html(url, timeout=15)
    return _html_to_text(doc)[:4000] if doc else ""


def ajouter(conn: sqlite3.Connection, lignes: list[dict], apply: bool,
            lire=lire_page) -> dict:
    bilan = {"lignes": len(lignes), "deja": 0, "injoignable": 0, "insere": 0}
    for l in lignes:
        existe = deja_en_base(conn, l["url"])
        if existe:
            bilan["deja"] += 1
            print(f"  = déjà en base  id={existe['id']} statut={existe['statut']} "
                  f"wp={existe['wp_post_id_as'] or '-'} | {(existe['title'] or '')[:60]}")
            continue
        texte = lire(l["url"])
        if not texte:
            bilan["injoignable"] += 1
            print(f"  ! page muette, retentée demain | {l['url']}")
            continue
        titre = l["titre"]
        print(f"  + {'insérée' if apply else 'à insérer'} [{l['territoire']}] "
              f"{titre[:70]} | {l['url']}")
        if not apply:
            continue
        description = (l["note"] + "\n\n" if l["note"] else "") + texte
        cur = conn.execute(
            "INSERT OR IGNORE INTO events_raw (title, description, territoire, url_source, "
            "url_officiel, source_name, source_type) VALUES (?,?,?,?,?,?,'institutionnel')",
            (titre[:300], description[:6000], l["territoire"], l["url"], l["url"],
             f"{SOURCE_NAME} : {l['signale']}"[:200]))
        bilan["insere"] += cur.rowcount
    if apply:
        conn.commit()
    return bilan


def etat(conn: sqlite3.Connection) -> int:
    """Chaque signalement et ce qu'il est devenu — le compteur de la règle 3."""
    rows = conn.execute(
        "SELECT id, statut, title, article_title, llm_justification, wp_post_id_as, "
        "date_event_start, duplicate_of, source_name FROM events_raw "
        "WHERE source_name LIKE ? ORDER BY id DESC", (SOURCE_NAME + " :%",)).fetchall()
    print(f"{len(rows)} signalement(s) en base (tous, passés compris) :")
    for r in rows:
        if r["duplicate_of"]:
            ou = f"fusionné dans id={r['duplicate_of']}"
        elif r["wp_post_id_as"]:
            ou = f"en ligne ? WP#{r['wp_post_id_as']} (à vérifier sur le site, règle 1)"
        elif r["statut"] == "rejected":
            ou = f"REJETÉ — {(r['llm_justification'] or '')[:90]}"
        elif r["article_title"]:
            ou = "rédigé, publication au prochain lot"
        else:
            ou = f"{r['statut']}, date={r['date_event_start'] or 'pas encore'}"
        print(f"  id={r['id']:>6}  {(r['article_title'] or r['title'] or '')[:55]:55}  {ou}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--apply", action="store_true", help="Insère (sinon simulation).")
    p.add_argument("--etat", action="store_true", help="Où en est chaque signalement.")
    p.add_argument("--liste", type=Path, default=LISTE)
    args = p.parse_args(argv)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    if args.etat:
        return etat(conn)
    lignes = lire_liste(args.liste)
    print(f"{args.liste.name} : {len(lignes)} ligne(s)"
          + ("" if args.apply else " — SIMULATION, rien n'est écrit (--apply)"))
    b = ajouter(conn, lignes, args.apply)
    # Recompté en base (règle 6), pas déduit de la boucle.
    en_base = conn.execute("SELECT COUNT(*) FROM events_raw WHERE source_name LIKE ?",
                           (SOURCE_NAME + " :%",)).fetchone()[0]
    print(f"Bilan : {b['lignes']} ligne(s) — {b['insere']} insérée(s), {b['deja']} déjà "
          f"en base, {b['injoignable']} page(s) muette(s). Signalements en base : {en_base}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
