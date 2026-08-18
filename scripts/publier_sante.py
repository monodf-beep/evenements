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
# LE MÊME EN-TÊTE QUE LE CHEMIN QUI MARCHE (scripts/publisher_as.py). Constaté le
# 2026-08-18 : `publish_batch_as` a mis à jour WP#6380 à 13h01, et sept minutes plus tard
# ce script rendait un ConnectTimeoutError sur le MÊME hôte. La seule différence entre les
# deux requêtes était l'en-tête : un agent utilisateur maison contre un navigateur. Le
# filtrage devant le site (Cloudflare/WAF) laisse passer l'un et fait tomber l'autre dans
# le vide — pas un 403 franc, un silence, ce qui est plus dur à diagnostiquer.
# On reprend donc l'en-tête éprouvé plutôt que d'en inventer un.
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
    # TROIS TENTATIVES ESPACÉES. Le premier échec observé était un ConnectTimeoutError,
    # pas un refus : le site n'a pas dit non, il n'a pas répondu. Un relevé quotidien qui
    # abandonne au premier hoquet réseau laisse une journée sans état, et c'est exactement
    # l'angle mort qu'il existe pour fermer.
    dernier = ""
    for essai in range(3):
        try:
            rep = requests.post(f"{url}{_ROUTE}", json={"releve": r},
                                auth=(user, mdp),
                                headers={**_UA, "X-CS-Auth": jeton}, timeout=30)
            if rep.status_code == 404:
                return False, "route cs/v1/sante absente — mu-plugin cs-sante.php déployé ?"
            rep.raise_for_status()
            gardes = (rep.json() or {}).get("gardes")
            return True, f"relevé déposé, {gardes} en réserve"
        except (requests.RequestException, ValueError) as exc:
            dernier = str(exc)[:160]
            log.warning("Dépôt du relevé, tentative %d/3 : %s", essai + 1, dernier)
            if essai < 2:
                time.sleep(5 * (essai + 1))
    return False, dernier


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Dépose l'état du pipeline sur WordPress.")
    p.add_argument("--publier", action="store_true", help="Envoie réellement.")
    args = p.parse_args(argv)

    r = releve()
    print(json.dumps(r, ensure_ascii=False, indent=1)[:2000])
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
