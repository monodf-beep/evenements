#!/usr/bin/env python3
"""Fixture : tout méta `as_*` ENVOYÉ par le publieur doit être ACCEPTÉ côté WordPress.

Aucun réseau, aucune base : on compare deux fichiers du dépôt.

D'OÙ ÇA VIENT — et c'est la CINQUIÈME fois (2026-08-17). Le lot de la nuit a rendu
« 156 publié(s), 0 échec(s) ». Le lendemain matin, l'inventaire WordPress comptait ZÉRO
fiche portant `as_une_now`. `publisher_as` envoyait bien la valeur ; l'allowlist
`$allowed` de `cs-publish.php` ne la connaissait pas, `update_post_meta` n'a donc jamais
été appelé — et un méta inconnu est jeté EN SILENCE, sans rien changer au code HTTP.

Un lot « 0 échec » et un lot dont la moitié des données n'arrive pas se ressemblent
EXACTEMENT vus depuis le journal du publieur. C'est le « zéro qui ne dit pas d'où il
vient » du journal du 2026-08-11, sous sa forme la plus coûteuse : ici c'est un SUCCÈS
annoncé qui ne dit pas ce qu'il a perdu en route.

Le même incident, mot pour mot, s'était produit le 2026-08-12 avec `as_deplacement_now`.
Un commentaire de quatre lignes avait alors été écrit dans `cs-publish.php` pour que ça
n'arrive plus. Ça n'a pas suffi — parce qu'un commentaire ne se déclenche pas tout seul.
CLAUDE.md le dit : « c'est la fixture, le dry-run et le périmètre affiché qui tiennent,
parce qu'eux se déclenchent tout seuls ». Voilà donc la fixture.

⚠️ CE QU'ELLE NE PROUVE PAS, et il faut le lire avant de s'y fier. Elle compare le
publieur au fichier `deploy/wordpress/cs-publish.php` — qui n'est PAS le code qui tourne.
Le vrai vit dans Code Snippets, en base (docs/DEPLOIEMENT_WORDPRESS.md), et la version en
ligne contient du code absent du dépôt. Cette fixture attrape donc l'oubli au moment où
il s'écrit ; elle ne dit rien de ce que WordPress accepte AUJOURD'HUI. Pour ça, il n'y a
qu'une preuve : interroger la base de méta du site (règle 1).

Lancer : .venv/bin/python -m tests.test_contrat_meta_as
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PUBLIEUR = ROOT / "scripts" / "publisher_as.py"
ENDPOINT = ROOT / "deploy" / "wordpress" / "cs-publish.php"

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


def metas_envoyees(source: str) -> set[str]:
    """Les clés `as_*` que le publieur pose dans son dict `meta`.

    On lit le SOURCE plutôt que d'appeler la fonction : construire un payload réel
    demanderait un événement complet et des dépendances réseau, et la question posée ici
    est purement textuelle — quelles clés existent dans ce fichier.
    """
    return set(re.findall(r'"(as_[a-z0-9_]+)"\s*:', source))


def metas_acceptees(source: str) -> set[str]:
    """Les clés listées dans le `$allowed` de `cs-publish.php`.

    On borne la lecture au bloc `$allowed = array( … );` — sinon on ramasserait les clés
    citées dans les commentaires du reste du fichier, et la fixture se croirait au vert
    parce qu'un méta est MENTIONNÉ quelque part.
    """
    m = re.search(r"\$allowed\s*=\s*array\((.*?)\);", source, re.DOTALL)
    if not m:
        return set()
    bloc = m.group(1)
    # Les commentaires du bloc citent des noms de méta (« ⚠️ Ne PAS trier sur
    # as_panel_vmean ») : les retirer AVANT d'extraire, faute de quoi un méta seulement
    # commenté passerait pour accepté.
    bloc = re.sub(r"//[^\n]*", "", bloc)
    return set(re.findall(r"'(as_[a-z0-9_]+)'", bloc))


envoyees = metas_envoyees(PUBLIEUR.read_text(encoding="utf-8"))
acceptees = metas_acceptees(ENDPOINT.read_text(encoding="utf-8"))

print("──── les deux listes sont bien lues ────")
# Un ensemble vide ferait passer la comparaison au vert sans rien comparer : c'est
# exactement le « zéro sans dénominateur » que ce dépôt traque. On l'interdit d'abord.
_check(f"le publieur envoie des métas as_* ({len(envoyees)} trouvées)", len(envoyees) >= 10,
       sorted(envoyees))
_check(f"l'allowlist en liste aussi ({len(acceptees)} trouvées)", len(acceptees) >= 10,
       sorted(acceptees))

print("\n──── aucun méta ne se perd en chemin ────")
perdus = sorted(envoyees - acceptees)
_check("tout ce que le publieur envoie est accepté", not perdus,
       f"\n      JETÉ EN SILENCE PAR WORDPRESS : {', '.join(perdus)}"
       f"\n      → ajouter ces clés au tableau $allowed de deploy/wordpress/cs-publish.php,"
       f"\n        PUIS au snippet EN LIGNE (Code Snippets) — le fichier du dépôt n'est pas"
       f"\n        le code qui tourne. Sans ça, le lot dira « 0 échec » et rien n'arrivera.")

print("\n──── les deux métas qui ont déjà coûté une journée chacun ────")
# Nommés exprès : ce sont les régressions dont on connaît le prix. Si l'un des deux
# disparaît d'un côté ou de l'autre, on veut le lire tout de suite, pas dans un diff.
for cle, incident in (("as_deplacement_now", "2026-08-12, section « Ça vaut le déplacement »"),
                      ("as_une_now", "2026-08-17, section « À la une »")):
    _check(f"`{cle}` est envoyé ET accepté ({incident})",
           cle in envoyees and cle in acceptees,
           f"envoyé={cle in envoyees} accepté={cle in acceptees}")

print("\n──── contre-épreuve : cette fixture sait-elle REFUSER ? ────")
# Sans ça, elle ne prouverait que sa capacité à dire oui — le défaut du portillon du
# 2026-08-06, passé au vert sur un design faux. On lui donne l'incident réel du jour :
# un `$allowed` d'où `as_une_now` a disparu.
FAUX = """
    $allowed = array('as_score', 'as_home_score',
        // ⚠️ Ne PAS trier cette section sur as_une_now, qui mesure autre chose.
        'as_deplacement_now');
"""
vu = metas_acceptees(FAUX)
_check("un `$allowed` amputé est bien vu comme amputé", "as_une_now" not in vu, sorted(vu))
_check("   et un méta seulement CITÉ EN COMMENTAIRE ne compte pas pour accepté — "
       "c'est ce qui aurait rendu la fixture complaisante",
       "as_une_now" not in vu and "as_deplacement_now" in vu, sorted(vu))
_check("   tandis que les clés réellement listées, elles, sont vues",
       {"as_score", "as_home_score"} <= vu, sorted(vu))

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
