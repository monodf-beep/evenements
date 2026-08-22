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

print("\n──── LES QUATRE PROMPTS portent la règle ────")
# Le contrôle qui compte : une consigne absente d'un prompt ne peut rien empêcher. Les
# quatre chemins d'écriture sont distincts et personne ne les tient à jour ensemble.
for chemin in ("scripts/enrich.py", "scripts/translate_events.py",
               "scripts/conform_articles.py", "utils/social.py"):
    src = (ROOT / chemin).read_text(encoding="utf-8")
    _check(f"{chemin}", "royaume de Sardaigne" in src or "Regno di Sardegna" in src)

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
