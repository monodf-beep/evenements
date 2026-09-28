#!/usr/bin/env python3
"""Fixture : la carte du menu colle-t-elle aux routes réelles ? (utils.menu)

D'OÙ ÇA VIENT — Franck, 2026-09-22 : « rends le back-office le plus simple possible,
s'il y a des choses qui ne servent plus on les enlève ». Simplifier suppose de savoir ce
qu'il y a. Or la liste du menu n'existait qu'en dur dans `base.html`, sans aucun lien
avec les routes : une page pouvait être servie sans figurer nulle part, ou figurer au
menu après la suppression de sa route.

C'est la mécanique des SCRIPTS ORPHELINS du 18/08 transposée à l'interface, et elle se
règle pareil — par une fixture qui confronte les deux listes, pas par de la vigilance.

CE QU'ELLE EXIGE, dans les deux sens :

  • toute route de PAGE servie par app.py est soit au menu, soit déclarée HORS_MENU
    avec sa raison. Il n'y a pas de troisième cas : c'est ce qui empêche une page de
    devenir invisible par accident ;
  • toute entrée du menu pointe sur une route qui existe VRAIMENT — un lien mort dans
    un menu est pire qu'une page absente, parce qu'on le clique ;
  • le jeton `actif` de chaque entrée est bien celui que la route passe à son gabarit,
    sinon l'entrée ne s'allume jamais et on ne sait plus où on est.

Et un CAS QUI DOIT PASSER : la recherche sans accents doit trouver la page accentuée.
Un opérateur pressé tape « completude », et une recherche qui échoue là-dessus fait
croire que la page n'existe pas.

Lancer : .venv/bin/python -m tests.test_menu
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import menu  # noqa: E402

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


SRC = (ROOT / "app" / "app.py").read_text(encoding="utf-8")

# Routes de PAGE : celles qui répondent en GET et rendent un gabarit. On écarte les
# points d'entrée machine (API, widget, webhooks) et les actions POST-seules, qui ne
# sont pas des destinations de menu.
_MACHINE = ("/api/", "/embed/", "/webhooks/", "/run/", "/go/", "/action/", "/set-",
            "/publier", "/enrich/", "/seo/", "/complete/", "/unmerge", "/validation/",
            "/regie/", "/semaine/", "/triage/", "/reseaux/", "/favicon")

routes = set()
for m in re.finditer(r'@app\.route\("([^"]+)"(?:\s*,\s*methods=\[([^\]]*)\])?', SRC):
    chemin, methodes = m.group(1), (m.group(2) or "")
    if methodes and "GET" not in methodes:
        continue                                   # POST seul : une action
    if any(chemin.startswith(p) for p in _MACHINE):
        continue
    routes.add(re.sub(r"/<[^>]+>", "", chemin) or "/")

au_menu = {p["url"] for p in menu.PAGES}
declarees = au_menu | set(menu.HORS_MENU)

orphelines = sorted(routes - declarees)
verifier("aucune page servie n'est absente de la carte",
         not orphelines, "non déclarées : " + ", ".join(orphelines))

mortes = sorted(au_menu - routes)
verifier("aucune entrée de menu ne pointe dans le vide",
         not mortes, "routes inexistantes : " + ", ".join(mortes))

fantomes = sorted(set(menu.HORS_MENU) - routes)
verifier("HORS_MENU ne garde pas des routes disparues",
         not fantomes, "à retirer de HORS_MENU : " + ", ".join(fantomes))

verifier("chaque exclusion porte sa raison",
         all(r.strip() for r in menu.HORS_MENU.values()))

# Le jeton `actif` doit être celui que la page pose réellement. ATTENTION : il se pose
# à DEUX endroits — `active=` dans app.py, ou `{% set active = ... %}` en tête du
# gabarit. Ne regarder qu'un des deux, c'est mesurer sa propre myopie : la première
# version de cette fixture déclarait cinq pages « jamais allumées » alors qu'elles
# l'étaient depuis leur template.
TEXTES = [SRC] + [p.read_text(encoding="utf-8")
                  for p in (ROOT / "app" / "templates").glob("*.html")]
poses = set()
for texte in TEXTES:
    poses |= set(re.findall(r"""active\s*=\s*["']([a-z_]+)["']""", texte))
manquants = sorted(p["actif"] for p in menu.PAGES if p["actif"] not in poses)
verifier("chaque entrée s'allume : son jeton `actif` est posé par la route",
         not manquants, "jetons jamais posés : " + ", ".join(manquants))

# --- Cohérence interne de la carte ---------------------------------------------
verifier("aucune URL en double au menu", len(au_menu) == len(menu.PAGES))
verifier("aucun jeton `actif` en double",
         len({p["actif"] for p in menu.PAGES}) == len(menu.PAGES))
verifier("chaque page appartient à un groupe déclaré",
         {p["groupe"] for p in menu.PAGES} <= {c for c, _, _ in menu.GROUPES})
verifier("chaque page dit ce qu'on y fait", all(p["resume"].strip() for p in menu.PAGES))
verifier("les épinglées existent toutes", len(menu.epinglees()) == len(menu.EPINGLEES))

# Aucune page ne doit être perdue par le regroupement d'affichage.
rendues = {p["actif"] for p in menu.epinglees()}
for _, _, _, pages in menu.groupes_avec_pages():
    rendues |= {p["actif"] for p in pages}
verifier("le menu affiche TOUTES les pages de la carte, sans exception",
         rendues == {p["actif"] for p in menu.PAGES},
         str(sorted({p["actif"] for p in menu.PAGES} - rendues)))
verifier("une épinglée n'apparaît pas deux fois",
         all(p["actif"] not in menu.EPINGLEES
             for _, _, _, pages in menu.groupes_avec_pages() for p in pages))
verifier("groupe_de désigne le bon repli", menu.groupe_de("systeme") == "analyser",
         menu.groupe_de("systeme"))
verifier("et il ne réclame aucun repli pour une épinglée", menu.groupe_de("tableur") == "")

# --- La recherche de la palette --------------------------------------------------
index = menu.index_recherche()
verifier("la palette indexe toutes les pages", len(index) == len(menu.PAGES))
verifier("la cible de recherche est sans accents ni majuscules",
         all(c["cible"] == c["cible"].lower() and "é" not in c["cible"] for c in index))
trouve = lambda q: [c["libelle"] for c in index if q in c["cible"]]
verifier("« completude » trouve le Tableur malgré l'accent — le cas qui doit PASSER",
         "Tableur" in trouve("completude"), str(trouve("completude")))
verifier("« photo » trouve l'Audit visuel", "Audit visuel" in trouve("photo"),
         str(trouve("photo")))
verifier("« cron » trouve le Pipeline auto", "Pipeline auto" in trouve("cron"),
         str(trouve("cron")))
verifier("on peut aussi taper l'adresse", "Audit visuel" in trouve("/audit-visuel"))
# Le ménage du 22/09 : « Coûts par date » n'est plus une entrée (c'est un onglet de
# « État du système »), mais taper « couts » doit toujours mener quelque part — une
# suppression qui rend une fonction introuvable n'est pas une simplification.
verifier("« couts » mène encore à l'écran qui les porte",
         trouve("couts") == ["État du système"], str(trouve("couts")))

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
