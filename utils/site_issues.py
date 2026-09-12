#!/usr/bin/env python3
"""Journal PERSISTANT des problèmes de SITE (front-end WordPress/Elementor — menu,
gabarits, filtres...) repérés en conversation (captures d'écran Franck) ou par un script
de surveillance (homepage_health.py).

Distinct de `utils.pipeline_status` (table `pipeline_runs`, SQLite sur le VPS — résultats
d'un RUN d'automatisation) : ici on journalise des BUGS DE SITE constatés, dans un fichier
VERSIONNÉ (`docs/site_issues.json`, suivi par git) plutôt qu'en base — ces problèmes sont
repérés depuis une session GitHub (accès dépôt, pas VPS/DB), et doivent rester lisibles
par n'importe quelle session future (humaine ou IA) sans dépendre de la mémoire du chat
ni d'un accès VPS. `git log` sur ce fichier donne l'historique ; le statut de chaque
entrée donne l'état courant.

Usage (dans une session Claude, ou en CLI) :
    python3 -m utils.site_issues add "Titre court" "Description" --category menu
    python3 -m utils.site_issues list
    python3 -m utils.site_issues resolve 3 --notes "Corrigé côté widget X, confirmé live."
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "docs" / "site_issues.json"


def _load() -> list[dict]:
    if PATH.exists():
        return json.loads(PATH.read_text(encoding="utf-8"))
    return []


def _save(issues: list[dict]) -> None:
    PATH.write_text(json.dumps(issues, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_issue(title: str, description: str, category: str = "wordpress-template",
             source: str = "conversation", prompt_file: str = "") -> int:
    """Ajoute un problème 'open'. Retourne son id."""
    issues = _load()
    new_id = max([i["id"] for i in issues], default=0) + 1
    issues.append({
        "id": new_id,
        "title": title,
        "description": description,
        "category": category,
        "status": "open",
        "source": source,
        "prompt_file": prompt_file,
        "opened_at": datetime.now().isoformat(timespec="seconds"),
        "resolved_at": None,
        "resolution_notes": "",
    })
    _save(issues)
    return new_id


def resolve_issue(issue_id: int, notes: str = "", status: str = "fixed") -> bool:
    """status : 'fixed' (corrigé) ou 'wontfix' (pas la peine)."""
    issues = _load()
    found = False
    for i in issues:
        if i["id"] == issue_id:
            i["status"] = status
            i["resolved_at"] = datetime.now().isoformat(timespec="seconds")
            i["resolution_notes"] = notes
            found = True
    if found:
        _save(issues)
    return found


def list_issues(status: str | None = "open") -> list[dict]:
    issues = _load()
    return [i for i in issues if status is None or i["status"] == status]


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Journal des problèmes de site.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add")
    p_add.add_argument("title")
    p_add.add_argument("description")
    p_add.add_argument("--category", default="wordpress-template")
    p_add.add_argument("--source", default="conversation")
    p_add.add_argument("--prompt-file", default="")

    p_list = sub.add_parser("list")
    p_list.add_argument("--status", default="open", help="open|fixed|wontfix|all")

    p_resolve = sub.add_parser("resolve")
    p_resolve.add_argument("id", type=int)
    p_resolve.add_argument("--notes", default="")
    p_resolve.add_argument("--status", default="fixed", choices=["fixed", "wontfix"])

    args = parser.parse_args(argv)

    if args.cmd == "add":
        new_id = add_issue(args.title, args.description, args.category,
                           args.source, args.prompt_file)
        print(f"Ajouté : issue #{new_id}")
    elif args.cmd == "list":
        status = None if args.status == "all" else args.status
        for i in list_issues(status):
            print(f"[{i['id']}] ({i['status']}) {i['title']} — {i['opened_at']}")
    elif args.cmd == "resolve":
        ok = resolve_issue(args.id, args.notes, args.status)
        print("OK" if ok else f"Id {args.id} introuvable")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))
