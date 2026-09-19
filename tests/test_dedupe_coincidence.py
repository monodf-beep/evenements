#!/usr/bin/env python3
"""Fixture : la règle de COÏNCIDENCE lieu + dates + jeton distinctif (2026-09-08).

⚠️ BASE JETABLE (init_db sur un fichier temporaire). Aucun réseau, aucun appel LLM.

D'OÙ ÇA VIENT. Le 08/09 au soir, Franck a vu deux pages EN LIGNE pour le même événement,
côte à côte sur le hub Vallée d'Aoste : WP#6413 « Pinocchio traverse les Alpes : quand un
bicentenaire ravive la Vallée d'Aoste » et WP#8193 « Pinocchio fait étape au Forte di Bard
pour les 200 ans de Carlo Collodi », 19–20 septembre, Bard. Mesuré : `same_story` ne
trouve qu'UN mot commun là où il en veut trois ; `_groups` ne lit ni la ville ni le lieu.
Trois autres paires en ligne ont été corbeillées à la main le même jour (Risò, Salone Auto
Torino, Orlando).

CE QU'ELLE VÉRIFIE — et pourquoi chaque cas est là :

  1. LA PAIRE RÉELLE (Pinocchio, titres exacts) est appariée, et le motif nomme le mot.
  2. ⚠️ LES CAS FRONTIÈRE QUI DOIVENT PASSER (règle 3 de CLAUDE.md) : une fixture qui ne
     contient que ce que la règle attrape prouve seulement qu'elle attrape.
       a. deux spectacles différents le même soir dans le même théâtre — titres qui
          portent tous deux le NOM DU LIEU (« Théâtre Charles Dullin ») : pas appariés ;
       b. deux expositions au même musée aux mêmes dates, mot commun « mostra » : non ;
       c. une fiche FR et sa traduction IT liée par translation_of : jamais — même quand
          le chemin des titres les rapprocherait (Salone Auto Torino) ;
       d. le même nom commun, mais deux jours différents : non (les dates sont exigées).
  3. Orlando (titres VRAISEMBLABLES, voir plus bas) : apparié. Risò : NON apparié, et
     c'est une LIMITE CONNUE, affichée mais pas comptée comme un échec — « riso » a quatre
     lettres, le plancher en veut cinq.
  4. dedupe.main : par défaut la paire est LISTÉE (log, --dry-run) et JAMAIS fusionnée ;
     avec --coincidence elle l'est. Le dry-run n'écrit rien dans les deux cas.
  5. verifier_doublons_publies --en-ligne : la paire Pinocchio publiée remonte, la sortie
     dit « par COÏNCIDENCE » avec le mot, la commande trash_by_ids est proposée, et le
     message Slack porte le motif. La même paire sur un événement TERMINÉ n'est pas une
     tâche (règle 5).

Lancer : .venv/bin/python -m tests.test_dedupe_coincidence
"""
import contextlib
import io
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db   # noqa: E402
import scripts.dedupe as dd                   # noqa: E402
import scripts.verifier_doublons_publies as vd  # noqa: E402

dd.DB_PATH = tmp
vd.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


AUJ = date.today()
FUTUR_D = (AUJ + timedelta(days=11)).isoformat()
FUTUR_F = (AUJ + timedelta(days=12)).isoformat()
PASSE_D = (AUJ - timedelta(days=40)).isoformat()
PASSE_F = (AUJ - timedelta(days=39)).isoformat()


def fiche(i, titre, terr, ville, lieu, debut, fin, translation_of=None, wp=None):
    return {"id": i, "title": titre, "territoire": terr, "ville": ville, "lieu": lieu,
            "date_event_start": debut, "date_event_end": fin,
            "translation_of": translation_of, "wp_post_id_as": wp,
            "url_source": f"https://src.example/{i}", "statut": "pending"}


# ── 1. la paire réelle ──────────────────────────────────────────────────────────────────
PINO_A = fiche(1, "Pinocchio traverse les Alpes : quand un bicentenaire ravive la Vallée d'Aoste",
               "vallee-aoste", "Bard", "Forte di Bard", "2026-09-19", "2026-09-20")
PINO_B = fiche(2, "Pinocchio fait étape au Forte di Bard pour les 200 ans de Carlo Collodi",
               "vallee-aoste", "Bard", "Forte di Bard", "2026-09-19", "2026-09-20")

print("──── 1. la paire Pinocchio (titres réels du 2026-09-08) ────")
_check("le chemin historique (titres) ne la voit PAS — c'est la mesure de départ",
       not dd._memes_titres(PINO_A, PINO_B))
motif = dd.coincidence_lieu_date(PINO_A, PINO_B)
_check("la coïncidence lieu + dates + jeton la voit", bool(motif), repr(motif))
_check("   et le motif nomme le mot qui l'a formée : « pinocchio »", "pinocchio" in motif, motif)
_check("   et la ville", "bard" in motif, motif)
_check("   et la période", "2026-09-19→2026-09-20" in motif, motif)
_check("_groups(coincidence=True) forme le groupe {1, 2}",
       [sorted(e["id"] for e in g) for g in dd._groups([PINO_A, PINO_B], coincidence=True)
        if len(g) > 1] == [[1, 2]])
_check("_groups() par défaut NE le forme PAS — le cron de 8h30 ne change pas de comportement",
       all(len(g) == 1 for g in dd._groups([PINO_A, PINO_B])))
_check("motif_groupe dit que le groupe tient par coïncidence, pas par le titre",
       "pinocchio" in dd.motif_groupe([PINO_A, PINO_B]))
_check("   et rend '' sur un groupe de titres jumeaux (chemin historique)",
       dd.motif_groupe([
           fiche(91, "Festival Musilac 2026 : programmation complète dévoilée", "savoie",
                 "Aix-les-Bains", "", "2026-07-10", "2026-07-13"),
           fiche(92, "Musilac 2026 dévoile sa programmation complète au bord du lac", "savoie",
                 "Aix-les-Bains", "", "2026-07-10", "2026-07-13")]) == "")

# ── 2. les cas frontière qui doivent PASSER ─────────────────────────────────────────────
print("\n──── 2. ⚠️ les cas frontière : ce que la règle NE doit PAS apparier ────")
# a. deux spectacles, même soir, même théâtre, le nom du lieu dans les deux titres
SPECT_A = fiche(11, "Le Malade imaginaire au Théâtre Charles Dullin", "savoie", "Chambéry",
                "Théâtre Charles Dullin", "2026-10-03", "2026-10-03")
SPECT_B = fiche(12, "Orchestre des Pays de Savoie au Théâtre Charles Dullin : soirée Brahms",
                "savoie", "Chambéry", "Théâtre Charles Dullin", "2026-10-03", "2026-10-03")
_check("a. deux spectacles différents le même soir au même théâtre : PAS appariés",
       dd.coincidence_lieu_date(SPECT_A, SPECT_B) == "",
       dd.coincidence_lieu_date(SPECT_A, SPECT_B))
_check("   (les mots du lieu — « charles », « dullin », « theatre » — ne comptent pas)",
       not (dd._jetons_distinctifs(SPECT_A["title"], frozenset({"theatre", "charles", "dullin"}))
            & dd._jetons_distinctifs(SPECT_B["title"], frozenset({"theatre", "charles", "dullin"}))))
_check("   alors que sans cette exclusion « charles »/« dullin » les auraient réunis — la "
       "garde est bien EXERCÉE, pas contournée par le hasard des titres",
       bool(dd._jetons_distinctifs(SPECT_A["title"]) & dd._jetons_distinctifs(SPECT_B["title"])))
# ⚠️ CE QUE CE CAS A RÉVÉLÉ EN L'ÉCRIVANT (2026-09-08) — et qui n'est PAS de cette règle.
# Le chemin HISTORIQUE (`same_story`, utils/sources.py:126 : trois mots significatifs
# communs) apparie ces deux spectacles PAR LES MOTS DU LIEU : « theatre », « charles »,
# « dullin ». Deux fiches pending avec le nom de la salle dans le titre, le même jour,
# fusionnent donc à 8h30. Mesuré ici, affiché, non compté : ce fichier teste la règle de
# coïncidence, et cacher ce défaut en changeant les titres serait une fixture qui ne
# cherche qu'à se donner raison. Le correctif appartient à `same_story` (hors de ce lot).
print(f"LIMITE CONNUE (chemin historique, hors de cette règle) : same_story apparie les deux "
      f"spectacles par les mots du lieu → _memes_titres={dd._memes_titres(SPECT_A, SPECT_B)}")
# Les mêmes deux soirées, titres SANS le nom de la salle — ce que l'affiche dit d'habitude.
# C'est cette forme-là qui sert aux volets 4 et 5, où l'on veut mesurer CETTE règle.
SPECT_C = dict(SPECT_A, title="Le Malade imaginaire, mise en scène de la Comédie itinérante")
SPECT_D = dict(SPECT_B, title="Orchestre des Pays de Savoie : soirée Brahms et Schumann")
_check("   deux spectacles au même théâtre le même soir, titres sans le nom du lieu : PAS "
       "appariés — ni par la coïncidence, ni par le titre",
       dd.coincidence_lieu_date(SPECT_C, SPECT_D) == "" and not dd._memes_titres(SPECT_C, SPECT_D))

# b. deux expositions, même musée, mêmes dates, « mostra » en commun
EXPO_A = fiche(21, "Mostra fotografica: Steve McCurry, Icons", "piemont", "Torino",
               "Palazzo Madama", "2026-10-01", "2027-01-10")
EXPO_B = fiche(22, "Mostra: i Macchiaioli e la luce del vero", "piemont", "Torino",
               "Palazzo Madama", "2026-10-01", "2027-01-10")
_check("b. deux expositions au même musée aux mêmes dates, mot commun « mostra » : PAS appariées",
       dd.coincidence_lieu_date(EXPO_A, EXPO_B) == "", dd.coincidence_lieu_date(EXPO_A, EXPO_B))

# c. FR + traduction IT liée — le chemin des TITRES les rapproche, la liaison l'interdit
SAL_FR = fiche(31, "Salone Auto Torino 2026 : trois jours de nouveautés au Valentino",
               "piemont", "Torino", "Parco del Valentino", "2026-09-25", "2026-09-27")
SAL_IT = fiche(32, "Salone Auto Torino 2026: tre giorni di novità al Valentino",
               "piemont", "Torino", "Parco del Valentino", "2026-09-25", "2026-09-27",
               translation_of=31)
_check("c. une fiche FR et sa traduction IT liée (translation_of) : jamais par coïncidence",
       dd.coincidence_lieu_date(SAL_FR, SAL_IT) == "")
_check("   paire_de_traduction vit dans dedupe et verifier l'importe (une seule définition)",
       vd.paire_de_traduction is dd.paire_de_traduction)
# La MÊME paire NON liée (deux fiches françaises, cas du 04-05/09) reste un doublon — par
# le chemin des TITRES (same_story dit oui : salone/auto/torino/valentino). La coïncidence,
# elle, ne la voit pas, et c'est voulu : les seuls noms propres communs sont la ville et le
# lieu, exclus par construction ; le reste diffère d'une langue à l'autre (trois/tre,
# jours/giorni). Une paire FR/IT non liée reste donc l'affaire du chemin historique.
SAL_FR2 = dict(SAL_IT, id=33, translation_of=None)
_check("   mais la même paire SANS liaison reste appariée par le TITRE (doublon du 04-05/09)",
       dd._memes_titres(SAL_FR, SAL_FR2))
_check("   et la coïncidence, seule, ne la verrait pas (ville et lieu exclus, le reste "
       "change de langue) — limite écrite dans docs/DEDOUBLONNAGE.md",
       dd.coincidence_lieu_date(SAL_FR, SAL_FR2) == "", dd.coincidence_lieu_date(SAL_FR, SAL_FR2))

# d. même mot, deux jours différents
_check("d. le même mot, deux jours différents : PAS appariés (les dates sont exigées)",
       dd.coincidence_lieu_date(PINO_A, dict(PINO_B, date_event_start="2026-09-26",
                                             date_event_end="2026-09-27")) == "")
_check("   ni une inclusion (l'exposition qui « contient » la visite guidée)",
       dd.coincidence_lieu_date(PINO_A, dict(PINO_B, date_event_end="2026-09-19")) == "")
_check("   ni deux fiches sans ville ni lieu, même mot, mêmes dates",
       dd.coincidence_lieu_date(dict(PINO_A, ville="", lieu=""),
                                dict(PINO_B, ville="", lieu="")) == "")
_check("   ni un lieu GÉNÉRIQUE partagé (« salle des fêtes ») sans la même ville",
       dd.coincidence_lieu_date(dict(PINO_A, ville="Margencel", lieu="Salle des fêtes"),
                                dict(PINO_B, ville="Draillant", lieu="Salle des fêtes")) == "")
_check("   mais un lieu PROPRE partagé suffit, même si la ville manque d'un côté",
       "lieu « forte di bard »" in dd.coincidence_lieu_date(dict(PINO_A, ville=""), PINO_B))
_check("   et la ville se compare sous sa forme canonique : « Aosta » = « Aoste »",
       "ville" in dd.coincidence_lieu_date(dict(PINO_A, ville="Aosta", lieu=""),
                                           dict(PINO_B, ville="Aoste", lieu="")))

# ── 3. Orlando et Risò ──────────────────────────────────────────────────────────────────
# TITRES VRAISEMBLABLES, PAS RELEVÉS : ce conteneur n'a pas la base. « Face à face –
# Orlando » est le titre réel de la fiche 917 (docs/CHANTIER_CONTENU_CASSE_2026-07-29.md,
# tests/test_confronter.py) ; l'autre est inventé. Pour Risò, seul « Risò 2026 » est attesté
# (docs/MESURES_2026-09-06.md, fiche 2232) ; la jumelle est inventée.
print("\n──── 3. Orlando (apparié) et Risò (limite connue) ────")
ORL_A = fiche(41, "Face à face – Orlando", "nice", "Nice", "Opéra Nice Côte d'Azur",
              "2026-09-29", "2026-10-06")
ORL_B = fiche(42, "Orlando de Haendel ouvre la saison lyrique à l'Opéra de Nice", "nice",
              "Nice", "Opéra Nice Côte d'Azur", "2026-09-29", "2026-10-06")
_check("Orlando : apparié, sur le mot « orlando »",
       "orlando" in dd.coincidence_lieu_date(ORL_A, ORL_B), dd.coincidence_lieu_date(ORL_A, ORL_B))
RISO_A = fiche(51, "Risò 2026", "piemont", "Vercelli", "", "2026-09-11", "2026-09-13")
RISO_B = fiche(52, "Risò 2026 : la fête du riz à Vercelli", "piemont", "Vercelli", "",
               "2026-09-11", "2026-09-13")
riso = dd.coincidence_lieu_date(RISO_A, RISO_B)
print(f"LIMITE CONNUE (non comptée) : Risò → coïncidence={riso!r} ; « riso » a 4 lettres, "
      f"le plancher JETON_MIN_LETTRES={dd.JETON_MIN_LETTRES}. Le chemin des titres, lui : "
      f"{dd._memes_titres(RISO_A, RISO_B)}.")

# ── 4. dedupe.main : candidat listé, jamais fusionné sans --coincidence ─────────────────
print("\n──── 4. dedupe.main : un CANDIDAT, pas une fusion aveugle ────")
conn = sqlite3.connect(tmp)
init_db(conn)
for f in (PINO_A, PINO_B, SPECT_C, SPECT_D, EXPO_A, EXPO_B):
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, territoire, ville, lieu, statut, "
        "date_event_start, date_event_end, description) VALUES (?,?,?,?,?,?,'pending',?,?,'')",
        (f["id"], f["title"], f["url_source"], f["territoire"], f["ville"], f["lieu"],
         f["date_event_start"], f["date_event_end"]))
conn.commit(); conn.close()


def etat():
    c = sqlite3.connect(tmp)
    rows = {i: (st, dup) for i, st, dup in
            c.execute("SELECT id, statut, duplicate_of FROM events_raw ORDER BY id")}
    c.close()
    return rows


buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = dd.main(["--dry-run"])
s = buf.getvalue()
_check("--dry-run rend 0 et n'écrit rien",
       rc == 0 and all(st == "pending" and dup is None for st, dup in etat().values()), etat())
_check("   il annonce 0 groupe fusionnable par le chemin des titres",
       "0 groupe(s) de doublons" in s, s[:200])
_check("   et LISTE le candidat Pinocchio, avec son motif",
       "CANDIDATS par coïncidence" in s and "ids 1, 2" in s and "pinocchio" in s, s)
_check("   sans y mettre les spectacles (11, 12) ni les expositions (21, 22)",
       "ids 11" not in s and "ids 21" not in s and "11, 12" not in s and "21, 22" not in s, s)

with contextlib.redirect_stdout(io.StringIO()):
    rc = dd.main([])
_check("le passage RÉEL par défaut ne fusionne RIEN (le cron de 8h30 reste ce qu'il était)",
       rc == 0 and all(st == "pending" and dup is None for st, dup in etat().values()), etat())

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = dd.main(["--dry-run", "--coincidence"])
s2 = buf.getvalue()
_check("--dry-run --coincidence annonce 1 groupe fusionnable et le marque « formé par coïncidence »",
       "1 groupe(s) de doublons" in s2 and "formé par coïncidence" in s2 and "pinocchio" in s2, s2)
_check("   et n'écrit toujours rien",
       all(st == "pending" and dup is None for st, dup in etat().values()), etat())

with contextlib.redirect_stdout(io.StringIO()):
    rc = dd.main(["--coincidence"])
apres = etat()
merged = [i for i, (st, _d) in apres.items() if st == "merged"]
_check("⚠️ le cas qui doit passer : --coincidence fusionne bien la paire annoncée, et elle seule",
       merged and len(merged) == 1 and {merged[0], apres[merged[0]][1]} == {1, 2}, apres)
_check("   les quatre autres fiches sont intactes",
       all(apres[i] == ("pending", None) for i in (11, 12, 21, 22)), apres)

# ── 5. verifier_doublons_publies : le rouvreur automatique de 9h50 ──────────────────────
print("\n──── 5. verifier_doublons_publies --en-ligne : la paire publiée remonte ────")
conn = sqlite3.connect(tmp)
conn.execute("DELETE FROM events_raw")   # base JETABLE : on repart propre pour ce volet
PUBLIEES = [
    # Pinocchio, telle qu'en production : deux pages, deux id WP, aucune liaison
    dict(PINO_A, id=6413, wp_post_id_as=6413, date_event_start=FUTUR_D, date_event_end=FUTUR_F),
    dict(PINO_B, id=8193, wp_post_id_as=8193, date_event_start=FUTUR_D, date_event_end=FUTUR_F),
    # les deux spectacles au même théâtre, publiés eux aussi : ne doivent pas remonter
    dict(SPECT_C, wp_post_id_as=7001, date_event_start=FUTUR_D, date_event_end=FUTUR_D),
    dict(SPECT_D, wp_post_id_as=7002, date_event_start=FUTUR_D, date_event_end=FUTUR_D),
    # la paire FR/IT liée, publiée : normale
    dict(SAL_FR, wp_post_id_as=7003, date_event_start=FUTUR_D, date_event_end=FUTUR_F),
    dict(SAL_IT, wp_post_id_as=7004, date_event_start=FUTUR_D, date_event_end=FUTUR_F),
    # la même coïncidence sur un événement TERMINÉ : pas une tâche (règle 5)
    dict(ORL_A, wp_post_id_as=7005, date_event_start=PASSE_D, date_event_end=PASSE_F),
    dict(ORL_B, wp_post_id_as=7006, date_event_start=PASSE_D, date_event_end=PASSE_F),
]
for f in PUBLIEES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, territoire, ville, lieu, statut, "
        "wp_post_id_as, translation_of, date_event_start, date_event_end, duplicate_of) "
        "VALUES (?,?,?,?,?,?,'published_sub',?,?,?,?,NULL)",
        (f["id"], f["title"], f["url_source"], f["territoire"], f["ville"], f["lieu"],
         f["wp_post_id_as"], f["translation_of"], f["date_event_start"], f["date_event_end"]))
conn.commit(); conn.close()

# AUCUN RÉSEAU : WordPress est remplacé par « tout est public ».
vd._etat = lambda wp_url, post_id: "public"
_envois: list[str] = []
import utils.slack as _slk  # noqa: E402
_slk.notify = lambda texte, blocks=None, urgent=False: _envois.append(texte) or True

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = vd.main(["--en-ligne", "--slack"])
out = buf.getvalue()
_check("rc=0 (lecture seule)", rc == 0)
_check("la paire Pinocchio publiée est signalée : [ 6413] et [ 8193] dans la sortie",
       "[ 6413]" in out and "[ 8193]" in out, out[:1500])
_check("   la sortie dit qu'elle tient par COÏNCIDENCE et nomme le mot",
       "par COÏNCIDENCE" in out and "pinocchio" in out, out)
_check("   le compteur « dont par coïncidence » vaut 1, à côté de son périmètre",
       "…dont par coïncidence   : 1" in out, out[:1200])
_check("   la commande de corbeille est proposée, entière (--statut rejected)",
       "trash_by_ids" in out and "--statut rejected" in out, out[-900:])
_check("les deux spectacles (11, 12) ne remontent PAS", "[   11]" not in out and "[   12]" not in out, out)
_check("la paire FR/IT liée (31, 32) ne remonte PAS et est comptée écartée",
       "[   31]" not in out and "écartés (paires FR/IT)  : 1" in out, out[:1500])
_check("la coïncidence sur un événement TERMINÉ (41, 42) n'est pas une tâche (règle 5)",
       "[   41]" not in out and "[   42]" not in out, out)
_check("le message Slack est parti et porte le motif de coïncidence",
       len(_envois) == 1 and "pinocchio" in _envois[0] and "WP#6413" in _envois[0]
       and "WP#8193" in _envois[0], _envois)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
