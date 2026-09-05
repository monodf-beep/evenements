#!/usr/bin/env python3
"""Verse les trouvailles d'un audit SEO dans le tableau de bord `/seo` du back-office.

POURQUOI CE SCRIPT EXISTE. La page `/seo` du back-office, ses tables `seo_findings` /
`seo_runs`, son tri par sévérité et ses boutons « fait / écarté » existent depuis
longtemps — et son sous-titre dit « audits SEO (manuels pour l'instant) ». Elle était
vide, non par manque de trouvailles, mais parce qu'aucun script ne l'alimentait. L'audit
du 2026-08-12 a été écrit dans un fichier Markdown que personne ne relira ; ce script le
fait atterrir là où il se transforme en gestes.

CE QU'ON VERSE, ET CE QU'ON NE VERSE PAS. Uniquement des défauts de GABARIT : chacun se
corrige une fois et vaut pour tout le catalogue. Aucune ligne « telle fiche a un titre
trop long ». C'est la leçon du 2026-08-11 — « 548 tâches, c'est ingérable » : une file
n'est utile que si chaque ligne a un geste au bout et si ce geste répare plus qu'une page.

IDEMPOTENT, ET C'EST LE POINT DÉLICAT. Un second run ne recrée pas ce qui existe déjà,
quel que soit son statut. Une trouvaille que Franck a soldée (« fait ») ou écartée
(« pas pertinent ») ne doit JAMAIS ressusciter toute seule : ce serait le meilleur moyen
de faire ignorer la file entière.

QUI ROUVRE, ALORS (règle 3) ? Trois rouvreurs, et aucun n'est « un humain qui y pense » :

  • pour les sept signaux de site (cache, Organization, robots, hreflang de l'accueil…),
    c'est `scripts/gabarit_health.py` : il mesure tous les jours et crie sur la BASCULE,
    donc une régression revient d'elle-même, même si la ligne a été soldée ici ;
  • pour les défauts éditoriaux, c'est la passe trimestrielle de l'agent B
    (`docs/AGENT_SEO_DASHBOARD_SPEC.md` §3), relancée avec `--force` ;
  • et `--force` reste disponible à tout moment pour reverser un fichier entier.

Le compteur de fin dit ce qu'il compte : combien versées, combien ignorées parce que déjà
présentes, et sous quel statut — un « 0 versée » ne doit pas pouvoir se confondre avec un
fichier vide ou une erreur de lecture.

DRY-RUN PAR DÉFAUT (règle 4). Sans `--apply`, le script montre ce qu'il verserait et
n'écrit rien. La première version faisait l'inverse — `--dry-run` en option, écriture par
défaut — et c'est `tests/test_regles_du_depot.py` qui l'a refusée avant le déploiement,
pas une relecture. Le cliquet fonctionne : on le laisse tel quel.

Usage :
    .venv/bin/python -m scripts.seo_findings_import docs/audit_seo_2026-08-12_findings.json
    .venv/bin/python -m scripts.seo_findings_import docs/audit_seo_2026-08-12_findings.json --apply
    .venv/bin/python -m scripts.seo_findings_import <fichier> --apply --force  # reverse tout
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("seo_findings_import")

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
SEVERITES = ("critical", "high", "medium", "low", "info")


def assure_tables(conn: sqlite3.Connection) -> None:
    """Même schéma que `app.app._ensure_seo_tables`, recopié pour que le script tourne en
    cron sans importer Flask. Les deux CREATE sont `IF NOT EXISTS` : si l'application les a
    déjà créées, on ne touche à rien."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS seo_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT DEFAULT (datetime('now')),
        scope TEXT, pages_count INTEGER, agents_used TEXT,
        tokens_used INTEGER, notes TEXT)""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS seo_findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER, page_url TEXT, category TEXT,
        severity TEXT NOT NULL DEFAULT 'medium',
        title TEXT NOT NULL, description TEXT, recommendation TEXT,
        source_agent TEXT, status TEXT NOT NULL DEFAULT 'todo',
        created_at TEXT DEFAULT (datetime('now')), resolved_at TEXT)""")
    conn.commit()


def _deja_presente(conn: sqlite3.Connection, titre: str) -> str | None:
    """Renvoie le statut de la trouvaille homonyme, ou None. Le titre fait la clé : c'est
    ce que Franck lit à l'écran, donc c'est le bon grain d'unicité — deux lignes au même
    titre seraient indiscernables pour lui, quelle que soit leur différence en base."""
    r = conn.execute("SELECT status FROM seo_findings WHERE title = ? LIMIT 1",
                     (titre,)).fetchone()
    return r[0] if r else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verse les trouvailles d'un audit SEO dans le tableau de bord /seo.")
    parser.add_argument("fichier", help="JSON produit par un audit (voir docs/).")
    parser.add_argument("--apply", action="store_true",
                        help="Écrit réellement. SANS ce drapeau, rien n'est enregistré.")
    parser.add_argument("--force", action="store_true",
                        help="Reverse même les trouvailles déjà présentes (y compris soldées).")
    args = parser.parse_args(argv)

    chemin = Path(args.fichier)
    try:
        data = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.error("fichier illisible (%s) : %s", chemin, exc)
        return 2

    trouvailles = data.get("findings") or []
    if not trouvailles:
        log.error("aucune trouvaille dans %s — rien à verser, et ce n'est PAS un succès",
                  chemin)
        return 2

    mauvaises = [f.get("title") for f in trouvailles
                 if f.get("severity") not in SEVERITES or not f.get("title")]
    if mauvaises:
        log.error("sévérité inconnue ou titre manquant sur %d ligne(s) : %s",
                  len(mauvaises), mauvaises[:3])
        return 2

    conn = sqlite3.connect(DB_PATH)
    assure_tables(conn)

    a_verser, ignorees = [], []
    for f in trouvailles:
        statut = None if args.force else _deja_presente(conn, f["title"])
        (ignorees if statut else a_verser).append((f, statut))

    print(f"{len(trouvailles)} trouvaille(s) dans le fichier "
          f"→ {len(a_verser)} à verser, {len(ignorees)} déjà présente(s)")
    for f, statut in ignorees:
        print(f"   déjà là [{statut}] {f['title'][:78]}")
    for f, _ in a_verser:
        print(f"   + [{f['severity']:8}] {f['title'][:78]}")

    if not args.apply:
        print("\nDry-run (défaut) : rien n'a été écrit. Relancer avec --apply pour verser.")
        conn.close()
        return 0
    if not a_verser:
        print("\nRien à verser (toutes déjà présentes). Utiliser --force pour reverser.")
        conn.close()
        return 0

    run = data.get("run") or {}
    cur = conn.execute(
        "INSERT INTO seo_runs (scope, pages_count, agents_used, tokens_used, notes) "
        "VALUES (?,?,?,?,?)",
        (run.get("scope"), run.get("pages_count"), run.get("agents_used"),
         run.get("tokens_used"), run.get("notes")))
    run_id = cur.lastrowid
    for f, _ in a_verser:
        conn.execute(
            "INSERT INTO seo_findings (run_id, page_url, category, severity, title, "
            "description, recommendation, source_agent, status) VALUES (?,?,?,?,?,?,?,?, 'todo')",
            (run_id, f.get("page_url"), f.get("category"), f["severity"], f["title"],
             f.get("description"), f.get("recommendation"),
             f.get("source_agent") or chemin.stem))
    conn.commit()

    # Règle 6 : on recompte EN BASE après l'écriture, on ne fait pas confiance à la
    # longueur de la liste qu'on vient de parcourir.
    todo = conn.execute("SELECT COUNT(*) FROM seo_findings WHERE status='todo'").fetchone()[0]
    graves = conn.execute("SELECT COUNT(*) FROM seo_findings WHERE status='todo' "
                          "AND severity IN ('critical','high')").fetchone()[0]
    conn.close()
    print(f"\nrun #{run_id} enregistré. En base après écriture : {todo} point(s) à traiter, "
          f"dont {graves} critique(s)/élevé(s) — c'est ce chiffre que porte la pastille /seo.")
    log.info("run #%d : %d versée(s), %d ignorée(s) ; %d à traiter en base",
             run_id, len(a_verser), len(ignorees), todo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
