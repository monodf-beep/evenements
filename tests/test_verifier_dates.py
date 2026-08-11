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

CAS = [
    # (id, titre, description, début, fin, wp, statut)
    (1, "Tribute to Céline Dion",
     "Le vendredi 21 août 2026 à 21h, le Théâtre de Verdure accueille le spectacle.",
     "2026-08-21", "2026-08-21", 7001, "pending"),                     # confirmé
    (2, "Concert d'été",
     "Rendez-vous le 21 août 2026 au kiosque.",
     "2026-08-22", "2026-08-22", 7002, "pending"),                     # CONTREDIT
    (3, "Fête patronale",
     "Come ogni anno, la festa si tiene il 15 agosto 2024 in piazza.",
     "2026-08-15", "2026-08-15", None, "pending"),                     # ANNÉE
    (4, "Saison culturelle",
     "Programme : 2 juin 2026, 15 juillet 2026, 30 septembre 2026. Réservations ouvertes.",
     AVENIR, AVENIR, None, "pending"),                                 # indécis
    (5, "Sortie au lac", "Entrée libre, chaussures de marche conseillées.",
     AVENIR, AVENIR, None, "pending"),                                 # muet
    # PASSÉ : une date fausse n'y envoie plus personne devant une porte close (règle 5).
    (6, "Concert de mai", "Le 21 août 2026 au kiosque.", PASSE, PASSE, None, "pending"),
    (7, "Déjà écartée", "Le 21 août 2026 au kiosque.",
     "2026-08-22", "2026-08-22", None, "rejected"),
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


print("\n──── 2 bis. le jour de la semaine ────")
_check("« sabato 7 maggio » est lu",
       verifier_dates.jours_nommes("venire a trovarci sabato 7 maggio dalle 16") ==
       {(5, 7): 5})
_check("le français aussi",
       verifier_dates.jours_nommes("Le vendredi 21 août 2026 à 21h") == {(8, 21): 4})
_check("un texte sans jour nommé ne dit rien",
       verifier_dates.jours_nommes("Le 21 août 2026 à 21h") == {})
# LE CAS 1069, RECOPIÉ : notre 07/05/2027 est un vendredi, la page dit samedi.
_check("le désaccord de jour est signalé",
       "samedi" in verifier_dates.verdict_jour({"2027-05-07"}, {(5, 7): 5}))
_check("et il DIT la dernière année qui collerait — 2022, donc l'annonce est vieille",
       "2022" in verifier_dates.verdict_jour({"2027-05-07"}, {(5, 7): 5}),
       verifier_dates.verdict_jour({"2027-05-07"}, {(5, 7): 5}))
_check("un jour qui COLLE ne dit rien — le cas près de la frontière",
       verifier_dates.verdict_jour({"2026-08-21"}, {(8, 21): 4}) == "")
_check("un jour nommé pour une AUTRE date ne juge pas la nôtre",
       verifier_dates.verdict_jour({"2026-08-21"}, {(9, 12): 5}) == "")

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
_check("la phrase du texte source est montrée pour la contradiction",
       "le texte dit : «" in sortie and "21 août 2026" in sortie, sortie[-1200:])
_check("et pour l'année périmée aussi", "15 agosto 2024" in sortie, sortie[-1200:])
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
           "Wed, 24 Jun 2026 13:44:10 +0000", AVENIR, AVENIR, "parsed", "pending",
           COLLECTE))
# Et le HTML brut, qui rendait l'extrait illisible (fiche 473 : « <time>20/05/2026</time> »)
c.execute("INSERT INTO events_raw (id, title, description, url_source, source_name, "
          " date_event_start, date_event_end, date_source, statut, scrape_date) "
          "VALUES (?,?,?,?,?,?,?,?,?,?)",
          (9, "Fête balisée", "<p>Rendez-vous le <time>21 août 2026</time> au kiosque.</p>",
           "https://exemple.fr/9", "Source officielle", "2026-08-22", "2026-08-22",
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
           "La visita agli studio è libera: ti basterà venire a trovarci sabato 7 maggio "
           "dalle 16.", "https://exemple.fr/10", "Paratissima (Torino)",
           "2027-05-07", "2027-05-07", "parsed", "pending", COLLECTE))
# Et le cas qui doit PASSER : jour annoncé, jour exact. Le 21/08/2026 est bien un vendredi.
c.execute("INSERT INTO events_raw (id, title, description, url_source, source_name, "
          " date_event_start, date_event_end, date_source, statut, scrape_date) "
          "VALUES (?,?,?,?,?,?,?,?,?,?)",
          (11, "Concert du vendredi", "Le vendredi 21 août 2026 à 21h au kiosque.",
           "https://exemple.fr/11", "Source officielle", "2026-08-21", "2026-08-21",
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
       "21 août 2026" in sortie_meta and "<time>" not in sortie_meta,
       sortie_meta[-900:])

print("\n──── 5. --en-ligne : d'abord ce que le public lit ────")
vues_ligne, _ = _sortie(["--en-ligne"])
_check("seule la contradiction PUBLIÉE remonte", vues_ligne == {2}, sorted(vues_ligne))

print("\n──── 6. --tout montre les indécises, sans les transformer en tâches ────")
vues_tout, sortie_tout = _sortie(["--tout"])
_check("l'indécise apparaît quand on la demande", 4 in vues_tout, sorted(vues_tout))
_check("la muette reste absente même de --tout", 5 not in vues_tout, sorted(vues_tout))

print(f"\n{'TOUT PASSE' if not echecs else str(echecs) + ' ÉCHEC(S)'}")
sys.exit(1 if echecs else 0)
