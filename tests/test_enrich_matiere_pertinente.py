#!/usr/bin/env python3
"""La matière « officielle » doit parler de CET événement (scripts/enrich.py, 2026-09-09).

MESURÉ en production le 09/09 au soir. Cinq fiches de bibliothèque de quartier ont vu le
résolveur rendre la RACINE `bct.comune.torino.it`, puis lire des pages de programme
génériques. Le même run écrivait « URL officielle NON mémorisée : pages sans mention du
titre » PUIS « matière officielle → article COMPLET » : deux détecteurs pour la même
chose, un seul juste (racine des fautes du 08/09). Conséquence : des articles longs du
modèle de qualité écrits sur des pages hors sujet — 219 749 tokens relus pour la seule
fiche 5208 — notés 7,4 à 8,1 et placés « En évidence (home) ».

Cette fixture éprouve la décision, pas la rédaction : elle rejoue le calcul de pertinence
tel qu'il est écrit dans enrich, avec de vrais titres et de vrais extraits de pages.

Usage : .venv/bin/python -m tests.test_enrich_matiere_pertinente
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.enrich import _fold, _event_tokens  # noqa: E402

echecs = 0


def verifier(nom: str, condition: bool, detail: str = "") -> None:
    global echecs
    if condition:
        print(f"OK    {nom}")
    else:
        echecs += 1
        print(f"ÉCHEC {nom}" + (f" — {detail}" if detail else ""))


def pertinent(titre: str, pages: list[str]) -> bool:
    """La décision telle qu'elle est prise dans enrich._enrich_one."""
    joint = _fold(" ".join((p or "")[:20000] for p in pages))
    toks = _event_tokens(titre)
    return (not toks) or any(t in joint for t in toks)


# ── Le cas réel qui a tout déclenché : pages de programme génériques de la
#    bibliothèque de Turin, pour un atelier couture qu'elles ne nomment jamais.
PAGES_GENERIQUES = [
    "<h1>Programmi</h1><p>Le biblioteche civiche torinesi propongono ogni mese "
    "incontri, letture e laboratori per tutte le et&agrave;.</p>",
    "<h1>Concerti e spettacoli</h1><p>Rassegna di appuntamenti musicali nelle sedi "
    "delle biblioteche civiche.</p>",
]
verifier("5180 « Mani in opera... con la macchina da cucire » sur des pages de programme "
         "génériques : matière NON pertinente (donc ni article long ni modèle cher)",
         not pertinent("Mani in opera... con la macchina da cucire", PAGES_GENERIQUES))
verifier("5208 « Piccoli racconti (0-3 anni) » : idem",
         not pertinent("Piccoli racconti (0-3 anni)", PAGES_GENERIQUES))

# ── CAS FRONTIÈRE QUI DOIT PASSER : la même bibliothèque, mais une page qui nomme
#    vraiment l'atelier. Si ce cas est refusé, la règle est devenue trop stricte et
#    on aurait cassé la complétion maximale là où elle a lieu d'être.
PAGE_QUI_NOMME = [
    "<h1>Mani in opera con la macchina da cucire</h1><p>Laboratorio di cucito "
    "creativo alla Biblioteca civica Villa Amoretti, ogni marted&igrave;.</p>",
]
verifier("frontière : une page qui NOMME l'atelier rend la matière pertinente "
         "(la complétion maximale reste possible)",
         pertinent("Mani in opera... con la macchina da cucire", PAGE_QUI_NOMME))

# ── Un mot du titre suffit, et il doit être significatif.
verifier("un seul mot significatif commun suffit (« Barolo »)",
         pertinent("Io, Barolo", ["<p>La rassegna Io, Barolo torna nel borgo medievale.</p>"]))
verifier("les mots courts et génériques ne comptent pas : un titre qui n'a que ceux-là "
         "ne peut pas rendre une page pertinente par hasard",
         not pertinent("Les Journées du patrimoine",
                       ["<p>Conseil municipal : ordre du jour de la séance.</p>"]))

# ── Titre sans aucun mot exploitable : on ne bloque pas (on ne sait pas juger).
# (Titre choisi après un premier essai raté : « Io, 2026 » n'était PAS un titre sans
# mot significatif — « 2026 » fait quatre caractères et compte comme un token. La
# fixture disait donc autre chose que ce qu'elle prétendait tester.)
verifier("titre sans aucun mot significatif (« Duo ») : la pertinence est accordée par "
         "défaut, faute de pouvoir en juger — on ne bloque jamais sur une ignorance",
         pertinent("Duo", ["<p>Une page quelconque.</p>"]))
verifier("…et « Duo » n'a effectivement aucun token exploitable",
         _event_tokens("Duo") == [], str(_event_tokens("Duo")))

# ── Accents : la comparaison est désaccentuée des deux côtés.
verifier("les accents ne font pas rater une page pertinente",
         pertinent("Soirées du Comité de lecture",
                   ["<p>Les soirees du comite de lecture reprennent en septembre.</p>"]))

# ── La valeur « confiance » est ramenée au français à l'écriture ────────────
_CONF = {"alta": "haute", "high": "haute", "elevata": "haute", "élevée": "haute",
         "media": "moyenne", "medium": "moyenne", "moyen": "moyenne",
         "bassa": "faible", "low": "faible", "basse": "faible"}
verifier("« alta », rendu par le modèle sur trois fiches italiennes ce soir, devient « haute »",
         _CONF.get("alta") == "haute")
verifier("« bassa » devient « faible »", _CONF.get("bassa") == "faible")
verifier("une valeur déjà française n'est pas dans la table de conversion (rien à faire)",
         "haute" not in _CONF and "moyenne" not in _CONF and "faible" not in _CONF)

print(f"\n{'SUCCÈS — 0 problème(s).' if echecs == 0 else f'ÉCHEC — {echecs} problème(s).'}")
sys.exit(1 if echecs else 0)
