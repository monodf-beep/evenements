#!/usr/bin/env python3
"""Lit la Search Console : quelles requêtes amènent du monde, et sur quelles pages.

POURQUOI CE SCRIPT EXISTE. L'audit éditorial du 2026-08-13 s'est arrêté sur une question
qu'aucune mesure du dépôt ne pouvait trancher : **les six articles reçoivent-ils des
visites, et sur quelles requêtes ?** Sans ça, l'ordre des articles à écrire repose sur la
matière disponible et la concurrence observée — deux critères honnêtes, mais indirects. La
Search Console, elle, dit ce que les gens tapent VRAIMENT pour tomber sur le site.

Ce script ne modifie rien, ni en base ni sur le site : il lit et il affiche.

⚠️ TROIS PIÈGES, ET ILS COÛTENT CHACUN UNE HEURE SI ON NE LES CONNAÎT PAS.

1. **La propriété est de type « Domaine », donc son identifiant est `sc-domain:…`**, pas
   `https://…`. Une propriété par préfixe d'URL s'écrit `https://agendasabauda.eu/` ; une
   propriété par domaine s'écrit `sc-domain:agendasabauda.eu`. Se tromper ne donne pas une
   erreur claire : ça donne une liste vide, qui ressemble trait pour trait à « le site ne
   reçoit aucune visite ». D'où `--check`, qui affiche les propriétés RÉELLEMENT visibles.

2. **Être propriétaire du projet Google Cloud ne donne AUCUN accès aux données.** Le compte
   de service doit être ajouté comme utilisateur *dans la Search Console elle-même*
   (Paramètres → Utilisateurs et autorisations → Ajouter, avec son adresse
   `…@….iam.gserviceaccount.com`). Tant que ce n'est pas fait, `--check` renvoie zéro
   propriété — et c'est le symptôme à reconnaître.

3. **Les données ont deux à trois jours de retard.** Demander « hier » renvoie du vide.
   La fenêtre par défaut s'arrête donc il y a trois jours, et le script AFFICHE les dates
   qu'il a réellement interrogées — sinon un zéro dû à la fraîcheur se lirait comme un zéro
   de trafic.

Usage :
    .venv/bin/python -m scripts.gsc_report --check          # les identifiants marchent-ils ?
    .venv/bin/python -m scripts.gsc_report                   # rapport complet, 28 jours
    .venv/bin/python -m scripts.gsc_report --jours 90
    .venv/bin/python -m scripts.gsc_report --articles        # seulement les articles
"""
from __future__ import annotations
import argparse
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("gsc_report")

SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]
# Le décalage de fraîcheur de la Search Console. Trois jours est la marge sûre : à deux
# jours, certaines lignes manquent encore et le total paraît plus bas qu'il n'est.
RETARD_JOURS = 3


def _service():
    """Construit le client Search Console, ou explique précisément ce qui manque."""
    chemin = os.getenv("GSC_CREDENTIALS", str(ROOT / "data" / "gsc-credentials.json"))
    if not Path(chemin).exists():
        log.error("fichier d'identifiants introuvable : %s", chemin)
        log.error("→ créer un compte de service Google Cloud, télécharger sa clé JSON, "
                  "la déposer là, ou pointer GSC_CREDENTIALS vers elle dans .env")
        return None
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        log.error("bibliothèques absentes — .venv/bin/pip install "
                  "google-api-python-client google-auth")
        return None
    creds = service_account.Credentials.from_service_account_file(chemin, scopes=SCOPE)
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def _fenetre(jours: int) -> tuple[str, str]:
    fin = date.today() - timedelta(days=RETARD_JOURS)
    return (fin - timedelta(days=jours)).isoformat(), fin.isoformat()


def _interroge(service, propriete: str, debut: str, fin: str,
               dimensions: list[str], limite: int = 25) -> list[dict]:
    corps = {"startDate": debut, "endDate": fin, "dimensions": dimensions,
             "rowLimit": limite}
    reponse = service.searchanalytics().query(siteUrl=propriete, body=corps).execute()
    return reponse.get("rows", [])


def _articles_du_sitemap(base: str) -> list[str]:
    """Les URLs d'articles viennent du sitemap, pas d'une liste en dur.

    Le jour où le septième article est publié, il entre dans le rapport tout seul. Une
    liste figée dans le code aurait été un état terminal de plus : personne ne pense à
    rouvrir un fichier Python pour y ajouter une ligne.
    """
    try:
        r = requests.get(f"{base}/post-sitemap.xml", timeout=30,
                         headers={"User-Agent": "gsc_report"})
        r.raise_for_status()
        return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
    except requests.RequestException as exc:
        log.warning("sitemap des articles injoignable (%s) — section articles ignorée", exc)
        return []


def _tableau(titre: str, lignes: list[dict], cle: str = "keys", largeur: int = 62) -> None:
    print(f"\n=== {titre} ===")
    if not lignes:
        print("   (aucune ligne — voir la fenêtre de dates ci-dessus avant de conclure "
              "à une absence de trafic)")
        return
    print(f"   {'':<{largeur}} {'clics':>6} {'impr.':>7} {'CTR':>6} {'pos.':>6}")
    for l in lignes:
        etiquette = " · ".join(l.get(cle, []))[:largeur]
        print(f"   {etiquette:<{largeur}} {l.get('clicks',0):>6.0f} "
              f"{l.get('impressions',0):>7.0f} {l.get('ctr',0)*100:>5.1f}% "
              f"{l.get('position',0):>6.1f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lit la Search Console (lecture seule) : requêtes, pages, articles.")
    parser.add_argument("--check", action="store_true",
                        help="Vérifie les identifiants et liste les propriétés visibles.")
    parser.add_argument("--jours", type=int, default=28, help="Profondeur (défaut 28).")
    parser.add_argument("--articles", action="store_true",
                        help="N'afficher que la performance des articles.")
    parser.add_argument("--limite", type=int, default=25, help="Lignes par tableau.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    base = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
    propriete = os.getenv("GSC_PROPERTY") or f"sc-domain:{base.split('//')[-1]}"

    service = _service()
    if service is None:
        return 2

    if args.check:
        sites = service.sites().list().execute().get("siteEntry", [])
        print(f"\n=== propriétés visibles par ce compte de service : {len(sites)} ===")
        for s in sites:
            print(f"   {s.get('permissionLevel','?'):<22} {s.get('siteUrl')}")
        if not sites:
            print("   AUCUNE. Ce n'est pas une panne d'identifiants : c'est que le compte")
            print("   de service n'a pas encore été ajouté comme utilisateur DANS la")
            print("   Search Console (Paramètres → Utilisateurs et autorisations).")
            return 1
        vue = {s.get("siteUrl") for s in sites}
        print(f"\n   propriété configurée : {propriete}")
        print("   " + ("✓ elle est bien dans la liste" if propriete in vue else
                       "✗ ABSENTE de la liste — corriger GSC_PROPERTY dans .env "
                       "(une propriété « Domaine » s'écrit sc-domain:…)"))
        return 0 if propriete in vue else 1

    debut, fin = _fenetre(args.jours)
    print(f"\nPropriété : {propriete}")
    print(f"Fenêtre interrogée : du {debut} au {fin} "
          f"({args.jours} jours, arrêtés il y a {RETARD_JOURS} jours — la Search Console "
          f"a ce retard de publication)")

    try:
        if not args.articles:
            _tableau("Requêtes", _interroge(service, propriete, debut, fin,
                                            ["query"], args.limite))
            _tableau("Pages", _interroge(service, propriete, debut, fin,
                                         ["page"], args.limite))

        urls = set(_articles_du_sitemap(base))
        if urls:
            pages = _interroge(service, propriete, debut, fin, ["page"], 1000)
            par_url = {p["keys"][0].rstrip("/"): p for p in pages}
            print(f"\n=== Articles ({len(urls)} au sitemap) ===")
            print(f"   {'':<62} {'clics':>6} {'impr.':>7} {'CTR':>6} {'pos.':>6}")
            vus = 0
            for u in sorted(urls):
                p = par_url.get(u.rstrip("/"))
                etiquette = u.replace(base, "")[:62]
                if p:
                    vus += 1
                    print(f"   {etiquette:<62} {p['clicks']:>6.0f} {p['impressions']:>7.0f} "
                          f"{p['ctr']*100:>5.1f}% {p['position']:>6.1f}")
                else:
                    print(f"   {etiquette:<62} {'—':>6} {'—':>7} {'—':>6} {'—':>6}")
            # Règle 6 : le compteur dit ce qu'il compte. « 0 clic » et « jamais affiché »
            # sont deux situations différentes, et seule la seconde signifie que Google
            # ignore la page.
            print(f"\n   {vus} article(s) sur {len(urls)} ont reçu au moins une impression "
                  f"sur la période. Un tiret signifie « jamais affiché », pas « zéro clic ».")
    except Exception as exc:  # noqa: BLE001 — on veut le message brut de l'API
        log.error("requête Search Console refusée : %s", exc)
        log.error("→ lancer --check : neuf fois sur dix, le compte de service n'est pas "
                  "utilisateur de la propriété, ou GSC_PROPERTY est mal écrit.")
        return 2
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
