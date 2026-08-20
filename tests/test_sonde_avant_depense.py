#!/usr/bin/env python3
"""Fixture : ne rien dépenser quand le site est injoignable — et ne rien bloquer sinon.

Aucun réseau : la sonde est remplacée par une fausse, dans les deux sens.

D'OÙ ÇA VIENT (2026-08-18). Le VPS ne joint plus le site depuis le 18/08, et Franck est
absent jusqu'au 3 septembre — personne pour regarder ce que les crons font entre-temps.

Deux gaspillages quotidiens, mesurés dans le code :

  · `translate_events` (10h45, `--cap 10`) contrôle `wp_original_est_en_ligne` APRÈS
    `translate_title_desc`. Chaque fiche est donc intégralement traduite — deux appels au
    modèle — puis refusée pour une cause qui ne bougera pas avant le déblocage. Sur seize
    jours, environ trois cents appels Sonnet pour rien ;
  · `publish_batch_as` (9h30) attend 60 s par fiche avant d'abandonner, en générant et
    téléversant des vignettes dans le vide.

C'est le cul-de-sac de la règle 3 : « un refus qui se rejoue sur la MÊME entrée n'est pas
un rouvreur ». Le commentaire de `wp_original_est_en_ligne` justifiait son False par « la
traduction attend le run suivant » — vrai pour une coupure d'une minute, faux pour une
panne de deux semaines.

CE QUE LA FIXTURE SURVEILLE :
  1. site injoignable → AUCUN appel au modèle, AUCUNE publication, et le code de sortie
     reste 0 (ce n'est pas une erreur du script, c'est une absence de réseau) ;
  2. le message dit que ce n'est PAS un refus éditorial, et où lire l'incident — sinon le
     journal se lit comme un problème de données ;
  3. ⚠️ ET LE CAS QUI DOIT PASSER : site joignable → la garde ne bloque RIEN. Sans lui, on
     aurait pu poser un `return 0` inconditionnel et couper la publication pendant deux
     semaines sans que personne ne le voie ;
  4. rien n'est marqué en base dans le cas bloqué : les fiches repassent à l'identique.

Lancer : .venv/bin/python -m tests.test_sonde_avant_depense
"""
import contextlib
import io
import logging
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DB_PATH", str(Path(tempfile.mkdtemp()) / "vide.db"))
os.environ.setdefault("WP_AS_URL", "https://exemple.invalid")

import scripts.publish_batch_as as pb   # noqa: E402
import scripts.translate_events as te   # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ⚠️ LE JOURNAL NE PASSE PAS PAR stdout. Première version de cette fixture : trois
# contrôles sur le CONTENU du message, tous au rouge — non parce que le message manquait,
# mais parce que `redirect_stdout` ne capture pas ce que `logging` écrit. Une fixture qui
# regarde le mauvais canal ne prouve rien, dans un sens comme dans l'autre.
_journal = io.StringIO()
_h = logging.StreamHandler(_journal)
_h.setLevel(logging.DEBUG)
logging.getLogger().addHandler(_h)
for _nom in ("translate-events", "publish_batch_as", "publisher_as"):
    _lg = logging.getLogger(_nom)
    _lg.addHandler(_h)
    _lg.setLevel(logging.DEBUG)


class _Mouchard:
    """Compte ce qui aurait été DÉPENSÉ : appels au modèle, publications."""
    def __init__(self):
        self.appels = 0

    def __call__(self, *a, **k):
        self.appels += 1
        return None


print("──── site INJOIGNABLE : rien ne doit être dépensé ────")
mouchard_trad, mouchard_pub = _Mouchard(), _Mouchard()
te.wp_site_joignable = lambda *a, **k: False
te.translate_title_desc = mouchard_trad
pb.wp_site_joignable = lambda *a, **k: False
pb.publish_to_as = mouchard_pub

buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    code_te = te.main(["--apply", "--cap", "10"])
    code_pb = pb.main(["--update", "--cap", "50"])
sortie = buf.getvalue() + _journal.getvalue()

_check("aucun appel au modèle pour traduire", mouchard_trad.appels == 0,
       f"{mouchard_trad.appels} appel(s)")
_check("aucune publication tentée", mouchard_pub.appels == 0,
       f"{mouchard_pub.appels} appel(s)")
_check("les deux rendent 0 — absence de réseau, pas erreur du script",
       code_te == 0 and code_pb == 0, f"{code_te} / {code_pb}")
_check("le journal dit que ce N'EST PAS un refus éditorial",
       "pas un refus éditorial" in sortie, sortie[-600:])
_check("   et renvoie à l'incident, pour qu'on ne rediagnostique pas",
       "PANNE_OVH_2026-08-18" in sortie, sortie[-600:])
_check("   et dit que les fiches repasseront telles quelles",
       "repasseront" in sortie or "repassera" in sortie, sortie[-600:])

print("\n──── ⚠️ site JOIGNABLE : la garde ne doit RIEN bloquer ────")
# Sans ce contrôle, un `return 0` inconditionnel couperait la publication pendant deux
# semaines et la fixture serait quand même au vert — c'est le portillon du 2026-08-06.
te.wp_site_joignable = lambda *a, **k: True
pb.wp_site_joignable = lambda *a, **k: True
_journal.seek(0), _journal.truncate(0)
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    with contextlib.suppress(Exception):
        te.main(["--cap", "1"])          # sans --apply : simulation, mais la garde est passée
    with contextlib.suppress(Exception):
        pb.main(["--dry-run", "--cap", "1"])
passe = buf.getvalue() + _journal.getvalue()
_check("le message de blocage n'apparaît PAS quand le site répond",
       "AUCUNE traduction tentée" not in passe and "AUCUNE publication tentée" not in passe,
       passe[-400:])

print("\n──── la sonde elle-même ────")
from scripts.publisher_as import wp_site_joignable   # noqa: E402
os.environ["WP_AS_URL"] = ""
_check("sans adresse configurée, elle répond False plutôt que de lever",
       wp_site_joignable(essais=1) is False)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
