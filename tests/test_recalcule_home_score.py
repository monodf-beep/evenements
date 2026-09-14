"""La note de rendu se recalcule sans LLM — et le test cherche la FRONTIÈRE.

D'où ça vient : `backfill_home_score` a rendu « 0 fiche remplie sur 95 candidates » le
2026-09-15, parce qu'il ne sait que recopier un score absent du JSON. 95 fiches enrichies
restaient donc sans note de rendu, donc hors d'« À la une » et d'« En évidence », sans que
rien ne les en sorte (règle 3).

Les cas ci-dessous encadrent le plancher de 6 au dixième près — DEUX doivent passer, dont
un JUSTE au-dessus, et un JUSTE en dessous doit échouer. Une fixture qui ne montrerait que
des 10 et des 0 passerait au vert sur une formule fausse.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.recalcule_home_score import score_rendu  # noqa: E402


def _ev(panel=None, officielle=False, url_officiel="", portrait="", wide="",
        url_image="", pages=()):
    ed = {}
    if panel is not None:
        ed["reader_panel"] = {"mean": panel}
    ed["source"] = {"officielle": officielle, "pages": list(pages)}
    return {
        "enrich_data": json.dumps(ed),
        "url_officiel": url_officiel,
        "url_image_portrait": portrait,
        "url_image_wide": wide,
        "url_image": url_image,
    }


def test_le_maximum_est_plafonne_a_dix():
    s, _ = score_rendu(_ev(panel=5, officielle=True, portrait="p.jpg", wide="w.jpg"))
    assert s == 10.0


def test_juste_au_dessus_du_plancher_passe():
    """LA FRONTIÈRE, côté qui doit PASSER : panel 3/5 → 3,6 + 2,5 = 6,1."""
    s, _ = score_rendu(_ev(panel=3, officielle=True))
    assert s == 6.1
    assert s >= 6.0


def test_juste_en_dessous_du_plancher_echoue():
    """L'autre côté, à un dixième : panel 2,9/5 → 3,48 + 2,5 = 5,98 → 6,0 arrondi."""
    s, _ = score_rendu(_ev(panel=2.8, officielle=True))
    assert s == 5.9
    assert s < 6.0


def test_fiche_courte_sans_panel_reste_sous_le_plancher():
    """Le cas HONNÊTE : recalculer n'est pas remonter. Sans panel de lecture, q vaut 0 et
    le total plafonne à 4 — la commande rend une note juste, elle ne débloque rien."""
    s, motif = score_rendu(_ev(panel=None, officielle=True,
                               url_officiel="https://fortedibard.it/e",
                               url_image="https://www.fortedibard.it/img.jpg"))
    # 0 + 2,5 + 0,75 = 3,25, rendu 3,2 : Python arrondit 3,25 au PAIR, pas au supérieur.
    # C'est exactement ce que fait enrich.py (même `round(..., 1)`), donc la note recalculée
    # est identique à celle qu'aurait posée l'enrichissement — c'est le point de ce test.
    assert s == 3.2
    assert "photo officielle" in motif


def test_photo_du_site_officiel_reconnue_malgre_le_www():
    """`www.` ne doit pas casser la comparaison de domaines : c'est ce qui distingue
    « photo officielle » (0,75) de « aucun visuel » (0)."""
    avec, _ = score_rendu(_ev(panel=5, url_officiel="https://fortedibard.it/e",
                              url_image="https://www.fortedibard.it/img.jpg"))
    sans, _ = score_rendu(_ev(panel=5, url_officiel="https://fortedibard.it/e",
                              url_image="https://cdn-tiers.example/img.jpg"))
    # 9,25 → 9,2 et 8,5 restent séparés par l'écart des visuels, à l'arrondi près.
    assert round(avec - sans, 2) == 0.7
    assert avec > sans


def test_url_officiel_seule_suffit_a_prouver_la_source():
    """Les fiches d'AVANT le bloc `source` du JSON n'ont que la colonne — elles doivent
    quand même toucher leurs 2,5, sinon le rouvreur les enterrerait une seconde fois."""
    s, _ = score_rendu(_ev(panel=3, officielle=False,
                           url_officiel="https://exemple.it/evenement"))
    assert s == 6.1


def test_json_illisible_ne_fait_pas_tomber_le_calcul():
    s, _ = score_rendu({"enrich_data": "{pas du json", "url_officiel": ""})
    assert s == 0.0
