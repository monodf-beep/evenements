#!/usr/bin/env python3
"""Fixture : une page d'accueil ou une rubrique n'illustre pas un événement.

MESURÉ le 2026-09-21 sur les 22 pages RACINE qui servent de source à des fiches publiées
encore devant nous. Neuf portaient un og:image ; **aucune ne montrait l'événement** :

    museorisorgimentotorino.it/   → backend-login-bg-01.jpg      (fond de la page admin)
    mal-thonon.org/               → saison-25-26.jpg             (affiche périmée d'un an)
    conservatoriotorino.eu/       → logo-conservatorio-bianco.jpg
    bonlieu-annecy.com/           → img_facebook (1).png
    opera-nice.org/               → share-opera-nice-cote-dazur.jpg
    palazzomadamatorino.it/       → Facciata-2011-photo-Gonella-1.jpg  (le bâtiment)

En août, la même balise du musée du Risorgimento portait l'affiche d'une exposition de
MARS — c'est le fond du problème : une page d'accueil illustre la programmation du
moment, donc au mieux un AUTRE événement. C'est cette affiche-là (« Trame di donne »,
6-7-8 mars 2026) qui illustrait encore, ce jour-là, la fiche « Une chasse aux énigmes en
famille au musée du Risorgimento » (WP#9615).

Et aucun de ces 22 sites n'était lui-même l'événement — l'exception ne coûtait donc rien
ce jour-là. Elle protège les domaines qui PORTENT le nom de l'événement (doujador.it,
beercult.it) : c'est le cas qui doit PASSER près de la frontière. Elle est volontairement
étroite, et sa limite est vérifiée plus bas : un titre RÉDIGÉ ne tient pas dans un
domaine, donc il n'en bénéficie pas.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_pages_generiques
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.pages import (est_racine, est_page_generique,  # noqa: E402
                         site_est_evenement, peut_illustrer, ancre_dans_une_liste)

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── racines (cas réels du jour) ────")
for u in ("https://www.museorisorgimentotorino.it/", "https://ogrtorino.it/",
          "https://mal-thonon.org/", "https://camera.to"):
    _check(f"racine : {u}", est_racine(u) and est_page_generique(u))

print("\n──── rubriques (cas réels du jour) ────")
for u, quoi in (("https://www.malrauxchambery.fr/ressources/presse", "ressources presse"),
                ("https://www.torinofilmfest.org/it/cartellastampa-comunicatistampa/",
                 "comunicati stampa"),
                # Source de QUATRE fiches publiées à venir : la page « séances scolaires »
                # de la MAL de Thonon, pas celle du spectacle.
                ("https://mal-thonon.org/scolaires", "séances scolaires")):
    _check(f"{quoi} → générique", est_page_generique(u) and not est_racine(u))

print("\n──── les pages d'ÉVÉNEMENT, qui doivent passer ────")
for u in ("https://www.malrauxchambery.fr/evenement/charcot-antartica-26-27/",
          "https://www.palazzomadamatorino.it/it/evento/corso-di-storia-dellarte-dentro-la-pittura/",
          "https://camera.to/mostre/bruno-boudjelal-foto-album-da-aurora-e-barriera/",
          "https://chatha.org/index.php/repertoire/bal-clandestin"):
    _check(f"page d'événement : …{u[-42:]}", not est_page_generique(u))

print("\n──── le site EST l'événement : sa page d'accueil illustre bien ────")
_check("doujador.it ↔ « Douja d'Or »", site_est_evenement("https://www.doujador.it/", "Douja d'Or"))
_check("beercult.it ↔ « BeerCult 2026 » (le millésime ne compte pas)",
       site_est_evenement("https://beercult.it/", "BeerCult 2026"))
_check("… donc sa racine PEUT illustrer",
       peut_illustrer("https://beercult.it/", "BeerCult 2026"))
# LA LIMITE, écrite noir sur blanc plutôt que découverte dans six mois : un titre RÉDIGÉ
# ne tient pas dans un domaine, donc l'exception ne joue pas et l'image de la page
# d'accueil est refusée. C'est assumé (voir utils/pages.site_est_evenement) : le chemin
# propre est de préciser la source, pas d'assouplir le test.
_check("un titre rédigé ne déclenche PAS l'exception, même sur le bon site",
       not site_est_evenement("https://beercult.it/",
                              "BeerCult 2026 à Aoste : trois jours entre bière alpine"))
# Et le piège que tout critère plus large rouvrirait : le domaine porte le nom du LIEU.
_check("« Risorgimento » dans le domaine ne fait pas du musée un événement",
       not site_est_evenement("https://www.museorisorgimentotorino.it/",
                              "Une chasse aux énigmes au musée du Risorgimento"))
_check("« Thonon » non plus (mal-thonon.org, og:image = affiche de saison 25-26)",
       not site_est_evenement("https://mal-thonon.org/",
                              "James Carter en concert au Théâtre Novarina de Thonon"))
_check("un musée n'est pas son exposition : la racine ne peut pas illustrer",
       not peut_illustrer("https://www.museorisorgimentotorino.it/",
                          "Une chasse aux énigmes en famille au musée du Risorgimento"))
_check("la rubrique presse de Malraux ne peut pas illustrer Charcot",
       not peut_illustrer("https://www.malrauxchambery.fr/ressources/presse",
                          "Charcot Antartica, un concert-récit sur l'Antarctique"))
_check("la page du spectacle, elle, peut",
       peut_illustrer("https://www.malrauxchambery.fr/evenement/charcot-antartica-26-27/",
                      "Charcot Antartica, un concert-récit sur l'Antarctique"))

print("\n──── frontières ────")
_check("un titre sans mot significatif ne fait pas du site un événement",
       not site_est_evenement("https://x.fr/", "Concert"))
_check("un seul mot du titre dans le domaine ne suffit pas (il les faut TOUS)",
       not site_est_evenement("https://stresafestival.eu/", "Stresa Festival rencontre Verdi"))
_check("un titre fait QUE de millésimes ne vaut pas exception",
       not site_est_evenement("https://beercult.it/", "2026"))
_check("non-URL → jamais générique, et illustrable (l'appelant décide)",
       not est_page_generique("gmail:abc") and peut_illustrer("gmail:abc", "Peu importe"))
_check("chaîne vide → pas de faux positif", not est_page_generique("") and not est_racine(""))

print("\n──── une ancre dans une page-programme (23/09, Plaisirs de Culture) ────")
PDC = "https://valledaostaheritage.com/events/plaisirs-de-culture-2026/"
for ancre, titre in (
    ("oltre-l-affresco-le-sorprese-nel-restauro-del-castello-di-issogne",
     "Oltre l'affresco : les coulisses du restauro du château d'Issogne"),
    ("aosta-si-rigenera-tra-restauro-storico-e-futuro-urbano",   # titre FR, ancre IT
     "Aoste se régénère entre restauration historique et avenir urbain"),
):
    _check(f"#{ancre[:30]}… : n'illustre pas", ancre_dans_une_liste(PDC + "#" + ancre)
           and not peut_illustrer(PDC + "#" + ancre, titre))
_check("FRONTIÈRE : la même page SANS ancre reste illustrable (elle n'est pas générique)",
       peut_illustrer(PDC, "Plaisirs de Culture en Vallée d'Aoste"))
_check("FRONTIÈRE : une ancre de section (#billetterie) ne retire rien",
       not ancre_dans_une_liste("https://theatre.fr/spectacle-x/#billetterie")
       and peut_illustrer("https://theatre.fr/spectacle-x/#billetterie", "Spectacle X"))
_check("FRONTIÈRE : une ancre de trois mots (#informations-pratiques-acces) non plus",
       not ancre_dans_une_liste("https://theatre.fr/spectacle-x/#informations-pratiques-acces"))
_check("FRONTIÈRE : un « # » vide ne compte pas", not ancre_dans_une_liste("https://x.fr/page#"))
_check("une ancre ne rachète pas une page qui porte le nom de l'événement",
       not peut_illustrer("https://doujador.it/#programma-della-douja-d-or-2026", "Douja d'Or"))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
