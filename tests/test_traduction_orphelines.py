#!/usr/bin/env python3
"""Fixture : une fiche marquée traduite dont la jumelle a DISPARU doit repasser en file —
et une fiche seulement DÉLIÉE ne doit surtout pas repasser.

D'OÙ ÇA VIENT — 2026-09-15. Franck : « encore des événements sans traduction ! », puis
« ça doit suivre un processus ». Mesuré sur WordPress le jour même : 202 fiches
françaises publiées, 117 sans jumelle italienne, dont 63 encore devant nous, alors que
le cron traduit 25 fiches par jour. `translated_at` était un état terminal sans rouvreur
(règle 3) : posé au succès, jamais effacé, y compris quand la jumelle n'existait plus.

LA FRONTIÈRE, et c'est tout l'enjeu de cette fixture : `unlink_bad_translations` efface
`translation_of` sur une paire mal appariée SANS supprimer la jumelle. Un rouvreur qui ne
regarderait que `translation_of` rouvrirait ces fiches-là et fabriquerait une TROISIÈME
fiche, doublon de la jumelle existante. Le marqueur `url_source = 'translated:<id>:<lang>'`
survit au déliage : c'est lui qui tient la frontière, et le cas 2 ci-dessous est celui qui
doit PASSER sans être touché.

Base jetable, aucun réseau, aucun appel LLM.

Lancer : .venv/bin/python -m tests.test_traduction_orphelines
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import translate_events as te          # noqa: E402
from scripts.audit_traduction_manquante import classe  # noqa: E402

# LES COLONNES QUE LES DEUX MESURES LISENT, et rien d'autre. Le schéma complet passerait
# par `scripts.scraper_events.init_db`, mais ce module importe `feedparser`, absent de
# l'environnement où tourne cette fixture — même pratique que tests/test_traduction_garage.py
# et tests/test_audit_lieux_gratuits.py. Ce qui compte et qui est respecté : la base est
# JETABLE, jamais data/events.db.
SCHEMA = ("CREATE TABLE events_raw (id INTEGER PRIMARY KEY, title TEXT, "
          "article_title TEXT, description TEXT, lieu TEXT, ville TEXT, "
          "organisateur TEXT, enrich_data TEXT, url_source TEXT UNIQUE, "
          "wp_post_id_as INTEGER, duplicate_of INTEGER, translation_of INTEGER, "
          "translated_lang TEXT, translated_at TEXT, llm_score INTEGER, "
          "user_score INTEGER, date_event_start TEXT, date_event_end TEXT, "
          "traduction_tentatives INTEGER DEFAULT 0, traduction_matiere TEXT)")

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


tmp = Path(tempfile.mkdtemp()) / "jetable.db"
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
conn.execute(SCHEMA)
conn.commit()


def ins(**kw):
    kw.setdefault("duplicate_of", None)
    cols = ",".join(kw)
    conn.execute(f"INSERT INTO events_raw ({cols}) VALUES ({','.join('?' * len(kw))})",
                 list(kw.values()))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


# 1 — LE DÉFAUT : traduite un jour, plus aucune jumelle nulle part.
orphelin = ins(title="Riccardo Benassi à la Fondazione Merz", url_source="https://ex.it/1",
               wp_post_id_as=7522, translated_at="2026-08-14 10:00:00", llm_score=7)

# 2 — LE CAS QUI DOIT RESTER FERMÉ, choisi près de la frontière : la jumelle a été DÉLIÉE
# (translation_of effacé par unlink_bad_translations) mais elle existe toujours. Seul le
# marqueur url_source la trahit. La rouvrir fabriquerait une troisième fiche.
delie = ins(title="La Rencontre Valdôtaine", url_source="https://ex.it/2",
            wp_post_id_as=3588, translated_at="2026-08-01 10:00:00", llm_score=7)
ins(title="L'Incontro Valdostano", url_source=f"translated:{delie}:it",
    wp_post_id_as=9001, llm_score=7)          # jumelle orpheline mais bien vivante

# 3 — paire saine : jumelle liée, rien à faire.
saine = ins(title="Foire de Saint-Ours", url_source="https://ex.it/3",
            wp_post_id_as=772, translated_at="2026-09-01 10:00:00", llm_score=9)
ins(title="Fiera di Sant'Orso", url_source=f"translated:{saine}:it",
    wp_post_id_as=773, translation_of=saine, translated_lang="it", llm_score=9)

# 4 — jamais publiée : la traduction vient APRÈS la publication, rien à rouvrir.
non_publiee = ins(title="Brouillon", url_source="https://ex.it/4",
                  wp_post_id_as=0, translated_at="2026-08-14 10:00:00", llm_score=7)

# 5 — piège de préfixe : le marqueur d'une AUTRE fiche ne doit pas protéger celle-ci.
# « translated:12:it » ne commence pas par « translated:1: » grâce aux deux-points ; si un
# jour quelqu'un retire ce séparateur, ce cas devient rouge.
piege = ins(title="Piège de préfixe", url_source="https://ex.it/5",
            wp_post_id_as=8000, translated_at="2026-08-14 10:00:00", llm_score=7)
ins(title="Jumelle d'une autre fiche", url_source=f"translated:{piege}9:it",
    wp_post_id_as=8001, llm_score=7)

n = te._rearme_traductions_orphelines(conn)


def ta(i):
    return conn.execute("SELECT translated_at FROM events_raw WHERE id=?", (i,)).fetchone()[0]


verifier("la fiche sans jumelle est ROUVERTE (translated_at effacé)", not ta(orphelin), repr(ta(orphelin)))
verifier("la fiche seulement DÉLIÉE reste fermée — pas de troisième fiche",
         bool(ta(delie)), repr(ta(delie)))
verifier("la paire saine n'est pas touchée", bool(ta(saine)), repr(ta(saine)))
verifier("une fiche jamais publiée n'est pas rouverte", bool(ta(non_publiee)), repr(ta(non_publiee)))
verifier("le marqueur d'une autre fiche ne protège pas celle-ci", not ta(piege), repr(ta(piege)))
verifier("le compteur dit exactement ce qu'il a rouvert", n == 2, f"{n} rouverte(s)")

# Rejouer ne doit rien rouvrir de plus : un rouvreur qui se déclenche en boucle sur les
# mêmes fiches est le martèlement qu'on corrige, pas un rouvreur.
verifier("deuxième passage : plus rien à rouvrir", te._rearme_traductions_orphelines(conn) == 0)

# ── L'AUDIT dit-il la même chose que le rouvreur ? Deux détecteurs pour la même question,
# c'est la racine du 08/09 : ils doivent répondre pareil sur les mêmes fiches.
jumelles = {r["translation_of"]: dict(r) for r in
            conn.execute("SELECT * FROM events_raw WHERE COALESCE(translation_of,0)!=0")}
marqueurs = {r[0] for r in conn.execute(
    "SELECT url_source FROM events_raw WHERE COALESCE(url_source,'') LIKE 'translated:%'")}


def fam(i):
    ev = dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (i,)).fetchone())
    return classe(ev, jumelles, marqueurs, None)[0]


verifier("audit : la rouverte est redevenue une candidate en file", fam(orphelin) == "en_file", fam(orphelin))
verifier("audit : la déliée est nommée « jumelle jamais publiée », jamais « disparue »",
         fam(delie) == "jumelle_jamais_publiee", fam(delie))
verifier("audit : la paire saine ne figure dans aucune famille de manque",
         fam(saine) == "en_file", fam(saine))

# ── La raison d'une jumelle jamais mise en ligne vient des PORTES, pas de moi ───────
# Une jumelle présente en base sans `wp_post_id_as` : l'audit doit dire CE QUI la retient,
# en interrogeant `utils.completeness` et `utils.radar` — les portes que `publish_batch_as`
# applique réellement. La première version de l'audit affirmait « la publication WordPress
# a échoué » : une inférence présentée comme un fait, et fausse pour les cinq fiches
# constatées le 15/09, qui n'ont jamais été présentées à la publication.
orphelin_pub = ins(title="Marisa Merz, La danza delle ore", url_source="https://ex.it/6",
                   wp_post_id_as=763, llm_score=8, translated_at="2026-09-01 10:00:00")
ins(title="Marisa Merz (it)", url_source=f"translated:{orphelin_pub}:it",
    translation_of=orphelin_pub, translated_lang="it", wp_post_id_as=0, llm_score=8)
jumelles = {r["translation_of"]: dict(r) for r in
            conn.execute("SELECT * FROM events_raw WHERE COALESCE(translation_of,0)!=0")}
marqueurs = {r[0] for r in conn.execute(
    "SELECT url_source FROM events_raw WHERE COALESCE(url_source,'') LIKE 'translated:%'")}
famille, precision = classe(
    dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (orphelin_pub,)).fetchone()),
    jumelles, marqueurs, None)
verifier("jumelle en base sans wp_post_id_as : famille « jamais publiée »",
         famille == "jumelle_jamais_publiee", famille)
verifier("et la raison est DONNÉE, pas supposée", "manque" in precision or "statut" in precision
         or "date" in precision, precision)
verifier("une fiche marquée traduite AVEC jumelle en base n'est pas rouverte",
         te._rearme_traductions_orphelines(conn) == 0)

conn.close()
print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
