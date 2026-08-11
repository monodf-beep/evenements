#!/usr/bin/env python3
"""Retrouve la date des fiches venues d'un mail, en relisant le mail.

Seize fiches de la file « À compléter » du 2026-08-11 n'avaient ni date ni page à ouvrir :
leur `url_source` est « gmail:… ». Six ateliers des musées de Chambéry, quatre annonces du
Département 06, Courmayeur, MITO, Turismo Torino. Aucune passe automatique ne pouvait les
servir, et c'est ce qui restait au fond de la file après tout le reste.

Leur date existe pourtant, écrite en toutes lettres dans le mail : « le vendredi 21 août à
18h30 ». Elle a été perdue parce que `gmail_collect` ne gardait que le résumé réécrit par
le modèle. Le corps est désormais conservé (`mail_corps`) — mais pour les fiches DÉJÀ en
base, il faut aller le rechercher.

C'EST POSSIBLE, et pour une seule raison : l'identifiant du message a été gardé dans
l'adresse de la fiche. « gmail:19fa305b67f95221#3 » désigne le mail et le rang de
l'événement dedans. Le message est donc retrouvable dans Gmail des mois plus tard.

CE QUE ÇA COÛTE : rien en API Anthropic. On télécharge des mails déjà reçus et on y
applique le lecteur de dates habituel, celui qui lit « du 11 au 29 août ». Le plafond du
2026-09-01 ne gêne pas.

CE QUE ÇA NE FAIT PAS : deviner. La date retenue est celle qui SUIT le titre de la fiche
dans le corps du mail (utils/mail_dates.py). Un mail annonce dix événements et porte vingt
dates ; sans cette ancre, chaque fiche recevrait la date de sa voisine — vérifié sur
fixture, l'erreur est silencieuse et systématique.

RÈGLE 4 : dry-run par défaut. RÈGLE 5 : seulement ce qui est devant nous. RÈGLE 6 : le
bilan est recompté en base, sur le périmètre de la pastille.

  .venv/bin/python -m scripts.dates_depuis_mail            # simulation
  .venv/bin/python -m scripts.dates_depuis_mail --apply
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
from utils.mail_dates import date_pres_du_titre, message_id_de  # noqa: E402

log = get_logger("dates_mail")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _a_traiter(conn: sqlite3.Connection, today: str) -> list[dict]:
    """Fiches issues d'un mail, sans date de début, encore devant nous.

    Une fiche sans AUCUNE date reste dans le lot : l'absence de date n'est pas une preuve
    de passé (règle 5), et c'est justement ce qu'on vient chercher."""
    return [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE url_source LIKE 'gmail:%' "
        "AND COALESCE(date_event_start,'') = '' "
        "AND statut NOT IN ('rejected','merged') AND duplicate_of IS NULL "
        "AND COALESCE(translation_of,0) = 0 "
        "AND (COALESCE(date_event_end,'') = '' OR date_event_end >= ?) "
        "ORDER BY id", (today,))]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="écrit (défaut : simulation)")
    ap.add_argument("--cap", type=int, default=100, help="nombre max de mails téléchargés")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        log.error("Base introuvable : %s", DB_PATH)
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    from scripts.gmail_collect import ensure_colonne_corps
    ensure_colonne_corps(conn)
    cibles = _a_traiter(conn, date.today().isoformat())
    if not cibles:
        print("Aucune fiche issue d'un mail n'attend de date.")
        conn.close()
        return 0

    print(f"═══ {len(cibles)} fiche(s) venues d'un mail, sans date de début ═══\n")

    # Un mail porte souvent PLUSIEURS fiches (les six ateliers de Chambéry viennent du
    # même envoi) : on le télécharge une fois, pas une fois par fiche.
    corps_par_mail: dict[str, str] = {}
    service = None
    trouves: list[tuple[int, str, str, str]] = []
    sans_corps = sans_date = 0

    for ev in cibles:
        mid = message_id_de(ev["url_source"])
        corps = (ev.get("mail_corps") or "").strip()
        if not corps and mid:
            if mid not in corps_par_mail:
                if len(corps_par_mail) >= args.cap:
                    break
                if service is None:
                    from scripts.gmail_collect import build_service
                    service = build_service()
                try:
                    from scripts.gmail_collect import parse_message
                    raw = service.users().messages().get(
                        userId="me", id=mid, format="full").execute()
                    corps_par_mail[mid] = parse_message(raw).get("body", "")
                except Exception as exc:                      # message supprimé, droits…
                    log.warning("[%s] mail %s illisible : %s", ev["id"], mid, exc)
                    corps_par_mail[mid] = ""
            corps = corps_par_mail[mid]
        if not corps:
            sans_corps += 1
            continue
        debut, fin = date_pres_du_titre(corps, ev.get("title") or "")
        if not debut:
            sans_date += 1
            print(f"  [{ev['id']:>5}] mail relu, aucune date SÛRE près du titre — "
                  f"{(ev.get('title') or '')[:52]}")
            continue
        trouves.append((ev["id"], debut, fin, (ev.get("title") or "")[:52]))
        print(f"  [{ev['id']:>5}] {debut} → {fin}   {(ev.get('title') or '')[:52]}")

    print(f"\n{len(corps_par_mail)} mail(s) téléchargé(s) · {len(trouves)} date(s) "
          f"trouvée(s) · {sans_date} sans date sûre · {sans_corps} sans corps disponible.")

    if not args.apply:
        print("\nSimulation — RIEN n'a été écrit. Ajouter --apply pour enregistrer.")
        conn.close()
        return 0

    for eid, debut, fin, _ in trouves:
        # On garde aussi le corps : la prochaine fois, plus besoin de Gmail.
        conn.execute(
            "UPDATE events_raw SET date_event_start=?, date_event_end=?, "
            "date_source='mail', date_checked_at=datetime('now') WHERE id=?",
            (debut, fin or debut, eid))
    for mid, corps in corps_par_mail.items():
        if corps:
            conn.execute("UPDATE events_raw SET mail_corps=? WHERE url_source LIKE ? "
                         "AND COALESCE(mail_corps,'')=''", (corps[:6000], f"gmail:{mid}%"))
    conn.commit()

    # Recompté en base, sur le périmètre EXACT de la pastille (règle 6).
    from scripts.lister_a_completer import _clause
    where, params = _clause(date.today().isoformat())
    reste = conn.execute(f"SELECT COUNT(*) FROM events_raw WHERE {where}",
                         params).fetchone()[0]
    conn.close()
    print(f"\n✅ {len(trouves)} fiche(s) datées depuis leur mail.")
    print(f"   La file « À compléter » contient maintenant {reste} fiche(s) "
          f"— même périmètre que la pastille du back-office.")
    print(f"   Les corps de mail sont conservés : la prochaine relecture n'aura plus "
          f"besoin de Gmail.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
