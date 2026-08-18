#!/usr/bin/env python3
"""Dépose l'état du pipeline dans une boîte aux lettres lisible sans accès au serveur.

D'OÙ ÇA VIENT — Franck, 2026-08-17 : « j'aimerais que tu sois autonome et que tu n'aies pas
besoin de moi. Comment faire ? » L'inventaire de la journée a montré que deux de mes six
sollicitations n'étaient pas des décisions mais des ALLERS-RETOURS : « le crédit API est-il
rétabli ? », « quel est l'état des files ? ». Chaque fois, il a collé une sortie de terminal.
Le pipeline savait déjà tout ça ; il ne l'exposait à personne.

CE QUE CE SCRIPT NE FAIT PAS : recompter. Les étages, le flux et le goulot viennent de
`utils.etat_systeme` — celui du tableau de bord, avec ses dénominateurs déjà éprouvés
(tests/test_etat_systeme.py : le passé ne compte pas, les traductions ne doublent pas les
étages amont, un étage sans cas rend None et non 0). Un second compteur écrit ici pour la
même chose finirait par contredire le premier, et c'est le plus gros qu'on croirait
(règle 6). Idem pour les passages de crons : `utils.pipeline_status`.

POURQUOI PAR WORDPRESS. Une route sur le backoffice aurait demandé un jeton de plus, donc
un secret de plus à confier et à révoquer. Or le VPS s'authentifie déjà auprès de WordPress
pour publier, et une session Claude l'atteint déjà : on réutilise le seul canal qui existe
des deux côtés. Même raisonnement que le rapatriement des rapports Slack du matin — ne pas
dupliquer un secret pour résoudre un problème de transport.

⚠️ AUCUN SECRET DANS LE RELEVÉ. Il est composé champ par champ, jamais par un balayage de
l'environnement, et `tests/test_publier_sante.py` REFUSE tout ce qui ressemble à une clé,
un jeton ou une URL de webhook. Ce qui part là-bas est de l'état d'exploitation, lisible par
tout compte capable d'éditer le site.

Usage :
    .venv/bin/python -m scripts.publier_sante            # affiche, n'envoie rien
    .venv/bin/python -m scripts.publier_sante --publier  # dépose sur WordPress (cron)
"""
from __future__ import annotations
import argparse
import base64
import json
import os
import sqlite3
import subprocess
import time
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils import etat_systeme as es  # noqa: E402
from utils import pipeline_status  # noqa: E402
from utils.logger import get_logger  # noqa: E402

log = get_logger("publier_sante")

DB = ROOT / "data" / "events.db"
# LE MÊME EN-TÊTE QUE LE CHEMIN QUI MARCHE (scripts/publisher_as.py) — par cohérence,
# PAS parce qu'on a prouvé que l'en-tête était en cause.
#
# ⚠️ CORRECTION DU 2026-08-18, ÉCRITE ICI PARCE QUE JE M'ÉTAIS TROMPÉ. J'avais d'abord
# noté que ce script rendait un `ConnectTimeoutError` sept minutes après un
# `publish_batch_as` réussi sur le MÊME hôte, et j'en avais conclu qu'un filtrage devant
# le site laissait passer le navigateur et faisait tomber l'agent maison. Mesuré ensuite,
# depuis une autre machine : `https://agendasabauda.eu/?rest_route=/cs/v1/sante` répond
# en 1,5 à 2,5 s avec l'en-tête navigateur ET avec `python-requests/2.31` — 401 sur GET
# sans authentification, 400 sur POST sans corps. Aucun des deux n'est filtré. La cause
# est donc AILLEURS (côté réseau du VPS, ou fenêtre anti-flood de l'hébergeur mutualisé),
# et l'en-tête n'y change rien. C'est la faute type de `docs/ERREURS_2026-08-17.md` :
# conclure sur un indice de surface au lieu d'aller mesurer. Le diagnostic ci-dessous
# existe pour que le PROCHAIN échec dise sa cause au lieu de me la faire deviner.
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
_ROUTE = "/?rest_route=/cs/v1/sante"

# Tout ce qui ressemble à un secret n'a rien à faire dans un relevé d'exploitation. La
# liste sert à la fixture ET de rappel à qui ajoutera un champ ici.
#
# ⚠️ `token` SEUL a été retiré, et c'est réfléchi. Un relevé de coût API porterait
# légitimement `tokens_utilises` ou `tokens_entree` : le motif l'aurait refusé, et un faux
# refus bloque le relevé ENTIER — donc rend le dispositif muet, ce qui est bien pire que le
# gain marginal du motif. Les vrais secrets de ce dépôt restent couverts : `sk-ant-…`
# (clé Anthropic), `hooks.slack.com/…` (webhook), `xoxb-…` (jeton Slack),
# `WP_AS_APP_PASSWORD` (password), `api_key`. C'est l'exigence de CLAUDE.md sur les
# portillons : la fixture contient un cas qui doit PASSER, choisi près de la frontière.
MOTS_INTERDITS = ("secret", "password", "passwd", "api_key", "apikey", "api-key",
                  "webhook", "hooks.slack.com", "authorization", "bearer",
                  "sk-ant", "xoxb-", "xoxp-", "app_password")


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True)
    return (r.stdout or "").strip() if r.returncode == 0 else ""


def etat_git() -> dict:
    """Ce que le dépôt de production dit de lui-même — la question « est-ce déployé ? »."""
    return {
        "branche": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": _git("rev-parse", "--short", "HEAD"),
        "date_head": _git("log", "-1", "--format=%cs"),
        "sujet_head": _git("log", "-1", "--format=%s")[:120],
        "propre": _git("status", "--porcelain") == "",
    }


def etat_crons() -> dict:
    """Dernier passage de chaque script, et son âge en heures.

    L'ÂGE plutôt que l'horodatage seul : « scraper : 2026-08-17 08:00 » demande un calcul
    mental, « scraper : il y a 8 h » se lit. Et c'est l'absence qui alerte, pas la date.
    """
    try:
        derniers = pipeline_status.last_runs()
    except Exception as exc:  # noqa: BLE001 — un relevé ne doit jamais tomber
        log.warning("Passages de crons illisibles (%s).", exc)
        return {}
    maintenant = datetime.now()
    out = {}
    for script, runs in (derniers or {}).items():
        if not runs:
            continue
        r = runs[0]
        quand = str(r.get("at") or r.get("ts") or "")[:19]
        heures = None
        try:
            heures = round((maintenant - datetime.fromisoformat(quand)).total_seconds() / 3600, 1)
        except (ValueError, TypeError):
            pass
        out[script] = {"dernier": quand, "il_y_a_h": heures,
                       "ok": r.get("ok"), "erreurs": r.get("error")}
    return out


def etat_files() -> dict:
    """Étages, flux et goulot — repris tels quels du tableau de bord, jamais recomptés."""
    if not DB.exists():
        return {"erreur": "base absente"}
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            etages = es.etages(conn)
            flux = es.flux(conn)
            goulot = es.goulot(etages)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        log.warning("Base illisible (%s).", exc)
        return {"erreur": str(exc)[:120]}
    return {
        "etages": [{"nom": e.get("nom"), "restants": e.get("restants"),
                    "faits": e.get("faits"), "pct": e.get("pct")} for e in etages],
        "flux": flux,
        "goulot": (goulot or {}).get("nom") if goulot else None,
    }


def etat_api() -> dict:
    """Le crédit API, vu par ses CONSÉQUENCES en base — pas par une question au fournisseur.

    Trois jours de panne de facturation ont arrêté évaluation, enrichissement, datation LLM,
    traduction et SEO (14 → 17 août). La question « est-ce rétabli ? » se répond ici : le
    nombre de fiches garées en `api_error` et la date du dernier enrichissement RÉUSSI.
    """
    if not DB.exists():
        return {"erreur": "base absente"}
    out: dict = {}
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
            if "enrich_status" in cols:
                out["api_error"] = conn.execute(
                    "SELECT COUNT(*) FROM events_raw WHERE enrich_status='api_error'"
                ).fetchone()[0]
                out["enrichis"] = conn.execute(
                    "SELECT COUNT(*) FROM events_raw WHERE enrich_status='done'"
                ).fetchone()[0]
            if "enriched_at" in cols:
                out["dernier_enrichissement"] = conn.execute(
                    "SELECT MAX(enriched_at) FROM events_raw"
                ).fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"erreur": str(exc)[:120]}
    return out


def etat_couts(jours: int = 7) -> dict:
    """Ce que la chaîne a coûté, et pour quel résultat.

    AJOUTÉ LE 2026-08-18, parce que Franck a posé LA question que je ne pouvais pas
    trancher : « quelle conséquence il va y avoir avec les dix fiches par jour ? ». Le
    coût par fiche est mesuré depuis le 11/08 (scripts/audit_couts), mais il vit dans la
    base du serveur — donc hors de portée d'une session. Sans ce champ, la réponse à
    toute question d'arbitrage de coût est « lance cette commande et colle-moi le
    résultat », c'est-à-dire exactement la dépendance qu'on supprime.

    On REPREND les fonctions d'audit_couts au lieu de recompter : deux compteurs du même
    nom finissent par se contredire, et c'est le plus gros qu'on croit (règle 6).

    ⚠️ Le coût par fiche n'a de sens qu'avec son dénominateur : on rend les deux, plus le
    nombre de postes mesurés — un total bas peut vouloir dire « peu dépensé » ou
    « instrumentation incomplète », et ces deux-là n'appellent pas la même décision.
    """
    from datetime import timedelta
    try:
        from scripts.audit_couts import _lire, _fiches_publiees
    except Exception as exc:  # noqa: BLE001 — un relevé ne doit jamais tomber
        return {"erreur": f"audit_couts illisible : {exc}"[:120]}
    depuis = (datetime.now() - timedelta(days=jours)).date().isoformat()
    try:
        lignes = _lire(depuis)
        publiees = _fiches_publiees(depuis)
    except Exception as exc:  # noqa: BLE001
        return {"erreur": str(exc)[:120]}
    total = sum(float(e.get("cout_usd") or 0) for e in lignes)
    par_poste: dict[str, float] = {}
    for e in lignes:
        poste = str(e.get("poste") or e.get("script") or "?")
        par_poste[poste] = par_poste.get(poste, 0.0) + float(e.get("cout_usd") or 0)
    haut = sorted(par_poste.items(), key=lambda kv: kv[1], reverse=True)[:6]
    return {
        "jours": jours,
        "appels_mesures": len(lignes),
        "cout_usd_total": round(total, 2),
        "fiches_publiees": publiees,
        "cout_usd_par_fiche": round(total / publiees, 2) if publiees else None,
        "postes_les_plus_chers": [{"poste": k, "usd": round(v, 2)} for k, v in haut],
    }


# Ce que chaque provenance COÛTE. C'est la seule classification qui compte pour
# l'arbitrage : « gratuit » = lecture déterministe (données structurées de la page,
# corps du mail, registre de lieux connus), « payant » = un appel au modèle.
PROVENANCES_GRATUITES = ("page", "mail", "source", "registre", "moisson", "jsonld")
PROVENANCES_PAYANTES = ("llm", "web")


def etat_provenance() -> dict:
    """D'où viennent RÉELLEMENT les dates et les lieux : du code, ou du modèle ?

    D'OÙ ÇA VIENT — Franck, 2026-08-18 : « toutes les données qu'on trouve dans les
    sources, pourquoi on a besoin d'agents ? Je te rappelle qu'une fois on avait quatre
    cents tâches et on a utilisé ZÉRO API. »

    La doctrine du dépôt (docs/LLM_OU_CODE.md) répond déjà « code par défaut, LLM pour
    l'irréductible ». Mais PERSONNE N'A JAMAIS MESURÉ la part réelle de chacun, alors que
    la base la connaît depuis toujours : `date_source` et `venue_source` enregistrent la
    provenance à chaque écriture. Sans ce chiffre, « on a besoin d'agents » et « on n'en a
    pas besoin » sont deux opinions ; avec lui, c'est un arbitrage.

    Le comptage porte sur les fiches ENCORE DEVANT NOUS (règle 5) : ce qui a été trouvé
    pour un événement de juin ne dit rien sur ce qu'il faut financer demain.
    """
    if not DB.exists():
        return {"erreur": "base absente"}
    from datetime import date as _date
    auj = _date.today().isoformat()
    out: dict = {}
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
            for champ in ("date_source", "venue_source"):
                if champ not in cols:
                    continue
                lignes = conn.execute(
                    f"SELECT COALESCE({champ},'(vide)') p, COUNT(*) n FROM events_raw "
                    "WHERE COALESCE(duplicate_of,0)=0 AND COALESCE(translation_of,0)=0 "
                    "  AND (COALESCE(date_event_end, date_event_start, '')='' "
                    "       OR COALESCE(date_event_end, date_event_start) >= ?) "
                    f"GROUP BY p ORDER BY n DESC", (auj,)).fetchall()
                detail = {str(p): int(n) for p, n in lignes}
                gratuit = sum(v for k, v in detail.items() if k in PROVENANCES_GRATUITES)
                payant = sum(v for k, v in detail.items() if k in PROVENANCES_PAYANTES)
                # Le reste (vide, none, llm_none, nodate) n'est ni l'un ni l'autre : ce
                # sont les champs NON RÉSOLUS. Les compter avec les gratuits ferait passer
                # un échec pour une économie.
                out[champ] = {
                    "detail": detail,
                    "gratuit": gratuit,
                    "payant": payant,
                    "non_resolu": sum(detail.values()) - gratuit - payant,
                    "part_gratuite_pct": (round(100 * gratuit / (gratuit + payant))
                                          if (gratuit + payant) else None),
                }
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"erreur": str(exc)[:120]}
    return out


def releve() -> dict:
    """Le relevé complet. Composé CHAMP PAR CHAMP : aucun balayage d'environnement, donc
    aucun secret ne peut s'y glisser par accident."""
    return {
        "date": datetime.now().isoformat(timespec="seconds"),
        "git": etat_git(),
        "crons": etat_crons(),
        "files": etat_files(),
        "api": etat_api(),
        "couts": etat_couts(),
        "provenance": etat_provenance(),
    }


def contient_un_secret(objet) -> str:
    """Renvoie le mot fautif si le relevé contient quelque chose qui ressemble à un secret.

    Contrôle de dernière minute AVANT l'envoi, en plus de la fixture : le jour où quelqu'un
    ajoutera un champ commode (« et si on mettait la config ? »), l'envoi refusera.
    """
    texte = json.dumps(objet, ensure_ascii=False).lower()
    for mot in MOTS_INTERDITS:
        if mot in texte:
            return mot
    return ""


def publier(r: dict) -> tuple[bool, str]:
    load_dotenv(ROOT / ".env")
    url = (os.getenv("WP_AS_URL") or "").rstrip("/")
    user = os.getenv("WP_AS_USER") or ""
    mdp = os.getenv("WP_AS_APP_PASSWORD") or ""
    if not (url and user and mdp):
        return False, "WP_AS_URL/USER/APP_PASSWORD absents"
    faute = contient_un_secret(r)
    if faute:
        return False, (f"REFUS : le relevé contient « {faute} » — un relevé "
                       f"d'exploitation ne transporte aucun secret")
    jeton = base64.b64encode(f"{user}:{mdp}".encode("utf-8")).decode("ascii")
    # TROIS TENTATIVES ESPACÉES DE 30 s PUIS 120 s. L'espacement d'origine (5 s, 10 s) a
    # été choisi contre un « hoquet réseau » ; l'échec réellement observé est un
    # `ConnectTimeoutError`, c'est-à-dire une connexion TCP qui n'aboutit pas. Sur un
    # hébergement mutualisé, ça se produit par FENÊTRE — une limite de connexions par IP
    # qui se referme pour une à quelques minutes. Rejouer trois fois en quinze secondes
    # retombe forcément dans la même fenêtre : les trois tentatives n'en faisaient qu'une.
    dernier = ""
    for essai, attente in enumerate((30, 120, 0)):
        try:
            rep = requests.post(f"{url}{_ROUTE}", json={"releve": r},
                                auth=(user, mdp),
                                headers={**_UA, "X-CS-Auth": jeton}, timeout=30)
            if rep.status_code == 404:
                return False, "route cs/v1/sante absente — mu-plugin cs-sante.php déployé ?"
            if rep.status_code in (401, 403):
                # Un refus n'est pas un hoquet : le rejouer deux fois ne fait qu'user le
                # compte. On sort tout de suite, en DISANT lequel des deux c'est.
                return False, (f"{rep.status_code} — identifiants WordPress refusés "
                               f"(WP_AS_USER / WP_AS_APP_PASSWORD), pas un problème réseau")
            rep.raise_for_status()
            gardes = (rep.json() or {}).get("gardes")
            return True, f"relevé déposé, {gardes} en réserve"
        except (requests.RequestException, ValueError) as exc:
            dernier = str(exc)[:160]
            log.warning("Dépôt du relevé, tentative %d/3 : %s", essai + 1, dernier)
            if attente:
                time.sleep(attente)
    return False, f"{dernier}\n{diagnostic(url)}"


def diagnostic(url: str) -> str:
    """POURQUOI le dépôt a échoué — mesuré, pas supposé.

    ÉCRIT APRÈS M'ÊTRE TROMPÉ (2026-08-18). Le premier échec ne disait que
    « ConnectTimeoutError ». J'ai supposé un filtrage sur l'agent utilisateur, corrigé
    l'agent, et l'échec a continué : deux allers-retours avec Franck pour une hypothèse
    que dix secondes de mesure auraient écartée. Un dispositif censé RENDRE autonome ne
    peut pas se permettre de rendre un message d'erreur qui demande une enquête.

    Les trois questions, dans l'ordre où elles éliminent des causes :

      1. le nom se résout-il ?           non → DNS, rien à voir avec WordPress ;
      2. le port 443 s'ouvre-t-il ?      non → filtrage ou fenêtre anti-flood côté hôte ;
      3. la route répond-elle SANS       401 → la route vit, seul l'identifiant a manqué ;
         authentification ?              autre → c'est WordPress qui est en cause.

    Aucun secret n'est employé ici : c'est justement une sonde anonyme, pour séparer
    « on ne m'atteint pas » de « on me refuse ».
    """
    from urllib.parse import urlparse
    hote = urlparse(url).hostname or url
    lignes = [f"— diagnostic sur {hote} —"]

    import socket
    try:
        ips = sorted({x[4][0] for x in socket.getaddrinfo(hote, 443)})
        lignes.append(f"DNS : {', '.join(ips)}")
    except OSError as exc:
        return "\n".join(lignes + [f"DNS : ÉCHEC ({exc}) → le nom ne se résout pas depuis "
                                   f"cette machine ; WordPress n'est pas en cause."])

    # UN PROXY EXPLIQUERAIT TOUT. `requests` honore http_proxy/https_proxy de
    # l'environnement — et `publier()` appelle `load_dotenv()`, donc une ligne de proxy
    # dans `.env` s'appliquerait ici. Un proxy mort donne exactement un ConnectTimeoutError
    # alors que le port du site, lui, s'ouvre très bien. On ne rend QUE le schéma et le
    # nom d'hôte du proxy : une URL de proxy peut porter un identifiant.
    # On ne garde que les clés qui pilotent VRAIMENT requests : la lecture de
    # l'environnement ramasse aussi npm_config_https, yarn_https, docker_https… qui ne
    # concernent pas ce script et noieraient la ligne utile.
    proxies = {k: v for k, v in requests.utils.get_environ_proxies(url).items()
               if k in ("http", "https", "all")}
    if proxies:
        noms = []
        for schema, cible in proxies.items():
            h = urlparse(cible).hostname or "?"
            noms.append(f"{schema}→{h}")
        lignes.append(f"PROXY configuré : {', '.join(noms)}")
        lignes.append("→ c'est par là que passe la requête, PAS en direct. Si le test TCP "
                      "ci-dessous réussit alors que le dépôt échoue, le proxy est le "
                      "coupable (variable http_proxy/https_proxy, éventuellement dans .env).")
    else:
        lignes.append("PROXY : aucun (connexion directe)")

    debut = time.monotonic()
    try:
        with socket.create_connection((hote, 443), timeout=10):
            lignes.append(f"TCP 443 : ouvert en {time.monotonic() - debut:.1f} s")
    except OSError as exc:
        lignes.append(f"TCP 443 : REFUSÉ/SANS RÉPONSE après "
                      f"{time.monotonic() - debut:.1f} s ({exc.__class__.__name__})")
        lignes.append("→ la connexion n'aboutit pas : filtrage ou limite de connexions "
                      "par IP chez l'hébergeur. Réessayer plus tard, ou depuis une autre "
                      "IP, dira lequel des deux.")
        return "\n".join(lignes)

    try:
        sonde = requests.get(f"{url}{_ROUTE}", headers=_UA, timeout=15)
        lignes.append(f"GET sans authentification : {sonde.status_code}")
        if sonde.status_code == 401:
            lignes.append("→ la route vit et exige une authentification, comme prévu. "
                          "L'échec du dépôt vient donc des identifiants ou du POST, "
                          "pas du réseau.")
        elif sonde.status_code == 404:
            lignes.append("→ route absente : mu-plugin cs-sante.php non déployé.")
        else:
            lignes.append("→ réponse inattendue : c'est WordPress qu'il faut regarder.")
    except requests.RequestException as exc:
        lignes.append(f"GET sans authentification : ÉCHEC ({str(exc)[:90]})")
        lignes.append("→ le port s'ouvre mais HTTPS ne répond pas : couche TLS ou serveur "
                      "web saturé.")
    return "\n".join(lignes)


def afficher(r: dict) -> None:
    """Ce que le terminal montre. LE PLUS IMPORTANT D'ABORD, et rien de coupé en silence.

    D'OÙ ÇA VIENT — 2026-08-18. La sortie était `json.dumps(relevé)[:2000]`. Or la
    provenance — le chiffre demandé par Franck, « pourquoi on a besoin d'agents » — est la
    DERNIÈRE section du relevé. Elle a donc été calculée trois fois et jetée trois fois
    par la troncature, sans que rien ne le dise : les trois sorties s'arrêtaient au milieu
    de la section « api », et j'ai cru que le script ne l'avait pas produite. Trois
    allers-retours pour un `[:2000]`.

    C'est la règle du 17/08 mot pour mot : **une liste tronquée doit annoncer son total**,
    sans quoi elle fabrique de fausses causes — y compris pour celui qui l'a écrite. Donc
    ici : les sections courtes et décisives en entier, le reste résumé, et la coupe DITE.
    """
    prov = r.get("provenance") or {}
    if "erreur" in prov:
        print(f"PROVENANCE : indisponible — {prov['erreur']}")
    elif prov:
        print("PROVENANCE — d'où viennent les dates et les lieux des fiches ENCORE DEVANT NOUS")
        for champ, m in prov.items():
            pct = m.get("part_gratuite_pct")
            print(f"  {champ:13s} code={m.get('gratuit')}  modèle={m.get('payant')}  "
                  f"non résolu={m.get('non_resolu')}  "
                  f"part du code : {pct if pct is not None else '—'}%")
            detail = ", ".join(f"{k}={v}" for k, v in (m.get("detail") or {}).items())
            print(f"                {detail}")
    else:
        print("PROVENANCE : aucune donnée (colonnes date_source/venue_source absentes ?)")

    couts = r.get("couts") or {}
    if couts:
        print("\nCOÛTS : " + ", ".join(f"{k}={v}" for k, v in couts.items()))

    print("\nÉTAT — " + json.dumps({k: v for k, v in r.items()
                                    if k not in ("provenance", "couts")},
                                   ensure_ascii=False)[:1200])
    print("(état abrégé pour le terminal ; le relevé COMPLET est ce qui part sur "
          "WordPress, rien n'est coupé à l'envoi)")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Dépose l'état du pipeline sur WordPress.")
    p.add_argument("--publier", action="store_true", help="Envoie réellement.")
    args = p.parse_args(argv)

    r = releve()
    afficher(r)
    faute = contient_un_secret(r)
    if faute:
        print(f"\n⚠️ REFUS : « {faute} » trouvé dans le relevé.")
        return 1
    if not args.publier:
        print("\nDRY-RUN — rien envoyé. Relancer avec --publier.")
        return 0
    ok, detail = publier(r)
    print(f"\n{'OK' if ok else 'ÉCHEC'} — {detail}")
    log.info("Relevé de santé : %s (%s)", "déposé" if ok else "non déposé", detail)
    if not ok:
        # IL SE TAIT QUAND TOUT VA BIEN — JAMAIS QUAND IL A ÉCHOUÉ.
        # Défaut constaté sur mon propre dispositif, le 2026-08-18 à 13h01 : le premier
        # passage (12h05) n'a rien déposé, et personne ne l'a su. Je l'avais écrit
        # « silencieux : c'est de la donnée, pas une alerte » — vrai pour le SUCCÈS,
        # faux pour l'échec. Un relevé de santé muet quand il tombe est un relevé qui
        # ment par omission : on croit l'état bon parce qu'on ne voit rien.
        # Le message part dans la boîte du jour, donc dans le récapitulatif — pas en
        # notification séparée : c'est une panne d'observation, pas une urgence.
        from utils import slack
        slack.notify(f"🩺 *Relevé de santé non déposé* — {detail}\n"
                     f"_Sans lui, une session Claude ne peut pas voir l'état du serveur "
                     f"(files, crons, crédit) et devra vous le demander. "
                     f"Journal : `tail -30 logs/sante.log`._")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
