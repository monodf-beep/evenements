# Le registre des décisions — la mémoire des signalements, pour qu'aucun ne se répète
# sans trace et qu'aucun ne meure en silence.
"""D'OÙ ÇA VIENT (2026-08-25). La fiche 4839 a été proposée à l'écartement QUATRE matins
de suite (21→25/08) sans qu'aucun geste soit posé : chaque matin, chaque agent relisait
les archives Slack pour reconstituer « signalé depuis quand, combien de fois » — un état
recalculé de mémoire, jamais écrit nulle part. Ce module l'écrit.

LA FORME : un journal d'événements EN AJOUT SEUL (`data/decisions.jsonl`). On n'y modifie
jamais une ligne ; l'état d'une décision est le REPLI de ses événements. C'est la règle 6
en structure de données : la trace est complète par construction, « résolu » est un
événement daté et signé, pas une case écrasée.

Trois événements suffisent :
  - `signale`  : quelqu'un (un audit, le cerveau, une session) voit un problème ;
  - `escalade` : la décision dépasse le mandat autonome, elle est posée à Franck —
                 UNE fois, datée ; les passages suivants n'ont plus à la répéter ;
  - `resolu`   : un geste a été posé, avec son résultat et son auteur.

RÈGLE 3 — QUI ROUVRE « RÉSOLU », ET SUR QUEL CRITÈRE. Un nouveau `signale` sur la même
clé ROUVRE la décision, automatiquement : le rouvreur sélectionne donc sur exactement le
même critère que le signaleur (même clé), pas sur un prédicat voisin — c'est la leçon des
neuf jours de `repair_polluted_descriptions` (docs/ETATS_TERMINAUX.md). Une décision
rouverte porte son compte de réouvertures : trois réouvertures, c'est un correctif qui ne
tient pas, et ça se voit.

Le compte des décisions garées est visible dans `scripts.decisions --liste`, qui affiche
toujours son dénominateur (« N en attente sur M enregistrées »).
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _chemin() -> Path:
    """Le fichier du registre. `DECISIONS_PATH` permet aux fixtures de pointer un
    jetable — même idiome que `DB_PATH`, même raison : jamais les données réelles."""
    brut = os.getenv("DECISIONS_PATH")
    return Path(brut) if brut else ROOT / "data" / "decisions.jsonl"


def _ajouter(evt: dict) -> None:
    evt = {"at": datetime.now().isoformat(timespec="seconds"), **evt}
    chemin = _chemin()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")


def _evenements() -> list[dict]:
    chemin = _chemin()
    if not chemin.exists():
        return []
    evts = []
    for brut in chemin.read_text(encoding="utf-8").splitlines():
        try:
            evts.append(json.loads(brut))
        except ValueError:
            continue  # une ligne corrompue ne doit pas rendre tout le registre illisible
    return evts


def etats() -> dict[str, dict]:
    """L'état de chaque décision : le repli, dans l'ordre, de ses événements."""
    d: dict[str, dict] = {}
    for evt in _evenements():
        cle = evt.get("cle")
        if not cle:
            continue
        e = d.setdefault(cle, {
            "cle": cle, "titre": "", "source": "", "geste": None, "etat": "ouverte",
            "premiere_vue": evt["at"], "derniere_vue": evt["at"], "vues": 0,
            "escalade_le": None, "resolution": None, "reouvertures": 0,
        })
        if evt.get("evt") == "signale":
            if e["etat"] == "resolue":
                # LE ROUVREUR (règle 3) : le problème est revenu, la décision rouvre —
                # même clé, donc même critère que le signaleur. Et ça se compte.
                e["etat"] = "ouverte"
                e["reouvertures"] += 1
                e["escalade_le"] = None
                e["resolution"] = None
            e["vues"] += 1
            e["derniere_vue"] = evt["at"]
            e["titre"] = evt.get("titre") or e["titre"]
            e["source"] = evt.get("source") or e["source"]
            e["geste"] = evt.get("geste") or e["geste"]
        elif evt.get("evt") == "escalade" and e["etat"] == "ouverte":
            e["escalade_le"] = evt["at"]
        elif evt.get("evt") == "resolu" and e["etat"] == "ouverte":
            e["etat"] = "resolue"
            e["resolution"] = {"at": evt["at"], "resultat": evt.get("resultat", ""),
                               "par": evt.get("par", "?")}
    return d


def signaler(cle: str, titre: str, source: str, geste: str | None = None) -> dict:
    """Enregistre un signalement (nouveau, répété — ou ROUVRANT, si la clé était
    résolue). Renvoie l'état replié après coup, pour que l'appelant sache s'il voit
    cette décision pour la première ou la dixième fois."""
    _ajouter({"evt": "signale", "cle": cle, "titre": titre, "source": source,
              **({"geste": geste} if geste else {})})
    return etats()[cle]


def escalader(cle: str, question: str = "") -> dict:
    """Marque la décision comme posée à Franck. REFUSE une clé inconnue ou résolue :
    escalader dans le vide, ou re-poser une question tranchée, sont deux façons de
    fabriquer du bruit — le registre les rend impossibles plutôt que silencieuses."""
    e = etats().get(cle)
    if e is None:
        raise ValueError(f"décision inconnue : {cle!r} — la signaler d'abord")
    if e["etat"] == "resolue":
        raise ValueError(f"décision déjà résolue : {cle!r} — un nouveau signalement la "
                         f"rouvrirait, mais on n'escalade pas une question tranchée")
    _ajouter({"evt": "escalade", "cle": cle, **({"question": question} if question else {})})
    return etats()[cle]


def resoudre(cle: str, resultat: str, par: str) -> dict:
    """Clôt la décision, avec le RÉSULTAT constaté (règle 6 : jamais l'intention) et
    son auteur. REFUSE une clé inconnue ou déjà résolue — un succès silencieux sur du
    vide est exactement le zéro sans dénominateur que ce dépôt traque."""
    e = etats().get(cle)
    if e is None:
        raise ValueError(f"décision inconnue : {cle!r} — rien à résoudre")
    if e["etat"] == "resolue":
        raise ValueError(f"décision déjà résolue : {cle!r} (le {e['resolution']['at']}, "
                         f"par {e['resolution']['par']})")
    _ajouter({"evt": "resolu", "cle": cle, "resultat": resultat, "par": par})
    return etats()[cle]


def en_attente() -> list[dict]:
    """Les décisions ouvertes, les plus anciennes d'abord — l'ancienneté est le poids."""
    return sorted((e for e in etats().values() if e["etat"] == "ouverte"),
                  key=lambda e: e["premiere_vue"])
