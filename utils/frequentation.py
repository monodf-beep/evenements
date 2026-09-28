#!/usr/bin/env python3
"""Quelles pages du back-office sont VRAIMENT ouvertes — compté par le back-office lui-même.

Franck, 2026-09-22 : « s'il y a des choses qui ne servent plus, on les enlève ».

POURQUOI PAS LE JOURNAL DU SERVEUR. On a essayé le même jour. La sortie ne contenait
aucune page du back-office et presque rien d'autre que du balayage automatisé — sondes
`/.env`, `/wp-login.php`, `/.git/config`. Deux défauts insurmontables pour cette
question : on lisait le mauvais fichier, et même le bon mélangerait les visites de
Franck avec celles des robots. Une page ouverte trois fois par un scanner paraîtrait
utile ; une page qu'il n'atteint pas paraîtrait morte.

CE QU'ON COMPTE, ET RIEN D'AUTRE :
  • une requête GET, qui a RÉUSSI (200), qui rend une PAGE (HTML) ;
  • d'une session AUTHENTIFIÉE — donc Franck, pas un robot ;
  • sur une adresse qui est AU MENU (`utils.menu`). Le reste (aperçus de fiches,
    exports, actions) n'est pas une destination de menu : le compter noierait la
    question posée.

LA DATE DE DÉPART EST AUSSI IMPORTANTE QUE LE COMPTE. Un zéro ne dit pas s'il vient
d'un désintérêt ou d'une mesure qui vient de commencer (CLAUDE.md). Chaque ligne porte
donc son premier passage, et l'affichage doit écrire « mesuré depuis le … » à côté des
chiffres — sinon on supprimera une page au bout de deux jours d'observation.

CE QU'IL NE FAIT PAS. Il n'enregistre ni qui, ni quoi, ni d'où : un chemin, un compte,
deux dates. Il ne sert qu'à répondre « est-ce que cette page s'ouvre encore ».
"""
from __future__ import annotations

import sqlite3

TABLE = "page_hits"


def assure(conn: sqlite3.Connection) -> None:
    """Crée la table si besoin. Appelée à chaque écriture — idempotent et sans coût."""
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
        chemin  TEXT PRIMARY KEY,
        n       INTEGER NOT NULL DEFAULT 0,
        premier TEXT NOT NULL,
        dernier TEXT NOT NULL)""")


def note(conn: sqlite3.Connection, chemin: str) -> None:
    """Compte une ouverture. Ne lève JAMAIS : une mesure ne casse pas la page mesurée."""
    try:
        assure(conn)
        conn.execute(
            f"INSERT INTO {TABLE} (chemin, n, premier, dernier) "
            "VALUES (?, 1, datetime('now'), datetime('now')) "
            "ON CONFLICT(chemin) DO UPDATE SET n = n + 1, dernier = datetime('now')",
            (chemin,))
        conn.commit()
    except sqlite3.Error:
        pass


def depuis(conn: sqlite3.Connection) -> str:
    """Date du tout premier passage enregistré — le périmètre de tous les chiffres."""
    try:
        assure(conn)
        r = conn.execute(f"SELECT MIN(premier) FROM {TABLE}").fetchone()
        return (r[0] or "")[:10] if r else ""
    except sqlite3.Error:
        return ""


def par_page(conn: sqlite3.Connection, pages: list[dict]) -> list[dict]:
    """Une ligne par page du MENU, ouvertures comprises — y compris celles à zéro.

    C'est le sens de la mesure : ce sont les zéros qu'on cherche. Les lire depuis la
    carte plutôt que depuis la table garantit qu'une page jamais ouverte apparaisse,
    au lieu d'être simplement absente — une absence ne se remarque pas.
    """
    try:
        assure(conn)
        lus = {r[0]: (r[1], r[2]) for r in
               conn.execute(f"SELECT chemin, n, dernier FROM {TABLE}").fetchall()}
    except sqlite3.Error:
        lus = {}
    out = []
    for p in pages:
        n, dernier = lus.get(p["url"], (0, ""))
        out.append({"url": p["url"], "libelle": p["libelle"], "icone": p["icone"],
                    "groupe": p["groupe"], "resume": p["resume"],
                    "n": n, "dernier": (dernier or "")[:10]})
    out.sort(key=lambda r: (r["n"], r["libelle"]))
    return out
