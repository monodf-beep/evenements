#!/usr/bin/env python3
"""Lit la Search Console : quelles requêtes amènent du monde, et sur quelles pages.

POURQUOI CE SCRIPT EXISTE. L'audit éditorial du 2026-08-13 s'est arrêté sur une question
qu'aucune mesure du dépôt ne pouvait trancher : **les six articles reçoivent-ils des
visites, et sur quelles requêtes ?** Sans ça, l'ordre des articles à écrire repose sur la
matière disponible et la concurrence observée — deux critères honnêtes, mais indirects. La
Search Console, elle, dit ce que les gens tapent VRAIMENT pour tomber sur le site.

Ce script ne touche JAMAIS au site. En base, il n'ecrit que sur `--enregistrer --apply`,
et seulement dans sa propre table `gsc_perf` : il n'approche aucune donnee du pipeline.

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
    .venv/bin/python -m scripts.gsc_report --csv export.zip  # sans API, depuis un export
    .venv/bin/python -m scripts.gsc_report --auth --client client_secret.json
    .venv/bin/python -m scripts.gsc_report --enregistrer --apply --jours 30   # archivage
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("gsc_report")

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]
# Le décalage de fraîcheur de la Search Console. Trois jours est la marge sûre : à deux
# jours, certaines lignes manquent encore et le total paraît plus bas qu'il n'est.
RETARD_JOURS = 3


def _service():
    """Construit le client Search Console. DEUX chemins d'authentification, au choix.

    POURQUOI DEUX (ajouté le 2026-08-13, après blocage réel). La première version n'acceptait
    qu'une clé de compte de service. Or l'organisation `culturasabauda.eu` applique la règle
    Google Cloud `iam.disableServiceAccountKeyCreation` — une protection activée par défaut
    sur les organisations récentes, qui INTERDIT de créer ce genre de clé. Le script était
    donc inutilisable sans affaiblir un réglage de sécurité, ce qui est un prix absurde pour
    lire des statistiques de recherche.

    Le compte OAuth ne tombe pas sous cette règle : ce n'est pas une clé de compte de
    service, c'est une autorisation donnée par un humain à une application. Et pour la
    Search Console c'est même MIEUX : l'utilisateur est déjà propriétaire de la propriété,
    donc l'étape « ajouter le compte de service comme utilisateur » disparaît.

    ⚠️ Le piège de l'OAuth, et il casse au bout d'une semaine sans prévenir : tant que
    l'application reste en statut **« Test »** dans l'écran de consentement Google, le jeton
    de rafraîchissement EXPIRE au bout de 7 jours. Il faut passer l'application « En
    production » (bouton *Publier l'application*) pour obtenir un jeton durable. Sinon le
    cron marche une semaine, puis échoue en silence.
    """
    try:
        from googleapiclient.discovery import build
    except ImportError:
        log.error("bibliothèques absentes — .venv/bin/pip install "
                  "google-api-python-client google-auth google-auth-oauthlib")
        return None

    jeton = os.getenv("GSC_OAUTH_TOKEN", str(ROOT / "data" / "gsc-oauth-token.json"))
    compte = os.getenv("GSC_CREDENTIALS", str(ROOT / "data" / "gsc-credentials.json"))

    # OAuth d'abord : c'est le chemin qui ne demande aucune dérogation de sécurité.
    if Path(jeton).exists():
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_file(jeton, SCOPE)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            Path(jeton).write_text(creds.to_json(), encoding="utf-8")
            log.info("jeton OAuth rafraîchi")
        return build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    if Path(compte).exists():
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(compte, scopes=SCOPE)
        return build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    log.error("aucun identifiant trouvé. Trois chemins possibles, du plus simple au plus lourd :")
    log.error("  A. OAuth (recommandé, aucune dérogation de sécurité) — créer un ID client "
              "OAuth de type « Application de bureau », télécharger son JSON sur le VPS, "
              "puis : gsc_report.py --auth --client <le.json>")
    log.error("     Le tour se fait DEPUIS LE VPS : le script affiche une adresse, tu "
              "l'ouvres dans ton navigateur, tu recolles l'adresse de retour. Le jeton "
              "atterrit dans %s", jeton)
    log.error("  B. Compte de service — clé JSON dans %s. Bloqué tant que la règle "
              "iam.disableServiceAccountKeyCreation s'applique au projet.", compte)
    log.error("  C. Sans API du tout : exporter le CSV depuis la Search Console et lancer "
              "gsc_report.py --csv <fichier>")
    return None


def _autoriser(client_json: str, sortie: str) -> int:
    """Tour OAuth SUR LE VPS, sans navigateur ni Python sur le poste de l'utilisateur.

    POURQUOI CE DÉTOUR (2026-08-13). Google a supprimé en 2022 le mode « copier-coller le
    code » (`urn:ietf:wg:oauth:2.0:oob`), ce qui laisse croire qu'il faut impérativement un
    navigateur sur la machine qui s'authentifie. C'est faux, et la version précédente de
    cette fonction demandait donc à Franck d'installer Python sur son portable pour une
    opération de cinq minutes.

    Le contournement standard : on demande une redirection vers `http://localhost:<port>`.
    L'utilisateur ouvre l'adresse d'autorisation dans SON navigateur, autorise, et Google le
    renvoie vers une adresse locale **qui n'aboutit pas** — page d'erreur « connexion
    refusée », ce qui est NORMAL et doit être annoncé, sinon on croit à un échec. Le code
    d'autorisation est dans la barre d'adresse ; il suffit de la recopier ici.

    Un client de type « Application de bureau » autorise `http://localhost` sur n'importe
    quel port sans qu'on ait à le déclarer.
    """
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        log.error("bibliothèque absente — .venv/bin/pip install google-auth-oauthlib")
        return 2
    if not Path(client_json).exists():
        log.error("fichier d'ID client introuvable : %s", client_json)
        return 2

    flow = Flow.from_client_secrets_file(
        client_json, scopes=SCOPE, redirect_uri="http://localhost:8765/")
    # access_type=offline + prompt=consent : sans les DEUX, Google ne renvoie pas de jeton
    # de rafraîchissement à la deuxième autorisation, et le cron meurt à la première
    # expiration sans qu'on comprenne pourquoi.
    url, _ = flow.authorization_url(access_type="offline", prompt="consent",
                                    include_granted_scopes="true")
    print("\n1. Ouvre cette adresse dans ton navigateur habituel :\n")
    print(f"   {url}\n")
    print("2. Autorise l'accès avec le compte Google qui possède la Search Console.")
    print("3. Ton navigateur affichera une page d'ERREUR (« connexion refusée » sur")
    print("   localhost:8765). C'est NORMAL et attendu — rien n'a échoué.")
    print("4. Copie l'adresse COMPLÈTE depuis la barre d'adresse et colle-la ci-dessous.\n")
    try:
        collee = input("Adresse collée > ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        log.error("interrompu — aucun jeton enregistré")
        return 1

    from urllib.parse import urlparse, parse_qs
    params = parse_qs(urlparse(collee).query)
    code = (params.get("code") or [None])[0]
    if not code:
        log.error("aucun paramètre `code` dans l'adresse collée. Colle bien l'adresse "
                  "entière, celle qui commence par http://localhost:8765/?code=…")
        return 2
    try:
        flow.fetch_token(code=code)
    except Exception as exc:  # noqa: BLE001 — le message de Google est ce qui aide ici
        log.error("échange du code refusé : %s", exc)
        return 2

    creds = flow.credentials
    if not creds.refresh_token:
        log.error("AUCUN jeton de rafraîchissement reçu — le script cesserait de marcher à "
                  "la première expiration. Recommence : l'adresse d'autorisation doit "
                  "contenir prompt=consent.")
        return 2
    Path(sortie).parent.mkdir(parents=True, exist_ok=True)
    Path(sortie).write_text(creds.to_json(), encoding="utf-8")
    os.chmod(sortie, 0o600)
    print(f"\n✓ Jeton enregistré dans {sortie} (lisible par toi seul)")
    print("  Lance maintenant : .venv/bin/python -m scripts.gsc_report --check")
    print("\n⚠️ Si l'application est en statut « Test » dans l'écran de consentement Google,")
    print("   ce jeton expirera dans 7 jours. Publie l'application pour qu'il dure.")
    return 0


def _depuis_csv(chemin: str) -> int:
    """Lit un export CSV de la Search Console — le chemin qui ne demande RIEN à débloquer.

    L'interface de la Search Console exporte en un clic (bouton *Exporter*, en haut à
    droite du rapport Performances). C'est la façon d'obtenir la réponse aujourd'hui, sans
    projet Google Cloud, sans compte de service et sans dérogation. Accepte le .zip complet
    ou un .csv isolé.

    Les en-têtes changent selon la langue de l'interface : on repère donc la colonne des
    libellés à son contenu (la première non numérique) plutôt qu'à son nom, ce qui évite de
    casser le jour où l'export sort en anglais.
    """
    import csv
    import io
    import zipfile

    p = Path(chemin)
    if not p.exists():
        log.error("fichier introuvable : %s", chemin)
        return 2
    tables: dict[str, list[list[str]]] = {}
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            for nom in z.namelist():
                if nom.lower().endswith(".csv"):
                    texte = z.read(nom).decode("utf-8-sig", errors="replace")
                    tables[nom] = list(csv.reader(io.StringIO(texte)))
    else:
        tables[p.name] = list(csv.reader(
            p.read_text(encoding="utf-8-sig", errors="replace").splitlines()))

    for nom, lignes in tables.items():
        if len(lignes) < 2:
            continue
        entete, corps = lignes[0], lignes[1:]
        print(f"\n=== {nom} — {len(corps)} ligne(s) ===")
        print("   " + " | ".join(entete))
        for l in corps[:25]:
            print("   " + " | ".join(l))
        if len(corps) > 25:
            print(f"   … {len(corps) - 25} ligne(s) de plus (fichier complet non tronqué)")
    if not tables:
        log.error("aucun CSV lisible dans %s", chemin)
        return 2
    return 0


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


def _enregistre(rows_page: list[dict], rows_query: list[dict],
                debut: str, fin: str) -> tuple[int, int]:
    """Archive le relevé en base. C'EST ÇA, l'automatisation qui compte.

    POURQUOI ARCHIVER PLUTÔT QU'ALERTER. À 19 clics sur trois mois, un rapport hebdomadaire
    envoyé sur Slack serait du bruit — et Franck a dit le 2026-08-13 « il m'en faut un ou
    deux par jour, mais c'est tout ». Ce cron n'envoie donc RIEN.

    Ce qu'il fait a plus de valeur : il constitue l'historique qui n'existe pas. Deux fois
    en deux jours, une question est restée sans réponse faute de comparatif — « le creux
    d'événements de novembre est-il un trou de sourcing ou un délai d'annonce ? » se
    tranche en regardant la même période l'an dernier, donnée que personne n'avait gardée.
    La Search Console ne conserve que seize mois et n'expose aucun passé antérieur à la
    validation. Chaque relevé non pris est perdu pour toujours.

    Rejouer la même période ne duplique pas : la clé est (période, dimension, valeur).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS gsc_perf (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        releve_le TEXT DEFAULT (datetime('now')),
        debut TEXT NOT NULL, fin TEXT NOT NULL,
        dimension TEXT NOT NULL, valeur TEXT NOT NULL,
        clics REAL, impressions REAL, ctr REAL, position REAL)""")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_gsc_perf_unique "
                 "ON gsc_perf(debut, fin, dimension, valeur)")
    n = {"page": 0, "query": 0}
    for dim, rows in (("page", rows_page), ("query", rows_query)):
        for r in rows:
            conn.execute(
                "INSERT OR REPLACE INTO gsc_perf "
                "(debut, fin, dimension, valeur, clics, impressions, ctr, position) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (debut, fin, dim, r["keys"][0], r.get("clicks"), r.get("impressions"),
                 r.get("ctr"), r.get("position")))
            n[dim] += 1
    conn.commit()
    # Règle 6 : on recompte en base, on ne fait pas confiance aux compteurs de boucle.
    total = conn.execute("SELECT COUNT(*) FROM gsc_perf").fetchone()[0]
    periodes = conn.execute("SELECT COUNT(DISTINCT debut||fin) FROM gsc_perf").fetchone()[0]
    conn.close()
    print(f"\nArchivé : {n['page']} page(s), {n['query']} requête(s) pour {debut} → {fin}.")
    print(f"En base après écriture : {total} ligne(s) sur {periodes} période(s) relevée(s).")
    return n["page"], n["query"]


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
    parser.add_argument("--csv", metavar="FICHIER",
                        help="Lit un export CSV/ZIP de la Search Console. Aucune API, "
                             "aucun identifiant, aucune dérogation de sécurité.")
    parser.add_argument("--auth", action="store_true",
                        help="Tour OAuth dans un navigateur (à lancer sur ton portable).")
    parser.add_argument("--client", metavar="JSON",
                        default=str(ROOT / "data" / "oauth-client.json"),
                        help="Fichier d'ID client OAuth. Défaut : data/oauth-client.json — "
                             "y déposer le JSON téléchargé depuis Google Cloud suffit.")
    parser.add_argument("--enregistrer", action="store_true",
                        help="Archive le relevé en base (table gsc_perf) pour constituer "
                             "l'historique. Silencieux : n'envoie rien sur Slack.")
    parser.add_argument("--apply", action="store_true",
                        help="Avec --enregistrer : écrit vraiment. Sans lui, simulation.")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")

    if args.csv:
        return _depuis_csv(args.csv)
    if args.auth:
        if not Path(args.client).exists():
            # Message écrit pour quelqu'un qui n'est pas développeur : on donne le geste
            # exact, pas un nom de fichier entre chevrons — que bash interprète comme une
            # redirection et qui produit « syntax error near unexpected token ». Vécu le
            # 2026-08-13, à cause d'un exemple mal écrit de ma part.
            log.error("fichier d'ID client absent : %s", args.client)
            log.error("→ Google Cloud → API et services → Identifiants → Créer des "
                      "identifiants → ID client OAuth → type « Application de bureau », "
                      "puis télécharger le JSON.")
            log.error("→ Le déposer ici sous le nom data/oauth-client.json, par exemple "
                      "avec : nano data/oauth-client.json  (coller, Ctrl+O, Entrée, Ctrl+X)")
            return 2
        return _autoriser(args.client,
                          os.getenv("GSC_OAUTH_TOKEN",
                                    str(ROOT / "data" / "gsc-oauth-token.json")))

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
        if args.enregistrer:
            pages = _interroge(service, propriete, debut, fin, ["page"], 5000)
            requetes = _interroge(service, propriete, debut, fin, ["query"], 5000)
            print(f"\nRelevé : {len(pages)} page(s), {len(requetes)} requête(s).")
            if not args.apply:
                print("Simulation (défaut) : rien n'a été écrit. "
                      "Relancer avec --apply pour archiver.")
                return 0
            _enregistre(pages, requetes, debut, fin)
            return 0

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
