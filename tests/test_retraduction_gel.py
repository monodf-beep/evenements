#!/usr/bin/env python3
"""Fixture : une re-traduction ne se rejoue pas sur une fiche au TEXTE GELÉ (2026-09-28).

⚠️ BASE JETABLE (init_db sur un fichier temporaire). AUCUN réseau, AUCUN appel LLM : les
trois portes vers l'extérieur (`postes_geles`, `translate_*`, `publish_to_as`) sont
remplacées par des doublures qui COMPTENT leurs appels — c'est le compteur d'appels API
qui prouve l'économie, pas la lecture du code.

D'OÙ ÇA VIENT. Le 28/09, `translate_events --retranslate 528 1016 --apply` annonce
« ✅ [1016→4146] versants fr / it » et « ✅ [528→3547] versants fr / it ». Dans le même
journal, deux lignes plus haut :

    Fiche GELÉE (retouche à la main du 2026-09-23 02:16:41)
      — champs non écrits : title, content, excerpt, seo

Interrogées une par une, les deux pages (WP#2340, WP#3807) étaient servies du côté
ITALIEN avec un TITRE FRANÇAIS. Le contrôle final ne regardait que le VERSANT, déjà bon
avant la commande : il ne pouvait donc jamais échouer. La base a reçu la traduction, la
page l'a refusée, et le bilan a rapporté l'intention (règle 6). Coût : quatre appels API
par passage, et `repair_lien_polylang --retraduire` tourne chaque semaine — le refus qui
se rejoue à l'identique sur la MÊME entrée, que la règle 3 interdit.

CE QUE LA FIXTURE VÉRIFIE :

  1. LE TÉMOIN ROUGE : sur la matière réelle, l'ANCIEN critère (« les deux versants sont
     bien fr / it ») rend VRAI alors que le site refuse le texte. Sans ce témoin, on ne
     saurait pas ce qui est réparé — et un témoin qui n'a jamais été rouge ne prouve rien
     (docs/ERREURS_2026-09-14).
  2. Le portillon AVANT les appels : la gelée est écartée pour ZÉRO appel API, et le
     journal nomme son rouvreur (`gel_texte --degel`).
  3. ⚠️ LE CAS FRONTIÈRE QUI DOIT PASSER, choisi près de la frontière : un jumeau du MÊME
     LOT, non gelé, est re-traduit normalement — le portillon ne doit pas prendre le lot
     en otage.
  4. Le site MUET (route sans réponse) ne vaut pas « aucune gelée » : on continue, et
     c'est la contre-épreuve d'APRÈS écriture qui attrape la gelée. Le bilan dit alors
     que son compte est partiel.
  5. Le bilan COMPTE les gelées à part (règle 6).

Lancer : python3 -m tests.test_retraduction_gel
"""
import argparse
import logging
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
import scripts.translate_events as te               # noqa: E402

te.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


AUJ = date.today()
D, F = (AUJ + timedelta(days=8)).isoformat(), (AUJ + timedelta(days=15)).isoformat()
ART_FR = ('{"article": {"titre": "Orlando de Haendel", "chapo": "Le Haendel de la '
          'nouvelle saison", "corps": "Le baroque revient dans la salle de l\'Opera, '
          'avec les musiciens de la maison et une mise en scene sobre."}}')

# Les deux couples réels du 28/09 (ORIGINAL → JUMEAU), plus un témoin non gelé.
LIGNES = [
    # id,  translation_of, wp_post_id_as, titre,                     lang
    (528,  None, 745,  "Orlando de Haendel à l'Opéra de Nice", None),
    (3547, 528,  2340, "Orlando de Haendel à l'Opéra Nice Côte d'Azur", "it"),   # GELÉE
    (1016, None, 3806, "Au château d'Ivrea, l'art contemporain", None),
    (4146, 1016, 3807, "Au château d'Ivrea, l'art contemporain en dialogue", "it"),  # GELÉE
    (900,  None, 4100, "Carmen à l'Opéra de Nice", None),
    (901,  900,  4101, "Carmen all'Opéra di Nizza", "it"),                        # SAINE
]
GELES_SITE = {2340, 3807}          # ce que répond GET cs/v1/gel

conn = sqlite3.connect(tmp)
init_db(conn)
for i, orig, wp, titre, lang in LIGNES:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, territoire, ville, "
        "lieu, statut, wp_post_id_as, translation_of, translated_lang, date_event_start, "
        "date_event_end, enrich_data, duplicate_of) "
        "VALUES (?,?,?,?,'comte-de-nice','Nice','Opéra','published_sub',?,?,?,?,?,?,NULL)",
        (i, titre, "Description de l'événement, en français.", f"https://src.example/{i}",
         wp, orig, lang, D, F, ART_FR))
conn.commit()
conn.close()

# ── Les doublures : elles COMPTENT, et la première rend ce que le site a répondu le 28/09.
appels = {"llm": 0, "publish": 0}
GEL_REPONSE = {"gele": True, "depuis": "2026-09-23 02:16:41",
               "motif": "Refonte SEO/lisibilite doctrine editoriale - batch 5",
               "champs": ["title", "content", "excerpt", "seo"], "forces": [], "restaures": []}


def _fausse_traduction(client, model, titre, desc, tgt, voix):
    appels["llm"] += 1
    return {"title": "Orlando di Haendel al Teatro dell'Opera",
            "description": "Descrizione dell'evento, in italiano."}


def _faux_article(client, model, src, tgt, voix):
    appels["llm"] += 1
    return ('{"article": {"titre": "Orlando di Haendel", "chapo": "Il barocco torna", '
            '"corps": "Il barocco torna nella sala del Teatro, con i musicisti della casa."}}')


def _faux_publish(event, skip_media=False, forcer_texte=None, retour=None):
    appels["publish"] += 1
    if retour is not None:
        gele = int(event.get("wp_post_id_as") or 0) in GELES_SITE
        retour["gel"] = dict(GEL_REPONSE) if gele else {"gele": False, "depuis": "",
                                                        "motif": "", "champs": [],
                                                        "forces": [], "restaures": []}
        retour["updated"] = True
    return int(event.get("wp_post_id_as") or 0), "https://agendasabauda.eu/x/", ""


te.translate_title_desc = _fausse_traduction
te.translate_article = _faux_article
te.publish_to_as = _faux_publish
te.verdict_titre_traduit = lambda titres, orig: ("ok", "")
te.titre_semble_intraduit = lambda *a, **k: False
te.titre_reecrit_mauvaise_langue = lambda *a, **k: False

journal: list[str] = []


class _Capte(logging.Handler):
    def emit(self, record):
        journal.append(record.getMessage())


te.log.addHandler(_Capte())
te.log.setLevel(logging.INFO)


def _args(ids):
    return argparse.Namespace(ids=list(ids), retranslate=True, apply=True,
                              model="modele-de-fixture", cap=None)


def _lance(ids, geles):
    appels["llm"] = appels["publish"] = 0
    journal.clear()
    te.postes_geles = lambda: (None if geles is None else set(geles))
    rc = te._retranslate(_args(ids), client=object(), voix="")
    return rc, "\n".join(journal)


print("──── 1. témoin rouge : l'ancien critère ne pouvait pas échouer ────")
# L'ancien ✅ portait sur les versants des deux permaliens, qui étaient DÉJÀ bons avant la
# commande. On rejoue ce critère-là, tel quel, sur la matière du 28/09.
_ancien_verdict = ("fr", "it") == ("fr", "it")
_check("l'ANCIEN critère (« versants fr / it ») rend VRAI sur la paire gelée",
       _ancien_verdict is True)
_check("   alors que le site refuse les quatre champs du texte",
       GEL_REPONSE["gele"] and GEL_REPONSE["champs"] == ["title", "content", "excerpt", "seo"])

print("\n──── 2. le portillon : écartée AVANT de dépenser un appel ────")
rc, out = _lance([528], GELES_SITE)
_check("rc=0", rc == 0, out)
_check("ZÉRO appel LLM dépensé sur la gelée", appels["llm"] == 0, f"llm={appels['llm']}")
_check("   et aucune écriture WordPress", appels["publish"] == 0, f"publish={appels['publish']}")
_check("le journal dit REFUS et pourquoi", "REFUS de retraduction" in out and "GELÉ" in out, out)
_check("   et nomme le rouvreur, avec l'id LOCAL (pas le numéro de post)",
       "gel_texte --degel 3547 --apply" in out, out)
_check("le bilan compte la gelée À PART", "1 écarté(s) pour TEXTE GELÉ (liste du site)" in out, out)
_check("   et renvoie à la file, qui porte son périmètre", "gel_texte --liste" in out, out)

print("\n   ⚠️ 3. le cas frontière qui doit PASSER : le lot n'est pas pris en otage")
rc, out = _lance([528, 1016, 900], GELES_SITE)
_check("rc=0", rc == 0, out)
_check("le jumeau SAIN (901) est bien re-traduit", "[jumeau 901] re-traduit" in out, out)
_check("   une seule fiche publiée, la saine", appels["publish"] == 1, f"publish={appels['publish']}")
_check("   et les appels LLM ne sont dépensés que pour elle (titre + article)",
       appels["llm"] == 2, f"llm={appels['llm']}")
_check("le bilan : 1 mis à jour, 2 gelées",
       "1 jumeau(x) mis à jour" in out and "2 écarté(s) pour TEXTE GELÉ" in out, out)
conn = sqlite3.connect(tmp)
titres = dict(conn.execute("SELECT id, title FROM events_raw WHERE id IN (901, 3547, 4146)"))
conn.close()
_check("la base a bien changé POUR la saine", titres[901].startswith("Orlando di Haendel"),
       titres[901])
_check("   et n'a PAS changé pour les gelées (le site les aurait refusées)",
       titres[3547].startswith("Orlando de Haendel") and titres[4146].startswith("Au château"),
       f"{titres[3547]!r} / {titres[4146]!r}")

print("\n──── 4. site MUET ≠ aucune gelée : la contre-épreuve d'après coup ────")
rc, out = _lance([528], None)
_check("rc=0 — un site muet ne bloque pas le lot", rc == 0, out)
_check("le journal DIT qu'on ne sait pas", "le site n'a pas répondu" in out, out)
_check("l'écriture a bien été tentée", appels["publish"] == 1, f"publish={appels['publish']}")
_check("et le résultat rapporté est le REFUS du site, pas un ✅",
       "TEXTE NON PUBLIÉ" in out and "divergent" in out, out)
_check("   avec la commande de réparation à 0 appel API",
       "publish_batch_as --update --ids 3547" in out, out)
_check("le bilan dit que son compte est PARTIEL",
       "1 écarté(s) pour TEXTE GELÉ (site muet : compte partiel)" in out, out)
_check("   et n'annonce aucun succès", "0 jumeau(x) mis à jour" in out, out)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
