#!/usr/bin/env python3
"""Fixture : ce qui a le droit de sortir en « Source officielle » sur une fiche.

Aucun réseau, aucune base : `_source_publiable` est une fonction pure d'un
dictionnaire d'événement. Ce test fige les quatre journées de réparations du
2026-08-04 et 2026-08-05, chaque cas correspondant à une vraie fiche cassée.

CE QU'IL PROTÈGE, ET POURQUOI CHAQUE GARDE EXISTE (docs/CONFORMITE.md §5) :

  1. SCHÉMA — 98 fiches publiées affichaient `translated:959:fr` sous le libellé
     « Source officielle ↗ », soit un lien mort donné au lecteur comme preuve de
     vérification. Même famille : `gmail:<id>`. C'est l'invariant, il passe en
     premier et ne dépend d'aucune liste à tenir à jour.
  2. ANCRE OFFICIELLE — le radar publie `url_officiel`, jamais `url_source` : la
     charte §8 interdit de lier l'ARTICLE DE PRESSE, pas la page d'organisateur
     qu'on remonte depuis lui. L'ancre vient de `utils.radar.official_anchor`,
     la MÊME fonction que le verrou de publication ; on l'appelle, on ne la
     reproduit pas (une réécriture partielle avait laissé 8 fiches sur 17 vides).
     Son troisième signal n'est PAS une URL mais la phrase « matière officielle
     lue » — d'où l'importance du cas 3.
  3. ROUTEURS — 9 fiches publiaient un lien de traçage de newsletter, dont 5
     portant `e=…`, NOTRE identifiant d'abonné, exposé sur des pages publiques.
  4. FAUX POSITIFS — les gardes ci-dessus sont larges (motif `*click*` en
     sous-domaine, paramètre `e=`). Les quatre derniers cas sont des sources
     légitimes qu'elles auraient pu emporter, dont bct.comune.torino.it, que
     Franck a explicitement demandé de conserver.

Lancer : .venv/bin/python -m tests.test_source_publiable
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publisher_as import _is_tracking_url, _source_publiable  # noqa: E402

PRESSE = "https://cdn-s-www.ledauphine.com/images/ABCD/le-festival-revient.jpg"


def materiel(pages=None, officielle=None) -> str:
    """`enrich_data` tel que l'écrit enrich.py : les pages officiellement LUES."""
    source = {}
    if pages is not None:
        source["pages"] = pages
    if officielle is not None:
        source["officielle"] = officielle
    return json.dumps({"source": source})


# (libellé, événement, radar ?, attendu)
CAS = [
    # 1. Schéma — l'invariant.
    ("pseudo-lien de traduction (WP#2205)",
     {"id": 3495, "url_source": "translated:959:fr"}, False, ""),
    ("pseudo-lien gmail",
     {"id": 1, "url_source": "gmail:18f2c4a9b"}, False, ""),
    ("ancre qui est elle-même un pseudo-lien",
     {"id": 2, "url_officiel": "translated:840:it"}, True, ""),

    # 2. Ancre officielle — les trois signaux de radar.official_anchor.
    ("radar résolu par url_officiel (WP#6306)",
     {"id": 4084, "url_source": PRESSE,
      "url_officiel": "https://www.valloire-baroque.com/"},
     True, "https://www.valloire-baroque.com/"),
    ("radar résolu par les pages LUES (les 8 oubliées)",
     {"id": 801, "url_source": PRESSE,
      "enrich_data": materiel(pages=["https://flowersfestival.it/programma"])},
     True, "https://flowersfestival.it/programma"),
    ("radar dont le seul signal est le booléen — ce n'est pas une URL",
     {"id": 3, "url_source": PRESSE, "enrich_data": materiel(officielle=True)},
     True, ""),
    ("radar non résolu — l'article de presse n'est JAMAIS publié (charte §8)",
     {"id": 2528, "url_source": PRESSE}, True, ""),

    # 3. Routeurs de newsletter.
    ("Mailchimp avec notre identifiant d'abonné (WP#6420)",
     {"id": 6420,
      "url_source": "https://us.list-manage.com/NEbt0b0Fxb4?e=06a93eea46&c2id=a89b9"},
     False, ""),
    ("MailUp (WP#6283)",
     {"id": 6283, "url_source": "https://turismovda.musvc2.net/e/tr?q=7KW4bRYma8X8"},
     False, ""),
    ("Salesforce Marketing Cloud (WP#7113)",
     {"id": 4584,
      "url_source": "https://click.marketingcloud.turismotorino.org/?qs=ABB7InYiOjE"},
     False, ""),
    ("routeur atteint PAR l'ancre officielle — la garde passe après",
     {"id": 4, "url_source": PRESSE,
      "url_officiel": "https://us.list-manage.com/x?e=06a93eea46"}, True, ""),

    # 4. Faux positifs — sources légitimes que les gardes ci-dessus frôlent.
    ("commune italienne en .it, que le motif *click* frôle (WP#7113 réparée)",
     {"id": 5, "url_source": "https://www.comune.strambino.to.it/eventi/tour"},
     False, "https://www.comune.strambino.to.it/eventi/tour"),
    ("bct.comune.torino.it — source à conserver, décision de Franck",
     {"id": 6, "url_source": "https://bct.comune.torino.it/eventi/lavoriamo-a-maglia"},
     False, "https://bct.comune.torino.it/eventi/lavoriamo-a-maglia"),
    ("office de tourisme officiel",
     {"id": 7, "url_source": "https://www.lovevda.it/it/eventi/fiabe-nel-bosco"},
     False, "https://www.lovevda.it/it/eventi/fiabe-nel-bosco"),
    ("url_officiel prime sur url_source hors radar : vérifiée > héritée",
     {"id": 8, "url_source": "https://agenda-tiers.example/fiche/42",
      "url_officiel": "https://mal-thonon.org/au-diapason/"},
     False, "https://mal-thonon.org/au-diapason/"),

    # 5. Robustesse — une ligne d'events_raw peut ne rien porter du tout.
    ("aucune colonne renseignée", {"id": 9}, True, ""),
    ("colonnes présentes mais nulles",
     {"id": 10, "url_source": None, "url_officiel": None, "enrich_data": None},
     False, ""),
]

# `_is_tracking_url` seule : elle sert aussi de garde ailleurs, on la fige à part.
CAS_ROUTEUR = [
    ("https://us.list-manage.com/x?e=06a", True),
    ("https://mailchi.mp/abc/lettre-aout", True),
    ("https://turismovda.musvc2.net/e/tr?q=abc", True),
    ("https://customer86768.musvc3.net/e/tr?q=abc", True),
    ("https://click.marketingcloud.turismotorino.org/?qs=ABB", True),
    ("https://exemple.fr/agenda?eid=99213", True),
    ("https://www.albertville.fr/un-ete-a-albe-2/", False),
    ("https://event.businessfrance.fr/french-riviera-beauty/", False),
    ("https://apejs.org/la-soute", False),
    ("", False),
]

echecs = 0

print("──── _source_publiable ────")
for libelle, event, radar, attendu in CAS:
    obtenu = _source_publiable(event, radar)
    if obtenu == attendu:
        print(f"OK    {libelle}\n      → {obtenu or '(vide)'}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}\n      attendu {attendu or '(vide)'}\n"
              f"      obtenu  {obtenu or '(vide)'}")

print("\n──── _is_tracking_url ────")
for url, attendu in CAS_ROUTEUR:
    obtenu = _is_tracking_url(url)
    if obtenu == attendu:
        print(f"OK    {'écartée' if attendu else 'gardée '}  {url[:64] or '(vide)'}")
    else:
        echecs += 1
        print(f"ÉCHEC attendu {'écartée' if attendu else 'gardée'} : {url[:64]}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s) "
      f"sur {len(CAS) + len(CAS_ROUTEUR)} cas.")
sys.exit(1 if echecs else 0)
