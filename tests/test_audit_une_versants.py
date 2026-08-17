#!/usr/bin/env python3
"""Fixture : « À la une » doit séparer les versants sur la VRAIE langue de la page.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau, aucun LLM.

D'OÙ ÇA VIENT. Le 2026-08-17 au matin, après le premier correctif de séparation des
versants, `audit_une` a rendu ceci :

    ### versant FRANÇAIS
    - 2026-08-31 (14 j) : Palio Montis Regalis: la t · Fiera Nazionale del Pepero · …
    ### versant ITALIEN
    - 2026-08-31 (14 j) : Concerto della Filarmonica · Brahms / Šostakovič

Trois titres italiens annoncés comme la une d'un lecteur FRANCOPHONE — alors que la
version française du Palio est publiée (WP#2285) et que c'est elle qui s'afficherait.
Et un versant italien qui paraît exsangue alors que tout le stock piémontais est de ce
côté-là.

LA CAUSE, en une ligne : le tri se faisait sur `translated_lang or "fr"`. Ce champ ne dit
pas « langue de la fiche », il dit « cette ligne est une TRADUCTION vers telle langue ».
Un original ne le porte jamais, quelle que soit sa langue — donc tous les originaux
italiens basculaient côté français.

C'est le même défaut que la veille (« le rapport montrait une une qui n'existe pour
personne »), une couche plus bas : la séparation avait été réparée, pas le critère qui
sépare. D'où cette fixture, qui tient le CRITÈRE et pas seulement la présence de deux
sections.

CE QU'ELLE SURVEILLE :
  1. un ORIGINAL italien (aucun `translated_lang`) part du côté ITALIEN ;
  2. sa traduction française part du côté FRANÇAIS — la paire ne s'entasse pas d'un
     seul bord ;
  3. un original français reste français : le correctif ne bascule pas tout à l'inverse
     (c'est le cas-qui-doit-passer, pris près de la frontière — un titre français sur un
     territoire italophone) ;
  4. et quand un versant a moins de trois candidates, la ligne le DIT au lieu d'afficher
     deux titres comme si de rien n'était.

Lancer : .venv/bin/python -m tests.test_audit_une_versants
"""
import contextlib
import io
import json
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

from scripts.scraper_events import init_db  # noqa: E402
import scripts.audit_une as au  # noqa: E402

au.DB_PATH = tmp
DANS_10_J = (date.today() + timedelta(days=10)).isoformat()
CARTES_ATTENDUES = au.CARTES_UNE

# Un intérêt confortable : ces fiches doivent TOUTES entrer en une, sinon le test ne
# mesure plus la répartition par langue mais les seuils, qui ont leur propre fixture.
DETAIL = json.dumps({"rayonnement": {"points": 2}, "specificite_territoriale": {"points": 1},
                     "edition_tradition": {"points": 2}, "notoriete_lieu": {"points": 3}})


def _article(chapo: str, corps: str) -> str:
    return json.dumps({"article": {"chapo": chapo, "corps": corps},
                       "home": {"affiches": "deux"}})


# (id, titre, territoire, translation_of, translated_lang, article_title, chapo, corps)
FICHES = [
    # 1. L'ORIGINAL ITALIEN, celui que le tri d'origine expédiait côté français.
    (1, "Fiera Nazionale del Peperone di Carmagnola", "Piemonte", None, None,
     "Fiera Nazionale del Peperone di Carmagnola",
     "La sagra più grande del Piemonte torna in città.",
     "Ogni sera spettacoli gratuiti nella piazza, con degustazioni e mostre "
     "dedicate al peperone; l'ingresso è libero per tutta la durata della "
     "manifestazione."),
    # 2. Sa traduction française — l'autre moitié de la paire.
    (2, "Foire nationale du poivron de Carmagnola", "Piemonte", 1, "fr",
     "Foire nationale du poivron de Carmagnola",
     "La plus grande fête du Piémont revient dans la ville.",
     "Chaque soirée propose des spectacles gratuits sur la place, avec des "
     "dégustations et une exposition consacrée au poivron ; l'entrée est libre "
     "pendant toute la durée de la manifestation."),
    # 3. ⚠️ LE CAS QUI DOIT PASSER, choisi près de la frontière : un original FRANÇAIS
    #    sur un territoire italophone. Si le correctif se contentait de renvoyer la
    #    langue du territoire, celui-ci basculerait à tort — et la fixture serait
    #    passée au vert sur un critère encore faux, comme le portillon du 2026-08-06.
    (3, "Le Grand Continent : rencontre au Forte di Bard", "Piemonte", None, None,
     "Le Grand Continent : rencontre au Forte di Bard",
     "Une conférence en français pour cette nouvelle journée de rencontres.",
     "Les intervenants se retrouvent dans la salle du fort pour une soirée "
     "ouverte à tous, avec une exposition et des ateliers pour les enfants tout "
     "au long de la journée."),
    # 4. Une troisième page française, pour que ce versant-là soit COMPLET. Sans elle,
    #    les deux versants seraient incomplets et le contrôle « une ligne complète ne
    #    porte aucun avertissement » n'aurait rien à mesurer : il passait au vert sur une
    #    ligne vide. C'est exactement le travers que CLAUDE.md reproche aux fixtures qui
    #    ne cherchent qu'à se donner raison.
    (4, "Fête du lac d'Annecy", "Savoie", None, None,
     "Fête du lac d'Annecy",
     "La grande soirée d'été revient sur les quais.",
     "Le spectacle est proposé chaque année dans cette ville, avec une entrée "
     "payante pour les gradins et un accès libre depuis les berges pour tous les "
     "spectateurs."),
]

conn = sqlite3.connect(tmp)
init_db(conn)
for eid, titre, terr, orig, lang, art_t, chapo, corps in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, wp_post_id_as, statut, "
        "llm_categorie, llm_score_detail, date_event_start, date_event_end, territoire, "
        "duplicate_of, enrich_status, home_score, url_image, enrich_data, article_title, "
        "translation_of, translated_lang) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,NULL,?,?,?,?,?,?,?)",
        (eid, titre, f"https://a.fr/{eid}", 900 + eid, "published_sub",
         "Gastronomie & Sagre", DETAIL, DANS_10_J, DANS_10_J, terr,
         "enriched", 8.0, f"https://exemple.fr/photos/{eid}.jpg",
         _article(chapo, corps), art_t, orig, lang))
conn.commit()
conn.close()

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── le critère de langue, fiche par fiche ────")
lignes = {f[0]: dict(zip(
    ("id", "title", "territoire", "translation_of", "translated_lang",
     "article_title"), f[:6])) for f in FICHES}
for f in FICHES:
    lignes[f[0]]["enrich_data"] = _article(f[6], f[7])

_check("un ORIGINAL italien est reconnu italien — sans `translated_lang`, "
       "c'est l'article qui fait foi",
       au.langue_fiche(lignes[1]) == "it", au.langue_fiche(lignes[1]))
_check("sa TRADUCTION française est reconnue française",
       au.langue_fiche(lignes[2]) == "fr", au.langue_fiche(lignes[2]))
_check("⚠️ et un original FRANÇAIS sur territoire italophone reste français "
       "(le cas qui doit passer)",
       au.langue_fiche(lignes[3]) == "fr", au.langue_fiche(lignes[3]))

print("\n──── ce que le rapport affiche ────")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    au.main([])
sortie = buf.getvalue()

fr = sortie.split("versant FRANÇAIS")[-1].split("versant ITALIEN")[0]
it = sortie.split("versant ITALIEN")[-1]

_check("le versant italien montre la fiche italienne",
       "Fiera Nazionale del Pepe" in it, it[:400])
_check("   et le versant français ne la montre PAS — c'était tout le défaut",
       "Fiera Nazionale del Pepe" not in fr, fr[:400])
_check("le versant français montre la version FRANÇAISE de la même fête",
       "Foire nationale du poiv" in fr, fr[:400])
_check("   et le versant italien ne la montre pas",
       "Foire nationale du poiv" not in it, it[:400])
_check("chaque versant annonce combien de pages il a de son côté",
       "page(s) publiée(s) de ce côté" in sortie,
       sortie[sortie.find("versant FRANÇAIS") - 40:][:200])

print("\n──── le trou se dit, il ne se devine pas ────")
# Un seul candidat côté italien : la section en affiche trois. La ligne doit annoncer
# les deux cartes vides plutôt que de se lire comme un relevé normal.
_check("une ligne à moins de trois candidates signale les cartes vides",
       "carte(s) vide(s)" in it, it[:600])
_check("   et elle dit COMBIEN il en manque", "2 carte(s) vide(s)" in it, it[:600])
# On borne au J+0 : plus loin, les trois fiches de la fixture sont passées et les
# lignes se vident LÉGITIMEMENT. Un contrôle qui porterait sur tout le bloc mesurerait
# ça, pas l'avertissement — et il partirait au rouge pour la bonne raison, ce qui est
# la pire espèce d'échec : celle qu'on finit par désactiver.
ligne_fr_j0 = [l for l in fr.splitlines() if l.startswith("- **") and "( 0 j)" in l][0]
_check("le versant français a bien ses trois candidates aujourd'hui…",
       ligne_fr_j0.count("·") == CARTES_ATTENDUES - 1, ligne_fr_j0)
_check("   …et sa ligne ne porte donc AUCUN avertissement — la mention n'apparaît "
       "que quand il manque vraiment quelque chose",
       "carte(s) vide(s)" not in ligne_fr_j0, ligne_fr_j0)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
