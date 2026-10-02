#!/usr/bin/env python3
"""Fixture : un original non public ne coûte AUCUN appel et ne gare PAS la fiche.

INCIDENT RÉEL, 22/09 → 01/10/2026 (registre : `traduction-boucle-originaux-corbeille`).
5486, 5459, 5630 et 6342 ont un post WordPress à la corbeille. Chaque matin le cron les
traduisait (deux appels API), puis le portillon « l'original doit être public » les
refusait, puis `marquer_refus` comptait — et trois refus garaient la fiche « sur une
matière inchangée ». CLAUDE.md règle 3 : un refus qui se rejoue sur la MÊME entrée n'est
pas un rouvreur ; et ici le garage ne rouvre que si la matière change, alors que la cause
est l'état de l'original sur le site. Revenu en ligne, l'original n'aurait JAMAIS relancé
sa traduction.

Ce que la fixture exige :
  A. original à la corbeille → le modèle n'est PAS appelé, rien n'est publié, verdict
     'original_absent' (et pas 'refus', donc aucun marquer_refus) ;
  B. ⚠️ le cas qui doit PASSER : original public → le modèle EST appelé. Sans lui, un
     `return` inconditionnel passerait au vert ;
  C. près de la frontière : sans --apply (simulation), la sonde réseau n'est pas posée —
     une simulation ne doit pas dépendre du site.

Aucun réseau, aucun LLM. Lancer : .venv/bin/python -m tests.test_traduction_original_absent
"""
import os
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.mkdtemp()) / "vide.db"))
os.environ.setdefault("WP_AS_URL", "https://exemple.invalid")

import scripts.translate_events as te  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    print(("OK    " if cond else "ÉCHEC ") + label, "" if cond else detail)
    if not cond:
        echecs += 1


class Args:
    def __init__(self, apply):
        self.apply = apply
        self.model = "fake"
        self.retranslate = False


appels = {"llm": 0}


def faux_llm(*a, **k):
    appels["llm"] += 1
    return None            # None => "error" : on s'arrête juste après l'appel


te.translate_title_desc = faux_llm
EV = {"id": 5486, "title": "Celebrazioni per la Giornata degli internati italiani",
      "description": "Cerimonia al Museo di Biella con deposizione di una corona.",
      "wp_post_id_as": 10242, "territoire": "piemont", "lieu": "Museo", "ville": "Biella",
      "url_image": "", "organisateur": "", "enrich_data": ""}


def verdict(apply, public):
    appels["llm"] = 0
    te.wp_original_est_en_ligne = lambda wp_id: public
    return te._translate_one(dict(EV), Args(apply), object(), "cle", "", "https://x",
                             ("u", "p"), {}, threading.Lock())


print("A. original à la corbeille")
v = verdict(True, False)
_check("verdict 'original_absent', pas 'refus' (donc aucun marquer_refus)",
       v == "original_absent", v)
_check("AUCUN appel au modèle", appels["llm"] == 0, appels)

print("B. le cas qui doit passer : original public")
v = verdict(True, True)
_check("le modèle est appelé (la sonde ne bloque rien)", appels["llm"] == 1, appels)

print("C. simulation (sans --apply) : pas de sonde réseau")
sondes = []
te.wp_original_est_en_ligne = lambda wp_id: sondes.append(wp_id) or False
te._translate_one(dict(EV), Args(False), object(), "cle", "", "https://x", ("u", "p"),
                  {}, threading.Lock())
_check("la sonde n'est pas appelée hors --apply", sondes == [], sondes)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
