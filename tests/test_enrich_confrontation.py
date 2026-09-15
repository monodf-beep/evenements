#!/usr/bin/env python3
"""Fixture : la confrontation branchée sur l'enrichissement (`scripts/enrich.py`).

CE QUE CETTE FIXTURE DOIT PROUVER, et pourquoi chacune des trois choses compte.

**Que c'est la PAGE OFFICIELLE qui est lue, pas la matière agrégée.** C'est tout le sujet.
La fiche 2289 a été datée « du 14 au 17 » par 74.agendaculturel.fr pendant que
guitare-en-scene.com écrivait « du 14 au 18 » : confronter la fiche à la matière qui l'a
datée n'aurait jamais rien montré. Si un jour quelqu'un remplace `official_pages` par
`material` pour « avoir plus de texte », le premier test ci-dessous doit virer au rouge.

**Que rien ne remonte quand tout va bien.** Un garde-fou qui alimente une file même
lorsqu'il est content, c'est la file de 454 points dont 315 étaient des silences. Les cas
qui doivent PASSER sont donc au moins aussi nombreux ici que ceux qui doivent remonter
(CLAUDE.md règle 3 : « la fixture doit contenir un cas qui doit PASSER, choisi près de la
frontière »).

**Que ça ne bloque rien.** `_confrontation` rend None quand aucune page n'a été lue, et
`verser_confrontation` doit alors laisser le résultat d'enrichissement intact — pas une
clé de plus, pas une ligne de file. Une page injoignable ne doit jamais coûter une fiche.

Lancer : .venv/bin/python -m tests.test_enrich_confrontation
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.enrich import _confrontation, _texte_officiel, verser_confrontation  # noqa: E402
from utils import confronter as C  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# La fiche 2289 telle qu'elle était : datée depuis l'agrégateur, jamais depuis la page.
FICHE = {"id": 2289, "date_event_start": "2026-07-14", "date_event_end": "2026-07-17",
         "url_source": "https://74.agendaculturel.fr/festival/guitare-en-scene.html",
         "scrape_date": "2026-07-20 20:48:24"}

PAGE_OFFICIELLE = [{"url": "https://www.guitare-en-scene.com/",
                    "html": "<html><body><h1>Guitare en scène 2026</h1>"
                            "<p>Le festival se tiendra du 14 au 18 juillet 2026 à "
                            "Saint-Julien-en-Genevois.</p></body></html>"}]

print("──── 1. C'est la PAGE OFFICIELLE qui est lue ────")
texte = _texte_officiel(PAGE_OFFICIELLE)
_check("le texte officiel est extrait du HTML des pages lues",
       "14 au 18 juillet" in texte, texte[:120])
_check("… et il ne contient PAS la description de l'agrégateur (elle n'est pas passée)",
       "du 14 au 17" not in texte)

r = _confrontation(FICHE, PAGE_OFFICIELLE)
_check("2289 : la page officielle contredit la fiche → a_lire",
       r is not None and r["a_lire"], r)
_check("2289 : et le motif nomme les deux dates",
       "2026-07-18" in r["motifs"][0] and "2026-07-17" in r["motifs"][0], r["motifs"])

print("\n──── 2. LES CAS QUI DOIVENT PASSER ────")
_check("aucune page officielle lue → None (et surtout pas un signalement)",
       _confrontation(FICHE, []) is None)
_check("des pages sans HTML exploitable → None aussi",
       _confrontation(FICHE, [{"url": "https://x.fr", "html": ""}]) is None)

JUSTE = dict(FICHE, date_event_end="2026-07-18")
r_ok = _confrontation(JUSTE, PAGE_OFFICIELLE)
_check("une fiche JUSTE ne remonte pas", r_ok is not None and not r_ok["a_lire"], r_ok)
_check("… et son constat garde quand même le compte des cas présentés",
       r_ok["bornes"]["verdict"] == C.CONFIRME and r_ok["bornes"]["plages"] == 1, r_ok)

# LE CAS-FRONTIÈRE : une page d'institution qui liste son été. Elle ne parle pas QUE de
# nous ; sans borne commune, elle ne contredit personne.
AGENDA = [{"url": "https://ville.fr/agenda", "html":
           "<p>Été 2026 : du 3 au 5 juillet 2026, Fête du lac ; du 21 au 23 août 2026, "
           "Marché des potiers ; du 28 au 30 août 2026, Forum des associations.</p>"}]
r_amb = _confrontation(dict(FICHE, date_event_start="2026-08-01",
                            date_event_end="2026-08-02"), AGENDA)
_check("page d'agenda qui liste trois autres événements → rien ne remonte",
       not r_amb["a_lire"] and r_amb["bornes"]["verdict"] == C.AMBIGU, r_amb)

print("\n──── 3. CE QUI EST VERSÉ, ET OÙ ────")
res = {"article": {"titre": "Guitare en scène"}, "a_verifier": ["Tarifs non publiés."]}
verser_confrontation(res, r)
_check("le constat entier va dans enrich_data.confrontation",
       res["confrontation"]["bornes"]["verdict"] == C.CONTREDIT, res.get("confrontation"))
_check("le point de l'agent est CONSERVÉ", "Tarifs non publiés." in res["a_verifier"])
_check("le motif de date est ajouté à la file",
       any("2026-07-18" in x for x in res["a_verifier"]), res["a_verifier"])
_check("… et il dit d'où il vient (l'humain doit savoir quoi rouvrir)",
       any("page officielle relue" in x for x in res["a_verifier"]), res["a_verifier"])

res_ok = {"a_verifier": []}
verser_confrontation(res_ok, r_ok)
_check("une fiche juste : le constat est gardé, la file reste VIDE",
       res_ok["confrontation"] and res_ok["a_verifier"] == [], res_ok)

res_none = {"a_verifier": ["Horaires à confirmer."]}
verser_confrontation(res_none, None)
_check("aucune page lue : le résultat d'enrichissement est intact",
       "confrontation" not in res_none and res_none["a_verifier"] == ["Horaires à confirmer."],
       res_none)

# Un `a_verifier` absent ou rendu en CHAÎNE par le modèle ne doit pas faire tomber
# l'enrichissement — le reste du fichier est déjà défensif là-dessus (`sync_checks`).
res_str = {"a_verifier": "Un seul point, en chaîne."}
verser_confrontation(res_str, r)
_check("`a_verifier` rendu en chaîne par le modèle : absorbé, rien ne casse",
       isinstance(res_str["a_verifier"], list) and len(res_str["a_verifier"]) == 2, res_str)
res_abs = {}
verser_confrontation(res_abs, r)
_check("`a_verifier` absent : créé proprement",
       len(res_abs.get("a_verifier", [])) == 1, res_abs)

print(f"\n{'TOUT PASSE' if not echecs else str(echecs) + ' ÉCHEC(S)'}")
sys.exit(1 if echecs else 0)
