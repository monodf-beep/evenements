#!/usr/bin/env python3
"""Fixture : la mesure des lieux trouvables gratuitement (scripts.audit_lieux_gratuits).

D'OÙ ÇA VIENT — la provenance mesurée le 2026-08-18 : 79 lieux lus par le code contre 454
payés au modèle, soit 15 %. Avant d'écrire le moindre extracteur, il faut savoir combien de
ces 454 étaient à portée de main. Ce script le compte ; cette fixture vérifie qu'il compte
JUSTE, parce qu'un compteur faux sur ce sujet enverrait brancher du code inutile — ou
renoncer à un gain réel.

CE QU'ELLE PROTÈGE, dans l'ordre :

  1. **un désaccord est compté comme un désaccord.** C'est le seul nombre qui décide : un
     signal qui propose beaucoup en se trompant coûte plus cher que les appels qu'il
     économise, parce qu'une ville fausse part en ligne ;
  2. **le signal « fiche sœur » ne recycle jamais une ville payante.** Sinon la mesure se
     félicite d'économiser une dépense… en la réutilisant ;
  3. **une commune ne se reconnaît qu'en MOT ENTIER.** Le cas près de la frontière est ici :
     « Venice » ne doit pas déclencher « Nice ». Une fixture qui n'aurait que des cas
     favorables passerait au vert sur un compteur faux — c'est le reproche de CLAUDE.md
     aux portillons du 06/08 ;
  4. **un zéro dit d'où il vient** : aucune fiche présentée n'est autre chose qu'aucun
     signal efficace.

Lancer : .venv/bin/python -m tests.test_audit_lieux_gratuits
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import audit_lieux_gratuits as A  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# ── La reconnaissance de commune, isolée ───────────────────────────────────────
communes = {"nice": "Nice", "aix les bains": "Aix Les Bains", "annecy": "Annecy"}
verifier("une commune est reconnue dans un titre",
         A.commune_dans("Festival de jazz à Annecy", communes) == "Annecy")
verifier("LE CAS QUI DOIT ÉCHOUER : « Venice » ne déclenche pas « Nice »",
         A.commune_dans("Biennale de Venice", communes) == "", "faux positif")
verifier("les accents et la casse ne font pas rater une commune",
         A.commune_dans("Concert à AIX-LES-BAINS", communes) == "Aix Les Bains")
verifier("un texte sans commune ne propose rien",
         A.commune_dans("Exposition de printemps", communes) == "")


# ── La mesure, sur une base jetable ────────────────────────────────────────────
# LES SEPT COLONNES QUE LA MESURE LIT, et rien d'autre. Le schéma complet passerait par
# `scripts.scraper_events.init_db`, mais ce module importe `feedparser`, absent de
# l'environnement où tourne cette fixture — et surtout la mesure ne touche à aucune autre
# colonne. Même pratique que tests/test_traduction_garage.py. Ce qui compte, et qui est
# respecté : la base est JETABLE, jamais data/events.db (CLAUDE.md, « Développement »).
SCHEMA = ("CREATE TABLE events_raw (id INTEGER PRIMARY KEY, title TEXT, url_source TEXT, "
          "lieu TEXT, ville TEXT, venue_source TEXT, date_event_start TEXT, "
          "date_event_end TEXT, duplicate_of INTEGER, translation_of INTEGER)")


def base_jetable(lignes):
    """Une base neuve, jamais data/events.db (CLAUDE.md, « Développement »)."""
    chemin = Path(tempfile.mkdtemp()) / "fixture.db"
    conn = sqlite3.connect(chemin)
    conn.execute(SCHEMA)
    for lg in lignes:
        conn.execute(
            "INSERT INTO events_raw (title, url_source, lieu, ville, venue_source, "
            "date_event_start, date_event_end) VALUES (?,?,?,?,?,?,?)",
            (lg["title"], lg["url"], lg.get("lieu", ""), lg.get("ville", ""),
             lg["venue_source"], "2099-01-01", "2099-01-01"))
    conn.commit()
    return conn


A_COMMUNES = A.charger_communes()
verifier("les listes de communes du dépôt se chargent", len(A_COMMUNES) > 500,
         f"{len(A_COMMUNES)} communes")

conn = base_jetable([
    # Payée, et le titre porte la bonne commune → un accord.
    {"title": "Marché de Noël à Annecy", "url": "https://x.fr/a", "ville": "Annecy",
     "venue_source": "llm"},
    # Payée, et le titre porte une AUTRE commune que celle retenue → un désaccord, qui
    # doit se voir : c'est lui qui interdit de brancher le signal les yeux fermés.
    {"title": "Concert à Chambéry", "url": "https://x.fr/b", "ville": "Annecy",
     "venue_source": "llm"},
    # Payée, aucun signal : ni commune dans le titre, ni dans l'URL.
    {"title": "Exposition de printemps", "url": "https://x.fr/c", "ville": "Annecy",
     "venue_source": "web"},
    # GRATUITE : elle n'est pas mesurée, mais elle alimente le vivier « fiche sœur ».
    {"title": "Marché de Noël à Annecy", "url": "https://x.fr/d", "ville": "Annecy",
     "venue_source": "page"},
])
m = A.mesurer(conn)

verifier("seules les fiches PAYÉES sont mesurées", m["fiches_payees"] == 3,
         str(m["fiches_payees"]))
verifier("le signal « titre » tombe juste une fois", m["signaux"]["titre"]["accord"] == 1,
         str(m["signaux"]["titre"]))
verifier("et son désaccord est COMPTÉ, pas absorbé",
         m["signaux"]["titre"]["desaccord"] == 1, str(m["signaux"]["titre"]))
# CE QUE « COUVERT » VEUT DIRE, et c'est là que je m'étais trompé en écrivant l'attendu :
# seule la fiche 1 est couverte. La fiche 2 PROPOSE quelque chose (« Chambéry ») mais se
# trompe — proposer n'est pas couvrir, sinon le taux de couverture compterait les erreurs
# comme des réussites et donnerait exactement le feu vert qu'il faut refuser. La fiche 3 ne
# propose rien.
verifier("« couvert » veut dire D'ACCORD : une proposition fausse ne couvre pas",
         m["couverts_par_au_moins_un_signal"] == 1,
         str(m["couverts_par_au_moins_un_signal"]))
verifier("les désaccords sont rendus en clair, pour être LUS",
         any(d["signal"] == "titre" for d in m["desaccords"]), str(m["desaccords"]))
conn.close()

# ── Le vivier des sœurs ne doit contenir AUCUNE ville payante ──────────────────
conn = base_jetable([
    {"title": "Fête du lac", "url": "https://x.fr/e", "ville": "Annecy",
     "venue_source": "llm"},
    # Même titre, ville venue elle aussi d'un appel payant : elle ne doit PAS servir de
    # source « gratuite » à sa jumelle, sinon on se félicite d'éviter une dépense qu'on
    # ne fait que réutiliser.
    {"title": "Fête du lac", "url": "https://x.fr/f", "ville": "Annecy",
     "venue_source": "web"},
])
m2 = A.mesurer(conn)
verifier("« soeur » ne propose rien quand la seule jumelle est payante",
         m2["signaux"]["soeur"]["propose"] == 0, str(m2["signaux"]["soeur"]))
verifier("le vivier des sœurs gratuites est bien vide ici",
         m2["soeurs_disponibles"] == 0, str(m2["soeurs_disponibles"]))
conn.close()

# ── Un zéro doit dire d'où il vient ────────────────────────────────────────────
conn = base_jetable([])
vide = A.rapport(A.mesurer(conn))
verifier("aucune fiche présentée est DIT, et distingué d'un signal inefficace",
         "AUCUNE fiche" in vide and "signal inefficace" in vide, vide[-200:])
conn.close()

# ── Le rapport porte son périmètre à côté de ses nombres (règle 6) ─────────────
conn = base_jetable([
    {"title": "Marché de Noël à Annecy", "url": "https://x.fr/a", "ville": "Annecy",
     "venue_source": "llm"}])
texte = A.rapport(A.mesurer(conn))
verifier("le périmètre est écrit à côté des nombres",
         "Périmètre :" in texte and "non doublons" in texte, texte[:300])
verifier("le rapport prévient que l'étalon est le modèle, pas la vérité",
         "n'est pas la vérité" in texte, texte[-400:])
conn.close()

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
