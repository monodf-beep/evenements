#!/usr/bin/env python3
"""Fixture : le tableur du back-office (utils.tableur).

D'OÙ ÇA VIENT — demande de Franck du 2026-09-22 : « il faut un vrai tableur dans le
backoffice ». Un tableur dont le but est de MONTRER CE QUI MANQUE se juge sur un seul
point : est-ce qu'il compte juste ? Un taux de remplissage faux envoie chercher ce qui
n'existe pas, et c'est exactement ce qui a produit les « 454 points à contrôler » du
11/08 dont 315 n'étaient pas des tâches.

CE QUE CETTE FIXTURE EXIGE, et qui a dicté la forme du module :

  • un récurrent SANS date ne compte pas comme un trou de date — la date y est remplacée
    par une note (cf. utils.completeness), donc il n'y a rien à aller chercher ;
  • un multi-lieux sans lieu ni ville non plus ;
  • un ZÉRO numérique (un score de 0) n'est PAS une case vide. Piège classique du
    `if not valeur` : il confond 0, '' et None, et fait disparaître les fiches notées 0
    du comptage ;
  • le catalogue ne fait pas foi : une colonne qu'il annonce mais qui n'est pas en base
    doit disparaître, et une colonne en base qu'il ignore doit REMONTER (groupe
    « Autres ») — sinon le tableur cache une partie de son sujet ;
  • aucun cas présenté → « — », jamais « 0 % ». Un zéro ne dit pas s'il vient d'un échec
    ou d'une absence de cas.

Et un CAS QUI DOIT PASSER, près de la frontière (règle 3 du CLAUDE.md) : une fiche
ordinaire à laquelle il manque vraiment le lieu DOIT compter pour un trou — sans quoi ce
module aurait l'air juste en ne signalant plus rien.

Lancer : .venv/bin/python -m tests.test_tableur
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import tableur as tab  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# --- Jeu d'essai : quatre fiches, chacune pour une raison précise ------------------
ORDINAIRE = {"id": 1, "title": "Concert au château", "date_event_start": "2026-10-04",
             "date_event_end": "2026-10-04", "lieu": "Château des ducs", "ville": "Annecy",
             "territoire": "Savoie", "llm_categorie": "Concerts & Musique",
             "url_image": "https://exemple/x.jpg", "llm_score": 8}

TROUEE = dict(ORDINAIRE, id=2, title="Expo sans lieu", lieu="", ville=None)

RECURRENTE = {"id": 3, "title": "Visites du musée", "recurring": 1,
              "date_event_start": "", "date_event_end": "", "lieu": "Musée",
              "ville": "Aoste", "territoire": "Vallee-Aoste",
              "llm_categorie": "Expositions & Patrimoine", "url_image": "", "llm_score": 5}

ITINERANTE = {"id": 4, "title": "Festival diffus", "multi_lieux": 1, "lieu": "", "ville": "",
              "date_event_start": "2026-11-01", "date_event_end": "2026-11-09",
              "territoire": "Piemonte", "llm_categorie": "Festivals",
              "url_image": "https://exemple/f.jpg", "llm_score": 0}

TOUTES = [ORDINAIRE, TROUEE, RECURRENTE, ITINERANTE]

# --- « Sans objet » : ce qui ne s'applique pas n'est pas un manque -----------------
verifier("un récurrent n'a pas de trou de date",
         tab.sans_objet(RECURRENTE, "date_event_start"))
verifier("un multi-lieux n'a pas de trou de lieu",
         tab.sans_objet(ITINERANTE, "lieu") and tab.sans_objet(ITINERANTE, "ville"))
verifier("une fiche ordinaire, si — c'est le cas qui doit PASSER",
         not tab.sans_objet(TROUEE, "lieu"))
verifier("la cellule le dit en clair plutôt que de rester blanche",
         tab.affiche(RECURRENTE, "date_event_start") == "sans objet")

# --- Vide : un zéro n'est pas un vide ---------------------------------------------
verifier("un score de 0 n'est PAS une case vide",
         not tab.est_vide(ITINERANTE, "llm_score"), "0 compté comme vide")
verifier("None est vide", tab.est_vide(TROUEE, "ville"))
verifier("une chaîne d'espaces est vide", tab.est_vide({"x": "   "}, "x"))
verifier("une colonne absente de la ligne est vide", tab.est_vide({}, "lieu"))

# --- Comptage des trous ------------------------------------------------------------
COLS = ["date_event_start", "lieu", "ville", "url_image"]
verifier("la fiche complète n'a aucun trou", tab.trous(ORDINAIRE, COLS) == 0,
         str(tab.trous(ORDINAIRE, COLS)))
verifier("la fiche trouée en a deux (lieu + ville)", tab.trous(TROUEE, COLS) == 2,
         str(tab.trous(TROUEE, COLS)))
verifier("la récurrente n'en a qu'un (l'image), pas la date",
         tab.trous(RECURRENTE, COLS) == 1, str(tab.trous(RECURRENTE, COLS)))
verifier("l'itinérante n'en a aucun", tab.trous(ITINERANTE, COLS) == 0,
         str(tab.trous(ITINERANTE, COLS)))

# --- Taux : (remplies, concernées), dénominateur ajusté ----------------------------
t = tab.taux(TOUTES, COLS)
verifier("le lieu se mesure sur 3 fiches, pas 4 (l'itinérante est hors sujet)",
         t["lieu"] == (2, 3), str(t["lieu"]))
verifier("la date se mesure sur 3 fiches (la récurrente est hors sujet)",
         t["date_event_start"] == (3, 3), str(t["date_event_start"]))
verifier("l'image se mesure sur les 4", t["url_image"] == (3, 4), str(t["url_image"]))
verifier("le pourcentage arrondit", tab.pourcent(2, 3) == "67 %", tab.pourcent(2, 3))
verifier("aucun cas présenté → « — », jamais « 0 % »", tab.pourcent(0, 0) == "—",
         tab.pourcent(0, 0))
verifier("zéro rempli sur des cas réels dit bien 0 %", tab.pourcent(0, 7) == "0 %")

# --- Le catalogue ne fait pas foi, la base fait foi --------------------------------
EN_BASE = ["id", "title", "lieu", "ville", "colonne_ajoutee_demain"]
vis = tab.colonnes_visibles(EN_BASE)
noms = [c for c, _, _ in vis]
verifier("une colonne du catalogue absente de la base disparaît",
         "date_event_start" not in noms, str(noms))
verifier("une colonne de la base absente du catalogue REMONTE",
         "colonne_ajoutee_demain" in noms, str(noms))
verifier("et elle atterrit dans « Autres »",
         ("colonne_ajoutee_demain", "colonne_ajoutee_demain", "Autres") in vis)
verifier("l'ordre du catalogue est conservé", noms[:2] == ["id", "title"], str(noms[:2]))

# --- Jeux de colonnes ---------------------------------------------------------------
verifier("un jeu se restreint à ce qui existe",
         tab.jeu("completion", vis) == ["id", "title", "lieu", "ville"],
         str(tab.jeu("completion", vis)))
verifier("« tout » rend toutes les colonnes visibles, « Autres » comprise",
         tab.jeu("tout", vis) == noms)
verifier("un jeu inconnu retombe sur la complétude, sans planter",
         tab.jeu("inexistant", vis) == tab.jeu("completion", vis))
verifier("tous les jeux ne citent que des colonnes du catalogue",
         all(c in {x for x, _, _ in tab.CATALOGUE}
             for cols in tab.JEUX.values() for c in cols),
         "un jeu cite une colonne inconnue du catalogue")
verifier("chaque groupe du catalogue est déclaré dans GROUPES",
         {g for _, _, g in tab.CATALOGUE} <= set(tab.GROUPES))
verifier("chaque jeu a son libellé", set(tab.JEUX) <= set(tab.JEU_LIBELLES))

# --- Affichage et export ne font pas le même travail --------------------------------
LONGUE = {"llm_justification": "x" * 200}
verifier("la cellule tronque une valeur longue",
         len(tab.affiche(LONGUE, "llm_justification")) < 200)
verifier("l'export, LUI, ne tronque pas — un export tronqué n'est pas un export",
         len(tab.exporte(LONGUE, "llm_justification")) == 200,
         str(len(tab.exporte(LONGUE, "llm_justification"))))
verifier("un booléen s'affiche en clair", tab.affiche(RECURRENTE, "recurring") == "oui")
verifier("et son absence aussi", tab.affiche(ORDINAIRE, "multi_lieux") == "")
verifier("l'export d'un vide est une chaîne vide, pas « None »",
         tab.exporte(TROUEE, "ville") == "")

# --- « Où ça pêche » : le classement désigne-t-il le bon tas ? ----------------------
# Trois colonnes fabriquées pour opposer les deux classements possibles. « rare » est la
# plus vide en POURCENTAGE (0 % sur 1 cas), « gros » est le plus gros TAS (40 manques).
FAUX_TAUX = {
    "gros":   (60, 100),   # 40 manques, 60 % rempli
    "moyen":  (80, 100),   # 20 manques, 80 % rempli
    "rare":   (0, 1),      #  1 manque,   0 % rempli  ← piège du classement par %
    "plein":  (100, 100),  #  0 manque
    "aucun":  (0, 0),      # aucun cas présenté
}
classement = tab.ou_ca_peche(FAUX_TAUX)
noms_peche = [c for c, _, _, _ in classement]
verifier("le plus gros tas vient en tête, pas la colonne à 0 %",
         noms_peche[0] == "gros", str(noms_peche))
verifier("« rare » figure quand même, mais en dernier",
         noms_peche[-1] == "rare", str(noms_peche))
verifier("une colonne PLEINE n'est pas signalée", "plein" not in noms_peche, str(noms_peche))
verifier("une colonne sans aucun cas présenté non plus — le zéro muet",
         "aucun" not in noms_peche, str(noms_peche))
verifier("le chiffre rendu est le nombre de MANQUES",
         classement[0][1] == 40, str(classement[0]))
verifier("et il porte son dénominateur", classement[0][2] == 100, str(classement[0]))
verifier("on n'en rend que quelques-uns", len(tab.ou_ca_peche(FAUX_TAUX, combien=2)) == 2)
verifier("aucun manque nulle part → liste vide, pas une alerte creuse",
         tab.ou_ca_peche({"a": (5, 5)}) == [])

# --- Fiches trouées -----------------------------------------------------------------
verifier("deux fiches sur quatre ont au moins un trou (lieu/ville, et l'image)",
         tab.fiches_trouees(TOUTES, COLS) == 2, str(tab.fiches_trouees(TOUTES, COLS)))
verifier("aucune colonne demandée → aucune fiche trouée",
         tab.fiches_trouees(TOUTES, []) == 0)

# --- Les infos pratiques, dépliées du JSON -----------------------------------------
# CE QUE CE BLOC GARDE. Le 22/09 ce module affirmait « aucune colonne ne stocke un
# tarif », en citant la docstring d'utils/infos_pratiques.py. Elle était vraie le jour
# où elle a été écrite ; moisson_officielle a créé la colonne depuis et la remplit tous
# les matins. Un COMMENTAIRE avait été pris pour un FAIT. La fixture porte donc sur la
# donnée réelle, pas sur ce que le code dit d'elle.
JSON_REEL = ('{"tarif": ["Plein tarif 12 \u20ac, tarif reduit 8 \u20ac"], '
             '"horaires": ["ouvert de 10h a 18h", "fermeture le lundi"], '
             '"langue": ["visite bilingue"]}')
depliee = tab.deplier_infos({"id": 9, "infos_pratiques": JSON_REEL})
verifier("le tarif est déplié tel quel, sans interprétation",
         depliee["ip_tarif"].startswith("Plein tarif 12"), repr(depliee["ip_tarif"]))
verifier("une famille absente donne une case VIDE, pas « gratuit »",
         depliee["ip_reservation"] == "", repr(depliee["ip_reservation"]))
verifier("on ne garde que le premier extrait de chaque famille",
         depliee["ip_horaires"] == "ouvert de 10h a 18h", repr(depliee["ip_horaires"]))
verifier("une case dépliée vide compte comme un trou",
         tab.est_vide(depliee, "ip_reservation") and not tab.est_vide(depliee, "ip_tarif"))

verifier("un JSON illisible ne fait rien planter, il laisse vide",
         tab.deplier_infos({"infos_pratiques": "{pas du json"})["ip_tarif"] == "")
verifier("une colonne source vide aussi",
         tab.deplier_infos({"infos_pratiques": None})["ip_horaires"] == "")
verifier("une ligne sans la colonne du tout aussi", tab.deplier_infos({})["ip_langue"] == "")
verifier("un JSON qui n'est pas un objet non plus",
         tab.deplier_infos({"infos_pratiques": "[1,2,3]"})["ip_tarif"] == "")

vis_ip = tab.colonnes_visibles(["id", "title", "infos_pratiques"])
noms_ip = [c for c, _, _ in vis_ip]
verifier("les colonnes virtuelles apparaissent quand leur SOURCE existe",
         "ip_tarif" in noms_ip and "ip_accessibilite" in noms_ip, str(noms_ip))
verifier("la colonne source brute, elle, ne s'affiche PAS (c'est du JSON)",
         "infos_pratiques" not in noms_ip, str(noms_ip))
verifier("sans la source, aucune colonne virtuelle — sinon on croirait à un manque "
         "de données là où c'est la colonne qui manque",
         not any(c.startswith("ip_") for c, _, _ in tab.colonnes_visibles(["id", "title"])))
verifier("le jeu « Infos pratiques » existe et tient debout",
         tab.jeu("pratique", vis_ip) == ["id", "title", "ip_tarif", "ip_horaires",
                                         "ip_reservation", "ip_accessibilite"],
         str(tab.jeu("pratique", vis_ip)))
verifier("un extrait long est tronqué en cellule",
         len(tab.affiche({"ip_tarif": "x" * 200}, "ip_tarif")) < 200)
verifier("mais pas à l'export", len(tab.exporte({"ip_tarif": "x" * 200}, "ip_tarif")) == 200)

# --- Source unique des champs modifiables ------------------------------------------
verifier("les champs modifiables sont tous au catalogue",
         set(tab.EDITABLES) <= {c for c, _, _ in tab.CATALOGUE},
         str(set(tab.EDITABLES) - {c for c, _, _ in tab.CATALOGUE}))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
