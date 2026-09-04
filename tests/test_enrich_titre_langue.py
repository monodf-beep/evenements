#!/usr/bin/env python3
"""Fixture : `scripts.enrich.titre_corps_langue_desaccord` détecte un titre d'article
publié dans une langue différente de son corps — SANS jamais refuser un titre où
seul un nom propre reste en langue source (règle 3 de CLAUDE.md : la fixture doit
contenir un cas qui doit PASSER, choisi près de la frontière — pas seulement des cas
qui confirment le design).

INCIDENT RÉEL, 2026-09-04 : WP#7472 « Regine in Scena. L'arte del costume italiano tra
cinema e teatro » publiée avec un corps français correct (chapô+corps), mais un titre
resté ITALIEN — `scripts.enrich` écrit toujours le corps dans la langue voulue (défaut
français), jamais retraduit le champ « titre » du JSON de l'agent s'il l'a laissé dans
la langue source. `scripts.audit_titre_corps_langue --tout` en a trouvé 29 en
production, toutes dans le même sens (titre IT, corps FR) — signe d'un biais
systématique, pas d'un hasard.

Cas PRÈS DE LA FRONTIÈRE (celui qui DOIT passer) : le titre « Ankama alla Cité
Internationale du Cinéma d'Animation » sous un corps italien — déjà documenté dans
`utils.lang.titre_reecrit_mauvaise_langue` comme un nom propre légitimement laissé en
français dans une fiche italienne. `lang_nette` (utils/lang.py) tranche le TITRE ENTIER
(contrairement à `titre_reecrit_mauvaise_langue`, qui ne juge que les mots NOUVEAUX par
rapport à une source) : avec un score IT dominé par « alla », la marge peut rester trop
faible pour trancher — c'est exactement le cas qui doit passer SANS appel LLM inutile.

Aucun réseau, fonction pure (`titre_corps_langue_desaccord` ne fait aucun appel API —
c'est `_process_one_event`, non testé ici, qui appelle `translate_title_desc` une fois
le désaccord détecté).

Lancer : .venv/bin/python -m tests.test_enrich_titre_langue
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.enrich import titre_corps_langue_desaccord  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"  OK  {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label}" + (f" — {detail}" if detail else ""))


# ── 1. Cas réel WP#7472 : titre IT sous un corps FR → DOIT être détecté ─────────
art_regine = {
    "titre": "Regine in Scena. L'arte del costume italiano tra cinema e teatro",
    "chapo": "Les costumes proviennent d'ateliers de couture italiens qui ont habillé "
             "des actrices dans des films et des pièces de théâtre devenus des classiques.",
    "corps": "Cette exposition présente les plus belles créations de la mode italienne "
             "au cinéma et au théâtre, avec des pièces rares venues de plusieurs musées.",
}
res = titre_corps_langue_desaccord(art_regine)
_check("Regine in Scena : désaccord détecté (titre IT, corps FR)",
      res is not None and res[0] == "it" and res[1] == "fr", res)

# ── 2. Cas Ankama : nom propre français dans un corps italien → NE DOIT PAS déclencher
#      de retraduction (règle 3 : le cas qui doit PASSER, choisi près de la frontière).
art_ankama = {
    "titre": "Ankama alla Cité Internationale du Cinéma d'Animation",
    "chapo": "Mostra dedicata all'universo di Ankama, con opere originali e proiezioni "
             "esclusive per il pubblico piemontese.",
    "corps": "Gli artisti presentano schizzi e animazioni inedite durante questo evento "
             "gratuito, aperto a tutti fino a domenica sera.",
}
res = titre_corps_langue_desaccord(art_ankama)
_check("Ankama : pas de désaccord signalé (nom propre légitime en français)",
      res is None, res)

# ── 3. Fiche cohérente FR/FR → pas de désaccord ─────────────────────────────────
art_coherent = {
    "titre": "Concert de musique classique au château",
    "chapo": "Un concert exceptionnel se tient dans la grande salle du château.",
    "corps": "Le programme réunit plusieurs musiciens régionaux pour cette soirée "
             "exceptionnelle, avec un répertoire varié allant du baroque au romantique.",
}
_check("fiche FR/FR cohérente : pas de désaccord", titre_corps_langue_desaccord(art_coherent) is None)

# ── 4. Titre nom propre seul (ex. artiste) + corps court : trop ambigu pour trancher,
#      ne doit PAS être compté comme un écart — ni comme une preuve d'absence.
art_ambigu = {"titre": "Katy Perry", "chapo": "Concert.", "corps": "Show."}
_check("titre/corps trop courts : aucune conclusion (ni écart, ni accord)",
      titre_corps_langue_desaccord(art_ambigu) is None)

# ── 5. Titre absent : rien à comparer ────────────────────────────────────────────
_check("pas de titre : aucune conclusion", titre_corps_langue_desaccord({}) is None)

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
