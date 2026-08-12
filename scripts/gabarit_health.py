#!/usr/bin/env python3
"""Surveille les signaux SEO de GABARIT — et n'alerte que sur leur CHANGEMENT.

POURQUOI CE SCRIPT EXISTE. L'audit SEO du 2026-08-12 (`docs/AUDIT_SEO_2026-08-12.md`)
a trouvé six défauts qui ne sont pas des défauts de fiche mais de gabarit : l'en-tête
`Cache-Control: no-store` posé sur TOUTES les réponses, jusque sur les fichiers `.css` ;
l'absence de tout nœud `Organization` dans le JSON-LD de l'accueil. Aucun des scripts
existants ne les voyait, et c'est logique : `site_audit` relit des fiches une par une,
`homepage_health` compte des cartes. Un signal de SITE n'appartient à aucun des deux.

POURQUOI UN DÉTECTEUR DE CHANGEMENT ET PAS UN SEUIL. Parce qu'au moment où ce script est
écrit, la moitié de ces signaux sont DÉJÀ au rouge. Un contrôle classique crierait donc
tous les jours dès le premier run, sur une situation connue — soit exactement la faute que
`site_audit.py` documente dans son propre commentaire :

    « Une alerte permanente sur une situation voulue, c'est le meilleur moyen de faire
      ignorer les vraies. »

On mémorise donc l'état sur disque et on ne dit quelque chose que lorsqu'une valeur
BASCULE. Silence tant que rien ne bouge ; une ligne le jour où ça casse — et une ligne
aussi le jour où c'est réparé, ce qui vaut confirmation que le correctif a bien atteint le
site (règle 1 : un fichier déployé ne prouve pas qu'il est en ligne).

Le déclencheur juste pour ces signaux n'est pas le calendrier mais le DÉPLOIEMENT : rien
ici ne change tout seul. Un détecteur de bascule est précisément un détecteur de déploiement
— y compris des déploiements que personne n'a annoncés, et il y en a : 34 mu-plugins `cs-*`
vivent sur le serveur, dont 16 sans copie versionnée.

AUCUN ÉTAT TERMINAL (règle 3). Un signal qu'on n'a pas réussi à mesurer n'écrase jamais sa
valeur mémorisée et ne compte pas comme une bascule : il est déclaré non mesuré, et le run
suivant le reprendra. Il n'existe donc pas de valeur qui « gare » un signal hors
surveillance ; la seule façon de sortir de la boucle est de supprimer le fichier d'état,
ce qui rejoue simplement une première mesure.

Ce script NE MODIFIE RIEN, ni en base ni sur le site : il constate.

Usage :
    .venv/bin/python -m scripts.gabarit_health            # run normal (cron)
    .venv/bin/python -m scripts.gabarit_health --montre   # affiche l'état, n'écrit rien
    .venv/bin/python -m scripts.gabarit_health --reinit   # repart d'une mesure neuve
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import slack
from utils import pipeline_status

log = get_logger("gabarit_health")

ETAT = Path(os.getenv("GABARIT_HEALTH_STATE", ROOT / "data" / "gabarit_health_state.json"))
UA = "Mozilla/5.0 (gabarit_health check)"

# Chaque signal : (clé, libellé lisible, valeur SAINE attendue).
# La valeur saine sert uniquement à colorer le message (🔴 / 🟢) ; l'alerte, elle, se
# déclenche sur la BASCULE, dans les deux sens.
_SIGNAUX = [
    ("robots_autorise", "robots.txt autorise l'exploration", True),
    ("home_indexable", "l'accueil n'est pas en noindex", True),
    ("sitemap_index", "sitemap_index.xml répond et liste les événements", True),
    ("html_cachable", "les pages HTML autorisent la mise en cache", True),
    ("asset_cachable", "les fichiers CSS autorisent la mise en cache", True),
    ("schema_organization", "l'accueil déclare une entité éditrice (Organization)", True),
    ("hreflang_accueil", "l'accueil porte fr + it + x-default", True),
]


def _cachable(cache_control: str | None) -> bool:
    """`no-store` interdit toute conservation, par le navigateur comme par un CDN.

    C'est LUI le défaut, pas `max-age=0` ni `must-revalidate` : une réponse
    `public, max-age=0, must-revalidate` est parfaitement conservable — le client la garde
    et se contente de la revalider, ce qui est un comportement normal et souhaitable pour
    un agenda qui change tous les jours. Ne tester que `no-store` évite de crier sur une
    configuration saine ; c'est le cas-limite qui DOIT passer, et il est dans la fixture.
    """
    if cache_control is None:
        return False
    return "no-store" not in cache_control.lower()


def _organization(html: str) -> bool:
    """Yoast émet l'entité éditrice dans son `@graph`, et son `@type` peut être une LISTE.

    Quand le site est déclaré comme une organisation ET une source de presse, Yoast écrit
    `"@type":["Organization","NewsMediaOrganization"]`. Chercher la chaîne exacte
    `"@type":"Organization"` raterait ce cas — qui est pourtant le mieux configuré des deux.
    On parcourt donc le JSON, on ne racle pas le texte.
    """
    for bloc in re.findall(
            r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            data = json.loads(bloc.strip())
        except (ValueError, TypeError):
            continue
        pile = [data]
        while pile:
            noeud = pile.pop()
            if isinstance(noeud, dict):
                types = noeud.get("@type")
                types = types if isinstance(types, list) else [types]
                if any(t and "Organization" in str(t) for t in types):
                    return True
                if noeud.get("publisher"):
                    return True
                pile.extend(noeud.values())
            elif isinstance(noeud, list):
                pile.extend(noeud)
    return False


def _robots_autorise(robots_txt: str) -> bool:
    """Un `Disallow: /` global est la régression la plus coûteuse et la plus silencieuse.

    Elle arrive en copiant une préproduction sur la production. Rien d'autre dans le dépôt
    ne la verrait, et Google met des semaines à la désapprendre. On ne regarde QUE le bloc
    `User-agent: *`, et on n'y refuse que la barre nue : `Disallow: /wp-admin/` est le
    réglage normal de tout WordPress et doit passer (cas-limite en fixture).
    """
    bloc_etoile = False
    for ligne in robots_txt.splitlines():
        ligne = ligne.split("#", 1)[0].strip()
        if not ligne:
            continue
        cle, _, valeur = ligne.partition(":")
        cle, valeur = cle.strip().lower(), valeur.strip()
        if cle == "user-agent":
            bloc_etoile = valeur == "*"
        elif cle == "disallow" and bloc_etoile and valeur == "/":
            return False
    return True


def _hreflang(html: str) -> bool:
    langues = {m.lower() for m in re.findall(
        r'<link[^>]+rel=["\']alternate["\'][^>]+hreflang=["\']([^"\']+)["\']', html, re.I)}
    langues |= {m.lower() for m in re.findall(
        r'<link[^>]+hreflang=["\']([^"\']+)["\'][^>]+rel=["\']alternate["\']', html, re.I)}
    return {"fr", "it", "x-default"} <= langues


def _premier_css(html: str, base: str) -> str | None:
    for m in re.finditer(r'<link[^>]+href=["\']([^"\']+\.css[^"\']*)["\']', html, re.I):
        href = m.group(1)
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return base + href
    return None


def mesurer(base: str, session: requests.Session) -> dict[str, bool | None]:
    """Renvoie un signal par clé. `None` = NON MESURÉ (réseau), jamais « faux ».

    La distinction compte : un zéro qui vient d'un échec ressemble exactement à un zéro
    qui vient d'une absence de cas. Ici, un signal non mesuré n'écrase rien et n'alerte pas.
    """
    signaux: dict[str, bool | None] = {cle: None for cle, _, _ in _SIGNAUX}

    def _get(url: str):
        try:
            return session.get(url, timeout=30, headers={"User-Agent": UA})
        except requests.RequestException as exc:
            log.warning("non mesuré — %s : %s", url, exc)
            return None

    r = _get(base + "/robots.txt")
    if r is not None and r.status_code == 200:
        signaux["robots_autorise"] = _robots_autorise(r.text)

    r = _get(base + "/sitemap_index.xml")
    if r is not None:
        signaux["sitemap_index"] = r.status_code == 200 and "tribe_events" in r.text

    accueil = _get(base + "/")
    if accueil is not None and accueil.status_code == 200:
        html = accueil.text
        signaux["html_cachable"] = _cachable(accueil.headers.get("Cache-Control"))
        signaux["schema_organization"] = _organization(html)
        signaux["hreflang_accueil"] = _hreflang(html)
        meta = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']*)',
                         html, re.I)
        signaux["home_indexable"] = not (meta and "noindex" in meta.group(1).lower())
        css = _premier_css(html, base)
        if css:
            rc = _get(css)
            if rc is not None and rc.status_code == 200:
                signaux["asset_cachable"] = _cachable(rc.headers.get("Cache-Control"))
    return signaux


def _etat() -> dict:
    try:
        return json.loads(ETAT.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return {}


def _ecrit_etat(etat: dict) -> None:
    try:
        ETAT.parent.mkdir(parents=True, exist_ok=True)
        ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as exc:
        log.error("état non enregistré (%s) — le run suivant refera une mesure neuve", exc)


def comparer(avant: dict, maintenant: dict[str, bool | None]) -> tuple[list, list, int]:
    """(bascules, non mesurés, nombre réellement mesuré).

    Une clé absente de `avant` n'est PAS une bascule : c'est une première mesure. Sans
    cette précaution, le premier run enverrait sept alertes d'un coup.
    """
    bascules, non_mesures = [], []
    mesures = 0
    for cle, libelle, sain in _SIGNAUX:
        val = maintenant.get(cle)
        if val is None:
            non_mesures.append(libelle)
            continue
        mesures += 1
        if cle in avant and avant[cle] != val:
            bascules.append((libelle, avant[cle], val, sain))
    return bascules, non_mesures, mesures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Surveille les signaux SEO de gabarit et alerte sur leur changement.")
    parser.add_argument("--montre", action="store_true",
                        help="Affiche l'état mesuré sans rien enregistrer ni notifier.")
    parser.add_argument("--reinit", action="store_true",
                        help="Oublie l'état mémorisé : la mesure du jour devient la référence.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    base = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
    session = requests.Session()
    maintenant = mesurer(base, session)
    avant = {} if args.reinit else _etat()

    for cle, libelle, sain in _SIGNAUX:
        val = maintenant.get(cle)
        etiquette = "non mesuré" if val is None else ("🟢" if val == sain else "🔴")
        log.info("%s %s = %s", etiquette, libelle, val)

    bascules, non_mesures, mesures = comparer(avant, maintenant)

    if args.montre:
        print(json.dumps(maintenant, ensure_ascii=False, indent=1))
        print(f"{mesures}/{len(_SIGNAUX)} signaux mesurés"
              f"{', non mesurés : ' + ', '.join(non_mesures) if non_mesures else ''}")
        return 0

    # Un signal non mesuré conserve sa valeur mémorisée : on ne perd pas la référence
    # parce que le réseau a hoqueté une fois.
    nouvel_etat = dict(avant)
    nouvel_etat.update({c: v for c, v in maintenant.items() if v is not None})

    if not avant:
        resume = (f"première mesure — {mesures}/{len(_SIGNAUX)} signaux relevés, "
                  f"référence enregistrée")
        log.info(resume)
        _ecrit_etat(nouvel_etat)
        pipeline_status.record_run("gabarit_health", ok=1, summary=resume)
        return 0

    if bascules:
        lignes = ["*Gabarit Agenda Sabauda — un signal SEO a changé*"]
        for libelle, ancien, nouveau, sain in bascules:
            fleche = "🟢 réparé" if nouveau == sain else "🔴 cassé"
            lignes.append(f"• {fleche} — {libelle} : {ancien} → {nouveau}")
        lignes.append(f"({mesures}/{len(_SIGNAUX)} signaux mesurés) {base}/")
        msg = "\n".join(lignes)
        log.warning(msg)
        slack.notify(msg)
        _ecrit_etat(nouvel_etat)
        casses = sum(1 for _, _, nouveau, sain in bascules if nouveau != sain)
        pipeline_status.record_run("gabarit_health", warn=casses,
                                   ok=len(bascules) - casses, summary=msg)
        return 1 if casses else 0

    resume = (f"aucun changement — {mesures}/{len(_SIGNAUX)} signaux mesurés"
              + (f", non mesurés : {', '.join(non_mesures)}" if non_mesures else ""))
    log.info(resume)
    _ecrit_etat(nouvel_etat)
    pipeline_status.record_run("gabarit_health", ok=1, summary=resume)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
