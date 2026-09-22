#!/usr/bin/env python3
"""Fixture : deux `translate_events.py --apply` ne peuvent plus tourner en même temps.

L'ACCIDENT (2026-09-22 au soir). Deux exécutions `--apply` simultanées (PID 54609 et
57330) ont chacune calculé leur file au démarrage ; les files se recouvraient ; chaque
fiche commune a été traduite deux fois → 11 fiches italiennes en double sur WordPress
(WP#11010 à 22:23:55, WP#11011 à 22:23:56). Le cron de 10:45 lance le même script : une
exécution manuelle à ce moment-là recrée l'accident. D'où le verrou `utils/verrou.py`.

CE QUE LA FIXTURE PROUVE — avec de VRAIS processus séparés, parce qu'un verrou qui ne
fonctionne qu'à l'intérieur d'un même processus ne protège de rien ici :

  1. un premier `--apply` prend le verrou, un second est REFUSÉ et apprend le PID du
     détenteur (c'est ce que dira le journal) ;
  2. CONTRE-ÉPREUVES qui doivent PASSER, choisies à la frontière :
       · le premier se termine normalement SANS relâcher → le suivant OBTIENT le verrou ;
       · le premier est tué au SIGKILL (aucun code de nettoyage ne tourne) → le suivant
         l'OBTIENT, et le PID périmé resté dans le fichier est remplacé — c'est tout
         l'intérêt de flock sur un fichier PID ;
       · une SIMULATION pendant qu'un `--apply` tourne n'est PAS refusée ;
       · une simulation qui tourne ne PREND PAS le verrou : un `--apply` lancé à côté passe ;
  3. par LECTURE (ast) de scripts/translate_events.py — qu'on ne peut pas importer ici
     sans `anthropic`, `.env` ni base — que `main()` prend ce verrou sur `args.apply`,
     AVANT la sonde réseau et AVANT la sélection des fiches, et sort en code non nul.

Aucun réseau, aucune base, aucun `.env` : le verrou vit dans un dossier jetable.

Lancer : python3 tests/test_translate_lock.py
"""
from __future__ import annotations

import ast
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import verrou  # noqa: E402

# Dossier jetable : on ne touche JAMAIS au data/translate_events.lock de production.
CHEMIN = Path(tempfile.mkdtemp(prefix="verrou-")) / "translate_events.lock"

# Le processus enfant : tente le verrou comme le ferait main(), annonce le résultat sur
# une ligne, puis soit sort tout de suite, soit dort pour TENIR la place.
ENFANT = r"""
import sys, time
sys.path.insert(0, sys.argv[1])
from utils import verrou
apply = sys.argv[3] == "apply"
v = verrou.exclusif_si(apply, sys.argv[2])
if v is None:
    print("SIMULATION", flush=True)
elif v.obtenu:
    print("PRIS", flush=True)
else:
    print("REFUSE " + v.detenteur, flush=True)
    sys.exit(verrou.CODE_DEJA_EN_COURS)
if sys.argv[4] == "tenir":
    time.sleep(120)
"""

echecs = 0
cas = 0


def verifier(ok: bool, message: str) -> None:
    global echecs, cas
    cas += 1
    if ok:
        print(f"OK    {message}")
    else:
        echecs += 1
        print(f"ÉCHEC {message}")


def lancer(mode: str, duree: str) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", ENFANT, str(ROOT), str(CHEMIN), mode, duree],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def tenir(mode: str = "apply") -> tuple[subprocess.Popen, str]:
    """Lance un détenteur et attend qu'il ait ANNONCÉ son résultat (pas de sleep au jugé)."""
    p = lancer(mode, "tenir")
    ligne = p.stdout.readline().strip()
    return p, ligne


def essayer(mode: str = "apply") -> tuple[int, str]:
    p = lancer(mode, "sortir")
    sortie, erreur = p.communicate(timeout=30)
    return p.returncode, (sortie.strip() or erreur.strip())


def arreter(p: subprocess.Popen, sig: int = signal.SIGKILL) -> None:
    if p.poll() is None:
        p.send_signal(sig)
    p.wait(timeout=30)


# ── 1. Deux --apply : le second est refusé ────────────────────────────────────────────
a, ligne_a = tenir("apply")
verifier(ligne_a == "PRIS", f"un premier --apply prend le verrou (annonce : {ligne_a!r})")
code_b, sortie_b = essayer("apply")
verifier(code_b == verrou.CODE_DEJA_EN_COURS and sortie_b.startswith("REFUSE"),
         f"un second --apply est REFUSÉ, code {code_b} (attendu "
         f"{verrou.CODE_DEJA_EN_COURS}, non nul)")
verifier(f"pid={a.pid}" in sortie_b,
         f"le refus nomme le PID du détenteur ({a.pid}) : {sortie_b!r}")

# ── 2c. Simulation pendant un --apply : elle n'est PAS refusée ─────────────────────────
code_s, sortie_s = essayer("simulation")
verifier(code_s == 0 and sortie_s == "SIMULATION",
         f"une simulation pendant un --apply passe (code {code_s}, {sortie_s!r})")

# ── 2b. Détenteur tué au SIGKILL : le verrou tombe avec lui ────────────────────────────
arreter(a, signal.SIGKILL)
verifier(a.returncode == -signal.SIGKILL, f"le détenteur est bien mort au SIGKILL "
                                          f"(code {a.returncode})")
verifier(f"pid={a.pid}" in CHEMIN.read_text(),
         "le fichier porte encore le PID périmé du mort (c'est le piège d'un fichier PID)")
c, ligne_c = tenir("apply")
verifier(ligne_c == "PRIS", f"après le SIGKILL, le suivant OBTIENT le verrou ({ligne_c!r})")
contenu = CHEMIN.read_text()
verifier(f"pid={c.pid}" in contenu and f"pid={a.pid}" not in contenu,
         "le PID périmé est remplacé par celui du nouveau détenteur")

# ── 2a. Détenteur qui se termine normalement SANS relâcher ─────────────────────────────
arreter(c, signal.SIGTERM)
code_d, sortie_d = essayer("apply")   # sort tout de suite, sans appeler relacher()
verifier(code_d == 0 and sortie_d == "PRIS",
         f"après un SIGTERM, le suivant l'obtient ({code_d}, {sortie_d!r})")
code_e, sortie_e = essayer("apply")
verifier(code_e == 0 and sortie_e == "PRIS",
         f"un processus terminé normalement sans relâcher ne bloque pas le suivant "
         f"({code_e}, {sortie_e!r})")

# ── 2d. Une simulation qui tourne ne prend PAS le verrou ───────────────────────────────
s, ligne_s = tenir("simulation")
verifier(ligne_s == "SIMULATION", f"la simulation tourne ({ligne_s!r})")
code_f, sortie_f = essayer("apply")
verifier(code_f == 0 and sortie_f == "PRIS",
         f"un --apply lancé PENDANT une simulation obtient le verrou ({code_f}, {sortie_f!r})")
arreter(s)

# ── 2e. Dans un même processus aussi, relacher() libère la place ───────────────────────
v1 = verrou.prendre(CHEMIN)
v2 = verrou.prendre(CHEMIN)
verifier(v1.obtenu and not v2.obtenu,
         "deux prises dans le même processus : la seconde est refusée (flock par "
         "description de fichier)")
v1.relacher()
v3 = verrou.prendre(CHEMIN)
verifier(v3.obtenu, "après relacher(), une nouvelle prise réussit")
v3.relacher()

# ── 3. Lecture : translate_events.main() prend bien ce verrou, au bon endroit ─────────
SOURCE = ROOT / "scripts" / "translate_events.py"
arbre = ast.parse(SOURCE.read_text(encoding="utf-8"))
main = next((n for n in arbre.body if isinstance(n, ast.FunctionDef) and n.name == "main"),
            None)


def _nom_appel(n: ast.Call) -> str:
    f = n.func
    return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")


def _premiere_ligne(nom: str) -> int | None:
    lignes = [n.lineno for n in ast.walk(main)
              if isinstance(n, ast.Call) and _nom_appel(n) == nom]
    return min(lignes) if lignes else None


appels_verrou = [n for n in ast.walk(main) if isinstance(n, ast.Call)
                 and _nom_appel(n) == "exclusif_si"] if main else []
verifier(bool(appels_verrou), "main() appelle verrou.exclusif_si")
if appels_verrou:
    appel = appels_verrou[0]
    premier = ast.unparse(appel.args[0]) if appel.args else ""
    verifier(premier == "args.apply",
             f"le verrou est conditionné à args.apply (trouvé : {premier!r})")
    l_verrou = appel.lineno
    for nom, pourquoi in (("wp_site_joignable", "la sonde réseau"),
                          ("_rearme_traductions_orphelines", "le rouvreur d'avant sélection"),
                          ("connect", "l'ouverture de la base"),
                          ("_retranslate", "la re-traduction --retranslate")):
        l_autre = _premiere_ligne(nom)
        verifier(l_autre is not None and l_verrou < l_autre,
                 f"verrou (ligne {l_verrou}) AVANT {pourquoi} (ligne {l_autre})")
    texte_main = ast.unparse(main)
    verifier("CODE_DEJA_EN_COURS" in texte_main,
             "le refus sort avec verrou.CODE_DEJA_EN_COURS (non nul)")
    verifier("data" in texte_main and "translate_events.lock" in texte_main,
             "le fichier de verrou est data/translate_events.lock (data/ est ignoré par git)")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s) sur {cas} cas.")
sys.exit(1 if echecs else 0)
