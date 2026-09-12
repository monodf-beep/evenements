#!/usr/bin/env python3
"""Fixture : le gradient d'imminence au-delà de 45 jours (`_bonus_lointain`).

⚠️ AUCUNE base, aucun réseau — teste directement `utils/deplacement.py`.

D'OÙ ÇA VIENT. `scripts/audit_deplacement.py` a mesuré le 05/09 (Franck, précisant le
18/08 : « il faut qu'il y ait de la nouveauté chaque semaine ») que Piémont et Vallée
d'Aoste montrent la MÊME tête 12 et 21 SEMAINES d'affilée sur 26 : au-delà du dernier
palier de `_FENETRES` (45 jours), le bonus d'imminence valait 0 pour tout le monde, et
le score intrinsèque — figé par construction — tranchait seul, pour des mois.

CE QUE CETTE FIXTURE VÉRIFIE :
  1. continuité avec `_FENETRES` : à 45 jours pile, le gradient vaut 0 (le palier des
     45 jours donne déjà 1 point, pas de double-comptage) ;
  2. il redescend à 0 à l'horizon (183 jours) et au-delà — jamais négatif ;
  3. ⚠️ LE CAS QUI DOIT PASSER : deux fiches à score intrinsèque ÉGAL, l'une à 160
     jours, l'autre à 100 jours (donc TOUTES LES DEUX hors de la portée de l'ancien
     mécanisme, qui rendait 0 pour les deux et les laissait dans l'ordre du score
     intrinsèque, donc à égalité stricte). AVEC le gradient, la plus proche doit
     l'emporter clairement — sans lui, ce test serait une confirmation, pas une preuve ;
  4. et le cas de non-régression : à moins de 45 jours, le résultat est STRICTEMENT le
     même qu'avant (le gradient vaut 0 dans la zone déjà couverte par `_FENETRES`) —
     sans lui, on ne saurait pas si le correctif a discrètement changé un comportement
     déjà validé par Franck.
  5. l'arrondi se fait par ROUND, jamais par troncature — le mu-plugin WordPress qui
     lit `as_deplacement_now` caste en `(int)` et tronquerait une décimale au lieu de
     l'arrondir ; c'est pour ça que `deplacement_now` doit renvoyer un entier déjà
     arrondi, jamais un flottant.

Lancer : .venv/bin/python -m tests.test_gradient_deplacement
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.deplacement import (      # noqa: E402
    _bonus_lointain, deplacement_now, HORIZON_JOURS, _FENETRES,
)

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


def _det(rayon, spec, edition, notoriete, orga=0):
    return json.dumps({"rayonnement": {"points": rayon},
                       "specificite_territoriale": {"points": spec},
                       "edition_tradition": {"points": edition},
                       "notoriete_lieu": {"points": notoriete},
                       "organisateur_moyens": {"points": orga}})


def _fiche(jours, detail, categorie="Gastronomie & Sagre"):
    """Un événement PONCTUEL (une seule date) dans `jours` jours, avec ce détail de
    score. Ponctuel exprès : isole le gradient, sans le point de rareté qui s'ajoute
    de toute façon aux deux côtés d'une comparaison symétrique."""
    from datetime import date, timedelta
    d = (date.today() + timedelta(days=jours)).isoformat()
    return {"date_event_start": d, "date_event_end": None,
           "llm_categorie": categorie, "llm_score_detail": detail}


SEUIL = max(seuil for seuil, _pts in _FENETRES)  # 45


print("──── continuité avec _FENETRES, aux bornes ────")
_check("à 45 jours pile (le palier existant), le gradient est nul — pas de double-compte",
       _bonus_lointain(SEUIL) == 0.0, _bonus_lointain(SEUIL))
_check("à 46 jours, il vient tout juste de démarrer (proche de 1, pas encore 0)",
       0.9 < _bonus_lointain(SEUIL + 1) < 1.0, _bonus_lointain(SEUIL + 1))
_check("pile à l'horizon (183 jours), il est retombé à 0",
       _bonus_lointain(HORIZON_JOURS) == 0.0, _bonus_lointain(HORIZON_JOURS))
_check("au-delà de l'horizon, toujours 0 — jamais négatif",
       _bonus_lointain(HORIZON_JOURS + 30) == 0.0, _bonus_lointain(HORIZON_JOURS + 30))
_check("à mi-chemin (~114 jours), autour de 0.5 — la bascule de l'arrondi",
       0.45 < _bonus_lointain(114) < 0.55, _bonus_lointain(114))

print("\n──── ⚠️ LE CAS QUI DOIT PASSER : deux fiches à score ÉGAL, loin toutes les deux ────")
# Score intrinsèque identique (rayon=2,spec=1,edition=2,notoriete=1 → même total pour les
# deux) : AVANT le gradient, deplacement_now rendait 0 de bonus pour les DEUX (160 et 100
# jours sont hors de portée de l'ancien mécanisme, qui s'arrêtait à 45) — égalité stricte,
# rien pour départager. Le gradient doit les départager, la plus proche gagnant.
detail_egal = _det(2, 1, 2, 1)
loin = _fiche(160, detail_egal)
proche = _fiche(100, detail_egal)
score_loin = deplacement_now(loin)
score_proche = deplacement_now(proche)
_check("la fiche à 100 jours l'emporte sur celle à 160 jours, à score intrinsèque égal",
       score_proche > score_loin, (score_proche, score_loin))
_check("   l'écart vient bien du gradient (+1), pas d'autre chose",
       score_proche - score_loin == 1, (score_proche, score_loin))

print("\n──── ⚠️ NON-RÉGRESSION : sous 45 jours, comportement STRICTEMENT inchangé ────")
detail_seul = _det(2, 1, 2, 0)
proche_7 = _fiche(5, detail_seul)     # dans la fenêtre des 7 jours (+3, +1 rareté ponctuel)
proche_20 = _fiche(20, detail_seul)   # fenêtre des 21 jours (+2, +1 rareté)
proche_40 = _fiche(40, detail_seul)   # fenêtre des 45 jours (+1, +1 rareté)
base = 2 * 2 + 1 * 3 + 2 * 1 + 0 * 1 + 2  # (rayon,spec,edition,notoriete pondérés) + langue
_check("fenêtre 7 jours : base + 3 (fenêtre) + 1 (rareté), rien du gradient",
       deplacement_now(proche_7) == base + 3 + 1, deplacement_now(proche_7))
_check("fenêtre 21 jours : base + 2 + 1", deplacement_now(proche_20) == base + 2 + 1,
       deplacement_now(proche_20))
_check("fenêtre 45 jours : base + 1 + 1", deplacement_now(proche_40) == base + 1 + 1,
       deplacement_now(proche_40))
for j in (5, 20, 40):
    _check(f"   _bonus_lointain reste nul dans la zone _FENETRES (j={j})",
           _bonus_lointain(j) == 0.0, _bonus_lointain(j))

print("\n──── l'arrondi ne renvoie jamais un flottant (piège du cast PHP) ────")
_check("deplacement_now(loin) est un int", isinstance(score_loin, int), type(score_loin))
_check("deplacement_now(proche) est un int", isinstance(score_proche, int), type(score_proche))

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
