#!/usr/bin/env python3
"""Fixture : la date près du titre, dans une newsletter qui en annonce dix.

Le corps est calqué sur celui des musées de Chambéry, qui a produit six fiches sans date
dans la file du 2026-08-11 (4242, 4244, 4245, 4247, 4248, 4249). Un seul mail, six
événements, six dates différentes — plus la date d'envoi et les horaires d'ouverture.

CE QUE LA FIXTURE PROTÈGE AVANT TOUT : qu'aucune fiche ne reçoive la date d'une AUTRE.
C'est le risque propre à ce format, et il est pire que l'absence de date : une fiche sans
date se répare, une fiche datée du mauvais jour envoie quelqu'un devant une porte close
et personne ne s'en aperçoit.

Lancer : .venv/bin/python -m tests.test_mail_dates
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.mail_dates import date_pres_du_titre, message_id_de  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


MAIL = """
Musées de Chambéry — la lettre du 3 août 2026

Nos musées sont ouverts du mardi au dimanche de 10h à 18h.

Visite commentée : Icônes, trésor du musée national d'Art médiéval de Korça
Le jeudi 13 août à 14h30, au Musée des Beaux-Arts. Gratuit sur inscription.

La visite-atelier des 4-6 ans : Ma petite icône
Le mercredi 19 août à 10h, au Musée des Beaux-Arts.

Sieste musicale aux Charmettes - OudéBach
Le vendredi 21 août à 18h30, aux Charmettes. Apportez un plaid.

Balade gourmande aux Charmettes
Le dimanche 30 août à 11h, aux Charmettes.

Bien-être aux Charmettes : Pilates
Tous les mardis, prochaine séance le 25 août à 9h30.

Retrouvez toute la programmation sur notre site.
"""

print("──── chaque fiche reçoit SA date, pas celle de sa voisine ────")
ATTENDU = [
    ("Visite commentée : Icônes, trésor du musée national d'Art médiéval de Korça",
     "2026-08-13"),
    ("La visite-atelier des 4-6 ans : Ma petite icône", "2026-08-19"),
    ("Sieste musicale aux Charmettes - OudéBach", "2026-08-21"),
    ("Balade gourmande aux Charmettes", "2026-08-30"),
    ("Bien-être aux Charmettes : Pilates", "2026-08-25"),
]
for titre, attendu in ATTENDU:
    debut, _fin = date_pres_du_titre(MAIL, titre)
    _check(f"« {titre[:44]} » → {attendu}", debut == attendu, f"(obtenu {debut!r})")

print("\n──── ce qui doit rendre VIDE ────")
_check("un titre absent du mail ne récolte pas la première date venue",
       date_pres_du_titre(MAIL, "Concert de jazz au Manège") == ("", ""),
       str(date_pres_du_titre(MAIL, "Concert de jazz au Manège")))
_check("un titre trop court pour discriminer ne récolte rien",
       date_pres_du_titre(MAIL, "Le") == ("", ""))
_check("corps vide → rien", date_pres_du_titre("", "Sieste musicale aux Charmettes") == ("", ""))
_check("titre vide → rien", date_pres_du_titre(MAIL, "") == ("", ""))
_check("aucune date dans le corps → rien",
       date_pres_du_titre("Une lettre sans la moindre date.", "Une lettre") == ("", ""))

print("\n──── les titres voisins bornent la fenêtre ────")
# LE CAS RÉEL DU 2026-08-11 : une description longue, puis l'annonce suivante avec SA
# date. Sans borne, la fenêtre déborde et la fiche reçoit la date de sa voisine — c'est
# arrivé en production sur « La visite-atelier des 4-6 ans » et « Sieste musicale ».
LONG = ("Musees de Chambery. "
        "La visite-atelier des 4-6 ans : Ma petite icone. "
        # Description assez courte pour que la date de la VOISINE tombe dans la fenêtre
        # de 220 caractères : c'est ainsi que la fuite se produit réellement.
        "Les enfants creeront leur icone imaginaire en atelier. "
        "Sieste musicale aux Charmettes - OudeBach. Le jeudi 6 aout a 18h30.")
sans_borne = date_pres_du_titre(LONG, "La visite-atelier des 4-6 ans : Ma petite icone")
_check("sans borne, la fenêtre attrape bien la date de la voisine (le défaut constaté)",
       sans_borne[0] == "2026-08-06", str(sans_borne))
avec_borne = date_pres_du_titre(
    LONG, "La visite-atelier des 4-6 ans : Ma petite icone",
    autres_titres=["Sieste musicale aux Charmettes - OudeBach"])
_check("avec le titre voisin comme borne, plus aucune date n'est posée",
       avec_borne == ("", ""), str(avec_borne))
_check("et la voisine, elle, garde bien sa date",
       date_pres_du_titre(LONG, "Sieste musicale aux Charmettes - OudeBach",
                          autres_titres=["La visite-atelier des 4-6 ans : Ma petite icone"]
                          )[0] == "2026-08-06")

print("\n──── l'extrait montré doit contenir la date ────")
# Deux des trois dates du premier run étaient « prouvées » par un extrait sans aucune
# date dedans. Une preuve qui ne montre pas le fait qu'elle établit rassure à tort.
ex = []
date_pres_du_titre(MAIL, "Sieste musicale aux Charmettes - OudéBach", _extraits=ex)
_check("l'extrait affiché porte bien la date lue", ex and "21 aout" in ex[0], str(ex))

print("\n──── deux dates différentes autour du même titre → rien ────")
# Le cas qui arrive vraiment : la newsletter reprend le même intitulé deux fois, pour
# deux séances. On ne devine pas laquelle est « la » date.
AMBIGU = ("Atelier poterie pour enfants — le 12 septembre à 14h. "
          "Plus loin : Atelier poterie pour enfants — le 26 septembre à 14h.")
_check("deux séances homonymes → aucune date posée",
       date_pres_du_titre(AMBIGU, "Atelier poterie pour enfants") == ("", ""),
       str(date_pres_du_titre(AMBIGU, "Atelier poterie pour enfants")))

print("\n──── retrouver le mail depuis l'adresse de la fiche ────")
_check("gmail:19fa305b67f95221#3 → 19fa305b67f95221",
       message_id_de("gmail:19fa305b67f95221#3") == "19fa305b67f95221")
_check("sans dièse, ça marche aussi",
       message_id_de("gmail:19fa305b67f95221") == "19fa305b67f95221")
_check("une vraie URL n'est pas un identifiant de mail",
       message_id_de("https://exemple.fr/evenement") == "")
_check("vide → vide", message_id_de("") == "" and message_id_de(None) == "")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
