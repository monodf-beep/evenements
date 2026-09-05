#!/usr/bin/env python3
"""Fixture : le vocabulaire interdit — lu EN DIRECT dans Obsidian, plus une seule copie
dans GitHub.

⚠️ BASE JETABLE pour la partie audit. Aucun réseau.

D'OÙ ÇA VIENT. Franck, 2026-08-21 : « ne jamais mettre "royaume de Sardaigne" mais mettre
"les États de Savoie" ». Puis, 2026-09-05, en reconstituant la voix éditoriale : la vraie
note Obsidian portait quatre règles absentes du JSON du dépôt (« frontière », « langues
régionales », « francoprovençal », « patois »), et deux règles du JSON n'avaient jamais
été recopiées côté Obsidian — la dérive que ce fichier existait pour éviter, déplacée
d'un cran. Franck, le même jour : « tout doit être dans Obsidian, les règles ne doivent
pas vivre dans GitHub » — et, sur la panne : « continuer sans filtre, silencieusement ».

CE QUE CETTE FIXTURE SURVEILLE, sur une note Obsidian FABRIQUÉE (fichier temporaire, avec
la forme réelle de la vraie note — tableau à 3 colonnes, gras, guillemets français) :
  1. l'expression est trouvée, AVEC LA PHRASE ;
  2. les variantes, l'italien et les accents comptent ;
  3. ⚠️ LE CAS QUI DOIT PASSER : un texte qui dit déjà « les États de Savoie » n'est pas
     signalé. Sans lui, on ne prouverait que la capacité à crier ;
  4. une alternative ENTIÈREMENT en gras est un remplacement direct ; une alternative en
     PROSE (« Reformuler (…) ») est un CONSEIL, pas un mot à mot — `remplacement()` doit
     rester "" dans ce cas, et `consigne_prompt()` doit quand même donner une consigne
     utilisable, pas juste « n'emploie jamais » ;
  5. LES QUATRE PROMPTS portent la règle EN VRAI (ils appellent `consigne_prompt()`, ils
     ne la recopient pas) ;
  6. ⚠️ LE CAS QUI DOIT PASSER, celui qui a motivé le changement du 05/09 : SANS AUCUNE
     copie dans `config/`, en pointant uniquement vers le fichier temporaire, tout
     continue de marcher — la preuve que GitHub ne porte plus la donnée ;
  7. ⚠️ ET LE CAS INVERSE, explicitement choisi par Franck : si la note est INJOIGNABLE
     (variable absente, fichier manquant), `interdits()` renvoie `()`, `trouver()` ne
     signale RIEN et ne lève AUCUNE exception — le pipeline continue sans filtre, pas de
     blocage, pas d'alerte. C'est un choix, pas un oubli : le test le fige.

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

# La note Obsidian FABRIQUÉE — même forme que la vraie (01-Commun/Vocabulaire interdit.md,
# relevée le 05/09/2026), avec les deux règles réellement en jeu ici, une ligne à
# alternative-CONSEIL (pas de remplacement direct) et une ligne sans aucun remplacement.
_NOTE_VOCAB = """---
tags: [charte, niveau-1, non-négociable, vocabulaire]
---

# Vocabulaire interdit

| Terme interdit | Pourquoi | Alternative |
| --- | --- | --- |
| **« royaume de Sardaigne »**, « Regno di Sardegna », « reame di Sardegna » | Le sujet est l'espace savoyard, pas l'appellation diplomatique de 1720 | **les États de Savoie** *(IT : gli Stati Sabaudi)* |
| **« Venise des Alpes »**, « Venise du Nord », « petite Venise », « perle des Alpes » | Surnom de guide touristique | Nommer la ville, sans remplacement |
| **« frontière »** | Politiquement chargé pour l'espace franco-italien alpin | Reformuler (« au-delà des Alpes », « en Piémont ») |
| **« transfrontalier »** en H1 | Cadre politique administratif | Formuler la fluidité culturelle autrement |
| **« espace alpin »**, « spazio alpino » pour Savoie + Piémont | Efface la spécificité culturelle | **espace sabaud** *(IT : spazio sabaudo)* |
"""

vocab_path = Path(tempfile.mkdtemp()) / "Vocabulaire interdit.md"
vocab_path.write_text(_NOTE_VOCAB, encoding="utf-8")
os.environ["OBSIDIAN_VOCAB_PATH"] = str(vocab_path)

from utils.vocabulaire import consigne_prompt, remplacement, trouver, interdits  # noqa: E402
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


print("──── zéro copie dans GitHub : rien sous config/ ────")
_check("config/vocabulaire_interdit.json n'existe plus",
       not (ROOT / "config" / "vocabulaire_interdit.json").exists())

print("\n──── la phrase de Franck, telle qu'elle est en ligne ────")
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

print("\n──── ⚠️ alternative en PROSE = un conseil, pas un remplacement mot à mot ────")
_check("« frontière » est détecté", trouver("Cette frontière naturelle sépare deux mondes.") != [])
_check("   mais n'a AUCUN remplacement direct (l'alternative n'est pas tout en gras)",
       remplacement("frontière") == "")
e_frontiere = next(e for e in interdits() if e["expression"] == "frontière")
_check("   le conseil de la note est bien capté",
       "Reformuler" in e_frontiere["_conseil"] and "au-delà des Alpes" in e_frontiere["_conseil"],
       e_frontiere)
_check("   la consigne au rédacteur porte ce conseil, pas juste une interdiction nue",
       "Reformuler" in consigne_prompt() and "au-delà des Alpes" in consigne_prompt())

print("\n──── la consigne envoyée aux rédacteurs ────")
c = consigne_prompt()
_check("elle donne le remplacement, pas seulement l'interdiction",
       "les États de Savoie" in c and "Ne dis JAMAIS" in c, c)
_check("   et l'italien a la sienne", "gli Stati Sabaudi" in consigne_prompt("it"),
       consigne_prompt("it"))
_check("celle sans remplacement se lit autrement",
       "N'emploie JAMAIS « Venise des Alpes »" in c, c)

print("\n──── LES QUATRE PROMPTS portent la règle — EN VRAI, PAS RECOPIÉE ────")
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
_check("scripts/translate_events.py, cible IT (le remplacement, en italien)",
      "gli Stati Sabaudi" in rendu_te_it)

rendu_ca = _ca.PROMPT.format(article_json="{}", vocabulaire_interdit=consigne_prompt("fr"))
_check("scripts/conform_articles.py (rendu réel)", "royaume de Sardaigne" in rendu_ca)

rendu_social = _social._CAPTION_AI_RULES.format(
    lang_full="français", vocabulaire_interdit=consigne_prompt("fr"))
_check("utils/social.py (rendu réel)", "royaume de Sardaigne" in rendu_social)

print("\n──── transfrontalier / espace alpin toujours vivants ────")
_check("« transfrontalier » est détecté", trouver("Cette exposition transfrontalière.") != [])
_check("« espace alpin » est détecté", trouver("Un événement au cœur de l'espace alpin.") != [])
_check("la consigne envoyée aux 4 prompts porte bien les deux",
      "transfrontalier" in consigne_prompt("fr") and "espace alpin" in consigne_prompt("fr"))
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
_check("⚠️ il avertit qu'une occurrence peut être un titre officiel",
       "titre officiel d'une exposition" in s, s[-600:])

print("\n──── ⚠️ Obsidian injoignable : silence total, pas de blocage (choix de Franck) ────")
del os.environ["OBSIDIAN_VOCAB_PATH"]
_check("plus aucune règle chargée", interdits() == ())
_check("trouver() ne lève rien et ne signale plus rien",
       trouver("Vestige du royaume de Sardaigne, la Venise des Alpes.") == [])
_check("consigne_prompt() renvoie une chaîne vide, pas une exception",
       consigne_prompt() == "")
os.environ["OBSIDIAN_VOCAB_PATH"] = "/chemin/qui/n/existe/pas.md"
_check("un chemin réglé mais introuvable se comporte pareil (pas d'exception)",
       interdits() == () and trouver("royaume de Sardaigne") == [])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
