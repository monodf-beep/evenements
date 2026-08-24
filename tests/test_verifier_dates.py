#!/usr/bin/env python3
"""Fixture : le contradicteur de dates. Base jetable — jamais data/events.db.

CE QUE LA FIXTURE SURVEILLE, dans l'ordre d'importance — et c'est l'inverse de l'ordre
qu'on croit. Le risque n'est pas de rater une contradiction : c'est d'en inventer. Un
détecteur qui signale trop rend une file que personne ne lit, et le 2026-08-11 en a
produit deux (25 « fautes » de temps dont 17 correctes, 454 « points à contrôler » dont
315 étaient des silences de la source).

  1. le SILENCE n'est jamais une tâche — un texte sans date ne contredit rien ;
  2. l'AMBIGUÏTÉ non plus — plusieurs dates, aucune n'est la nôtre : notre date vient
     peut-être de la page officielle, qu'on n'a pas sous la main ;
  3. une date CONFIRMÉE ne remonte pas, même si le texte cite dix autres dates autour
     (une page de saison cite ses voisines, un mail porte sa date d'envoi) ;
  4. et seulement ensuite : les deux formes franches sont bien vues.

Lancer : .venv/bin/python -m tests.test_verifier_dates
"""
import io
import contextlib
import re
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import verifier_dates  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ── 1. Le cœur, testé sans base ──────────────────────────────────────────────────────
REF = date(2026, 8, 11)
print("──── 1. l'inventaire des dates d'un texte ────")
_check("une date en toutes lettres est lue",
       "2026-08-21" in verifier_dates.dates_du_texte("Le vendredi 21 août 2026 à 21h", REF))
_check("l'italien aussi",
       "2026-08-15" in verifier_dates.dates_du_texte("Il 15 agosto 2026 in piazza", REF))
_check("l'année sous-entendue s'accroche à la COLLECTE, pas à aujourd'hui",
       "2026-09-19" in verifier_dates.dates_du_texte("Le 19 septembre à 21h", REF))
_check("plusieurs dates sont toutes rendues (c'est le NOMBRE qui décide ensuite)",
       len(verifier_dates.dates_du_texte(
           "Du 3 juin au 13 septembre 2026, ouverture le 2 juin 2026", REF)) >= 3)
_check("un texte sans date rend l'ensemble vide",
       verifier_dates.dates_du_texte("Entrée libre, réservation conseillée.", REF) == set())

print("\n──── 2. les verdicts ────")
_check("silence → muet, jamais une tâche",
       verifier_dates.verdict({"2026-08-21"}, set())[0] == "muet")
_check("date présente → confirmé",
       verifier_dates.verdict({"2026-08-21"}, {"2026-08-21"})[0] == "confirme")
_check("date présente PARMI d'autres → confirmé quand même (page de saison, mail daté)",
       verifier_dates.verdict({"2026-08-21"},
                              {"2026-08-21", "2026-07-02", "2026-09-30"})[0] == "confirme")
_check("une seule date, différente → contredit",
       verifier_dates.verdict({"2026-08-22"}, {"2026-08-21"})[0] == "contredit")
_check("même jour, autre année → année",
       verifier_dates.verdict({"2026-08-15"}, {"2024-08-15"})[0] == "annee")
_check("plusieurs dates, aucune n'est la nôtre → INDÉCIS, pas contredit — "
       "le cas près de la frontière, celui qui doit PASSER",
       verifier_dates.verdict({"2026-08-21"},
                              {"2026-06-02", "2026-07-15", "2026-09-30"})[0] == "indecis")
_check("l'année prime sur le contredit quand les deux pourraient s'appliquer",
       verifier_dates.verdict({"2026-08-15"}, {"2024-08-15"})[0] == "annee")
_check("la date de FIN compte aussi comme confirmation",
       verifier_dates.verdict({"2026-06-03", "2026-09-13"}, {"2026-09-13"})[0] == "confirme")

# ── 3. Sur une base ──────────────────────────────────────────────────────────────────
tmp = Path(tempfile.mkdtemp(prefix="fixture-verifdates-"))
db = tmp / "events.db"
conn = sqlite3.connect(db)
init_db(conn)
AVENIR = (date.today() + timedelta(days=40)).isoformat()
PASSE = (date.today() - timedelta(days=40)).isoformat()
COLLECTE = date.today().isoformat() + " 06:00:00"

# ⚠️ LES DATES DES FICHES SONT RELATIVES À AUJOURD'HUI, ET C'EST INDISPENSABLE.
# Elles étaient écrites en dur (« 2026-08-21 », « 2026-08-15 ») : la fixture est passée
# au ROUGE toute seule le 2026-08-16, quand le 15 août est devenu la veille et que la
# règle 5 a écarté la fiche « année périmée » du rapport. Trois assertions sont tombées
# sans qu'une ligne de code ait bougé.
#
# Le danger n'est pas l'échec, il est l'HABITUDE qu'il installe : un test qui rougit
# selon le calendrier s'explique par « c'est juste la date », et le jour où il rougit
# pour une vraie régression, on le classera pareil.
#
# Les dates du TEXTE suivent celles de la base, construites ensemble : c'est leur écart
# qui fait le verdict, jamais leur valeur absolue.
_J = date.today() + timedelta(days=40)
_TXT = f"{_J.day} août {_J.year}" if _J.month == 8 else _J.strftime("%d/%m/%Y")
_J1 = _J + timedelta(days=1)
# Trois dates de programme, TOUTES différentes de la nôtre et toutes à venir : c'est ce
# qui fait l'indécision, et rien d'autre. Les décaler de `_J` garantit qu'aucune ne
# deviendra notre date au fil des jours.
_P1, _P2, _P3 = (_J + timedelta(days=d) for d in (10, 20, 30))
# Pour les cas « jour de semaine » (8bis) : deux dates de plus, avec leur VRAI jour de
# semaine calculé — jamais écrit en dur, sinon le cas se dérègle au fil du calendrier
# exactement comme _J1 avant lui (fiches 3 et 4, corrigé le 2026-08-18).
from utils.jours import NOM_DU_JOUR as _NOM_JOUR  # noqa: E402
_J8 = _J + timedelta(days=3)                       # sert le cas RSS (peu importe le jour)
_J9 = _J + timedelta(days=5)                        # sert le cas HTML — un jour AVANT
_J9M1 = _J9 - timedelta(days=1)
_J11 = _J + timedelta(days=7)                       # jour annoncé = jour RÉEL, cas qui passe
_JOUR_J11 = _NOM_JOUR[_J11.weekday()]
# Fiche 10 (Paratissima) : il faut un jour de semaine FAUX pour la date choisie. On prend
# le jour civilement suivant celui de _J (garanti différent, aucun calcul de calendrier
# fragile) plutôt qu'un jour écrit en dur qui pourrait un jour coïncider par hasard.
_J10 = _J + timedelta(days=14)
_JOUR_J10_FAUX = _NOM_JOUR[(_J10.weekday() + 1) % 7]
# Noms de mois écrits ici, PAS lus dans utils.jours._MOIS (privé, sans accent, fait pour
# la RECONNAISSANCE — pas pour construire un texte lisible). Les deux jeux ne se
# recouvrent que par les valeurs, jamais par l'objet.
_MOIS_FR = {1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
            7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre",
            12: "décembre"}
_MESE_IT = {1: "gennaio", 2: "febbraio", 3: "marzo", 4: "aprile", 5: "maggio",
            6: "giugno", 7: "luglio", 8: "agosto", 9: "settembre", 10: "ottobre",
            11: "novembre", 12: "dicembre"}
_TXT1 = f"{_J1.day} août {_J1.year}" if _J1.month == 8 else _J1.strftime("%d/%m/%Y")

CAS = [
    # (id, titre, description, début, fin, wp, statut)
    (1, "Tribute to Céline Dion",
     f"Le {_TXT} à 21h, le Théâtre de Verdure accueille le spectacle.",
     _J.isoformat(), _J.isoformat(), 7001, "pending"),                 # confirmé
    (2, "Concert d'été",
     f"Rendez-vous le {_TXT} au kiosque.",
     _J1.isoformat(), _J1.isoformat(), 7002, "pending"),               # CONTREDIT
    # ANNÉE — même jour ET même MOIS, autre millésime. Le mois était écrit « agosto » en
    # dur : le 2026-08-21 il a cessé de correspondre à `_J`, passé en septembre, et le cas
    # est devenu un simple « contredit ». Le compteur ANNÉE est tombé à zéro sans que rien
    # ne le dise. Tout ce qui vient d'une date se construit donc à partir de `_J`.
    (3, "Fête patronale",
     f"Come ogni anno, la festa si tiene il {_J.day:02d}/{_J.month:02d}/{_J.year - 2} in piazza.",
     _J.isoformat(), _J.isoformat(), None, "pending"),                 # ANNÉE
    # INDÉCIS — plusieurs dates dans le texte, AUCUNE n'est la nôtre. Les trois étaient
    # écrites en dur ; le 2026-08-21, « 30 septembre 2026 » EST devenue notre date, et le
    # cas est passé de « indécis » à « confirmé ». Un cas-frontière qui se retourne tout
    # seul ne prouve plus rien — il prouve même le contraire de ce qu'il annonce.
    (4, "Saison culturelle",
     f"Programme : {_P1:%d/%m/%Y}, {_P2:%d/%m/%Y}, {_P3:%d/%m/%Y}. Réservations ouvertes.",
     AVENIR, AVENIR, None, "pending"),                                 # indécis
    (5, "Sortie au lac", "Entrée libre, chaussures de marche conseillées.",
     AVENIR, AVENIR, None, "pending"),                                 # muet
    # PASSÉ : une date fausse n'y envoie plus personne devant une porte close (règle 5).
    (6, "Concert de mai", f"Le {_TXT} au kiosque.", PASSE, PASSE, None, "pending"),
    (7, "Déjà écartée", f"Le {_TXT} au kiosque.",
     _J1.isoformat(), _J1.isoformat(), None, "rejected"),
]
for eid, titre, desc, deb, fin, wp, statut in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, source_name, "
        " date_event_start, date_event_end, date_source, statut, scrape_date, "
        " wp_post_id_as) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (eid, titre, desc, f"https://exemple.fr/{eid}", "Source officielle",
         deb, fin, "parsed", statut, COLLECTE, wp))
conn.commit()
conn.close()
verifier_dates.DB_PATH = db


def _sortie(argv=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        verifier_dates.main(argv or [])
    s = buf.getvalue()
    return {int(m) for m in re.findall(r"^  \[\s*(\d+)\]", s, re.M)}, s


print("\n──── 1 ter. la borne de plage — une plage à moitié juste est fausse ────")
# TROUVÉ PAR L'AUTRE CONVERSATION le 2026-08-12, sur deux fiches EN LIGNE : Guitare en
# scène (source « du 14 au 18 juillet », fiche du 14 au 17) et Festa di San Savino (source
# « dal 4 all'8 luglio », fiche du 4 au 7). Un jour perdu à la fin, deux fois.
#
# Mon verdict les déclarait CONFIRMÉES : il suffisait qu'UNE borne figure dans le texte. Or
# c'est la fin qui envoie quelqu'un devant une porte close le dernier jour.
_check("Guitare en scène : fiche 14-17, source 14-18 → BORNE, plus « confirmé »",
       verifier_dates.verdict({"2026-07-14", "2026-07-17"},
                              {"2026-07-14", "2026-07-18"})[0] == "borne")
_check("San Savino : fiche 4-7, source 4-8 → BORNE",
       verifier_dates.verdict({"2026-07-04", "2026-07-07"},
                              {"2026-07-04", "2026-07-08"})[0] == "borne")
# LE SIGNALEMENT DOIT NOMMER LA BONNE DATE. La première version désignait le 14 juillet —
# notre propre début, déjà confirmé — comme remplaçant du 17, en annonçant « 3 jours
# d'écart » là où la correction est le 18, à un jour. Un signalement qui nomme la mauvaise
# date envoie corriger de travers.
_m = verifier_dates.verdict({"2026-07-14", "2026-07-17"},
                            {"2026-07-14", "2026-07-18"})[1]
_check("il nomme la voisine la PLUS PROCHE, jamais une de nos propres bornes",
       "2026-07-18" in _m and "1 jour" in _m, _m)

# LES CAS QUI DOIVENT PASSER, choisis près de la frontière — sans eux ce contrôle
# transformerait toute page de saison en file de bruit.
_check("plage exacte → confirmée",
       verifier_dates.verdict({"2026-07-14", "2026-07-18"},
                              {"2026-07-14", "2026-07-18"})[0] == "confirme")
_check("dates lointaines dans le texte → confirmée, pas « borne »",
       verifier_dates.verdict({"2026-06-03", "2026-09-13"},
                              {"2026-06-03", "2026-07-15"})[0] == "confirme")
_check("un autre MOIS ne fait pas une borne décalée",
       verifier_dates.verdict({"2026-07-31", "2026-08-05"},
                              {"2026-07-31", "2026-09-02"})[0] == "confirme")
_check("date unique confirmée → confirmée",
       verifier_dates.verdict({"2026-08-21"}, {"2026-08-21", "2026-09-30"})[0] == "confirme")

print("\n──── 2 bis. le jour de la semaine ────")
_check("« sabato 7 maggio » est lu",
       verifier_dates.jours_nommes("venire a trovarci sabato 7 maggio dalle 16") ==
       {(5, 7): {5}})
_check("le français aussi",
       verifier_dates.jours_nommes("Le vendredi 21 août 2026 à 21h") == {(8, 21): {4}})
# LE FAUX POSITIF TERRA MADRE, RECOPIÉ. L'article nomme DEUX fois le 27 septembre ; la
# première mention est juste. La version qui écrasait ne gardait que la seconde et
# accusait une date confirmée par slowfood.it.
_TM = ("Da giovedi 24 a domenica 27 settembre 2026 a Torino si terra la 40a edizione. "
       "Lunedi 27 settembre le scuole restano chiuse.")
_check("les DEUX mentions du même quantième sont gardées",
       verifier_dates.jours_nommes(_TM) == {(9, 27): {6, 0}},
       verifier_dates.jours_nommes(_TM))
_check("et une source qui se contredit ne prouve rien CONTRE nous — Terra Madre passe",
       verifier_dates.verdict_jour({"2026-09-27"}, verifier_dates.jours_nommes(_TM)) == "",
       verifier_dates.verdict_jour({"2026-09-27"}, verifier_dates.jours_nommes(_TM)))
_check("un texte sans jour nommé ne dit rien",
       verifier_dates.jours_nommes("Le 21 août 2026 à 21h") == {})
# LE CAS 1069, RECOPIÉ : notre 07/05/2027 est un vendredi, la page dit samedi.
_check("le désaccord de jour est signalé",
       "samedi" in verifier_dates.verdict_jour({"2027-05-07"}, {(5, 7): {5}}))
# LES ANNÉES SONT ÉNUMÉRÉES, PAS CHOISIES. La première version prenait max() sur une
# fenêtre qui va jusqu'à deux ans devant : elle annonçait 2027 pour une annonce de 2021,
# c'est-à-dire l'hypothèse la plus flatteuse. Un affichage qui choisit à la place du
# lecteur choisit toujours dans le sens de celui qui l'a écrit.
# UNE SEULE ANNÉE POSSIBLE, ET ELLE EST DERRIÈRE : le geste n'est pas de re-dater, c'est
# d'écarter (règle 5). C'est le cas de l'écrasante majorité des 19 fiches du 2026-08-11.
_check("annonce ancienne : le GESTE est nommé, et c'est écarter",
       "2022-05-07" in verifier_dates.verdict_jour({"2027-05-07"}, {(5, 7): {5}}) and
       "ÉCARTER" in verifier_dates.verdict_jour({"2027-05-07"}, {(5, 7): {5}}),
       verifier_dates.verdict_jour({"2027-05-07"}, {(5, 7): {5}}))
_check("deux années possibles : aucun geste n'est dicté, l'ambiguïté est dite",
       "ÉCARTER" not in verifier_dates.verdict_jour({"2026-12-11"}, {(12, 11): {5}}),
       verifier_dates.verdict_jour({"2026-12-11"}, {(12, 11): {5}}))
_check("décalage d'un an : l'année voisine est proposée, et les DEUX sont listées",
       "2021, 2027" in verifier_dates.verdict_jour({"2026-12-11"}, {(12, 11): {5}}) and
       "UN AN" in verifier_dates.verdict_jour({"2026-12-11"}, {(12, 11): {5}}),
       verifier_dates.verdict_jour({"2026-12-11"}, {(12, 11): {5}}))
_check("un jour qui COLLE ne dit rien — le cas près de la frontière",
       verifier_dates.verdict_jour({"2026-08-21"}, {(8, 21): {4}}) == "")
_check("un jour nommé pour une AUTRE date ne juge pas la nôtre",
       verifier_dates.verdict_jour({"2026-08-21"}, {(9, 12): {5}}) == "")
_check("la phrase du jour de semaine est retrouvable — le signalement DOIT se lire",
       "sabato 7 maggio" in verifier_dates.phrase_du_jour(
           "ti bastera venire a trovarci sabato 7 maggio dalle 16.", 5, 7))

print("\n──── 3. sur une base ────")
vues, sortie = _sortie()
_check("la contradiction franche est listée", 2 in vues, sorted(vues))
_check("l'année périmée est listée", 3 in vues, sorted(vues))
_check("la fiche CONFIRMÉE n'est pas listée", 1 not in vues, sorted(vues))
_check("l'INDÉCISE n'est pas listée — pas de geste au bout (règle 6)",
       4 not in vues, sorted(vues))
_check("la MUETTE n'est pas listée — on ne vérifie pas un silence",
       5 not in vues, sorted(vues))
_check("le PASSÉ est hors périmètre (règle 5)", 6 not in vues, sorted(vues))
_check("la fiche écartée est hors périmètre", 7 not in vues, sorted(vues))
_check("exactement deux fiches à regarder", vues == {2, 3}, sorted(vues))

print("\n──── 4. le compte rendu se vérifie lui-même ────")
_check("les muettes sont COMPTÉES même si elles ne sont pas listées",
       re.search(r"1\s+muettes", sortie) is not None, sortie[:900])
_check("les indécises aussi", re.search(r"1\s+indécises", sortie) is not None)
_check("les confirmées aussi — sinon un « 0 contradiction » ne dirait pas s'il vient "
       "d'une base saine ou d'une requête vide",
       re.search(r"1\s+confirmées", sortie) is not None)
_check("le périmètre est écrit à côté du total", "règle 5" in sortie)
_check("la portée est bornée", "SIGNALEMENT" in sortie)
# Ces fiches-là sont PUBLIÉES : une correction à tort réécrit une page que des gens
# lisent. Le lecteur doit voir la PHRASE, pas deux nombres qui s'opposent.
# Les libellés attendus se construisent depuis les MÊMES dates que les fiches : les
# écrire en dur, c'est ce qui a fait rougir cette fixture toute seule le 2026-08-16.
_check("la phrase du texte source est montrée pour la contradiction",
       "le texte dit : «" in sortie and _TXT in sortie, sortie[-1200:])
_check("et pour l'année périmée aussi",
       f"{_J.day:02d}/{_J.month:02d}/{_J.year - 2}" in sortie, sortie[-1200:])
_check("le verdict rend la date du texte qui a déclenché le signalement",
       verifier_dates.verdict({"2026-08-22"}, {"2026-08-21"})[2] == "2026-08-21")
_check("et rien quand il n'y a pas de signalement",
       verifier_dates.verdict({"2026-08-21"}, {"2026-08-21"})[2] == "")

print("\n──── 4 bis. la métadonnée n'est PAS un texte écrit pour des humains ────")
# LE FAUX SIGNALEMENT DU 2026-08-11 AU SOIR. `date_start` reçoit `entry.get("published")`,
# l'horodatage de publication du flux — jamais la date de l'événement. La fiche 923
# (Charlie Winston) a été annoncée « contredite » parce que son unique date était
# « Wed, 24 Jun 2026 13:44:10 +0000 ».
c = sqlite3.connect(db)
c.execute("INSERT INTO events_raw (id, title, description, url_source, source_name, "
          " date_start, date_event_start, date_event_end, date_source, statut, "
          " scrape_date) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
          (8, "Charlie Winston", "Concert à la Maison des Arts du Léman. Tarifs sur place.",
           "https://exemple.fr/8", "Maison des Arts du Léman",
           f"Wed, {_J8:%d %b %Y} 13:44:10 +0000", AVENIR, AVENIR, "parsed", "pending",
           COLLECTE))
# Et le HTML brut, qui rendait l'extrait illisible (fiche 473 : « <time>20/05/2026</time> »)
c.execute("INSERT INTO events_raw (id, title, description, url_source, source_name, "
          " date_event_start, date_event_end, date_source, statut, scrape_date) "
          "VALUES (?,?,?,?,?,?,?,?,?,?)",
          (9, "Fête balisée",
           f"<p>Rendez-vous le <time>{_J9M1.day} {_MOIS_FR[_J9M1.month]} {_J9M1.year}"
           "</time> au kiosque.</p>",
           "https://exemple.fr/9", "Source officielle", _J9.isoformat(), _J9.isoformat(),
           "parsed", "pending", COLLECTE))
c.commit()
c.close()
# LE CAS 1069, EN BASE. Le texte dit « sabato 7 maggio » ; notre 07/05/2027 est un
# vendredi. Aucune des deux autres règles ne le voit : le quantième CONCORDE des deux
# côtés, donc le verdict serait « confirmé ». Seul le jour de semaine sépare 2022 de 2027.
c = sqlite3.connect(db)
c.execute("INSERT INTO events_raw (id, title, description, url_source, source_name, "
          " date_event_start, date_event_end, date_source, statut, scrape_date) "
          "VALUES (?,?,?,?,?,?,?,?,?,?)",
          (10, "Studio Visit Paratissima Factory",
           f"La visita agli studio è libera: ti basterà venire a trovarci "
           f"{_JOUR_J10_FAUX} {_J10.day} {_MESE_IT[_J10.month]} dalle 16.",
           "https://exemple.fr/10", "Paratissima (Torino)",
           _J10.isoformat(), _J10.isoformat(), "parsed", "pending", COLLECTE))
# Et le cas qui doit PASSER : jour annoncé, jour exact. Le 21/08/2026 est bien un vendredi.
c.execute("INSERT INTO events_raw (id, title, description, url_source, source_name, "
          " date_event_start, date_event_end, date_source, statut, scrape_date) "
          "VALUES (?,?,?,?,?,?,?,?,?,?)",
          (11, f"Concert du {_JOUR_J11}",
           f"Le {_JOUR_J11} {_J11.day} {_MOIS_FR[_J11.month]} {_J11.year} à 21h au kiosque.",
           "https://exemple.fr/11", "Source officielle", _J11.isoformat(), _J11.isoformat(),
           "parsed", "pending", COLLECTE))
c.commit()
c.close()
vues_meta, sortie_meta = _sortie()
_check("le jour de semaine démasque la fiche 1069 — que les deux autres règles ratent",
       10 in vues_meta, sorted(vues_meta))
_check("et le jour de semaine JUSTE ne déclenche rien", 11 not in vues_meta,
       sorted(vues_meta))
_check("le compte rendu nomme la famille", "JOUR DE SEMAINE" in sortie_meta)
_check("l'horodatage RSS ne contredit RIEN — ce n'est pas le texte de la source",
       8 not in vues_meta, sorted(vues_meta))
_check("mais une date en HTML est bien lue, balises retirées", 9 in vues_meta,
       sorted(vues_meta))
_check("et son extrait se lit sans balises",
       f"{_J9M1.day} {_MOIS_FR[_J9M1.month]} {_J9M1.year}" in sortie_meta
       and "<time>" not in sortie_meta,
       sortie_meta[-900:])

print("\n──── 4 ter. classé sans suite : vérifié une fois, tu ne le redis plus ────")
# Les cinq signalements du 2026-08-11 étaient tous JUSTES. Sans mémoire, ils reviennent à
# l'identique tous les jours — et une liste qui affiche toujours les mêmes lignes apprend à
# ne plus être lue. C'est le jour où une sixième arrive qu'on ne la voit pas.
from scripts import classer_sans_suite as _cl                        # noqa: E402
import tempfile as _tf                                              # noqa: E402
_cl.MEMOIRE = tmp / "classes.json"
_cl.DB_PATH = db
verifier_dates.DB_PATH = db

_avant, _ = _sortie()
_check("la fiche 2 est signalée avant tout classement", 2 in _avant, sorted(_avant))

_cl.main(["2", "--motif", "vérifié à la source : la date de la salle confirme la nôtre, "
                          "le 21 août venait d'un autre spectacle de la même lettre"])
_apres, sortie_cl = _sortie()
_check("classée : elle disparaît de la liste", 2 not in _apres, sorted(_apres))
_check("mais elle est COMPTÉE, pas tue — sinon on la découvre des semaines plus tard",
       "classées sans suite" in sortie_cl, sortie_cl[:700])

# LE POINT CENTRAL : le classement doit TOMBER quand la question change. Un classement
# définitif serait un cul-de-sac de plus (règle 3).
#
# ⚠️ ICI-MÊME, LE 2026-08-24 : les deux dates qui suivent étaient écrites en dur
# ('2026-08-23', '2026-08-22'). Le calendrier a avancé, elles sont passées dans le passé,
# et la fiche 2 est sortie du périmètre (règle 5) pour tout le RESTE du fichier — trois
# assertions en cascade sont tombées, dont une ("re-classée après re-vérification") est
# restée VERTE pour la mauvaise raison : elle passait parce que la fiche avait disparu du
# périmètre, pas parce que le classement tenait. La même faute qu'aux fiches 3 et 4,
# retrouvée six jours plus tard dans un coin du fichier qu'on n'avait pas relu.
_J2A = _J1 + timedelta(days=1)          # future, ET différente de _J1 : invalide la mémoire
c = sqlite3.connect(db)
c.execute("UPDATE events_raw SET date_event_start=?, date_event_end=? WHERE id=2",
          (_J2A.isoformat(), _J2A.isoformat()))
c.commit(); c.close()
_rouvert, _ = _sortie()
_check("notre date change → le classement TOMBE, le signalement revient",
       2 in _rouvert, sorted(_rouvert))

# Et l'inverse : si la matière source bouge, pareil.
_J2B = _J + timedelta(days=25)
c = sqlite3.connect(db)
c.execute("UPDATE events_raw SET date_event_start=?, date_event_end=? WHERE id=2",
          (_J2B.isoformat(), _J2B.isoformat()))
c.commit(); c.close()
_cl.main(["2", "--motif", "re-vérifié après changement, la source confirme notre date "
                          "telle qu'elle est aujourd'hui"])
_check("re-classée après re-vérification", 2 not in _sortie()[0])
_J2C = _J + timedelta(days=50)
c = sqlite3.connect(db)
c.execute("UPDATE events_raw SET description=? WHERE id=2",
          (f"Rendez-vous le {_J2C.day} {_MOIS_FR[_J2C.month]} {_J2C.year}.",))
c.commit(); c.close()
_check("la SOURCE change → le classement tombe aussi", 2 in _sortie()[0], sorted(_sortie()[0]))

_check("un motif trop court est refusé — c'est lui qu'on relira dans six mois",
       _cl.main(["3", "--motif", "ok"]) == 1)

print("\n──── 5. --en-ligne : d'abord ce que le public lit ────")
vues_ligne, _ = _sortie(["--en-ligne"])
_check("seule la contradiction PUBLIÉE remonte", vues_ligne == {2}, sorted(vues_ligne))

print("\n──── 6. --tout montre les indécises, sans les transformer en tâches ────")
vues_tout, sortie_tout = _sortie(["--tout"])
_check("l'indécise apparaît quand on la demande", 4 in vues_tout, sorted(vues_tout))
_check("la muette reste absente même de --tout", 5 not in vues_tout, sorted(vues_tout))

print(f"\n{'TOUT PASSE' if not echecs else str(echecs) + ' ÉCHEC(S)'}")
sys.exit(1 if echecs else 0)
