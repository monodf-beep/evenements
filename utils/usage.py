# SYNCED FROM observatoire-business-sabaudo — ne pas diverger (extraction future cultura-core)
"""Suivi de la consommation API (tokens + coût estimé) pour visibilité dans l'admin.

Chaque appel LLM enregistre une ligne dans logs/api_usage.jsonl (modèle, tokens
entrée/sortie, recherches web, coût estimé). L'admin agrège et affiche le total de
la semaine et le cumul. Fail-safe : un échec d'écriture n'interrompt jamais un appel.

Les tarifs (USD / million de tokens) sont indicatifs et éditables ci-dessous.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USAGE_FILE = ROOT / "logs" / "api_usage.jsonl"
ALERT_FILE = ROOT / "logs" / "api_alert.json"

# Indices d'un problème d'ACCÈS API : crédit, facturation OU limite d'usage atteinte.
_CREDIT_HINTS = ("credit", "billing", "balance", "insufficient", "quota",
                 "payment", "exceeded", "402", "too low", "usage limit",
                 "usage limits", "reached your", "rate limit", "regain access")

# Tarifs estimatifs (USD par million de tokens) : (entrée, sortie).
PRICES = {
    "claude-opus-4-8": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-5": (3.0, 15.0),  # tarif à confirmer (aligné sur claude-sonnet-4-6)
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),  # tarif à confirmer (aligné sur claude-haiku-4-5)
}
_DEFAULT_PRICE = (3.0, 15.0)
_WEB_SEARCH_PER_1K = 10.0  # USD pour 1000 recherches web (outil serveur)


def _week(dt: datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def cost_of(model: str, in_tok: int, out_tok: int, web: int = 0) -> float:
    in_r, out_r = PRICES.get(model, _DEFAULT_PRICE)
    return in_tok / 1e6 * in_r + out_tok / 1e6 * out_r + web / 1000 * _WEB_SEARCH_PER_1K


def flag_credit_issue(message: str) -> None:
    """Pose un drapeau « crédit API épuisé / facturation » visible dans l'admin."""
    try:
        ALERT_FILE.parent.mkdir(parents=True, exist_ok=True)
        ALERT_FILE.write_text(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(), "message": str(message)[:300],
        }, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def clear_alert() -> None:
    try:
        ALERT_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# DEUX CAUSES, DEUX DURÉES DE BLOCAGE. Le drapeau servait indistinctement à tout, avec
# sept jours pour tout le monde. Or les deux causes ne se lèvent pas de la même façon :
#
#   • LIMITE D'USAGE atteinte (quota, rate limit) — se résout par l'écoulement du temps,
#     et le message d'Anthropic annonce souvent l'heure de reset. Bloquer longtemps est
#     juste : retenter avant l'heure dite ne peut que réechouer.
#   • SOLDE À RECHARGER — se résout par une action HUMAINE de trente secondes, à un
#     moment que le code ne peut pas connaître. Mesuré le 2026-08-05 : le solde tombe à
#     zéro pendant le cron de 07:00 UTC, Franck recharge dans la journée, et le pipeline
#     reste bloqué quand même. Le drapeau ne se lève qu'au prochain appel RÉUSSI — or il
#     empêche justement tout appel. Une demi-journée perdue, et une session entière
#     passée à croire que le crédit manquait alors qu'il était là.
#
# Le correctif du 2026-07-31 traitait déjà ce cercle vicieux, mais seulement pour les
# messages portant une heure de reset explicite (« regain access on … », cf.
# scripts/enrich.py). Un message de solde n'en porte aucune : il retombait donc sur les
# sept jours pleins. D'où un TTL court pour cette cause-là. Le coût d'une nouvelle
# tentative est nul (l'API refuse en HTTP 400, aucun token consommé), alors qu'une
# journée de pipeline à l'arrêt se paie en fiches non publiées.
_TTL_LIMITE_JOURS = 7
_TTL_SOLDE_MINUTES = 30

# Ce qui distingue « recharge ton compte » de « attends ». Volontairement plus étroit que
# _CREDIT_HINTS, qui sert à DÉTECTER un problème d'accès : ici on qualifie sa nature, et
# un doute doit retomber sur le blocage long (prudent), pas sur le court.
_SOLDE_HINTS = ("credit balance", "too low", "insufficient", "billing", "payment", "402")


def _ttl_secondes(message: str) -> int:
    """Durée pendant laquelle le drapeau bloque, selon la cause lue dans le message."""
    blob = (message or "").lower()
    if any(h in blob for h in _SOLDE_HINTS):
        return _TTL_SOLDE_MINUTES * 60
    return _TTL_LIMITE_JOURS * 86400


def get_alert() -> dict | None:
    """Renvoie l'alerte d'accès API en cours, ou None si elle a expiré.

    La durée dépend de la cause (cf. _ttl_secondes) : une limite d'usage bloque sept
    jours, un solde à recharger seulement trente minutes."""
    try:
        data = json.loads(ALERT_FILE.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(data.get("ts", ""))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age < _ttl_secondes(data.get("message") or ""):
            return data
    except Exception:
        return None
    return None


def note_api_error(exc) -> None:
    """Inspecte une exception d'appel API : si elle évoque un problème de crédit /
    facturation / quota, pose le drapeau d'alerte. Sinon, ne fait rien."""
    try:
        blob = f"{getattr(exc, 'status_code', '')} {exc}".lower()
        if any(h in blob for h in _CREDIT_HINTS):
            flag_credit_issue(exc)
    except Exception:
        pass


def record(model: str, in_tok: int = 0, out_tok: int = 0, web: int = 0, label: str = "") -> None:
    """Enregistre un appel API (jamais bloquant). Un appel réussi LÈVE l'alerte crédit."""
    clear_alert()
    try:
        now = datetime.now(timezone.utc)
        event = {
            "ts": now.isoformat(), "week": _week(now), "model": model,
            "in": int(in_tok or 0), "out": int(out_tok or 0), "web": int(web or 0),
            "cost": round(cost_of(model, int(in_tok or 0), int(out_tok or 0), int(web or 0)), 5),
            "label": label,
        }
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USAGE_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def record_message(model: str, message, web: int = 0, label: str = "") -> None:
    """Enregistre depuis un objet message Anthropic (lit message.usage)."""
    try:
        u = getattr(message, "usage", None)
        in_tok = getattr(u, "input_tokens", 0) or 0
        out_tok = getattr(u, "output_tokens", 0) or 0
        # Recherches web (outil serveur) si exposées par le SDK.
        stu = getattr(u, "server_tool_use", None)
        if web == 0 and stu is not None:
            web = getattr(stu, "web_search_requests", 0) or 0
        record(model, in_tok, out_tok, web, label)
    except Exception:
        pass


def summarize() -> dict:
    """Agrège l'usage : par semaine, par modèle, et PAR ÉTAPE.

    L'agrégat par étape manquait alors que chaque appel porte son étiquette depuis le
    début (`label` : « rédaction », « traduction », « évaluation », « datation »…). Le
    tableau de bord montrait donc combien on dépense, jamais À QUOI — et « 218 dollars sur
    claude-sonnet-5 » ne dit pas s'il faut réduire la rédaction, la traduction ou les
    recherches de lieux. Franck, 2026-08-11 : « il faudrait que tu expliques le détail des
    coûts ». Un chiffre sans sa décomposition ne se pilote pas, il se subit — c'est la même
    règle que pour les files, appliquée à l'argent.

    On garde aussi l'entrée et la sortie SÉPARÉES par étape. C'est la vraie information :
    sur les 4 041 appels cumulés au 11 août, l'entrée pèse 45 millions de jetons pour
    4 millions en sortie, soit environ 17 500 jetons envoyés par appel. Aux tarifs actuels
    (3 $ / million en entrée, 15 $ en sortie), les deux tiers de la facture viennent de ce
    qu'on ENVOIE, pas de ce que le modèle écrit."""
    weeks: dict[str, dict] = {}
    total = {"cost": 0.0, "in": 0, "out": 0, "web": 0, "calls": 0,
             "by_model": {}, "by_label": {}}
    if not USAGE_FILE.exists():
        return {"weeks": {}, "total": total, "current_week": _week(datetime.now(timezone.utc))}
    try:
        lines = USAGE_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    for line in lines:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        wk = e.get("week", "?")
        model = e.get("model", "?")
        cost, i, o, w = e.get("cost", 0.0), e.get("in", 0), e.get("out", 0), e.get("web", 0)
        # Une étiquette vide vaut « non étiqueté » plutôt que de disparaître : un poste de
        # dépense qu'on ne voit pas est un poste qu'on ne réduira jamais.
        label = (e.get("label") or "").strip() or "(non étiqueté)"
        for bucket in (weeks.setdefault(wk, {"cost": 0.0, "in": 0, "out": 0, "web": 0,
                                             "calls": 0, "by_model": {}, "by_label": {}}),
                       total):
            bucket["cost"] += cost
            bucket["in"] += i
            bucket["out"] += o
            bucket["web"] += w
            bucket["calls"] += 1
            bm = bucket["by_model"].setdefault(model, {"cost": 0.0, "in": 0, "out": 0, "calls": 0})
            bm["cost"] += cost
            bm["in"] += i
            bm["out"] += o
            bm["calls"] += 1
            bl = bucket.setdefault("by_label", {}).setdefault(
                label, {"cost": 0.0, "in": 0, "out": 0, "calls": 0})
            bl["cost"] += cost
            bl["in"] += i
            bl["out"] += o
            bl["calls"] += 1
    return {"weeks": weeks, "total": total,
            "current_week": _week(datetime.now(timezone.utc))}


def explique(total: dict) -> dict:
    """Traduit les totaux en phrases pilotables : où part l'argent, et sur quoi agir.

    TROIS CHIFFRES, ET LE TROISIÈME EST LE SEUL LEVIER.

    `part_entree` — la fraction de la facture due aux jetons ENVOYÉS. Contre-intuitif :
    l'entrée est cinq fois moins chère que la sortie au jeton, et elle coûte pourtant plus,
    parce qu'on en envoie dix fois plus. On ne paie pas ce que le modèle écrit, on paie ce
    qu'on lui donne à lire.

    `entree_par_appel` — combien de jetons partent à chaque requête. C'est la voix
    éditoriale, le savoir local, les personas, la consigne et la matière source, réunis et
    renvoyés en entier À CHAQUE FOIS. Au-delà de dix mille, il y a un stock à réduire ou à
    mettre en cache.

    `cout_par_appel` — l'unité qui permet d'arbitrer : est-ce que cette étape vaut son
    prix ? La réponse dépend de ce qu'elle produit, et c'est un jugement humain — le
    chiffre ne le remplace pas, il le rend possible."""
    appels = max(1, total.get("calls", 0))
    tin, tout = total.get("in", 0), total.get("out", 0)
    # Le coût réel est déjà additionné appel par appel ; on ne le recalcule pas. On
    # reconstitue seulement la RÉPARTITION, au tarif moyen constaté sur les modèles vus.
    part_in = 0.0
    for m, d in (total.get("by_model") or {}).items():
        pin, pout = PRICES.get(m, _DEFAULT_PRICE)
        part_in += d.get("in", 0) / 1e6 * pin
    cout = total.get("cost", 0.0)
    return {
        "appels": total.get("calls", 0),
        "cout": cout,
        "cout_par_appel": cout / appels,
        "entree_par_appel": round(tin / appels),
        "sortie_par_appel": round(tout / appels),
        "part_entree": round(part_in / cout * 100) if cout else None,
        "ratio": round(tin / tout, 1) if tout else None,
    }
