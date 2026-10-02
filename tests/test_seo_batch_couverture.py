#!/usr/bin/env python3
"""Fixture : `scripts.seo_batch` traite TOUTE fiche en ligne, dans sa langue, et refuse
d'écrire un SEO rédigé dans la mauvaise langue.

D'OÙ ÇA VIENT — 2026-09-09, colonne Yoast du back-office (capture de Franck) : presque
tout rouge, un vert sur vingt, gris sur toutes les fiches italiennes. Deux culs-de-sac
dans `_select` : « score ≥ 7 » (une fiche en ligne notée 6 n'entrait jamais) et
« traductions exclues » depuis le 02/08 « en attendant de rédiger en italien ».

Six cas, chacun décidant seul :
  ① en ligne, score 4, FR             → SÉLECTIONNÉE (en ligne ⇒ SEO, le score ne compte pas) ;
  ② pas en ligne, score 4             → PAS sélectionnée (le seuil garde son sens hors ligne) ;
  ③ LE CAS QUI DOIT PASSER, à la frontière : pas en ligne, score exactement 7 → sélectionnée ;
  ④ traduction IT en ligne            → sélectionnée ET optimize_seo appelé avec lang='it' ;
  ⑤ en ligne mais ANNULÉE             → PAS sélectionnée (on n'optimise pas une annulation) ;
  ⑥ garde de langue : le faux LLM répond en FRANÇAIS pour la fiche IT → rien d'écrit,
     compté en « mauvaise langue », les autres fiches sont bien écrites.
Et le dry-run affiche la file entière avec son périmètre.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau (publication et LLM remplacés).

Lancer : .venv/bin/python -m tests.test_seo_batch_couverture
"""
import contextlib
import io
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)
os.environ["ANTHROPIC_API_KEY"] = "factice-jamais-appelee"

from scripts.scraper_events import init_db  # noqa: E402
import scripts.seo_batch as seo_batch  # noqa: E402
import scripts.publish_batch_as as pba  # noqa: E402

seo_batch.DB_PATH = tmp
publications: list[list[str]] = []
pba.main = lambda argv: publications.append(list(argv)) or 0   # jamais de réseau

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


conn = sqlite3.connect(tmp)
init_db(conn)
COLS = ("id, title, description, url_source, ville, territoire, lieu, statut, llm_score, "
        "llm_categorie, date_event_start, date_event_end, wp_post_id_as, translation_of, "
        "translated_lang, annule_le")
LIGNES = [
    (1, "Concert de musique classique à Annecy", "Un concert au bord du lac.", "https://a.fr/1",
     "Annecy", "Savoie", "Salle", "published_cs", 4, "Musique", "2099-11-15", "2099-11-15", 101, None, None, None),
    (2, "Marché de Noël de Chambéry", "Marché de Noël.", "https://a.fr/2",
     "Chambéry", "Savoie", "Place", "evaluated", 4, "Marchés", "2099-12-01", "2099-12-01", None, None, None, None),
    (3, "Festival de théâtre à Thonon", "Festival de théâtre.", "https://a.fr/3",
     "Thonon", "Savoie", "Théâtre", "evaluated", 7, "Spectacle", "2099-10-01", "2099-10-01", None, None, None, None),
    (4, "Concerto di musica classica ad Annecy", "Un concerto in riva al lago.", "translated:1:it",
     "Annecy", "Savoie", "Salle", "published_cs", 4, "Musique", "2099-11-15", "2099-11-15", 104, 1, "it", None),
    (5, "Fête du lac annulée", "Annulée.", "https://a.fr/5",
     "Annecy", "Savoie", "Lac", "published_cs", 9, "Fêtes", "2099-08-01", "2099-08-01", 105, None, None, "2026-09-01"),
]
conn.executemany(f"INSERT INTO events_raw ({COLS}) VALUES ({','.join('?'*16)})", LIGNES)
conn.commit()
conn.close()

# ── Sélection (dry-run) ────────────────────────────────────────────────────────────
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    seo_batch.main(["--dry-run", "--cap", "50"])
sortie = buf.getvalue()
ids = {int(l.split("[")[1].split()[0]) for l in sortie.splitlines() if l.strip().startswith("[")}
verifier("① en ligne, score 4 : SÉLECTIONNÉE", 1 in ids, sortie)
verifier("② pas en ligne, score 4 : PAS sélectionnée", 2 not in ids)
verifier("③ LE CAS QUI DOIT PASSER : pas en ligne, score 7 pile : sélectionnée", 3 in ids)
verifier("④ traduction IT en ligne : sélectionnée", 4 in ids)
verifier("⑤ annulée : PAS sélectionnée", 5 not in ids)
verifier("dry-run : la file entière est affichée avec son périmètre",
         "File entière (en ligne, devant nous, sans SEO, hors cap) : 2" in sortie, sortie)
verifier("dry-run : la fiche IT est annoncée en 'it'", "· it ·" in sortie, sortie)

# ── Langue demandée + garde de langue ──────────────────────────────────────────────
appels: list[tuple[int, str]] = []


def _faux_optimize(ev, client, model, lang=None):
    appels.append((ev["id"], lang))
    if ev["id"] == 4:
        # Le LLM « oublie » l'italien : titre et méta en français sur la fiche IT.
        return {"seo_title": "Concert de musique classique à Annecy — Agenda Sabauda",
                "seo_meta": "Un concert au bord du lac, entrée libre, le samedi soir.",
                "seo_answer": "Le concert a lieu à Annecy.", "seo_faq": [],
                "seo_keyphrase": "concert Annecy", "seo_slug": "concert-annecy", "seo_tags": [],
                "seo_lang": "it"}
    return {"seo_title": f"{ev['title']} — Agenda Sabauda",
            "seo_meta": "Rendez-vous en Savoie, au bord du lac, entrée libre le samedi.",
            "seo_answer": "Le rendez-vous a lieu en Savoie.", "seo_faq": [],
            "seo_keyphrase": "k", "seo_slug": "s", "seo_tags": [], "seo_lang": "fr"}


seo_batch.seo_mod.optimize_seo = _faux_optimize
with contextlib.redirect_stdout(io.StringIO()):
    seo_batch.main(["--cap", "50", "--delay", "0"])

langs = dict(appels)
verifier("④ optimize_seo appelé avec lang='it' pour la traduction", langs.get(4) == "it", str(appels))
verifier("① optimize_seo appelé avec lang='fr' pour la fiche française", langs.get(1) == "fr", str(appels))

c = sqlite3.connect(tmp)
avec_seo = {r[0] for r in c.execute("SELECT id FROM events_raw WHERE seo_at IS NOT NULL")}
c.close()
verifier("⑥ SEO en mauvaise langue : RIEN écrit pour la fiche IT", 4 not in avec_seo, str(avec_seo))
verifier("⑥ …et les fiches en bonne langue sont bien écrites", {1, 3} <= avec_seo, str(avec_seo))
verifier("la fiche en ligne est republiée (texte seul), la fiche IT refusée ne l'est pas",
         publications and "1" in publications[0] and "4" not in publications[0], str(publications))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
