#!/usr/bin/env python3
"""Fixture : le portillon de langue bloque une "traduction" dont le TITRE est resté
dans la langue source, même quand la description, elle, a été correctement traduite.

INCIDENT RÉEL, trouvé le 2026-08-06 : WP#2174 « La Saint-Ours 2026 - Rendez Vous en
Vallée d'Aoste » publié comme fiche ITALIENNE (translation_of=473, url_source=
'translated:473:it'). La description était de l'italien correct ; le titre, lui,
était resté mot pour mot celui de l'original français. Le seul filet existant
(`batch_report.verdict_titre_traduit`) compare l'IDENTITÉ du titre à l'original —
un titre recopié tel quel « partage » trivialement tous ses mots avec sa source, donc
passait ce contrôle sans jamais broncher. `utils.lang.detect_lang(titre, description)`
n'aurait pas vu le problème non plus : la description, plus longue, noie le signal
du titre (vérifié : la fonction combinée conclut bien 'it' sur ce cas réel).

Deux volets :
  1. utils.lang.titre_semble_intraduit — la fonction pure, sur des cas réels tirés
     de la base (titres déjà traduits, noms propres neutres, le cas Saint-Ours).
  2. scripts.translate_events._translate_one_interne — le portillon est bien câblé :
     REFUS, aucun appel à publish_to_as, rien écrit en base.

⚠️ Aucun réseau : translate_title_desc et publish_to_as sont monkey-patchées.

Lancer : .venv/bin/python -m tests.test_titre_intraduit
"""
import os
import sqlite3
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.lang import titre_semble_intraduit  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ── 1. titre_semble_intraduit, cas réels ────────────────────────────────────────
print("──── titre_semble_intraduit sur des cas réels (base de production) ────")
CAS = [
    # (titre produit, titre SOURCE, cible, doit_signaler)
    # LE VRAI BUG (WP#2174) : titre recopié mot pour mot depuis l'original français.
    ("La Saint-Ours 2026 - Rendez Vous en Vallée d'Aoste",
     "La Saint-Ours 2026 - Rendez Vous en Vallée d'Aoste", "it", True),
    # LE FAUX POSITIF DU 2026-08-08 (fiche 3588, refusée à tort en production) :
    # « compie 50 anni » est de l'italien correct, la traduction a fonctionné — seul
    # « Rencontre », NOM PROPRE de l'événement, portait un marqueur français. Un nom
    # propre français reste français en version italienne, c'est la règle en Vallée
    # d'Aoste bilingue. Le titre a bien été RÉÉCRIT (< 80 % de mots repris) → pas de refus.
    ("La Rencontre Valdôtaine compie 50 anni",
     "La Rencontre Valdôtaine fête ses 50 ans", "it", False),
    # Nom propre pur, identique des deux côtés : recopié, mais il n'y a RIEN à traduire
    # — score neutre (0,0), donc jamais signalé malgré la reprise à 100 %.
    ("Katy Perry", "Katy Perry", "it", False),
    ("Orelsan", "Orelsan", "it", False),
    # Traductions normales, dans les deux sens.
    ("Visita al Castello di Montrottier", "Visite au Château de Montrottier", "it", False),
    ("60 minutes de violoncelle", "60 minuti di violoncello", "fr", False),
    ("Le 44TFF sera dédié à Marilyn Monroe",
     "Il 44TFF sarà dedicato a Marilyn Monroe", "fr", False),
    # Sans titre source, on ne peut rien conclure : silence plutôt que devinette.
    ("La Saint-Ours 2026 - Rendez Vous en Vallée d'Aoste", "", "it", False),
]
for titre, source, cible, attendu in CAS:
    obtenu = titre_semble_intraduit(titre, cible, source)
    _check(f"cible={cible} « {titre[:42]} » → signalé={obtenu}", obtenu == attendu,
          f"attendu {attendu}")

# ── 2. Câblage dans _translate_one_interne : REFUS, rien publié, rien écrit ─────
print("\n──── _translate_one_interne : le titre non traduit est REFUSÉ ────")
tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.translate_events as te  # noqa: E402

te.DB_PATH = tmp

conn = sqlite3.connect(tmp)
init_db(conn)
conn.execute(
    "INSERT INTO events_raw (id, title, description, url_source, lieu, ville, "
    "territoire, statut, llm_score, date_event_start, date_event_end, wp_post_id_as) "
    "VALUES (473, 'La Saint-Ours 2026 - Rendez Vous en Vallée d''Aoste', "
    "'La Saint-Ours est un rendez-vous artisanal dans le centre historique d''Aoste.', "
    "'https://a.fr/473', 'Centre historique', 'Aoste', 'Vallee-Aoste', 'evaluated', 8, "
    "'2027-01-30', '2027-01-31', 772)")
conn.commit()
conn.close()

ev = {
    "id": 473, "title": "La Saint-Ours 2026 - Rendez Vous en Vallée d'Aoste",
    "description": "La Saint-Ours est un rendez-vous artisanal dans le centre "
                   "historique d'Aoste.",
    "lieu": "Centre historique", "ville": "Aoste", "territoire": "Vallee-Aoste",
    "organisateur": "", "url_image": "", "enrich_data": "", "article_title": "",
    "wp_permalink_as": "https://agendasabauda.eu/evenement/la-saint-ours/",
    "wp_post_id_as": 772,
}


class _Args:
    apply = True
    model = "modele-test"


appels_publish = []
te.publish_to_as = lambda ev: (appels_publish.append(ev) or (0, "", ""))
# Portillon SÉPARÉ (WP#7286, 2026-08-06) : l'original doit être 'publish' sur
# WordPress au moment de la traduction — sans réseau ni WP_AS_URL en test, il
# répond toujours False. Neutralisé ici pour isoler CE test sur son propre
# portillon (la langue), pas sur celui-là — cf. tests/test_wp_original_en_ligne.py
# pour sa propre fixture dédiée.
te.wp_original_est_en_ligne = lambda wp_id: True
# Le titre "traduit" reste identique au français — exactement le bug réel.
te.translate_title_desc = lambda *a, **k: {
    "title": "La Saint-Ours 2026 - Rendez Vous en Vallée d'Aoste",
    "description": "La Saint-Ours 2026 è un evento culturale che si svolge in Vallée "
                   "d'Aoste, con prodotti tipici e tradizioni locali.",
}

resultat = te._translate_one_interne(
    ev, _Args(), client=object(), api_key="factice", voix="", wp_url="",
    auth=("", ""), img_lang={}, img_lang_lock=threading.Lock())

_check("résultat = 'refus'", resultat == "refus", f"obtenu {resultat!r}")
_check("publish_to_as JAMAIS appelé", appels_publish == [], str(appels_publish))

conn = sqlite3.connect(tmp)
n = conn.execute("SELECT COUNT(*) FROM events_raw").fetchone()[0]
translated_at = conn.execute(
    "SELECT translated_at FROM events_raw WHERE id=473").fetchone()[0]
conn.close()
_check("aucune fiche traduite créée en base (toujours 1 seule ligne)", n == 1, f"n={n}")
_check("translated_at de l'original toujours vide (repasse au run suivant)",
      not translated_at, repr(translated_at))

# ── 3. Contre-épreuve : une VRAIE traduction du titre passe normalement ─────────
print("\n──── contre-épreuve : titre correctement traduit → publié normalement ────")
appels_publish.clear()
te.publish_to_as = lambda ev: (appels_publish.append(ev) or (9999, "https://x/", "https://x/img.jpg"))
te.translate_title_desc = lambda *a, **k: {
    "title": "La Sant'Orso 2026 - Fiera dell'artigianato in Valle d'Aosta",
    "description": "La Sant'Orso 2026 è un evento culturale che si svolge in Vallée "
                   "d'Aoste, con prodotti tipici e tradizioni locali.",
}
resultat = te._translate_one_interne(
    ev, _Args(), client=object(), api_key="factice", voix="", wp_url="",
    auth=("", ""), img_lang={}, img_lang_lock=threading.Lock())
_check("résultat = 'done'", resultat == "done", f"obtenu {resultat!r}")
_check("publish_to_as appelé une fois", len(appels_publish) == 1, str(appels_publish))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
