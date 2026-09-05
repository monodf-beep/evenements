#!/usr/bin/env python3
"""Fixture : un SEO calculé mais jamais arrivé sur le site DOIT repasser au run suivant.

INCIDENT RÉEL, 2026-08-10, conséquence directe de la panne du 8 au 10 août : WordPress
répondait 500 à tout, mais le cron SEO de 10h30 tournait quand même. L'appel LLM
(Anthropic, indépendant du site) réussissait → `seo_at` écrit ; la republication
échouait → Yoast ne recevait rien. Or `_select` écarte tout ce qui a `seo_at IS NOT
NULL` : ces fiches portaient un SEO que le site n'a jamais vu, et RIEN ne les repêchait.
Le cul-de-sac de la règle 3, fabriqué par une panne au lieu d'un refus.

Ce que la fixture doit prouver — et pas seulement que le code s'exécute :
  1. la fiche restée en arrière est bien REPRISE (le rouvreur existe) ;
  2. une fiche dont la republication a RÉUSSI n'est PAS reprise (sinon on republie tout,
     tous les jours — un rouvreur qui ne se referme jamais est un autre défaut) ;
  3. le passage suivant, après un échec, la reprend ENCORE (le run échoué ne referme
     rien par erreur) ;
  4. le rattrapage initial ne réveille pas toute la base : les fiches publiées APRÈS
     leur calcul SEO sont marquées comme déjà poussées ;
  5. règle 5 : un événement PASSÉ n'est pas repris — le réparer ne sert personne.

⚠️ Aucun réseau : publish_batch_as.main est monkey-patché.

Lancer : .venv/bin/python -m tests.test_seo_push_retard
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db  # noqa: E402
import scripts.seo_batch as sb  # noqa: E402

sb.DB_PATH = tmp

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


AUJOURDHUI = "2026-08-10"
conn = sqlite3.connect(tmp)
init_db(conn)

# id 1 — SEO calculé le 9, dernière publication réussie le 6 : le trajet n'a pas eu lieu.
# id 2 — SEO calculé le 9, publiée le 9 juste après : arrivée sur le site, rien à faire.
# id 3 — même retard que 1, mais l'événement est PASSÉ (règle 5) : on n'y touche pas.
# id 4 — jamais publiée sur WP (wp_post_id_as vide) : rien à repousser.
CAS = [
    (1, "Retard", "2026-08-09 10:30:00", "2026-08-06 09:30:00", 900, "2026-12-01"),
    (2, "Arrivée", "2026-08-09 10:30:00", "2026-08-09 10:30:12", 901, "2026-12-02"),
    (3, "Passée", "2026-08-09 10:30:00", "2026-08-06 09:30:00", 902, "2026-07-01"),
    (4, "Hors ligne", "2026-08-09 10:30:00", None, None, "2026-12-03"),
]
for eid, titre, seo_at, pub, wp, fin in CAS:
    conn.execute(
        "INSERT INTO events_raw (id, title, url_source, statut, llm_score, seo_at, "
        "published_as_date, wp_post_id_as, date_event_start, date_event_end) "
        "VALUES (?,?,?,'published_cs',8,?,?,?,?,?)",
        (eid, titre, f"https://x/{eid}", seo_at, pub, wp, fin, fin))
conn.commit()

# ── 1. Rattrapage initial : seul le vrai retard reste non marqué ────────────────
print("──── création de seo_pushed_at + rattrapage initial ────")
sb._ensure_seo_pushed_col(conn)
marques = {r[0]: r[1] for r in conn.execute(
    "SELECT id, seo_pushed_at FROM events_raw")}
_check("id 2 (publiée après son SEO) marquée comme déjà poussée",
       marques[2] == "2026-08-09 10:30:00", repr(marques[2]))
_check("id 1 (publiée avant son SEO) laissée en retard", marques[1] is None, repr(marques[1]))
_check("id 4 (jamais publiée) laissée en retard", marques[4] is None, repr(marques[4]))

# ── 2. Sélection du retard ──────────────────────────────────────────────────────
print("\n──── _a_repousser ────")
retard = sb._a_repousser(conn, AUJOURDHUI, 20)
_check("id 1 repris", 1 in retard, str(retard))
_check("id 2 NON repris (son SEO est arrivé)", 2 not in retard, str(retard))
_check("id 3 NON repris (événement passé — règle 5)", 3 not in retard, str(retard))
_check("id 4 NON repris (pas de post WordPress à republier)", 4 not in retard, str(retard))
conn.close()

# ── 3. Le run complet : une republication qui ÉCHOUE ne referme rien ────────────
print("\n──── run avec republication en échec : la fiche doit rester en file ────")
import scripts.publish_batch_as as pba  # noqa: E402
from utils import slack, pipeline_status  # noqa: E402

messages = []
slack.notify = lambda m, *a, **k: messages.append(m)
pipeline_status.record_run = lambda *a, **k: None
sb.date = type("D", (), {"today": staticmethod(lambda: type("d", (), {
    "isoformat": staticmethod(lambda: AUJOURDHUI)})())})


def _publish_echoue(argv):
    """Le site est en 500 : publish_batch_as n'écrit RIEN (published_as_date inchangé)."""
    return 1


pba.main = _publish_echoue
sb.os.environ["ANTHROPIC_API_KEY"] = ""      # aucun appel LLM dans ce test
sys.modules["scripts.publish_batch_as"].main = _publish_echoue

code = sb.main(["--cap", "0"])
conn = sqlite3.connect(tmp)
_check("id 1 toujours en retard après l'échec",
       conn.execute("SELECT seo_pushed_at FROM events_raw WHERE id=1").fetchone()[0] is None)
_check("le bilan Slack annonce le retard restant",
       any("le site n'a pas reçu" in m for m in messages), str(messages))
# Une alerte qui ne dit pas quoi faire ne sert à rien : elle doit nommer la fiche ET
# donner la commande qui en explique la rétention.
_check("l'alerte nomme la fiche et la commande à taper",
       any("--ids 1 " in m and "publish_batch_as" in m for m in messages), str(messages))
conn.close()

# ── 4. Le run suivant, republication RÉUSSIE : la fiche sort de la file ─────────
print("\n──── run avec republication réussie : la fiche sort de la file ────")
messages.clear()


def _publish_reussit(argv):
    ids = [int(a) for a in argv[argv.index("--ids") + 1:] if a.isdigit()]
    c = sqlite3.connect(tmp)
    for i in ids:
        c.execute("UPDATE events_raw SET published_as_date='2026-08-10 11:00:00' WHERE id=?", (i,))
    c.commit()
    c.close()
    return 0


sys.modules["scripts.publish_batch_as"].main = _publish_reussit
sb.main(["--cap", "0"])
conn = sqlite3.connect(tmp)
_check("id 1 marquée poussée (seo_pushed_at = seo_at)",
       conn.execute("SELECT seo_pushed_at FROM events_raw WHERE id=1").fetchone()[0]
       == "2026-08-09 10:30:00")
_check("plus aucun retard à signaler", not any("toujours pas reçu" in m for m in messages),
       str(messages))
_check("id 1 ne ressort plus de _a_repousser",
       1 not in sb._a_repousser(conn, AUJOURDHUI, 20))
conn.close()

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
