#!/usr/bin/env python3
"""Fixture : le calendrier des catégories (`utils/calendrier.py` +
`config/calendrier_categories.json`).

⚠️ AUCUNE base, aucun réseau — les comptes de fiches sont passés à la main.

D'OÙ ÇA VIENT. Franck, 05/09/2026 : « le cinéma en plein air c'est terminé maintenant
[…] les festivals sont terminés aussi […] Il faut un calendrier où à partir de telle
date on valorise telle catégorie, puis telle autre, d'autres s'enlèvent à partir d'une
date. » Et : « le comptage n'est pas forcément le point, mais la saisonnalité ».

CE QUE CETTE FIXTURE VÉRIFIE :
  1. le fichier est cohérent avec le reste du dépôt : exactement les onze catégories
     de `scripts/evaluator.CATEGORIES`, sous le même nom, avec des slugs uniques ;
  2. le 05/09/2026 (le jour de la demande) : Cinéma et Festivals sont RETIRÉS, ils ne
     sont dans aucune tuile même avec des fiches devant eux ;
  3. ⚠️ LE CAS QUI DOIT PASSER, choisi près de la frontière : le 31 août, Cinéma est
     encore de saison (fort) et OBTIENT une tuile ; le 1er septembre, plus. Sans ce cas,
     la fixture ne prouverait que ce qu'on voulait entendre ;
  4. la saison ordonne, le compte ne fait que retirer : en décembre, Sport (fort) avec
     2 fiches passe DEVANT Conférences (hors fenêtre) avec 50 fiches — c'est l'inverse
     de ce que j'avais proposé (trancher au nombre), et que Franck a refusé ;
  5. le filet : une catégorie de saison mais SANS fiche devant elle est écartée, avec
     un motif qui le dit ;
  6. les fenêtres qui chevauchent le Nouvel An marchent (Marchés, 15/11 → 06/01 : le
     2 janvier est dedans, le 7 non) et les bornes sont incluses ;
  7. `prochains_changements` depuis le 05/09 annonce bien l'entrée de Jeune public le
     17/10 (Toussaint) — le « à partir de telle date » est calculé, pas écrit à la main.

Lancer : .venv/bin/python -m tests.test_calendrier_categories
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import calendrier as cal            # noqa: E402
from scripts.evaluator import CATEGORIES       # noqa: E402

CFG = cal.charger()
NOMS = [c["nom"] for c in CFG["categories"]]
# Un compte « confortable » pour toutes : ainsi seul le CALENDRIER décide.
PLEIN = {n: 10 for n in NOMS}


def _noms(sel):
    return [e["nom"] for e in sel["retenues"]]


def test_onze_categories_et_slugs():
    assert sorted(NOMS) == sorted(CATEGORIES), (sorted(NOMS), sorted(CATEGORIES))
    slugs = [c["slug_fr"] for c in CFG["categories"]] + [c["slug_it"] for c in CFG["categories"]]
    assert len(slugs) == len(set(slugs)), "slug en double"


def test_05_septembre_cinema_et_festivals_retires():
    j = date(2026, 9, 5)
    etats = {e["nom"]: e for e in cal.saisons(j, CFG)}
    assert etats["Cinéma"]["niveau"] == "exclu", etats["Cinéma"]
    assert etats["Festivals"]["niveau"] == "exclu", etats["Festivals"]
    assert etats["Spectacle vivant"]["niveau"] == "fort"
    sel = cal.tuiles(j, PLEIN, CFG)
    assert "Cinéma" not in _noms(sel) and "Festivals" not in _noms(sel), _noms(sel)
    assert len(sel["retenues"]) == CFG["n_tuiles"], _noms(sel)
    motifs = {e["nom"]: e["motif"] for e in sel["ecartees"]}
    assert "hors saison" in motifs["Cinéma"], motifs


def test_frontiere_cinema_31_aout_oui_1er_septembre_non():
    """Le cas qui DOIT passer : la veille de la bascule, la tuile est encore là."""
    assert "Cinéma" in _noms(cal.tuiles(date(2026, 8, 31), PLEIN, CFG))
    assert "Cinéma" not in _noms(cal.tuiles(date(2026, 9, 1), PLEIN, CFG))


def test_la_saison_ordonne_le_compte_ne_fait_que_retirer():
    j = date(2026, 12, 10)
    comptes = dict(PLEIN, **{"Sport": 2, "Conférences & Rencontres": 50})
    etats = {e["nom"]: e["niveau"] for e in cal.saisons(j, CFG)}
    assert etats["Sport"] == "fort" and etats["Conférences & Rencontres"] == "base", etats
    ordre = _noms(cal.tuiles(j, comptes, CFG, n=11, seuil=1))
    assert ordre.index("Sport") < ordre.index("Conférences & Rencontres"), ordre


def test_filet_page_vide():
    j = date(2026, 12, 10)
    comptes = dict(PLEIN, **{"Sport": 0})
    sel = cal.tuiles(j, comptes, CFG)
    assert "Sport" not in _noms(sel)
    motif = next(e["motif"] for e in sel["ecartees"] if e["nom"] == "Sport")
    assert "0 fiche" in motif and "seuil" in motif, motif


def test_fenetre_a_cheval_sur_nouvel_an_et_bornes_incluses():
    assert cal.dans_fenetre(date(2027, 1, 2), "11-15", "01-06")
    assert cal.dans_fenetre(date(2026, 11, 15), "11-15", "01-06")     # borne basse incluse
    assert cal.dans_fenetre(date(2027, 1, 6), "11-15", "01-06")       # borne haute incluse
    assert not cal.dans_fenetre(date(2027, 1, 7), "11-15", "01-06")
    assert not cal.dans_fenetre(date(2026, 11, 14), "11-15", "01-06")
    marches = next(e for e in cal.saisons(date(2027, 1, 2), CFG) if e["nom"] == "Marchés & Foires")
    assert marches["niveau"] == "fort", marches


def test_prochains_changements_calcules():
    ch = cal.prochains_changements(date(2026, 9, 5), CFG, horizon=60)
    jp = [c for c in ch if c["nom"] == "Jeune public & Famille" and c["apres"] == "fort"]
    assert jp and jp[0]["date"] == date(2026, 10, 17), jp
    assert all(c["date"] > date(2026, 9, 5) for c in ch)


def test_grille_couvre_toute_l_annee():
    for ligne in cal.grille_annee(2026, CFG):
        total = sum(s["largeur"] for s in ligne["segments"])
        assert abs(total - 1.0) < 1e-9, (ligne["nom"], total)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    ko = 0
    for t in tests:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as exc:
            ko += 1
            print(f"  KO   {t.__name__} : {exc}")
    print(f"{len(tests) - ko}/{len(tests)} au vert")
    sys.exit(1 if ko else 0)
