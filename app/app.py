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
import json
import os
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import re

from scripts.publisher import publish_to_cs
from scripts.scraper_events import load_sources, init_db
from utils.logger import get_logger
from utils import usage
from utils.sources import pick_image, load_territory_images
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
    "published_cs": "Publié CS",
    "published_sub": "Site dédié",
    "rejected": "Rejeté",
}

app = Flask(__name__, template_folder="templates")
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


_TERRITORY_IMAGES = load_territory_images()


def event_image(ev: dict) -> str:
    """Image de l'événement, ou bannière de substitution par territoire."""
    return ev.get("url_image") or pick_image(
        ev.get("territoire", ""), str(ev.get("id", "")), _TERRITORY_IMAGES)


def clean_html(text: str) -> str:
    """Retire les balises HTML pour un aperçu texte propre."""
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", text or "")).strip()


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


# --------------------------------------------------------------------------- #
# Lancement manuel des étapes du pipeline (boutons du dashboard)
# --------------------------------------------------------------------------- #
TASKS = {
    "scrape":   {"script": "scripts/scraper_events.py", "label": "Scraping RSS", "icon": "📡", "cost": False},
    "gmail":    {"script": "scripts/gmail_collect.py",   "label": "Newsletters Gmail", "icon": "📬", "cost": True},
    "evaluate": {"script": "scripts/evaluator.py",       "label": "Évaluation LLM", "icon": "🧠", "cost": True},
}
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


def launch_task(task: str) -> tuple[bool, str]:
    """Lance un script du pipeline en arrière-plan (non bloquant)."""
    if _running_state().get(task):
        return False, "déjà en cours"
    script = ROOT / TASKS[task]["script"]
    logf = ROOT / "logs" / f"run_{task}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    fh = open(logf, "ab")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script)], cwd=str(ROOT),
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
    conn.close()

    total = sum(status_counts.values())
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

    return render_template(
        "dashboard.html",
        total=total, to_validate=to_validate,
        status_counts=status_counts, status_labels=STATUS_LABELS,
        terr_counts=terr_counts, cat_counts=cat_counts,
        territories=TERRITORIES,
        cost=cost, alert=friendly_alert(),
        src_counts=src_counts, src_total=sum(src_counts.values()),
        newsletters=newsletters, nl_active=nl_active,
        tasks=tasks, any_running=any_running,
    )


@app.route("/run/<task>", methods=["POST"])
@require_auth
def run_task(task: str):
    if task not in TASKS:
        return "Tâche inconnue", 404
    ok, msg = launch_task(task)
    log.info("Lancement manuel '%s' : %s", task, msg)
    return redirect(url_for("dashboard"))


@app.route("/validation")
@require_auth
def validation():
    conn = get_db()
    events = conn.execute("""
        SELECT * FROM events_raw
        WHERE statut = 'evaluated' AND llm_score >= 7
        ORDER BY llm_score DESC, scrape_date DESC
    """).fetchall()
    conn.close()
    return render_template("index.html", events=events, alert=friendly_alert())


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
    return render_template("preview.html", e=ev, image=event_image(ev))


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
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    where, params = [], []
    if statut:
        where.append("statut = ?"); params.append(statut)
    if terr:
        where.append("territoire = ?"); params.append(terr)
    if q:
        where.append("title LIKE ?"); params.append(f"%{q}%")
    wsql = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) n FROM events_raw {wsql}", params).fetchone()["n"]
    rows = conn.execute(
        f"SELECT * FROM events_raw {wsql} ORDER BY scrape_date DESC, id DESC LIMIT ? OFFSET ?",
        params + [PAGE_SIZE, (page - 1) * PAGE_SIZE]).fetchall()
    statut_counts = {r["statut"]: r["n"] for r in conn.execute(
        "SELECT statut, COUNT(*) n FROM events_raw GROUP BY statut")}
    conn.close()

    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return render_template(
        "events.html", events=[dict(r) for r in rows],
        statut=statut, territoire=terr, q=q, page=page, pages=pages, total=total,
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

    if action == "publish_cs":
        wp_id = publish_to_cs(dict(event))
        if wp_id:
            conn.execute("""
            UPDATE events_raw SET statut='published_cs',
            published_cs_date=datetime('now'), wp_post_id_cs=? WHERE id=?
            """, (wp_id, event_id))
            conn.commit()
            log.info("Publié CS : event_id=%d wp_id=%d", event_id, wp_id)
    elif action == "subdomain":
        conn.execute(
            "UPDATE events_raw SET statut='published_sub' WHERE id=?",
            (event_id,)
        )
        conn.commit()
    elif action == "reject":
        conn.execute(
            "UPDATE events_raw SET statut='rejected' WHERE id=?",
            (event_id,)
        )
        conn.commit()

    conn.close()
    nxt = request.form.get("next", "")
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = url_for("validation")
    return redirect(nxt)


if __name__ == "__main__":
    app.run(debug=False, port=5001)
