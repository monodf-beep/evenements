#!/usr/bin/env python3
"""Backoffice de validation des événements — interface Franck.

Auth HTTP Basic. Design minimaliste fonctionnel.
- /            : dashboard (KPIs, coûts API, répartitions, sources, newsletters)
- /validation  : file des événements à valider (score ≥ 7)
- /action/...  : Publier CS / Subdomain / Rejeter

Lance avec : gunicorn -w 1 -b 127.0.0.1:5001 'app.app:app'
"""
from __future__ import annotations
import os
import sqlite3
import sys
from collections import Counter
from functools import wraps
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for
from flask import Response

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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
STATUS_LABELS = {
    "pending": "En attente",
    "evaluated": "À valider",
    "published_cs": "Publié CS",
    "published_sub": "Site dédié",
    "rejected": "Rejeté",
}

app = Flask(__name__, template_folder="templates")


def check_auth(username, password):
    return (username == os.getenv("BACKOFFICE_USER", "admin")
            and password == os.getenv("BACKOFFICE_PASSWORD", ""))


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response("Accès refusé", 401,
                            {"WWW-Authenticate": 'Basic realm="Backoffice"'})
        return f(*args, **kwargs)
    return decorated


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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

    return render_template(
        "dashboard.html",
        total=total, to_validate=to_validate,
        status_counts=status_counts, status_labels=STATUS_LABELS,
        terr_counts=terr_counts, cat_counts=cat_counts,
        territories=TERRITORIES,
        cost=cost, alert=usage.get_alert(),
        src_counts=src_counts, src_total=sum(src_counts.values()),
        newsletters=newsletters, nl_active=nl_active,
    )


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
    return render_template("index.html", events=events, alert=usage.get_alert())


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
    return redirect(url_for("validation"))


if __name__ == "__main__":
    app.run(debug=False, port=5001)
