#!/usr/bin/env python3
"""Backoffice de validation des événements — interface Franck.

Auth HTTP Basic. Design minimaliste fonctionnel (pas de CSS élaboré).
Lance avec : gunicorn -w 1 -b 127.0.0.1:5001 'app.app:app'
"""
from __future__ import annotations
import os
import sqlite3
import sys
from functools import wraps
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for
from flask import Response

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publisher import publish_to_cs
from utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
log = get_logger("backoffice")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

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


@app.route("/")
@require_auth
def index():
    conn = get_db()
    events = conn.execute("""
        SELECT * FROM events_raw
        WHERE statut = 'evaluated' AND llm_score >= 7
        ORDER BY llm_score DESC, scrape_date DESC
    """).fetchall()
    conn.close()
    return render_template("index.html", events=events)


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
    return redirect(url_for("index"))


@app.route("/stats")
@require_auth
def stats():
    conn = get_db()
    counts = conn.execute("""
        SELECT statut, COUNT(*) as n FROM events_raw GROUP BY statut
    """).fetchall()
    conn.close()
    return render_template("stats.html", counts=counts)


if __name__ == "__main__":
    app.run(debug=False, port=5001)
