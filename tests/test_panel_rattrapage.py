#!/usr/bin/env python3
"""Fixture : le rattrapage du panel. Base jetable, panel simulé — aucun appel réel.

CE QU'ELLE SURVEILLE, ET L'ORDRE COMPTE.

Ce script est le premier de la journée qui DÉPENSE de l'argent et qui touche à
`enrich_data`, la colonne où vivent les articles. Les deux risques ne sont donc pas les
mêmes que d'habitude :

  1. qu'un DRY-RUN appelle le modèle. Le panel est l'appel le plus répété du pipeline
     (plusieurs personas par fiche) : une simulation qui facture serait un piège, et on ne
     le découvrirait qu'à la facture ;
  2. qu'un ARTICLE soit réécrit. La charte l'interdit — le panel rend un verdict, jamais
     une publication. Le contrôle est explicite ici parce qu'aucune relecture de code ne
     rattrape une écriture qu'on n'a pas voulue ;
  3. qu'une fiche DÉJÀ jugée soit re-jugée : ce serait payer pour un second avis sur la
     même matière, et ne plus savoir lequel croire ;
  4. et seulement ensuite : que le verdict arrive bien là où publisher_as va le chercher.

Lancer : .venv/bin/python -m tests.test_panel_rattrapage
"""
import contextlib
import io
import json
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import panel_rattrapage  # noqa: E402
from scripts.enrich import PANEL_VERSION as _VERSION  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


tmp = Path(tempfile.mkdtemp(prefix="fixture-panelrat-"))
db = tmp / "fixture.db"
conn = sqlite3.connect(db)
init_db(conn)

AVENIR = (date.today() + timedelta(days=30)).isoformat()
PASSE = (date.today() - timedelta(days=30)).isoformat()

LONG = "Le festival réunit cette année quatre ensembles baroques. " * 12
COURT = "Marché de producteurs, place du village."


def _ed(corps="", panel=None):
    d = {"article": {"corps": corps}}
    if panel is not None:
        d["reader_panel"] = panel
    return json.dumps(d, ensure_ascii=False)


CAS = [
    # id, titre, enrich_data, début, fin, wp
    (1, "Festival baroque", _ed(LONG), AVENIR, AVENIR, 7001),          # à relire
    (2, "Nuits de la guitare", _ed(LONG), AVENIR, AVENIR, 7002),       # à relire
    (3, "Jugée par le panel actuel",
     _ed(LONG, {"verdict": "ok", "mean": 4, "version": _VERSION}),
     AVENIR, AVENIR, 7003),
    # ANCIEN INSTRUMENT, DEUX FORMES : sans marque du tout (avant le 13/08), et avec une
    # marque PÉRIMÉE (une version antérieure du même soir). Les deux doivent se rouvrir —
    # c'est le second qui manquait, et qui a bloqué la troisième mesure en production.
    (8, "Jugée sans marque", _ed(LONG, {"verdict": "revise", "mean": 2}),
     AVENIR, AVENIR, 7008),
    (9, "Jugée par une version périmée",
     _ed(LONG, {"verdict": "revise", "mean": 2, "version": "2026-08-13-a"}),
     AVENIR, AVENIR, 7009),
    (4, "Entrée de catalogue", _ed(COURT), AVENIR, AVENIR, 7004),
    (5, "Jamais rédigée", _ed(""), AVENIR, AVENIR, 7005),
    (6, "Concert de mai", _ed(LONG), PASSE, PASSE, 7006),              # règle 5
    (7, "Brouillon", _ed(LONG), AVENIR, AVENIR, None),                 # non publiée
]
for eid, titre, ed, deb, fin, wp in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, enrich_data, url_source, source_name, "
        " date_event_start, date_event_end, statut, wp_post_id_as) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (eid, titre, ed, f"https://exemple.fr/{eid}", "Source officielle",
         deb, fin, "pending", wp))
# UNE TRADUCTION de la fiche 1, dans le même lot. Elle ne doit PAS être jugée : on ne
# réécrit jamais une traduction, on corrige l'original et on retraduit.
conn.execute(
    "INSERT INTO events_raw (id, title, enrich_data, url_source, source_name, "
    " date_event_start, date_event_end, statut, wp_post_id_as, translation_of, "
    " translated_lang) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
    (10, "Festival barocco", _ed(LONG), "https://exemple.fr/10", "Source officielle",
     AVENIR, AVENIR, "pending", 7010, 1, "it"))
conn.commit()
conn.close()
panel_rattrapage.DB_PATH = db


def _sortie(argv=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        panel_rattrapage.main(argv or [])
    return buf.getvalue()


# LE .env, ET POURQUOI CE CONTRÔLE EST DE NIVEAU SOURCE. La première version de ce
# script ne chargeait pas le .env : le dry-run passait parfaitement (il n'appelle rien) et
# --apply s'arrêtait sur « clé absente » alors qu'elle était là. Aucune simulation ne peut
# attraper ça, puisque le défaut ne vit QUE sur le chemin payant. On vérifie donc la
# présence de l'appel dans le source — c'est faible, mais ça empêche de le retirer sans
# s'en apercevoir, et c'est mieux que le contrôle qui n'existait pas.
print("──── 0. la clé d'API doit être cherchée là où elle est ────")
_src = (ROOT / "scripts" / "panel_rattrapage.py").read_text(encoding="utf-8")
_check("le module charge le .env — sinon --apply échoue avec une clé pourtant présente",
       "load_dotenv(" in _src)

print("\n──── 0 bis. les infos pratiques données au panel ────")
from scripts.enrich import _bloc_infos_pratiques  # noqa: E402
b = _bloc_infos_pratiques({"date_event_start": "2026-09-18", "date_event_end": "2026-09-20",
                           "lieu": "Forte di Bard", "ville": "Bard",
                           "horaire": "21h00", "prix": "12 €"})
_check("la date, le lieu, l'horaire et le tarif sont montrés au persona",
       all(x in b for x in ("2026-09-18", "Forte di Bard", "21h00", "12 €")), b)
_check("   et la consigne interdit de reprocher ce que la fiche affiche déjà",
       "ne reproche PAS" in b, b)
# ON NE MEUBLE PAS. Un champ vide doit RESTER absent : c'est le seul cas où « il manque
# l'horaire » désigne encore quelque chose à faire.
b2 = _bloc_infos_pratiques({"date_event_start": "2026-09-18", "lieu": "", "ville": "",
                            "horaire": "", "prix": ""})
_check("un champ vide n'est pas inventé — il reste absent",
       "horaire" not in b2 and "tarif" not in b2 and "2026-09-18" in b2, b2)
_check("aucune info du tout → aucun bloc, pas un cadre vide",
       _bloc_infos_pratiques({}) == "")
# CE QUI MANQUE À LA FICHE NE DOIT PAS PESER SUR L'ARTICLE. Mesuré le 2026-08-13 : une
# fois la date et le lieu donnés, les personas se sont rabattus sur l'horaire et le
# tarif, absents de la base. Aucune réécriture ne les ferait apparaître — les compter
# contre l'article, c'est reprocher un silence dont il n'est pas responsable.
_check("un fait pratique absent est nommé comme un manque de la FICHE, pas de l'article",
       "manque à la FICHE, pas à l'article" in b, b)
# ⚠️ CONTRÔLE DE NIVEAU SOURCE, donc FRAGILE : la consigne est écrite sur plusieurs
# littéraux, et chercher la phrase entière échouait sur la coupure de ligne alors que le
# code était juste. On cherche donc un fragment qui tient sur UNE ligne. Même limite que
# le contrôle du .env plus haut, et même raison de le garder : il empêche qu'on retire la
# consigne sans s'en apercevoir.
from scripts.enrich import reader_review  # noqa: E402
import inspect  # noqa: E402
_src_rr = inspect.getsource(reader_review)
_check("et la distance ne fait plus baisser la note d'un local — elle n'est pas le fait "
       "de l'article",
       "NE DOIVENT PAS FAIRE BAISSER TA" in _src_rr)

print("\n──── 1. la sélection, et ce qu'elle ÉCARTE en le disant ────")
s = _sortie()
_check("les deux fiches sans verdict sont retenues", "[    1]" in s and "[    2]" in s)
_check("la fiche DÉJÀ jugée est écartée — on ne paie pas deux fois le même avis",
       "[    3]" not in s and "a déjà un verdict" in s)
_check("l'entrée de catalogue est écartée (le panel n'y a pas de prise)",
       "[    4]" not in s and "catalogue" in s)
_check("la fiche jamais rédigée est écartée", "[    5]" not in s and "rien à faire relire" in s)
_check("le PASSÉ est hors périmètre (règle 5)", "[    6]" not in s)
_check("une fiche non publiée est hors périmètre par défaut", "[    7]" not in s)
_check("… et --tout la fait entrer", "[    7]" in _sortie(["--tout"]))
_check("chaque écart est COMPTÉ, pas seulement subi", "écartées —" in s)
# CE QUE FRANCK A VU DANS LA SORTIE DES 42 : dix traductions relues en plus de leurs
# originaux. Le coût double, et surtout le reproche ne s'adresse à personne.
_check("une TRADUCTION n'est pas jugée — on corrige l'original, pas elle",
       "[   10]" not in s)
_check("   et l'écart est nommé, pas silencieux", "traduction —" in s)
_check("   même avec --rejuger : ce n'est pas une question de version",
       "[   10]" not in _sortie(["--rejuger"]))

# LE ROUVREUR, ET SA BORNE. Il doit rouvrir l'ancien instrument, et LUI SEUL.
_check("un verdict de l'ANCIEN panel est écarté par défaut… ", "[    8]" not in s)
_check("   …mais nommé comme tel, avec la commande qui le rouvre",
       "version PÉRIMÉE" in s and "--rejuger" in s)
s_rj = _sortie(["--rejuger"])
_check("--rejuger rouvre un verdict SANS marque", "[    8]" in s_rj)
_check("   et un verdict d'une version PÉRIMÉE — une provenance qui ne distingue pas "
       "les versions successives n'est qu'une demi-provenance", "[    9]" in s_rj)
_check("   le motif nomme la version périmée ET la courante", _VERSION in s)
_check("   et NE rouvre PAS un verdict de l'instrument actuel — ce serait le refus "
       "qui se rejoue à l'identique (règle 3)", "[    3]" not in s_rj)

print("\n──── 2. le dry-run ne doit RIEN appeler ni RIEN écrire ────")


class _Explose:
    """Toute construction de client anthropic pendant un dry-run est une faute."""
    def __init__(self, *a, **k):
        raise AssertionError("le dry-run a tenté de construire un client anthropic")


import anthropic  # noqa: E402
_vrai = anthropic.Anthropic
anthropic.Anthropic = _Explose
try:
    s = _sortie()
    _check("aucun client de modèle n'est construit en simulation", "DRY-RUN" in s)
finally:
    anthropic.Anthropic = _vrai

avant = sqlite3.connect(db).execute(
    "SELECT enrich_data FROM events_raw WHERE id=1").fetchone()[0]
_check("   et enrich_data n'a pas bougé", "reader_panel" not in avant)

print("\n──── 3. --apply : le verdict arrive, l'article ne bouge pas ────")
_appels = []


def _faux_panel(article, ev, client, model):
    _appels.append(ev["id"])
    return {"verdict": "revise", "mean": 2.0, "votes": 2,
            "reviews": [{"verdict": "revise", "manques": ["aucun nom d'artiste"]}]}


import scripts.enrich as _enrich  # noqa: E402
_vrai_panel = _enrich.reader_panel
_enrich.reader_panel = _faux_panel
anthropic.Anthropic = lambda *a, **k: object()
import os  # noqa: E402
os.environ["ANTHROPIC_API_KEY"] = "fixture"
try:
    s = _sortie(["--apply", "--cap", "1"])
finally:
    _enrich.reader_panel = _vrai_panel
    anthropic.Anthropic = _vrai

_check("une seule fiche relue quand --cap 1", len(_appels) == 1, f"→ {_appels}")
_check("   et le plafond est ANNONCÉ, jamais silencieux", "au-delà de --cap" in s)

c = sqlite3.connect(db)
apres = json.loads(c.execute("SELECT enrich_data FROM events_raw WHERE id=?",
                             (_appels[0],)).fetchone()[0])
_check("le verdict est rangé là où publisher_as va le chercher",
       apres.get("reader_panel", {}).get("verdict") == "revise")
_check("   avec un statut de révision explicite, jamais vide",
       apres["reader_panel"].get("revision") == "aucune")
# LE CONTRÔLE QUI COMPTE LE PLUS DE TOUT CE FICHIER.
_check("L'ARTICLE N'A PAS ÉTÉ RÉÉCRIT — un verdict n'est pas une publication",
       apres["article"]["corps"] == LONG)
_check("le bilan RECOMPTE en base au lieu d'annoncer une longueur de liste",
       "vérifié(s) en base" in s)
_check("et il rappelle qu'aucun article n'a été touché",
       "AUCUN ARTICLE N'A ÉTÉ RÉÉCRIT" in s)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
