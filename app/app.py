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

from flask import Flask, flash, redirect, render_template, request, session, url_for

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import re

from scripts.publisher import publish_to_cs
from scripts.scraper_events import load_sources, init_db
from utils.logger import get_logger
from utils import usage
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
log = get_logger("backoffice")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
NEWSLETTERS_FILE = ROOT / "config" / "newsletters.txt"

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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
    pending = validate = 0
    try:
        conn = get_db()
        pending = conn.execute(
            "SELECT COUNT(*) n FROM events_raw WHERE statut='pending'").fetchone()["n"]
        validate = conn.execute(
            "SELECT COUNT(*) n FROM events_raw WHERE statut='evaluated' AND llm_score>=7"
        ).fetchone()["n"]
        conn.close()
    except Exception:
        pass
    return {"nav": {"pending": pending, "validate": validate},
            "nav_alert": friendly_alert(),
            # Base WordPress (lien direct vers un brouillon créé : wp_post_id_cs).
            "wp_base": (os.getenv("WP_URL", "") or "").rstrip("/")}


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
    conn.close()
    metrics = {
        "future": future, "with_photo": with_photo,
        "photo_pct": round(with_photo / future * 100) if future else 0,
        "route_cs": route_cs, "route_as": route_as,
        "past_active": past_active, "queue_cs": queue_cs, "thr": thr,
    }
    return render_template(
        "pilotage.html", m=metrics, terr_future=terr_future, home=home,
        territories=TERRITORIES, today=today, alert=friendly_alert())


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
        conn.execute(
            "UPDATE events_raw SET statut='published_sub' WHERE id=?",
            (event_id,)
        )
        conn.commit()
        flash(f"📋 « {title} » classé pour Agenda Sabauda.", "ok")
    elif action == "reject":
        conn.execute(
            "UPDATE events_raw SET statut='rejected' WHERE id=?",
            (event_id,)
        )
        conn.commit()
        flash(f"❌ « {title} » rejeté.", "ok")

    conn.close()
    nxt = request.form.get("next", "")
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = url_for("validation")
    return redirect(nxt)


# Statuts assignables en un clic depuis la liste (triage rapide, SANS effet de bord :
# ni WordPress ni LLM — juste l'étiquette). Le push WordPress reste l'action dédiée.
_STATUS_PICK = {"evaluated", "published_cs", "published_sub", "rejected"}


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
