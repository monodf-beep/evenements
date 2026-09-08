#!/usr/bin/env python3
"""Fixture : les GUIDES vus par le panel de personas (scripts.panel_site).

D'OÙ ÇA VIENT — Franck, 2026-08-17 : « les guides, ça doit être rédigé une fois et c'est
tout. La seule chose que je demande, c'est que le guide puisse être lu par le panel de
personas pour vérifier si ça correspond bien à ce qu'on fait avec le reste du site. »
Donc : le panel sait lire un guide, et AUCUN cron ne le déclenche.

CE QUE LA FIXTURE ÉPROUVE — la transformation seule, sans réseau ni crédit API. La
récupération HTTP, elle, a été vérifiée sur le site réel : 12 guides listés, soit
exactement le nombre d'articles publiés en base (6 FR + 6 IT).

Et elle fige surtout le défaut du jour, trouvé en LISANT la sortie : la première version
listait SIX guides sur douze. Polylang filtre les collections REST — articles ET
catégories — sur la langue courante, et la catégorie italienne ne s'appelle pas `guide`
mais `guide-it`. Le compteur « 6 guide(s) » avait l'air juste ; c'est le pire des cas,
celui d'une liste incomplète qui ne se plaint pas.

Lancer : .venv/bin/python -m tests.test_panel_guides
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.panel_site import GUIDES_SLUGS, LANGUES, guides_depuis_payload  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# Charge réelle de l'API, recopiée de la réponse du site le 2026-08-17.
PAYLOAD = [
    {"id": 2422, "link": "https://agendasabauda.eu/festivals-savoie-2026/",
     "title": {"rendered": "Festivals de l&rsquo;&eacute;t&eacute; en Savoie 2026"}},
    {"id": 2423, "link": "https://agendasabauda.eu/it/festival-savoia-2026/",
     "title": {"rendered": "Festival dell&rsquo;estate in Savoia 2026"}},
    {"id": 2422, "link": "https://agendasabauda.eu/festivals-savoie-2026/",
     "title": {"rendered": "Festivals de l&rsquo;&eacute;t&eacute; en Savoie 2026"}},
    {"id": 9999, "link": "", "title": {"rendered": "Guide sans adresse"}},
    {"id": 3648, "link": "https://agendasabauda.eu/cuisine-nissarde-tables-labellisees/",
     "title": {"rendered": "O&ugrave; manger ni&ccedil;ois : les tables <em>labellis&eacute;es</em>"}},
]

guides = guides_depuis_payload(PAYLOAD)
par_cle = {g["cle"]: g for g in guides}

verifier("le doublon d'identifiant ne compte qu'une fois", len(guides) == 3,
         f"{len(guides)} guide(s) : {[g['cle'] for g in guides]}")
verifier("un guide sans adresse est écarté", "guide-9999" not in par_cle)

# Les entités HTML doivent disparaître : on donne un TEXTE à lire à un persona, pas du
# balisage. « l&rsquo;&eacute;t&eacute; » dans un prompt, c'est une lecture faussée.
verifier("les entités HTML sont décodées",
         par_cle["guide-2422"]["label"] == "Guide : Festivals de l’été en Savoie 2026",
         par_cle["guide-2422"]["label"])
verifier("les balises sont retirées du titre",
         par_cle["guide-3648"]["label"] == "Guide : Où manger niçois : les tables labellisées",
         par_cle["guide-3648"]["label"])
verifier("le guide italien est bien là (c'était la moitié manquante)",
         "guide-2423" in par_cle)

# Tout le panel lit : la demande est un contrôle de cohérence avec le RESTE du site, et
# un territoire renseigné restreindrait la lecture aux personas locaux.
verifier("aucun territoire n'est imposé, donc tout le panel lit",
         all(g["territoire"] is None for g in guides))
verifier("la clé permet de désigner un guide par son identifiant",
         par_cle["guide-2422"]["cle"].split("-")[-1] == "2422")

# Le garde-fou contre la rechute : le slug italien suffixé et les deux langues.
verifier("le slug italien suffixé par Polylang est cherché", "guide-it" in GUIDES_SLUGS)
verifier("les deux langues du site sont interrogées", tuple(LANGUES) == ("fr", "it"))

# Une charge vide ne doit pas ressembler à un succès silencieux : la fonction rend une
# liste vide, et c'est l'appelant (guides_publies) qui le DIT dans le journal.
verifier("une charge vide rend une liste vide", guides_depuis_payload([]) == [])

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
