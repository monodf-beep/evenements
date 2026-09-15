#!/usr/bin/env python3
"""Fixture : ce que le refermeur de site_health_check doit LAISSER OUVERT.

Constat qui a motivé l'ajout (2026-08-12, 00h22). La page `/seo` annonçait « 64 points à
traiter, dont 20 critiques/élevés ». En les lisant : **34 d'entre eux** étaient la même
ligne, « URL du sitemap redirige (1 saut(s)) au lieu de 200 direct », tous datés du
29 juillet. Une relecture des 230 URLs du sitemap le 12 août n'en a trouvé **aucune** qui
redirige encore. Les redirections étaient réparées depuis des jours ; rien ne savait le
constater, parce que `site_health_check.py` savait ouvrir des points et rien ne savait les
fermer — le défaut structurel décrit par la règle 3 du CLAUDE.md.

Un refermeur automatique est cependant plus dangereux qu'un ouvreur : refermer à tort fait
disparaître un vrai problème sans que personne ne le voie. Les trois frontières, et le cas
qui doit rester OUVERT de chaque côté :

  • PÉRIMÈTRE DE MESURE — une URL au-delà de `--cap`, ou en timeout, n'a pas été mesurée.
    Elle ressemble EXACTEMENT à une URL saine du point de vue du script. Un point la
    concernant doit rester ouvert : « je ne l'ai pas regardée » n'est pas « elle va bien ».
    C'est le zéro qui vient d'une absence de cas, pas d'un succès.

  • PROPRIÉTÉ — les trouvailles d'un audit manuel (`source_agent` différent) ne sont pas
    du ressort de ce script. Il ne mesure pas ce qu'elles décrivent ; il n'a rien à en
    dire, et surtout pas « c'est réglé ».

  • PERSISTANCE — un point que la mesure du jour retrouve à l'identique reste ouvert,
    évidemment. C'est le cas trivial, et c'est celui qu'une régression casserait en
    silence.
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.site_health_check import solder_disparus

REDIRIGE = "URL du sitemap redirige (1 saut(s)) au lieu de 200 direct"


def _base() -> sqlite3.Connection:
    """Base jetable en mémoire — jamais data/events.db, même en lecture."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE seo_findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, page_url TEXT,
        category TEXT, severity TEXT, title TEXT, description TEXT,
        recommendation TEXT, source_agent TEXT, status TEXT DEFAULT 'todo',
        created_at TEXT, resolved_at TEXT)""")
    return conn


def _ajoute(conn, url, titre, agent="site_health_check", statut="todo"):
    return conn.execute(
        "INSERT INTO seo_findings (page_url, title, source_agent, status) VALUES (?,?,?,?)",
        (url, titre, agent, statut)).lastrowid


def _statut(conn, pid):
    return conn.execute("SELECT status FROM seo_findings WHERE id=?", (pid,)).fetchone()[0]


# Le sitemap tel que le run l'a énuméré. `jamais-vue` en fait partie : c'est une URL
# DÉCLARÉE au sitemap mais située au-delà de `--cap`, donc jamais vérifiée. La distinction
# est tout l'objet du refermeur — « au-delà du plafond » (présente, non mesurée, on ne
# touche pas) n'est PAS « retirée du sitemap » (absente, prémisse caduque, on solde). Ma
# première fixture les confondait et le test est tombé au bon endroit.
SITEMAP = {"https://agendasabauda.eu/a/", "https://agendasabauda.eu/jamais-dans-le-lot/",
           "https://agendasabauda.eu/jamais-vue/",
           "https://agendasabauda.eu/lente/", "https://agendasabauda.eu/b/"}


def test_solde_ce_qui_a_disparu():
    """Le cas réel : l'URL répond, elle ne redirige plus, le point se referme."""
    conn = _base()
    pid = _ajoute(conn, "https://agendasabauda.eu/a/", REDIRIGE)
    soldes = solder_disparus(conn, findings=[], repondues={"https://agendasabauda.eu/a/"},
                             urls_sitemap=SITEMAP)
    assert [s[0] for s in soldes] == [pid]
    assert soldes[0][3] == "vérifiée, le défaut a disparu"
    assert _statut(conn, pid) == "done"


def test_une_url_RETIREE_DU_SITEMAP_se_solde():
    """Le cas qui manquait au premier run réel : 22 points bloqués à jamais.

    « Le sitemap référence X, qui redirige » : si X n'est plus au sitemap, la prémisse a
    disparu. Sans ce motif, ces points restaient ouverts pour toujours puisque le script
    ne revérifie que ce que le sitemap déclare.
    """
    conn = _base()
    pid = _ajoute(conn, "https://agendasabauda.eu/territoire/piemont/", REDIRIGE)
    soldes = solder_disparus(conn, findings=[], repondues=set(), urls_sitemap=SITEMAP)
    assert [s[0] for s in soldes] == [pid]
    assert soldes[0][3] == "ne figure plus au sitemap"
    assert _statut(conn, pid) == "done"


def test_un_sitemap_INJOIGNABLE_ne_solde_RIEN_sur_ce_motif():
    """Garde-fou : sans énumération fiable, tout point paraîtrait « retiré du sitemap ».

    C'est le zéro qui vient d'un échec et non d'une absence de cas. Une nuit où le
    sitemap ne répond pas, la file entière se refermerait — en annonçant un beau chiffre.
    """
    conn = _base()
    a = _ajoute(conn, "https://agendasabauda.eu/territoire/piemont/", REDIRIGE)
    b = _ajoute(conn, "https://agendasabauda.eu/a/", REDIRIGE)
    for sitemap in (None, set()):
        soldes = solder_disparus(conn, findings=[], repondues=set(), urls_sitemap=sitemap)
        assert soldes == []
    assert _statut(conn, a) == "todo"
    assert _statut(conn, b) == "todo"


def test_une_url_NON_MESUREE_reste_ouverte():
    """Hors --cap ou en timeout : absente de `repondues`, donc jamais soldée.

    C'est la garantie principale. Sans elle, un run borné à 300 URLs refermerait tous les
    points portant sur les 500 suivantes — en annonçant un beau chiffre.
    """
    conn = _base()
    hors_cap = _ajoute(conn, "https://agendasabauda.eu/jamais-vue/", REDIRIGE)
    timeout = _ajoute(conn, "https://agendasabauda.eu/lente/", REDIRIGE)
    soldes = solder_disparus(conn, findings=[], repondues=set(), urls_sitemap=SITEMAP)
    assert soldes == []
    assert _statut(conn, hors_cap) == "todo"
    assert _statut(conn, timeout) == "todo"


def test_un_point_d_audit_manuel_n_est_JAMAIS_solde():
    """Même URL, même absence de défaut mesuré : ce script n'a pas autorité dessus."""
    conn = _base()
    manuel = _ajoute(conn, "https://agendasabauda.eu/a/",
                     "Aucune balise H1 sur la page d'accueil", agent="audit_manuel")
    sans_agent = _ajoute(conn, "https://agendasabauda.eu/a/",
                         "Titre trop court", agent=None)
    soldes = solder_disparus(conn, findings=[], repondues={"https://agendasabauda.eu/a/"},
                             urls_sitemap=SITEMAP)
    assert soldes == []
    assert _statut(conn, manuel) == "todo"
    assert _statut(conn, sans_agent) == "todo"


def test_un_point_encore_constate_reste_ouvert():
    conn = _base()
    pid = _ajoute(conn, "https://agendasabauda.eu/a/", REDIRIGE)
    encore = [{"page_url": "https://agendasabauda.eu/a/", "title": REDIRIGE}]
    soldes = solder_disparus(conn, findings=encore, repondues={"https://agendasabauda.eu/a/"},
                             urls_sitemap=SITEMAP)
    assert soldes == []
    assert _statut(conn, pid) == "todo"


def test_meme_url_deux_defauts_on_ne_solde_que_celui_qui_a_disparu():
    """Frontière fine : la clé est le COUPLE (url, titre), pas l'URL seule."""
    conn = _base()
    parti = _ajoute(conn, "https://agendasabauda.eu/a/", REDIRIGE)
    reste = _ajoute(conn, "https://agendasabauda.eu/a/", "URL du sitemap en erreur (404)")
    encore = [{"page_url": "https://agendasabauda.eu/a/",
               "title": "URL du sitemap en erreur (404)"}]
    soldes = solder_disparus(conn, findings=encore, repondues={"https://agendasabauda.eu/a/"},
                             urls_sitemap=SITEMAP)
    assert [s[0] for s in soldes] == [parti]
    assert _statut(conn, parti) == "done"
    assert _statut(conn, reste) == "todo"


def test_un_point_deja_solde_n_est_pas_retouche():
    """`done` et `dismissed` sortent de la requête : pas de resoldage en boucle."""
    conn = _base()
    fait = _ajoute(conn, "https://agendasabauda.eu/a/", REDIRIGE, statut="done")
    ecarte = _ajoute(conn, "https://agendasabauda.eu/b/", REDIRIGE, statut="dismissed")
    soldes = solder_disparus(conn, findings=[],
                             repondues={"https://agendasabauda.eu/a/",
                                        "https://agendasabauda.eu/b/"},
                             urls_sitemap=SITEMAP)
    assert soldes == []
    assert _statut(conn, fait) == "done"
    assert _statut(conn, ecarte) == "dismissed"


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
