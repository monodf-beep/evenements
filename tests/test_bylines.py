#!/usr/bin/env python3
"""Fixture : la signature d'un article n'est pas l'organisateur — sans casser les vrais.

Les cinq cas d'entrée viennent de la file « À vérifier » du 2026-08-11, vérifiés un par
un contre les sources officielles (voir docs/VERIFICATION_2026-08-11.md). Ce sont donc
des cas RÉELS, pas des cas construits pour donner raison au portillon.

CE QUE LA FIXTURE PROTÈGE EN PREMIER — et c'est le point de la règle 3 de CLAUDE.md, qui
demande un cas qui doit PASSER, choisi près de la frontière : « Denis Falconieri » et
« Arabella Pezza » ont exactement la même forme. Deux prénoms, deux noms, aucune
majuscule qui les distingue. Ce qui les sépare n'est PAS le nom, c'est ce que la matière
en dit : l'un est annoncé comme organisateur, l'autre signe l'article. Un portillon qui
viderait les deux serait « efficace » sur les cinq incidents et détruirait au passage
tous les petits organisateurs qui s'appellent comme des gens.

Lancer : .venv/bin/python -m tests.test_bylines
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.bylines import (  # noqa: E402
    corrobore, est_nom_de_personne, est_signature_de_flux, organisateur_depuis_flux,
    porte_un_mot_d_organisme, verdict,
)

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── les cinq incidents du 2026-08-11 : à vider ────")
# Matière volontairement proche de celle des vraies fiches : le nom y figure, mais dans
# son rôle de signataire ou de témoin — jamais comme organisateur.
INCIDENTS = [
    ("Arabella Pezza",
     "La Foire de Saint-Ours réunit l'artisanat valdôtain dans le centre historique "
     "d'Aoste. Un article d'Arabella Pezza pour notre rubrique culture."),
    ("Stefania Marchiano",
     "Percorso in Rosso revient à Saint-Rhémy-en-Bosses. Propos recueillis par "
     "Stefania Marchiano."),
    ("Amelio Ambrosi",
     "Marché au Fort : les producteurs s'installent au Forte di Bard. "
     "Contact : Amelio Ambrosi, 0165 000000."),
    ("Denis Falconieri",
     "Fénis : un rendez-vous d'été à Tsantì de Bouva. Denis Falconieri a assisté à "
     "la première édition."),
    ("Emilie DUPONT",
     "La Farandole 2026 : cinq continents en danse dans la Métropole de Nice."),
]
for nom, matiere in INCIDENTS:
    v, raison = verdict(nom, matiere)
    _check(f"« {nom} » → vider", v == "vider", f"({v} : {raison})")

print("\n──── LE CAS QUI DOIT PASSER — même forme, autre rôle ────")
CORROBORES = [
    ("Denis Falconieri",
     "La fête de Tsantì de Bouva est organisée par Denis Falconieri, président de "
     "l'association des habitants."),
    ("Laurent Pitteloud",
     "Il Collontrek è organizzato da Laurent Pitteloud per il versante svizzero."),
    ("Maurizio Lanivi",
     "Una manifestazione a cura di Maurizio Lanivi e di un gruppo di appassionati."),
    ("Lou Cat",
     "La Farandole, portée par Lou Cat, collectif des arts traditionnels."),
]
for nom, matiere in CORROBORES:
    v, raison = verdict(nom, matiere)
    _check(f"« {nom} » annoncé organisateur → garder", v == "garder", f"({v} : {raison})")

_check("le sens de lecture compte : « organisé par X » corrobore",
       corrobore("Denis Falconieri", "Fête organisée par Denis Falconieri"))
_check("… mais « X a assisté » ne corrobore pas",
       not corrobore("Denis Falconieri", "Denis Falconieri a assisté à la fête"))
_check("… et un « organisé par » qui parle de QUELQU'UN D'AUTRE ne corrobore pas",
       not corrobore("Denis Falconieri",
                     "Fête organisée par la Pro Loco. Denis Falconieri était présent."))

print("\n──── les vrais organisateurs, jamais touchés ────")
VRAIS = [
    "Ville de Nice", "Comune di Bard", "Région autonome Vallée d'Aoste",
    "Pro Loco di Saint-Rhémy-en-Bosses", "Forte di Bard", "Musei Reali di Torino",
    "Théâtre National de Nice", "Chambre valdôtaine", "Collectif des Arts Traditionnels",
    "Conservatorio di Torino", "Association des Amis du Fort", "Fondazione Torino Musei",
    "Orchestre de la Suisse Romande", "Festival Guitare en Scène",
    # LE FAUX POSITIF DU 2026-08-11, gardé ici pour de bon : la purge a vidé « Interreg
    # ALCOTRA » sur trois fiches. Deux mots capitalisés, aucun mot d'organisme — la forme
    # exacte d'un prénom et d'un nom. C'est le programme de coopération France-Italie, et
    # il organise vraiment ses webinaires. Aucune règle de FORME ne distinguera jamais
    # « Interreg ALCOTRA » de « Arabella Pezza » : seul le vocabulaire peut le faire, donc
    # cette liste s'allongera encore, et c'est --restaurer qui répare l'existant.
    "Interreg ALCOTRA", "Programme ALCOTRA", "ATL Terre dell'Alto Piemonte",
]
for nom in VRAIS:
    v, raison = verdict(nom, "")
    _check(f"« {nom} » → garder", v == "garder", f"({v} : {raison})")

print("\n──── signatures de CMS ────")
for nom in ("Redazione", "La Redazione", "admin", "Webmaster", "Ufficio stampa", "-"):
    _check(f"« {nom} » reconnu comme signature de flux", est_signature_de_flux(nom))
    _check(f"« {nom} » → vider", verdict(nom, "")[0] == "vider")

print("\n──── bornes de la reconnaissance de nom ────")
_check("un mot seul n'est pas un nom de personne", not est_nom_de_personne("Pezza"))
_check("quatre mots non plus", not est_nom_de_personne("Jean Pierre Marie Dupont"))
_check("les particules ne comptent pas comme mots",
       est_nom_de_personne("Jean de La Fontaine"), "3 mots significatifs attendus")
_check("minuscules → pas un nom propre", not est_nom_de_personne("comité des fêtes"))
_check("un chiffre → jamais un nom", not est_nom_de_personne("Salle 2 Nice"))
_check("une URL → jamais un nom", not est_nom_de_personne("https://exemple.fr"))
_check("« Ville de Nice » porte un mot d'organisme", porte_un_mot_d_organisme("Ville de Nice"))
_check("« Arabella Pezza » n'en porte aucun",
       not porte_un_mot_d_organisme("Arabella Pezza"))

print("\n──── ce qu'on écrit au moment de la collecte ────")
_check("un auteur RSS journaliste n'entre pas en base",
       organisateur_depuis_flux("Arabella Pezza", "Un article d'Arabella Pezza.") == "")
_check("un auteur RSS institutionnel est conservé",
       organisateur_depuis_flux("Ville de Nice", "") == "Ville de Nice")
_check("un auteur RSS vide reste vide", organisateur_depuis_flux("", "") == "")
_check("colonne déjà vide → on ne fabrique rien", verdict("", "")[0] == "garder")

print("\n──── défensif ────")
_check("None ne lève pas", verdict(None, None)[0] == "garder")
_check("espaces seuls → traité comme vide", verdict("   ", "")[0] == "garder")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
