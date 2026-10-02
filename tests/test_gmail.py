"""Tests du collecteur Gmail : mapping territoire, parsing d'un mail, extraction
LLM (mockée) et insertion/déduplication. Aucun réseau ni compte Gmail requis.
"""
from __future__ import annotations

import base64
import sqlite3
import sys
from pathlib import Path

import anthropic
# LE CLIENT HTTP DU SDK ANTHROPIC A CHANGÉ DE NOM, et ce fichier l'importait en dur.
#
# Trouvé le 2026-09-29 en cherchant pourquoi la suite refusait de passer au vert :
# `anthropic` 1.x embarque `httpx2` et non plus `httpx` — sa propre signature le dit
# (`APIConnectionError(*, message: str, request: httpx2.Request)`), et `httpx` n'est
# ni dans requirements.txt ni tiré par le SDK. Cet import échouait donc AVANT celui de
# `pytest`, et c'est ça qui coûtait cher : `tests/run_all.py` sait tolérer l'absence
# d'un LANCEUR de tests (« non exécutable ici »), pas celle d'une bibliothèque. La
# fixture comptait donc ROUGE, et `scripts/auto_deploiement` refuse de déployer sur une
# suite rouge — un déploiement autonome bloqué par un renommage chez un fournisseur.
#
# On prend celui qui est là, plutôt que d'épingler un nom qui rebougera : la requête ne
# sert ici qu'à remplir l'argument obligatoire d'une exception fabriquée pour le test.
try:
    import httpx
except ModuleNotFoundError:            # SDK anthropic >= 1.x
    import httpx2 as httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import gmail_collect as gc
from scripts.scraper_events import init_db


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii")


class _Msg:
    def __init__(self, text):
        self.content = [type("C", (), {"text": text})()]
        self.usage = None


class _Client:
    """Faux client Anthropic : renvoie un texte fixe ou lève une exception."""
    def __init__(self, text=None, exc=None):
        self._text, self._exc = text, exc
        self.messages = self

    def create(self, **kwargs):
        if self._exc:
            raise self._exc
        return _Msg(self._text)


# --------------------------------------------------------------------------- #
def test_match_territory():
    wl = gc.load_whitelist()
    assert gc.match_territory("Salone <comunicazione@email.salonelibro.it>", wl) == "Piemonte"
    assert gc.match_territory("TNN <billetterie@tnn.fr>", wl) == "Nice"
    assert gc.match_territory("Bonlieu <info@bonlieu-annecy.com>", wl) == "Savoie"
    assert gc.match_territory("inconnu@example.org", wl) == ""


def test_parse_message():
    msg = {
        "id": "abc123",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "Salone <comunicazione@email.salonelibro.it>"},
                {"name": "Subject", "value": "Programma di giugno"},
                {"name": "Date", "value": "Mon, 30 Jun 2026 10:00:00 +0200"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64("Conferenza di Recalcati il 5 luglio")}},
                {"mimeType": "text/html", "body": {"data": _b64('<p>Conferenza <img src="https://x/p.jpg"></p>')}},
            ],
        },
    }
    email = gc.parse_message(msg)
    assert email["message_id"] == "abc123"
    assert "salonelibro.it" in email["sender"]
    assert email["subject"] == "Programma di giugno"
    assert email["body"].startswith("Conferenza") and "Recalcati" in email["body"]
    assert email["image"] == "https://x/p.jpg"


def test_extract_events_ok():
    client = _Client(text='Voici : [{"titre":"Concerto","date_start":"2026-07-05","url":"https://ev/1"}]')
    out = gc.extract_events({"sender": "x", "subject": "s", "body": "b"}, client, "m")
    assert isinstance(out, list) and out[0]["titre"] == "Concerto"


def test_extract_events_no_json_returns_empty():
    client = _Client(text="Pas d'événement cette semaine.")
    assert gc.extract_events({"sender": "x", "subject": "s", "body": "b"}, client, "m") == []


def test_extract_events_api_error_returns_sentinel():
    exc = anthropic.APIConnectionError(message="boom", request=httpx.Request("POST", "http://x"))
    client = _Client(exc=exc)
    assert gc.extract_events({"sender": "x", "subject": "s", "body": "b"}, client, "m") is gc.API_ERROR


def test_insert_events_and_dedup(tmp_path):
    conn = sqlite3.connect(tmp_path / "e.db")
    init_db(conn)
    email = {"message_id": "abc", "image": "https://img", "sender": "comunicazione@email.salonelibro.it"}
    events = [
        {"titre": "Concerto", "date_start": "2026-07-05", "lieu": "Auditorium", "ville": "Torino",
         "description": "desc", "url": "https://ev/1"},
        {"titre": "", "url": "https://ev/2"},          # sans titre → ignoré
        {"titre": "Mostra", "url": ""},                # sans url → url_source synthétique
    ]
    n = gc.insert_events(conn, events, email, "Piemonte")
    assert n == 2
    row = conn.execute("SELECT territoire, statut, source_name FROM events_raw WHERE url_source='https://ev/1'").fetchone()
    assert row == ("Piemonte", "pending", "comunicazione@email.salonelibro.it")
    assert conn.execute("SELECT 1 FROM events_raw WHERE url_source='gmail:abc#2'").fetchone() is not None
    # 2e passage : déduplication stricte → 0 inséré
    assert gc.insert_events(conn, events, email, "Piemonte") == 0
    conn.close()


def test_seen_table(tmp_path):
    conn = sqlite3.connect(tmp_path / "e.db")
    gc.ensure_seen_table(conn)
    assert gc.already_seen(conn, "m1") is False
    gc.mark_seen(conn, "m1"); conn.commit()
    assert gc.already_seen(conn, "m1") is True
    conn.close()
