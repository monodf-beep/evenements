"""Un paragraphe resté dans l'autre langue doit être vu — mais pas une citation.

D'où ça vient : Franck, 2026-09-15, devant WP#8324 en ligne — « problème de traduction
(comment c'est encore possible !?!?) ». Fiche italienne (URL /it/, territoire
« Piemonte »), titre et premier paragraphe en italien, TROIS paragraphes du corps en
français. Mesuré sur tout le site : dix fiches publiées dans ce cas.

Les cas ci-dessous viennent des DONNÉES RÉELLES, pas d'exemples inventés, et ils
encadrent la marge au point près :

  • le plus FAIBLE des vrais défauts mesurés est à 5 (WP#7476, WP#8184) → doit être vu ;
  • le faux positif mesuré est à 4 (WP#3721, une phrase française qui énumère des titres
    de chansons italiennes) → **doit PASSER**. C'est le cas près de la frontière qu'exige
    la règle 3 du dépôt : une fixture qui ne contiendrait que des cas flagrants passerait
    au vert sur un portillon trop large.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.lang import paragraphes_mauvaise_langue, MARGE_PARAGRAPHE  # noqa: E402

# WP#3721, fiche FRANÇAISE. Écart mesuré : 4. Doit passer.
CITATION_DE_TITRES = (
    "Parmi les chansons attendues figurent Self Control, Infinito, Sei La Più Bella Del "
    "Mondo, Il Battito Animale et Ti Pretendo, que le public reprend depuis quarante ans."
)
# WP#8324, fiche ITALIENNE. Écart mesuré : 23. Doit être vu.
VRAI_FRANCAIS = (
    "Marisa Merz, née à Turin en 1926 et morte en 2019, est l'une des figures majeures de "
    "l'Arte Povera, mouvement apparu dans la ville dans les années 1960. Elle s'en "
    "distingue par des sculptures suspendues en cuivre ou en aluminium tissé, de l'argile "
    "crue façonnée en petits visages, de la cire et du papier."
)
# WP#8324, premier paragraphe. Italien véritable dans une fiche italienne : rien à dire.
VRAI_ITALIEN = (
    "Dal 29 ottobre 2026 al 4 aprile 2027, la Fondazione Merz di Torino presenta la "
    "propria tappa de La danza delle ore, mostra in tre atti dedicata a Marisa Merz, "
    "coprodotta con il Castello di Rivoli e la Galleria Civica d'Arte Moderna di Torino."
)


def test_le_vrai_paragraphe_francais_dans_une_fiche_italienne_est_vu():
    trouves = paragraphes_mauvaise_langue(VRAI_FRANCAIS, "it")
    assert len(trouves) == 1
    assert trouves[0][0] >= MARGE_PARAGRAPHE


def test_la_citation_de_titres_italiens_dans_une_phrase_francaise_PASSE():
    """LA FRONTIÈRE, côté qui doit passer. Mesuré à 4, sous la marge de 5."""
    assert paragraphes_mauvaise_langue(CITATION_DE_TITRES, "fr") == []


def test_un_paragraphe_italien_dans_une_fiche_italienne_ne_dit_rien():
    assert paragraphes_mauvaise_langue(VRAI_ITALIEN, "it") == []


def test_le_meme_texte_juge_dans_l_autre_sens():
    """Contre-épreuve : le paragraphe italien DOIT ressortir si la fiche est française.
    Sans ce sens-là, un portillon qui rendrait toujours [] passerait les trois premiers."""
    trouves = paragraphes_mauvaise_langue(VRAI_ITALIEN, "fr")
    assert len(trouves) == 1


def test_plusieurs_paragraphes_rendus_du_plus_flagrant_au_moins():
    texte = VRAI_ITALIEN + "\n\n" + VRAI_FRANCAIS + "\n\n" + VRAI_FRANCAIS[:200]
    trouves = paragraphes_mauvaise_langue(texte, "it")
    assert len(trouves) == 2
    assert trouves[0][0] >= trouves[1][0]


def test_un_fragment_court_est_ignore():
    """« 20h30 : introduction par Pierre-Olivier François » — une ligne de programme n'a
    presque pas de mots grammaticaux, donc le comptage n'y veut rien dire."""
    assert paragraphes_mauvaise_langue("20h30 : introduction par le réalisateur", "it") == []


def test_langue_inconnue_ne_leve_pas():
    assert paragraphes_mauvaise_langue(VRAI_FRANCAIS, "es") == []
    assert paragraphes_mauvaise_langue("", "it") == []
