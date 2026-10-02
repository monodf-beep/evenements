#!/usr/bin/env python3
"""Les fichiers « SYNCED FROM observatoire-business-sabaudo » ont-ils divergé ?

POURQUOI CE SCRIPT EXISTE. Une dizaine de fichiers sont des copies verbatim partagées
avec observatoire-business-sabaudo, en attendant l'extraction de cultura-core. La seule
chose qui empêchait l'oubli était une ligne de commentaire en tête de fichier. Elle n'a
pas suffi : `config/blocked_image_domains.txt` avait divergé, et cette divergence a
laissé passer 41 fiches illustrées par des photos de presse (docs/CONFORMITE.md §3).
Le 2026-08-05, trois reports étaient en attente en même temps, dont un que personne
n'avait remarqué. Un commentaire ne se lit qu'une fois ; un audit refuse à chaque run.

CE QU'IL FAIT. Il relève l'empreinte de chaque fichier marqué et la compare à celle
enregistrée dans `config/sync_amont.json` au moment du dernier report effectif. Trois
verdicts possibles par fichier :

  · aligné            — l'empreinte n'a pas bougé depuis le dernier report ;
  · À PORTER          — le fichier a été modifié ICI depuis le dernier report ;
  · divergence assumée — écart voulu et documenté (ex. territory_images.txt).

Il détecte aussi un fichier marqué ABSENT du manifeste (une autre session a pu en
ajouter un) et une entrée dont le fichier a disparu.

CE QU'IL NE FAIT PAS. Il ne lit pas l'autre dépôt : il n'a aucun moyen de savoir ce qui
s'y trouve. Il dit « ce fichier a bougé chez nous depuis qu'on l'a déclaré aligné »,
pas « les deux versions diffèrent ». C'est suffisant pour le seul risque réel — oublier
de porter — et ça ne demande aucun accès distant.

Usage :
    .venv/bin/python -m scripts.audit_sync_amont            # audit, sort 1 si dérive
    .venv/bin/python -m scripts.audit_sync_amont --record   # APRÈS avoir porté
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFESTE = ROOT / "config" / "sync_amont.json"

MARQUEUR = "SYNCED FROM"
# PREMIÈRE LIGNE SEULEMENT, et c'est délibéré. Les huit fichiers concernés portent tous
# le marqueur en ligne 1 : c'est la convention, pas un hasard. Chercher plus loin ramène
# la PROSE qui parle du marqueur — README, docs/BACKLOG.md et docs/CONFORMITE.md le
# citent tous les trois sans être synchronisés, et ce script s'attrapait lui-même par sa
# propre docstring. Une règle stricte sur une convention respectée vaut mieux qu'une
# règle large assortie d'une liste d'exceptions à tenir.
LIGNES_ENTETE = 1

# Dossiers sans intérêt ici, et qui coûteraient cher à parcourir.
IGNORES = {".git", ".venv", "node_modules", "data", "logs", "rapports", "__pycache__"}


def empreinte(chemin: Path) -> str:
    """SHA-256 du contenu, insensible aux fins de ligne : le dépôt est édité depuis
    Windows et Linux, et un CRLF n'est pas une divergence de fond."""
    brut = chemin.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(brut).hexdigest()


def fichiers_marques() -> list[str]:
    """Chemins relatifs des fichiers portant l'en-tête, triés."""
    trouves = []
    for chemin in ROOT.rglob("*"):
        if not chemin.is_file():
            continue
        if IGNORES & set(chemin.relative_to(ROOT).parts):
            continue
        try:
            with open(chemin, "r", encoding="utf-8", errors="strict") as fh:
                debut = "".join(next(fh, "") for _ in range(LIGNES_ENTETE))
        except (UnicodeDecodeError, OSError):
            continue
        if MARQUEUR in debut:
            trouves.append(chemin.relative_to(ROOT).as_posix())
    return sorted(trouves)


def charger() -> dict:
    if not MANIFESTE.exists():
        return {}
    return json.loads(MANIFESTE.read_text(encoding="utf-8")).get("fichiers", {})


def auditer() -> tuple[list, list, list, list]:
    """(alignés, à porter, divergences assumées, anomalies de manifeste)."""
    manifeste = charger()
    presents = fichiers_marques()
    alignes, a_porter, assumees, anomalies = [], [], [], []

    for rel in presents:
        entree = manifeste.get(rel)
        if entree is None:
            anomalies.append((rel, "porte l'en-tête mais N'EST PAS au manifeste"))
            continue
        if entree.get("statut") == "divergence_assumee":
            assumees.append((rel, entree.get("note", "")))
            continue
        actuel = empreinte(ROOT / rel)
        if entree.get("sha256_porte") == actuel:
            alignes.append((rel, entree.get("porte_le", "?")))
        else:
            a_porter.append((rel, entree.get("porte_le") or "jamais",
                             entree.get("note", "")))

    for rel in manifeste:
        if rel not in presents:
            anomalies.append((rel, "au manifeste mais l'en-tête a disparu du fichier"))
    return alignes, a_porter, assumees, anomalies


def enregistrer() -> int:
    """Fige l'état ACTUEL comme « porté ». À n'appeler qu'après l'avoir fait vraiment."""
    manifeste = charger()
    aujourdhui = date.today().isoformat()
    marques = fichiers_marques()
    # Un fichier qui a perdu son en-tête n'est plus partagé : sans cet élagage, son
    # entrée resterait au manifeste et l'anomalie qu'elle produit ne se refermerait
    # JAMAIS — un audit qui échoue toujours finit par ne plus être lu.
    for rel in [r for r in manifeste if r not in marques]:
        print(f"  retiré du manifeste (l'en-tête a disparu du fichier) : {rel}")
        manifeste.pop(rel)
    for rel in marques:
        entree = manifeste.setdefault(rel, {})
        if entree.get("statut") == "divergence_assumee":
            continue
        entree["sha256_porte"] = empreinte(ROOT / rel)
        entree["porte_le"] = aujourdhui
        entree["statut"] = "porte"
        entree.pop("note", None)
    MANIFESTE.write_text(json.dumps(
        {"_lisez_moi": "Voir scripts/audit_sync_amont.py. Ne pas éditer à la main : "
                       "utiliser --record APRÈS avoir porté dans l'autre dépôt.",
         "fichiers": dict(sorted(manifeste.items()))},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Manifeste mis à jour ({len(manifeste)} fichier(s)) : {MANIFESTE}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--record", action="store_true",
                    help="Fige l'état actuel comme porté. À lancer APRÈS avoir "
                         "réellement copié les fichiers dans l'autre dépôt.")
    args = ap.parse_args(argv)
    if args.record:
        return enregistrer()

    alignes, a_porter, assumees, anomalies = auditer()
    print("=" * 78)
    print("Fichiers partagés avec observatoire-business-sabaudo")
    print("=" * 78)
    print(f"  alignés depuis le dernier report : {len(alignes)}")
    print(f"  À PORTER                         : {len(a_porter)}")
    print(f"  divergences assumées             : {len(assumees)}")
    print(f"  anomalies de manifeste           : {len(anomalies)}")

    if a_porter:
        print("\n--- À PORTER dans observatoire-business-sabaudo ---")
        for rel, depuis, note in a_porter:
            print(f"  {rel}")
            print(f"      dernier report : {depuis}")
            if note:
                print(f"      {note}")
    if anomalies:
        print("\n--- ANOMALIES ---")
        for rel, quoi in anomalies:
            print(f"  {rel} — {quoi}")
    if assumees:
        print("\n--- divergences assumées (aucune action) ---")
        for rel, note in assumees:
            print(f"  {rel} — {note}")
    if alignes:
        print("\n--- alignés ---")
        for rel, depuis in alignes:
            print(f"  {rel} (porté le {depuis})")

    if a_porter or anomalies:
        print("\nUne fois la copie faite dans l'autre dépôt :")
        print("  .venv/bin/python -m scripts.audit_sync_amont --record")
        return 1
    print("\nRien à porter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
