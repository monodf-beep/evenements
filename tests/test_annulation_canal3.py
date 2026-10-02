#!/usr/bin/env python3
"""Fixture : canal 3 (docs/EVENEMENTS_ANNULES.md) — un marqueur d'annulation trouvé
sur la PROPRE page source d'un événement, relue par dates.py/venues.py.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau : `requests.get` est mocké
(`scripts.dates.requests.get`, seul point d'entrée réseau — `_robust_get` est
partagé par `fetch_event_dates` ET `fetch_event_venue`) ; `slack.notify` est mocké
pour ne rien poster, seulement compter les appels. `ANTHROPIC_API_KEY` est retirée
de l'environnement pour garantir qu'aucune passe LLM ne parte en réseau non plus.

Contrairement à `tests/test_annulation.py` (canal 2 : la fiche VISÉE et la fiche qui
PORTE le marqueur sont deux fiches différentes — un article de presse apparié par la
dédup), ici c'est LA MÊME fiche : sa propre page dit qu'elle est annulée/reportée.
On vérifie donc en plus que `annulation_fiche_visee_id` pointe vers SON PROPRE id.

Deux sections, chacune sur sa base jetable pour rester isolée :
  A. scripts.dates  — fetch_event_dates (passe JSON-LD/<time>) déclenche le signal,
     ET la datation normale continue de fonctionner (le signal est un AJOUT, jamais
     un blocage) ; pas de re-alerte tant que la fiche reste sélectionnée ;
     audit_annulations SANS MODIFICATION voit la suspicion et sait la résoudre
     (auto si la fiche visée — elle-même — était publiée et ne l'est plus plus,
     manuel sinon) ;
  B. scripts.venues — fetch_event_venue (passe JSON-LD location) : même mécanique,
     et l'extraction du lieu continue de fonctionner normalement.

Lancer : .venv/bin/python -m tests.test_annulation_canal3
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.pop("ANTHROPIC_API_KEY", None)  # jamais de passe LLM réseau dans ce test

from scripts.scraper_events import init_db  # noqa: E402
import scripts.dates as dates_mod  # noqa: E402
import scripts.venues as venues_mod  # noqa: E402
import scripts.audit_annulations as audit  # noqa: E402

alertes = []
dates_mod.slack.notify = lambda text, blocks=None: alertes.append(text) or True


class _FakeResp:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


def _fake_get(url, timeout=None, headers=None, allow_redirects=None):
    html = PAGES.get(url)
    if html is None:
        return _FakeResp("", status_code=404)
    return _FakeResp(html, status_code=200)


dates_mod.requests.get = _fake_get  # seul point d'entrée réseau (_robust_get)

echecs = 0


def _check(cond, ok_msg, ko_msg):
    global echecs
    if cond:
        print(f"OK    {ok_msg}")
    else:
        echecs += 1
        print(f"ÉCHEC : {ko_msg}")


def _page(startdate=None, location=None, marqueur=""):
    """Fabrique une page JSON-LD minimale, avec ou sans marqueur d'annulation
    dans le TEXTE VISIBLE (jamais dans un <script> — on vérifie ailleurs, par
    _sans_script, que ce dernier serait ignoré exprès)."""
    ld = {"@type": "Event", "name": "Test"}
    if startdate:
        ld["startDate"] = startdate
    if location:
        ld["location"] = location
    import json as _json
    return (f'<html><head><script type="application/ld+json">'
            f'{_json.dumps(ld)}</script></head><body>'
            f'<h1>Titre de la page</h1>'
            f'<p>{marqueur}</p>'
            f'<p>Un paragraphe de contenu quelconque.</p>'
            f'</body></html>')


# ══════════════════════ A. scripts.dates — fetch_event_dates ══════════════════════
print("──── A. dates.py : fetch_event_dates relit la page, marqueur détecté ────")

tmp_a = Path(tempfile.mkdtemp()) / "fixture_a.db"
os.environ["DB_PATH"] = str(tmp_a)
dates_mod.DB_PATH = tmp_a
audit.DB_PATH = tmp_a

PAGES = {
    "https://exemple.fr/cimes": _page(startdate="2026-09-10",
                                      marqueur="ANNULÉ : cet événement n'aura pas lieu."),
    "https://exemple.fr/saveurs": _page(startdate="2026-09-15"),  # aucun marqueur
    "https://exemple.fr/musique": _page(startdate="2026-10-01",
                                        marqueur="Concert rinviato a data da destinarsi."),
}

conn = sqlite3.connect(tmp_a)
init_db(conn)
FICHES_A = [
    # id, titre, url, statut, wp_post_id_as
    (1, "Festival des Cimes", "https://exemple.fr/cimes", "pending", None),
    (2, "Marché des Saveurs", "https://exemple.fr/saveurs", "pending", None),
    (3, "Nuits de la Musique", "https://exemple.fr/musique", "published_sub", 901),
]
for eid, titre, url, statut, wp in FICHES_A:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, territoire, "
        "statut, source_type, wp_post_id_as) VALUES (?,?,?,?,?,?,?,?)",
        (eid, titre, "matière quelconque, sans date dedans", url, "Savoie", statut,
         "officielle", wp))
conn.commit()
conn.close()


def _row_a(eid):
    conn = sqlite3.connect(tmp_a); conn.row_factory = sqlite3.Row
    r = dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())
    conn.close()
    return r


rc = dates_mod.main(["--no-llm"])
_check(rc == 0, "dates.main() rend 0", f"code retour {rc}")

f1, f2, f3 = _row_a(1), _row_a(2), _row_a(3)

# Le signal est un AJOUT : la datation normale doit avoir fonctionné pour LES TROIS,
# marqueur présent ou non — rien n'est bloqué par la détection canal 3.
_check(f1["date_event_start"] == "2026-09-10" and f2["date_event_start"] == "2026-09-15"
      and f3["date_event_start"] == "2026-10-01",
      "les trois fiches sont datées normalement (marqueur ou non, rien de bloqué)",
      f"dates : f1={f1['date_event_start']} f2={f2['date_event_start']} f3={f3['date_event_start']}")

_check(len(alertes) == 2, f"2 alertes envoyées (fiches 1 et 3, pas 2) : {len(alertes)}",
      f"{len(alertes)} alerte(s) : {alertes}")

_check(bool(f1.get("annulation_detectee_at")) and f1.get("annulation_fiche_visee_id") == 1
      and f1.get("annulation_visee_etait_publiee") == 0,
      "fiche 1 (pas publiée) : suspicion posée, visée = ELLE-MÊME, « n'était pas publiée »",
      f"f1 : detectee={f1.get('annulation_detectee_at')} visee={f1.get('annulation_fiche_visee_id')} "
      f"etait_publiee={f1.get('annulation_visee_etait_publiee')}")

_check(not f2.get("annulation_detectee_at"),
      "fiche 2 (pas de marqueur) : aucune suspicion posée",
      f"f2 a une suspicion alors qu'elle n'a pas de marqueur : {f2.get('annulation_detectee_at')}")

_check(bool(f3.get("annulation_detectee_at")) and f3.get("annulation_fiche_visee_id") == 3
      and f3.get("annulation_visee_etait_publiee") == 1,
      "fiche 3 (déjà publiée, WP#901) : suspicion posée, visée = ELLE-MÊME, « était publiée »",
      f"f3 : detectee={f3.get('annulation_detectee_at')} visee={f3.get('annulation_fiche_visee_id')} "
      f"etait_publiee={f3.get('annulation_visee_etait_publiee')}")

print("\n──── A. deuxième passage : les 3 fiches sont déjà datées (date_source='page'), "
     "donc plus jamais resélectionnées par la passe page — silence attendu ────")
alertes.clear()
rc2 = dates_mod.main(["--no-llm"])
f1b, f3b = _row_a(1), _row_a(3)
_check(not alertes and f1b["annulation_detectee_at"] == f1["annulation_detectee_at"]
      and f3b["annulation_detectee_at"] == f3["annulation_detectee_at"],
      "silence : aucune fiche re-fetchée (déjà datées), donc aucune re-détection possible",
      f"alertes={alertes}")

print("\n──── A. la garde anti-spam elle-même : si la page était re-fetchée avec le "
     "même marqueur (cas réel : réarmement après cooldown), pas de 2e alerte ────")
conn = sqlite3.connect(tmp_a); conn.row_factory = sqlite3.Row
conn2 = sqlite3.connect(tmp_a)
ev1 = dict(conn.execute("SELECT * FROM events_raw WHERE id=1").fetchone())
marqueur = dates_mod.signale_annulation_page(
    conn2, ev1, "ANNULÉ : cet événement n'aura pas lieu.", source="test direct")
conn.close(); conn2.close()
_check(marqueur is None and len(alertes) == 0,
      "signale_annulation_page() se tait : annulation_detectee_at déjà posé",
      f"marqueur={marqueur} alertes={alertes}")

print("\n──── A. audit_annulations voit la suspicion SANS AUCUNE modification du script ────")
import io, logging
buf = io.StringIO()
h = logging.StreamHandler(buf); h.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger("audit-annulations").addHandler(h)
audit.main([])
sortie = buf.getvalue()
_check("2 suspicion(s) au total" in sortie and "2 encore EN ATTENTE" in sortie,
      "audit : 2 suspicions au total, 2 encore en attente (rien publié n'a bougé)",
      f"sortie inattendue :\n{sortie}")

print("\n──── A. fiche 3 dépubliée (Franck) → résolution AUTOMATIQUE (comme le canal 2) ────")
conn = sqlite3.connect(tmp_a)
conn.execute("UPDATE events_raw SET wp_post_id_as=NULL WHERE id=3")
conn.commit()
conn.close()
buf.truncate(0); buf.seek(0)
audit.main([])
sortie = buf.getvalue()
_check("1 résolue(s) automatiquement" in sortie and "1 encore EN ATTENTE" in sortie
      and "suspect [1]" in sortie and "suspect [3]" not in sortie,
      "audit : fiche 3 résolue automatiquement (dépubliée), fiche 1 encore en attente",
      f"sortie :\n{sortie}")

print("\n──── A. --resolu : clôture manuelle de la fiche 1 (jamais publiée) ────")
audit.main(["--resolu", "1"])
f1c = _row_a(1)
_check(not f1c.get("annulation_detectee_at"), "fiche 1 : suspicion clôturée manuellement",
      f"toujours active : {f1c.get('annulation_detectee_at')}")


# ══════════════════════ B. scripts.venues — fetch_event_venue ══════════════════════
print("\n──── B. venues.py : fetch_event_venue relit la page, marqueur détecté ────")

tmp_b = Path(tempfile.mkdtemp()) / "fixture_b.db"
os.environ["DB_PATH"] = str(tmp_b)
venues_mod.DB_PATH = tmp_b
audit.DB_PATH = tmp_b

PAGES.clear()
PAGES["https://exemple.fr/expo-alpine"] = _page(
    location={"name": "Musée de l'Alpe", "address": {"addressLocality": "Chambéry"}},
    marqueur="Exposition POSTPONED until further notice.")
PAGES["https://exemple.fr/expo-glaciers"] = _page(
    location={"name": "Espace Glaciers", "address": {"addressLocality": "Annecy"}})

conn = sqlite3.connect(tmp_b)
init_db(conn)
FICHES_B = [
    (4, "Exposition Alpine", "https://exemple.fr/expo-alpine", "pending", None),
    (5, "Exposition des Glaciers", "https://exemple.fr/expo-glaciers", "pending", None),
]
for eid, titre, url, statut, wp in FICHES_B:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, territoire, "
        "statut, source_type, wp_post_id_as) VALUES (?,?,?,?,?,?,?,?)",
        (eid, titre, "matière quelconque", url, "Savoie", statut, "officielle", wp))
conn.commit()
conn.close()


def _row_b(eid):
    conn = sqlite3.connect(tmp_b); conn.row_factory = sqlite3.Row
    r = dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())
    conn.close()
    return r


alertes.clear()
rc_b = venues_mod.main(["--no-llm"])
_check(rc_b == 0, "venues.main() rend 0", f"code retour {rc_b}")

f4, f5 = _row_b(4), _row_b(5)
_check(f4["lieu"] == "Musée de l'Alpe" and f4["ville"] == "Chambéry"
      and f5["lieu"] == "Espace Glaciers" and f5["ville"] == "Annecy",
      "les deux fiches ont leur lieu/ville normalement extraits (rien de bloqué)",
      f"f4=({f4['lieu']!r},{f4['ville']!r}) f5=({f5['lieu']!r},{f5['ville']!r})")

_check(len(alertes) == 1, f"1 alerte envoyée (fiche 4 seulement) : {len(alertes)}",
      f"{len(alertes)} alerte(s) : {alertes}")

_check(bool(f4.get("annulation_detectee_at")) and f4.get("annulation_fiche_visee_id") == 4
      and f4.get("annulation_visee_etait_publiee") == 0,
      "fiche 4 : suspicion posée, visée = ELLE-MÊME",
      f"f4 : detectee={f4.get('annulation_detectee_at')} visee={f4.get('annulation_fiche_visee_id')}")
_check(not f5.get("annulation_detectee_at"), "fiche 5 (pas de marqueur) : rien posé",
      f"f5 a une suspicion : {f5.get('annulation_detectee_at')}")

print("\n──── B. deuxième passage : lieu déjà trouvé → plus jamais resélectionnée, silence ────")
alertes.clear()
venues_mod.main(["--no-llm"])
f4b = _row_b(4)
_check(not alertes and f4b["annulation_detectee_at"] == f4["annulation_detectee_at"],
      "silence : fiche 4 non re-fetchée (lieu déjà rempli)", f"alertes={alertes}")

print("\n──── B. audit_annulations voit aussi la suspicion venue de venues.py, sans "
     "aucune modification du script (mêmes colonnes que le canal 2) ────")
buf.truncate(0); buf.seek(0)
audit.main([])
sortie = buf.getvalue()
_check("1 suspicion(s) au total" in sortie and "1 encore EN ATTENTE" in sortie
      and "suspect [4]" in sortie,
      "audit : la suspicion posée par venues.py est bien visible et en attente",
      f"sortie :\n{sortie}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
