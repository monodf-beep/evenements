#!/usr/bin/env python3
"""Fixture : les trois garde-fous qui relisent la source (`utils/confronter.py`).

⚠️ CETTE FIXTURE DOIT PROUVER LES DEUX SENS. CLAUDE.md règle 3, écrite après le portillon
du 06/08 : « la fixture doit contenir un cas qui doit PASSER, choisi près de la frontière.
Celle du 06/08 n'avait que des cas qui confirmaient le design : elle est passée au vert sur
un portillon faux. Un test qui ne cherche qu'à se donner raison ne prouve rien. »

Les cas qui doivent PASSER sont donc les plus importants du fichier, et ils sont choisis à
l'endroit exact où un contrôle trop zélé se serait trompé :

  • une page d'institution qui liste quinze événements — elle ne contredit personne ;
  • une page permanente d'office de tourisme sans aucune année (le cas visitmondovi.it,
    nommé par le brief lui-même comme faux positif du contrôle « année ») ;
  • une source injoignable, qui n'est PAS une source morte ;
  • un `translated:` ou un `gmail:`, qui ne sont pas des URL à interroger.

Et les cas qui doivent ÉCHOUER sont les fiches réelles du 2026-08-12, avec le texte de leur
page officielle tel que le brief le cite.

Lancer : .venv/bin/python -m tests.test_confronter
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import confronter as C  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


REF = date(2026, 7, 20)


print("──── 1. (c) LES BORNES — les deux fiches réelles doivent être CONTREDITES ────")
# 2289 « Guitare en scène » : la page officielle dit 18, la fiche disait 17.
r = C.bornes_contre_la_page("2026-07-14", "2026-07-17",
                            "Festival Guitare en scène, du 14 au 18 Juillet 2026 "
                            "à Saint-Julien-en-Genevois.", REF)
_check("2289 : même début, fin différente → contredit", r["verdict"] == C.CONTREDIT, r)
_check("2289 : le motif NOMME les deux dates, il ne dit pas « écart »",
       "2026-07-18" in r["motif"] and "2026-07-17" in r["motif"], r["motif"])

# 2265 « Festa di San Savino » : la commune dit 8, la fiche disait 7.
r = C.bornes_contre_la_page("2026-07-04", "2026-07-07",
                            "Festa Patronale di San Savino. Dal 4 all'8 luglio 2026", REF)
_check("2265 : « Dal 4 all'8 » contre 4→7 → contredit", r["verdict"] == C.CONTREDIT, r)

print("\n──── 2. (c) LES CAS QUI DOIVENT PASSER ────")
_check("la page dit EXACTEMENT ce que nous disons → confirmé",
       C.bornes_contre_la_page("2026-07-14", "2026-07-18",
                               "du 14 au 18 juillet 2026", REF)["verdict"] == C.CONFIRME)

# LE cas-frontière : une page d'agenda qui liste plusieurs événements. Un contrôle naïf
# (« nos bornes ne sont pas dans la page ») crierait ici, et il crierait sur tout site
# d'institution. C'est le faux positif le plus probable du lot.
agenda = ("Programme de l'été : du 3 au 5 juillet 2026, Fête du lac ; "
          "du 14 au 18 juillet 2026, Guitare en scène ; "
          "du 21 au 23 août 2026, Marché des potiers.")
r = C.bornes_contre_la_page("2026-08-01", "2026-08-02", agenda, REF)
_check("page qui liste 3 événements et pas le nôtre → AMBIGU, jamais contredit",
       r["verdict"] == C.AMBIGU, r)
_check("… et elle est comptée (3 plages lues), pour qu'un zéro reste lisible",
       r["plages"] == 3, r)

r = C.bornes_contre_la_page("2026-07-14", "2026-07-18", agenda, REF)
_check("la même page, quand elle NOUS contient → confirmé", r["verdict"] == C.CONFIRME, r)

_check("page sans aucune date → MUET, jamais contredit",
       C.bornes_contre_la_page("2026-07-14", "2026-07-18",
                               "Le festival revient cet été.", REF)["verdict"] == C.MUET)
_check("fiche sans date → muet (une donnée manquante n'est pas une contradiction)",
       C.bornes_contre_la_page("", "", "du 14 au 18 juillet 2026", REF)["verdict"] == C.MUET)
_check("événement d'un seul jour confirmé par « le 9 juillet »… reste non contredit",
       C.bornes_contre_la_page("2026-07-09", "2026-07-09",
                               "Spectacle le 9 juillet 2026 à 21h", REF)["verdict"]
       in (C.CONFIRME, C.MUET))

print("\n──── 2 bis. (c) CE QUE LA MESURE DU 2026-08-16 A APPORTÉ ────")
# Passage sur 168 fiches publiées encore devant nous (leur propre description stockée) :
# 7 signalements, 4 événements, DEUX FAUX. Les quatre cas sont ici, deux qui doivent
# remonter et deux qui doivent PASSER — c'est la fixture bidirectionnelle de la règle 3.

# 6382 « Earthink Festival » — LE défaut du lot : notre propre matière annonce une plage,
# la base ne garde que son premier jour.
EARTHINK = ("Dal 27 agosto al 12 settembre 2026 torna Earthink Festival, che festeggia "
            "la sua XV edizione. La manifestazione si svolgerà tra l'Astigiano, la "
            "Valchiusella e Torino.")
r = C.bornes_contre_la_page("2026-08-27", "2026-08-27", EARTHINK, date(2026, 7, 8))
_check("6382 : la plage s'effondre sur son jour de début → verdict PROPRE (effondree)",
       r["verdict"] == C.EFFONDREE, r)
_check("6382 : le motif dit que la FIN manque, il ne fait pas arbitrer deux dates",
       "2026-09-12" in r["motif"] and "fin manque" in r["motif"], r["motif"])
_check("6382 : et il remonte bien à un humain", C.EFFONDREE in C.A_LIRE)

# 6969 « Achille Lauro » — LE faux positif jumeau, et le plus instructif : même forme
# (fiche d'un seul jour, plage dans le texte), mais la plage est celle du TOURNOI qui
# contient notre soirée, et le texte écrit notre jour noir sur blanc.
ATP = ("Le Nitto ATP Finals 2026, che si svolgeranno a Torino dal 15 al 22 novembre, "
       "avranno come prologo una serata-evento. Protagonista sarà Achille Lauro, che "
       "giovedì 12 novembre alle ore 21 trasformerà l'Inalpi Arena.")
r = C.bornes_contre_la_page("2026-11-12", "2026-11-12", ATP, date(2026, 7, 30))
_check("6969 : le jour écrit SEUL confirme la fiche, la plage voisine ne la contredit pas",
       r["verdict"] == C.CONFIRME, r)
_check("6969 : la plage du tournoi reste COMPTÉE (1 plage lue)", r["plages"] == 1, r)
_check("… et le jour isolé ne se lit QUE hors plage (sinon 6382 serait « confirmée »)",
       C.jours_isoles(EARTHINK, date(2026, 7, 8)) == set(),
       C.jours_isoles(EARTHINK, date(2026, 7, 8)))

# 14 « Matisse – Yves Saint Laurent » — la matière collectée est un item de newsletter qui
# parle d'un AUTRE festival. Une seule plage dans le texte : l'ancienne règle « une seule
# plage → aucune ambiguïté » criait ici, et elle avait tort.
NEWSLETTER = ("Le Nice Classic Festival 2026 se déroulera du 21 juillet au 09 août 2026 "
              "dans le Cloître du Monastère de Cimiez à Nice. Lire la suite...")
r = C.bornes_contre_la_page("2026-06-17", "2026-09-28", NEWSLETTER, date(2026, 6, 1))
_check("14 : une seule plage, mais AUCUNE borne commune → ambigu, jamais contredit",
       r["verdict"] == C.AMBIGU, r)
_check("14 : elle est comptée quand même (1 plage lue)", r["plages"] == 1, r)

# 1856 « Jazz Art » — le désaccord symétrique : même fin, autre début. Notre matière dit
# 16 juillet, la base disait 13 mai. La fin commune prouve qu'on parle du même festival.
r = C.bornes_contre_la_page("2026-05-13", "2026-08-20",
                            "Festival de jazz sur le toit terrasse de l'espace culturel "
                            "départemental Lympia à Nice, du 16 juillet au 20 août.",
                            date(2026, 5, 12))
_check("1856 : même fin, début différent → contredit", r["verdict"] == C.CONTREDIT, r)
_check("1856 : le motif NOMME les deux débuts",
       "2026-07-16" in r["motif"] and "2026-05-13" in r["motif"], r["motif"])

print("\n──── 3. (a) L'ANNÉE ────")
# 2319 « Ah ! La Belle Saison » : la page ne parle que de 2025, la fiche annonçait 2026.
r = C.annee_dans_la_source("2026-06-01",
                           "La belle saison 2025, 7ème édition. Spectacles en juin et "
                           "juillet 2025 au Théâtre des Collines.")
_check("2319 : la page ne cite que 2025 → absente", r["verdict"] == C.ABSENTE, r)
_check("2319 : le motif dit QUELLES années la page porte",
       "2025" in r["motif"], r["motif"])

# LE cas-frontière nommé par le brief : visitmondovi.it, page permanente sans année.
r = C.annee_dans_la_source("2026-07-19",
                           "La sagra si tiene ogni anno la terza domenica di luglio "
                           "nel centro storico.")
_check("page permanente SANS aucune année → muet, pas « absente » (cas visitmondovi)",
       r["verdict"] == C.MUET, r)
_check("l'année présente → confirmé",
       C.annee_dans_la_source("2026-07-19", "Edizione 2026 della sagra")["verdict"]
       == C.CONFIRME)
# Le cas 864 : une archive qui cite toutes les années. Le brief prévient que le contrôle
# « année » ne l'attrape pas — la fixture doit le CONSTATER, pas le maquiller.
r = C.annee_dans_la_source("2026-07-19", "Archivio news 2010 2011 2020 2023 2026")
_check("864 : une archive qui cite notre année passe ce contrôle (c'est l'URL qui l'attrape)",
       r["verdict"] == C.CONFIRME, r)

print("\n──── 4. (b) L'URL ────")


class _Rep:
    def __init__(self, code): self.status_code = code


_check("909 : 404 → absente",
       C.statut_source("https://www.opera-nice.org/agenda/chopin/20260918-1800/",
                       get=lambda u: _Rep(404))["verdict"] == C.ABSENTE)
_check("200 → confirmé",
       C.statut_source("https://x.fr/e", get=lambda u: _Rep(200))["verdict"] == C.CONFIRME)

# LES CAS QUI DOIVENT PASSER : ne jamais conclure à la mort d'une source qu'on n'a pas jointe.
def _boom(u):
    raise TimeoutError("délai dépassé")


r = C.statut_source("https://x.fr/e", get=_boom)
_check("réseau en panne → « injoignable », JAMAIS « absente »", r["verdict"] == "injoignable", r)
_check("500 côté serveur → injoignable, pas absente",
       C.statut_source("https://x.fr/e", get=lambda u: _Rep(500))["verdict"] == "injoignable")
_check("403 (mur d'accès) → absente, et on ne le franchit pas",
       C.statut_source("https://x.fr/e", get=lambda u: _Rep(403))["verdict"] == C.ABSENTE)
_check("`translated:845:it` n'est pas une URL → non_page",
       C.statut_source("translated:845:it", get=lambda u: _Rep(404))["verdict"] == "non_page")
_check("`gmail:` n'est pas une URL → non_page",
       C.statut_source("gmail:18f2c", get=lambda u: _Rep(404))["verdict"] == "non_page")
_check("Google News n'est pas une source à interroger → non_page",
       C.statut_source("https://news.google.com/rss/articles/x",
                       get=lambda u: _Rep(404))["verdict"] == "non_page")

print("\n──── 5. L'AGRÉGAT : ce qui remonte à un humain ────")
ev = {"date_event_start": "2026-07-14", "date_event_end": "2026-07-17",
      "url_source": "https://74.agendaculturel.fr/festival/guitare-en-scene.html",
      "scrape_date": "2026-07-20 20:48:24"}
r = C.confronter(ev, "Festival Guitare en scène, du 14 au 18 Juillet 2026",
                 get=lambda u: _Rep(200))
_check("la fiche 2289 remonte, avec un motif en français",
       r["a_lire"] and len(r["motifs"]) == 1, r["motifs"])

ev_ok = {"date_event_start": "2026-07-14", "date_event_end": "2026-07-18",
         "url_source": "https://x.fr/e", "scrape_date": "2026-07-20 20:48:24"}
_check("une fiche juste ne remonte PAS",
       C.confronter(ev_ok, "du 14 au 18 juillet 2026",
                    get=lambda u: _Rep(200))["a_lire"] is False)
_check("une page MUETTE ne fait pas remonter une fiche juste",
       C.confronter(ev_ok, "Le festival revient cet été.",
                    get=lambda u: _Rep(200))["a_lire"] is False)
_check("… mais le constat garde le compte des cas présentés (muet ≠ pas de page)",
       C.confronter(ev_ok, "Le festival revient cet été.",
                    get=lambda u: _Rep(200))["bornes"]["verdict"] == C.MUET)
_check("`ref` vient de la COLLECTE, pas d'aujourd'hui",
       C._ref_de_collecte({"scrape_date": "2026-07-20 20:48:24"}) == date(2026, 7, 20))

print(f"\n{'TOUT PASSE' if not echecs else str(echecs) + ' ÉCHEC(S)'}")
sys.exit(1 if echecs else 0)
