#!/usr/bin/env python3
"""Fixture : un plafond API en cours d'audit visuel n'efface AUCUN signalement actif
et n'audite AUCUNE planche restante — au lieu de rendre une liste vide interprétée
comme « tout est OK ».

TROUVÉ le 2026-08-05 en balayant les points d'appel LLM après l'incident du
2026-08-04 (utils/api_limite.py). `scripts.image_audit.judge_grid` attrapait TOUTE
exception (`except Exception`) et rendait `[]` — « rien à signaler ». Or
`_persist_flags` traite toute fiche AUDITÉE mais NI signalée NI en échec de
téléchargement comme REJUGÉE OK, et referme son flag actif (`resolved_at=now`). Sous
plafond, `main()` passait `[r["id"] for r in rows]` — TOUT le catalogue sélectionné,
pas seulement les planches réellement jugées — à `_persist_flags` : un plafond
aurait donc effacé silencieusement les signalements de photos DÉJÀ identifiées comme
hors-sujet, sans qu'aucune ait été rejugée. Pire que le martèlement trouvé ailleurs
le même jour : ici, un plafond PRODUIT un faux verdict positif, pas seulement du bruit.

⚠️ BASE JETABLE, aucun appel réseau réel : `build_grid` est monkey-patché (pas de
téléchargement d'image), le client Anthropic est un faux objet scripté.

Lancer : .venv/bin/python -m tests.test_image_audit_plafond
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
os.environ["ANTHROPIC_API_KEY"] = "factice-jamais-appelee"

from scripts.scraper_events import init_db  # noqa: E402
import scripts.image_audit as image_audit  # noqa: E402
from utils.api_limite import PlafondAPI  # noqa: E402

image_audit.DB_PATH = tmp
image_audit.build_grid = lambda batch: (b"planche-factice", set())  # pas de réseau/PIL


class ErreurPlafond(Exception):
    status_code = 400

    def __str__(self):
        return ("Error code: 400 - You have reached your specified API usage limits. "
                "You will regain access on 2026-09-01 at 00:00 UTC.")


class _Bloc:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Msg:
    def __init__(self, text):
        self.content = [_Bloc(text)]
        self.usage = None


class FauxClient:
    """1er appel (planche 1) réussit sans rien signaler, 2e appel (planche 2) plafonne."""
    def __init__(self):
        self.appels = 0

    class _Messages:
        def __init__(self, parent):
            self._p = parent

        def create(self, **kw):
            self._p.appels += 1
            if self._p.appels == 1:
                return _Msg('{"flagged": []}')
            raise ErreurPlafond()

    @property
    def messages(self):
        return self._Messages(self)


class _MessagesToujoursOK:
    def create(self, **kw):
        return _Msg('{"flagged": []}')


class ClientToujoursOK:
    @property
    def messages(self):
        return _MessagesToujoursOK()


# main() construit son propre client (`anthropic.Anthropic(api_key=..., timeout=90.0)`) —
# on remplace la CLASSE elle-même pour injecter nos faux clients sans réseau, comme le
# scénario en cours l'exige (voir chaque appel de main() ci-dessous).
import anthropic  # noqa: E402
_client_a_injecter = [None]
anthropic.Anthropic = lambda **kw: _client_a_injecter[0]


def _base(nb_batch1=20, nb_batch2=4, flag_sur_batch2=True):
    if tmp.exists():
        tmp.unlink()
    conn = sqlite3.connect(tmp)
    init_db(conn)
    total = nb_batch1 + nb_batch2
    for i in range(total):
        conn.execute(
            "INSERT INTO events_raw (title, description, url_source, url_image, "
            "image_source, statut, llm_score) VALUES (?,?,?,?,?,?,?)",
            (f"Événement {i}", "Une sortie culturelle.", f"https://a.fr/{i}",
             f"https://a.fr/img{i}.jpg", "web", "evaluated", 8))
    conn.commit()
    if flag_sur_batch2:
        # Un signalement ACTIF déjà posé sur une fiche de la 2e planche (jamais atteinte
        # avant le plafond). `_select` trie par id DESCENDANT : la 1re planche prend les
        # id LES PLUS HAUTS, la 2e (jamais atteinte ici) les plus bas — id=2 y est donc.
        image_audit._ensure_audit_flags_table(conn)
        cible = 2
        conn.execute(
            "INSERT INTO image_audit_flags (event_id, reason, flagged_at, resolved_at) "
            "VALUES (?, 'photo hors-sujet (posé avant ce run)', datetime('now'), NULL)",
            (cible,))
        conn.commit()
    conn.close()
    return cible if flag_sur_batch2 else None


echecs = 0

# ── 1. judge_grid lève PlafondAPI au lieu de rendre [] ──────────────────────────
print("──── judge_grid sous plafond ────")
batch = [{"id": 1, "title": "x", "url_image": "https://a.fr/1.jpg"}]
faux = FauxClient()
r1 = image_audit.judge_grid(batch, b"planche", faux, set())  # 1er appel : réussit
if r1 == []:
    print("OK    1er appel : réussit normalement (liste vide, rien signalé)")
else:
    print(f"ÉCHEC : 1er appel aurait dû rendre [], obtenu {r1}")
    echecs += 1
try:
    image_audit.judge_grid(batch, b"planche", faux, set())  # 2e appel : plafond
    print("ÉCHEC judge_grid : a rendu une liste au lieu de lever PlafondAPI")
    echecs += 1
except PlafondAPI:
    print("OK    judge_grid : PlafondAPI levée au 2e appel")

# ── 2. Le lot complet (main()) : plafond à la 2e planche ────────────────────────
print("\n──── image_audit.main() : plafond à la 2e planche ────")
cible = _base(20, 4, flag_sur_batch2=True)
_client_a_injecter[0] = FauxClient()
rc = image_audit.main(["--no-slack"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
flag = conn.execute(
    "SELECT resolved_at FROM image_audit_flags WHERE event_id=?", (cible,)
).fetchone()
conn.close()

if rc == 3:
    print("OK    code retour 3 sous plafond")
else:
    print(f"ÉCHEC : rc={rc}, attendu 3")
    echecs += 1

if flag is not None and flag["resolved_at"] is None:
    print(f"OK    flag actif de la fiche {cible} PRÉSERVÉ (pas rejugée, pas effacée)")
else:
    print(f"ÉCHEC : flag de la fiche {cible} = {dict(flag) if flag else None} — "
          "aurait dû rester actif (resolved_at NULL)")
    echecs += 1

# ── 3. Contre-épreuve : sans plafond, l'audit tourne et persiste normalement ────
print("\n──── contre-épreuve : chaîne normale (main()) ────")
_base(3, 0, flag_sur_batch2=False)
_client_a_injecter[0] = ClientToujoursOK()
rc = image_audit.main(["--no-slack"])
if rc == 0:
    print("OK    rc=0 sans plafond — la correction n'a rien cassé")
else:
    print(f"ÉCHEC contre-épreuve : rc={rc}, attendu 0")
    echecs += 1

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
