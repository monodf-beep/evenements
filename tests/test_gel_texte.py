#!/usr/bin/env python3
"""Fixture : le cron ne repasse plus sur un texte repris à la main — et il le RELÂCHE
dès qu'on lui rend la main.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau, aucune clé API.

D'OÙ ÇA VIENT — Franck, 2026-09-21 : « si cowork a travaillé le seo, on ne doit pas
pouvoir revenir dessus avec le cron ». L'ordre de travail est « création FR + IT → cron
SEO → reprise à la main / Cowork », et il ne va que dans ce sens.

CE QUE CE FICHIER CHERCHE À PRENDRE EN DÉFAUT, et pas seulement à confirmer (CLAUDE.md
règle 3 : « la fixture doit contenir un cas qui doit PASSER, choisi près de la
frontière ») :

  • un gel qui gèle trop — la fiche NON gelée, et celle dont `wp_gel_at` vaut la chaîne
    VIDE plutôt que NULL, doivent rester dans la file. C'est le cas frontière : les deux
    valeurs se ressemblent en SQL et une seule est écrite par le code ;
  • un gel qui ne se lève pas — après dégel, la fiche doit REVENIR dans la file du cron.
    Un état terminal sans rouvreur est le défaut structurel du dépôt (règle 3) ;
  • un gel qu'on pose sans savoir — quand le site ne dit RIEN du gel (mu-plugin pas
    encore en ligne), la base ne doit pas bouger. « Pas de gel » et « on ne sait pas »
    ne doivent pas rendre le même résultat, sinon un déploiement oublié dégèlerait tout
    en silence ;
  • un gel qui se cache — la fiche gelée sort de toutes les files, elle doit donc être
    COMPTÉE ailleurs (règle 6), et seulement quand elle compte : en ligne et devant nous.

Lancer : .venv/bin/python -m tests.test_gel_texte
"""
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db          # noqa: E402
import scripts.seo_batch as seo_batch               # noqa: E402
import scripts.publish_batch_as as pub              # noqa: E402
from scripts.publisher_as import _build_payload     # noqa: E402

seo_batch.DB_PATH = tmp

AUJ = date.today().isoformat()
DEMAIN = (date.today() + timedelta(days=30)).isoformat()
HIER = (date.today() - timedelta(days=30)).isoformat()

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


class Args:
    """Les arguments de seo_batch._select, réduits à ce que la sélection lit."""
    ids = None
    redo = False
    include_past = False
    min_score = 7
    cap = 50


def _base():
    if tmp.exists():
        tmp.unlink()
    conn = sqlite3.connect(tmp)
    init_db(conn)
    # 1 — fiche ordinaire, en ligne, devant nous : la référence.
    # 2 — MÊME fiche, mais `wp_gel_at` à la chaîne VIDE : cas frontière, doit passer.
    # 3 — gelée : doit disparaître des files et être comptée à part.
    # 4 — gelée mais PASSÉE : hors périmètre (règle 5), ne doit pas gonfler le compteur.
    # 5 — gelée mais JAMAIS publiée : rien à protéger sur le site, idem.
    lignes = [
        (1, "Un concert",        "http://s/1", 9, 8001, DEMAIN, None),
        (2, "Une expo",          "http://s/2", 9, 8002, DEMAIN, ""),
        (3, "Fiche retravaillée", "http://s/3", 9, 8003, DEMAIN, "2026-09-21 10:00:00"),
        (4, "Fiche d'hier",      "http://s/4", 9, 8004, HIER,   "2026-09-21 10:00:00"),
        (5, "Jamais publiée",    "http://s/5", 9, None,  DEMAIN, "2026-09-21 10:00:00"),
    ]
    for i, titre, url, score, wp, debut, gel in lignes:
        conn.execute(
            "INSERT INTO events_raw (id, title, url_source, statut, llm_score, "
            "wp_post_id_as, date_event_start, date_event_end, wp_gel_at) "
            "VALUES (?,?,?, 'evaluated', ?, ?, ?, ?, ?)",
            (i, titre, url, score, wp, debut, debut, gel))
    conn.commit()
    return conn


# ── 1. La sélection du cron SEO ────────────────────────────────────────────────
print("──── sélection de seo_batch ────")
conn = _base()
conn.row_factory = sqlite3.Row
ids = [r["id"] for r in seo_batch._select(conn, Args(), AUJ)]
_check("la fiche ordinaire reste dans la file", 1 in ids, f"(file : {ids})")
_check("wp_gel_at = '' (chaîne vide) n'est PAS un gel — cas frontière", 2 in ids,
       f"(file : {ids})")
_check("la fiche gelée est écartée du cron SEO", 3 not in ids, f"(file : {ids})")

# ── 2. Le compteur des fiches garées (règle 6) ─────────────────────────────────
n = seo_batch._geles(conn, AUJ)
_check("une seule fiche comptée gelée : en ligne ET devant nous", n == 1, f"(compté {n})")

# ── 3. La file des SEO calculés mais jamais arrivés sur le site ────────────────
# `seo_pushed_at` est créée à la volée par seo_batch lui-même (et par lui seul) : sur une
# base neuve, la requête de retard ne tourne pas sans ça.
seo_batch._ensure_seo_pushed_col(conn)
conn.execute("UPDATE events_raw SET seo_at='2026-09-20 09:00:00' WHERE id IN (1,3)")
conn.commit()
retard = [r[0] for r in conn.execute(seo_batch._SQL_RETARD, (AUJ,)).fetchall()]
_check("la fiche ordinaire attend bien d'être repoussée", 1 in retard, f"(file : {retard})")
_check("la fiche gelée n'est PAS republiée en boucle tous les jours",
       3 not in retard, f"(file : {retard})")

# ── 4. LE ROUVREUR : dégelée, la fiche revient dans la file ────────────────────
print("\n──── dégel : le pipeline reprend la main ────")
conn.execute("UPDATE events_raw SET wp_gel_at=NULL WHERE id=3")
conn.commit()
retard = [r[0] for r in conn.execute(seo_batch._SQL_RETARD, (AUJ,)).fetchall()]
_check("après dégel, la fiche revient dans la file de republication",
       3 in retard, f"(file : {retard})")
_check("après dégel, plus rien n'est compté comme gelé", seo_batch._geles(conn, AUJ) == 0)
# Pour la SÉLECTION, on lève aussi `seo_at` (posé à l'étape 3) : le gel n'est pas le seul
# filtre, et un test qui ne remet pas le reste à plat mesurerait « déjà optimisée » en
# croyant mesurer « encore gelée ». La première version de cette fixture s'y est fait
# prendre — c'est exactement ce qu'on lui demande de faire.
conn.execute("UPDATE events_raw SET seo_at=NULL WHERE id=3")
conn.commit()
ids = [r["id"] for r in seo_batch._select(conn, Args(), AUJ)]
_check("après dégel, la fiche revient dans la file du cron SEO", 3 in ids, f"(file : {ids})")
conn.close()

# ── 5. Ce que la base apprend du site — et ce qu'elle n'invente pas ────────────
print("\n──── recopie de la réponse du site (publish_batch_as._ranger_gel) ────")
conn = _base()
geles, restaures = [], []
pub._ranger_gel(conn, 1, {"gele": True, "depuis": "2026-09-21 11:00:00",
                          "motif": "retouche détectée (empreinte)",
                          "champs": ["title", "content", "seo"]}, geles, restaures)
row = conn.execute("SELECT wp_gel_at, wp_gel_champs, wp_gel_motif FROM events_raw "
                   "WHERE id=1").fetchone()
_check("le site dit « gelée » → la base le recopie", bool(row[0]) and "content" in row[1],
       f"(lu : {row})")
_check("et la fiche est comptée dans le bilan du lot", geles == [1], f"(lu : {geles})")

pub._ranger_gel(conn, 3, {"gele": False}, geles, restaures)
row = conn.execute("SELECT wp_gel_at FROM events_raw WHERE id=3").fetchone()
_check("le site dit « plus gelée » → la base lâche le marqueur (le rouvreur)",
       row[0] is None, f"(lu : {row})")

# LE CAS QUI COMPTE : le mu-plugin n'est pas en ligne, la réponse ne dit RIEN du gel.
pub._ranger_gel(conn, 4, None, geles, restaures)
row = conn.execute("SELECT wp_gel_at FROM events_raw WHERE id=4").fetchone()
_check("pas de clé « gel » dans la réponse → la base ne bouge pas (≠ « pas de gel »)",
       bool(row[0]), f"(lu : {row})")

pub._ranger_gel(conn, 2, {"gele": True, "depuis": "x", "motif": "", "champs": [],
                          "restaures": ["content"]}, geles, restaures)
_check("un texte que le site a dû RESTAURER est signalé à part", restaures == [2],
       f"(lu : {restaures})")
conn.close()

# ── 6. Le payload : le gel se joue sur le SITE, jamais ici ─────────────────────
print("\n──── payload envoyé à cs/v1/event ────")
ev = {"id": 1, "title": "Un concert", "wp_post_id_as": 8001,
      "date_event_start": DEMAIN, "date_event_end": DEMAIN, "description": "Texte.",
      "wp_gel_at": "2026-09-21 10:00:00"}
p = _build_payload(dict(ev))
_check("aucun « forcer_texte » par défaut", "forcer_texte" not in p, f"(clés : {sorted(p)})")
_check("le TEXTE part quand même — c'est le site qui refuse, pas nous "
       "(sinon les dates et les métas as_* ne descendraient plus)",
       "content" in p and "title" in p)
p = _build_payload(dict(ev), forcer_texte=["title"])
_check("une annulation force le seul titre", p.get("forcer_texte") == ["title"],
       f"(lu : {p.get('forcer_texte')})")

print(f"\n{'SUCCÈS' if not echecs else 'ÉCHEC'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
