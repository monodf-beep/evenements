#!/usr/bin/env python3
"""Fixture : le scan des GUIDES et CURIOSITÉS par scripts.audit_vocabulaire.

D'OÙ ÇA VIENT. `audit_vocabulaire.py` ne lisait que `events_raw` — les guides et
curiosités, publiés en posts WordPress autonomes sans ligne correspondante dans cette
table, n'étaient jamais examinés. Trouvé en corrigeant à la main « royaume de Sardaigne »
dans le guide WP#2420 (« Expositions à Turin 2026 »), présent depuis la création du guide.
Franck, 2026-09-06 : « c'est un problème ».

CE QUE CETTE FIXTURE SURVEILLE, sans réseau (tout appel HTTP est remplacé) :
  1. `_articles_depuis_payload` (fonction PURE) : déduplique par id, écarte un article
     sans lien, décode les entités HTML du titre, retire les balises du corps ;
  2. ⚠️ LE CAS QUI DOIT PASSER, choisi près de la frontière : un article qui contient
     DÉJÀ le remplacement correct (« les États de Savoie ») n'est PAS signalé — sans lui,
     on ne prouverait que la capacité à crier sur un mot-clé, jamais l'absence de faux
     positif sur le texte qui a justement été corrigé ;
  3. la panne réseau sur UNE catégorie n'efface pas le rapport de l'autre, et s'annonce
     comme un échec de lecture (« NON VÉRIFIÉ »), jamais comme un zéro silencieux ;
  4. les deux familles (guides, curiosités) sont comptées et affichées SÉPARÉMENT, et
     séparément du total events_raw — un compteur doit dire ce qu'il compte (règle 6).

Lancer : .venv/bin/python -m tests.test_audit_vocabulaire_articles
"""
import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

_NOTE_VOCAB = """---
tags: [charte, niveau-1, non-négociable, vocabulaire]
---

# Vocabulaire interdit

| Terme interdit | Pourquoi | Alternative |
| --- | --- | --- |
| **« royaume de Sardaigne »**, « Regno di Sardegna » | Le sujet est l'espace savoyard, pas l'appellation diplomatique de 1720 | **les États de Savoie** *(IT : gli Stati Sabaudi)* |
"""
vocab_path = Path(tempfile.mkdtemp()) / "Vocabulaire interdit.md"
vocab_path.write_text(_NOTE_VOCAB, encoding="utf-8")
os.environ["OBSIDIAN_VOCAB_PATH"] = str(vocab_path)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.audit_vocabulaire as av  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ── base events_raw vide : ce fichier ne teste QUE le côté articles ────────────────
import sqlite3  # noqa: E402
conn = sqlite3.connect(tmp)
init_db(conn)
conn.close()

print("──── _articles_depuis_payload, fonction pure ────")
payload = [
    {"id": 10, "link": "https://agendasabauda.eu/guide-turin/",
     "title": {"rendered": "Expositions &agrave; Turin 2026"},
     "content": {"rendered": "<p>Vestige de la capitale du <strong>royaume de "
                              "Sardaigne</strong>.</p>"}},
    {"id": 10, "link": "https://agendasabauda.eu/guide-turin/",  # doublon d'id
     "title": {"rendered": "Expositions &agrave; Turin 2026"},
     "content": {"rendered": "<p>Vestige de la capitale du royaume de Sardaigne.</p>"}},
    {"id": 99, "link": "", "title": {"rendered": "Sans adresse"}, "content": {"rendered": ""}},
]
arts = av._articles_depuis_payload(payload)
_check("le doublon d'id ne compte qu'une fois", len(arts) == 1, arts)
_check("un article sans lien est écarté", all(a["id"] != 99 for a in arts))
_check("les entités HTML du titre sont décodées",
       arts[0]["titre"] == "Expositions à Turin 2026", arts[0]["titre"])
_check("les balises du corps sont retirées",
       "<strong>" not in arts[0]["texte"] and "royaume de Sardaigne" in arts[0]["texte"],
       arts[0]["texte"])

print("\n──── le scan complet, réseau simulé ────")
GUIDE_VIOLATION = [{
    "id": 2420, "link": "https://agendasabauda.eu/expositions-turin-2026/",
    "title": {"rendered": "Expositions à Turin 2026"},
    "content": {"rendered": "<p>L'ancienne capitale du royaume de Sardaigne.</p>"},
}]
# ⚠️ LE CAS QUI DOIT PASSER : le remplacement correct est déjà en place, rien à signaler.
CURIOSITE_CORRIGEE = [{
    "id": 8227, "link": "https://agendasabauda.eu/curiosites-turin/",
    "title": {"rendered": "Six curiosités de Turin"},
    "content": {"rendered": "<p>Parlement subalpin des États de Savoie.</p>"},
}]


def _wp_simule(slugs, base=av.BASE_URL):
    if slugs == av.GUIDES_SLUGS:
        return av._articles_depuis_payload(GUIDE_VIOLATION), []
    if slugs == av.CURIOSITES_SLUGS:
        return av._articles_depuis_payload(CURIOSITE_CORRIGEE), []
    raise AssertionError(f"slugs inattendus : {slugs}")


av._articles_wp = _wp_simule
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    av.main([])
s = buf.getvalue()

_check("le guide fautif est compté à part, 1 sur 1",
       "Guides publié(e)s (hors agenda) : 1 examiné(e)s — 1 concerné(e)(s)" in s, s)
_check("la curiosité déjà corrigée n'est PAS signalée (0 sur 1)",
       "Curiosités publié(e)s (hors agenda) : 1 examiné(e)s — 0 concerné(e)(s)" in s, s)
_check("le lien du guide fautif apparaît, pas un WP#id de fiche événement",
       "https://agendasabauda.eu/expositions-turin-2026/" in s, s)
_check("le total events_raw reste à 0, séparé de celui des articles",
       "FICHES CONCERNÉES       : 0" in s, s)

print("\n──── panne réseau sur UNE catégorie : jamais un zéro silencieux ────")


def _wp_panne(slugs, base=av.BASE_URL):
    if slugs == av.GUIDES_SLUGS:
        raise ConnectionError("DNS injoignable (simulé)")
    return av._articles_depuis_payload(CURIOSITE_CORRIGEE), []


av._articles_wp = _wp_panne
buf2 = io.StringIO()
with contextlib.redirect_stdout(buf2):
    av.main([])
s2 = buf2.getvalue()
_check("la panne sur les guides est annoncée comme un échec, pas un zéro",
       "NON VÉRIFIÉ" in s2 and "guides" in s2.lower(), s2)
_check("elle ne prétend jamais qu'il n'y a « aucune occurrence »",
       "guides" not in s2.split("NON VÉRIFIÉ")[0].lower()
       or "0 examiné" not in s2.split("NON VÉRIFIÉ")[1][:80], s2)
_check("les curiosités, non touchées par la panne, sont quand même rapportées",
       "Curiosités publié(e)s (hors agenda) : 1 examiné(e)s" in s2, s2)

print("\n──── une langue en échec n'est pas une liste vide déguisée ────")


def _wp_moitie(slugs, base=av.BASE_URL):
    if slugs == av.GUIDES_SLUGS:
        return av._articles_depuis_payload(GUIDE_VIOLATION), ["it"]
    return av._articles_depuis_payload(CURIOSITE_CORRIGEE), []


av._articles_wp = _wp_moitie
buf3 = io.StringIO()
with contextlib.redirect_stdout(buf3):
    av.main([])
s3 = buf3.getvalue()
_check("la langue manquante est nommée, pas juste comptée en moins",
       "langue(s) non interrogée(s) (it)" in s3, s3)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
