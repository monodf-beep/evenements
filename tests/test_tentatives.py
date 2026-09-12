#!/usr/bin/env python3
"""Fixture : la mémoire des recherches (utils.tentatives). Base JETABLE.

D'OÙ ÇA VIENT — Franck, 2026-08-18 : « toutes les informations, on les trouve. C'est juste
que des fois c'est mal cherché […] il faut relancer sur des événements spécifiques.
J'aimerais que tu sois autonome dessus. »

Le manque était précis : `lister_a_completer` rendait chaque matin la MÊME liste, sans
mémoire. L'agent rouvrait donc la même page, qui se taisait toujours. Vingt créneaux par
run à refaire ce qui avait déjà échoué.

CE QUE LA FIXTURE EXIGE, et c'est l'exigence de la règle 3 sous une autre forme :

  • une relance doit être DIFFÉRENTE de la tentative ratée — jamais le même angle ;
  • une fiche dont tous les angles sont épuisés SORT de la file (sinon elle la sature —
    les 315 « tarifs non publiés » du 11/08) ;
  • …mais elle y REVIENT après un délai, parce qu'une source publie parfois tard. C'est le
    seul moyen honnête de distinguer « ne le dira jamais » de « ne le dit pas encore » ;
  • et un angle qui a TROUVÉ clôt la recherche : on ne rouvre pas ce qui est résolu.

Lancer : .venv/bin/python -m tests.test_tentatives
"""
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import tentatives as t  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# ── L'escalade : chaque relance change d'angle ──────────────────────────────────
verifier("sans historique, on commence par la page qu'on a",
         t.prochain_angle([]) == "page_fiche")
verifier("après la page muette, on passe à l'organisateur",
         t.prochain_angle([{"angle": "page_fiche", "resultat": "muet"}])
         == "site_organisateur")
verifier("une page INACCESSIBLE ne se re-tente pas non plus (c'est déjà tenté)",
         t.prochain_angle([{"angle": "page_fiche", "resultat": "inaccessible"}])
         == "site_organisateur")

partiel = [{"angle": a, "resultat": "muet"} for a in
           ("page_fiche", "site_organisateur", "commune_ot")]
verifier("le quatrième angle est la recherche par le NOM (la plus rentable le 11/08)",
         t.prochain_angle(partiel) == "recherche_nom")

tous = [{"angle": a, "resultat": "muet"} for a in t.ANGLES]
verifier("quand tout a été essayé, il n'y a plus d'angle", t.prochain_angle(tous) is None)
verifier("et la fiche est déclarée épuisée", t.epuisee(tous))

# ── Ce qui est TROUVÉ n'est plus cherché… mais doit être APPLIQUÉ ───────────────
trouve = [{"angle": "page_fiche", "resultat": "muet"},
          {"angle": "site_organisateur", "resultat": "trouve"}]
verifier("des angles restent : la fiche n'est pas épuisée", not t.epuisee(trouve))
verifier("et la trouvaille est signalée comme EN SOUFFRANCE tant que la fiche est là",
         t.trouvaille_en_souffrance(trouve))
r_trouve = t.resume(trouve)
verifier("le résumé oriente vers l'APPLICATION, plus vers la recherche",
         "PAS APPLIQUÉ" in r_trouve and "completer_verifie" in r_trouve, r_trouve)

# LE CAS ZOMBIE DE PRODUCTION (fiches 4785 et 4809, mesuré le 2026-08-28) : les six
# angles faits, dont un « trouve » jamais appliqué (la porte refusait la colonne image).
# L'ancienne `epuisee()` rendait FAUX à cause du « trouve » : la fiche n'était ni active
# (plus d'angle suivant) ni épuisée (donc jamais rouverte par le délai) — une ligne
# permanente dans la file, sans geste au bout, et un résumé qui affirmait « la source ne
# publie pas cette information » alors que la note portait l'URL exacte de l'image.
zombie = ([{"angle": a, "resultat": "muet"} for a in t.ANGLES[:-1]]
          + [{"angle": t.ANGLES[-1], "resultat": "trouve",
              "note": "oktoberfest.torino.it/…/3x2-1.jpg, 2000×1334, HTTP 200"}])
verifier("six angles faits + un trouve : la fiche est bien ÉPUISÉE côté recherche",
         t.epuisee(zombie))
r_zombie = t.resume(zombie)
verifier("le résumé du zombie ne MENT plus (« la source ne publie pas » interdit ici)",
         "la source ne publie pas" not in r_zombie, r_zombie)
verifier("   il désigne le geste : lire la note du trouve, poser via completer_verifie",
         "PAS APPLIQUÉ" in r_zombie, r_zombie)

# ── Le rouvreur : après le délai, pas avant ─────────────────────────────────────
maintenant = datetime(2026, 9, 20, 10, 0, 0)
recent = [{"angle": a, "resultat": "muet",
           "at": (maintenant - timedelta(days=3)).isoformat()} for a in t.ANGLES]
verifier("épuisée depuis 3 jours : on NE rouvre pas (sinon on ramène le martèlement)",
         not t.a_rouvrir(recent, maintenant))
vieux = [{"angle": a, "resultat": "muet",
          "at": (maintenant - timedelta(days=t.EPUISEMENT_JOURS + 1)).isoformat()}
         for a in t.ANGLES]
verifier(f"épuisée depuis plus de {t.EPUISEMENT_JOURS} jours : elle repasse",
         t.a_rouvrir(vieux, maintenant))
verifier("une fiche NON épuisée n'est pas concernée par le rouvreur",
         not t.a_rouvrir(partiel, maintenant))

# ── Le résumé, écrit pour être lu par l'agent ───────────────────────────────────
verifier("le résumé d'une fiche neuve dit par où commencer",
         "page_fiche" in t.resume([]), t.resume([]))
r = t.resume(partiel)
verifier("le résumé dit ce qui a été tenté ET l'angle suivant, en clair",
         "commune_ot=muet" in r and "PROCHAIN ANGLE : recherche_nom" in r, r)
verifier("l'épuisement est dit comme un fait sur la SOURCE, pas comme un échec",
         "la source ne publie pas" in t.resume(tous), t.resume(tous))

# ── Le cycle complet sur une vraie base ─────────────────────────────────────────
with tempfile.TemporaryDirectory() as tmp:
    conn = sqlite3.connect(str(Path(tmp) / "essai.db"))
    conn.row_factory = sqlite3.Row
    t.enregistrer(conn, 4771, "lieu", "page_fiche", "muet",
                  "la page ne donne que « Domenica 6 settembre, ore 10 »")
    t.enregistrer(conn, 4771, "lieu", "site_organisateur", "muet", "turismoinlanga : rien")
    faits = t.deja_tentes(conn, 4771, "lieu")
    verifier("les deux tentatives sont relues dans l'ordre",
             [x["angle"] for x in faits] == ["page_fiche", "site_organisateur"], str(faits))
    verifier("la note est conservée — c'est elle qui sert au suivant",
             "Domenica 6 settembre" in faits[0]["note"], faits[0]["note"])
    verifier("le prochain angle tient compte des deux",
             t.prochain_angle(faits) == "commune_ot")
    verifier("un autre CHAMP de la même fiche a sa propre mémoire",
             t.deja_tentes(conn, 4771, "image") == [])
    try:
        t.enregistrer(conn, 1, "lieu", "au_pif", "muet")
        verifier("un angle inventé est refusé", False, "aucune exception")
    except ValueError:
        verifier("un angle inventé est refusé (pas de mémoire fantaisiste)", True)
    conn.close()

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
