#!/usr/bin/env python3
"""Fixture : un paragraphe resté en français dans une traduction italienne est
retraduit À PART avant de refuser l'article (translate_events.translate_article).

Incident du 23/09/2026 : `--retranslate` sur Plaisirs de Culture, sept jumelles
refusées par le portillon de langue — des phrases françaises entières recopiées au
milieu d'un corps italien (« Cette initiative s'inscrit dans la quatorzième édition de
Plaisirs de Culture… »). Refuser était juste ; rejouer l'appel complet aurait refusé à
l'identique. La seconde passe n'envoie QUE les paragraphes restés.

Cas couverts, dans les deux sens :
  - traduction correcte du premier coup → UN seul appel, rien de plus (doit PASSER) ;
  - paragraphe resté, seconde passe réussie → article accepté, paragraphe remplacé à
    sa place, markdown et autres paragraphes intacts ;
  - seconde passe qui rend encore du français → REFUS, comme avant ;
  - seconde passe au mauvais nombre d'entrées → REFUS, rien d'inventé.

Aucun réseau (faux client). Lancer : .venv/bin/python -m tests.test_traduction_seconde_passe
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.translate_events as te  # noqa: E402
from utils import usage  # noqa: E402

usage.record_message = lambda *a, **k: None

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


class FauxClient:
    """Rend, dans l'ordre, les réponses données ; retient les prompts reçus."""
    def __init__(self, reponses):
        self.reponses = list(reponses)
        self.prompts = []
        self.messages = self

    def create(self, model, max_tokens, messages):
        self.prompts.append(messages[0]["content"])
        txt = self.reponses.pop(0)
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=txt)])


SOURCE = json.dumps({"article": {
    "titre": "Au fil des ondes",
    "chapo": "La Maison de Mosse accueille une exposition sur les télécommunications.",
    "corps": ("## Une histoire valdôtaine\n\n"
              "La Maison de Mosse elle-même raconte l'histoire : cette maison forte du XIVe "
              "siècle accueille les visiteurs pendant tout le week-end.\n\n"
              "Cette initiative s'inscrit dans la quatorzième édition de Plaisirs de Culture "
              "en Vallée d'Aoste, avec des visites guidées pour les familles.")},
    "sources": ["https://exemple.it"]}, ensure_ascii=False)

IT_TITRE = "Sul filo delle onde"
IT_CHAPO = "La Maison de Mosse ospita una mostra sulla storia delle telecomunicazioni."
IT_P1 = ("La Maison de Mosse stessa racconta la storia: questa casaforte del XIV secolo "
         "accoglie i visitatori per tutto il fine settimana.")
IT_P2 = ("L'iniziativa fa parte della quattordicesima edizione di Plaisirs de Culture en "
         "Vallée d'Aoste, con visite guidate per le famiglie.")
FR_P2 = ("Cette initiative s'inscrit dans la quatorzième édition de Plaisirs de Culture en "
         "Vallée d'Aoste, avec des visites guidées pour les familles.")


def _premier(p2):
    return json.dumps({"titre": IT_TITRE, "chapo": IT_CHAPO,
                       "corps": f"## Una storia valdostana\n\n{IT_P1}\n\n{p2}"},
                      ensure_ascii=False)


# ── 1. Du premier coup : un seul appel (le cas qui doit PASSER sans détour) ──────────
c = FauxClient([_premier(IT_P2)])
r = te.translate_article(c, "m", SOURCE, "it")
_check("traduction correcte : acceptée", r is not None)
_check("traduction correcte : UN seul appel", len(c.prompts) == 1, str(len(c.prompts)))

# ── 2. Paragraphe resté, seconde passe réussie ──────────────────────────────────────
c = FauxClient([_premier(FR_P2), json.dumps([IT_P2], ensure_ascii=False)])
r = te.translate_article(c, "m", SOURCE, "it")
_check("paragraphe resté + seconde passe : acceptée", r is not None)
if r:
    corps = json.loads(r)["article"]["corps"]
    _check("le paragraphe est remplacé À SA PLACE",
           corps == f"## Una storia valdostana\n\n{IT_P1}\n\n{IT_P2}", repr(corps))
    _check("les champs non textuels sont recopiés",
           json.loads(r)["sources"] == ["https://exemple.it"])
_check("la seconde passe n'envoie QUE le paragraphe resté",
       len(c.prompts) == 2 and FR_P2 in c.prompts[1] and IT_P1 not in c.prompts[1])

# ── 3. Seconde passe qui rend encore du français → refus ────────────────────────────
c = FauxClient([_premier(FR_P2), json.dumps([FR_P2], ensure_ascii=False)])
_check("seconde passe encore en français : REFUS",
       te.translate_article(c, "m", SOURCE, "it") is None)

# ── 4. Mauvais nombre d'entrées → refus, rien d'inventé ─────────────────────────────
c = FauxClient([_premier(FR_P2), json.dumps([IT_P2, IT_P1], ensure_ascii=False)])
_check("seconde passe au mauvais compte : REFUS",
       te.translate_article(c, "m", SOURCE, "it") is None)

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)")
    sys.exit(1)
print("Tout passe.")
