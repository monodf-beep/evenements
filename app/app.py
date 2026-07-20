#!/usr/bin/env python3
"""Backoffice de validation des événements — interface Franck.

Auth HTTP Basic. Design minimaliste fonctionnel.
- /            : dashboard (KPIs, coûts API, répartitions, sources, newsletters)
- /validation  : file des événements à valider (score ≥ 7)
- /action/...  : Publier CS / Subdomain / Rejeter

Lance avec : gunicorn -w 1 -b 127.0.0.1:5001 'app.app:app'
"""
from __future__ import annotations
import hashlib
import hmac
import html
import json
import os
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import datetime, date, timedelta
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import re

from scripts.publisher import publish_to_cs
from scripts.publisher_as import publish_to_as
from scripts.scraper_events import load_sources, init_db
from utils.logger import get_logger
from utils import usage
from utils import completeness as comp
from utils import slack
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
log = get_logger("backoffice")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
NEWSLETTERS_FILE = ROOT / "config" / "newsletters.txt"

# URL publique du backoffice — sert à fabriquer les liens de suivi /go/<id> lus
# par WordPress. On la FORCE (au lieu de request.host_url) car derrière Traefik la
# requête arrive en http sur la loopback : un lien http:// serait rejeté par le
# fail-safe « https-only » de cs-regie-serve.php. Surchargée par BACKOFFICE_BASE_URL.
PUBLIC_BASE_URL = os.getenv(
    "BACKOFFICE_BASE_URL", "https://backoffice.agendasabauda.eu").rstrip("/")

# Garantit que la base + le schéma existent, même sur un VPS frais où aucun
# scraping n'a encore tourné : sinon le dashboard planterait sur "no such table".
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_conn = sqlite3.connect(DB_PATH)
init_db(_conn)
_conn.close()

TERRITORIES = ["Savoie", "Piemonte", "Vallee-Aoste", "Nice"]
PAGE_SIZE = 50
STATUS_LABELS = {
    "pending": "En attente",
    "evaluated": "À valider",
    "published_cs": "Cultura Sabauda",
    "published_sub": "Agenda Sabauda",
    "rejected": "Rejeté",
    "merged": "Fusionné",
}

# --------------------------------------------------------------------------- #
# Périodes de travail (« ce week-end », « week-end prochain »…)
# On travaille par PÉRIODE : la vue re-fait surface aux événements qui CHEVAUCHENT
# la fenêtre (une expo longue réapparaît chaque week-end, comme GuidaTorino). Le
# coût, lui, est piloté par le STATUT (on n'évalue/enrichit que les 'pending').
# --------------------------------------------------------------------------- #
def _weekend_of(d: date) -> tuple[date, date]:
    """(vendredi, dimanche) du week-end de la semaine contenant d (week-end = ven→dim)."""
    wd = d.weekday()  # lun=0 … dim=6
    friday = d + timedelta(days=(4 - wd)) if wd <= 4 else d - timedelta(days=(wd - 4))
    return friday, friday + timedelta(days=2)


PERIOD_PRESETS = ["weekend", "next_weekend", "7d", "month"]


def period_bounds(preset: str, dfrom: str, dto: str):
    """Renvoie (from_iso, to_iso, label) pour un preset ou une plage perso. ('','','') si aucun."""
    today = date.today()
    if preset == "weekend":
        f, s = _weekend_of(today)
        return f.isoformat(), s.isoformat(), "Ce week-end"
    if preset == "next_weekend":
        f, s = _weekend_of(today + timedelta(days=7))
        return f.isoformat(), s.isoformat(), "Week-end prochain"
    if preset == "7d":
        return today.isoformat(), (today + timedelta(days=7)).isoformat(), "7 prochains jours"
    if preset == "month":
        return today.isoformat(), (today + timedelta(days=30)).isoformat(), "30 prochains jours"
    if dfrom or dto:
        f = dfrom or today.isoformat()
        t = dto or f
        return f, t, f"{f} → {t}"
    return "", "", ""


def annotate_period(events: list[dict], pfrom: str, pto: str) -> list[dict]:
    """Marque chaque événement pour la valorisation d'une période :
    - _ending  : c'est le DERNIER week-end (événement en cours qui se termine dans la
                 fenêtre) → angle « dernière chance », comme GuidaTorino ;
    - _republish : déjà valorisé (publié) mais toujours en cours → à re-proposer ;
    - _new     : retenu, pas encore valorisé.
    Tout est déterministe (comparaison de dates ISO), pas de LLM."""
    for e in events:
        start = e.get("date_event_start") or ""
        end = e.get("date_event_end") or ""
        is_range = bool(end) and (not start or start < end)
        e["_ending"] = bool(pfrom and pto and end and is_range and pfrom <= end <= pto)
        e["_republish"] = e.get("statut") in ("published_cs", "published_sub")
        e["_new"] = e.get("statut") == "evaluated"
    return events


def overlap_clause(pfrom: str, pto: str) -> tuple[str, list]:
    """Clause SQL : l'événement CHEVAUCHE [pfrom, pto]. Les non-datés (start/end vides
    ou NULL) sont naturellement exclus. Un « jusqu'au X » (start vide, end rempli) est
    inclus s'il court encore pendant la fenêtre."""
    return ("COALESCE(date_event_start,'') <= ? AND COALESCE(date_event_end,'') >= ?",
            [pto, pfrom])


def incomplete_clause(today: str) -> tuple[str, list]:
    """Clause SQL : événement RETENU, À VENIR, mais INCOMPLET (porte qualité).

    Miroir exact de utils.completeness.is_complete côté base : un champ obligatoire
    manque (date, lieu, ville, territoire, catégorie, image). Les non-datés sont
    inclus (ils manquent justement la date) SAUF les récurrents (la date y est
    remplacée par une note → non requise). cf. utils/completeness.py."""
    parts = []
    for k, _ in comp.MANDATORY:
        if k == "date_event_start":
            # Récurrent : date non requise (note « vérifiez sur la source »).
            parts.append("(COALESCE(date_event_start,'')='' AND COALESCE(recurring,0)=0)")
        else:
            parts.append(f"COALESCE({k},'')=''")
    empties = " OR ".join(parts)
    clause = (
        "statut IN ('evaluated','published_cs','published_sub') AND duplicate_of IS NULL "
        "AND (COALESCE(date_event_end, date_event_start, '')='' "
        "     OR COALESCE(date_event_end, date_event_start) >= ?) "
        f"AND ({empties})")
    return clause, [today]


app = Flask(__name__, template_folder="templates", static_folder="static")
# Clé de session : FLASK_SECRET_KEY si fournie, sinon dérivée (stable entre les
# workers gunicorn) des identifiants — pas de secret aléatoire qui invaliderait
# les sessions à chaque redémarrage / par worker.
app.secret_key = os.getenv("FLASK_SECRET_KEY") or hashlib.sha256(
    (os.getenv("BACKOFFICE_USER", "admin") + ":"
     + os.getenv("BACKOFFICE_PASSWORD", "")).encode("utf-8")
).hexdigest()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")


def check_auth(username, password):
    """Comparaison à temps constant des identifiants du .env."""
    u = os.getenv("BACKOFFICE_USER", "admin")
    p = os.getenv("BACKOFFICE_PASSWORD", "")
    return (hmac.compare_digest(username or "", u)
            and hmac.compare_digest(password or "", p))


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        if check_auth(request.form.get("username"), request.form.get("password")):
            session["logged_in"] = True
            session["user"] = request.form.get("username")
            # Anti open-redirect : on n'autorise qu'un chemin local.
            nxt = request.args.get("next") or ""
            if not nxt.startswith("/") or nxt.startswith("//"):
                nxt = url_for("dashboard")
            return redirect(nxt)
        error = "Identifiants incorrects."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def get_db():
    # timeout=30 + busy_timeout : on ATTEND le verrou (jusqu'à 30 s) au lieu de lever
    # « database is locked » quand un script du pipeline écrit en même temps. WAL
    # (posé par init_db) permet en plus la lecture concurrente pendant une écriture.
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=30000")
    except sqlite3.OperationalError:
        pass
    return conn


def event_image(ev: dict) -> str:
    """URL de la photo de l'événement (vide si la source n'en fournit pas).

    Pas de bannière de substitution ici : l'alternative pour les événements sans
    photo est une tâche à venir (voir docs/BACKLOG.md).
    """
    return ev.get("url_image") or ""


def clean_html(text: str) -> str:
    """Texte propre : retire les balises ET décode les entités HTML (&nbsp; …)."""
    text = re.sub(r"(?s)<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def friendly_alert():
    """Met en forme l'alerte API (crédit/quota) pour le bandeau du backoffice.

    Extrait le type de problème et, si présente, la date de reprise d'accès.
    """
    a = usage.get_alert()
    if not a:
        return None
    msg = a.get("message", "")
    low = msg.lower()
    m = re.search(r"regain access on (\d{4}-\d{2}-\d{2})(?: at (\d{2}:\d{2}))?", msg)
    reset = None
    if m:
        reset = m.group(1) + (f" à {m.group(2)} UTC" if m.group(2) else "")
    if any(k in low for k in ("usage limit", "reached your", "quota", "regain access")):
        kind = "Quota / limite d'usage API atteint"
    elif any(k in low for k in ("credit", "billing", "balance", "insufficient", "payment", "402")):
        kind = "Crédit API épuisé / facturation"
    else:
        kind = "Problème d'accès à l'API"
    return {"kind": kind, "reset": reset, "raw": msg, "ts": a.get("ts", "")}


@app.context_processor
def inject_globals():
    """Compteurs de navigation + alerte, disponibles dans TOUTES les pages (base.html)."""
    pending = validate = tocomplete = 0
    try:
        conn = get_db()
        pending = conn.execute(
            "SELECT COUNT(*) n FROM events_raw WHERE statut='pending'").fetchone()["n"]
        validate = conn.execute(
            "SELECT COUNT(*) n FROM events_raw WHERE statut='evaluated' AND llm_score>=7"
        ).fetchone()["n"]
        clause, cp = incomplete_clause(date.today().isoformat())
        tocomplete = conn.execute(
            f"SELECT COUNT(*) n FROM events_raw WHERE {clause}", cp).fetchone()["n"]
        conn.close()
    except Exception:
        pass
    regie = 0
    try:
        conn = get_db()
        _ensure_regie_table(conn)
        regie = conn.execute(
            "SELECT COUNT(*) n FROM ad_campaigns WHERE statut='active' "
            "AND date_fin IS NOT NULL AND date_fin<>'' "
            "AND julianday(date_fin)-julianday('now','localtime') <= 3").fetchone()["n"]
        conn.close()
    except Exception:
        pass
    return {"nav": {"pending": pending, "validate": validate,
                    "tocomplete": tocomplete, "regie": regie},
            "nav_alert": friendly_alert(),
            # Bases WordPress (liens directs vers les brouillons créés) :
            #   wp_base    → culturasabauda.eu (article, wp_post_id_cs)
            #   wp_as_base → agendasabauda.eu (événement, wp_post_id_as)
            "wp_base": (os.getenv("WP_URL", "") or "").rstrip("/"),
            "wp_as_base": (os.getenv("WP_AS_URL", "") or "").rstrip("/")}


# --------------------------------------------------------------------------- #
# Lancement manuel des étapes du pipeline (boutons du dashboard)
# --------------------------------------------------------------------------- #
TASKS = {
    "scrape":   {"script": "scripts/scraper_events.py", "label": "Scraping RSS", "icon": "📡", "cost": False, "phase": "collect", "help": "Récupère les événements des flux RSS."},
    "gmail":    {"script": "scripts/gmail_collect.py",   "label": "Newsletters Gmail", "icon": "📬", "cost": True, "phase": "collect", "help": "Lit les newsletters du label « Agenda »."},
    "press":    {"script": "scripts/press_kits.py",      "label": "Dossiers de presse", "icon": "📎", "cost": False, "phase": "collect", "help": "Lit les dossiers de presse du label « Presse »."},
    "dedupe":   {"script": "scripts/dedupe.py",          "label": "Déduplication", "icon": "🔗", "cost": False, "phase": "prepare", "help": "Fusionne les doublons multi-sources."},
    "dates":    {"script": "scripts/dates.py",           "label": "Datation", "icon": "📅", "cost": False, "phase": "prepare", "help": "Extrait la vraie date de chaque événement."},
    "evaluate": {"script": "scripts/evaluator.py",       "label": "Évaluation", "icon": "🧠", "cost": True, "period": True, "phase": "prepare", "help": "Claude note l'intérêt éditorial (0-10)."},
    "enrich":   {"script": "scripts/enrich.py",          "label": "Enrichissement + rédaction", "icon": "✍️", "cost": True, "period": True, "phase": "prepare", "help": "Recherche + rédige l'article des retenus."},
    "visuals":  {"script": "scripts/visuals.py",         "label": "Compléter les visuels", "icon": "🖼️", "cost": True, "period": True, "phase": "prepare", "help": "Photo pour les retenus sans image : og:image → Wikimedia Commons (licenciable, LLM) → bannière territoire."},
    "complete": {"script": "scripts/complete_period.py", "label": "Tout compléter (période)", "icon": "✨", "cost": True, "period": True, "phase": "prepare", "help": "Enchaîne datation → évaluation → visuels → enrichissement sur la période. Idempotent : ne refait que ce qui manque."},
    "autocomplete": {"script": "scripts/autocomplete.py", "label": "Auto-compléter + porte qualité", "icon": "🛠️", "cost": True, "period": True, "phase": "prepare", "help": "Complète les événements retenus incomplets (date/lieu/image via scraping + recherche web), pousse les COMPLETS en brouillon Agenda Sabauda, et signale sur Slack ce qui reste à compléter. Choisis une période pour limiter le traitement."},
    "newsletter": {"script": "scripts/newsletter.py",    "label": "Newsletter (brouillon)", "icon": "📧", "cost": False, "phase": "publish", "help": "Brouillon Brevo des événements Savoie de la semaine."},
}
COLLECT_TASKS = [k for k, v in TASKS.items() if v.get("phase") == "collect"]
PREPARE_TASKS = [k for k, v in TASKS.items() if v.get("phase") == "prepare"]
RUN_STATE = ROOT / "data" / "run_state.json"


def _load_runstate() -> dict:
    try:
        return json.loads(RUN_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_runstate(st: dict) -> None:
    try:
        RUN_STATE.parent.mkdir(parents=True, exist_ok=True)
        RUN_STATE.write_text(json.dumps(st), encoding="utf-8")
    except Exception:
        pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def _running_state() -> dict:
    """Renvoie {task: running_bool} en RÉCOLTANT les process terminés.

    Un process fini devient zombie tant qu'il n'est pas « reaped » : os.kill(0)
    le verrait encore vivant. On utilise waitpid(WNOHANG) pour le récolter et
    on persiste un flag « done » (le service tourne en 1 worker gunicorn, donc
    c'est bien le parent qui suit ses enfants).
    """
    st = _load_runstate()
    changed = False
    result = {}
    for task, info in st.items():
        if info.get("done") or not info.get("pid"):
            result[task] = False
            continue
        pid = int(info["pid"])
        running = True
        try:
            wpid, _status = os.waitpid(pid, os.WNOHANG)
            if wpid == pid:           # vient de se terminer (récolté)
                running = False
        except ChildProcessError:     # pas/plus notre enfant
            running = _pid_alive(pid)
        except Exception:
            running = _pid_alive(pid)
        if not running:
            info["done"] = True
            changed = True
        result[task] = running
    if changed:
        _save_runstate(st)
    return result


def launch_task(task: str, extra_args: list | None = None) -> tuple[bool, str]:
    """Lance un script du pipeline en arrière-plan (non bloquant)."""
    if _running_state().get(task):
        return False, "déjà en cours"
    script = ROOT / TASKS[task]["script"]
    logf = ROOT / "logs" / f"run_{task}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    fh = open(logf, "ab")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script), *(extra_args or [])], cwd=str(ROOT),
            stdout=fh, stderr=fh, start_new_session=True)
    except Exception as exc:  # pragma: no cover
        return False, f"échec : {exc}"
    st = _load_runstate()
    st[task] = {"pid": proc.pid, "done": False,
                "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    _save_runstate(st)
    return True, "lancé"


def tasks_status() -> dict:
    st = _load_runstate()
    running = _running_state()
    out = {}
    for key, meta in TASKS.items():
        info = st.get(key, {})
        logf = ROOT / "logs" / f"run_{key}.log"
        tail = ""
        if logf.exists():
            try:
                lines = logf.read_text(encoding="utf-8", errors="replace").strip().splitlines()
                tail = lines[-1][:200] if lines else ""
            except Exception:
                tail = ""
        out[key] = {**meta, "running": running.get(key, False),
                    "started": info.get("started", ""), "tail": tail}
    return out


def load_newsletters() -> list[dict]:
    """Lit config/newsletters.txt : nom;domaine;territoire;statut."""
    rows: list[dict] = []
    if not NEWSLETTERS_FILE.exists():
        return rows
    for line in NEWSLETTERS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ";" not in line:
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) >= 4:
            rows.append({"nom": parts[0], "domaine": parts[1],
                         "territoire": parts[2], "statut": parts[3]})
    return rows


@app.route("/")
@require_auth
def dashboard():
    conn = get_db()
    status_counts = {r["statut"]: r["n"] for r in conn.execute(
        "SELECT statut, COUNT(*) n FROM events_raw GROUP BY statut")}
    terr_counts = {r["territoire"] or "—": r["n"] for r in conn.execute(
        "SELECT territoire, COUNT(*) n FROM events_raw GROUP BY territoire")}
    cat_counts = conn.execute(
        "SELECT llm_categorie c, COUNT(*) n FROM events_raw "
        "WHERE llm_categorie IS NOT NULL AND llm_categorie != '' "
        "GROUP BY llm_categorie ORDER BY n DESC").fetchall()
    to_validate = conn.execute(
        "SELECT COUNT(*) n FROM events_raw WHERE statut='evaluated' AND llm_score>=7"
    ).fetchone()["n"]
    imgrow = conn.execute(
        "SELECT SUM(CASE WHEN url_image IS NOT NULL AND url_image != '' THEN 1 ELSE 0 END) wi, "
        "COUNT(*) t FROM events_raw").fetchone()
    with_img = imgrow["wi"] or 0
    without_img = (imgrow["t"] or 0) - with_img
    # Brouillons RÉELLEMENT créés sur WordPress (tracés par wp_post_id_*), pas par le
    # statut : c'est ce qui bouge quand tu publies (le KPI se met enfin à jour).
    draftrow = conn.execute(
        "SELECT SUM(CASE WHEN COALESCE(wp_post_id_cs,0)>0 THEN 1 ELSE 0 END) cs, "
        "SUM(CASE WHEN COALESCE(wp_post_id_as,0)>0 THEN 1 ELSE 0 END) ag FROM events_raw"
    ).fetchone()
    drafts_cs = draftrow["cs"] or 0
    drafts_as = draftrow["ag"] or 0
    # Alertes métier : ce qui bloque le flux éditorial (visibles en bandeau).
    biz = {
        "undated": conn.execute(
            "SELECT COUNT(*) n FROM events_raw WHERE COALESCE(date_event_start,'')='' "
            "AND COALESCE(date_event_end,'')='' AND statut NOT IN ('rejected','merged') "
            "AND duplicate_of IS NULL").fetchone()["n"],
        "retained_nophoto": conn.execute(
            "SELECT COUNT(*) n FROM events_raw WHERE statut IN "
            "('evaluated','published_cs','published_sub') AND duplicate_of IS NULL "
            "AND COALESCE(url_image,'')=''").fetchone()["n"],
    }
    # SEO : événements phares (publiés sur Cultura Sabauda) et combien ont déjà
    # leurs métadonnées SEO générées. Point d'entrée visible depuis le dashboard.
    try:
        seo = {
            "phares": conn.execute(
                "SELECT COUNT(*) n FROM events_raw WHERE statut='published_cs' "
                "AND duplicate_of IS NULL").fetchone()["n"],
            "optimises": conn.execute(
                "SELECT COUNT(*) n FROM events_raw WHERE seo_at IS NOT NULL").fetchone()["n"],
        }
    except sqlite3.OperationalError:
        seo = {"phares": 0, "optimises": 0}
    conn.close()

    # « Collectés » actifs : hors rejetés/fusionnés (le total brut était trompeur).
    total = sum(n for s, n in status_counts.items() if s not in ("rejected", "merged"))
    summary = usage.summarize()
    week = summary["current_week"]
    cost = {
        "week_label": week,
        "week": summary["weeks"].get(week, {}).get("cost", 0.0),
        "total": summary["total"]["cost"],
        "calls_total": summary["total"]["calls"],
        "by_model": summary["total"]["by_model"],
    }

    src_counts = Counter(s["territoire"] for s in load_sources())
    newsletters = load_newsletters()
    nl_active = sum(1 for n in newsletters if n["statut"] == "actif")
    tasks = tasks_status()
    any_running = any(t["running"] for t in tasks.values())
    # Derniers lancements, le plus RÉCENT en premier (tri par horodatage décroissant).
    runs = sorted([(k, t) for k, t in tasks.items() if t.get("tail")],
                  key=lambda kt: kt[1].get("started", ""), reverse=True)

    # Période de travail du panneau de run (défaut : week-end prochain) + aperçu du
    # nombre d'événements que chaque étape coûteuse traiterait sur cette fenêtre.
    preset = request.args.get("preset", "next_weekend")
    dfrom = request.args.get("dfrom", "")
    dto = request.args.get("dto", "")
    pfrom, pto, plabel = period_bounds(preset, dfrom, dto)
    scope = {"eval": None, "enrich": None}
    if pfrom and pto:
        clause, cp = overlap_clause(pfrom, pto)
        thr = int(os.getenv("ENRICH_MIN_SCORE", "7"))
        conn = get_db()
        scope["eval"] = conn.execute(
            f"SELECT COUNT(*) n FROM events_raw WHERE statut='pending' AND {clause}",
            cp).fetchone()["n"]
        scope["enrich"] = conn.execute(
            "SELECT COUNT(*) n FROM events_raw WHERE statut IN ('evaluated','published_sub') "
            "AND llm_score >= ? AND (enrich_status IS NULL OR enrich_status='') "
            f"AND duplicate_of IS NULL AND {clause}", [thr, *cp]).fetchone()["n"]
        conn.close()

    return render_template(
        "dashboard.html",
        total=total, to_validate=to_validate,
        status_counts=status_counts, status_labels=STATUS_LABELS,
        terr_counts=terr_counts, cat_counts=cat_counts,
        territories=TERRITORIES,
        cost=cost, alert=friendly_alert(),
        src_counts=src_counts, src_total=sum(src_counts.values()),
        newsletters=newsletters, nl_active=nl_active,
        tasks=tasks, any_running=any_running, runs=runs,
        with_img=with_img, without_img=without_img, biz=biz, seo=seo,
        drafts_cs=drafts_cs, drafts_as=drafts_as,
        preset=preset, dfrom=dfrom, dto=dto, plabel=plabel,
        presets=PERIOD_PRESETS, scope=scope, today=date.today().isoformat(),
    )


@app.route("/pilotage")
@require_auth
def pilotage():
    """Onglet « Pilotage » : santé ÉDITORIALE / couverture, calculée uniquement
    depuis la base (aucune API externe, rien qui casse). Le pilotage du TRAFIC
    (impressions, clics, position) vit dans Looker Studio, pas ici — cf.
    docs/MARKETING_ET_PILOTAGE_AGENDA_SABAUDO.md."""
    today = date.today().isoformat()
    # « À venir » = se termine (ou commence, à défaut de fin) aujourd'hui ou après.
    end_expr = "COALESCE(NULLIF(date_event_end,''), NULLIF(date_event_start,''))"
    active = "statut NOT IN ('rejected','merged') AND duplicate_of IS NULL"
    retained = "statut IN ('evaluated','published_cs','published_sub') AND duplicate_of IS NULL"
    thr = int(os.getenv("ENRICH_MIN_SCORE", "7"))
    conn = get_db()

    def one(sql, params=()):
        return conn.execute(sql, params).fetchone()["n"]

    # 1. Fond de stock : événements actifs À VENIR (datés).
    future = one(f"SELECT COUNT(*) n FROM events_raw WHERE {active} AND {end_expr} >= ?", (today,))

    # 2. Couverture par territoire (actifs à venir) — déséquilibre = signal éditorial.
    terr_rows = conn.execute(
        f"SELECT COALESCE(NULLIF(territoire,''),'—') t, COUNT(*) n FROM events_raw "
        f"WHERE {active} AND {end_expr} >= ? GROUP BY t", (today,)).fetchall()
    terr_future = {r["t"]: r["n"] for r in terr_rows}

    # 3. Photo (actifs à venir) — le trou de sourcing déjà identifié.
    with_photo = one(
        f"SELECT COUNT(*) n FROM events_raw WHERE {active} AND {end_expr} >= ? "
        "AND COALESCE(url_image,'')!=''", (today,))

    # 4. Routage (actifs à venir, scorés) : ≥ seuil → Cultura Sabauda ; < seuil → Agenda Sabauda.
    route_cs = one(
        f"SELECT COUNT(*) n FROM events_raw WHERE {active} AND {end_expr} >= ? "
        "AND llm_score >= ?", (today, thr))
    route_as = one(
        f"SELECT COUNT(*) n FROM events_raw WHERE {active} AND {end_expr} >= ? "
        "AND llm_score IS NOT NULL AND llm_score < ?", (today, thr))

    # 5. Passés NON purgés : retenus dont la date est révolue mais toujours actifs.
    past_active = one(
        f"SELECT COUNT(*) n FROM events_raw WHERE {retained} AND {end_expr} != '' "
        f"AND {end_expr} < ?", (today,))

    # 6. File de publication : candidats Cultura Sabauda (≥ seuil, à venir) pas encore
    #    poussés en brouillon WordPress.
    queue_cs = one(
        f"SELECT COUNT(*) n FROM events_raw WHERE statut='evaluated' AND llm_score >= ? "
        f"AND duplicate_of IS NULL AND {end_expr} >= ? AND COALESCE(wp_post_id_cs,0)=0",
        (thr, today))

    # Aperçu des modules de la home publique : combien chaque rubrique (Ce week-end,
    # Sagres, Concerts…) contiendrait AUJOURD'HUI. Sert à voir l'auto-remplissage et
    # les trous. cf. utils/home_modules.py (= spéc des requêtes TEC pour WordPress).
    from utils import home_modules as hm
    home = hm.preview(conn, date.today(), thr)
    # Conseiller « ce que TU dois faire » : actions humaines déduites de l'état de
    # la base (le reste est automatique). cf. utils/advisor.py.
    from utils import advisor as adv
    todo = adv.advise(conn, date.today(), thr, TERRITORIES)
    conn.close()
    metrics = {
        "future": future, "with_photo": with_photo,
        "photo_pct": round(with_photo / future * 100) if future else 0,
        "route_cs": route_cs, "route_as": route_as,
        "past_active": past_active, "queue_cs": queue_cs, "thr": thr,
    }
    return render_template(
        "pilotage.html", m=metrics, terr_future=terr_future, home=home, todo=todo,
        territories=TERRITORIES, today=today, alert=friendly_alert())


@app.route("/process")
@require_auth
def process_page():
    """Schéma pédagogique : le process complet, les agents, les boucles.

    Page statique (aucune requête base/API) — juste une carte du fonctionnement."""
    return render_template("process.html", active="process")


# Wireframe annoté de la home : sections RÉELLES observées sur agendasabauda.eu,
# chacune avec sa règle d'affichage (intention → filtre → score → tri → statut).
# statut : ok=dynamique en place · cabler=à câbler · corriger=bug à corriger ·
#          placeholder=faux contenu à convertir · encours=en cours.
HOME_SECTIONS = [
    {"nom": "En-tête + navigation", "kind": "struct", "intention": "Repères de marque + accès rapides",
     "filtre": "—", "score": "—", "tri": "—", "statut": "ok",
     "note": "Ce week-end · Événements · Curiosités · Lieux · Annoncer · bascule FR/IT."},
    {"nom": "Hero — « Agenda Sabauda »", "kind": "struct", "intention": "Identité + accroche transfrontalière",
     "filtre": "—", "score": "—", "tri": "—", "statut": "ok", "note": "Masthead + baseline."},
    {"nom": "À la une / En vedette", "kind": "vedette", "intention": "« Le rendez-vous à ne pas manquer »",
     "filtre": "événements à venir (date ≥ aujourd'hui)", "score": "le PLUS HAUT (llm_score max)",
     "tri": "score ↓ · limite 1", "statut": "cabler",
     "note": "1 grande carte = l'événement le mieux noté du moment. C'est ici que le score sert le plus."},
    {"nom": "Ce week-end", "kind": "liste", "intention": "« Que faire ce week-end ? »",
     "filtre": "date = samedi→dimanche courant · tous territoires", "score": "départage",
     "tri": "date ↑ puis score ↓", "statut": "ok", "note": "Se décale tout seul chaque semaine."},
    {"nom": "Événements d'aujourd'hui", "kind": "liste", "intention": "« Ce soir / aujourd'hui »",
     "filtre": "⚠️ actuellement STRICTEMENT = aujourd'hui → souvent VIDE (« No data »)",
     "score": "—", "tri": "date ↑", "statut": "corriger",
     "note": "À passer en « à venir (7 jours) » : un agenda clairsemé n'a pas d'événement CHAQUE jour."},
    {"nom": "Nouveautés sur Agenda Sabauda", "kind": "cartes", "intention": "« Quoi de neuf »",
     "filtre": "événements récemment AJOUTÉS", "score": "—", "tri": "date d'ajout ↓", "statut": "placeholder",
     "note": "Aujourd'hui = 3 faux articles codés en dur → à convertir en Sélection dynamique."},
    {"nom": "En évidence", "kind": "cartes", "intention": "« Notre sélection »",
     "filtre": "à venir + score élevé", "score": "seuil haut", "tri": "score ↓", "statut": "encours",
     "note": "Affiche de VRAIS événements (Festival, Concert) — images en cours de correction."},
    {"nom": "L'agenda à venir", "kind": "liste", "intention": "« Les prochains rendez-vous »",
     "filtre": "date ≥ aujourd'hui", "score": "—", "tri": "date ↑", "statut": "ok",
     "note": "Liste chronologique des suivants (Sagra, Course…)."},
    {"nom": "Par catégorie — En famille · Concerts · Expos · Gastronomie", "kind": "cartes",
     "intention": "« Par envie »", "filtre": "catégorie choisie + à venir",
     "score": "mise en avant interne", "tri": "score ↓ puis date ↑", "statut": "cabler",
     "note": "Les catégories existent (bilingues) ; chaque section = une Listing Grid filtrée."},
    {"nom": "Par territoire — Savoie · Piémont · V. d'Aoste · Nice", "kind": "chips",
     "intention": "« Tel territoire »", "filtre": "archive du territoire", "score": "—",
     "tri": "date ↑", "statut": "ok", "note": "Archives de taxonomie déjà en place (bilingues)."},
    {"nom": "Ça vaut le déplacement", "kind": "cartes", "intention": "Transfrontalier — « vaut le voyage »",
     "filtre": "curation MANUELLE (événements voisins épinglés)", "score": "—", "tri": "éditorial",
     "statut": "placeholder", "note": "Aujourd'hui = « Titre/Visuel/Itinéraire à définir » → Sélection manuelle."},
    {"nom": "Publicité", "kind": "struct", "intention": "Régie annonceurs", "filtre": "—", "score": "—",
     "tri": "—", "statut": "ok", "note": "Gérée dans l'onglet Régie (emplacements + suivi des clics)."},
    {"nom": "Pied de page", "kind": "struct", "intention": "Navigation secondaire + mentions",
     "filtre": "—", "score": "—", "tri": "—", "statut": "ok", "note": "Liens explorer / projet / légales."},
]

_STATUT_LABEL = {
    "ok": ("Dynamique en place", "#1a7f4b", "#e9f6ee"),
    "encours": ("En cours", "#b45309", "#fdf3e3"),
    "corriger": ("À corriger", "#dc2626", "#fdeaea"),
    "placeholder": ("Placeholder → à convertir", "#8a5a00", "#fbf1dd"),
    "cabler": ("À câbler", "#2563eb", "#e8f0fe"),
    "struct": ("Structure", "#6F6B62", "#f0efe9"),
}


# Plan des encarts publicitaires — le plan de 12 blocs câblé dans le THÈME
# (agenda-sabauda-core). MODÈLE « OVERRIDE » (décision 2026-07-20) : chaque bloc est
# AdSense par défaut ; une campagne créée dans le backoffice pour ce bloc REMPLACE
# l'AdSense le temps de la campagne (via le shortcode [cs_slot bloc="N"]…AdSense…[/cs_slot]).
# ⚠️ = incertitude relevée à la lecture du code (STATUS.md vs fichier réel).
AD_PLAN = [
    {"bloc": "1", "format": "Leaderboard 970×90", "emplacement": "Gouttière gauche (homepage-template.php)",
     "dm": "Desktop", "page": "Home", "statut": "AdSense actif (attente Google)", "src": "actif"},
    {"bloc": "2", "format": "Pavé 300×250", "emplacement": "Gouttière droite + pavé sur /evenement/*",
     "dm": "Desktop", "page": "Home + fiche événement", "statut": "AdSense actif (attente Google)", "src": "actif"},
    {"bloc": "3", "format": "Sticky footer 950×120", "emplacement": "Sous le carrousel",
     "dm": "⚠️ incertain (fichier « mobile », décrit desktop)", "page": "Home", "statut": "AdSense — à configurer", "src": "todo"},
    {"bloc": "4", "format": "Skin 950×90", "emplacement": "Sous les tuiles de catégories",
     "dm": "⚠️ incertain (idem)", "page": "Home", "statut": "Skin — à configurer (désactivé)", "src": "todo"},
    {"bloc": "5", "format": "Pavé 300×250", "emplacement": "Colonne « En évidence »",
     "dm": "⚠️ incertain (idem)", "page": "Home", "statut": "AdSense — à configurer", "src": "todo"},
    {"bloc": "6", "format": "Barre sticky 728×90", "emplacement": "Barre sticky desktop",
     "dm": "Desktop (présumé, non confirmé)", "page": "Home", "statut": "AdSense — à configurer", "src": "todo"},
    {"bloc": "7–11", "format": "5 encarts inline (5:3)", "emplacement": "Inline dans la liste",
     "dm": "Mobile (explicite)", "page": "Home", "statut": "AdSense — à configurer", "src": "todo"},
    {"bloc": "12", "format": "Barre sticky mobile", "emplacement": "Bas d'écran mobile",
     "dm": "Mobile (explicite)", "page": "Home", "statut": "AdSense — à configurer", "src": "todo"},
    {"bloc": "13–16", "format": "—", "emplacement": "Aucun usage prévu",
     "dm": "—", "page": "—", "statut": "Réserve (aucun usage)", "src": "reserve"},
]

REGIE_SYSTEMS = [
    {"nom": "Plan 12 blocs (thème agenda-sabauda-core)", "ou": "Live — hors git",
     "role": "La grille d'emplacements pub de la home (gouttières, sticky, inline…)",
     "verdict": "garder", "note": "Fait autorité — colle au Kit Annonceurs. C'est l'ossature des blocs."},
    {"nom": "Ad Inserter", "ou": "Live (wp-admin)",
     "role": "La COUCHE AdSense : le défaut de chaque bloc (leaderboard, pavé…)",
     "verdict": "garder", "note": "Chaque bloc AdSense s'enveloppe dans [cs_slot bloc=\"N\"] pour l'override backoffice."},
    {"nom": "cs-regie-serve.php (backoffice → WP)", "ou": "Git (réécrit 20/07) — pas encore déployé",
     "role": "La primitive d'OVERRIDE : shortcode [cs_slot] = pub backoffice si active, sinon AdSense",
     "verdict": "garder", "note": "API /api/active-ads OK (HTTP 200). Reste à envelopper chaque bloc AdSense côté thème."},
    {"nom": "cs-regie.php (skin/gouttières)", "ou": "Git — jamais déployé",
     "role": "Skin + gouttières via option WP",
     "verdict": "abandonner", "note": "Redondant : le thème gère déjà skin/gouttières (blocs 1, 3, 4)."},
]


@app.route("/wireframe-home")
@require_auth
def wireframe_home():
    """Wireframe annoté de la home : sections + règles + plan des encarts pub."""
    return render_template("wireframe_home.html", active="wireframe",
                           sections=HOME_SECTIONS, labels=_STATUT_LABEL,
                           ad_plan=AD_PLAN, regie_systems=REGIE_SYSTEMS)


# --- Couverture : compteurs par section × territoire × langue --------------------
# Montre, pour chaque fenêtre temporelle du site, combien d'événements RÉELLEMENT en
# ligne (publiés sur Agenda Sabauda) alimentent chaque territoire en FR et en IT.
# But : repérer les MANQUES d'un coup d'œil (ex. « ça vaut le détour » Savoie/Nice en
# IT ≈ 0, car les sources françaises ne produisent pas de fiches italiennes).
_COUV_TERRITOIRES = [
    ("Savoie / Haute-Savoie", ("savoie", "haute savoie")),
    ("Piémont", ("piemont", "piemonte", "piedmont")),
    ("Vallée d'Aoste", ("aoste", "aosta")),
    ("Nice / Alpes-Maritimes", ("nice", "alpes maritimes", "azur")),
]
_MOIS_ABBR = ("", "janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.",
              "août", "sept.", "oct.", "nov.", "déc.")


def _couv_norm(s):
    import unicodedata
    s = (s or "").lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _couv_terr_group(territoire):
    n = _couv_norm(territoire)
    for label, keys in _COUV_TERRITOIRES:
        if any(k in n for k in keys):
            return label
    return "Autre / non classé"


def _couv_date(s):
    try:
        return date.fromisoformat((s or "")[:10])
    except (ValueError, TypeError):
        return None


def _couv_data(conn):
    from utils.lang import detect_lang
    today = date.today()
    wd = today.weekday()                       # lundi=0 … dimanche=6
    sat = today - timedelta(days=wd - 5) if wd >= 5 else today + timedelta(days=5 - wd)
    sun = sat + timedelta(days=1)
    eow = today + timedelta(days=6 - wd)       # dimanche de la semaine en cours
    far = date(2999, 1, 1)
    windows = [
        ("Aujourd'hui", today, today, today.strftime("%d/%m")),
        ("Ce week-end", sat, sun,
         "sam. %d – dim. %d %s" % (sat.day, sun.day, _MOIS_ABBR[sun.month])),
        ("Cette semaine", today, eow, "jusqu'au dim. %d %s" % (eow.day, _MOIS_ABBR[eow.month])),
        ("À venir (tous)", today, far, "à partir d'aujourd'hui"),
    ]
    terr_labels = [t[0] for t in _COUV_TERRITOIRES] + ["Autre / non classé"]

    # matrice[iwin][terr][lang] = compteur ; catégories (à venir) idem.
    mat = {i: {t: {"fr": 0, "it": 0} for t in terr_labels} for i in range(len(windows))}
    cats = {}
    undated = 0

    rows = conn.execute(
        "SELECT title, description, territoire, llm_categorie, "
        "date_event_start, date_start, date_event_end "
        "FROM events_raw WHERE COALESCE(wp_post_id_as,0)>0 AND duplicate_of IS NULL"
    ).fetchall()

    for r in rows:
        es = _couv_date(r["date_event_start"]) or _couv_date(r["date_start"])
        ee = _couv_date(r["date_event_end"]) or es
        lang = detect_lang(r["title"] or "", r["description"] or "", r["territoire"] or "")
        lang = "it" if lang == "it" else "fr"
        grp = _couv_terr_group(r["territoire"])
        if es is None:
            undated += 1
            continue
        for i, (_n, ws, we, _lbl) in enumerate(windows):
            if es <= we and ee >= ws:          # chevauchement fenêtre
                mat[i][grp][lang] += 1
        # Catégories : sur la fenêtre « à venir » (dernière), si l'événement y tombe.
        if ee >= today:
            cat = (r["llm_categorie"] or "—").strip() or "—"
            cats.setdefault(cat, {"fr": 0, "it": 0})[lang] += 1

    # Mise en forme pour le template.
    sections = []
    for i, (name, _ws, _we, lbl) in enumerate(windows):
        trows, tf, ti = [], 0, 0
        for t in terr_labels:
            fr, it = mat[i][t]["fr"], mat[i][t]["it"]
            if t == "Autre / non classé" and fr == 0 and it == 0:
                continue
            trows.append({"terr": t, "fr": fr, "it": it, "total": fr + it})
            tf += fr
            ti += it
        sections.append({"name": name, "label": lbl, "rows": trows,
                         "tot_fr": tf, "tot_it": ti, "tot": tf + ti})
    cat_rows = sorted(
        ({"cat": c, "fr": v["fr"], "it": v["it"], "total": v["fr"] + v["it"]}
         for c, v in cats.items()), key=lambda x: -x["total"])
    return {"sections": sections, "cats": cat_rows, "undated": undated,
            "n_total": len(rows)}


@app.route("/couverture")
@require_auth
def couverture():
    """Compteurs de couverture : section × territoire × langue (repérage des manques)."""
    conn = get_db()
    data = _couv_data(conn)
    conn.close()
    return render_template("couverture.html", active="couverture", **data)


_COWORK_PROMPT_FILE = ROOT / "docs" / "COWORK_AUTOCOMPLETION.md"


def _cowork_prompt() -> str:
    """Extrait le bloc de prompt (entre les ``` ) du doc, pour l'afficher/copier.
    Repli : le doc entier si le bloc n'est pas trouvé."""
    try:
        txt = _COWORK_PROMPT_FILE.read_text(encoding="utf-8")
    except OSError:
        return "(docs/COWORK_AUTOCOMPLETION.md introuvable)"
    m = re.search(r"```\s*\n(.*?)\n```", txt, re.S)
    return m.group(1).strip() if m else txt


def _ensure_cowork_table(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS cowork_runs ("
                 "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "created_at TEXT NOT NULL, report TEXT NOT NULL)")


@app.route("/cowork")
@require_auth
def cowork_page():
    """Prompt de la tâche Cowork (retrouvable) + journal horodaté des passages."""
    conn = get_db()
    _ensure_cowork_table(conn)
    runs = [dict(r) for r in conn.execute(
        "SELECT id, created_at, report FROM cowork_runs "
        "ORDER BY id DESC LIMIT 100").fetchall()]
    last = runs[0]["created_at"] if runs else None
    conn.commit()
    conn.close()
    return render_template("cowork.html", active="cowork",
                           prompt=_cowork_prompt(), runs=runs, last=last)


@app.route("/cowork/log", methods=["POST"])
@require_auth
def cowork_log():
    """Enregistre un passage de Cowork (rapport collé), horodaté côté serveur."""
    report = (request.form.get("report", "") or "").strip()
    if not report:
        flash("⚠️ Rapport vide — rien enregistré.", "err")
        return redirect(url_for("cowork_page"))
    conn = get_db()
    _ensure_cowork_table(conn)
    conn.execute("INSERT INTO cowork_runs (created_at, report) VALUES "
                 "(datetime('now','localtime'), ?)", (report[:20000],))
    conn.commit()
    conn.close()
    flash("✅ Passage Cowork enregistré dans le journal.", "ok")
    return redirect(url_for("cowork_page") + "#journal")


# --------------------------------------------------------------------------- #
# Régie publicitaire — démarche + gestion des campagnes manuelles
# --------------------------------------------------------------------------- #
# Blocs publicitaires du site (cf. docs/REGIE_ANNONCEURS.md).
#   source 'adsense' : rempli automatiquement par Google (rien à gérer ici)
#   source 'manuel'  : régie directe → gérable depuis cette page
AD_BLOCKS = {
    "1": {"nom": "Leaderboard (haut)",           "format": "970×90 · 350×90 mobile",   "source": "adsense",
          "w": 970,  "h": 90,   "prix_base": 250, "prix_lancement": 150},
    "2": {"nom": "Pavé in-article",              "format": "300×250 / 336×280",        "source": "adsense",
          "w": 300,  "h": 250,  "prix_base": 200, "prix_lancement": 120},
    "3": {"nom": "Bandeau bas d'écran (sticky)", "format": "970×90 · vignette mobile", "source": "manuel",
          "w": 970,  "h": 90,   "prix_base": 220, "prix_lancement": 140},
    "4": {"nom": "Habillage / Skin",             "format": "1920×1080 (desktop only)", "source": "manuel",
          "w": 1920, "h": 1080, "prix_base": 600, "prix_lancement": 390},
}


def _ensure_regie_table(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS ad_campaigns ("
                 "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "created_at TEXT NOT NULL, annonceur TEXT NOT NULL, "
                 "bloc TEXT NOT NULL, format TEXT, url TEXT, image_url TEXT, "
                 "date_debut TEXT, date_fin TEXT, tarif TEXT, note TEXT, "
                 "statut TEXT NOT NULL DEFAULT 'active')")
    # Migration douce : compteur de clics (ajouté après coup, sans casser l'existant).
    cols = {r[1] for r in conn.execute("PRAGMA table_info(ad_campaigns)").fetchall()}
    if "clicks" not in cols:
        conn.execute("ALTER TABLE ad_campaigns ADD COLUMN clicks INTEGER NOT NULL DEFAULT 0")
    if "last_click" not in cols:
        conn.execute("ALTER TABLE ad_campaigns ADD COLUMN last_click TEXT")


@app.route("/regie")
@require_auth
def regie_page():
    """Démarche pour poser une pub manuelle + suivi des campagnes (dates, échéances)."""
    conn = get_db()
    _ensure_regie_table(conn)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM ad_campaigns ORDER BY "
        "CASE statut WHEN 'active' THEN 0 ELSE 1 END, "
        "date_fin IS NULL, date_fin").fetchall()]
    conn.commit()
    conn.close()
    today = date.today()
    occupied = {}  # bloc -> campagne active en cours
    for r in rows:
        r["days_left"] = None
        if r.get("date_fin"):
            try:
                r["days_left"] = (date.fromisoformat(r["date_fin"]) - today).days
            except ValueError:
                pass
        r["expired"] = bool(r["statut"] == "active" and r["days_left"] is not None
                            and r["days_left"] < 0)
        if r["statut"] == "active" and not r["expired"]:
            occupied.setdefault(r["bloc"], r)
    return render_template("regie.html", active="regie", blocks=AD_BLOCKS,
                           campaigns=rows, occupied=occupied,
                           today=today.isoformat(),
                           go_base=PUBLIC_BASE_URL)


@app.route("/regie/add", methods=["POST"])
@require_auth
def regie_add():
    """Enregistre une campagne (trace + date de fin pour l'alerte d'échéance)."""
    f = request.form
    annonceur = (f.get("annonceur", "") or "").strip()
    bloc = (f.get("bloc", "") or "").strip()
    if not annonceur or bloc not in AD_BLOCKS:
        flash("⚠️ Annonceur et bloc sont obligatoires.", "err")
        return redirect(url_for("regie_page") + "#ajouter")
    conn = get_db()
    _ensure_regie_table(conn)
    conn.execute(
        "INSERT INTO ad_campaigns (created_at, annonceur, bloc, format, url, "
        "image_url, date_debut, date_fin, tarif, note, statut) VALUES "
        "(datetime('now','localtime'),?,?,?,?,?,?,?,?,?,'active')",
        (annonceur[:200], bloc, AD_BLOCKS[bloc]["format"],
         (f.get("url", "") or "").strip()[:500],
         (f.get("image_url", "") or "").strip()[:500],
         (f.get("date_debut", "") or "").strip()[:10],
         (f.get("date_fin", "") or "").strip()[:10],
         (f.get("tarif", "") or "").strip()[:50],
         (f.get("note", "") or "").strip()[:1000]))
    conn.commit()
    conn.close()
    flash("✅ Campagne enregistrée dans la régie.", "ok")
    return redirect(url_for("regie_page"))


@app.route("/regie/end/<int:cid>", methods=["POST"])
@require_auth
def regie_end(cid):
    """Marque une campagne comme terminée (à faire à l'échéance, après avoir "
    "désactivé/remplacé le bloc côté site)."""
    conn = get_db()
    _ensure_regie_table(conn)
    conn.execute("UPDATE ad_campaigns SET statut='ended' WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    flash("Campagne marquée « terminée ».", "ok")
    return redirect(url_for("regie_page"))


@app.route("/regie/delete/<int:cid>", methods=["POST"])
@require_auth
def regie_delete(cid):
    """Supprime définitivement une ligne de campagne."""
    conn = get_db()
    _ensure_regie_table(conn)
    conn.execute("DELETE FROM ad_campaigns WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    flash("Campagne supprimée.", "ok")
    return redirect(url_for("regie_page"))


@app.route("/regie/edit/<int:cid>", methods=["POST"])
@require_auth
def regie_edit(cid):
    """Corrige une campagne existante (garde l'id, les clics et la date de création)."""
    f = request.form
    annonceur = (f.get("annonceur", "") or "").strip()
    bloc = (f.get("bloc", "") or "").strip()
    if not annonceur or bloc not in AD_BLOCKS:
        flash("⚠️ Annonceur et bloc sont obligatoires.", "err")
        return redirect(url_for("regie_page"))
    conn = get_db()
    _ensure_regie_table(conn)
    conn.execute(
        "UPDATE ad_campaigns SET annonceur=?, bloc=?, format=?, url=?, image_url=?, "
        "date_debut=?, date_fin=?, tarif=?, note=? WHERE id=?",
        (annonceur[:200], bloc, AD_BLOCKS[bloc]["format"],
         (f.get("url", "") or "").strip()[:500],
         (f.get("image_url", "") or "").strip()[:500],
         (f.get("date_debut", "") or "").strip()[:10],
         (f.get("date_fin", "") or "").strip()[:10],
         (f.get("tarif", "") or "").strip()[:50],
         (f.get("note", "") or "").strip()[:1000], cid))
    conn.commit()
    conn.close()
    flash("✅ Campagne mise à jour.", "ok")
    return redirect(url_for("regie_page"))


@app.route("/regie/reactivate/<int:cid>", methods=["POST"])
@require_auth
def regie_reactivate(cid):
    """Repasse une campagne « terminée » en active."""
    conn = get_db()
    _ensure_regie_table(conn)
    conn.execute("UPDATE ad_campaigns SET statut='active' WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    flash("Campagne réactivée.", "ok")
    return redirect(url_for("regie_page"))


@app.route("/go/<int:cid>")
def regie_go(cid):
    """Redirection PUBLIQUE comptée : enregistre le clic puis renvoie vers l'annonceur.

    C'est le lien à mettre comme destination de la pub (/go/<id>) : chaque clic
    est compté ici (indépendamment du consentement et de Google), puis le visiteur
    est redirigé vers le vrai site de l'annonceur. Pas d'auth : les visiteurs
    doivent pouvoir cliquer. Pas d'open-redirect : la destination vient de la base
    (posée par l'admin), jamais de l'URL.
    """
    conn = get_db()
    _ensure_regie_table(conn)
    row = conn.execute("SELECT url FROM ad_campaigns WHERE id=?", (cid,)).fetchone()
    dest = (row["url"] if row else "") or ""
    if dest and re.match(r"^https?://", dest):
        conn.execute("UPDATE ad_campaigns SET clicks=clicks+1, "
                     "last_click=datetime('now','localtime') WHERE id=?", (cid,))
        conn.commit()
        conn.close()
        return redirect(dest, code=302)
    conn.close()
    fallback = (os.getenv("WP_AS_URL", "") or "https://agendasabauda.eu").rstrip("/")
    return redirect(fallback + "/", code=302)


@app.route("/api/active-ads")
def regie_active_ads():
    """API PUBLIQUE lue par WordPress : les pubs manuelles actuellement à diffuser.

    Renvoie, par bloc, la créative active du jour (statut actif, dans la fenêtre de
    dates, image + destination renseignées). Le module WordPress cs-regie-serve.php
    interroge cette URL (avec cache) et affiche la pub tout seul — plus de copier-coller.
    Un seul annonceur par bloc (le plus récent l'emporte).
    """
    conn = get_db()
    _ensure_regie_table(conn)
    today = date.today().isoformat()
    rows = conn.execute(
        "SELECT id, bloc, image_url, url FROM ad_campaigns "
        "WHERE statut='active' AND image_url<>'' AND url<>'' "
        "AND (date_debut IS NULL OR date_debut='' OR date_debut<=?) "
        "AND (date_fin   IS NULL OR date_fin=''   OR date_fin>=?) "
        "ORDER BY id ASC", (today, today)).fetchall()
    conn.close()
    base = PUBLIC_BASE_URL  # https + host public, sinon rejet par l'allowlist WP
    ads = {}
    for r in rows:
        ads[r["bloc"]] = {
            "id": r["id"],
            "image": r["image_url"],
            "link": base + "/go/" + str(r["id"]),
            "format": AD_BLOCKS.get(r["bloc"], {}).get("format", ""),
        }
    resp = jsonify({"ads": ads})
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Cache-Control"] = "public, max-age=120"
    return resp


@app.route("/api/status")
@require_auth
def api_status():
    """État minimal du pipeline pour le polling JS (fin de tâche → un seul reload)."""
    running = any(t["running"] for t in tasks_status().values())
    return {"running": running}


@app.route("/run/<task>", methods=["POST"])
@require_auth
def run_task(task: str):
    if task not in TASKS:
        return "Tâche inconnue", 404
    extra = []
    # Étapes coûteuses : on peut les circonscrire à une période de travail.
    if TASKS[task].get("period"):
        pfrom, pto, plabel = period_bounds(
            request.form.get("preset", ""),
            request.form.get("dfrom", ""), request.form.get("dto", ""))
        if pfrom and pto:
            extra = ["--from", pfrom, "--to", pto]
    ok, msg = launch_task(task, extra)
    scope = f" [{extra[1]}→{extra[3]}]" if extra else ""
    log.info("Lancement manuel '%s'%s : %s", task, scope, msg)
    return redirect(url_for("dashboard"))


@app.route("/validation")
@require_auth
def validation():
    preset = request.args.get("preset", "")
    dfrom = request.args.get("dfrom", "")
    dto = request.args.get("dto", "")
    pfrom, pto, plabel = period_bounds(preset, dfrom, dto)
    conn = get_db()
    if pfrom and pto:
        # « Plan du week-end » : tout ce qui CHEVAUCHE la fenêtre et mérite d'être mis
        # en avant — les nouveaux retenus ET les déjà-publiés encore en cours (re-valo).
        clause, cp = overlap_clause(pfrom, pto)
        events = conn.execute(
            f"SELECT * FROM events_raw WHERE {clause} AND duplicate_of IS NULL AND ("
            "  (statut='evaluated' AND llm_score>=7) "
            "  OR statut IN ('published_cs','published_sub')) "
            "ORDER BY date_event_start ASC, llm_score DESC", cp).fetchall()
    else:
        events = conn.execute(
            "SELECT * FROM events_raw WHERE statut='evaluated' AND llm_score>=7 "
            "ORDER BY llm_score DESC, scrape_date DESC").fetchall()
    conn.close()
    events = annotate_period([dict(e) for e in events], pfrom, pto)
    return render_template(
        "index.html", events=events, alert=friendly_alert(),
        preset=preset, dfrom=dfrom, dto=dto, plabel=plabel,
        presets=PERIOD_PRESETS, has_period=bool(pfrom and pto))


@app.route("/preview/<int:event_id>")
@require_auth
def preview(event_id: int):
    conn = get_db()
    ev = conn.execute("SELECT * FROM events_raw WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    if not ev:
        return "Événement introuvable", 404
    ev = dict(ev)
    ev["description_clean"] = clean_html(ev.get("description"))
    image = event_image(ev)
    is_radar = (ev.get("source_type") == "radar"
                or "(radar)" in (ev.get("source_name") or ""))
    image_host = urlparse(image).netloc if image else ""
    # Données enrichies (article rédigé + contexte sourcé), si l'agent a tourné.
    enriched = None
    if ev.get("enrich_data"):
        try:
            enriched = json.loads(ev["enrich_data"])
        except (ValueError, TypeError):
            enriched = None
    enrich_running = _running_state().get("enrich", False)
    # SEO/GEO/AEO : le JSON-LD Event est DÉTERMINISTE (construit depuis la base,
    # toujours affiché) ; les champs title/méta/réponse/FAQ sont générés à la
    # demande (bouton). cf. utils/seo.py + docs/AGENT_SEO_DASHBOARD_SPEC.md.
    from utils import seo as seo_mod
    jsonld = seo_mod.event_jsonld_str(ev)
    seo_faq = []
    if ev.get("seo_faq"):
        try:
            seo_faq = json.loads(ev["seo_faq"])
        except (ValueError, TypeError):
            seo_faq = []
    seo_tags = []
    if ev.get("seo_tags"):
        try:
            seo_tags = json.loads(ev["seo_tags"])
        except (ValueError, TypeError):
            seo_tags = []
    faq_jsonld = seo_mod.faq_jsonld_str(seo_faq)
    # Détail du score d'importance (critère par critère), si évalué.
    score_detail = None
    if ev.get("llm_score_detail"):
        try:
            score_detail = json.loads(ev["llm_score_detail"])
        except (ValueError, TypeError):
            score_detail = None
    # Dossier(s) de presse rattaché(s) à cet événement (matière primaire).
    press_kits = []
    try:
        conn2 = get_db()
        press_kits = [dict(r) for r in conn2.execute(
            "SELECT subject, sender, n_photos, "
            "       (LENGTH(COALESCE(pdf_text,'')) + LENGTH(COALESCE(body_text,''))) AS chars "
            "FROM press_kits WHERE matched_event_id = ?", (event_id,)).fetchall()]
        conn2.close()
    except sqlite3.OperationalError:
        press_kits = []
    return render_template("preview.html", e=ev, image=image,
                           image_host=image_host, is_radar=is_radar,
                           enriched=enriched, enrich_running=enrich_running,
                           press_kits=press_kits, score_detail=score_detail,
                           jsonld=jsonld, seo_faq=seo_faq, seo_tags=seo_tags,
                           faq_jsonld=faq_jsonld)


@app.route("/enrich/<int:event_id>", methods=["POST"])
@require_auth
def enrich_one(event_id: int):
    """Lance l'agent d'enrichissement sur UN événement (non bloquant, suivi via run_state)."""
    ok, msg = launch_task("enrich", [str(event_id)])
    if ok:
        flash("✍️ Enrichissement lancé — la recherche web + rédaction prend ~40 à 90 s. "
              "La page se rafraîchit toute seule.", "ok")
    else:
        flash(f"⚠️ Enrichissement non lancé : {msg}.", "err")
    return redirect(url_for("preview", event_id=event_id))


@app.route("/seo/<int:event_id>", methods=["POST"])
@require_auth
def seo_optimize(event_id: int):
    """Génère les champs SEO/AEO (title, méta, réponse directe, FAQ) via LLM pour
    UN événement phare. Le JSON-LD, lui, est déterministe (affiché sans ce bouton).
    Réservé aux événements importants — coût maîtrisé. cf. utils/seo.py."""
    import anthropic
    from utils import seo as seo_mod
    conn = get_db()
    row = conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return "Événement introuvable", 404
    ev = dict(row)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        conn.close()
        flash("⚠️ Clé API absente — SEO non généré.", "err")
        return redirect(url_for("preview", event_id=event_id))
    model = (os.getenv("ANTHROPIC_MODEL_SEO") or os.getenv("ANTHROPIC_MODEL_VISUALS")
             or "claude-haiku-4-5")
    try:
        client = anthropic.Anthropic(api_key=api_key)
        result = seo_mod.optimize_seo(ev, client, model)
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        usage.note_api_error(exc)
        conn.close()
        flash("⚠️ Appel API échoué (crédit/quota ?) — voir le bandeau d'alerte.", "err")
        return redirect(url_for("preview", event_id=event_id))
    if not result:
        conn.close()
        flash("⚠️ Réponse illisible du modèle — réessaie.", "err")
        return redirect(url_for("preview", event_id=event_id))
    conn.execute(
        "UPDATE events_raw SET seo_title=?, seo_meta=?, seo_answer=?, seo_faq=?, "
        "seo_keyphrase=?, seo_slug=?, seo_tags=?, seo_model=?, seo_at=datetime('now') "
        "WHERE id=?",
        (result["seo_title"], result["seo_meta"], result["seo_answer"],
         json.dumps(result["seo_faq"], ensure_ascii=False),
         result["seo_keyphrase"], result["seo_slug"],
         json.dumps(result["seo_tags"], ensure_ascii=False), model, event_id))
    conn.commit()
    conn.close()
    flash("✨ SEO généré : title, méta, réponse directe et FAQ ci-dessous.", "ok")
    return redirect(url_for("preview", event_id=event_id) + "#seo")


# Champs qu'on autorise à compléter/corriger À LA MAIN depuis l'aperçu (liste blanche
# stricte : les clés viennent d'ici, jamais de l'utilisateur → pas d'injection SQL).
_MANUAL_FIELDS = ("date_event_start", "date_event_end", "lieu", "ville",
                  "territoire", "llm_categorie")


@app.route("/complete/<int:event_id>", methods=["POST"])
@require_auth
def complete_event(event_id: int):
    """Saisie MANUELLE des champs manquants (date, lieu, ville…) — sans API. Sert à
    compléter à la main les événements que la recherche web n'a pas résolus, et permet
    à une routine Claude-dans-Chrome de piloter ce même formulaire. On ne touche qu'aux
    champs réellement fournis (on n'efface rien par mégarde)."""
    updates = {}
    for k in _MANUAL_FIELDS:
        v = (request.form.get(k) or "").strip()
        if v:
            updates[k] = v
    if updates.get("date_event_start") and not updates.get("date_event_end"):
        updates["date_event_end"] = updates["date_event_start"]  # 1 jour → début = fin
    if updates:
        if "date_event_start" in updates:
            updates["date_source"] = "manuel"
        conn = get_db()
        sets = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE events_raw SET {sets} WHERE id=?",
                     (*updates.values(), event_id))
        conn.commit()
        conn.close()
        flash("💾 Champs complétés à la main : " + ", ".join(updates) + ".", "ok")
    else:
        flash("Rien à enregistrer (aucun champ rempli).", "err")
    return redirect(request.form.get("next") or url_for("preview", event_id=event_id))


@app.route("/site-dedie")
@require_auth
def site_dedie():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM events_raw WHERE statut = 'published_sub' "
        "ORDER BY llm_score DESC, scrape_date DESC"
    ).fetchall()
    conn.close()
    events = []
    for r in rows:
        e = dict(r)
        e["_img"] = event_image(e)
        e["_excerpt"] = clean_html(e.get("description"))[:180]
        events.append(e)
    return render_template("site_dedie.html", events=events)


@app.route("/events")
@require_auth
def events():
    statut = request.args.get("statut", "")
    terr = request.args.get("territoire", "")
    q = request.args.get("q", "").strip()
    src = request.args.get("src", "")  # "" tous · radar · newsletter · officiel
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    img = request.args.get("img", "")  # "" toutes · "1" avec photo · "0" sans
    sort = request.args.get("sort", "")  # "" défaut · "score" = meilleur score en haut
    preset = request.args.get("preset", "")
    dfrom = request.args.get("dfrom", "")
    dto = request.args.get("dto", "")
    dated = request.args.get("dated", "")  # "" tous · "undated" = date à confirmer
    pfrom, pto, plabel = period_bounds(preset, dfrom, dto)

    base_where, base_params = [], []
    # Statut : défaut = ACTIFS (tout sauf rejeté/fusionné, le bruit) ; « all » = tout ;
    # sinon un statut précis. Permet « tous sauf rejeté » en un clic.
    if statut in ("", "actifs"):
        base_where.append("statut NOT IN ('rejected', 'merged')")
    elif statut != "all":
        base_where.append("statut = ?"); base_params.append(statut)
    if terr:
        base_where.append("territoire = ?"); base_params.append(terr)
    if q:
        base_where.append("title LIKE ?"); base_params.append(f"%{q}%")
    # Type de source : radar (presse, à confirmer) · newsletter (Gmail) · officiel
    # (flux de lieux/institutions, territoire fiable). Aide à isoler le bruit radar.
    if src == "radar":
        base_where.append("(source_type = 'radar' OR source_name LIKE '%(radar)%')")
    elif src == "sans_radar":
        base_where.append("source_type != 'radar' AND COALESCE(source_name,'') NOT LIKE '%(radar)%'")
    elif src == "newsletter":
        base_where.append("url_source LIKE 'gmail:%'")
    elif src == "officiel":
        base_where.append("source_type != 'radar' AND COALESCE(source_name,'') NOT LIKE '%(radar)%' "
                          "AND COALESCE(url_source,'') NOT LIKE 'gmail:%'")

    where, params = list(base_where), list(base_params)
    if img == "1":
        where.append("url_image IS NOT NULL AND url_image != ''")
    elif img == "0":
        where.append("(url_image IS NULL OR url_image = '')")
    # Filtre période : chevauchement de la fenêtre, OU bac « date à confirmer ».
    if dated == "undated":
        where.append("COALESCE(date_event_start,'')='' AND COALESCE(date_event_end,'')=''")
    elif pfrom and pto:
        clause, cparams = overlap_clause(pfrom, pto)
        where.append(clause); params.extend(cparams)
    wsql = ("WHERE " + " AND ".join(where)) if where else ""
    base_wsql = ("WHERE " + " AND ".join(base_where)) if base_where else ""

    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) n FROM events_raw {wsql}", params).fetchone()["n"]
    imgrow = conn.execute(
        "SELECT SUM(CASE WHEN url_image IS NOT NULL AND url_image != '' THEN 1 ELSE 0 END) wi, "
        f"COUNT(*) t FROM events_raw {base_wsql}", base_params).fetchone()
    with_img = imgrow["wi"] or 0
    without_img = (imgrow["t"] or 0) - with_img
    # Tri. Défaut = QUALITÉ : le haut de liste est publiable tel quel (photo +
    # score élevé + article prêt), et ça se dégrade en descendant. « date » et
    # « score » restent disponibles explicitement.
    has_photo = "(CASE WHEN url_image IS NOT NULL AND url_image != '' THEN 1 ELSE 0 END)"
    is_ready = "(CASE WHEN enrich_status = 'enriched' THEN 1 ELSE 0 END)"
    if sort == "score":
        order = "COALESCE(llm_score,-1) DESC, scrape_date DESC, id DESC"
    elif sort == "date":
        order = ("date_event_start ASC, id DESC" if pfrom and pto and dated != "undated"
                 else "scrape_date DESC, id DESC")
    else:  # qualité (défaut)
        order = (f"{has_photo} DESC, COALESCE(llm_score,-1) DESC, {is_ready} DESC, "
                 "COALESCE(NULLIF(date_event_start,''),'9999-12-31') ASC, id DESC")
    rows = conn.execute(
        f"SELECT * FROM events_raw {wsql} ORDER BY {order} LIMIT ? OFFSET ?",
        params + [PAGE_SIZE, (page - 1) * PAGE_SIZE]).fetchall()
    statut_counts = {r["statut"]: r["n"] for r in conn.execute(
        "SELECT statut, COUNT(*) n FROM events_raw GROUP BY statut")}
    total_all = sum(statut_counts.values())
    actifs_count = total_all - statut_counts.get("rejected", 0) - statut_counts.get("merged", 0)
    undated_count = conn.execute(
        "SELECT COUNT(*) n FROM events_raw WHERE COALESCE(date_event_start,'')='' "
        "AND COALESCE(date_event_end,'')='' AND statut != 'merged'").fetchone()["n"]
    src_counts = conn.execute(
        "SELECT "
        "SUM(CASE WHEN source_type='radar' OR source_name LIKE '%(radar)%' THEN 1 ELSE 0 END) radar, "
        "SUM(CASE WHEN url_source LIKE 'gmail:%' THEN 1 ELSE 0 END) newsletter, "
        "SUM(CASE WHEN source_type!='radar' AND COALESCE(source_name,'') NOT LIKE '%(radar)%' "
        "     AND COALESCE(url_source,'') NOT LIKE 'gmail:%' THEN 1 ELSE 0 END) officiel "
        "FROM events_raw").fetchone()
    conn.close()

    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return render_template(
        "events.html", events=annotate_period([dict(r) for r in rows], pfrom, pto),
        statut=statut, territoire=terr, q=q, img=img, src=src, page=page, pages=pages, total=total,
        with_img=with_img, without_img=without_img, src_counts=src_counts,
        total_all=total_all, actifs_count=actifs_count,
        preset=preset, dfrom=dfrom, dto=dto, dated=dated, plabel=plabel, sort=sort,
        presets=PERIOD_PRESETS, undated_count=undated_count,
        today=date.today().isoformat(),
        territories=TERRITORIES, status_labels=STATUS_LABELS,
        statut_counts=statut_counts, alert=friendly_alert())


# --------------------------------------------------------------------------- #
# PORTE QUALITÉ — liste « À compléter » + complétion manuelle (dashboard/Slack)
# Un événement retenu ne part sur Agenda Sabauda que COMPLET (utils/completeness).
# Ici : la file des incomplets, l'édition à la main des champs manquants, et un
# point d'entrée Slack pour que Franck renvoie une info qu'il a trouvée lui-même.
# --------------------------------------------------------------------------- #

# Champs éditables à la main (clé DB → libellé). Sous-ensemble des obligatoires +
# la date de fin (facultative mais utile). L'image se colle par URL.
_COMPLETE_FIELDS = [
    ("date_event_start", "Date de début (AAAA-MM-JJ)"),
    ("date_event_end",   "Date de fin (AAAA-MM-JJ, facultatif)"),
    ("lieu",             "Lieu"),
    ("ville",            "Ville"),
    ("territoire",       "Territoire"),
    ("llm_categorie",    "Catégorie"),
    ("url_image",        "URL de l'image"),
]
# Clés acceptées via Slack (avec alias courts) → colonne DB.
_SLACK_KEYS = {
    "lieu": "lieu", "ville": "ville", "territoire": "territoire",
    "categorie": "llm_categorie", "catégorie": "llm_categorie",
    "image": "url_image", "url_image": "url_image",
    "date": "date_event_start", "date_start": "date_event_start",
    "date_debut": "date_event_start", "date_end": "date_event_end",
    "date_fin": "date_event_end",
}


@app.route("/a-completer")
@require_auth
def a_completer():
    """File des événements RETENUS incomplets (la porte qualité les retient ici).

    Filtrable par PÉRIODE : pour se concentrer (et pour lancer l'auto-complétion)
    sur une fenêtre au lieu de tout traiter."""
    today = date.today().isoformat()
    preset = request.args.get("preset", "")
    dfrom = request.args.get("dfrom", "")
    dto = request.args.get("dto", "")
    pfrom, pto, plabel = period_bounds(preset, dfrom, dto)
    clause, cp = incomplete_clause(today)
    sql = f"SELECT * FROM events_raw WHERE {clause}"
    params = list(cp)
    if pfrom and pto:
        # Datés chevauchant la fenêtre (les non-datés n'ont pas de période).
        oc, op = overlap_clause(pfrom, pto)
        sql += f" AND {oc}"
        params += op
    sql += (" ORDER BY COALESCE(llm_score,0) DESC, "
            "COALESCE(NULLIF(date_event_start,''),'9999-12-31') ASC")
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    events = []
    for r in rows:
        e = dict(r)
        e["_missing"] = comp.missing_labels(e)
        e["_recurring_note"] = comp.recurring_note(e)
        e["_img"] = event_image(e)
        events.append(e)
    return render_template(
        "a_completer.html", events=events, fields=_COMPLETE_FIELDS,
        territories=TERRITORIES, today=today, active="tocomplete",
        preset=preset, dfrom=dfrom, dto=dto, plabel=plabel,
        presets=PERIOD_PRESETS, alert=friendly_alert())


def _apply_completion(conn, event_id: int, values: dict) -> tuple[bool, list[str]]:
    """Écrit les champs fournis (non vides) et renvoie (complet?, manques restants)."""
    clean = {k: v.strip() for k, v in values.items()
             if k in dict(_COMPLETE_FIELDS) and (v or "").strip()}
    if clean:
        sets = ", ".join(f"{k}=?" for k in clean)
        conn.execute(f"UPDATE events_raw SET {sets} WHERE id=?",
                     [*clean.values(), event_id])
        conn.commit()
    row = conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone()
    ev = dict(row) if row else {}
    return comp.is_complete(ev), comp.missing_labels(ev)


def _autopush_if_ready(conn, event_id: int) -> tuple[bool, int | None]:
    """Complétion manuelle → PUSH IMMÉDIAT : si l'événement est complet + à venir +
    pas encore sur l'agenda, on le pousse tout de suite en brouillon Agenda Sabauda
    (au lieu d'attendre le prochain passage du cron). Renvoie (poussé?, wp_id|None).
    Ne pousse jamais un événement passé (cf. porte qualité)."""
    row = conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone()
    if not row:
        return False, None
    ev = dict(row)
    if not comp.is_complete(ev) or ev.get("wp_post_id_as"):
        return False, None
    end = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()
    if not end or end < date.today().isoformat():
        return False, None
    wp_id = publish_to_as(ev)
    if wp_id:
        conn.execute("UPDATE events_raw SET wp_post_id_as=?, "
                     "published_as_date=datetime('now') WHERE id=?", (wp_id, event_id))
        conn.commit()
        return True, wp_id
    return False, None


@app.route("/complete/<int:event_id>", methods=["POST"])
@require_auth
def complete_event_manual(event_id: int):
    """Complétion À LA MAIN depuis la liste « À compléter »."""
    conn = get_db()
    row = conn.execute("SELECT id FROM events_raw WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return "Événement introuvable", 404
    values = {k: request.form.get(k, "") for k, _ in _COMPLETE_FIELDS}
    complete, missing = _apply_completion(conn, event_id, values)
    pushed, wp_id = _autopush_if_ready(conn, event_id) if complete else (False, None)
    conn.close()
    if pushed:
        flash(f"✅ Complété et poussé en brouillon Agenda Sabauda (id {wp_id}).", "ok")
    elif complete:
        flash("✅ Complété. Non poussé (événement passé ou déjà sur l'agenda) — "
              "l'auto-complétion le gérera si besoin.", "ok")
    else:
        flash(f"💾 Enregistré. Il manque encore : {', '.join(missing)}.", "ok")
    return redirect(url_for("a_completer") + f"#e{event_id}")


def _parse_slack_kv(text: str) -> tuple[int | None, dict]:
    """Parse « [complete] <id> lieu=… ville=… » → (id, {colonne: valeur})."""
    text = (text or "").strip()
    if text.lower().startswith("complete"):
        text = text[len("complete"):].strip()
    m = re.match(r"(\d+)\s*(.*)", text, re.S)
    if not m:
        return None, {}
    event_id = int(m.group(1))
    rest = m.group(2)
    values: dict = {}
    # key=value, la valeur court jusqu'au prochain « mot= » ou la fin.
    for km in re.finditer(r"(\w+)=(.*?)(?=\s+\w+=|$)", rest, re.S):
        key = _SLACK_KEYS.get(km.group(1).lower())
        if key:
            values[key] = km.group(2).strip()
    return event_id, values


def _verify_slack(req) -> bool:
    """Vérifie la signature Slack (HMAC v0). Refuse si le secret n'est pas configuré."""
    secret = (os.getenv("SLACK_SIGNING_SECRET") or "").strip()
    if not secret:
        return False
    ts = req.headers.get("X-Slack-Request-Timestamp", "")
    sig = req.headers.get("X-Slack-Signature", "")
    if not ts or not sig:
        return False
    try:
        if abs(datetime.now().timestamp() - int(ts)) > 300:
            return False  # anti-rejeu (> 5 min)
    except ValueError:
        return False
    base = f"v0:{ts}:{req.get_data(as_text=True)}".encode("utf-8")
    mine = "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mine, sig)


@app.route("/slack/complete", methods=["POST"])
def slack_complete():
    """Commande Slack « /agenda complete <id> lieu=… » — Franck renvoie une info.

    PAS de session backoffice : l'authentification est la SIGNATURE Slack (HMAC avec
    SLACK_SIGNING_SECRET). Sans secret configuré, l'endpoint refuse tout."""
    if not _verify_slack(request):
        return ("Signature Slack invalide (ou SLACK_SIGNING_SECRET absent).", 401)
    event_id, values = _parse_slack_kv(request.form.get("text", ""))
    if not event_id:
        return {"response_type": "ephemeral",
                "text": "Usage : `/agenda complete <id> lieu=… ville=… url_image=…`"}
    conn = get_db()
    row = conn.execute("SELECT id FROM events_raw WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return {"response_type": "ephemeral", "text": f"Événement {event_id} introuvable."}
    if not values:
        conn.close()
        return {"response_type": "ephemeral",
                "text": "Aucun champ reconnu. Ex : `lieu=Théâtre… ville=… url_image=…`"}
    complete, missing = _apply_completion(conn, event_id, values)
    pushed, wp_id = _autopush_if_ready(conn, event_id) if complete else (False, None)
    conn.close()
    champs = ", ".join(values.keys())
    if pushed:
        txt = (f"✅ Événement {event_id} complété ({champs}) et POUSSÉ en brouillon "
               f"Agenda Sabauda (id {wp_id}).")
    elif complete:
        txt = (f"✅ Événement {event_id} complété ({champs}). Non poussé "
               "(passé ou déjà sur l'agenda).")
    else:
        txt = (f"💾 Événement {event_id} mis à jour ({champs}). "
               f"Il manque encore : {', '.join(missing)}.")
    return {"response_type": "ephemeral", "text": txt}


@app.route("/action/<int:event_id>/<action>", methods=["POST"])
@require_auth
def action(event_id: int, action: str):
    conn = get_db()
    event = conn.execute(
        "SELECT * FROM events_raw WHERE id = ?", (event_id,)
    ).fetchone()
    if not event:
        conn.close()
        return "Événement introuvable", 404

    title = (event["title"] or "")[:70]
    if action == "publish_cs":
        existed = event["wp_post_id_cs"]
        wp_id = publish_to_cs(dict(event))
        if wp_id:
            conn.execute("""
            UPDATE events_raw SET statut='published_cs',
            published_cs_date=datetime('now'), wp_post_id_cs=? WHERE id=?
            """, (wp_id, event_id))
            conn.commit()
            log.info("Publié CS : event_id=%d wp_id=%d", event_id, wp_id)
            verbe = "mis à jour" if existed and wp_id == existed else "créé"
            flash(f"✅ « {title} » → brouillon WordPress {verbe} (id {wp_id}).", "ok")
        else:
            flash(f"❌ Échec WordPress pour « {title} » — vérifie WP_URL / identifiants (voir logs).", "err")
    elif action == "subdomain":
        # CLASSER uniquement (pas de publication) — miroir des pastilles de statut.
        conn.execute(
            "UPDATE events_raw SET statut='published_sub' WHERE id=?",
            (event_id,)
        )
        conn.commit()
        flash(f"📋 « {title} » classé pour Agenda Sabauda.", "ok")
    elif action == "publish_as":
        # PUBLIER vers agendasabauda.eu (événement TEC) — pendant de « Publier CS ».
        existed = event["wp_post_id_as"]
        wp_id = publish_to_as(dict(event))
        if wp_id:
            conn.execute("""
            UPDATE events_raw SET statut='published_sub',
            published_as_date=datetime('now'), wp_post_id_as=? WHERE id=?
            """, (wp_id, event_id))
            conn.commit()
            log.info("Publié Agenda Sabauda : event_id=%d wp_id=%d", event_id, wp_id)
            verbe = "mis à jour" if existed and wp_id == existed else "créé"
            flash(f"✅ « {title} » → brouillon Agenda Sabauda {verbe} (id {wp_id}).", "ok")
        else:
            flash(f"❌ Échec Agenda Sabauda pour « {title} » — vérifie "
                  f"WP_AS_URL / identifiants (voir logs).", "err")
    elif action == "reject":
        conn.execute(
            "UPDATE events_raw SET statut='rejected' WHERE id=?",
            (event_id,)
        )
        conn.commit()
        flash(f"❌ « {title} » rejeté.", "ok")
    elif action == "recurring":
        # Événement récurrent / permanent (sans date unique) : on remplace la date
        # par une note renvoyant à la source. Il quitte « À compléter » (la date
        # n'est plus requise). Note personnalisable via le champ `note`.
        note = (request.form.get("note", "") or "").strip()
        conn.execute("UPDATE events_raw SET recurring=1, recurring_note=? WHERE id=?",
                     (note or None, event_id))
        conn.commit()
        flash(f"🔁 « {title} » marqué récurrent — les dates renvoient à la source.", "ok")
    elif action == "recurring_off":
        conn.execute("UPDATE events_raw SET recurring=0, recurring_note=NULL WHERE id=?",
                     (event_id,))
        conn.commit()
        flash(f"↩️ « {title} » n'est plus récurrent.", "ok")

    conn.close()
    nxt = request.form.get("next", "")
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = url_for("validation")
    return redirect(nxt)


@app.route("/set-focal/<int:event_id>", methods=["POST"])
@require_auth
def set_focal(event_id: int):
    """Règle le CADRAGE de la vignette 4:3 : point focal (x,y ∈ [0,1]) + mode
    (auto/cover/letterbox). Sert quand le recadrage auto coupe mal (titre d'affiche
    rogné…). Si l'événement est déjà sur l'Agenda, on RE-POUSSE aussitôt pour que la
    correction soit visible tout de suite."""
    def _f(name, default):
        try:
            return min(max(float(request.form.get(name, "")), 0.0), 1.0)
        except (TypeError, ValueError):
            return default
    fx, fy = _f("focal_x", 0.5), _f("focal_y", 0.5)
    mode = (request.form.get("mode", "") or "").strip().lower()
    if mode not in ("", "cover", "letterbox"):
        mode = ""  # valeur inconnue → auto
    conn = get_db()
    row = conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return "Événement introuvable", 404
    conn.execute("UPDATE events_raw SET card_focal_x=?, card_focal_y=?, card_mode=? "
                 "WHERE id=?", (fx, fy, mode or None, event_id))
    conn.commit()
    ev = dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone())
    conn.close()
    log.info("Cadrage vignette id=%d : focal=(%.2f,%.2f) mode=%s", event_id, fx, fy,
             mode or "auto")
    label = {"": "auto", "cover": "recadrage", "letterbox": "affiche entière"}[mode]
    if ev.get("wp_post_id_as"):
        wp_id = publish_to_as(ev)
        if wp_id:
            flash(f"🖼 Cadrage enregistré ({label}) et vignette régénérée sur l'Agenda "
                  f"(WP #{wp_id}).", "ok")
        else:
            flash(f"🖼 Cadrage enregistré ({label}), mais la re-publication a échoué "
                  "(voir logs).", "err")
    else:
        flash(f"🖼 Cadrage enregistré ({label}) — s'appliquera à la publication Agenda.",
              "ok")
    return redirect(url_for("preview", event_id=event_id) + f"#cadrage")


# Statuts assignables en un clic depuis la liste (triage rapide, SANS effet de bord :
# ni WordPress ni LLM — juste l'étiquette). Le push WordPress reste l'action dédiée.
_STATUS_PICK = {"evaluated", "published_cs", "published_sub", "rejected"}


@app.route("/set-score/<int:event_id>", methods=["POST"])
@require_auth
def set_score(event_id: int):
    """Ajuste le score À LA MAIN + MÉMORISE la correction (l'évaluateur apprend).
    On écrit le nouveau score dans llm_score (utilisé partout) ET user_score, et on
    journalise (titre + traits + ancien→nouveau) dans utils/score_memory."""
    try:
        new = max(0, min(10, int(request.form.get("score", ""))))
    except (ValueError, TypeError):
        flash("⚠️ Score invalide (0 à 10).", "err")
        return redirect(request.form.get("next", "") or url_for("a_completer"))
    conn = get_db()
    row = conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return "Événement introuvable", 404
    ev = dict(row)
    old = ev.get("llm_score")
    conn.execute("UPDATE events_raw SET llm_score=?, user_score=?, "
                 "score_overridden_at=datetime('now') WHERE id=?", (new, new, event_id))
    conn.commit()
    conn.close()
    from utils import score_memory
    score_memory.record(ev, old, new)
    log.info("Score ajusté id=%d : %s → %d (mémorisé)", event_id, old, new)
    flash(f"🧠 Score de « {(ev.get('title') or '')[:50]} » : {old} → {new}. "
          "Mémorisé — l'évaluateur s'alignera sur ton goût.", "ok")
    nxt = request.form.get("next", "")
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = url_for("a_completer")
    return redirect(nxt if "#" in nxt else f"{nxt}#e{event_id}")


@app.route("/set-status/<int:event_id>/<statut>", methods=["POST"])
@require_auth
def set_status(event_id: int, statut: str):
    if statut not in _STATUS_PICK:
        return "Statut invalide", 400
    conn = get_db()
    conn.execute("UPDATE events_raw SET statut=? WHERE id=?", (statut, event_id))
    conn.commit()
    conn.close()
    nxt = request.form.get("next", "")
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = url_for("events")
    # Ancre : on revient sur la même ligne (pas de saut en haut de page).
    if "#" not in nxt:
        nxt = f"{nxt}#e{event_id}"
    return redirect(nxt)


if __name__ == "__main__":
    app.run(debug=False, port=5001)
