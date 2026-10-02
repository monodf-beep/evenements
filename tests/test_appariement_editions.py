#!/usr/bin/env python3
"""Fixture : `scripts.appariement_editions` — qui est proposé comme édition suivante
d'une fiche déjà publiée, et surtout qui NE L'EST PAS.

Sept cas, choisis près de la frontière plutôt qu'au centre — le risque réel est celui
du 2026-08-02 (fusion à tort par recouvrement de tokens), transposé à un an d'écart :

  1. même festival, même lieu, ~365 j d'écart, l'un publié → PROPOSÉ (cas nominal) ;
  2. même festival mais AUCUN des deux n'est publié → PAS proposé (rien à réutiliser) ;
  3. même festival mais LIEUX DIFFÉRENTS (le festival a déménagé) → PAS proposé ;
  4. même mots-clés mais titres à faible recouvrement (deux salons différents qui
     partagent juste "salon" + la ville) → PAS proposé ;
  5. écart de 40 jours (même année, pas deux éditions) → PAS proposé ;
  6. écart de 600 jours (trop loin pour être l'édition suivante) → PAS proposé ;
  7. LE CAS QUI DOIT PASSER, à la frontière basse : écart de 301 jours, lieu absent
     d'un côté (donnée manquante, pas désaccord) → PROPOSÉ.

⚠️ Ne lit jamais data/events.db — fixtures construites en mémoire.

Lancer : .venv/bin/python -m tests.test_appariement_editions
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.appariement_editions import appariements  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


def ev(id_, title, lieu, date_start, wp=None):
    return {"id": id_, "title": title, "lieu": lieu, "date_event_start": date_start,
            "wp_post_id_as": wp, "duplicate_of": None}


EVENTS = [
    # 1. Cas nominal
    ev(1, "La Farandole 2026 : festival international de folklore",
       "Promenade des Anglais", "2026-08-12", wp=6001),
    ev(2, "La Farandole 2027 : festival international de folklore",
       "Promenade des Anglais", "2027-08-11"),
    # 2. Ni l'un ni l'autre publié
    ev(3, "Terra Madre 2026 : Salone del Gusto", "Lingotto Fiere", "2026-09-24"),
    ev(4, "Terra Madre 2027 : Salone del Gusto", "Lingotto Fiere", "2027-09-23"),
    # 3. Lieux différents (déménagement) — festival déménagé, pas la même édition
    ev(5, "Foire de Savoie 2026", "Parc des expositions de Chambéry", "2026-05-01", wp=6002),
    ev(6, "Foire de Savoie 2027", "Halle olympique d'Albertville", "2027-05-01"),
    # 4. Faible recouvrement (deux salons distincts, même ville)
    ev(7, "Salon du livre de Turin", "Lingotto Fiere", "2026-05-14", wp=6003),
    ev(8, "Salon de l'auto de Turin", "Lingotto Fiere", "2027-05-13"),
    # 5. Écart de 40 jours (même année)
    ev(9, "Festival Jazz à Vienne", "Théâtre antique", "2026-07-01", wp=6004),
    ev(10, "Festival Jazz à Vienne, nocturne exceptionnelle", "Théâtre antique", "2026-08-10"),
    # 6. Écart de 600 jours
    ev(11, "Fête du Jambon de Bosses 2026", "Bosses", "2026-07-28", wp=6005),
    ev(12, "Fête du Jambon de Bosses 2028", "Bosses", "2028-03-20"),
    # 7. Cas frontière : 301 jours, lieu absent d'un côté
    ev(13, "Vicoforte, la grande fiera del santuario", "", "2026-09-08", wp=6006),
    ev(14, "Vicoforte, la grande fiera del santuario 2027", "Santuario di Vicoforte", "2027-07-05"),
]

paires = appariements(EVENTS)
trouves = {frozenset((a["id"], b["id"])) for a, b, _ in paires}

verifier("① cas nominal (Farandole, même lieu, ~365 j, publié) : PROPOSÉ",
         frozenset((1, 2)) in trouves)
verifier("② aucun publié (Terra Madre) : PAS proposé",
         frozenset((3, 4)) not in trouves)
verifier("③ lieux différents (Foire de Savoie déménagée) : PAS proposé",
         frozenset((5, 6)) not in trouves)
verifier("④ faible recouvrement (salon du livre ≠ salon de l'auto) : PAS proposé",
         frozenset((7, 8)) not in trouves)
verifier("⑤ écart de 40 jours, même année (Jazz à Vienne) : PAS proposé",
         frozenset((9, 10)) not in trouves)
verifier("⑥ écart de 600 jours (Jambon de Bosses) : PAS proposé",
         frozenset((11, 12)) not in trouves)
verifier("⑦ LE CAS QUI DOIT PASSER : 301 j, lieu absent d'un côté (Vicoforte) : PROPOSÉ",
         frozenset((13, 14)) in trouves)

verifier("aucune paire fantôme au-delà des 2 attendues", len(paires) == 2, str(trouves))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
