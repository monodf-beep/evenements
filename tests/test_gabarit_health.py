#!/usr/bin/env python3
"""Fixture : ce que gabarit_health doit LAISSER PASSER, pas seulement ce qu'il refuse.

Le CLAUDE.md est explicite depuis le 2026-08-08 : « la fixture doit contenir un cas qui
doit PASSER, choisi près de la frontière. Un test qui ne cherche qu'à se donner raison ne
prouve rien. » Le portillon du 06/08 était vert sur un design faux parce qu'il ne testait
que des cas confirmant son intuition.

Les trois frontières de ce script, et le cas sain qui les longe :

  • CACHE — le défaut est `no-store`, PAS `max-age=0`. Une réponse
    `public, max-age=0, must-revalidate` est parfaitement conservable : le client la garde
    et revalide, ce qui est le réglage NORMAL d'un agenda qui change tous les jours. Un
    contrôle qui refuserait `max-age=0` crierait sur une configuration saine.

  • ROBOTS — le défaut est `Disallow: /` nu sous `User-agent: *`. `Disallow: /wp-admin/`
    est le réglage standard de tout WordPress et doit passer. Refuser toute ligne
    `Disallow` reviendrait à alerter sur la quasi-totalité des sites du monde.

  • ORGANIZATION — Yoast écrit parfois `"@type": ["Organization","NewsMediaOrganization"]`
    quand le site est déclaré à la fois organisation et source de presse. C'est la
    configuration la MIEUX renseignée des deux, et une recherche de la chaîne exacte
    `"@type":"Organization"` la raterait.

Les cas « cassés » viennent tous du relevé réel du 2026-08-12 sur agendasabauda.eu, pas
d'une invention : l'en-tête de cache est copié trait pour trait de la réponse du serveur.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.gabarit_health import (
    _cachable, _robots_autorise, _organization, _hreflang, _premier_css, comparer)

# Relevé le 2026-08-12 sur https://agendasabauda.eu/ — la chaîne exacte servie.
CACHE_REEL_CASSE = "no-cache, must-revalidate, max-age=0,no-store, no-cache, must-revalidate, post-check=0, pre-check=0"


def test_cache_le_cas_sain_qui_longe_la_frontiere():
    """max-age=0 + must-revalidate SANS no-store : conservable, ne doit PAS alerter."""
    assert _cachable("public, max-age=0, must-revalidate") is True
    assert _cachable("public, max-age=0") is True
    assert _cachable("no-cache") is True          # no-cache ≠ no-store : on garde, on revalide
    assert _cachable("private, max-age=600") is True


def test_cache_le_defaut_reel():
    assert _cachable(CACHE_REEL_CASSE) is False
    assert _cachable("no-store, no-cache, must-revalidate, post-check=0, pre-check=0") is False
    assert _cachable("NO-STORE") is False          # insensible à la casse
    assert _cachable(None) is False                # en-tête absent = on ne peut rien garantir


def test_robots_le_cas_sain_qui_longe_la_frontiere():
    """Un Disallow existe, mais ciblé : c'est le réglage normal, il doit passer."""
    assert _robots_autorise("User-agent: *\nDisallow: /wp-admin/") is True
    assert _robots_autorise("User-agent: *\nDisallow:") is True            # le robots.txt réel
    assert _robots_autorise("User-agent: *\nDisallow: /wp-admin/\nAllow: /wp-admin/admin-ajax.php") is True
    # Barre nue, mais sur UN SEUL robot : le site reste ouvert aux autres, donc pas d'alerte.
    assert _robots_autorise("User-agent: BadBot\nDisallow: /\n\nUser-agent: *\nDisallow:") is True


def test_robots_la_regression_catastrophique():
    assert _robots_autorise("User-agent: *\nDisallow: /") is False
    assert _robots_autorise("user-agent:*\ndisallow:/") is False           # casse et espaces
    assert _robots_autorise("User-agent: *\nDisallow: /   # préprod") is False


def test_organization_le_cas_sain_qui_longe_la_frontiere():
    """@type en LISTE — la configuration la mieux renseignée, à ne pas rater."""
    liste = ('<script type="application/ld+json">{"@context":"https://schema.org",'
             '"@graph":[{"@type":["Organization","NewsMediaOrganization"],'
             '"name":"Agenda Sabauda"}]}</script>')
    assert _organization(liste) is True
    # Référence par `publisher` sans nœud typé : compte aussi.
    pub = ('<script type="application/ld+json">{"@type":"WebPage",'
           '"publisher":{"@id":"https://agendasabauda.eu/#organization"}}</script>')
    assert _organization(pub) is True
    # Nœud enfoui profond dans le graphe.
    profond = ('<script type="application/ld+json">{"@graph":[{"@type":"WebPage",'
               '"about":{"@type":"Organization","name":"AS"}}]}</script>')
    assert _organization(profond) is True


def test_organization_le_graphe_reel_du_2026_08_12():
    """Le graphe servi ce jour-là : quatre nœuds, aucune entité éditrice."""
    reel = ('<script type="application/ld+json" class="yoast-schema-graph">'
            '{"@context":"https://schema.org","@graph":['
            '{"@type":"WebPage","@id":"https://agendasabauda.eu/"},'
            '{"@type":"ImageObject","@id":"https://agendasabauda.eu/#primaryimage"},'
            '{"@type":"BreadcrumbList","@id":"https://agendasabauda.eu/#breadcrumb"},'
            '{"@type":"WebSite","@id":"https://agendasabauda.eu/#website"}]}</script>')
    assert _organization(reel) is False
    # Un JSON-LD illisible ne doit pas faire planter le run — il ne prouve rien, c'est tout.
    assert _organization('<script type="application/ld+json">{ceci n\'est pas du json}</script>') is False
    assert _organization('<html><body>rien du tout</body></html>') is False


def test_hreflang():
    ok = ('<link rel="alternate" hreflang="fr" href="/"/>'
          '<link rel="alternate" hreflang="it" href="/it/home-it/"/>'
          '<link rel="alternate" hreflang="x-default" href="/"/>')
    assert _hreflang(ok) is True
    # Attributs dans l'ordre inverse : même page, autre sérialisation.
    inverse = ('<link hreflang="fr" rel="alternate" href="/"/>'
               '<link hreflang="it" rel="alternate" href="/it/"/>'
               '<link hreflang="x-default" rel="alternate" href="/"/>')
    assert _hreflang(inverse) is True
    # x-default manquant : incomplet, donc faux.
    assert _hreflang('<link rel="alternate" hreflang="fr" href="/"/>'
                     '<link rel="alternate" hreflang="it" href="/it/"/>') is False
    assert _hreflang('<html></html>') is False


def test_premier_css_resout_les_trois_formes_de_href():
    base = "https://agendasabauda.eu"
    assert _premier_css('<link rel="stylesheet" href="/wp-content/a.css">', base) == \
        "https://agendasabauda.eu/wp-content/a.css"
    assert _premier_css('<link rel="stylesheet" href="//cdn.x/a.css">', base) == "https://cdn.x/a.css"
    assert _premier_css('<link rel="stylesheet" href="https://x/a.css?ver=3">', base) == \
        "https://x/a.css?ver=3"
    assert _premier_css('<html>aucune feuille</html>', base) is None


def test_premiere_mesure_n_alerte_pas():
    """Sans référence, sept signaux basculeraient d'un coup au premier run."""
    bascules, non_mesures, mesures = comparer({}, {
        "robots_autorise": True, "home_indexable": True, "sitemap_index": True,
        "html_cachable": False, "asset_cachable": False,
        "schema_organization": False, "hreflang_accueil": True})
    assert bascules == []
    assert mesures == 7
    assert non_mesures == []


def test_un_signal_non_mesure_n_est_pas_une_bascule():
    """Règle 3 : un échec réseau ne doit pas garer un signal ni fabriquer une alerte.

    C'est le piège du « zéro qui ressemble à une absence de cas » : sans cette
    distinction, une coupure réseau se lirait comme « le robots.txt vient d'interdire
    l'exploration », et on partirait chercher une panne qui n'existe pas.
    """
    avant = {"robots_autorise": True, "html_cachable": False}
    bascules, non_mesures, mesures = comparer(avant, {
        "robots_autorise": None,        # non mesuré : silence
        "html_cachable": False})        # inchangé : silence
    assert bascules == []
    assert mesures == 1
    assert "robots.txt autorise l'exploration" in non_mesures[0]


def test_la_bascule_est_signalee_dans_LES_DEUX_SENS():
    """Le retour au vert compte autant : il prouve que le correctif a atteint le SITE.

    Règle 1 transposée au déploiement — un fichier poussé ne prouve pas qu'il est en
    ligne. Le jour où html_cachable repasse à True, c'est la seule preuve qu'on ait.
    """
    avant = {"html_cachable": False, "schema_organization": True}
    bascules, _, _ = comparer(avant, {"html_cachable": True, "schema_organization": False})
    libelles = {b[0]: (b[1], b[2]) for b in bascules}
    assert len(bascules) == 2
    assert libelles["les pages HTML autorisent la mise en cache"] == (False, True)
    assert libelles["l'accueil déclare une entité éditrice (Organization)"] == (True, False)


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
