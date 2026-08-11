#!/usr/bin/env python3
"""L'ÉTAT DE LA CHAÎNE, étage par étage — combien sont passés, combien restent, sur quoi.

Franck, 2026-08-11 au soir : « j'aimerais avoir une vision globale du SEO, du taux
d'articles qui ne sont pas traduits, le taux d'articles qui ne sont pas enrichis rédigés,
et d'autres éléments qui pourraient m'aider à la compréhension du système qu'on a créé. »

Il y a déjà un onglet Pilotage, mais il répond à une autre question : la santé ÉDITORIALE
(couverture par territoire, équilibre, trous de sourcing). Celui-ci répond à « où en est la
MACHINE » — un événement entre par la collecte et ressort publié, traduit et référencé ;
entre les deux il franchit huit étages, et chacun peut être le goulot.

LA RÈGLE QUI GOUVERNE TOUT CE MODULE, et qui a coûté une journée entière le 2026-08-11 :
**un pourcentage sans son dénominateur ne veut rien dire.** Ce jour-là, trois compteurs du
back-office ont menti — pas sur leurs données, sur leur PÉRIMÈTRE. « 793 points à
vérifier » quand l'écran en montrait 28. « 108 fiches trop maigres » dont seize étaient
encore devant nous. Franck : « 548 tâches ! c'est ingérable. »

Chaque étage porte donc trois choses ensemble, indissociables :
  • `total` — le dénominateur, c'est-à-dire QUI est concerné ;
  • `perimetre` — la même chose EN FRANÇAIS, affichée à côté du chiffre ;
  • `reste` — ce qui manque, avec un lien pour aller le voir.

Et un étage dont le dénominateur vaut zéro n'affiche pas « 0 % » mais « aucun cas » : les
deux se ressemblent trait pour trait et n'appellent pas du tout le même geste. C'est la
leçon des trois « 0 » du 2026-08-11, qui semblaient désigner des sources pauvres et
désignaient en réalité trois requêtes mal écrites.

TOUT VIENT DE LA BASE. Aucun appel réseau, aucune clé d'API — la page doit rester lisible
quand le plafond d'usage est atteint, ce qui est précisément le moment où l'on veut savoir
ce qui est bloqué.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

# Règle 5 : on ne compte que ce qui est encore devant nous. C'est `date_event_end` qui
# décide — une exposition de mai à septembre compte tout l'été —, une fiche RÉCURRENTE
# n'est jamais passée, et une fiche SANS date n'est pas « passée » mais incomplète.
_FIN = "COALESCE(NULLIF(date_event_end,''), NULLIF(date_event_start,''))"
# ⚠️ `COALESCE(…, '')` AUTOUR DE _FIN, ET PAS SEULEMENT `_FIN = ''`. Sur une fiche sans
# aucune date, les deux NULLIF rendent NULL, et en SQL `NULL = ''` ne vaut pas VRAI : il
# vaut NULL, donc la fiche tombait des trois branches à la fois et disparaissait du
# périmètre. Elle était comptée nulle part — ni à venir, ni passée.
#
# C'est mot pour mot ce que la règle 5 interdit : « une fiche sans date ne se classe PAS
# en passé, c'est une donnée manquante ». Le tableau de bord aurait donc affiché 100 % de
# fiches datées en excluant silencieusement celles qui n'ont pas de date. Attrapé par la
# fixture, pas par la relecture.
_A_VENIR = (f"(COALESCE(recurring,0)=1 OR COALESCE({_FIN},'')='' OR {_FIN} >= :auj)")
_ACTIF = "statut NOT IN ('rejected','merged') AND COALESCE(duplicate_of,0)=0"
_RETENU = ("statut IN ('evaluated','published_cs','published_sub') "
           "AND COALESCE(duplicate_of,0)=0")
# Les traductions sont des COPIES : les compter dans les étages amont doublerait tout.
_ORIGINAL = "COALESCE(translation_of,0)=0"


def _colonnes(conn: sqlite3.Connection) -> set[str]:
    return {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}


def _n(conn: sqlite3.Connection, where: str, auj: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM events_raw WHERE {where}",
                        {"auj": auj}).fetchone()[0]


def etages(conn: sqlite3.Connection, auj: str | None = None) -> list[dict]:
    """Les huit étages de la chaîne, du plus amont au plus aval.

    L'ORDRE COMPTE ET IL EST LE MESSAGE. Un étage ne peut pas mieux faire que celui qui le
    précède : on ne traduit pas un article qui n'est pas écrit, on ne référence pas une
    page qui n'est pas publiée. Lu de haut en bas, le premier pourcentage qui s'effondre
    EST le goulot — inutile de chercher plus bas."""
    auj = auj or date.today().isoformat()
    cols = _colonnes(conn)
    base = f"{_ACTIF} AND {_ORIGINAL} AND {_A_VENIR}"
    retenu = f"{_RETENU} AND {_ORIGINAL} AND {_A_VENIR}"
    multi = "OR COALESCE(multi_lieux,0)=1" if "multi_lieux" in cols else ""

    total_actif = _n(conn, base, auj)
    total_retenu = _n(conn, retenu, auj)
    publie = f"{retenu} AND COALESCE(wp_post_id_as,0)<>0"
    total_publie = _n(conn, publie, auj)

    out = [
        {"cle": "evalue", "nom": "Évalués",
         "quoi": "un score d'importance a été attribué",
         "perimetre": "événements actifs, encore devant nous",
         "total": total_actif,
         "fait": _n(conn, f"{base} AND llm_score IS NOT NULL", auj),
         "lien": "/events"},
        {"cle": "date", "nom": "Datés",
         "quoi": "une date, ou le drapeau « récurrent »",
         "perimetre": "événements retenus, encore devant nous",
         "total": total_retenu,
         "fait": _n(conn, f"{retenu} AND (COALESCE(date_event_start,'')<>'' "
                          f"OR COALESCE(recurring,0)=1)", auj),
         "lien": "/a-completer"},
        {"cle": "lieu", "nom": "Situés",
         "quoi": "un lieu ET une ville",
         "perimetre": "événements retenus, encore devant nous",
         "total": total_retenu,
         "fait": _n(conn, f"{retenu} AND ((COALESCE(lieu,'')<>'' "
                          f"AND COALESCE(ville,'')<>'') {multi})", auj),
         "lien": "/a-completer"},
        {"cle": "image", "nom": "Illustrés",
         "quoi": "une image — sans elle la fiche ne se publie pas",
         "perimetre": "événements retenus, encore devant nous",
         "total": total_retenu,
         "fait": _n(conn, f"{retenu} AND COALESCE(url_image,'')<>''", auj),
         "lien": "/audit-visuel"},
        {"cle": "redige", "nom": "Rédigés",
         "quoi": "un article écrit, pas seulement la fiche brute",
         "perimetre": "événements retenus, encore devant nous",
         "total": total_retenu,
         "fait": _n(conn, f"{retenu} AND COALESCE(article_md,'')<>''", auj),
         "lien": "/events"},
        {"cle": "publie", "nom": "Publiés",
         "quoi": "en ligne sur agendasabauda.eu",
         "perimetre": "événements RÉDIGÉS, encore devant nous",
         "total": _n(conn, f"{retenu} AND COALESCE(article_md,'')<>''", auj),
         "fait": total_publie,
         "lien": "/events",
         "note": "un identifiant en base ne prouve pas qu'un post soit en ligne "
                 "(il survit à la corbeille) — seul WordPress fait foi"},
        {"cle": "traduit", "nom": "Traduits en italien",
         "quoi": "une version italienne existe et pointe sur l'original",
         "perimetre": "événements PUBLIÉS, encore devant nous",
         "total": total_publie,
         "fait": _n(conn, f"{publie} AND EXISTS (SELECT 1 FROM events_raw t "
                          f"WHERE t.translation_of = events_raw.id)", auj),
         "lien": "/events"},
        {"cle": "seo", "nom": "Référencés (SEO)",
         "quoi": "titre et description de référencement rédigés",
         "perimetre": "événements PUBLIÉS, encore devant nous",
         "total": total_publie,
         "fait": _n(conn, f"{publie} AND COALESCE(seo_title,'')<>'' "
                          f"AND COALESCE(seo_meta,'')<>''", auj),
         "lien": "/seo"},
    ]
    for e in out:
        e["reste"] = max(0, e["total"] - e["fait"])
        # ZÉRO CAS ≠ ZÉRO POUR CENT. Un étage sans dénominateur n'a pas échoué : il n'a
        # rien eu à faire, et l'afficher « 0 % » enverrait chercher une panne inexistante.
        e["pct"] = round(e["fait"] / e["total"] * 100) if e["total"] else None
    return out


def flux(conn: sqlite3.Connection, auj: str | None = None) -> dict:
    """Le RÉGIME de la chaîne sur sept jours : ce qui entre, ce qui sort, ce qui est refusé.

    Les étages disent l'état ; celui-ci dit le mouvement. Les deux sont nécessaires : une
    chaîne à 100 % partout qui ne collecte plus rien est morte, et ça ne se voit sur aucun
    pourcentage."""
    auj = auj or date.today().isoformat()
    depuis = (date.fromisoformat(auj) - timedelta(days=7)).isoformat()
    q = lambda w: conn.execute(  # noqa: E731
        f"SELECT COUNT(*) FROM events_raw WHERE {w}", (depuis,)).fetchone()[0]
    return {
        "jours": 7,
        "collectes": q("substr(COALESCE(scrape_date,''),1,10) >= ?"),
        "ecartes": q("substr(COALESCE(scrape_date,''),1,10) >= ? AND statut='rejected'"),
        "publies": q("substr(COALESCE(published_as_date,''),1,10) >= ?"),
        "sources": conn.execute(
            "SELECT COUNT(DISTINCT source_name) FROM events_raw "
            "WHERE substr(COALESCE(scrape_date,''),1,10) >= ?", (depuis,)).fetchone()[0],
    }


def goulot(etages_: list[dict]) -> dict | None:
    """Le premier étage qui décroche — et lui seul.

    POURQUOI UN SEUL. Une liste de huit alertes ne se lit pas, elle se subit : c'est la
    faute des 454 « points à contrôler » du 2026-08-11, où le seul qui comptait était noyé
    sous trois cents silences de la source. Et comme un étage ne peut pas mieux faire que
    celui qui le précède, réparer le premier suffit souvent à en redresser trois.

    Seuil à 90 % : en dessous, il reste plus d'une fiche sur dix en carafe, ce qui se voit
    sur le site."""
    for e in etages_:
        if e["pct"] is not None and e["pct"] < 90 and e["reste"] > 0:
            return e
    return None
