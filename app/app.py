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

from flask import (Flask, Response, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from markupsafe import Markup
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import re

from scripts.publisher import publish_to_cs, build_post
from scripts.publisher_as import publish_to_as
from scripts.scraper_events import load_sources, init_db
from utils.logger import get_logger
from utils import usage
from utils import completeness as comp
from utils import triage as triage_mod
from utils import slack
from utils import organizers
from utils import semaine as semaine_mod
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

# État d'UI léger (préférences non critiques : ex. « pastille À valider vue jusqu'à
# l'id N »). Fichier JSON dans data/ (gitignoré, propre au VPS).
UI_STATE_FILE = DB_PATH.parent / "ui_state.json"


def load_ui_state() -> dict:
    try:
        return json.loads(UI_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_ui_state(state: dict) -> None:
    try:
        UI_STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass
_conn = sqlite3.connect(DB_PATH)
init_db(_conn)
# Colonnes de traduction (ajoutées par scripts.translate_events) : garanties ici pour que
# les requêtes de l'app (ex. exclure les traductions de « À compléter ») ne plantent pas
# sur une base où la traduction n'a jamais tourné.
for _col in ("translation_of", "translated_at", "translated_lang"):
    try:
        _conn.execute(f"ALTER TABLE events_raw ADD COLUMN {_col} TEXT")
    except sqlite3.OperationalError:
        pass
# Drapeau « lieux multiples » (festival itinérant / programme diffus) : relâche
# l'exigence lieu/ville de la porte qualité.
try:
    _conn.execute("ALTER TABLE events_raw ADD COLUMN multi_lieux INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass
# Drapeau « 🌟 vaut le détour » : événement phare autorisé à apparaître sur les comptes
# Instagram des AUTRES territoires (choix éditorial, cf. tableau Réseaux).
try:
    _conn.execute("ALTER TABLE events_raw ADD COLUMN worth_trip INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass
# Historique des publications Instagram (idempotence + statut visible dans /reseaux).
_conn.execute("""
    CREATE TABLE IF NOT EXISTS social_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        territoire_label TEXT NOT NULL,
        lang TEXT NOT NULL,
        kind TEXT NOT NULL,
        status TEXT NOT NULL,
        ig_media_id TEXT,
        error TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
""")
try:
    _conn.execute("ALTER TABLE social_posts ADD COLUMN platform TEXT DEFAULT 'instagram'")
except sqlite3.OperationalError:
    pass
# Publications Instagram PROGRAMMÉES (l'API Graph n'offre aucune programmation
# native pour un outil tiers) : Franck choisit un jour/heure, cette table garde
# l'intention, et scripts/ig_scheduler.py (cron séparé, toutes les 15 min) publie
# au bon moment via le MÊME chemin que la publication immédiate (_do_publish_instagram).
_conn.execute("""
    CREATE TABLE IF NOT EXISTS ig_scheduled_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        territoire_label TEXT NOT NULL,
        lang TEXT NOT NULL,
        kind TEXT NOT NULL,
        scheduled_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now')),
        published_at TEXT,
        error TEXT
    )
""")
# Légende Instagram réécrite par LLM (voix Enrico Nos Alpes + anti-signes-IA), mise en
# cache : générée à la demande (bouton, payant), jamais recalculée à chaque page vue.
for _col in ("social_caption_fr", "social_caption_it"):
    try:
        _conn.execute(f"ALTER TABLE events_raw ADD COLUMN {_col} TEXT")
    except sqlite3.OperationalError:
        pass
# Mémoire des handles Instagram d'organisateurs, confirmés une fois par Franck puis
# réutilisés silencieusement (mentions automatiques, cf. utils/organizers.py).
organizers.ensure_table(_conn)
_conn.commit()
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
        elif k in ("lieu", "ville"):
            # Multi-lieux : lieu/ville non requis (festival itinérant, programme diffus).
            parts.append(f"(COALESCE({k},'')='' AND COALESCE(multi_lieux,0)=0)")
        else:
            parts.append(f"COALESCE({k},'')=''")
    empties = " OR ".join(parts)
    clause = (
        "statut IN ('evaluated','published_cs','published_sub') AND duplicate_of IS NULL "
        # Les TRADUCTIONS sont des copies d'événements déjà publiés : on ne les complète
        # jamais à la main (leur « source » est un pseudo-lien translated:NNN). On complète
        # l'ORIGINAL, puis on retraduit. → hors file « À compléter ».
        "AND COALESCE(translation_of,0)=0 "
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
        # Pastille « À valider » (Cultura Sabauda). On/off : masquée tant que Franck ne
        # travaille pas CS. Sinon elle compte QUE les à-venir (les passés ne se valident plus).
        if load_ui_state().get("validate_badge_off"):
            validate = 0
        else:
            validate = conn.execute(
                "SELECT COUNT(*) n FROM events_raw WHERE statut='evaluated' AND llm_score>=7 "
                "AND COALESCE(NULLIF(date_event_end,''), date_event_start) >= ?",
                (date.today().isoformat(),)).fetchone()["n"]
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
    verifier = 0
    try:
        conn = get_db()
        _ensure_checks_table(conn)
        verifier = conn.execute(
            "SELECT COUNT(*) n FROM checks WHERE status='pending'").fetchone()["n"]
        conn.close()
    except Exception:
        pass
    audit = 0
    try:
        conn = get_db()
        _ensure_audit_flags_table(conn)
        audit = conn.execute(
            "SELECT COUNT(*) n FROM image_audit_flags WHERE resolved_at IS NULL").fetchone()["n"]
        conn.close()
    except Exception:
        pass
    return {"nav": {"pending": pending, "validate": validate,
                    "tocomplete": tocomplete, "regie": regie, "verifier": verifier,
                    "audit": audit},
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
    """Lit config/newsletters.txt : nom;domaine;territoire;statut[;url_inscription]."""
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
                         "territoire": parts[2], "statut": parts[3],
                         "url": parts[4] if len(parts) >= 5 else ""})
    return rows


def save_newsletter_statut(domaine: str, statut: str) -> bool:
    """Réécrit config/newsletters.txt en changeant le statut de la ligne dont le domaine
    correspond (préserve commentaires/ordre). Sert au bouton on/off du tableau de bord."""
    if statut not in ("actif", "attente", "candidat", "inactif") or not domaine:
        return False
    if not NEWSLETTERS_FILE.exists():
        return False
    out, changed = [], False
    for line in NEWSLETTERS_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and ";" in s:
            parts = [p.strip() for p in s.split(";")]
            if len(parts) >= 4 and parts[1] == domaine and not changed:
                parts[3] = statut
                out.append(";".join(parts))
                changed = True
                continue
        out.append(line)
    if changed:
        NEWSLETTERS_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


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


@app.route("/newsletters/toggle", methods=["POST"])
@require_auth
def newsletters_toggle():
    """Bouton on/off du tableau de bord : bascule le statut d'une newsletter et enregistre.
    candidat → attente (inscrit, à vérifier) ; attente ↔ actif (à vérifier / vérifié)."""
    save_newsletter_statut(request.form.get("domaine", ""), request.form.get("statut", ""))
    return redirect(url_for("dashboard") + "#sources")


@app.route("/reglages", methods=["GET", "POST"])
@require_auth
def reglages():
    """Réglages de coût du pipeline : profil IA (éco/qualité) + mode d'enrichissement
    (off/court/long), avec les conséquences expliquées. Lu par l'évaluateur/enrichissement."""
    from utils import settings as psettings
    if request.method == "POST":
        psettings.save({"ai_profile": request.form.get("ai_profile", ""),
                        "enrich_mode": request.form.get("enrich_mode", ""),
                        "social_caption_auto": bool(request.form.get("social_caption_auto")),
                        "social_caption_limit": request.form.get("social_caption_limit", 3)})
        flash("Réglages enregistrés — appliqués au prochain passage du pipeline (cron ou lancement manuel).", "ok")
        return redirect(url_for("reglages"))
    return render_template("reglages.html", active="reglages",
                           st=psettings.load(), model=psettings.model())


def _parse_cron_log(path: Path, max_bytes: int = 250_000) -> dict | None:
    """Extrait le DERNIER passage du pipeline quotidien depuis logs/cron_pipeline.log.
    Renvoie {started, ended, steps:[{name, ok}], enrich_seen, translate_seen} ou None."""
    try:
        text = path.read_text(errors="replace")[-max_bytes:]
    except OSError:
        return None
    starts = [m.start() for m in re.finditer(r"=== PIPELINE QUOTIDIEN", text)]
    if not starts:
        return None
    block = text[starts[-1]:]
    m0 = re.search(r"\[([\d\-:\s]+)\][^\n]*PIPELINE QUOTIDIEN", block)
    started = (m0.group(1).strip() if m0 else "")
    steps: list[dict] = []
    for line in block.splitlines():
        m = re.search(r"\]\s*(✓|✗)\s+(.+?)(\s*\(échec.*)?$", line)
        if m:
            steps.append({"name": m.group(2).strip(), "ok": m.group(1) == "✓"})
    names = " ".join(s["name"] for s in steps)
    return {"started": started, "ended": "FIN PIPELINE" in block, "steps": steps,
            "enrich_seen": "enrichissement" in names, "translate_seen": "traduction" in names}


# Planification déclarée (miroir lisible de deploy/CRONTAB_SETUP.txt — pour affichage).
_PIPELINE_SCHEDULE = [
    ("Pipeline complet", "tous les jours 6h05", "collecte → éval → visuels → enrichissement (rédaction FR) → autocomplete (publication) → traduction IT"),
    ("Autocomplete", "tous les jours 6h40", "repasse compléter/pousser les fiches complètes"),
    ("Newsletter (brouillon)", "lundi 7h00", "brouillon Brevo de la semaine"),
    ("Audit visuel", "dimanche 5h00", "planches contact des images"),
    ("Instagram", "toutes les 15 min", "publie les posts programmés"),
]


@app.route("/pipeline")
@require_auth
def pipeline_view():
    """Visibilité du pipeline AUTOMATIQUE (cron) : dernier passage, étapes, planning.
    La création d'article (enrichissement) et la traduction IT tournent en cron —
    plus besoin de bouton. On peut couper la dépense via /reglages (enrich_mode)."""
    from utils import settings as psettings
    run = _parse_cron_log(ROOT / "logs" / "cron_pipeline.log")
    return render_template("pipeline.html", active="pipeline", run=run,
                           schedule=_PIPELINE_SCHEDULE, st=psettings.load())


@app.route("/voix", methods=["GET", "POST"])
@require_auth
def voix_view():
    """Voix éditoriale ACTIVE (le ton appliqué à la rédaction). Montre qu'elle est chargée
    et pas cassée, depuis quelle source, et permet de CHOISIR la voix parmi celles de
    l'atelier Obsidian (dossier VOIX_DIR / docs/voix)."""
    from utils import voix as voixmod
    from utils import settings as psettings
    if request.method == "POST":
        # Deux actions : "adopt" importe les couches forcées par l'env dans voix_layers ;
        # "save" (défaut) enregistre les couches cochées, ordonnées par priorité.
        action = request.form.get("action", "save")
        if action == "adopt":
            names = voixmod.env_layer_names()
            psettings.save({"voix_layers": names})
            flash("Couches Obsidian adoptées — retire OBSIDIAN_VOIX_PATH du .env pour piloter ici.", "ok")
        else:
            n = int(request.form.get("n", "0") or 0)
            picked = []
            for i in range(n):
                if request.form.get(f"sel_{i}"):
                    name = request.form.get(f"name_{i}", "")
                    try:
                        order = int(request.form.get(f"ord_{i}", "0") or 0)
                    except (TypeError, ValueError):
                        order = 0
                    if name:
                        picked.append((order, i, name))
            picked.sort(key=lambda t: (t[0], t[1]))
            psettings.save({"voix_layers": [p[2] for p in picked]})
            flash("Couches de voix enregistrées — appliquées au prochain run.", "ok")
        return redirect(url_for("voix_view"))
    return render_template("voix.html", active="voix", st=voixmod.voix_status())


@app.route("/personas")
@require_auth
def personas_view():
    """Panel de personas LECTEURS (docs/personas/ ou dossier PERSONAS_DIR). Montre qui
    relit les articles développés après rédaction, pour que Franck puisse les relire et
    les éditer. Lecture seule : on édite les personas dans le dépôt / Obsidian."""
    from utils import personas as personas_mod
    return render_template("personas.html", active="personas",
                           st=personas_mod.personas_status())


def _ensure_checks_table(conn):
    """Table des points « à vérifier » (garde-fou humain sur les faits). Idempotent.
    Même DDL que scripts/enrich.py._ensure_checks_table."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now')),
        resolved_at TEXT
    )""")
    conn.commit()


def _ensure_audit_flags_table(conn):
    """Verdicts persistés de l'audit visuel (idempotent, même pattern que `checks`).
    Même DDL que scripts/image_audit.py._ensure_audit_flags_table : le cron ÉCRIT, le
    back-office LIT (et écrit aussi via « juger » / « relancer »)."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS image_audit_flags (
        event_id INTEGER PRIMARY KEY,
        reason TEXT,
        flagged_at TEXT,
        resolved_at TEXT
    )""")
    conn.commit()


def _persist_audit_flags(conn, audited_ids, flagged_map):
    """Aligne image_audit_flags sur un jugement à la demande : flag (UPSERT) les images
    signalées, résout (resolved_at=now) les autres vignettes jugées OK. Cohérent avec le
    cron scripts/image_audit._persist_flags."""
    _ensure_audit_flags_table(conn)
    flagged_ids = set(flagged_map or {})
    for eid, reason in (flagged_map or {}).items():
        conn.execute(
            "INSERT INTO image_audit_flags (event_id, reason, flagged_at, resolved_at) "
            "VALUES (?, ?, datetime('now'), NULL) "
            "ON CONFLICT(event_id) DO UPDATE SET reason=excluded.reason, "
            "flagged_at=CASE WHEN image_audit_flags.resolved_at IS NULL "
            "THEN image_audit_flags.flagged_at ELSE datetime('now') END, "
            "resolved_at=NULL",
            (eid, reason or ""))
    for eid in audited_ids:
        if eid in flagged_ids:
            continue
        conn.execute(
            "UPDATE image_audit_flags SET resolved_at=datetime('now') "
            "WHERE event_id=? AND resolved_at IS NULL", (eid,))
    conn.commit()


@app.route("/verifier", methods=["GET", "POST"])
@require_auth
def verifier_view():
    """File « À vérifier » : les faits que le pipeline signale comme incertains, poussés à
    l'humain. On solde un point d'un clic (bouton « vérifié »)."""
    conn = get_db()
    _ensure_checks_table(conn)
    if request.method == "POST":
        done_id = request.form.get("done_check_id")
        if done_id:
            conn.execute(
                "UPDATE checks SET status='done', resolved_at=datetime('now') WHERE id=?",
                (done_id,))
            conn.commit()
            flash("Point vérifié.", "ok")
        conn.close()
        return redirect(url_for("verifier_view"))
    rows = conn.execute(
        "SELECT c.id, c.event_id, c.label, e.article_title, e.title "
        "FROM checks c LEFT JOIN events_raw e ON e.id=c.event_id "
        "WHERE c.status='pending' ORDER BY c.event_id, c.id").fetchall()
    conn.close()
    groups, index = [], {}
    for r in rows:
        eid = r["event_id"]
        if eid not in index:
            index[eid] = len(groups)
            groups.append({"event_id": eid,
                           "titre": (r["article_title"] or r["title"] or f"Fiche {eid}"),
                           "checks": []})
        groups[index[eid]]["checks"].append({"id": r["id"], "label": r["label"]})
    return render_template("verifier.html", active="verifier", groups=groups)


@app.route("/couverture")
@require_auth
def couverture():
    """Compteurs de couverture : section × territoire × langue (repérage des manques)."""
    conn = get_db()
    data = _couv_data(conn)
    conn.close()
    return render_template("couverture.html", active="couverture", **data)


# ---------- Audit visuel « planches contact » (contrôle humain d'un coup d'œil) ----------
def _relancer_image(conn, event_id: int) -> None:
    """Re-cherche une image pour un événement via la chaîne scripts.visuals.resolve_image
    (og:image → photo de page → Wikimedia Commons/Europeana → bannière), met à jour
    url_image / image_source / crédit / point focal en base et flash le résultat.

    Appelé depuis l'écran « Audit visuel » quand une photo posée s'avère hors-sujet.
    keep_existing=False : on veut EXPRÈS remplacer l'image actuelle jugée douteuse, donc
    on vide url_image côté copie mémoire pour forcer resolve_image à repartir du haut de
    la chaîne au lieu de conserver la photo existante."""
    row = conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone()
    if not row:
        flash(f"Fiche {event_id} introuvable.", "err")
        return
    ev = dict(row)
    old_url = (row["url_image"] or "").strip()
    ev["url_image"] = ""  # force la re-recherche depuis le début de la chaîne
    cat_banners = banners = None
    try:
        from scripts import visuals as vz
        client = None
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
        banners = vz.load_territory_images()
        cat_banners = vz.load_territory_category_images()
        blocked = vz.load_blocked_image_domains()
        verify_model = os.getenv("ANTHROPIC_MODEL_VISION") or "claude-haiku-4-5"
        # verify_client=client : on ACTIVE l'agent vision (comme --verify) — on relance
        # justement parce qu'une image douteuse est passée, autant vérifier la nouvelle.
        url, credit, source, fx, fy = vz.resolve_image(
            ev, client, blocked, banners,
            verify_client=client, verify_model=verify_model,
            cat_banners=cat_banners, keep_existing=False)
    except Exception as exc:  # noqa: BLE001 — on veut afficher toute erreur à l'humain
        log.warning("Relance image [%s] échouée : %s", event_id, exc)
        flash(f"Fiche {event_id} : relance image échouée ({exc}).", "err")
        return
    # Si la re-résolution retombe sur la MÊME image (requête générique → Commons rend le
    # même résultat, ex. un portrait de la personnalité) ou ne trouve rien, on ne laisse
    # PAS l'image signalée en place : repli sur la bannière territoriale (propre, jamais
    # hors-sujet). Le sens du bouton « relancer » depuis l'audit : faire DISPARAÎTRE
    # l'image douteuse, pas re-tomber dessus.
    if not url or url == old_url:
        from utils.sources import pick_banner_image
        burl = pick_banner_image(ev.get("territoire", ""), ev.get("llm_categorie", ""),
                                 str(event_id), cat_banners or {}, banners or {})
        if not burl:
            flash(f"Fiche {event_id} : aucune meilleure image ni bannière disponible.", "err")
            return
        url, credit, source, fx, fy = burl, "", "banner", 0.5, 0.5
    ev["url_image"], ev["image_credit"], ev["image_source"] = url, credit, source
    ev["card_focal_x"], ev["card_focal_y"] = fx, fy
    conn.execute(
        "UPDATE events_raw SET url_image=?, image_credit=?, image_source=?, "
        "card_focal_x=?, card_focal_y=? WHERE id=?",
        (url, credit, source, fx, fy, event_id))
    conn.commit()
    # RE-PUSH vers WordPress — SANS ça, la base change mais le site NON (le bug « je clique
    # sur relancer mais rien ne change » : l'ancienne version ne re-poussait jamais).
    pushed = False
    try:
        from scripts.publisher_as import publish_to_as
        new_id, permalink, raw_url = publish_to_as(ev)
        if new_id:
            pushed = True
            # Sur repli bannière, publish_to_as ne ré-héberge pas d'original (anti-bake) →
            # on VIDE wp_raw_image_url_as pour que l'audit ne réaffiche pas l'ancienne
            # photo hébergée (c'est la cause de « l'audit montre X, la fiche montre Y »).
            if source == "banner":
                conn.execute("UPDATE events_raw SET wp_raw_image_url_as='' WHERE id=?", (event_id,))
            if permalink or raw_url:
                conn.execute(
                    "UPDATE events_raw SET wp_permalink_as=COALESCE(NULLIF(?,''), wp_permalink_as), "
                    "wp_raw_image_url_as=COALESCE(NULLIF(?,''), wp_raw_image_url_as) WHERE id=?",
                    (permalink, raw_url, event_id))
            conn.commit()
    except Exception as exc:  # noqa: BLE001
        log.warning("Relance image [%s] : re-push WP échoué : %s", event_id, exc)
    # La photo douteuse est remplacée : on solde le flag d'audit (la nouvelle image sera
    # re-jugée au prochain passage du cron). Best-effort — ne bloque pas la relance.
    try:
        _ensure_audit_flags_table(conn)
        conn.execute(
            "UPDATE image_audit_flags SET resolved_at=datetime('now') "
            "WHERE event_id=? AND resolved_at IS NULL", (event_id,))
        conn.commit()
    except Exception:  # noqa: BLE001
        pass
    _wp = " et publiée sur le site" if pushed else " (⚠️ re-push WordPress échoué — réessaie)"
    flash(f"Fiche {event_id} : nouvelle image posée (source : {source}){_wp}.", "ok")


def _audit_visuel_rows(conn, dfrom: str, dto: str, limit: int, flagged_only: bool = False) -> list:
    """Vignettes de la planche contact HTML pour la période/limite données. Mêmes
    critères que scripts.image_audit._select : retenus, non doublon, vraie photo
    (url_image non vide, image_source != 'banner'), + filtre de période optionnel.
    Chaque ligne reçoit `thumb`/`audit_image_url` (notre copie hébergée en priorité,
    comme image_audit) — la seconde clé est celle qu'attend image_audit.build_grid.
    LEFT JOIN image_audit_flags (non résolus) : chaque carte signalée par le cron reçoit
    `flag_raison` et ressort surlignée AU CHARGEMENT. `flagged_only` ne garde que les
    événements portant un flag actif (sur tout le catalogue, borné par `limit`)."""
    _ensure_audit_flags_table(conn)
    q = ("SELECT e.id, e.title, e.url_image, e.image_source, e.territoire, e.llm_categorie, "
         "e.wp_raw_image_url_as, e.date_event_start, f.reason AS flag_raison "
         "FROM events_raw e "
         "LEFT JOIN image_audit_flags f ON f.event_id = e.id AND f.resolved_at IS NULL "
         "WHERE e.duplicate_of IS NULL AND e.statut IN ({}) "
         "AND COALESCE(e.url_image,'') <> '' AND COALESCE(e.image_source,'') <> 'banner' "
        ).format(",".join("?" * len(comp.RETAINED_STATUTS)))
    params = list(comp.RETAINED_STATUTS)
    if flagged_only:
        q += "AND f.event_id IS NOT NULL "
    if dfrom:
        q += "AND COALESCE(e.date_event_start,'') >= ? "
        params.append(dfrom)
    if dto:
        q += "AND COALESCE(e.date_event_start,'') <= ? "
        params.append(dto)
    q += "ORDER BY e.id DESC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    for r in rows:
        thumb = (r.get("wp_raw_image_url_as") or "").strip() or r["url_image"]
        r["thumb"] = thumb
        r["audit_image_url"] = thumb
    return rows


def _audit_visuel_juger(rows: list) -> "dict | None":
    """Fait juger l'agent vision de scripts.image_audit sur les vignettes AFFICHÉES
    (mêmes filtres) : compose les planches contact (lots de 20), les envoie une par une
    au juge et agrège les cases signalées hors-sujet. Renvoie {event_id: raison} (peut
    être vide) ou None si l'audit n'a pas pu tourner. Flashe un message dans tous les
    cas. Réutilise image_audit.build_grid / judge_grid — aucune logique réimplémentée."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        flash("Audit vision impossible : ANTHROPIC_API_KEY absente de l'environnement.", "err")
        return None
    if not rows:
        flash("Aucune vignette à juger sur ce périmètre.", "err")
        return None
    try:
        import anthropic
        from scripts import image_audit as ia
        client = anthropic.Anthropic(api_key=api_key, timeout=90.0)
        flagged_all = []
        for i in range(0, len(rows), 20):  # mêmes lots de 20 que image_audit.main
            batch = rows[i:i + 20]
            grid, failed = ia.build_grid(batch)
            flagged_all.extend(ia.judge_grid(batch, grid, client, failed))
    except Exception as exc:  # noqa: BLE001 — on veut afficher toute erreur à l'humain
        log.warning("Audit vision (à la demande) échoué : %s", exc)
        flash(f"Audit vision échoué ({exc}).", "err")
        return None
    flagged_map = {f["id"]: (f.get("raison") or "photo hors-sujet") for f in flagged_all}
    if flagged_map:
        resume = ", ".join(f"#{fid}" for fid in flagged_map)
        flash(f"Audit vision : {len(flagged_map)} image(s) signalée(s) hors-sujet sur "
              f"{len(rows)} vignette(s) — {resume}.", "err")
    else:
        flash(f"Audit vision : aucune image suspecte sur {len(rows)} vignette(s). 🎉", "ok")
    return flagged_map


@app.route("/audit-visuel", methods=["GET", "POST"])
@require_auth
def audit_visuel():
    """Planche contact HTML : grille de vignettes (photo + titre + territoire + catégorie
    + lien fiche) des événements retenus portant une VRAIE image (pas la bannière
    générique), pour un contrôle visuel humain d'un coup d'œil. Pendant interactif du
    cron scripts/image_audit.py (qui, lui, fait juger un agent vision + digest Slack).
    Actions POST : « relancer_image » (re-pose une image via resolve_image) et
    « juger » (fait juger l'agent vision de image_audit sur les vignettes affichées et
    surligne les cases signalées)."""
    conn = get_db()
    dfrom = (request.args.get("from") or "").strip()
    dto = (request.args.get("to") or "").strip()
    try:
        limit = int(request.args.get("limit") or 120)
    except (TypeError, ValueError):
        limit = 120
    limit = max(1, min(limit, 600))  # garde-fou : borne le nombre de vignettes chargées
    flagged_only = (request.args.get("flagged") or "").strip() in ("1", "true", "on")

    if request.method == "POST":
        action = request.form.get("action")
        if action == "juger":
            # Le jugement vision (téléchargements + appels) est LENT : le faire dans la
            # requête tuait le worker gunicorn (WORKER TIMEOUT → 500). On lance donc
            # l'audit en ARRIÈRE-PLAN — c'est le MÊME script que le cron, qui PERSISTE
            # ses verdicts dans image_audit_flags ; les cases signalées apparaîtront au
            # rafraîchissement (le badge et le surlignage se mettent à jour tout seuls).
            conn.close()
            try:
                subprocess.Popen(
                    [sys.executable, "-m", "scripts.image_audit",
                     "--limit", str(limit), "--no-slack"],
                    cwd=str(ROOT), start_new_session=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                flash("Audit vision lancé en arrière-plan — les images signalées "
                      "apparaîtront au rafraîchissement (quelques minutes selon le "
                      "nombre d'images).", "ok")
            except Exception as exc:  # noqa: BLE001 — on montre l'échec à l'humain
                flash(f"Impossible de lancer l'audit : {exc}", "err")
            keep = {k: v for k, v in request.args.items()
                    if k in ("from", "to", "limit", "flagged")}
            return redirect(url_for("audit_visuel", **keep))
        if action == "relancer_image" and request.form.get("event_id"):
            anchor = ""
            try:
                eid = int(request.form["event_id"])
                _relancer_image(conn, eid)
                anchor = f"#av-{eid}"  # revenir À LA CARTE, pas en haut de page
            except (TypeError, ValueError):
                flash("Identifiant d'événement invalide.", "err")
            conn.close()
            keep = {k: v for k, v in request.args.items() if k in ("from", "to", "limit", "flagged")}
            return redirect(url_for("audit_visuel", **keep) + anchor)
        conn.close()
        # Conserve les filtres de période/limite/signalées dans la redirection.
        keep = {k: v for k, v in request.args.items() if k in ("from", "to", "limit", "flagged")}
        return redirect(url_for("audit_visuel", **keep))

    rows = _audit_visuel_rows(conn, dfrom, dto, limit, flagged_only)
    conn.close()
    return render_template("audit_visuel.html", active="audit_visuel",
                           events=rows, dfrom=dfrom, dto=dto, limit=limit,
                           flagged_only=flagged_only)


# ---------- Couverture GÉO (catalogue → pages hub SEO hyperlocal) ----------
# Traduit docs/CATALOGUE_GEO_SEO.md en tableau de bord : pour chaque entité (ville,
# massif, vallée, lac, station), combien d'événements PUBLIÉS à venir → laquelle franchit
# le seuil et « gradue » en page dédiée. Le comptage se fait sur la ville (langue-agnostique).
_GEO_SEUIL = 8                                           # nb d'événements pour mériter une page

# (type, nom, priorité, [communes/termes cherchés dans la ville]). Les groupes (massifs,
# vallées, lacs) listent leurs communes membres pour agréger.
_GEO_CATALOGUE = {
    "Savoie / Haute-Savoie": [
        ("ville", "Annecy", "P1", ["annecy"]),
        ("ville", "Chambéry", "P1", ["chambery"]),
        ("ville", "Chamonix", "P1", ["chamonix"]),
        ("ville", "Aix-les-Bains", "P2", ["aix les bains", "aix-les-bains"]),
        ("ville", "Albertville", "P2", ["albertville"]),
        ("ville", "Annemasse", "P2", ["annemasse"]),
        ("ville", "Thonon-les-Bains", "P2", ["thonon"]),
        ("ville", "Évian-les-Bains", "P2", ["evian"]),
        ("ville", "Megève", "P2", ["megeve"]),
        ("ville", "Moûtiers", "P3", ["moutiers"]),
        ("ville", "Bourg-Saint-Maurice", "P3", ["bourg saint maurice", "bourg-saint-maurice"]),
        ("ville", "Saint-Julien-en-Genevois", "P3", ["saint julien en genevois", "saint-julien"]),
        ("lac", "Lac d'Annecy", "P1", ["annecy", "veyrier", "talloires", "menthon", "sevrier", "duingt"]),
        ("lac", "Lac du Bourget", "P2", ["aix les bains", "bourget du lac", "chanaz"]),
        ("massif", "Aravis", "P2", ["la clusaz", "grand bornand", "thones", "manigod", "saint jean de sixt"]),
        ("massif", "Bauges", "P2", ["le chatelard", "lescheraines", "aillon", "la motte en bauges"]),
        ("vallée", "Chablais", "P2", ["thonon", "evian", "morzine", "les gets", "abondance", "chatel", "avoriaz"]),
        ("vallée", "Tarentaise", "P2", ["bourg saint maurice", "moutiers", "aime", "val d isere",
                                        "tignes", "les arcs", "la plagne", "courchevel"]),
        ("vallée", "Maurienne", "P2", ["saint jean de maurienne", "modane", "val cenis", "la toussuire"]),
        ("vallée", "Pays du Mont-Blanc", "P2", ["chamonix", "saint gervais", "megeve", "combloux",
                                                "les houches", "passy", "sallanches"]),
    ],
    "Piémont": [
        ("ville", "Torino / Turin", "P1", ["torino", "turin"]),
        ("ville", "Cuneo", "P2", ["cuneo"]),
        ("ville", "Alba", "P1", ["alba"]),
        ("ville", "Asti", "P2", ["asti"]),
        ("ville", "Alessandria", "P2", ["alessandria"]),
        ("ville", "Biella", "P2", ["biella"]),
        ("ville", "Novara", "P2", ["novara"]),
        ("ville", "Vercelli", "P2", ["vercelli"]),
        ("ville", "Verbania", "P2", ["verbania"]),
        ("ville", "Mondovì", "P3", ["mondovi"]),
        ("ville", "Ivrea", "P2", ["ivrea"]),
        ("ville", "Rivoli", "P2", ["rivoli"]),
        ("colline", "Langhe", "P1", ["alba", "bra", "la morra", "barolo", "dogliani", "neive", "barbaresco", "cherasco"]),
        ("colline", "Monferrato", "P1", ["casale monferrato", "nizza monferrato", "moncalvo", "acqui terme"]),
        ("colline", "Roero", "P2", ["canale", "bra", "santo stefano roero"]),
        ("vallate", "Val di Susa", "P2", ["susa", "bardonecchia", "oulx", "avigliana", "sestriere"]),
        ("vallate", "Valsesia", "P2", ["varallo", "alagna"]),
        ("lac", "Lago Maggiore", "P1", ["verbania", "stresa", "arona", "baveno"]),
        ("lac", "Lago d'Orta", "P2", ["orta san giulio", "omegna"]),
    ],
    "Vallée d'Aoste": [
        ("ville", "Aoste / Aosta", "P1", ["aoste", "aosta"]),
        ("ville", "Courmayeur", "P1", ["courmayeur"]),
        ("ville", "Cervinia", "P1", ["cervinia", "breuil"]),
        ("ville", "Cogne", "P2", ["cogne"]),
        ("ville", "Saint-Vincent", "P2", ["saint vincent", "saint-vincent"]),
        ("ville", "La Thuile", "P2", ["la thuile"]),
        ("ville", "Gressoney", "P2", ["gressoney"]),
        ("ville", "Champoluc / Ayas", "P2", ["champoluc", "ayas"]),
        ("ville", "Pila", "P2", ["pila"]),
        ("vallée", "Valdigne", "P3", ["courmayeur", "la thuile", "morgex", "pre saint didier"]),
        ("vallée", "Valtournenche", "P2", ["cervinia", "breuil", "valtournenche"]),
    ],
    "Nice / Alpes-Maritimes": [
        ("ville", "Nice", "P1", ["nice"]),
        ("ville", "Menton", "P1", ["menton"]),
        ("ville", "Villefranche-sur-Mer", "P2", ["villefranche"]),
        ("ville", "Beaulieu-sur-Mer", "P3", ["beaulieu"]),
        ("ville", "Èze", "P2", ["eze"]),
        ("ville", "Saint-Laurent-du-Var", "P3", ["saint laurent du var"]),
        ("ville", "Roquebrune-Cap-Martin", "P3", ["roquebrune cap martin", "roquebrune-cap-martin"]),
        ("cap", "Cap Ferrat", "P2", ["saint jean cap ferrat", "cap ferrat", "cap-ferrat"]),
        ("vallée", "Vallée de la Roya", "P2", ["tende", "breil", "saorge", "la brigue", "fontan"]),
        ("vallée", "Vallée de la Vésubie", "P2", ["saint martin vesubie", "roquebilliere", "lantosque"]),
        ("vallée", "Vallée de la Tinée", "P3", ["saint sauveur", "isola", "saint etienne de tinee"]),
        ("station", "Isola 2000 / Auron / Valberg", "P2", ["isola", "auron", "valberg"]),
    ],
}


def _geo_match(nville: str, nlieu: str, terms: list) -> bool:
    """Un événement (ville/lieu normalisés) appartient-il à l'entité (ses termes) ?
    Termes ≥ 4 car. : correspondance souple (inclusion dans un sens ou l'autre) ; termes
    courts : égalité stricte (évite les faux positifs type « bra » dans « brasserie »)."""
    for t in terms:
        if len(t) >= 4:
            if (nville and (t in nville or nville in t)) or (len(t) >= 5 and t in nlieu):
                return True
        elif t == nville:
            return True
    return False


def _geo_data(conn):
    today = date.today().isoformat()
    rows = conn.execute(
        "SELECT ville, lieu, territoire FROM events_raw "
        "WHERE COALESCE(wp_post_id_as,0)>0 AND duplicate_of IS NULL "
        "AND COALESCE(date_event_start,'')<>'' "
        "AND COALESCE(NULLIF(date_event_end,''), date_event_start) >= ?", (today,)).fetchall()
    # Pré-normalise chaque événement une fois, rangé par territoire.
    by_terr = {t: [] for t in _GEO_CATALOGUE}
    for r in rows:
        grp = _couv_terr_group(r["territoire"])
        if grp in by_terr:
            by_terr[grp].append((_couv_norm(r["ville"] or ""), _couv_norm(r["lieu"] or ""),
                                 (r["ville"] or "").strip()))
    groups = []
    for terr, entities in _GEO_CATALOGUE.items():
        evs = by_terr.get(terr, [])
        rows_out, matched_villes = [], set()
        for typ, name, prio, terms in entities:
            nterms = [_couv_norm(t) for t in terms]
            n = 0
            for i, (nville, nlieu, _raw) in enumerate(evs):
                if _geo_match(nville, nlieu, nterms):
                    n += 1
                    if typ == "ville":
                        matched_villes.add(i)
            rows_out.append({"type": typ, "name": name, "prio": prio, "count": n,
                             "ready": n >= _GEO_SEUIL})
        rows_out.sort(key=lambda e: (-e["count"], e["name"]))
        # Villes NON cataloguées qui produisent du volume → candidates à ajouter.
        hors = Counter(raw or "(sans ville)" for i, (_nv, _nl, raw) in enumerate(evs)
                       if i not in matched_villes)
        groups.append({
            "territoire": terr, "total": len(evs),
            "hors_villes": len(evs) - len(matched_villes),   # événements sans ville cataloguée
            "ready": sum(1 for e in rows_out if e["ready"]),
            "entities": rows_out,
            "top_hors": hors.most_common(12),
        })
    return {"groups": groups, "seuil": _GEO_SEUIL}


@app.route("/couverture-geo")
@require_auth
def couverture_geo():
    """Combien d'événements publiés par entité géo → laquelle mérite une page (graduation)."""
    conn = get_db()
    data = _geo_data(conn)
    conn.close()
    return render_template("couverture_geo.html", active="couverture_geo", **data)


# ---------- Composeur de newsletter (Phase 1 : voir / curer / ordonner) ----------
# Une newsletter par TERRITOIRE, envoyée le vendredi matin. On la compose toute la
# semaine (dès lundi). Sélection auto = retenus du territoire dans la fenêtre, triés
# par score ; Franck ajuste l'ordre, inclut/exclut, pioche dans les « presque retenus ».
# La sélection ordonnée est stockée par (territoire, édition) en JSON.
_NL_TERRITOIRES = [t[0] for t in _COUV_TERRITOIRES]      # 4 groupes (labels)
_NL_SEED = 8                                             # nb inclus par défaut (amorce)
_NL_WINDOW_DAYS = 7                                      # vendredi → +7 jours


def _nl_slug(label):
    return _couv_norm(label).replace(" ", "-")


def _parse_list_ids(raw):
    """« 3, 7;9 » → [3, 7, 9]. Tolère virgules, points-virgules, espaces."""
    return [int(x) for x in re.split(r"[,;\s]+", (raw or "").strip()) if x.isdigit()]


def _nl_env_key(terr_label):
    """Nom d'env-var de la liste Brevo propre au territoire : BREVO_LIST_<SLUG>.
    Ex. « Savoie / Haute-Savoie » → BREVO_LIST_SAVOIE_HAUTE_SAVOIE."""
    return "BREVO_LIST_" + _nl_slug(terr_label).upper().replace("-", "_")


def _nl_list_ids(terr_label):
    """IDs de liste Brevo pour ce territoire : la liste dédiée BREVO_LIST_<SLUG>
    si elle est renseignée, sinon repli sur la liste globale BREVO_LIST_ID."""
    return _parse_list_ids(os.getenv(_nl_env_key(terr_label), "")) or \
        _parse_list_ids(os.getenv("BREVO_LIST_ID", ""))


def _nl_terr_from_slug(slug):
    for lbl in _NL_TERRITOIRES:
        if _nl_slug(lbl) == slug:
            return lbl
    return _NL_TERRITOIRES[0]


def _nl_edition(param=""):
    """Date de l'édition = un vendredi. Défaut : le prochain vendredi (aujourd'hui inclus)."""
    try:
        return date.fromisoformat(param)
    except (ValueError, TypeError):
        today = date.today()
        return today + timedelta(days=(4 - today.weekday()) % 7)


def _nl_window(edition):
    return edition.isoformat(), (edition + timedelta(days=_NL_WINDOW_DAYS)).isoformat()


def _ensure_nl_table(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS newsletter_editions ("
                 "territoire TEXT NOT NULL, edition TEXT NOT NULL, "
                 "picks_json TEXT NOT NULL DEFAULT '[]', updated_at TEXT, "
                 "PRIMARY KEY (territoire, edition))")


def _nl_pool(conn, terr_label, pfrom, pto):
    """Événements RETENUS, DATÉS, du territoire, chevauchant la fenêtre, triés par score."""
    rows = conn.execute(
        "SELECT id, title, territoire, ville, lieu, llm_categorie, llm_score, user_score, "
        "date_event_start, date_event_end, url_image FROM events_raw "
        "WHERE statut IN ('evaluated','published_cs','published_sub') AND duplicate_of IS NULL "
        "AND COALESCE(date_event_start,'')<>'' "
        "AND COALESCE(date_event_start,'') <= ? "
        "AND COALESCE(NULLIF(date_event_end,''), date_event_start) >= ?",
        (pto, pfrom)).fetchall()
    pool = []
    for r in rows:
        e = dict(r)
        if _couv_terr_group(e["territoire"]) != terr_label:
            continue
        e["score"] = e["user_score"] if e["user_score"] is not None else (e["llm_score"] or 0)
        pool.append(e)
    pool.sort(key=lambda e: (-e["score"], e["date_event_start"] or ""))
    return pool


def _nl_read_picks(conn, terr_label, edition_iso):
    row = conn.execute("SELECT picks_json FROM newsletter_editions WHERE territoire=? AND edition=?",
                       (terr_label, edition_iso)).fetchone()
    if row is None:
        return None
    try:
        return [int(x) for x in json.loads(row["picks_json"])]
    except (ValueError, TypeError):
        return []


def _nl_save_picks(conn, terr_label, edition_iso, picks):
    conn.execute(
        "INSERT INTO newsletter_editions (territoire, edition, picks_json, updated_at) "
        "VALUES (?,?,?,datetime('now','localtime')) "
        "ON CONFLICT(territoire, edition) DO UPDATE SET "
        "picks_json=excluded.picks_json, updated_at=excluded.updated_at",
        (terr_label, edition_iso, json.dumps(picks)))
    conn.commit()


@app.route("/newsletter")
@require_auth
def newsletter_compose():
    terr = _nl_terr_from_slug(request.args.get("t", ""))
    edition = _nl_edition(request.args.get("e", ""))
    edition_iso = edition.isoformat()
    conn = get_db()
    _ensure_nl_table(conn)
    pool = _nl_pool(conn, terr, *_nl_window(edition))
    picks = _nl_read_picks(conn, terr, edition_iso)
    if picks is None:                                   # amorce : top _NL_SEED par score
        picks = [e["id"] for e in pool[:_NL_SEED]]
        _nl_save_picks(conn, terr, edition_iso, picks)
    conn.close()
    by_id = {e["id"]: e for e in pool}
    selected = []
    for pos, i in enumerate([i for i in picks if i in by_id], 1):
        e = by_id[i]
        e["position"] = pos
        selected.append(e)
    picked = set(picks)
    candidates = [e for e in pool if e["id"] not in picked]
    territs = [{"label": l, "slug": _nl_slug(l), "on": l == terr} for l in _NL_TERRITOIRES]
    return render_template(
        "newsletter.html", active="newsletter", territs=territs,
        terr=terr, terr_slug=_nl_slug(terr), edition=edition_iso, edition_dt=edition,
        prev_edition=(edition - timedelta(days=7)).isoformat(),
        next_edition=(edition + timedelta(days=7)).isoformat(),
        win_from=_nl_window(edition)[0], win_to=_nl_window(edition)[1],
        selected=selected, candidates=candidates, n_pool=len(pool),
        n_selected=len(selected),
        brevo_env_key=_nl_env_key(terr),
        brevo_list_ids=_nl_list_ids(terr),
        brevo_dedicated=bool(_parse_list_ids(os.getenv(_nl_env_key(terr), ""))))


@app.route("/newsletter/action", methods=["POST"])
@require_auth
def newsletter_action():
    terr = _nl_terr_from_slug(request.form.get("t", ""))
    edition_iso = _nl_edition(request.form.get("e", "")).isoformat()
    action = request.form.get("action", "")
    try:
        eid = int(request.form.get("event_id", "0"))
    except ValueError:
        eid = 0
    conn = get_db()
    _ensure_nl_table(conn)
    if action == "reset":
        conn.execute("DELETE FROM newsletter_editions WHERE territoire=? AND edition=?",
                     (terr, edition_iso))
        conn.commit()
        conn.close()
        flash("Sélection réinitialisée (amorce automatique).", "ok")
        return redirect(url_for("newsletter_compose", t=_nl_slug(terr), e=edition_iso))
    picks = _nl_read_picks(conn, terr, edition_iso) or []
    if action == "add" and eid and eid not in picks:
        picks.append(eid)
    elif action == "remove" and eid in picks:
        picks.remove(eid)
    elif action in ("up", "down") and eid in picks:
        i = picks.index(eid)
        j = i - 1 if action == "up" else i + 1
        if 0 <= j < len(picks):
            picks[i], picks[j] = picks[j], picks[i]
    _nl_save_picks(conn, terr, edition_iso, picks)
    conn.close()
    return redirect(url_for("newsletter_compose", t=_nl_slug(terr), e=edition_iso) + "#e" + str(eid))


@app.route("/newsletter/brevo", methods=["POST"])
@require_auth
def newsletter_brevo():
    """Crée le brouillon Brevo avec LA sélection composée (dans l'ordre choisi). Jamais
    d'envoi — Brevo garde le brouillon pour relecture/envoi manuel."""
    terr = _nl_terr_from_slug(request.form.get("t", ""))
    edition = _nl_edition(request.form.get("e", ""))
    edition_iso = edition.isoformat()
    conn = get_db()
    _ensure_nl_table(conn)
    picks = _nl_read_picks(conn, terr, edition_iso) or []
    if not picks:
        conn.close()
        flash("Sélection vide — rien à envoyer.", "err")
        return redirect(url_for("newsletter_compose", t=_nl_slug(terr), e=edition_iso))
    ph = ",".join("?" * len(picks))
    full = {r["id"]: dict(r) for r in conn.execute(
        f"SELECT * FROM events_raw WHERE id IN ({ph})", picks).fetchall()}
    conn.close()
    ordered = [full[i] for i in picks if i in full]     # respecte l'ordre composé

    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "")
    sender_name = os.getenv("BREVO_SENDER_NAME", "Agenda Sabauda")
    list_ids = _nl_list_ids(terr)
    if not api_key or not sender_email or not list_ids:
        flash("Config Brevo incomplète dans .env (BREVO_API_KEY / BREVO_SENDER_EMAIL / "
              "et %s ou, à défaut, BREVO_LIST_ID)." % _nl_env_key(terr), "err")
        return redirect(url_for("newsletter_compose", t=_nl_slug(terr), e=edition_iso))

    try:
        from scripts.newsletter import build_data, variant_magazine, _fmt_day
        from utils.brevo import create_draft_campaign, campaign_edit_url, BrevoError
        wl = f"Du {_fmt_day(edition_iso)} au {_fmt_day(_nl_window(edition)[1])}"
        subject = f"Agenda Sabauda — {terr}, à l'affiche cette semaine"
        tagline = f"Les sorties à vivre en {terr}"
        # Composition MANUELLE : l'ordre choisi par l'humain fait foi → pas d'axe temporel.
        html = variant_magazine(build_data(ordered, week_label=wl, tagline=tagline, temporal=False))
        try:
            cid = create_draft_campaign(
                api_key=api_key, name=f"Agenda Sabauda — {terr} — {wl}", subject=subject,
                sender_name=sender_name, sender_email=sender_email,
                list_ids=list_ids, html_content=html)
        except BrevoError as exc:
            flash("Brevo a refusé la création du brouillon : %s" % exc, "err")
            return redirect(url_for("newsletter_compose", t=_nl_slug(terr), e=edition_iso))
        flash(Markup("📧 Brouillon Brevo créé avec %d événement(s) — "
                     "<a href='%s' target='_blank' rel='noopener'><b>relire / envoyer dans Brevo ↗</b></a>"
                     % (len(ordered), campaign_edit_url(cid))), "ok")
    except (ImportError, OSError, ValueError) as exc:
        flash("Échec de fabrication du brouillon : %s" % exc, "err")
    return redirect(url_for("newsletter_compose", t=_nl_slug(terr), e=edition_iso))


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


# ---------- Widget public « Agenda Sabauda » (embeddable partenaires) ----------
# Un partenaire (office de tourisme, mairie, blog…) colle UNE ligne sur son site et
# affiche les prochains événements de l'Agenda, avec liens retour vers le site public.
# Deux intégrations : <script> (rendu dans la page hôte, Shadow DOM isolé) ou <iframe>
# (page autonome). Le flux JSON est PUBLIC + CORS *, sans auth : les visiteurs des
# partenaires doivent pouvoir le charger. Les fiches pointent vers agendasabauda.eu.
_EMBED_MAX = 20
_EMBED_DEFAULT = 6

# Script embeddable autonome (aucune dépendance). Rendu dans un Shadow DOM pour ne pas
# hériter/polluer le CSS du site hôte. Lit ses data-* et interroge /embed/events.json.
_EMBED_WIDGET_JS = r"""(function(){
  var s = document.currentScript;
  if(!s){ return; }
  var base = s.src.replace(/\/embed\/widget\.js.*$/, '');
  var d = function(k, def){ var v = s.getAttribute('data-'+k); return (v===null||v==='')?def:v; };
  var terr=d('territoire',''), ville=d('ville',''), lang=d('lang',''),
      limit=d('limit','6'), title=d('title','Agenda Sabauda'),
      accent=d('accent','#7a5b3a');
  if(!/^#[0-9a-fA-F]{3,8}$/.test(accent)){ accent='#7a5b3a'; }
  var host = document.createElement('div');
  host.className = 'agenda-sabauda-widget';
  s.parentNode.insertBefore(host, s.nextSibling);
  var root = host.attachShadow ? host.attachShadow({mode:'open'}) : host;
  var css = document.createElement('style');
  css.textContent = ''
    + ':host,*{box-sizing:border-box}'
    + '.w{--a:'+accent+';font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:#2a2622;max-width:640px}'
    + '.hd{display:flex;align-items:center;gap:.5rem;margin:0 0 .6rem;font-size:.78rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--a)}'
    + '.hd:before{content:"";width:1.4rem;height:2px;background:var(--a);border-radius:2px}'
    + '.it{display:flex;gap:.7rem;align-items:center;text-decoration:none;color:inherit;padding:.5rem;border-radius:10px;transition:background .15s}'
    + '.it:hover{background:rgba(0,0,0,.04)}'
    + '.th{width:64px;height:52px;flex:0 0 auto;border-radius:7px;background:#e7e1d6 center/cover no-repeat}'
    + '.bd{min-width:0;flex:1}'
    + '.ti{font-weight:600;font-size:.92rem;line-height:1.25;margin:0 0 .15rem;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}'
    + '.mt{font-size:.76rem;color:#6b6357;line-height:1.3}'
    + '.dt{color:var(--a);font-weight:600}'
    + '.ft{margin:.5rem .1rem 0;font-size:.72rem}'
    + '.ft a{color:var(--a);text-decoration:none;font-weight:600}'
    + '.em{font-size:.85rem;color:#6b6357;padding:.6rem .5rem}';
  root.appendChild(css);
  var wrap = document.createElement('div'); wrap.className='w';
  var hd = document.createElement('div'); hd.className='hd'; hd.textContent=title;
  wrap.appendChild(hd);
  var list = document.createElement('div'); wrap.appendChild(list);
  var ft = document.createElement('div'); ft.className='ft';
  var fa = document.createElement('a'); fa.href=base==''?'#':base; fa.target='_blank'; fa.rel='noopener';
  ft.appendChild(fa); wrap.appendChild(ft);
  root.appendChild(wrap);
  var q = [];
  if(terr){ q.push('t='+encodeURIComponent(terr)); }
  if(ville){ q.push('ville='+encodeURIComponent(ville)); }
  if(lang){ q.push('lang='+encodeURIComponent(lang)); }
  q.push('limit='+encodeURIComponent(limit));
  fetch(base+'/embed/events.json?'+q.join('&')).then(function(r){return r.json();}).then(function(data){
    var evs = (data && data.events) || [];
    fa.href = data && data.source ? data.source : (base||'#');
    fa.textContent = 'Voir tout l’agenda →';
    if(!evs.length){ var em=document.createElement('div'); em.className='em';
      em.textContent='Aucun événement à venir pour le moment.'; list.appendChild(em); return; }
    evs.forEach(function(e){
      var a=document.createElement('a'); a.className='it'; a.href=e.url; a.target='_blank'; a.rel='noopener';
      var th=document.createElement('div'); th.className='th';
      if(e.image){ th.style.backgroundImage='url("'+String(e.image).replace(/"/g,'')+'")'; }
      a.appendChild(th);
      var bd=document.createElement('div'); bd.className='bd';
      var ti=document.createElement('div'); ti.className='ti'; ti.textContent=e.title; bd.appendChild(ti);
      var mt=document.createElement('div'); mt.className='mt';
      if(e.date_label){ var dt=document.createElement('span'); dt.className='dt'; dt.textContent=e.date_label; mt.appendChild(dt); }
      var tail=[]; if(e.ville){ tail.push(e.ville); } if(e.categorie){ tail.push(e.categorie); }
      if(tail.length){ mt.appendChild(document.createTextNode((e.date_label?' · ':'')+tail.join(' · '))); }
      bd.appendChild(mt); a.appendChild(bd); list.appendChild(a);
    });
  }).catch(function(){ var em=document.createElement('div'); em.className='em';
    em.textContent='Agenda momentanément indisponible.'; list.appendChild(em); });
})();
"""


def _as_public_base():
    return (os.getenv("WP_AS_URL", "") or "https://agendasabauda.eu").rstrip("/")


def _terr_from_slug_strict(slug):
    """Slug → libellé de territoire, ou None si aucun ne correspond (pas de repli)."""
    for lbl in _NL_TERRITOIRES:
        if _nl_slug(lbl) == slug:
            return lbl
    return None


def _embed_date_label(start, end):
    d1, d2 = _couv_date(start), _couv_date(end)
    if not d1:
        return ""
    fmt = lambda d: "%d %s" % (d.day, _MOIS_ABBR[d.month])
    return "%s → %s" % (fmt(d1), fmt(d2)) if d2 and d2 != d1 else fmt(d1)


def _embed_events(conn, terr_label=None, ville=None, lang=None, limit=_EMBED_DEFAULT):
    """Prochains événements EN LIGNE sur l'Agenda (wp_post_id_as), triés par date."""
    today = date.today().isoformat()
    rows = conn.execute(
        "SELECT id, title, territoire, ville, lieu, llm_categorie, description, "
        "date_event_start, date_event_end, url_image, wp_post_id_as FROM events_raw "
        "WHERE COALESCE(wp_post_id_as,0)>0 AND duplicate_of IS NULL "
        "AND COALESCE(date_event_start,'')<>'' "
        "AND COALESCE(NULLIF(date_event_end,''), date_event_start) >= ? "
        "ORDER BY date_event_start ASC", (today,)).fetchall()
    base = _as_public_base()
    from utils.lang import detect_lang
    out = []
    for r in rows:
        if terr_label and _couv_terr_group(r["territoire"]) != terr_label:
            continue
        if ville and _couv_norm(ville) not in _couv_norm(r["ville"] or ""):
            continue
        if lang and detect_lang(r["title"] or "", r["description"] or "",
                                r["territoire"] or "") != lang:
            continue
        out.append({
            "id": r["id"],
            "title": r["title"] or "",
            "date_label": _embed_date_label(r["date_event_start"], r["date_event_end"]),
            "ville": r["ville"] or "",
            "lieu": r["lieu"] or "",
            "categorie": r["llm_categorie"] or "",
            "territoire": _couv_terr_group(r["territoire"]),
            "image": r["url_image"] or "",
            "url": "%s/?p=%d" % (base, int(r["wp_post_id_as"])),
        })
        if len(out) >= limit:
            break
    return out


def _embed_params(src):
    """Lit t/ville/lang/limit depuis un mapping (request.args)."""
    terr = _terr_from_slug_strict(src.get("t", "") or "")
    ville = (src.get("ville", "") or "").strip() or None
    lang = (src.get("lang", "") or "").strip().lower()
    lang = lang if lang in ("fr", "it") else None
    try:
        limit = max(1, min(_EMBED_MAX, int(src.get("limit", _EMBED_DEFAULT))))
    except (ValueError, TypeError):
        limit = _EMBED_DEFAULT
    return terr, ville, lang, limit


@app.route("/embed/events.json")
def embed_events_json():
    """Flux public des prochains événements (CORS *). Params : t, ville, lang, limit."""
    terr, ville, lang, limit = _embed_params(request.args)
    conn = get_db()
    events = _embed_events(conn, terr, ville, lang, limit)
    conn.close()
    resp = jsonify({"events": events, "count": len(events),
                    "source": _as_public_base(),
                    "generated": datetime.now().isoformat(timespec="seconds")})
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Cache-Control"] = "public, max-age=600"
    return resp


@app.route("/embed/widget.js")
def embed_widget_js():
    """Script embeddable : crée un conteneur isolé (Shadow DOM) et affiche les fiches.
    Le partenaire colle UNE ligne ; le script lit ses data-* et interroge events.json."""
    js = _EMBED_WIDGET_JS
    resp = Response(js, mimetype="application/javascript; charset=utf-8")
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


@app.route("/embed/widget")
def embed_widget_iframe():
    """Page autonome pour intégration en <iframe> (rendu serveur, styles isolés)."""
    terr, ville, lang, limit = _embed_params(request.args)
    conn = get_db()
    events = _embed_events(conn, terr, ville, lang, limit)
    conn.close()
    title = (request.args.get("title", "") or "Agenda Sabauda").strip()[:60]
    accent = _embed_accent(request.args.get("accent", ""))
    resp = Response(render_template(
        "embed_widget.html", events=events, title=title, accent=accent,
        source=_as_public_base()))
    resp.headers["Cache-Control"] = "public, max-age=600"
    resp.headers["X-Frame-Options"] = "ALLOWALL"          # embeddable partout
    return resp


def _embed_accent(raw):
    """Valide une couleur hex fournie par le partenaire (sinon accent par défaut)."""
    raw = (raw or "").strip()
    return raw if re.match(r"^#[0-9a-fA-F]{3,8}$", raw) else "#7a5b3a"


@app.route("/partenariat")
@require_auth
def partenariat():
    """Générateur du widget : aperçu + code à coller (script / iframe) pour la page
    « Travailler avec nous » du site et pour les partenaires."""
    terr, ville, lang, limit = _embed_params(request.args)
    accent = _embed_accent(request.args.get("accent", ""))
    title = (request.args.get("title", "") or "Agenda Sabauda").strip()[:60]
    territs = [{"label": l, "slug": _nl_slug(l)} for l in _NL_TERRITOIRES]
    qs = {"t": _nl_slug(terr) if terr else "", "ville": ville or "",
          "lang": lang or "", "limit": limit, "accent": accent, "title": title}
    query = "&".join("%s=%s" % (k, v) for k, v in qs.items() if v not in ("", None))
    return render_template(
        "partenariat.html", active="partenariat", territs=territs,
        sel_terr=_nl_slug(terr) if terr else "", ville=ville or "", lang=lang or "",
        limit=limit, accent=accent, title=title, query=query,
        base=PUBLIC_BASE_URL)


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
    today = date.today().isoformat()
    n_queue = conn.execute(
        "SELECT COUNT(*) n FROM events_raw WHERE statut='evaluated' AND llm_score>=7").fetchone()["n"]
    n_past = conn.execute(
        "SELECT COUNT(*) n FROM events_raw WHERE statut='evaluated' AND llm_score>=7 "
        "AND COALESCE(NULLIF(date_event_end,''), date_event_start) < ?", (today,)).fetchone()["n"]
    conn.close()
    events = annotate_period([dict(e) for e in events], pfrom, pto)
    return render_template(
        "index.html", events=events, alert=friendly_alert(),
        preset=preset, dfrom=dfrom, dto=dto, plabel=plabel,
        presets=PERIOD_PRESETS, has_period=bool(pfrom and pto),
        n_queue=n_queue, n_past=n_past,
        badge_off=bool(load_ui_state().get("validate_badge_off")))


@app.route("/validation/tidy", methods=["POST"])
@require_auth
def validation_tidy():
    """File « À valider » (Cultura Sabauda). action=archive_past : archive les événements
    PASSÉS (→ 'rejected', réversible). action=badge_off/badge_on : masque/réaffiche la
    pastille (tant que Franck ne travaille pas CS). Aucune touche aux fiches à-venir."""
    action = request.form.get("action", "")
    if action == "archive_past":
        conn = get_db()
        cur = conn.execute(
            "UPDATE events_raw SET statut='rejected', "
            "llm_justification='Passé — archivé depuis À valider.' "
            "WHERE statut='evaluated' AND llm_score>=7 "
            "AND COALESCE(NULLIF(date_event_end,''), date_event_start) < ?",
            (date.today().isoformat(),))
        conn.commit()
        conn.close()
        flash("À valider : %d événement(s) passé(s) archivé(s)." % cur.rowcount, "ok")
    elif action == "badge_off":
        save_ui_state({**load_ui_state(), "validate_badge_off": True})
        flash("Pastille « À valider » masquée. Réactive-la quand tu reprendras Cultura Sabauda.", "ok")
    elif action == "badge_on":
        st = load_ui_state(); st.pop("validate_badge_off", None); save_ui_state(st)
        flash("Pastille « À valider » réaffichée.", "ok")
    return redirect(url_for("validation"))


@app.route("/preview/<int:event_id>")
@require_auth
def preview(event_id: int):
    conn = get_db()
    ev = conn.execute("SELECT * FROM events_raw WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    if not ev:
        return "Événement introuvable", 404
    ev = dict(ev)
    # Fiche traduite : son url_source est un pseudo-lien « translated:NNN:lang ». On
    # affiche à la place la VRAIE source de l'original (lien cliquable, vérifiable).
    if (ev.get("url_source") or "").startswith("translated:") and ev.get("translation_of"):
        conn2 = get_db()
        orig = conn2.execute("SELECT url_source FROM events_raw WHERE id=?",
                             (ev["translation_of"],)).fetchone()
        conn2.close()
        if orig and (orig["url_source"] or "") and not (orig["url_source"] or "").startswith("translated:"):
            ev["url_source"] = orig["url_source"]
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
    # Le preview affichait le corps/chapô en MARKDOWN BRUT (**gras** et « ## » littéraux →
    # « rien en gras »). On rend le markdown en HTML — MÊME conversion que la publication
    # WordPress (scripts.publisher._md_to_html) — pour juger le VRAI article.
    if isinstance(enriched, dict) and isinstance(enriched.get("article"), dict):
        try:
            from scripts.publisher import _md_to_html, _md_inline
            from utils.clean_text import polish_prose
            _art = enriched["article"]
            # MÊME nettoyage déterministe que la publication (gras/tirets) : le preview
            # doit montrer l'article TEL QU'IL SERA publié, pas le markdown brut du modèle.
            if _art.get("corps"):
                _art["corps_html"] = _md_to_html(polish_prose(_art["corps"]))
            if _art.get("chapo"):
                _art["chapo_html"] = _md_inline(polish_prose(_art["chapo"]))
        except Exception:  # noqa: BLE001 — rendu markdown non bloquant
            pass
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
    # Partage réseaux : post Instagram prêt à copier (légende FR + IT, hashtags, alt).
    from utils import social as social_mod
    conn3 = get_db()
    ev["_organizer_handle"] = organizers.confirmed_handle(conn3, ev.get("organisateur") or "")
    conn3.close()
    ig_post = social_mod.instagram_post(ev)
    return render_template("preview.html", e=ev, image=image,
                           image_host=image_host, is_radar=is_radar,
                           enriched=enriched, enrich_running=enrich_running,
                           press_kits=press_kits, score_detail=score_detail,
                           jsonld=jsonld, seo_faq=seo_faq, seo_tags=seo_tags,
                           faq_jsonld=faq_jsonld, ig_post=ig_post)


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
                  "territoire", "llm_categorie", "url_officiel",
                  # Affiches manuelles : pour les sites JS/gated où l'extraction auto échoue
                  # (dossier de presse derrière accréditation, visuel rendu en JavaScript).
                  "url_image", "url_image_portrait", "url_image_wide")


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
    # Case « lieux multiples » : appliquée seulement si le formulaire la porte
    # (marqueur), pour ne pas l'effacer lors d'un post partiel (ex. Claude-in-Chrome).
    if request.form.get("multi_lieux_present"):
        updates["multi_lieux"] = 1 if request.form.get("multi_lieux") else 0
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


# --------------------------------------------------------------------------- #
# « Cette semaine » (demande de Franck) : file de travail UNIQUE — une tâche =
# une décision atomique (photo à valider, texte à relire), au lieu de naviguer
# entre une dizaine de pages pour savoir quoi faire. Une tâche redevient à faire
# d'elle-même dès que son contenu change (comparaison directe au contenu actuel,
# pas une invalidation à gérer partout ailleurs dans le code où l'image/texte
# peut changer — cron, back-office, republication…).
# --------------------------------------------------------------------------- #
_SEMAINE_CAP = 20


@app.route("/semaine")
@require_auth
def semaine():
    conn = get_db()
    tasks = semaine_mod.tasks(conn)
    since = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")
    done_week = conn.execute(
        "SELECT (SELECT COUNT(*) FROM events_raw WHERE image_reviewed_at >= ?) + "
        "(SELECT COUNT(*) FROM events_raw WHERE text_reviewed_at >= ?) n",
        (since, since)).fetchone()["n"]
    conn.close()
    from utils import social as social_mod
    for t in tasks:
        if t["kind"] == "organisateur":
            continue
        e = t["event"]
        e["_img"] = event_image(e)
        if t["kind"] == "texte":
            _, e["_content"] = build_post(e)
        elif t["kind"] == "instagram-manuel":
            e["_caption"] = social_mod.caption(e, social_mod.default_lang(e.get("territoire", "")))
    # Mode rattrapage (?rattrapage=1) : Franck veut TOUT voir d'un coup, pas de plafond.
    shown = tasks if request.args.get("rattrapage") == "1" else tasks[:_SEMAINE_CAP]
    return render_template(
        "semaine.html", tasks=shown, total=len(tasks),
        done_week=done_week, active="semaine")


@app.route("/semaine/valider/<int:event_id>/<champ>", methods=["POST"])
@require_auth
def semaine_valider(event_id, champ):
    """Marque une tâche faite (« ça va ») — champ = 'photo' | 'texte' | 'instagram-manuel'.
    Reprend d'elle-même si le contenu concerné change ensuite (cf. utils.semaine.tasks) ;
    'instagram-manuel' ne reprend PAS tout seul (ig_manual_mode reste à 1 tant que
    Franck ne republie pas en manuel), c'est une simple date de fin de tâche."""
    conn = get_db()
    row = conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return redirect(url_for("semaine"))
    ev = dict(row)
    now = datetime.now().isoformat(timespec="seconds")
    if champ == "photo":
        conn.execute("UPDATE events_raw SET image_reviewed_at=?, image_reviewed_url=? WHERE id=?",
                     (now, ev.get("url_image") or "", event_id))
    elif champ == "texte":
        conn.execute("UPDATE events_raw SET text_reviewed_at=?, text_reviewed_hash=? WHERE id=?",
                     (now, semaine_mod.text_hash(ev), event_id))
    elif champ == "instagram-manuel":
        conn.execute("UPDATE events_raw SET ig_manual_done_at=? WHERE id=?", (now, event_id))
    conn.commit()
    conn.close()
    return redirect(url_for("semaine") + f"#e{event_id}-{champ}")


@app.route("/semaine/organisateur/<key>/confirmer", methods=["POST"])
@require_auth
def semaine_organisateur_confirmer(key):
    """Confirme le handle Instagram d'un organisateur — mémorisé et réutilisé
    silencieusement ensuite dans toutes les légendes (utils.social.caption), sans
    plus jamais redemander à Franck pour ce même organisateur."""
    handle = (request.form.get("handle") or "").lstrip("@").strip()
    conn = get_db()
    if handle:
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            "UPDATE organizer_ig_handles SET handle=?, status='confirmed', confirmed_at=? "
            "WHERE organisateur_key=?", (handle, now, key))
        conn.commit()
        flash(f"✅ Compte Instagram confirmé : @{handle}.", "ok")
    else:
        flash("⚠️ Handle vide — rien d'enregistré.", "err")
    conn.close()
    return redirect(url_for("semaine") + "#organisateur-" + key)


@app.route("/semaine/organisateur/<key>/refuser", methods=["POST"])
@require_auth
def semaine_organisateur_refuser(key):
    """Aucun compte à mentionner pour cet organisateur — ne redemande plus."""
    conn = get_db()
    conn.execute("UPDATE organizer_ig_handles SET status='none' WHERE organisateur_key=?", (key,))
    conn.commit()
    conn.close()
    flash("🚫 Aucun compte retenu pour cet organisateur.", "ok")
    return redirect(url_for("semaine"))


@app.route("/triage")
@require_auth
def triage():
    """TRIAGE des fiches bloquées : pour chaque fiche « À compléter », on DEVINE la
    cause (permanent → récurrent ; itinérant → multi-lieux ; sinon manuel) et on
    propose la bonne action en 1 clic. Objectif : vider la file de tout ce qui est
    résoluble par une simple case, pour ne garder que le vraiment ambigu."""
    today = date.today().isoformat()
    clause, cp = incomplete_clause(today)
    sql = (f"SELECT * FROM events_raw WHERE {clause} "
           "ORDER BY COALESCE(NULLIF(date_event_start,''),'9999-12-31') ASC")
    conn = get_db()
    rows = conn.execute(sql, list(cp)).fetchall()
    conn.close()
    buckets = {"recurring": [], "multi_lieux": [], "both": [], "manual": []}
    for r in rows:
        e = dict(r)
        e["_triage"] = triage_mod.classify(e)
        e["_img"] = event_image(e)
        buckets[e["_triage"]["primary"]].append(e)
    counts = {k: len(v) for k, v in buckets.items()}
    counts["total"] = len(rows)
    # Nombre de fiches qu'une simple case suffirait à compléter (gain immédiat).
    counts["resolvable"] = sum(
        1 for v in buckets.values() for e in v if e["_triage"]["resolved_by_flags"])
    return render_template(
        "triage.html", buckets=buckets, counts=counts, today=today,
        active="triage", alert=friendly_alert())


@app.route("/triage/apply", methods=["POST"])
@require_auth
def triage_apply():
    """Applique EN LOT une relaxation éditoriale (récurrent OU multi-lieux) à toutes
    les fiches de la file où le triage la suggère. Réversible (recurring_off /
    multi_lieux_off). Ne publie rien et n'invente aucune donnée — relâche juste une
    exigence. On RE-CALCULE la suggestion au moment de l'action (pas de confiance à
    des ids venus du formulaire)."""
    kind = request.form.get("kind", "")
    if kind not in ("recurring", "multi_lieux"):
        flash("⚠️ Action de triage inconnue.", "err")
        return redirect(url_for("triage"))
    today = date.today().isoformat()
    clause, cp = incomplete_clause(today)
    conn = get_db()
    rows = conn.execute(f"SELECT * FROM events_raw WHERE {clause}", list(cp)).fetchall()
    n = 0
    for r in rows:
        c = triage_mod.classify(dict(r))
        if kind == "recurring" and c["suggest_recurring"]:
            conn.execute("UPDATE events_raw SET recurring=1 WHERE id=?", (r["id"],))
            n += 1
        elif kind == "multi_lieux" and c["suggest_multi"]:
            conn.execute("UPDATE events_raw SET multi_lieux=1 WHERE id=?", (r["id"],))
            n += 1
    conn.commit()
    conn.close()
    libelle = "récurrent" if kind == "recurring" else "multi-lieux"
    flash(f"✅ {n} fiche(s) marquée(s) « {libelle} » — elles quittent la file.", "ok")
    return redirect(url_for("triage"))


# --- Réseaux : tableau de publication Instagram, un « compte » par territoire ---------
# Chaque compte publie les PRINCIPAUX événements de SON territoire (top score, à venir,
# complets) + une section « 🌟 Vaut le détour » (événements phares des AUTRES territoires,
# marqués worth_trip). Légende générée dans la langue du compte (VdA = FR puis IT).
_RESEAUX_ACCOUNTS = [
    ("Savoie / Haute-Savoie", ["fr"]),
    ("Piémont", ["it"]),
    ("Vallée d'Aoste", ["fr", "it"]),
    ("Nice / Alpes-Maritimes", ["fr"]),
]
_RESEAUX_MAINS = 8       # nb de « principaux » remontés par territoire (on en choisit 3/sem)
_RESEAUX_DETOURS = 3     # nb de « vaut le détour » proposés par compte


def _auto_rewrite_captions(by_terr: dict) -> int:
    """Réécrit automatiquement (LLM, payant) les légendes des meilleurs événements
    par territoire × langue, SI le réglage social_caption_auto est activé (cf.
    /reglages). Plafonné à settings.social_caption_limit() par territoire × langue —
    volume nécessairement petit (cadence réseaux = quelques posts/semaine, jamais
    100/jour). Ne réécrit QUE les événements qui n'ont pas encore de légende IA en
    cache (jamais de double coût). Mute les dicts de `by_terr` EN PLACE ; renvoie le
    nombre de légendes générées. N'échoue jamais bruyamment : une erreur API laisse
    simplement l'événement sur sa légende gratuite, journalisée seulement."""
    from utils import settings as pipeline_settings
    if not pipeline_settings.social_caption_auto():
        return 0
    limit = pipeline_settings.social_caption_limit()
    if limit <= 0:
        return 0
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return 0
    import anthropic
    from utils import social as social_mod
    model = (os.getenv("ANTHROPIC_MODEL_SEO") or os.getenv("ANTHROPIC_MODEL_VISUALS")
             or "claude-haiku-4-5")
    client = anthropic.Anthropic(api_key=api_key)
    conn = get_db()
    n = 0
    try:
        for label, langs in _RESEAUX_ACCOUNTS:
            candidates = by_terr.get(label, [])[:_RESEAUX_MAINS]
            for lg in langs:
                done = 0
                for e in candidates:
                    if done >= limit:
                        break
                    if e.get(f"social_caption_{lg}"):
                        continue  # déjà en cache — jamais régénéré tout seul
                    try:
                        text = social_mod.caption_ai(e, lg, client, model)
                    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
                        usage.note_api_error(exc)
                        log.warning("Auto-réécriture légende échouée (id=%s, %s) : %s",
                                    e.get("id"), lg, exc)
                        continue
                    if not text:
                        continue
                    e[f"social_caption_{lg}"] = text
                    conn.execute(f"UPDATE events_raw SET social_caption_{lg}=? WHERE id=?",
                                (text, e["id"]))
                    n += 1
                    done += 1
        if n:
            conn.commit()
    finally:
        conn.close()
    return n


@app.route("/reseaux")
@require_auth
def reseaux():
    from utils import social as social_mod, instagram_publish as ig
    today = date.today().isoformat()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM events_raw "
        "WHERE statut IN ('evaluated','published_cs','published_sub') "
        "  AND duplicate_of IS NULL AND COALESCE(translation_of,0)=0 "
        "  AND (COALESCE(date_event_end, date_event_start,'')='' "
        "       OR COALESCE(date_event_end, date_event_start) >= ?) "
        "ORDER BY COALESCE(llm_score,0) DESC, "
        "         COALESCE(NULLIF(date_event_start,''),'9999-12-31') ASC",
        (today,)).fetchall()
    published = {(r["event_id"], r["lang"], r["kind"]): r["status"]
                 for r in conn.execute(
                     "SELECT event_id, lang, kind, status FROM social_posts "
                     "WHERE status='ok' AND id IN "
                     "(SELECT MAX(id) FROM social_posts GROUP BY event_id, lang, kind)")}
    scheduled: dict = {}
    for r in conn.execute(
            "SELECT event_id, lang, kind, scheduled_at FROM ig_scheduled_posts "
            "WHERE status='pending' ORDER BY scheduled_at ASC"):
        scheduled.setdefault(r["event_id"], []).append(
            {"lang": r["lang"], "kind": r["kind"], "scheduled_at": r["scheduled_at"]})
    # Ne garder que les événements POSTABLES (complets) et les grouper par territoire.
    by_terr: dict = {}
    detour_pool: list = []
    for r in rows:
        e = dict(r)
        if not comp.is_complete(e):
            continue
        # Mention organisateur (si confirmée) : injectée AVANT tout appel à
        # social_mod.caption (cf. _pack ci-dessous), pendant que conn est encore ouverte.
        e["_organizer_handle"] = organizers.confirmed_handle(conn, e.get("organisateur") or "")
        grp = _couv_terr_group(e.get("territoire"))
        by_terr.setdefault(grp, []).append(e)
        if e.get("worth_trip"):
            detour_pool.append(e)
    conn.close()

    n_auto = _auto_rewrite_captions(by_terr)
    if n_auto:
        flash(f"🪄 {n_auto} légende(s) réécrite(s) automatiquement (voix Enrico) 💶.", "ok")

    def _pack(e, langs):
        e = dict(e)
        e["_img"] = event_image(e)
        # Légende réécrite (Enrico + humanisée) si déjà générée pour cet événement,
        # sinon la version gratuite auto-générée (cf. utils.social.caption_ai / caption).
        e["_caps"] = {lg: e.get(f"social_caption_{lg}") or social_mod.caption(e, lg)
                     for lg in langs}
        e["_ai_caps"] = {lg: bool(e.get(f"social_caption_{lg}")) for lg in langs}
        e["_alts"] = {lg: social_mod.alt_text(e, lg) for lg in langs}
        e["_keyword"] = e.get("dm_keyword") or social_mod.dm_keyword(e.get("title") or "")
        e["_published"] = {lg: {k: published.get((e["id"], lg, k)) == "ok"
                                for k in ("single", "carousel", "story")}
                           for lg in langs}
        e["_scheduled"] = scheduled.get(e["id"], [])
        return e

    accounts = []
    for label, langs in _RESEAUX_ACCOUNTS:
        mains = [_pack(e, langs) for e in by_terr.get(label, [])[:_RESEAUX_MAINS]]
        detours = [_pack(e, langs) for e in detour_pool
                   if _couv_terr_group(e.get("territoire")) != label][:_RESEAUX_DETOURS]
        accounts.append({"label": label, "langs": langs,
                         "mains": mains, "detours": detours,
                         "ig_ready": ig.configured(label)})
    return render_template("reseaux.html", accounts=accounts, today=today,
                           active="reseaux", posts_per_week=3)


@app.route("/reseaux/rewrite/<int:event_id>", methods=["POST"])
@require_auth
def reseaux_rewrite(event_id: int):
    """Réécrit la légende via LLM (voix Enrico Nos Alpes + anti-signes-IA, cf.
    utils.social.caption_ai) pour UN événement, À LA DEMANDE — coût maîtrisé, jamais
    automatique. Le résultat est mis en cache (events_raw.social_caption_<lang>)."""
    import anthropic
    from utils import social as social_mod
    lang = request.form.get("lang", "fr")
    if lang not in ("fr", "it"):
        lang = "fr"
    conn = get_db()
    row = conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return "Événement introuvable", 404
    ev = dict(row)
    title = (ev.get("title") or "")[:70]
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        conn.close()
        flash("⚠️ Clé API absente — légende non réécrite.", "err")
        return redirect(url_for("reseaux") + f"#e{event_id}")
    model = (os.getenv("ANTHROPIC_MODEL_SEO") or os.getenv("ANTHROPIC_MODEL_VISUALS")
             or "claude-haiku-4-5")
    try:
        client = anthropic.Anthropic(api_key=api_key)
        text = social_mod.caption_ai(ev, lang, client, model)
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        usage.note_api_error(exc)
        conn.close()
        flash("⚠️ Appel API échoué (crédit/quota ?) — voir le bandeau d'alerte.", "err")
        return redirect(url_for("reseaux") + f"#e{event_id}")
    if not text:
        conn.close()
        flash(f"⚠️ « {title} » — réponse illisible du modèle, réessaie.", "err")
        return redirect(url_for("reseaux") + f"#e{event_id}")
    conn.execute(f"UPDATE events_raw SET social_caption_{lang}=? WHERE id=?",
                (text, event_id))
    conn.commit()
    conn.close()
    flash(f"✨ « {title} » — légende réécrite ({lang.upper()}, voix Enrico) 💶.", "ok")
    return redirect(url_for("reseaux") + f"#e{event_id}")


def _do_publish_instagram(ev: dict, terr_label: str, lang: str, kind: str, conn,
                          *, caption_override: str = "", alt_override: str = "",
                          dm_keyword_override: str = "") -> dict:
    """Chemin de publication PARTAGÉ par la publication immédiate (/reseaux/publish)
    et la publication programmée (scripts/ig_scheduler.py) : résolution image,
    construction légende, choix single/carousel/story, appel Graph API, journal
    social_posts, cross-post Facebook/Threads best-effort. UN SEUL endroit à
    maintenir pour ces deux appelants — ne PAS dupliquer cette logique ailleurs.
    Ne flashe rien, ne redirige rien : renvoie {ok, error, title, terr_label,
    cross_done} et laisse l'appelant décider de la présentation."""
    from utils import social as social_mod, social_image, social_overlay, wp_media
    from utils import instagram_publish as ig
    event_id = ev["id"]
    title = (ev.get("title") or "")[:70]

    if not ig.configured(terr_label):
        return {"ok": False, "title": title, "terr_label": terr_label,
                "error": f"Compte Instagram non configuré pour « {terr_label} » — "
                         f"voir docs/RESEAUX_INSTAGRAM_SETUP.md."}

    # Priorité à la copie déjà hébergée dans NOTRE médiathèque WordPress (posée au
    # publish AS) plutôt qu'à l'image source d'origine : évite de retélécharger depuis
    # le site source à chaque publication Instagram, où certains sites bloquent le
    # téléchargement par un défi anti-robot (Cloudflare…) — notre copie n'a jamais ce
    # souci. Repli sur l'image source si l'événement n'a pas encore été publié sur AS.
    img_url = (ev.get("wp_raw_image_url_as") or "").strip() or event_image(ev)
    try:
        img_resp = requests.get(
            img_url, timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                   "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                     "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                     "Referer": f"{urlparse(img_url).scheme}://{urlparse(img_url).netloc}/"})
        # Cloudflare (et défenses anti-robot similaires) répond parfois 200 avec une
        # page de défi JS plutôt qu'un 403 franc — le Content-Type révèle le pot aux
        # roses. On distingue ce cas d'un simple lien cassé : un en-tête ne le
        # débloquera jamais, il faudrait un vrai navigateur (hors périmètre ici).
        cf_challenge = img_resp.headers.get("cf-mitigated", "") == "challenge"
        img_resp.raise_for_status()
        content_type = img_resp.headers.get("Content-Type", "").split(";")[0].strip()
        if not content_type.startswith("image/"):
            if cf_challenge:
                err = (f"« {title} » — le site source protège ses images par un défi "
                       "anti-robot Cloudflare : aucun en-tête ne peut le passer, il "
                       "faudrait un vrai navigateur. Choisis un autre événement pour "
                       "ce post, ou dépose la photo manuellement.")
            else:
                err = (f"« {title} » — l'URL de la photo n'a pas renvoyé une image "
                       f"(reçu : {content_type or 'inconnu'}). Source probablement "
                       "protégée contre le hotlinking, ou lien cassé.")
            return {"ok": False, "title": title, "terr_label": terr_label, "error": err}
        src = img_resp.content
    except requests.HTTPError as exc:
        cf = exc.response is not None and exc.response.headers.get("cf-mitigated") == "challenge"
        if cf:
            err = (f"« {title} » — le site source bloque avec un défi anti-robot "
                   "Cloudflare (aucun en-tête ne le contourne). Choisis un autre "
                   "événement pour ce post, ou dépose la photo manuellement.")
        else:
            err = f"« {title} » — photo source injoignable ({exc})."
        return {"ok": False, "title": title, "terr_label": terr_label, "error": err}
    except requests.RequestException as exc:
        return {"ok": False, "title": title, "terr_label": terr_label,
                "error": f"« {title} » — photo source injoignable ({exc})."}

    # Légende / texte alternatif : ceux édités à la main dans /reseaux si fournis,
    # sinon l'auto-généré. Composition (dont l'ajout du crédit image sans doublonner)
    # centralisée dans social_mod.finalize_caption — SOURCE DE VÉRITÉ unique partagée
    # avec scripts/ig_scheduler.py._publish.
    caption = social_mod.finalize_caption(ev, lang, caption_override or None)
    date_str = social_mod.format_date(ev.get("date_event_start", ""),
                                      ev.get("date_event_end", ""), lang)
    where = ", ".join(p for p in (ev.get("lieu"), ev.get("ville")) if p)
    alt = alt_override or social_mod.alt_text(ev, lang)
    # Mot-clé DM (commentaire → réponse privée) : édité à la main si fourni, sinon
    # auto-déduit du titre — PERSISTÉ (pas juste au moment du clic, le webhook devra
    # le relire n'importe quand plus tard).
    keyword = dm_keyword_override.strip().upper() or social_mod.dm_keyword(ev.get("title") or "")
    if keyword != (ev.get("dm_keyword") or ""):
        conn.execute("UPDATE events_raw SET dm_keyword=? WHERE id=?", (keyword, event_id))
        conn.commit()
    territoire = ev.get("territoire", "")
    ville = ev.get("ville", "")
    full_title = ev.get("title", "")
    try:
        if kind == "carousel":
            slide1 = social_overlay.compose(
                "carrousel-1", territoire, src, title=full_title, date_str=date_str, ville=ville)
            slides = social_image.carousel(
                src, title=full_title, date_str=date_str, where=where,
                territoire=territoire, ville=ville, slide1_override=slide1)
            urls = []
            for i, sl in enumerate(slides):
                url = wp_media.upload_bytes(
                    social_image.to_jpeg(sl), f"ig-{event_id}-{lang}-{i}.jpg", alt=alt)
                if not url:
                    raise RuntimeError("upload WordPress échoué")
                urls.append(url)
            result = ig.publish_carousel(terr_label, urls, caption, alt_text=alt)
            cross_url = urls[0] if urls else None
        elif kind == "story":
            img = social_overlay.compose(
                "story-9x16", territoire, src, title=full_title, date_str=date_str,
                where=where, ville=ville)
            if img is None:  # pas d'overlay pour ce territoire -> repli Pillow
                img = social_image.story(
                    src, title=full_title, date_str=date_str, territoire=territoire, ville=ville)
            url = wp_media.upload_bytes(
                social_image.to_jpeg(img), f"ig-{event_id}-{lang}-story.jpg", alt=alt)
            if not url:
                raise RuntimeError("upload WordPress échoué")
            result = ig.publish_story(terr_label, url)
            cross_url = url
        else:
            img = social_overlay.compose(
                "post-4x5", territoire, src, title=full_title, date_str=date_str,
                where=where, ville=ville)
            if img is None:  # pas d'overlay pour ce territoire -> repli Pillow
                img = social_image.single_post(
                    src, title=full_title, date_str=date_str, territoire=territoire, ville=ville)
            url = wp_media.upload_bytes(
                social_image.to_jpeg(img), f"ig-{event_id}-{lang}.jpg", alt=alt)
            if not url:
                raise RuntimeError("upload WordPress échoué")
            result = ig.publish_single(terr_label, url, caption, alt_text=alt)
            cross_url = url
    except Exception as exc:  # visuel/upload/API : jamais de 500, on journalise et informe
        result = {"ok": False, "error": str(exc)}
        cross_url = None

    conn.execute(
        "INSERT INTO social_posts (event_id, territoire_label, lang, kind, status, "
        "ig_media_id, error, platform) VALUES (?,?,?,?,?,?,?,?)",
        (event_id, terr_label, lang, kind, "ok" if result.get("ok") else "error",
         result.get("media_id"), result.get("error"), "instagram"))

    # Cross-post best-effort : « un contenu, 3 canaux » (cf. RESEAUX_SOCIAUX_PLAN §4).
    # Seulement pour le post simple, seulement si Instagram a réussi (même image, même
    # légende), et SEULEMENT si le territoire est configuré — jamais bloquant, jamais
    # d'échec Instagram à cause de Facebook/Threads.
    cross_done = []
    if result.get("ok") and kind == "single" and cross_url:
        from utils import facebook_publish as fb, threads_publish as th
        for platform_name, label, mod in (("facebook", "Facebook", fb),
                                          ("threads", "Threads", th)):
            if not mod.configured(terr_label):
                continue
            fn = mod.publish_photo if platform_name == "facebook" else mod.publish_single
            r = fn(terr_label, cross_url, caption)
            conn.execute(
                "INSERT INTO social_posts (event_id, territoire_label, lang, kind, "
                "status, ig_media_id, error, platform) VALUES (?,?,?,?,?,?,?,?)",
                (event_id, terr_label, lang, kind, "ok" if r.get("ok") else "error",
                 r.get("post_id") or r.get("media_id"), r.get("error"), platform_name))
            if r.get("ok"):
                cross_done.append(label)

    conn.commit()
    return {"ok": bool(result.get("ok")), "error": result.get("error"),
            "title": title, "terr_label": terr_label, "cross_done": cross_done}


@app.route("/reseaux/publish/<int:event_id>", methods=["POST"])
@require_auth
def reseaux_publish(event_id: int):
    """Génère le visuel (Pillow) + upload sur agendasabauda.eu + publie sur le compte
    Instagram du territoire. Nécessite IG_ACCOUNT_ID_<SLUG> / IG_TOKEN_<SLUG> pour ce
    territoire (cf. docs/RESEAUX_INSTAGRAM_SETUP.md) — sinon message clair, rien ne
    casse. Idempotent : republier exige une confirmation explicite (force=1). Un
    scheduled_at futur enregistre l'intention (ig_scheduled_posts) au lieu de publier
    tout de suite — c'est scripts/ig_scheduler.py (cron séparé) qui appellera alors
    _do_publish_instagram au bon moment, EXACTEMENT le même chemin qu'ici."""
    from utils import social as social_mod
    from utils import instagram_publish as ig
    lang = request.form.get("lang", "fr")
    kind = request.form.get("kind", "single")
    force = request.form.get("force") == "1"
    manual_mode = request.form.get("ig_manual_mode") == "1"
    scheduled_at = (request.form.get("scheduled_at", "") or "").strip()
    # Retour : l'écran Réseaux par défaut, ou la page d'origine (fiche/onglet 🚀).
    nxt = (request.form.get("next", "") or "").strip()
    conn = get_db()
    row = conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return "Événement introuvable", 404
    ev = dict(row)
    ev["_organizer_handle"] = organizers.confirmed_handle(conn, ev.get("organisateur") or "")
    terr_label = _couv_terr_group(ev.get("territoire"))
    title = (ev.get("title") or "")[:70]

    if not comp.is_complete(ev):
        conn.close()
        flash(f"⚠️ « {title} » incomplet — impossible à publier.", "err")
        return redirect(nxt or url_for("reseaux"))

    # Finition Instagram MANUELLE : musique/tag natif impossibles via l'API Graph, et
    # tout appel API publie immédiatement (pas de brouillon) — donc quand Franck coche
    # cette case, on n'appelle JAMAIS l'API. Ni compte configuré, ni génération/upload
    # de visuel requis ici : /preview propose légende + visuel source à copier/coller,
    # et /semaine relance tant que ce n'est pas marqué posté (cf. utils.semaine.tasks).
    if manual_mode:
        keyword = (request.form.get("dm_keyword", "") or "").strip().upper() \
            or social_mod.dm_keyword(ev.get("title") or "")
        conn.execute(
            "UPDATE events_raw SET ig_manual_mode=1, ig_manual_done_at=NULL, "
            "dm_keyword=? WHERE id=?", (keyword, event_id))
        conn.commit()
        conn.close()
        flash(f"📱 « {title} » mis de côté pour une publication manuelle — légende et "
              "visuel prêts sur la fiche, poste-le toi-même dans l'app Instagram.", "ok")
        return redirect(url_for("preview", event_id=event_id))

    if not ig.configured(terr_label):
        conn.close()
        flash(f"⚙️ Compte Instagram non configuré pour « {terr_label} » — "
              f"voir docs/RESEAUX_INSTAGRAM_SETUP.md.", "err")
        return redirect(nxt or url_for("reseaux"))
    if not force:
        already = conn.execute(
            "SELECT id FROM social_posts WHERE event_id=? AND lang=? AND kind=? "
            "AND status='ok'", (event_id, lang, kind)).fetchone()
        if already:
            conn.close()
            flash(f"↩️ « {title} » déjà publié — republie avec confirmation si voulu.", "err")
            return redirect(nxt or (url_for("reseaux") + f"#e{event_id}"))

    # Programmation : Meta n'offre aucune programmation native pour un outil tiers,
    # donc on garde nous-mêmes l'intention et un cron à nous (ig_scheduler.py)
    # appellera _do_publish_instagram au moment choisi — rien n'est publié ici.
    if scheduled_at:
        try:
            when = datetime.fromisoformat(scheduled_at)
        except ValueError:
            when = None
        if when and when > datetime.now():
            conn.execute(
                "INSERT INTO ig_scheduled_posts (event_id, territoire_label, lang, "
                "kind, scheduled_at, status) VALUES (?,?,?,?,?,'pending')",
                (event_id, terr_label, lang, kind, when.isoformat(timespec="minutes")))
            conn.commit()
            conn.close()
            flash(f"🗓️ « {title} » programmé pour le {when.strftime('%d/%m/%Y %H:%M')}.", "ok")
            return redirect(nxt or (url_for("reseaux") + f"#e{event_id}"))
        # Date invalide ou passée : on ignore silencieusement et on publie tout de
        # suite (mieux vaut publier que perdre le clic de Franck).

    result = _do_publish_instagram(
        ev, terr_label, lang, kind, conn,
        caption_override=(request.form.get("caption", "") or "").strip(),
        alt_override=(request.form.get("alt_text", "") or "").strip(),
        dm_keyword_override=(request.form.get("dm_keyword", "") or ""))
    conn.close()
    if result["ok"]:
        extra = f" + {', '.join(result['cross_done'])}" if result.get("cross_done") else ""
        flash(f"🚀 « {title} » publié sur Instagram ({terr_label}, {lang.upper()}){extra}.", "ok")
    else:
        flash(f"❌ Échec publication « {title} » : {result.get('error')}", "err")
    return redirect(nxt or (url_for("reseaux") + f"#e{event_id}"))


def _dm_keyword_matches(text: str, keyword: str) -> bool:
    """Comparaison tolérante aux accents/majuscules : le commentaire doit CONTENIR
    le mot-clé, pas lui être identique (ex. « trop hâte pour MONTROTTIER » matche)."""
    import unicodedata

    def _norm(s: str) -> str:
        n = unicodedata.normalize("NFKD", s or "")
        return "".join(c for c in n if not unicodedata.combining(c)).upper()

    keyword = _norm(keyword).strip()
    return bool(keyword) and keyword in _norm(text)


@app.route("/webhooks/instagram", methods=["GET", "POST"])
def webhook_instagram():
    """Réception des commentaires Instagram (Meta Webhooks) → réponse privée (DM)
    automatique quand le commentaire contient le mot-clé de l'événement (events_raw
    .dm_keyword). AUCUNE authentification back-office ici — c'est Meta qui appelle
    cette route, jamais un utilisateur connecté. Toujours répondre 200 à Meta (même
    en cas d'erreur de notre côté) pour éviter des retries en boucle.

    Prérequis .env : IG_WEBHOOK_VERIFY_TOKEN (choisi par nous, collé aussi dans la
    config webhook du dashboard Meta) + IG_APP_SECRET (secret de l'app Meta, pour
    vérifier la signature des requêtes entrantes — jamais traiter un payload non
    signé correctement, n'importe qui pourrait sinon déclencher de faux DM)."""
    if request.method == "GET":
        expected = os.getenv("IG_WEBHOOK_VERIFY_TOKEN", "")
        if (expected and request.args.get("hub.mode") == "subscribe"
                and request.args.get("hub.verify_token") == expected):
            return request.args.get("hub.challenge", ""), 200
        return "forbidden", 403

    raw = request.get_data()
    log.info("Webhook Instagram : requête POST reçue (%d octets).", len(raw))

    app_secret = os.getenv("IG_APP_SECRET", "")
    if app_secret:
        sig = request.headers.get("X-Hub-Signature-256", "")
        expected_sig = "sha256=" + hmac.new(app_secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, sig):
            log.warning("Webhook Instagram : signature invalide — ignoré.")
            return "", 200
    else:
        log.warning("Webhook Instagram : IG_APP_SECRET absent — signature NON vérifiée.")

    payload = request.get_json(silent=True) or {}
    log.info("Webhook Instagram : payload = %s", payload)
    from utils import instagram_publish as ig
    from utils import social as social_mod
    conn = get_db()
    for entry in payload.get("entry", []):
        ig_account_id = entry.get("id", "")
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            value = change.get("value") or {}
            comment_id = value.get("id", "")
            text = value.get("text", "") or ""
            media_id = (value.get("media") or {}).get("id", "")
            log.info("Webhook Instagram : commentaire %r (media=%s) sur compte %s",
                     text, media_id, ig_account_id)
            if not comment_id or not media_id:
                continue
            row = conn.execute(
                "SELECT event_id FROM social_posts WHERE ig_media_id=? AND status='ok' "
                "AND platform='instagram' LIMIT 1", (media_id,)).fetchone()
            if not row:
                log.info("Webhook Instagram : media_id %s introuvable dans social_posts — "
                         "aucun événement associé.", media_id)
                continue
            ev = conn.execute("SELECT * FROM events_raw WHERE id=?", (row["event_id"],)).fetchone()
            if not ev or not _dm_keyword_matches(text, ev["dm_keyword"] or ""):
                log.info("Webhook Instagram : commentaire %r ne matche pas le mot-clé %r "
                         "(événement %s).", text, ev["dm_keyword"] if ev else None, row["event_id"])
                continue
            territoire = ig.territoire_for_account_id(ig_account_id)
            if not territoire:
                log.warning("Webhook Instagram : compte IG %s non reconnu (aucun "
                           "IG_ACCOUNT_ID_<SLUG> correspondant).", ig_account_id)
                continue
            title = (ev["title"] or "").strip()
            link = (ev["wp_permalink_as"] or "").strip()
            msg = f"Salut 👋 Merci pour ton commentaire sur « {title} » !"
            if link:
                msg += " Toutes les infos juste en dessous 👇"
            result = ig.send_private_reply(territoire, comment_id, msg)
            if not result.get("ok"):
                log.warning("Webhook Instagram : DM échoué (commentaire %s, événement %s) : %s",
                           comment_id, ev["id"], result.get("error"))
            elif link and result.get("recipient_id"):
                # Second message, normal (pas une réponse privée) : de vrais boutons
                # cliquables tout de suite, contrairement au lien en texte brut qui
                # met un instant à devenir tapable côté Instagram.
                buttons = [("Voir l'événement", link)]
                gcal = social_mod.google_calendar_url(dict(ev))
                if gcal:
                    buttons.append(("Ajouter à mon agenda", gcal))
                btn = ig.send_link_buttons(territoire, result["recipient_id"], title, buttons)
                if not btn.get("ok"):
                    log.warning("Webhook Instagram : bouton lien échoué (commentaire %s, "
                               "événement %s) : %s", comment_id, ev["id"], btn.get("error"))
    conn.close()
    return "", 200


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
    wp_id, permalink, raw_url = publish_to_as(ev)
    if wp_id:
        conn.execute("UPDATE events_raw SET wp_post_id_as=?, wp_permalink_as=?, "
                     "wp_raw_image_url_as=?, published_as_date=datetime('now') WHERE id=?",
                     (wp_id, permalink, raw_url, event_id))
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
        wp_id, permalink, raw_url = publish_to_as(dict(event))
        if wp_id:
            conn.execute("""
            UPDATE events_raw SET statut='published_sub',
            published_as_date=datetime('now'), wp_post_id_as=?, wp_permalink_as=?,
            wp_raw_image_url_as=? WHERE id=?
            """, (wp_id, permalink, raw_url, event_id))
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
    elif action == "multi_lieux":
        # Festival itinérant / programme diffus sur plusieurs communes : lieu et ville
        # ne sont plus exigés. La fiche quitte « À compléter » (cf. completeness).
        conn.execute("UPDATE events_raw SET multi_lieux=1 WHERE id=?", (event_id,))
        conn.commit()
        flash(f"📍 « {title} » marqué multi-lieux — lieu/ville non requis.", "ok")
    elif action == "multi_lieux_off":
        conn.execute("UPDATE events_raw SET multi_lieux=0 WHERE id=?", (event_id,))
        conn.commit()
        flash(f"↩️ « {title} » n'est plus multi-lieux.", "ok")
    elif action == "worth_trip":
        conn.execute("UPDATE events_raw SET worth_trip=1 WHERE id=?", (event_id,))
        conn.commit()
        flash(f"🌟 « {title} » — « vaut le détour » : il pourra être posté sur les "
              "comptes des autres territoires.", "ok")
    elif action == "worth_trip_off":
        conn.execute("UPDATE events_raw SET worth_trip=0 WHERE id=?", (event_id,))
        conn.commit()
        flash(f"↩️ « {title} » n'est plus « vaut le détour ».", "ok")

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

    # Remplacement de l'image : possible même une fois l'événement complet (avant,
    # seul le flux « À compléter » le permettait). Si l'URL change, le point focal
    # de l'ANCIENNE image ne veut plus rien dire pour la nouvelle → repli sur le
    # centre/auto plutôt que d'appliquer un cadrage désormais hors-sujet.
    new_url = (request.form.get("url_image", "") or "").strip()
    old_url = (row["url_image"] or "").strip()
    image_changed = bool(new_url) and new_url != old_url
    if image_changed:
        fx, fy, mode = 0.5, 0.5, ""
        conn.execute(
            "UPDATE events_raw SET url_image=?, image_credit='', image_source='manual', "
            "card_focal_x=?, card_focal_y=?, card_mode=? WHERE id=?",
            (new_url, fx, fy, mode or None, event_id))
        log.info("Image remplacée à la main id=%d : %s", event_id, new_url[:80])
    else:
        conn.execute("UPDATE events_raw SET card_focal_x=?, card_focal_y=?, card_mode=? "
                     "WHERE id=?", (fx, fy, mode or None, event_id))
    conn.commit()
    ev = dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (event_id,)).fetchone())
    conn.close()
    log.info("Cadrage vignette id=%d : focal=(%.2f,%.2f) mode=%s", event_id, fx, fy,
             mode or "auto")
    label = {"": "auto", "cover": "recadrage", "letterbox": "affiche entière"}[mode]
    if image_changed:
        label = f"nouvelle image, {label}"
    if ev.get("wp_post_id_as"):
        wp_id, permalink, raw_url = publish_to_as(ev)
        if wp_id:
            conn2 = get_db()
            conn2.execute(
                "UPDATE events_raw SET wp_permalink_as=COALESCE(NULLIF(?,''), wp_permalink_as), "
                "wp_raw_image_url_as=COALESCE(NULLIF(?,''), wp_raw_image_url_as) WHERE id=?",
                (permalink, raw_url, event_id))
            conn2.commit()
            conn2.close()
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
