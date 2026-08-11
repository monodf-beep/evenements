#!/usr/bin/env python3
"""Fixture : lire POUR DE BON les données structurées d'une page officielle.

Franck, 2026-08-11 : « j'aimerais qu'on soit implacable au niveau automatisation de la
collecte des informations officielles AVANT de passer par les LLM pour interpréter. Pour
l'instant de nombreuses informations manquent, le tableau de bord déborde de demandes de
complétion. »

Ce que le dépôt faisait tenait en deux expressions régulières cherchant la chaîne
`"startDate":"…"` dans du HTML. Tout ce qui s'écarte de cette forme exacte était
invisible — à commencer par le bloc `@graph` que produisent Yoast et Rank Math, c'est-à-
dire la forme de la majorité des sites WordPress, donc d'une bonne part de nos sources.

Les formes testées ici ne sont pas inventées : ce sont celles qu'on rencontre.
  • `@graph` (Yoast/Rank Math) — l'Event est noyé parmi Organization, WebPage, Place ;
  • guillemets échappés — JSON-LD injecté depuis une chaîne par un builder de page ;
  • tableau de plusieurs objets dans un seul <script> ;
  • microdata `itemprop` — l'autre forme que schema.org autorise, tout aussi valable.

ET LE CAS QUI DOIT RENDRE VIDE : une page de PROGRAMME qui déclare dix concerts. Y
prendre une date, c'est prendre celle d'un autre événement — l'accident exact de WP#6798.
« Implacable » veut dire implacable à COLLECTER ce qui est déclaré, jamais à deviner ce
qui ne l'est pas.

Lancer : .venv/bin/python -m tests.test_jsonld
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import jsonld as J  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


YOAST = '''<script type="application/ld+json">{"@context":"https://schema.org",
"@graph":[{"@type":"Organization","name":"Musée X"},{"@type":"WebPage","name":"Page"},
{"@type":"Event","name":"Concert d'été","startDate":"2026-09-12T20:30:00+02:00",
"endDate":"2026-09-12T23:00:00+02:00","location":{"@type":"Place","name":"Cour du Château",
"address":{"@type":"PostalAddress","addressLocality":"Annecy"}},
"image":["https://x.fr/affiche.jpg"]}]}</script>'''

ECHAPPE = ('<script type="application/ld+json">{\\"@type\\":\\"Event\\",'
           '\\"name\\":\\"Expo\\",\\"startDate\\":\\"2026-10-01\\"}</script>')

TABLEAU = ('<script type="application/ld+json">[{"@type":"BreadcrumbList"},'
           '{"@type":"ExhibitionEvent","name":"Milo Manara","startDate":"2026-10-04",'
           '"endDate":"2027-01-15"}]</script>')

PROGRAMME = '''<script type="application/ld+json">[
{"@type":"Event","name":"Concert A","startDate":"2026-09-01"},
{"@type":"Event","name":"Concert B","startDate":"2026-09-08"}]</script>'''

DOUBLON = '''<script type="application/ld+json">{"@type":"Event","name":"Récital",
"startDate":"2026-09-01"}</script>
<script type="application/ld+json">{"@type":"MusicEvent","name":"Récital",
"startDate":"2026-09-01","location":{"@type":"Place","name":"Auditorium"}}</script>'''

ORGA = '<script type="application/ld+json">{"@type":"Organization","name":"Ville"}</script>'
CASSE = '<script type="application/ld+json">{ ceci n\'est pas du JSON }</script>'
MICRO = '''<div itemscope itemtype="https://schema.org/Event">
<meta itemprop="startDate" content="2026-11-05T19:00"/>
<span itemprop="location">Théâtre Charles Dullin</span>
<span itemprop="addressLocality">Chambéry</span></div>'''

print("──── formes réelles de JSON-LD ────")
c = J.champs(YOAST)
_check("@graph Yoast : début", c.get("date_event_start") == "2026-09-12", str(c))
_check("@graph Yoast : fin", c.get("date_event_end") == "2026-09-12", str(c))
_check("@graph Yoast : lieu", c.get("lieu") == "Cour du Château", str(c))
_check("@graph Yoast : ville", c.get("ville") == "Annecy", str(c))
_check("@graph Yoast : image", c.get("url_image") == "https://x.fr/affiche.jpg", str(c))

_check("guillemets échappés lus",
       J.champs(ECHAPPE).get("date_event_start") == "2026-10-01", str(J.champs(ECHAPPE)))

t = J.champs(TABLEAU)
_check("tableau + ExhibitionEvent : une expo est un événement",
       t.get("date_event_start") == "2026-10-04" and t.get("date_event_end") == "2027-01-15",
       str(t))

d = J.champs(DOUBLON)
_check("même événement décrit deux fois (thème + Yoast) → pas d'ambiguïté",
       d.get("date_event_start") == "2026-09-01", str(d))

print("\n──── ce qui doit rendre VIDE ────")
_check("page de PROGRAMME (deux concerts distincts) → rien", J.champs(PROGRAMME) == {},
       str(J.champs(PROGRAMME)))
_check("organisation seule → rien", J.champs(ORGA) == {}, str(J.champs(ORGA)))
_check("JSON illisible → rien, et aucune exception", J.champs(CASSE) == {},
       str(J.champs(CASSE)))
_check("page sans données structurées → rien", J.champs("<html></html>") == {})

print("\n──── microdata ────")
m = J.champs_microdata(MICRO)
_check("microdata : début", m.get("date_event_start") == "2026-11-05", str(m))
_check("microdata : lieu", m.get("lieu") == "Théâtre Charles Dullin", str(m))
_check("microdata : ville", m.get("ville") == "Chambéry", str(m))

print("\n──── types_presents : la question que le premier diagnostic n'a pas posée ────")
_check("les @type de la page sont énumérés",
       "event" in J.types_presents(YOAST) and "organization" in J.types_presents(YOAST),
       str(J.types_presents(YOAST)))
_check("une page sans Event le dit", J.types_presents(ORGA) == ["organization"],
       str(J.types_presents(ORGA)))

# ── Le gain profite à TOUTE la chaîne, pas au seul script de moisson ───────────
# dates.dates_from_page et venues.venue_from_page sont appelées par le cron de datation,
# par l'auto-complétion du back-office et par la moisson. Les brancher sur le parseur
# fait bénéficier tous ces chemins du même élargissement, au lieu de le réserver au
# dernier arrivé — et les formes historiques doivent continuer de passer.
print("\n──── dates.py et venues.py utilisent le parseur ────")
from scripts.dates import dates_from_page  # noqa: E402
from scripts.venues import venue_from_page  # noqa: E402

_check("dates_from_page lit le @graph Yoast",
       dates_from_page(YOAST)[:2] == ("2026-09-12", "2026-09-12"), str(dates_from_page(YOAST)))
_check("venue_from_page lit le @graph Yoast",
       venue_from_page(YOAST)[:2] == ("Cour du Château", "Annecy"), str(venue_from_page(YOAST)))
_check("dates_from_page lit les microdata",
       dates_from_page(MICRO)[0] == "2026-11-05", str(dates_from_page(MICRO)))
_check("venue_from_page lit les microdata",
       venue_from_page(MICRO)[0] == "Théâtre Charles Dullin", str(venue_from_page(MICRO)))
# CONTRE-ÉPREUVE : la forme historique (regex) doit continuer de passer — le parseur
# s'ajoute devant, il ne remplace pas.
ANCIEN = ('<html>"startDate": "2026-07-05" "location": {"name": "Salle X", '
          '"address": {"addressLocality": "Chambéry"}}</html>')
_check("la forme historique passe toujours (le parseur s'AJOUTE)",
       dates_from_page(ANCIEN)[0] == "2026-07-05"
       and venue_from_page(ANCIEN)[:2] == ("Salle X", "Chambéry"),
       f"{dates_from_page(ANCIEN)} / {venue_from_page(ANCIEN)}")
_check("une page sans rien ne rend rien",
       dates_from_page("<html></html>") == ("", "", "")
       and venue_from_page("<html></html>") == ("", "", ""))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
