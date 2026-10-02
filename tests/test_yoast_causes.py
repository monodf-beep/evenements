#!/usr/bin/env python3
"""Fixture : le classement « pourquoi c'est rouge » de scripts/yoast_scores.

Aucun réseau, aucun Node, aucune base : des notes FABRIQUÉES, de la même forme que ce que
rend scripts/yoast_score.js (seo_detail / lis_detail = [{id, score}]).

D'OÙ ÇA VIENT. Franck, 21/09/2026 : « apparemment ce qu'on fait ne résout pas tout le
temps le SEO ». Le moteur calculait le détail par critère depuis toujours ; `ecrire()`
n'envoyait que deux nombres agrégés, donc le détail était jeté à chaque passage — même
défaut que le 18/08.

CE QUE LA FIXTURE SURVEILLE, dont deux cas qui doivent PASSER, près de la frontière :
  1. le classement sort les critères mauvais, du plus répandu au moins répandu ;
  2. ⚠️ CAS QUI DOIT PASSER : un critère VERT partout n'apparaît pas. Sans lui, un
     classement qui listerait tout serait indétectable ;
  3. ⚠️ LE PÉRIMÈTRE : Yoast n'applique pas tous ses critères à toutes les fiches, donc
     `concernees` compte les fiches où le critère s'applique, jamais le total ;
  4. ⚠️ LA FRONTIÈRE DU SEUIL : à seuil 5, une note de 5 est mauvaise et une note de 6 ne
     l'est pas — exactement un point de part et d'autre ;
  5. un identifiant inconnu n'est pas masqué : il s'affiche tel quel.

Lancer : .venv/bin/python -m tests.test_yoast_causes
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


from scripts.yoast_scores import causes                       # noqa: E402

# Trois fiches. « textLength » est vert partout ; « subheadingsTooLongText » est mauvais
# sur les trois ; « passiveVoice » ne s'applique qu'à deux d'entre elles.
NOTES = [
    {"id": 1, "lis_detail": [{"id": "subheadingsTooLongText", "score": 2},
                             {"id": "textLength", "score": 9},
                             {"id": "passiveVoice", "score": 3}]},
    {"id": 2, "lis_detail": [{"id": "subheadingsTooLongText", "score": 2},
                             {"id": "textLength", "score": 9},
                             {"id": "passiveVoice", "score": 9}]},
    {"id": 3, "lis_detail": [{"id": "subheadingsTooLongText", "score": 2},
                             {"id": "textLength", "score": 9}],
     "seo_detail": [{"id": "critereInconnuDeLaListe", "score": 1}]},
]

rangs = causes(NOTES)
par_id = {e["critere"]: e for e in rangs}

verifier("le critère le plus répandu est en tête",
         rangs[0]["critere"] == "subheadingsTooLongText", [e["critere"] for e in rangs])
verifier("il est compté sur les trois fiches",
         par_id["subheadingsTooLongText"]["mauvais"] == 3
         and par_id["subheadingsTooLongText"]["concernees"] == 3)
verifier("⚠️ CAS QUI DOIT PASSER : un critère vert partout n'est PAS une cause",
         "textLength" not in par_id, list(par_id))
verifier("⚠️ LE PÉRIMÈTRE : un critère qui ne s'applique qu'à 2 fiches compte sur 2",
         par_id["passiveVoice"]["mauvais"] == 1
         and par_id["passiveVoice"]["concernees"] == 2,
         par_id.get("passiveVoice"))
verifier("la note moyenne accompagne le compte (elle contrôle le seuil)",
         par_id["passiveVoice"]["moyenne"] == 6.0, par_id["passiveVoice"]["moyenne"])
verifier("les deux familles sont distinguées",
         par_id["subheadingsTooLongText"]["famille"] == "lisibilité"
         and par_id["critereInconnuDeLaListe"]["famille"] == "SEO")
verifier("un critère connu est traduit en français",
         par_id["subheadingsTooLongText"]["libelle"] == "texte trop long sans sous-titre (H2)")
verifier("un critère INCONNU n'est pas masqué : il s'affiche tel quel",
         par_id["critereInconnuDeLaListe"]["libelle"] == "critereInconnuDeLaListe")

# ⚠️ La frontière du seuil, un point de part et d'autre.
FRONTIERE = [{"id": 9, "lis_detail": [{"id": "justeDessous", "score": 5},
                                      {"id": "justeAudessus", "score": 6}]}]
ids_5 = {e["critere"] for e in causes(FRONTIERE, seuil=5)}
verifier("⚠️ FRONTIÈRE : à seuil 5, une note de 5 est mauvaise",
         "justeDessous" in ids_5)
verifier("⚠️ FRONTIÈRE, CAS QUI DOIT PASSER : une note de 6 ne l'est pas",
         "justeAudessus" not in ids_5, ids_5)
ids_6 = {e["critere"] for e in causes(FRONTIERE, seuil=6)}
verifier("et le seuil se déplace vraiment (à 6, les deux sortent)",
         ids_6 == {"justeDessous", "justeAudessus"}, ids_6)

verifier("aucune note = aucun classement (pas d'exception)", causes([]) == [])

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
