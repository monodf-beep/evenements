#!/usr/bin/env python3
"""Fixture : deux fiches au titre IDENTIQUE sont le même événement (2026-09-21).

⚠️ BASE JETABLE (init_db sur un fichier temporaire). Aucun réseau, aucun appel LLM.

D'OÙ ÇA VIENT. Le 21/09, Franck envoie deux captures du hub Vallée d'Aoste : « problème de
duplication ». Trois cartes « Marché au Fort » aux mêmes dates à Bard (WP#6435, 9523,
9533), deux « Lo Pan Ner » (WP#9371, 9373). Relevé le même jour par l'API WordPress :
huit doublons FR encore devant nous, sur 188 fiches en ligne et non terminées.

LA MESURE QUI A TOUT DIT — et c'est le témoin ROUGE de cette fixture, §1 : sur les titres
tels qu'ils sont EN BASE, `same_story("Marché au Fort 2026", "Marché au Fort 2026")` rend
False. Deux titres strictement identiques ne s'apparient pas, parce que le seuil de trois
mots significatifs a été écrit pour des titres rédigés de dix mots. Le digest de
publication du 19/09 imprimait les deux lignes l'une sous l'autre sans rien dire :
« [5608] Marché au Fort 2026 — WP#9523 » / « [5612] Marché au Fort 2026 — WP#9533 ».

CE QUE LA FIXTURE VÉRIFIE :

  1. LE TÉMOIN ROUGE : sur quatre titres réels, `same_story(t, t)` est False. Sans ce
     témoin, on ne saurait pas que la règle ajoutée a jamais eu quelque chose à réparer
     (journal du 14/09 : « un témoin ne prouve rien s'il n'a jamais été rouge »).
  2. LES CINQ PAIRES RÉELLES sont appariées par `_groups()` SANS option (le cron de
     8h30), avec les ville/lieu/dates réels lus dans la base de production :
     Marché au Fort, Lo Pan Ner, La Foire des Alpes, We Want Jazz (casse), Diálogos
     (point final). Les deux dernières prouvent que la normalisation sert ; la
     troisième que le millésime doit compter comme mot porteur.
  3. ⚠️ LES CAS FRONTIÈRE QUI DOIVENT PASSER (règle 3 de CLAUDE.md) — une fixture qui ne
     contient que ce que la règle attrape prouve seulement qu'elle attrape :
       a. deux « Marché de Noël » le même week-end à Annecy et à Chambéry : PAS appariés
          (deux communes connues et différentes) ;
       b. le même « Marché de Noël » aux mêmes dates dans la MÊME commune : apparié —
          c'est le vrai doublon, et la garde du (a) ne doit pas l'emporter avec ;
       c. deux « Visite guidée » aux mêmes dates dans la même ville : PAS appariés (le
          titre ne porte aucun mot qui NOMME quoi que ce soit) ;
       d. titre identique, dates différentes : non (deux éditions, deux fiches) ;
       e. titre identique, une fiche sans date : non (donnée manquante, règle 5) ;
       f. une fiche et sa traduction IT liée par translation_of : jamais.
  4. Le motif est une PHRASE lisible, pas un booléen, et il nomme le titre et la période.
  5. `verifier_doublons_publies --en-ligne` remonte la paire PUBLIÉE et propose la
     commande de corbeille — c'est par là que les fiches déjà en ligne reviennent.

Lancer : .venv/bin/python -m tests.test_dedupe_titre_identique
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
from utils.sources import same_story          # noqa: E402

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
FUTUR_D = (AUJ + timedelta(days=19)).isoformat()
FUTUR_F = (AUJ + timedelta(days=20)).isoformat()
AUTRE_D = (AUJ + timedelta(days=54)).isoformat()


def fiche(i, titre, terr, ville, lieu, debut, fin, translation_of=None, wp=None):
    return {"id": i, "title": titre, "territoire": terr, "ville": ville, "lieu": lieu,
            "date_event_start": debut, "date_event_end": fin,
            "translation_of": translation_of, "wp_post_id_as": wp,
            "url_source": f"https://src.example/{i}", "statut": "pending"}


# ════════════════════════════════════════════════════════════════════════════════════════
# 1. LE TÉMOIN ROUGE — ce que le code faisait la veille
# ════════════════════════════════════════════════════════════════════════════════════════
print("──── 1. témoin rouge : les détecteurs d'avant ne voyaient RIEN ────")
for t in ("Marché au Fort 2026", "Lo Pan Ner", "La Foire des Alpes 2026", "We Want Jazz 2026"):
    _check(f"same_story(« {t} », lui-même) = False — le trou mesuré le 21/09",
           same_story(t, t) is False)

# ════════════════════════════════════════════════════════════════════════════════════════
# 2. LES PAIRES RÉELLES — ville, lieu et dates lus dans la base de production le 21/09
# ════════════════════════════════════════════════════════════════════════════════════════
MF_A = fiche(5608, "Marché au Fort 2026", "vallee-aoste", "Bard",
             "Borgo medievale di Bard / Marché au Fort", "2026-10-10", "2026-10-11")
MF_B = fiche(5612, "Marché au Fort 2026", "vallee-aoste", "Bard",
             "Bourg médiéval de Bard / Marché au Fort", "2026-10-10", "2026-10-11")
PN_A = fiche(5464, "Lo Pan Ner", "vallee-aoste", "Valle d'Aosta (vari comuni)",
             "Forni comunitari nei villaggi", "2026-10-17", "2026-10-18")
PN_B = fiche(5465, "Lo Pan Ner", "vallee-aoste", "Vallée d'Aoste",
             "Fours communautaires des villages", "2026-10-17", "2026-10-18")
FA_A = fiche(5609, "La Foire des Alpes 2026", "vallee-aoste", "Saint-Christophe",
             "Arena Croix-Noire", "2026-11-07", "2026-11-08")
FA_B = fiche(5613, "La Foire des Alpes 2026", "vallee-aoste", "Saint-Christophe",
             "Arène Croix-Noire", "2026-11-07", "2026-11-08")
# Casse et ponctuation : les deux seules différences de ces paires-là, en ligne le 21/09.
WJ_A = fiche(5551, "We want Jazz 2026", "vallee-aoste", "Saint-Vincent",
             "Grand Hôtel Billia", "2026-02-20", "2026-10-31")
WJ_B = fiche(5719, "We Want Jazz 2026", "vallee-aoste", "Saint-Vincent",
             "Grand Hôtel Billia", "2026-02-20", "2026-10-31")
DI_A = fiche(5607, "Mostre: Diálogos.", "vallee-aoste", "Fénis, Aosta, Saint-Pierre, Introd",
             "MAV - Museo dell'Artigianato Valdostano", "2026-09-15", "2027-02-07")
DI_B = fiche(5721, "Mostre: Diálogos", "vallee-aoste", "Fénis, Aosta, Saint-Pierre, Introd",
             "MAV - Museo dell'Artigianato Valdostano", "2026-09-15", "2027-02-07")

print("\n──── 2. les paires réelles, appariées par le cron de 8h30 (aucune option) ────")
for nom, a, b in (("Marché au Fort  [5608]/[5612]", MF_A, MF_B),
                  ("Lo Pan Ner      [5464]/[5465]", PN_A, PN_B),
                  ("Foire des Alpes [5609]/[5613]", FA_A, FA_B),
                  ("We Want Jazz    [5551]/[5719] (casse)", WJ_A, WJ_B),
                  ("Diálogos        [5607]/[5721] (point final)", DI_A, DI_B)):
    motif = dd.titre_identique(a, b)
    _check(f"{nom} : appariée", bool(motif), repr(motif))
    _check(f"    et `_groups()` SANS option la forme — c'est le cron de 8h30",
           [sorted(e["id"] for e in g) for g in dd._groups([a, b]) if len(g) > 1]
           == [sorted([a["id"], b["id"]])])

# ════════════════════════════════════════════════════════════════════════════════════════
# 3. LES CAS FRONTIÈRE — ceux qui doivent PASSER, choisis au plus près de la règle
# ════════════════════════════════════════════════════════════════════════════════════════
print("\n──── 3. cas frontière ────")

# (a) La seule famille de faux positifs que « titre identique + mêmes dates » laisse
#     passer : une fête calendaire célébrée le même week-end dans deux communes.
NOEL_ANNECY = fiche(11, "Marché de Noël", "savoie", "Annecy", "Place Notre-Dame",
                    FUTUR_D, FUTUR_F)
NOEL_CHAMBERY = fiche(12, "Marché de Noël", "savoie", "Chambéry", "Place Saint-Léger",
                      FUTUR_D, FUTUR_F)
noms_communes, _ = dd._communes()
_check("Annecy et Chambéry sont bien des communes CONNUES (sinon le cas ne prouve rien)",
       dd._plie("Annecy") in noms_communes and dd._plie("Chambéry") in noms_communes)
_check("(a) « Marché de Noël » à Annecy et à Chambéry, mêmes dates : PAS apparié",
       not dd.titre_identique(NOEL_ANNECY, NOEL_CHAMBERY))
_check("    et `_groups()` les laisse séparés",
       all(len(g) == 1 for g in dd._groups([NOEL_ANNECY, NOEL_CHAMBERY])))

# (b) …mais le même marché dans la MÊME commune est le doublon qu'on cherche. Si la garde
#     du (a) emportait ce cas-là, elle protégerait la règle contre son propre travail.
NOEL_ANNECY_BIS = fiche(13, "Marché de Noël", "savoie", "Annecy", "Place Notre-Dame",
                        FUTUR_D, FUTUR_F)
_check("(b) « Marché de Noël » deux fois à Annecy, mêmes dates : APPARIÉ",
       bool(dd.titre_identique(NOEL_ANNECY, NOEL_ANNECY_BIS)))

# (c) Un titre qui ne nomme rien : deux visites guidées le même jour dans la même ville
#     sont deux visites, pas deux fiches de la même.
VG_A = fiche(21, "Visite guidée", "piemont", "Torino", "Palazzo Madama", FUTUR_D, FUTUR_D)
VG_B = fiche(22, "Visite guidée", "piemont", "Torino", "Palazzo Reale", FUTUR_D, FUTUR_D)
_check("(c) « Visite guidée » : PAS apparié — aucun mot porteur dans le titre",
       not dd.titre_identique(VG_A, VG_B))
_check("    et « Concerto » non plus",
       not dd.titre_identique(
           fiche(23, "Concerto", "piemont", "Torino", "Auditorium", FUTUR_D, FUTUR_D),
           fiche(24, "Concerto", "piemont", "Torino", "Conservatorio", FUTUR_D, FUTUR_D)))
_check("    alors que « Lo Pan Ner », lui, porte deux mots porteurs",
       dd._mots_porteurs("lo pan ner") == {"pan", "ner"},
       dd._mots_porteurs("lo pan ner"))
# Le millésime compte : « La Foire des Alpes 2026 » n'a QUE des mots génériques (« foire »
# est un type d'événement, « alpes » un lieu) et se faisait refuser — fixture rouge du 21/09.
_check("    et « la foire des alpes 2026 » ne tient QUE par son millésime",
       dd._mots_porteurs("la foire des alpes 2026") == {"2026"},
       dd._mots_porteurs("la foire des alpes 2026"))
_check("    tandis que « visite guidee » n'a ni mot porteur ni millésime",
       dd._mots_porteurs("visite guidee") == set())

# (d) Deux éditions du même événement : même titre, dates différentes. La règle ne les
#     rapproche pas — c'est `adopter_edition` qui s'en occupe, pas la fusion.
ED_A = fiche(31, "Lo Pan Ner", "vallee-aoste", "Vallée d'Aoste", "", FUTUR_D, FUTUR_F)
ED_B = fiche(32, "Lo Pan Ner", "vallee-aoste", "Vallée d'Aoste", "", AUTRE_D, AUTRE_D)
_check("(d) titre identique mais dates différentes : PAS apparié",
       not dd.titre_identique(ED_A, ED_B))

# (e) Une fiche sans date est une donnée manquante, pas un doublon (règle 5).
SD_A = fiche(41, "Lo Pan Ner", "vallee-aoste", "Vallée d'Aoste", "", FUTUR_D, FUTUR_F)
SD_B = fiche(42, "Lo Pan Ner", "vallee-aoste", "Vallée d'Aoste", "", "", "")
_check("(e) titre identique, une fiche SANS date : PAS apparié",
       not dd.titre_identique(SD_A, SD_B))

# (f) Deux langues d'un même événement : deux pages Polylang, jamais un doublon. Le cas
#     est réel : une traduction IT garde souvent le titre propre tel quel.
TR_FR = fiche(51, "Lo Pan Ner", "vallee-aoste", "Vallée d'Aoste", "", FUTUR_D, FUTUR_F)
TR_IT = fiche(52, "Lo Pan Ner", "vallee-aoste", "Valle d'Aosta", "", FUTUR_D, FUTUR_F,
              translation_of=51)
_check("(f) une fiche et sa traduction liée : JAMAIS appariées",
       not dd.titre_identique(TR_FR, TR_IT))
_check("    et `_groups()` les laisse séparées",
       all(len(g) == 1 for g in dd._groups([TR_FR, TR_IT])))

# ════════════════════════════════════════════════════════════════════════════════════════
# 4. LE MOTIF — une phrase qu'un humain lit, pas un booléen
# ════════════════════════════════════════════════════════════════════════════════════════
print("\n──── 4. le motif ────")
m = dd.titre_identique(PN_A, PN_B)
_check("le motif nomme le titre", "lo pan ner" in m, m)
_check("   et la période", "2026-10-17→2026-10-18" in m, m)
_check("   et se dit « titre identique », pas « coïncidence »", m.startswith("titre identique"), m)
_check("motif_groupe rend '' : le groupe tient bien par les TITRES, le compteur "
       "« dont par coïncidence » ne doit pas le compter",
       dd.motif_groupe([PN_A, PN_B]) == "")

# ════════════════════════════════════════════════════════════════════════════════════════
# 5. LES FICHES DÉJÀ PUBLIÉES — le chemin de retour (cron 9h50)
# ════════════════════════════════════════════════════════════════════════════════════════
print("\n──── 5. verifier_doublons_publies --en-ligne sur la paire PUBLIÉE ────")
conn = sqlite3.connect(tmp)
init_db(conn)
PUB = [dict(MF_A, wp_post_id_as=9523, statut="published_sub"),
       dict(MF_B, wp_post_id_as=9533, statut="published_sub"),
       # Le décor : une paire FR/IT liée, qui ne doit pas remonter.
       dict(TR_FR, wp_post_id_as=9371, statut="published_sub"),
       dict(TR_IT, wp_post_id_as=9401, statut="published_sub")]
for f in PUB:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, territoire, ville, lieu, statut, "
        "wp_post_id_as, translation_of, date_event_start, date_event_end, duplicate_of) "
        "VALUES (?,?,?,?,?,?,'published_sub',?,?,?,?,NULL)",
        (f["id"], f["title"], f["url_source"], f["territoire"], f["ville"], f["lieu"],
         f["wp_post_id_as"], f["translation_of"], f["date_event_start"], f["date_event_end"]))
conn.commit()
conn.close()

# AUCUN RÉSEAU : WordPress est remplacé par « tout est public ».
vd._etat = lambda wp_url, post_id: "public"

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = vd.main(["--en-ligne"])
out = buf.getvalue()
_check("rc=0 (lecture seule)", rc == 0)
_check("la paire Marché au Fort publiée est signalée : [ 5608] et [ 5612]",
       "[ 5608]" in out and "[ 5612]" in out, out[:1500])
_check("   la commande de corbeille est proposée, entière (--statut rejected)",
       "trash_by_ids" in out and "--statut rejected" in out, out[-900:])
_check("la paire FR/IT liée ne remonte PAS et est comptée écartée",
       "[   51]" not in out and "écartés (paires FR/IT)" in out, out[:1500])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
