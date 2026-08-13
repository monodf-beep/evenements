#!/usr/bin/env python3
"""CONTRADICTEUR — deux fiches EN LIGNE qui racontent le même événement.

D'OÙ ÇA VIENT. Le 2026-08-13, la liste « bande maigre » de `audit_substance_published`
montrait sept titres présents DEUX fois, en italien les deux fois :

    [4421] WP#6380  Tour de l'Avenir 2026 - Strambino Lago Serrù
    [4584] WP#7113  Tour de l'Avenir 2026 - Strambino - Lago Serrù

Personne ne les cherchait. `scripts/dedupe.py` tourne à 8h sur `statut='pending'` : il
dédoublonne ce qui ARRIVE, jamais ce qui est DÉJÀ publié. Son option `--rescan` sait le
faire, mais elle FUSIONNE — c'est-à-dire qu'elle décide toute seule laquelle des deux
pages disparaît. Or CLAUDE.md range la fusion parmi les arbitrages humains, à côté du
défusionnage et du re-classement d'une fiche rejetée par Franck.

Donc ce script ne fusionne rien et n'a pas de `--apply` : il DÉSIGNE, Franck tranche.

CE QU'IL NE FAUT SURTOUT PAS APPARIER. Une traduction française peut porter un titre
italien, quand le nom de l'événement EST italien — « Campionato Italiano Canoa Slalom »
reste tel quel en français. Ces paires-là sont normales : ce sont deux pages liées par
Polylang, une par langue, et les fusionner détruirait le site bilingue. C'est le piège
de la fiche 3588 (« La Rencontre Valdôtaine »), où un portillon a pris un NOM PROPRE
pour la preuve d'une traduction ratée. On écarte donc toute paire dont les deux fiches
sont liées par `translation_of`, dans un sens ou dans l'autre, ou qui traduisent le même
original.

PÉRIMÈTRE — écrit ici et RÉPÉTÉ à côté de chaque nombre (règle 6) : fiches publiées
(`wp_post_id_as` renseigné), non déjà marquées doublon, et ENCORE DEVANT NOUS. Deux
pages jumelles sur un événement de juin ne se réparent pas : plus personne ne les
cherche, et les départager coûterait du temps pour rien (règle 5).

La définition de « même événement » n'est pas réinventée ici : on appelle `_groups` de
`scripts/dedupe.py`, avec ses gardes années et dates. Deux définitions concurrentes de
la ressemblance finiraient par se contredire, et c'est la plus bavarde qu'on croirait.

Usage (VPS) :
    .venv/bin/python -m scripts.verifier_doublons_publies
    .venv/bin/python -m scripts.verifier_doublons_publies --slack
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
from scripts.dedupe import _groups  # noqa: E402  — MÊME définition que le dédoublonnage
from scripts.audit_substance_published import devant_nous  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _connect_ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def paire_de_traduction(a: dict, b: dict) -> bool:
    """Ces deux fiches sont-elles les deux langues d'un même événement ?

    Trois formes de la même liaison : a traduit b, b traduit a, ou toutes deux
    traduisent le même original (cas des fiches jumelles créées de chaque côté).
    Une paire pareille est NORMALE et ne doit jamais remonter — cf. l'en-tête.
    """
    ta, tb = int(a.get("translation_of") or 0), int(b.get("translation_of") or 0)
    return ta == b["id"] or tb == a["id"] or (ta and ta == tb)


def _lien(ev: dict) -> str:
    """Ce qu'on donne à un humain pour ALLER VOIR. Le permalien s'il est connu ; sinon on
    le dit, parce que `/?p=<id>` répond 404 pour tout `tribe_events`, vivant ou mort
    (règle 1) — proposer cette adresse ferait croire à une page supprimée."""
    return (ev.get("wp_permalink_as") or "").strip() or "(permalien inconnu en base)"


def _periode(ev: dict) -> str:
    d, f = (ev.get("date_event_start") or "")[:10], (ev.get("date_event_end") or "")[:10]
    if ev.get("recurring"):
        return "récurrent"
    if d and f and f != d:
        return f"{d} → {f}"
    return d or f or "sans date"


def analyser(rows: list[dict], today: str) -> tuple[list[list[dict]], dict]:
    """Renvoie les groupes suspects ET le compte de ce qui s'est présenté.

    Le second élément existe pour une raison précise : un `0` doit pouvoir se lire.
    « Aucun doublon » et « aucune fiche examinée » se ressemblent EXACTEMENT dans une
    sortie qui ne compte que le résultat — trois fois le 2026-08-11 un zéro a été pris
    pour une source pauvre alors qu'il venait de la requête.
    """
    vivantes = [ev for ev in rows if devant_nous(ev, today)]
    groupes = [g for g in _groups(vivantes) if len(g) > 1]
    suspects, ecartes = [], 0
    for g in groupes:
        # Un groupe entièrement composé de traductions les unes des autres n'est pas un
        # doublon. On ne retire pas la fiche traduite du groupe : on écarte la PAIRE, car
        # un trio FR/IT + vrai doublon doit continuer de remonter.
        reste = [a for i, a in enumerate(g)
                 if not all(paire_de_traduction(a, b) for j, b in enumerate(g) if j != i)]
        if len(reste) > 1:
            suspects.append(reste)
        else:
            ecartes += 1
    return suspects, {"publiees": len(rows), "vivantes": len(vivantes),
                      "groupes": len(groupes), "traductions": ecartes}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Deux fiches EN LIGNE sur le même événement. Lecture seule.")
    parser.add_argument("--slack", action="store_true", help="Poster le bilan sur Slack.")
    args = parser.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n"
              f"(data/ est hors dépôt Git — lancer ce script sur le VPS.)")
        return 1

    conn = _connect_ro(DB_PATH)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL").fetchall()]
    conn.close()

    suspects, compte = analyser(rows, date.today().isoformat())

    print("=" * 78)
    print("DOUBLONS PARMI LES FICHES EN LIGNE — lecture seule, rien n'a été modifié")
    print("=" * 78)
    print(f"Base                     : {DB_PATH}")
    print(f"Publiées (toutes dates)  : {compte['publiees']}")
    print(f"…dont encore devant nous : {compte['vivantes']}  ← LE PÉRIMÈTRE EXAMINÉ")
    print(f"Groupes de titres proches: {compte['groupes']}")
    print(f"…écartés (paires FR/IT)  : {compte['traductions']}  — normales, à LIER, "
          f"jamais à fusionner")
    print(f"SUSPECTS                 : {len(suspects)}")
    print()

    if not suspects:
        print("Aucun groupe suspect. Ce zéro se lit : "
              f"{compte['vivantes']} fiches examinées, {compte['groupes']} groupes formés,")
        print(f"{compte['traductions']} écartés comme paires de traduction. Un zéro sur "
              f"zéro fiche examinée aurait la même tête ;")
        print("c'est pour ça que les deux nombres sont là.")
        return 0

    for n, g in enumerate(suspects, 1):
        print(f"--- {n}. {len(g)} fiches en ligne sur le même événement ---")
        for ev in sorted(g, key=lambda e: e["id"]):
            print(f"  [{ev['id']:>5}] WP#{ev['wp_post_id_as']:<6} {_periode(ev):<24} "
                  f"{(ev.get('title') or '')[:52]}")
            print(f"          {_lien(ev)}")
        print()

    # LE GESTE AU BOUT DE LA LIGNE (règle 6). Une file sans geste n'est pas une file :
    # sur les 454 « points à contrôler » du 2026-08-11, trois cents n'avaient rien qu'un
    # humain puisse faire, et le seul qui comptait était noyé dessous.
    print("CE QU'IL Y A À FAIRE, groupe par groupe — c'est un arbitrage ÉDITORIAL, pas")
    print("technique, et aucun script ne le prend à votre place :")
    print("  • ouvrir les deux pages ; si c'est bien le même événement, garder celle qui")
    print("    a le meilleur article et corbeiller l'autre (réversible) :")
    print("      .venv/bin/python -m scripts.trash_by_ids <id à retirer> --apply")
    print("  • si ce sont DEUX ÉDITIONS différentes (2025 et 2026, ou deux dates), il n'y")
    print("    a rien à faire : les garder toutes les deux et me le dire, pour que la")
    print("    garde années/dates de dedupe soit corrigée plutôt que contournée.")

    if args.slack:
        from utils import slack
        lignes = [f"• {len(g)} pages : " + ", ".join(f"WP#{e['wp_post_id_as']}" for e in g)
                  for g in suspects[:10]]
        slack.post(f"*{len(suspects)} doublon(s) suspect(s) EN LIGNE* "
                   f"(sur {compte['vivantes']} fiches publiées encore devant nous)\n"
                   + "\n".join(lignes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
