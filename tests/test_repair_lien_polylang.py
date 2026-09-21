#!/usr/bin/env python3
"""Fixture : une paire FR/IT du bon versant, mais que Polylang ne relie pas.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau, aucun LLM : la décision du script
est une fonction PURE (`verdict`), c'est elle qu'on éprouve, pas la plomberie HTTP.

D'OÙ ÇA VIENT (2026-09-21). Franck : « pourquoi j'ai des articles sans traduction ? ».
Mesuré depuis l'extérieur : 107 pages au versant français, 68 seulement portent un
`hreflang="it"`. WP#8137 « Carla With Love » et WP#8175, sa traduction italienne publiée
une heure après, existent toutes les deux, publiques, chacune du BON côté — et la page
française n'annonce aucune version italienne. Il ne manquait que le lien.

CE QUE LA FIXTURE SURVEILLE :
  1. ⚠️ LE CAS QUI DOIT PASSER, choisi près de la frontière : une paire SAINE dont le
     hreflang ne diffère que par le schéma et la barre finale. Un test d'égalité naïf la
     déclarerait « liée ailleurs » — le script reposerait alors un lien sur les 68 paines
     saines et noierait les 39 vraies dans son rapport ;
  2. la paire sans aucun hreflang sort, et c'est la SEULE que `--apply` toucherait ;
  3. deux pages du MÊME versant ne sont jamais reliées — leur geste est ailleurs ;
  4. une adresse en forme provisoire ne conclut rien (on s'abstient, on ne crie pas) ;
  5. un hreflang qui mène à une TROISIÈME page n'est pas recouvert en silence ;
  6. le périmètre (règle 5) écarte le passé, et une fiche SANS DATE y reste.

Lancer : .venv/bin/python -m tests.test_repair_lien_polylang
"""
import os
import sqlite3
import sys
import tempfile
import types
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Ce conteneur de session n'a pas python-dotenv (le VPS, lui, l'a). La fixture ne lit
# aucun `.env` : on pose un bouchon plutôt que de rendre le test dépendant de la machine.
if "dotenv" not in sys.modules:
    try:
        import dotenv  # noqa: F401
    except ModuleNotFoundError:
        faux = types.ModuleType("dotenv")
        faux.load_dotenv = lambda *a, **k: False
        sys.modules["dotenv"] = faux

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db          # noqa: E402
import scripts.repair_lien_polylang as rl           # noqa: E402

rl.DB_PATH = tmp
FUTUR = (date.today() + timedelta(days=20)).isoformat()
PASSE = (date.today() - timedelta(days=20)).isoformat()

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ══ LES EN-TÊTES RÉELS, RELEVÉS LE 21/09 SUR LE SITE ════════════════════════════════
#
# Recopiés d'une mesure, pas inventés : c'est la seule façon de savoir que l'expression
# régulière lit ce que Polylang écrit VRAIMENT. La paire WP#9366 ↔ WP#9507 était saine ce
# jour-là, WP#8137 ne portait aucun hreflang.
HTML_SAIN = '''<html lang="fr-FR"><head>
<link rel="alternate" href="https://agendasabauda.eu/evenement/smile-lorchestra/" hreflang="fr" />
<link rel="alternate" href="https://agendasabauda.eu/it/evenement/smile-lorchestra-2/" hreflang="it" />
<link rel="alternate" href="https://agendasabauda.eu/evenement/smile-lorchestra/" hreflang="x-default" />
</head></html>'''
# Même chose, attributs dans l'AUTRE ordre : Yoast et Polylang n'écrivent pas pareil selon
# la version. Dépendre d'un ordre qu'on n'a pas choisi, c'est se préparer un faux négatif.
HTML_SAIN_ORDRE_INVERSE = ('<link rel="alternate" hreflang="it" '
                           'href="https://agendasabauda.eu/it/evenement/smile-lorchestra-2/" />')
# WP#8137 : pas UNE ligne d'alternate. C'est le cas de Franck.
HTML_CARLA = '<html lang="fr-FR"><head><title>Carla With Love</title></head></html>'

print("──── ce que Polylang écrit est bien lu ────")
alts = rl.alternates(HTML_SAIN)
_check("les trois alternates sont lus", set(alts) == {"fr", "it", "x-default"}, alts)
_check("   et l'italien pointe la bonne page",
       alts["it"].endswith("/it/evenement/smile-lorchestra-2/"), alts)
_check("l'ordre inverse des attributs est lu aussi",
       rl.alternates(HTML_SAIN_ORDRE_INVERSE).get("it", "").endswith("smile-lorchestra-2/"),
       rl.alternates(HTML_SAIN_ORDRE_INVERSE))
_check("une page sans alternate n'en invente aucun", rl.alternates(HTML_CARLA) == {},
       rl.alternates(HTML_CARLA))

print("\n──── ⚠️ LE CAS QUI DOIT PASSER, pris près de la frontière ────")
# Une paire SAINE dont le hreflang ne diffère de l'adresse de la jumelle que par le
# schéma (http/https) et la barre finale. C'est la forme que rendent réellement deux
# sources différentes : l'API REST donne un `link` canonique, l'en-tête de la page peut
# porter l'autre schéma derrière un proxy. Une comparaison naïve dirait « lien ailleurs »
# sur les 68 paires saines du site — le rapport deviendrait illisible et le script
# reposerait des liens qui n'en ont pas besoin.
v = rl.verdict("fr", "it", rl.alternates(HTML_SAIN),
               "http://agendasabauda.eu/it/evenement/smile-lorchestra-2")
_check("une paire saine reste « deja_lie » malgré http/https et la barre finale",
       v == "deja_lie", v)
# Et le pendant : un paramètre de suivi collé à l'adresse ne doit pas non plus la faire
# passer pour une autre page.
v = rl.verdict("fr", "it", rl.alternates(HTML_SAIN),
               "https://agendasabauda.eu/it/evenement/smile-lorchestra-2/?utm_source=x")
_check("   ni un paramètre de requête", v == "deja_lie", v)

print("\n──── ce qui doit sortir, sort ────")
v = rl.verdict("fr", "it", rl.alternates(HTML_CARLA),
               "https://agendasabauda.eu/it/evenement/carla-2/")
_check("le cas Carla : bon versant des deux côtés, aucun hreflang → lien_absent",
       v == "lien_absent", v)
v = rl.verdict("fr", "it", rl.alternates(HTML_SAIN),
               "https://agendasabauda.eu/it/evenement/une-tout-autre-page/")
_check("un hreflang qui mène à une TROISIÈME page → lien_ailleurs (jamais recouvert)",
       v == "lien_ailleurs", v)

print("\n──── le versant est juste, le TEXTE non : on s'abstient ────")
# TROUVÉ EN PRODUCTION LE 21/09 À 16h04, deux heures après la livraison de ce script, et
# ma fixture ne pouvait pas l'attraper : elle ne contenait que des versants. WP#2340
# (jumelle de WP#745) a été republiée du versant ITALIEN en gardant son titre FRANÇAIS
# « Orlando de Haendel à l'Opéra Nice Côte d'Azur ». La première version aurait lié la
# paire : le sélecteur de langue aurait servi une page française aux lecteurs italiens, et
# `audit_langue_polylang` se serait taise (versant servi = langue demandée = 'it').
from utils.lang import effective_lang  # noqa: E402

JUM_ORLANDO = {   # texte RÉEL de WP#2340, recopié d'une mesure
    "title": "Orlando de Haendel à l'Opéra Nice Côte d'Azur",
    "description": "L'Opéra de Nice donne une nouvelle production d'Orlando, avec une "
                   "distribution internationale.",
    "territoire": "comte-de-nice"}
JUM_CARLA = {     # texte RÉEL de WP#8175, la jumelle italienne SAINE
    "title": "«Carla With Love»: Martina Arduino interpreta Carla Fracci ai Musei Reali "
             "di Torino",
    "description": "Lo spettacolo è in programma ai Musei Reali di Torino, con ingresso "
                   "su prenotazione.",
    "territoire": "piemont"}
# Près de la frontière : un titre italien fait presque uniquement de noms propres. C'est
# le cas où `detect_lang` a le moins de matière — et une abstention ici coûterait un lien
# qu'il fallait poser.
JUM_NOMS_PROPRES = {"title": "Paratissima 2026: Esterno Notte a Torino",
                    "description": "", "territoire": "piemont"}

_check("la jumelle du versant it dont le texte est FRANÇAIS n'est pas liée",
       rl.verdict("fr", "it", {}, "https://a/x", effective_lang(JUM_ORLANDO))
       == "jumelle_mauvaise_langue")
_check("   même quand un hreflang correct existe déjà (le verdict passe devant)",
       rl.verdict("fr", "it", rl.alternates(HTML_SAIN),
                  "https://agendasabauda.eu/it/evenement/smile-lorchestra-2/",
                  effective_lang(JUM_ORLANDO)) == "jumelle_mauvaise_langue")
_check("⚠️ la vraie jumelle italienne, elle, reste à lier (le cas qui doit passer)",
       rl.verdict("fr", "it", {}, "https://a/x", effective_lang(JUM_CARLA))
       == "lien_absent")
_check("⚠️ et un titre italien presque tout en noms propres aussi (frontière)",
       rl.verdict("fr", "it", {}, "https://a/x", effective_lang(JUM_NOMS_PROPRES))
       == "lien_absent")
_check("sans mesure de langue, le script se comporte comme avant (rétrocompatible)",
       rl.verdict("fr", "it", {}, "https://a/x", "") == "lien_absent")

print("\n──── ce qu'on ne relie JAMAIS ────")
# Les deux pages du même côté : c'est le cas Orlando (WP#745 et WP#2340, tous deux au
# versant français le 20/07). Les relier ne montrerait rien au lecteur — Polylang veut
# deux langues — et masquerait le vrai défaut, qui est une traduction publiée du mauvais
# côté. Son geste est `--retranslate`, pas un liage.
_check("deux pages du même versant → meme_versant, même si un hreflang traîne",
       rl.verdict("fr", "fr", rl.alternates(HTML_SAIN), "https://a/x") == "meme_versant")
_check("   et l'inverse aussi (deux pages italiennes)",
       rl.verdict("it", "it", {}, "https://a/x") == "meme_versant")
# Une adresse en forme provisoire (`?p=<id>`) ne dit rien du versant : `cote_du_permalien`
# rend '' et on s'abstient. Crier sur une donnée absente est le défaut du 18/08.
_check("une adresse provisoire ne conclut rien → versant_muet",
       rl.verdict("", "it", {}, "https://a/x") == "versant_muet")
_check("   dans un sens comme dans l'autre",
       rl.verdict("fr", "", {}, "https://a/x") == "versant_muet")

print("\n──── le versant vient d'UNE seule définition ────")
# Pas de second détecteur : `cote_du_permalien` est celle de audit_langue_polylang et du
# dédoublonnage. Deux copies d'une même question se contredisent un jour (21/09).
from utils.lang import cote_du_permalien  # noqa: E402
_check("cote_du_permalien lit le préfixe /it/",
       cote_du_permalien("https://agendasabauda.eu/it/evenement/x/") == "it")
_check("   et l'absence de préfixe = versant français",
       cote_du_permalien("https://agendasabauda.eu/evenement/x/") == "fr")
_check("   et une forme provisoire reste muette",
       cote_du_permalien("https://agendasabauda.eu/?p=8137") == "")

print("\n──── le périmètre : règle 5, et une fiche sans date n'est pas du passé ────")
# (id, translation_of, wp_post_id_as, debut, fin)
FICHES = [
    (1, None, 901, FUTUR, FUTUR),     # original à venir
    (2, 1, 902, FUTUR, FUTUR),        # sa jumelle → DANS le périmètre
    (3, None, 903, PASSE, PASSE),     # original terminé
    (4, 3, 904, PASSE, PASSE),        # sa jumelle → écartée
    (5, None, 905, "", ""),           # original SANS DATE : donnée manquante, pas du passé
    (6, 5, 906, "", ""),              # sa jumelle → DANS le périmètre
    (7, None, 907, FUTUR, FUTUR),     # original à venir…
    (8, 7, None, FUTUR, FUTUR),       # …jumelle sans numéro WP : pas notre question
]
conn = sqlite3.connect(tmp)
init_db(conn)
for eid, orig, wp, deb, fin in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, statut, wp_post_id_as, "
        "wp_permalink_as, date_event_start, date_event_end, duplicate_of, translation_of) "
        "VALUES (?,?,?,?,?,?,?,?,NULL,?)",
        (eid, f"Fiche {eid}", f"https://src/{eid}", "published_sub", wp,
         f"https://agendasabauda.eu/evenement/f{eid}/" if wp else "",
         deb, fin, orig))
conn.commit()
conn.row_factory = sqlite3.Row
lot = rl.paires(conn, None, tout=False)
tout = rl.paires(conn, None, tout=True)
ids = sorted(j["id"] for _, j in lot)
_check("la paire à venir est retenue", 2 in ids, ids)
_check("la paire SANS DATE est retenue (donnée manquante, pas événement fini)",
       6 in ids, ids)
_check("la paire terminée est écartée par défaut", 4 not in ids, ids)
_check("   mais --tout la ramène", 4 in sorted(j["id"] for _, j in tout),
       sorted(j["id"] for _, j in tout))
_check("une jumelle sans numéro WordPress n'est pas de ce script",
       8 not in ids and 8 not in sorted(j["id"] for _, j in tout), ids)
_check("--ids ne garde que la paire demandée",
       sorted(j["id"] for _, j in rl.paires(conn, [1], tout=False)) == [2],
       rl.paires(conn, [1], tout=False))
conn.close()

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
