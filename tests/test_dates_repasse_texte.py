#!/usr/bin/env python3
"""Fixture : la passe texte de dates.py se rejoue, et n'efface jamais rien.

Franck, le 2026-08-11 au soir, devant la file « À compléter » à 68 : « on a toujours trop
de tâches ». La cause n'était pas la collecte, c'était une SÉLECTION.

La passe 1 de `scripts/dates.py` lit la date dans le titre et la description. Elle est
gratuite et instantanée. Elle ne passait pourtant qu'UNE FOIS par fiche : sa requête
portait sur `date_source` vide, or dès le premier échec cette colonne passait à 'none',
et la fiche sortait définitivement de son champ de vision.

Entre-temps la matière change — `dedupe` fusionne une fiche mieux titrée, `enrich` écrit
un `article_title` qui porte la date, le parseur s'améliore. Le parseur d'aujourd'hui lit
sans hésiter « les 8 et 9 août » dans le titre de la fiche 3083, affichée « date ? »
depuis des semaines. Et l'absence de date est un CERCLE VICIEUX : sans elle, la règle 5
interdit de classer la fiche en « passé » — donc elle ne quitte aucune file. Le Tour de
France Femmes, terminé le 9 août, occupait encore l'écran le 11 pour cette seule raison.

CE QUE LA FIXTURE PROTÈGE EN PREMIER : qu'en se rejouant, la passe n'EFFACE rien. C'est
le risque que la relance introduit et que l'ancienne version ne courait pas. Une fiche qui
n'a qu'une date de fin (« jusqu'au 20 septembre ») verrait cette fin réécrite à vide au
premier passage où le parseur échoue.

Lancer : .venv/bin/python -m tests.test_dates_repasse_texte
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import dates as dates_mod  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


tmp = Path(tempfile.mkdtemp(prefix="fixture-dates-"))
db = tmp / "events.db"
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
init_db(conn)
dates_mod.DB_PATH = db
dates_mod.ensure_columns(conn)
for col in ("article_title TEXT", "translation_of INTEGER"):
    try:
        conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col}")
    except sqlite3.OperationalError:
        pass

CAS = [
    # (id, titre, description, article_title, date_source, start, end)
    # 1 — LE CAS DU 11/08 : déjà déclarée « non datable », mais son titre porte la date.
    (1, "Le Tour de France Femmes 2026 s'achève à Nice les 8 et 9 août", "", "",
     "none", "", ""),
    # 2 — datable seulement par le titre d'ARTICLE (le titre brut du flux est muet).
    (2, "Communiqué de presse", "", "Cinéma de plein air : programmation du 11 au 29 août",
     "none", "", ""),
    # 3 — n'a QU'UNE date de fin, et son texte n'est plus datable : à ne pas effacer.
    (3, "Exposition permanente", "", "", "parsed", "", "2026-09-20"),
    # 4 — déjà datée : hors sélection, rien ne doit bouger.
    (4, "Concert du 5 mai", "", "", "page", "2026-05-05", "2026-05-05"),
    # 5 — vraiment indatable : doit rester à 'none' pour que la passe page la reprenne.
    (5, "Nice Jazz Fest", "Trois soirées au Théâtre de Verdure.", "", "", "", ""),
    # 6 — TRADUCTION : ses dates sont copiées de l'original, jamais re-dérivées.
    (6, "Il Tour de France Femmes si conclude l'8 e 9 agosto", "", "", "", "", ""),
    # 7 — « jusqu'au… » : le texte ne donne QUE la fin. La fiche gagne quelque chose, mais
    # elle reste incomplète — et c'est exactement ce que le compteur annonçait à tort
    # comme « datée » le 2026-08-11 (64 annoncées, 10 réelles).
    (7, "Un été à Albé, saison patrimoniale jusqu'au 20 septembre", "", "", "", "", ""),
]
for eid, titre, desc, art, src, s, e in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, article_title, "
        "date_source, date_event_start, date_event_end) VALUES (?,?,?,?,?,?,?,?)",
        (eid, titre, desc, f"https://exemple.fr/{eid}", art, src, s, e))
conn.execute("UPDATE events_raw SET translation_of=1 WHERE id=6")
conn.commit()
conn.close()


def _lire(eid):
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    r = c.execute("SELECT date_event_start s, date_event_end e, date_source src "
                  "FROM events_raw WHERE id=?", (eid,)).fetchone()
    c.close()
    return r["s"], r["e"], r["src"]


dates_mod.main(["--no-fetch", "--no-llm", "--no-republish"])

print("──── la fiche que l'ancienne sélection ne regardait plus ────")
_check("fiche 1 datée depuis son titre malgré date_source='none'",
       _lire(1)[:2] == ("2026-08-08", "2026-08-09"), str(_lire(1)))
_check("… et sa provenance est 'parsed'", _lire(1)[2] == "parsed", str(_lire(1)))

print("\n──── le titre d'article, quand le titre brut est muet ────")
_check("fiche 2 datée depuis article_title", _lire(2)[:2] == ("2026-08-11", "2026-08-29"),
       str(_lire(2)))
_check("… avec une provenance distincte, pour pouvoir y revenir",
       _lire(2)[2] == "parsed_article", str(_lire(2)))

print("\n──── CE QUI NE DOIT SURTOUT PAS ARRIVER : effacer ────")
_check("fiche 3 : la date de fin seule survit à une passe qui échoue",
       _lire(3)[1] == "2026-09-20", str(_lire(3)))
_check("fiche 4 : une fiche déjà datée n'est pas touchée",
       _lire(4)[:2] == ("2026-05-05", "2026-05-05"), str(_lire(4)))
_check("fiche 4 : sa provenance non plus", _lire(4)[2] == "page", str(_lire(4)))

print("\n──── les autres ────")
_check("fiche 5 indatable → 'none', pour que la passe page la reprenne",
       _lire(5) == ("", "", "none"), str(_lire(5)))
# La traduction ne doit JAMAIS être datée par le parseur : son titre italien passé à un
# parseur écrit pour le français a déjà produit des dates fausses (Jazz Art : 2 mois
# d'écart ; Matisse : 1 mois, incident du 2026-08-02). Elle reçoit ses dates par COPIE de
# son original — et c'est un effet secondaire heureux de cette correction : dater la
# fiche 1 date aussi sa traduction, dans le même run.
_check("fiche 6 (traduction) non datée par le TEXTE mais copiée de son original",
       _lire(6)[2] == "copie-traduction", str(_lire(6)))
_check("… et la copie porte bien les dates de l'original",
       _lire(6)[:2] == _lire(1)[:2], f"{_lire(6)} vs {_lire(1)}")

print("\n──── « jusqu'au 20 septembre » : gagné une fin, TOUJOURS incomplète ────")
_check("fiche 7 a bien reçu sa date de fin", _lire(7)[1] == "2026-09-20", str(_lire(7)))
_check("… mais elle n'a PAS de date de début, et le compteur ne doit pas la dire datée",
       _lire(7)[0] == "", str(_lire(7)))

print("\n──── on rejoue : rien ne se dégrade ────")
avant = [_lire(i) for i in range(1, 8)]
dates_mod.main(["--no-fetch", "--no-llm", "--no-republish"])
_check("deuxième passage identique au premier",
       [_lire(i) for i in range(1, 8)] == avant,
       str([_lire(i) for i in range(1, 8)]))

print("\n──── le début lu sur la page, CORROBORÉ par la fin connue ────")
# « date de début, date de fin ! » (Franck, 2026-08-11). Une page porte toujours plusieurs
# dates : celle de l'article, celles des autres événements, les horaires. On ne cherche
# donc pas « une date », on cherche une PLAGE qui se termine à la date qu'on connaît déjà.
PAGE = ("Publié le 3 mars 2026 par la rédaction · "
        "L'exposition est visible du 12 juin au 20 septembre 2026 au musée · "
        "Ouvert de 10h à 18h · Prochainement : concert du 5 octobre 2026 · "
        "© Ville de Nice 2026")
_check("plage dont la fin correspond → le début est rendu",
       dates_mod.debut_depuis_page(PAGE, "2026-09-20") == "2026-06-12",
       dates_mod.debut_depuis_page(PAGE, "2026-09-20"))
_check("aucune plage ne finit à cette date → rien, surtout pas la première date venue",
       dates_mod.debut_depuis_page(PAGE, "2026-11-30") == "",
       dates_mod.debut_depuis_page(PAGE, "2026-11-30"))
_check("sans fin connue, on ne cherche même pas",
       dates_mod.debut_depuis_page(PAGE, "") == "")
_check("page vide → rien", dates_mod.debut_depuis_page("", "2026-09-20") == "")
AMBIGU = ("Le parcours est ouvert du 12 juin au 20 septembre 2026 · "
          "Les ateliers, eux, se tiennent du 1 juillet au 20 septembre 2026")
_check("DEUX débuts possibles pour la même fin → on ne rend RIEN",
       dates_mod.debut_depuis_page(AMBIGU, "2026-09-20") == "",
       dates_mod.debut_depuis_page(AMBIGU, "2026-09-20"))
_check("un début postérieur à la fin est refusé",
       dates_mod.debut_depuis_page("du 25 septembre au 20 septembre 2026", "2026-09-20") == "")

print("\n──── la passe page ne doit RIEN effacer ────")
# Le piège : la sélection de la passe page vient d'être élargie aux fiches qui ont déjà
# une date de fin. Son UPDATE réécrivait les deux colonnes avec ('','') quand la page ne
# donnait rien — il aurait donc effacé la fin à chaque page muette.
_vrai_fetch = dates_mod.fetch_event_dates


def _fetch_muet(url, _capture=None):
    if _capture is not None:
        _capture["text"] = "Une page sans la moindre date exploitable."
    return ("", "", "nodate")


def _fetch_corroborant(url, _capture=None):
    if _capture is not None:
        _capture["text"] = ("Saison patrimoniale · L'édition se tient "
                            "du 4 juillet au 20 septembre 2026 · Entrée libre")
    return ("", "", "nodate")


dates_mod.fetch_event_dates = _fetch_muet
dates_mod.main(["--no-llm", "--no-republish"])
_check("fiche 7 : page muette, sa date de fin est INTACTE", _lire(7)[1] == "2026-09-20",
       str(_lire(7)))
_check("fiche 3 : idem, la fin seule survit à la passe page", _lire(3)[1] == "2026-09-20",
       str(_lire(3)))

_check("fiche 7 : lue sans résultat, elle passe à 'nodate' (plafond de tentatives et "
       "ré-armement s'en occupent) — elle n'est donc PAS relue au run suivant",
       _lire(7)[2] == "nodate", str(_lire(7)))

# Fiche neuve pour le cas corroboré : la 7 vient d'être marquée 'nodate', et c'est le bon
# comportement — une page relue en boucle le même jour ne donnerait pas autre chose.
c = sqlite3.connect(db)
c.execute("INSERT INTO events_raw (id, title, description, url_source, date_source, "
          "date_event_start, date_event_end) VALUES (8,'Saison patrimoniale','', "
          "'https://exemple.fr/8','parsed','','2026-09-20')")
c.commit()
c.close()

dates_mod.fetch_event_dates = _fetch_corroborant
dates_mod.main(["--no-llm", "--no-republish"])
_check("fiche 8 : le début est trouvé sur la page et corroboré par la fin",
       _lire(8)[0] == "2026-07-04", str(_lire(8)))
_check("… la fin connue n'a pas bougé", _lire(8)[1] == "2026-09-20", str(_lire(8)))
_check("… et la provenance le dit", _lire(8)[2] == "page_corroboree", str(_lire(8)))
dates_mod.fetch_event_dates = _vrai_fetch

print("\n──── la passe page : règle 5, et les candidats d'abord ────")
# Le run du 2026-08-11 à 14h41 : 717 fiches ré-armées, 200 pages lues, ZÉRO résultat —
# alors que le même chemin avait daté 31 fiches sur 49 une heure plus tôt. Le plafond
# prenait les 200 PREMIÈRES par numéro, donc les plus vieilles ; les fiches qui ont une
# date de fin, seules à pouvoir servir la corroboration, étaient enterrées vers la 600ᵉ
# place. Un plafond sans tri lit toujours le même fond de tiroir.
c = sqlite3.connect(db)
c.execute("INSERT INTO events_raw (id,title,description,url_source,date_source,"
          "date_event_start,date_event_end) VALUES "
          "(30,'Vieille fiche terminée','','https://exemple.fr/30','none','','2020-01-01'),"
          "(31,'Fiche sans aucune date','','https://exemple.fr/31','none','',''),"
          "(32,'Fin connue à venir','','https://exemple.fr/32','none','','2027-09-20')")
c.commit()
c.close()
_lus = []
dates_mod.fetch_event_dates = (lambda url, _capture=None:
                               (_lus.append(url), ("", "", "nodate"))[1])
dates_mod.main(["--no-llm", "--no-republish"])
dates_mod.fetch_event_dates = _vrai_fetch
_check("la fiche dont la FIN est passée n'est pas lue (règle 5)",
       "https://exemple.fr/30" not in _lus, str(_lus))
_check("la fiche SANS aucune date reste lue — absence n'est pas passé",
       "https://exemple.fr/31" in _lus, str(_lus))
_check("la fiche qui a une fin à venir est lue EN PREMIER (candidate à la corroboration)",
       _lus and _lus[0] == "https://exemple.fr/32", str(_lus))

print("\n──── le bilan de fin de run compte des DATES, pas des étiquettes ────")
# Il comptait `date_source IN ('parsed','page','llm','copie-traduction')` : une liste en
# dur, donc un compteur qui se périme dès qu'on ajoute une provenance. Le 11/08, l'arrivée
# de 'parsed_article' et 'page_corroboree' a fait TOMBER le total de 1635 à 1611 dans le
# run même où 31 fiches venaient d'être datées.
c = sqlite3.connect(db)
c.row_factory = sqlite3.Row
bilan = dates_mod._bilan_dates(c)
reel_debut = c.execute("SELECT COUNT(*) n FROM events_raw WHERE "
                       "COALESCE(date_event_start,'') <> '' AND statut != 'merged'"
                       ).fetchone()["n"]
c.close()
_check("le total 'début' correspond aux fiches qui ont vraiment une date de début",
       bilan["debut"] == reel_debut, f"{bilan} vs {reel_debut}")
_check("une provenance inédite n'échappe pas au compteur",
       bilan["debut"] >= 1 and _lire(8)[2] == "page_corroboree", str(bilan))
_check("les trois familles couvrent tout le stock",
       bilan["debut"] + bilan["fin_seule"] + bilan["rien"] ==
       (lambda: (lambda cc: cc.execute(
           "SELECT COUNT(*) FROM events_raw WHERE statut != 'merged'").fetchone()[0])(
               sqlite3.connect(db)))(), str(bilan))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s). Base jetable : {tmp}")
sys.exit(1 if echecs else 0)
