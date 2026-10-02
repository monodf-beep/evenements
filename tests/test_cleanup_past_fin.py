#!/usr/bin/env python3
"""Fixture : « passé » se juge sur la date de FIN (scripts.cleanup_as_dupes).

D'OÙ ÇA VIENT — 2026-08-18. Le ménage hebdomadaire imprimait depuis toujours « ℹ 21 sont
déjà sur l'agenda (brouillon WP) → pense à `cleanup_as_dupes --past --execute` » : un
message automatique qui demande à un humain de taper une commande réversible, c'est-à-dire
la règle 3 prise en défaut. Avant de l'automatiser, il fallait vérifier ce que `--past`
mettait réellement à la corbeille.

CE QU'IL FAISAIT : il tranchait sur la date de DÉBUT. L'inventaire réel du site, ce
jour-là, contenait :

    [582] « Marc Chagall s'expose à Vercelli » — brouillon, début 2026-03-29, fin 2026-10-13
    [578] « Au Castello di Rivoli »           — brouillon, début 2026-01-01, fin 2026-12-31

Cinq mois de début révolu, deux mois d'exposition encore à venir. Automatiser `--past` en
l'état aurait corbeillé ces brouillons en plein milieu — c'est exactement l'erreur que la
règle 5 de CLAUDE.md interdit : « c'est `date_event_end` qui décide, jamais
`date_event_start` seule ».

La route WordPress ne rendait même pas la fin : il a fallu l'ajouter (snippet #10).

LE CAS QUI DOIT PASSER est donc ici le cas NON FLAGUÉ : Chagall doit survivre. Une fixture
qui ne vérifierait que « les vieux événements sont bien détectés » aurait validé le
comportement fautif.

Lancer : .venv/bin/python -m tests.test_cleanup_past_fin
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.cleanup_as_dupes import find_incomplete_past  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


AUJOURDHUI = "2026-08-18"

# Charge recopiée de l'inventaire réel (cs/v1/list), plus deux cas construits.
INVENTAIRE = [
    {"id": 582, "title": "Marc Chagall s'expose à Vercelli", "status": "draft",
     "start": "2026-03-29 00:00:00", "end": "2026-10-13 23:59:59", "venue": 12, "thumb": 1},
    {"id": 578, "title": "Au Castello di Rivoli", "status": "draft",
     "start": "2026-01-01 00:00:00", "end": "2026-12-31 23:59:59", "venue": 9, "thumb": 1},
    {"id": 700, "title": "Concert d'un soir, bien terminé", "status": "draft",
     "start": "2026-07-04 20:00:00", "end": "2026-07-04 23:00:00", "venue": 5, "thumb": 1},
    {"id": 14, "title": "Matisse — Yves Saint Laurent", "status": "publish",
     "start": "2026-06-17 00:00:00", "end": "2026-09-28 23:59:59", "venue": 3, "thumb": 1},
    {"id": 900, "title": "Vieil événement, inventaire sans fin", "status": "draft",
     "start": "2026-05-02 00:00:00", "venue": 7, "thumb": 1},
    {"id": 901, "title": "Brouillon sans lieu ni date", "status": "draft",
     "start": "", "venue": 0, "thumb": 0},
]

passes = find_incomplete_past(INVENTAIRE, AUJOURDHUI, incomplete=False, past=True)

# ── LE CAS QUI DOIT PASSER (= ne pas être flagué) ───────────────────────────────
verifier("l'exposition en cours (Chagall, fin en octobre) est ÉPARGNÉE",
         582 not in passes, str(passes.get(582)))
verifier("l'exposition annuelle (Rivoli, fin en décembre) est ÉPARGNÉE",
         578 not in passes, str(passes.get(578)))

# ── Ce qui doit bien être attrapé ───────────────────────────────────────────────
verifier("le concert du 4 juillet est bien détecté comme passé", 700 in passes)
verifier("le motif nomme la FIN, pour qu'on puisse le contredire",
         "fin 2026-07-04" in passes.get(700, ""), passes.get(700))

# ── Ce qu'on ne touche jamais ───────────────────────────────────────────────────
verifier("un exemplaire PUBLIÉ n'est jamais flagué", 14 not in passes)

# ── Compatibilité : un inventaire sans `end` retombe sur le début, et le DIT ────
verifier("sans date de fin, on retombe sur le début", 900 in passes)
verifier("et le motif annonce que la fin était inconnue",
         "fin inconnue" in passes.get(900, ""), passes.get(900))

# ── Une fiche sans aucune date n'est pas « passée » (règle 5) ───────────────────
verifier("une fiche sans date n'est PAS classée passée", 901 not in passes)

# …mais elle reste attrapable comme incomplète, ce qui est un autre motif.
incomplets = find_incomplete_past(INVENTAIRE, AUJOURDHUI, incomplete=True, past=False)
verifier("la fiche sans lieu ni date est vue comme incomplète", 901 in incomplets)
verifier("et l'exposition en cours n'est pas devenue incomplète au passage",
         582 not in incomplets)

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
