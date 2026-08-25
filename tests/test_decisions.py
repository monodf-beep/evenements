#!/usr/bin/env python3
"""Fixture : le registre des décisions — la mémoire qui manquait à la fiche 4839.

⚠️ REGISTRE JETABLE via DECISIONS_PATH — jamais data/decisions.jsonl. Aucun réseau.

CE QU'ELLE ÉPROUVE, dans l'ordre d'importance :

  1. LA RÉOUVERTURE (règle 3). « Résolu » est un état terminal ; son rouvreur est un
     nouveau signalement sur la MÊME clé — même critère que le signaleur, pas un prédicat
     voisin (la leçon des neuf jours de repair_polluted_descriptions). Sans ce test, le
     registre serait un cimetière : on y entrerait, on n'en sortirait plus.
  2. les REFUS explicites : résoudre l'inconnu, escalader le résolu — un succès
     silencieux sur du vide est le zéro sans dénominateur de ce dépôt.
  3. la répétition COMPTE au lieu de se perdre : vues, première/dernière date.
  4. le zéro dit son dénominateur dans la sortie CLI.

Lancer : .venv/bin/python -m tests.test_decisions
"""
import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["DECISIONS_PATH"] = str(Path(tempfile.mkdtemp()) / "decisions.jsonl")

from utils import decisions  # noqa: E402
import scripts.decisions as cli  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── un zéro dit son dénominateur, même sur registre vierge ────")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    cli.main(["--liste"])
_check("la liste vide annonce « 0 en attente sur 0 enregistrée(s) »",
       "0 en attente sur 0 enregistrée(s)" in buf.getvalue(), buf.getvalue())

print("\n──── la répétition compte au lieu de se perdre ────")
e = decisions.signaler("fiche-4839", "Coro & Bentu : restaurant classé événement",
                       "bilan_matin", geste="trash_by_ids 4839")
_check("premier signalement : vue 1 fois, ouverte", e["vues"] == 1 and e["etat"] == "ouverte")
e = decisions.signaler("fiche-4839", "Coro & Bentu : restaurant classé événement",
                       "bilan_matin")
premiere = e["premiere_vue"]
_check("second signalement : vues=2, la première date ne bouge pas",
       e["vues"] == 2 and e["premiere_vue"] == premiere, str(e))
_check("le geste proposé au premier passage survit au second",
       e["geste"] == "trash_by_ids 4839", str(e["geste"]))

print("\n──── l'escalade est datée, une fois — plus de harcèlement quotidien ────")
e = decisions.escalader("fiche-4839", "restaurant, pas un événement : écarter ?")
_check("l'escalade est datée", bool(e["escalade_le"]))
_check("la décision reste EN ATTENTE (escaladée ≠ résolue)",
       any(x["cle"] == "fiche-4839" for x in decisions.en_attente()))

print("\n──── la résolution clôt, avec résultat et auteur ────")
e = decisions.resoudre("fiche-4839", "statut rejected posé, recompté en base", "cerveau")
_check("résolue, avec le constat et l'auteur",
       e["etat"] == "resolue" and e["resolution"]["par"] == "cerveau", str(e))
_check("elle sort de la file d'attente",
       not any(x["cle"] == "fiche-4839" for x in decisions.en_attente()))

print("\n──── RÈGLE 3 : le rouvreur, sur le MÊME critère que le signaleur ────")
e = decisions.signaler("fiche-4839", "Coro & Bentu réapparu", "bilan_matin")
_check("un nouveau signalement ROUVRE la décision résolue",
       e["etat"] == "ouverte" and e["reouvertures"] == 1, str(e))
_check("   et elle revient dans la file, marquée rouverte",
       any(x["cle"] == "fiche-4839" and x["reouvertures"] == 1
           for x in decisions.en_attente()))
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    cli.main(["--liste"])
_check("   la liste avertit : le correctif précédent n'a pas tenu",
       "ROUVERTE" in buf.getvalue() and "n'a pas tenu" in buf.getvalue(), buf.getvalue())

print("\n──── contre-épreuve : les refus sont explicites, jamais silencieux ────")
try:
    decisions.resoudre("inconnue-999", "rien", "personne")
    _check("résoudre une clé inconnue est REFUSÉ", False, "aucune exception levée")
except ValueError as exc:
    _check("résoudre une clé inconnue est REFUSÉ", "inconnue" in str(exc), str(exc))
decisions.resoudre("fiche-4839", "re-réglée", "cerveau")
try:
    decisions.escalader("fiche-4839")
    _check("escalader une décision résolue est REFUSÉ", False, "aucune exception levée")
except ValueError as exc:
    _check("escalader une décision résolue est REFUSÉ", "résolue" in str(exc), str(exc))
try:
    decisions.resoudre("fiche-4839", "encore", "cerveau")
    _check("résoudre deux fois est REFUSÉ (avec la date du premier geste)", False,
           "aucune exception levée")
except ValueError as exc:
    _check("résoudre deux fois est REFUSÉ (avec la date du premier geste)",
           "déjà résolue" in str(exc), str(exc))

print("\n──── le CLI refuse un signalement anonyme ────")
# Un signalement sans titre ni provenance est illisible dans trois jours — argparse
# doit le refuser (SystemExit 2), pas l'enregistrer à moitié.
try:
    with contextlib.redirect_stderr(io.StringIO()):
        cli.main(["--signaler", "x"])
    _check("--signaler sans --titre/--source est refusé", False, "accepté à tort")
except SystemExit as exc:
    _check("--signaler sans --titre/--source est refusé", exc.code == 2, str(exc.code))

print("\n──── les agents du matin ont bien leur porte vers le registre ────")
# Le registre ne sert que si le cerveau peut y écrire et le bilan le lire : on vérifie
# les harnais, pas l'intention. Le bilan est borné à --liste (le contrôleur ne peut pas
# amender la mémoire de l'acteur qu'il contrôle).
cerveau = (ROOT / "scripts" / "cerveau.sh").read_text(encoding="utf-8")
bilan = (ROOT / "scripts" / "bilan_matin.sh").read_text(encoding="utf-8")
_check("cerveau.sh autorise scripts.decisions (lecture ET écriture)",
       '"Bash(.venv/bin/python -m scripts.decisions:*)"' in cerveau)
_check("bilan_matin.sh n'autorise QUE --liste",
       '"Bash(.venv/bin/python -m scripts.decisions --liste:*)"' in bilan
       and '"Bash(.venv/bin/python -m scripts.decisions:*)"' not in bilan)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
