#!/usr/bin/env python3
"""QUELS DOMAINES SOURCES REFUSENT LE SERVEUR — et combien de fiches en dépendent.

CE QU'IL REND VISIBLE. Quatre scripts vont relire la page d'origine d'une fiche pour la
compléter : `dates` (mode web), `venues`, `autocomplete`, `repair_polluted_descriptions`.
Quand la page répond, ils réparent. Quand elle refuse, ils notent l'échec **fiche par
fiche**, dans leur journal, et passent à la suivante. C'est correct — mais si c'est le
DOMAINE ENTIER qui refuse, la même panne se répète des centaines de fois sans jamais être
nommée une seule.

LE CAS QUI L'A FAIT ÉCRIRE (2026-08-04). `repair_polluted_descriptions` échouait sur la
fiche 2153 : « page inaccessible ». Vérification faite, ce n'était pas la page — c'est
**tout `agendaculturel.fr` qui répond 403 à ce serveur**, racine comprise, sur ses quatre
sous-domaines (`06.`, `73.`, `74.`, `www.`), avec ou sans user-agent de navigateur.

Mesure : **338 fiches** viennent de ce domaine, dont **242 encore devant nous** et 207
sans date — c'est-à-dire précisément celles que `dates` et `venues` essaieront de
compléter, en vain, chaque semaine. Aucune alerte n'existait pour ça.

CE QU'IL NE FAIT PAS. Il ne juge pas la source (c'est `audit_bad_sources`), ne retire rien
et ne corrige rien : un 403 peut être temporaire, ou tomber le jour où le domaine change
d'hébergeur. Il DIT, avec le nombre de fiches concernées, pour qu'on décide en connaissance
de cause — trouver une autre source, ou cesser d'essayer.

Une requête par DOMAINE, pas par fiche : c'est tout l'intérêt. Lecture seule, aucun LLM.

Usage :
    .venv/bin/python -m scripts.audit_sources_bloquees
    .venv/bin/python -m scripts.audit_sources_bloquees --slack
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("audit-sources-bloquees")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
# En dessous, le domaine ne pèse pas assez pour qu'une alerte serve à quelque chose : on
# ne veut pas d'une liste de trente lignes dont vingt-huit portent sur une fiche unique.
MIN_FICHES = 5


def _racine(hote: str) -> str:
    """Domaine racine, sous-domaines repliés dessus.

    INDISPENSABLE ICI, et pas un raffinement : agendaculturel.fr sert ses fiches depuis
    `06.`, `73.`, `74.` et `www.`, et le 403 les couvre TOUTES. Comptés séparément, chaque
    sous-domaine passe sous le seuil et le blocage devient invisible — précisément le
    défaut que ce script existe pour corriger, reproduit dans le script lui-même.

    Deux étiquettes : suffisant pour du .fr et du .it, qui sont tout ce que couvre cet
    agenda. Un `.co.uk` serait mal replié — à revoir le jour où il y en aura un."""
    bouts = hote.split(".")
    return ".".join(bouts[-2:]) if len(bouts) > 2 else hote


def _domaines(conn: sqlite3.Connection, auj: date) -> dict[str, dict]:
    """Domaine → nombre de fiches, dont celles encore DEVANT NOUS (règle 5).

    Le compte qui compte est le second : un domaine mort dont toutes les fiches sont
    passées ne coûte plus rien, et l'alerter ferait exactement le travail inutile que la
    règle 5 interdit de fabriquer."""
    out: dict[str, dict] = {}
    for r in conn.execute("SELECT url_source, date_event_start, date_event_end, recurring, "
                          "       COALESCE(wp_post_id_as, 0) AS wp FROM events_raw "
                          "WHERE url_source LIKE 'http%'"):
        brut = (urlparse(r["url_source"]).hostname or "").lower()
        if not brut:
            continue
        d = out.setdefault(_racine(brut), {"total": 0, "devant": 0, "en_ligne": 0,
                                           "exemple": r["url_source"]})
        d["total"] += 1
        derniere = r["date_event_end"] or r["date_event_start"]
        vivant = bool(r["recurring"]) or not derniere or str(derniere)[:10] >= auj.isoformat()
        if vivant:
            d["devant"] += 1
            if r["wp"]:
                d["en_ligne"] += 1
    return out


def _etat(url: str) -> tuple[str, int | None]:
    """('ok' | 'refus' | 'injoignable', code). On interroge la page d'un vrai exemple et
    non la racine : certains sites servent leur accueil et bloquent le reste."""
    try:
        r = requests.get(url, timeout=20, headers=UA, allow_redirects=True)
    except requests.RequestException:
        return "injoignable", None
    if r.status_code < 400:
        return "ok", r.status_code
    # 403/401/429 = le serveur nous refuse ; 404 sur UN exemple ne dit rien du domaine.
    return ("refus" if r.status_code in (401, 403, 429) else "ok"), r.status_code


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Domaines sources qui refusent le serveur.")
    p.add_argument("--slack", action="store_true", help="Poste s'il y a à dire.")
    p.add_argument("--min", type=int, default=MIN_FICHES,
                   help=f"Seuil de fiches vivantes pour signaler (défaut {MIN_FICHES}).")
    args = p.parse_args(argv)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    auj = date.today()
    doms = {h: d for h, d in _domaines(conn, auj).items() if d["devant"] >= args.min}
    conn.close()

    bloques = []
    for hote, d in sorted(doms.items(), key=lambda kv: -kv[1]["devant"]):
        etat, code = _etat(d["exemple"])
        if etat != "ok":
            bloques.append((hote, d, etat, code))

    print(f"\n{len(doms)} domaine(s) pesant au moins {args.min} fiches encore devant nous.")
    if not bloques:
        print("Aucun ne refuse le serveur.\n")
        return 0

    print(f"\n⚠️  {len(bloques)} domaine(s) INACCESSIBLE(S) — toute réparation de date, de "
          f"lieu\n    ou de description y échouera, une fiche à la fois, sans alerte.\n")
    lignes = []
    for hote, d, etat, code in bloques:
        txt = (f"{hote} — {etat}" + (f" ({code})" if code else "")
               + f" · {d['devant']} fiche(s) devant nous, dont {d['en_ligne']} en ligne "
                 f"(sur {d['total']} au total)")
        print(f"  {txt}")
        lignes.append(txt)
    print("\n  Ce n'est pas une panne à réparer ici : un 403 peut être temporaire, ou "
          "tomber\n  le jour où le domaine change d'hébergeur. C'est un choix à faire — "
          "trouver une\n  autre source, ou cesser d'essayer.\n")

    if args.slack:
        from utils import slack
        slack.notify("🚫 *Sources qui refusent le serveur*\n"
                     + "\n".join(f"• {t}" for t in lignes)
                     + "\n_Les réparations de dates, lieux et descriptions y échouent "
                       "silencieusement._")
    log.info("Sources bloquées : %s", [b[0] for b in bloques])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
