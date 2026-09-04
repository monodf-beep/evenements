#!/usr/bin/env python3
"""Fixture : le vocabulaire interdit — une source, quatre prompts, un audit.

⚠️ BASE JETABLE pour la partie audit. Aucun réseau.

D'OÙ ÇA VIENT. Franck, 2026-08-21, en lisant https://agendasabauda.eu/expositions-turin-2026/ :
« de l'ancienne capitale du royaume de Sardaigne […] ne jamais mettre "royaume de
Sardaigne" mais mettre "les États de Savoie" ».

CE QUE LA FIXTURE SURVEILLE :
  1. l'expression est trouvée, AVEC LA PHRASE — sans elle, impossible de distinguer notre
     prose du titre officiel d'une exposition, et une correction à l'aveugle abîmerait un
     nom propre ;
  2. les variantes et l'italien comptent (« Regno di Sardegna »), accents ignorés ;
  3. ⚠️ LE CAS QUI DOIT PASSER : un texte qui dit déjà « les États de Savoie » n'est pas
     signalé. Sans lui, on ne prouverait que la capacité à crier ;
  4. la consigne de prompt donne le REMPLACEMENT, pas seulement l'interdiction — « ne dis
     pas X » laisse le rédacteur sans solution, donc libre d'improviser ;
  5. et LES QUATRE PROMPTS la portent. C'est le contrôle qui compte vraiment : « Venise
     des Alpes » figurait dans les quatre et a quand même été publié, mais un prompt qui
     ne la porte PAS ne peut rien empêcher du tout.

Lancer : .venv/bin/python -m tests.test_vocabulaire
"""
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from utils.vocabulaire import consigne_prompt, remplacement, trouver  # noqa: E402
from scripts.scraper_events import init_db                            # noqa: E402
import scripts.audit_vocabulaire as av                                # noqa: E402

av.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── la phrase de Franck, telle qu'elle est en ligne ────")
reelle = ("Le palais domine la place, vestige de l'ancienne capitale du royaume de "
          "Sardaigne. Le bâtiment lui-même, entre vestiges romains et façades baroques.")
t = trouver(reelle)
_check("l'expression est trouvée", [e for e, _p in t] == ["royaume de Sardaigne"], t)
_check("   et la PHRASE est rendue, pas un simple oui",
       t and "ancienne capitale" in t[0][1] and "bâtiment lui-même" not in t[0][1], t)
_check("le remplacement est celui de Franck",
       remplacement("royaume de Sardaigne") == "les États de Savoie")
_check("   et l'italien a le sien",
       remplacement("royaume de Sardaigne", "it") == "gli Stati Sabaudi")

print("\n──── variantes, langues, accents ────")
_check("l'italien est reconnu", trouver("La mostra sul Regno di Sardegna a Torino."))
_check("la casse est ignorée", trouver("le ROYAUME DE SARDAIGNE"))
_check("les accents aussi", trouver("l'Etat du royaume de Sardaigne"))
_check("« Venise des Alpes » reste interdit", trouver("Annecy, la Venise des Alpes."))
_check("   et lui n'a AUCUN remplacement — on nomme la ville",
       remplacement("Venise des Alpes") == "")

print("\n──── ⚠️ ce qui NE doit PAS être signalé ────")
_check("un texte qui dit déjà « les États de Savoie » est propre (le cas qui doit passer)",
       trouver("Capitale des États de Savoie, Turin garde ses façades baroques.") == [])
_check("   « Sardaigne » seule ne déclenche rien — c'est une île",
       trouver("Une exposition sur la Sardaigne et ses nuraghes.") == [])
_check("   ni « royaume » seul", trouver("Le royaume animal au musée d'histoire naturelle.") == [])

print("\n──── la consigne envoyée aux rédacteurs ────")
c = consigne_prompt()
_check("elle donne le remplacement, pas seulement l'interdiction",
       "les États de Savoie" in c and "Ne dis JAMAIS" in c, c)
_check("   et l'italien a la sienne", "gli Stati Sabaudi" in consigne_prompt("it"),
       consigne_prompt("it"))
_check("celle sans remplacement se lit autrement",
       "N'emploie JAMAIS « Venise des Alpes »" in c, c)

print("\n──── LES QUATRE PROMPTS portent la règle — EN VRAI, PAS RECOPIÉE ────")
# CORRIGÉ le 04/09 (audit du 31/08 §2.5, décision de Franck le même jour sur
# « transfrontalier »/« espace alpin ») : jusque-là, ce bloc vérifiait qu'une CHAÎNE
# recopiée à la main figurait dans le SOURCE des 4 fichiers — un contrôle qui ne
# prouvait rien sur ce qui part vraiment au LLM, et qui expliquait pourquoi « petite
# Venise »/« perle des Alpes » vivaient dans les prompts sans jamais être dans ce
# fichier JSON (donc jamais vues par l'audit sur le déjà-publié). Les 4 prompts
# appellent maintenant `vocabulaire.consigne_prompt()` au lieu de recopier — ce bloc
# APPELLE CHAQUE CHEMIN RÉEL et vérifie ce qui en sort, pas ce qui est écrit en dur.
import scripts.enrich as _enrich                      # noqa: E402
import scripts.translate_events as _te                # noqa: E402
import scripts.conform_articles as _ca                # noqa: E402
import utils.social as _social                         # noqa: E402

rendu_enrich = _enrich.ENRICH_PROMPT.format(
    title="t", dates="d", lieu="l", territoire="terr", organisateur="org",
    categorie="cat", material="mat", vocabulaire_interdit=consigne_prompt("fr"))
_check("scripts/enrich.py (rendu réel)", "royaume de Sardaigne" in rendu_enrich)

rendu_te_fr = _te._charte_prompt("fr")
rendu_te_it = _te._charte_prompt("it")
_check("scripts/translate_events.py, cible FR", "royaume de Sardaigne" in rendu_te_fr)
# consigne_prompt() affiche toujours l'EXPRESSION en français (c'est la clé du JSON),
# seul le REMPLACEMENT change de langue — cohérent avec le test dédié plus haut
# (« et l'italien a la sienne » vérifie déjà gli Stati Sabaudi, pas Regno di Sardegna).
_check("scripts/translate_events.py, cible IT (le remplacement, en italien)",
      "gli Stati Sabaudi" in rendu_te_it)

rendu_ca = _ca.PROMPT.format(article_json="{}", vocabulaire_interdit=consigne_prompt("fr"))
_check("scripts/conform_articles.py (rendu réel)", "royaume de Sardaigne" in rendu_ca)

rendu_social = _social._CAPTION_AI_RULES.format(
    lang_full="français", vocabulaire_interdit=consigne_prompt("fr"))
_check("utils/social.py (rendu réel)", "royaume de Sardaigne" in rendu_social)

print("\n──── la décision du 04/09 (transfrontalier / espace alpin) est bien vivante ────")
_check("« transfrontalier » est détecté", trouver("Cette exposition transfrontalière.") != [])
_check("« espace alpin » est détecté", trouver("Un événement au cœur de l'espace alpin.") != [])
_check("la consigne envoyée aux 4 prompts porte bien les deux",
      "transfrontalier" in consigne_prompt("fr") and "espace alpin" in consigne_prompt("fr"))
# Les 2 usages du mot dans le PROMPT LUI-MÊME (translate_events décrivait le média comme
# « alpin transfrontalier », social.py pareil) ont été corrigés en « sabaud » — sinon le
# prompt aurait interdit d'une main ce qu'il écrit de l'autre.
_check("translate_events.py ne s'auto-décrit plus comme « transfrontalier »",
      "transfrontalier" not in rendu_te_fr.split("VOCABULAIRE INTERDIT")[0])
rendu_social_complet = _social._CAPTION_AI_RULES.format(
    lang_full="français", vocabulaire_interdit="")
_check("utils/social.py ne s'auto-décrit plus comme « transfrontalier » non plus",
      "transfrontalier" not in rendu_social_complet)

print("\n──── l'audit sur une base ────")
conn = sqlite3.connect(tmp)
init_db(conn)
for eid, wp, titre, corps in (
        (1, 8001, "Palazzo Madama", "Vestige de la capitale du royaume de Sardaigne."),
        (2, 8002, "Turin baroque", "Capitale des États de Savoie, la ville garde ses façades."),
        (3, 8003, "Il Regno di Sardegna", "Una mostra dedicata al Regno di Sardegna.")):
    conn.execute(
        "INSERT INTO events_raw (id, title, article_title, enrich_data, url_source, "
        "wp_post_id_as, statut, duplicate_of) VALUES (?,?,?,?,?,?,?,NULL)",
        (eid, titre, titre, json.dumps({"article": {"chapo": corps, "corps": ""}}),
         f"https://a.fr/{eid}", wp, "published_sub"))
conn.commit(); conn.close()

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    av.main([])
s = buf.getvalue()
_check("il compte 2 fiches concernées sur 3", "FICHES CONCERNÉES       : 2" in s, s[:600])
_check("   la propre n'y est pas", "WP#8002" not in s, s)
_check("il montre la phrase de chacune", "« …Vestige de la capitale" in s, s)
_check("il donne le remplacement à côté de l'expression",
       "→ « les États de Savoie »" in s, s)
# ⚠️ LE CAS AMBIGU, ET IL DOIT RESTER AMBIGU : la fiche 3 s'appelle « Il Regno di
# Sardegna » — c'est peut-être le titre officiel d'une exposition. L'audit la signale,
# mais il doit dire de LIRE avant de corriger, sinon on réécrit un nom propre.
_check("⚠️ il avertit qu'une occurrence peut être un titre officiel",
       "titre officiel d'une exposition" in s, s[-600:])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
