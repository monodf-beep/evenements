"""Tests de l'évaluateur LLM : bifurcation des scores et robustesse aux pannes API.

Les appels Anthropic sont entièrement remplacés (monkeypatch de evaluate_event) :
aucun réseau ni clé réelle requis. On vérifie le passage de statut en base.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import evaluator
from scripts.scraper_events import init_db


def _seed(path: Path, events: list[dict]) -> None:
    conn = sqlite3.connect(path)
    init_db(conn)
    for ev in events:
        conn.execute(
            "INSERT INTO events_raw (title, url_source, territoire, statut) "
            "VALUES (?, ?, ?, 'pending')",
            (ev["title"], ev["url_source"], ev.get("territoire", "Piemonte")),
        )
    conn.commit()
    conn.close()


def _row(path: Path, url: str) -> tuple:
    conn = sqlite3.connect(path)
    row = conn.execute(
        "SELECT statut, llm_score FROM events_raw WHERE url_source = ?", (url,)
    ).fetchone()
    conn.close()
    return row


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Base temporaire + clé API factice (la création du client ne fait pas de réseau)."""
    path = tmp_path / "events.db"
    monkeypatch.setattr(evaluator, "DB_PATH", path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    return path


def test_bifurcation_par_score(db, monkeypatch):
    """score≥7 → evaluated ; 4-6 → published_sub ; <4 → rejected ; JSON illisible → rejected."""
    _seed(db, [
        {"title": "Expo savante", "url_source": "u-9"},
        {"title": "Festival moyen", "url_source": "u-5"},
        {"title": "Boulevard", "url_source": "u-2"},
        {"title": "Réponse cassée", "url_source": "u-bad"},
    ])
    results = {
        "u-9": {"score": 9, "categorie": "EXPOSITIONS & PATRIMOINE", "justification": "j"},
        "u-5": {"score": 5, "categorie": "FESTIVALS", "justification": "j"},
        "u-2": {"score": 2, "categorie": "CRÉATION VIVANTE", "justification": "j"},
        "u-bad": None,  # pas de JSON exploitable
    }
    monkeypatch.setattr(evaluator, "evaluate_event",
                        lambda ev, client, model: results[ev["url_source"]])

    assert evaluator.main() == 0

    assert _row(db, "u-9")[0] == "evaluated"
    assert _row(db, "u-5")[0] == "published_sub"
    assert _row(db, "u-2")[0] == "rejected"
    assert _row(db, "u-bad")[0] == "rejected"
    assert _row(db, "u-9")[1] == 9  # le score est bien persisté


@pytest.mark.parametrize("score,statut", [
    (10, "evaluated"), (7, "evaluated"),       # seuil haut
    (6, "published_sub"), (4, "published_sub"), # seuil bas
    (3, "rejected"), (0, "rejected"),
])
def test_seuils_exacts(db, monkeypatch, score, statut):
    _seed(db, [{"title": f"s{score}", "url_source": "u"}])
    monkeypatch.setattr(evaluator, "evaluate_event",
        lambda ev, client, model: {"score": score, "categorie": "X", "justification": "j"})
    assert evaluator.main() == 0
    assert _row(db, "u")[0] == statut


def test_erreur_api_laisse_pending(db, monkeypatch):
    """Une panne API ne doit JAMAIS rejeter : l'événement reste pending (réévalué plus tard)."""
    _seed(db, [
        {"title": "premier", "url_source": "u-api"},
        {"title": "suivant", "url_source": "u-next"},
    ])
    monkeypatch.setattr(evaluator, "evaluate_event",
                        lambda ev, client, model: evaluator.API_ERROR)

    assert evaluator.main() == 0

    # l'événement en erreur reste pending et sans score
    assert _row(db, "u-api") == ("pending", None)
    # le batch s'interrompt sur erreur API : le suivant reste pending aussi
    assert _row(db, "u-next") == ("pending", None)
