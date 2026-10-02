#!/usr/bin/env python3
"""L'ÉVALUATEUR NOTE-T-IL COMME FRANCK ? — mesure de la dérive, lecture seule.

LE TROU QUE ÇA FERME. `utils/score_memory` enregistre chaque correction de score faite au
back-office et `scripts/evaluator.py` réinjecte les plus récentes comme exemples de
calibrage : « au fil du temps, il note comme Franck ». C'est écrit dans le module — mais
RIEN NE VÉRIFIE QUE ÇA MARCHE. On a une boucle d'apprentissage sans instrument de mesure,
donc sans moyen de savoir si elle apprend, si elle stagne, ou si elle dérive.

Le 2026-08-03, c'est Franck qui a remarqué que les quatre événements mis en avant sur la
home n'étaient pas intéressants. Aucune machine ne l'aurait vu. Ce script ne remplace pas
ce regard — il donne le seul indicateur que la machine peut produire honnêtement : l'écart
entre ce qu'elle a noté et ce qu'un humain a corrigé.

TROIS MESURES, ET C'EST TOUT :
  1. le BIAIS — l'évaluateur sous-note-t-il ou sur-note-t-il, et de combien ;
  2. OÙ il se concentre — par territoire et par catégorie, car un biais général et un
     biais sur « Piémont » n'appellent pas la même correction ;
  3. s'il DIMINUE — en comparant les corrections récentes aux plus anciennes. C'est la
     seule qui dise si le calibrage sert à quelque chose.

CE QU'IL NE PEUT PAS DIRE, et il le dit :
  • Franck ne corrige QUE ce qu'il regarde. Une fiche mal notée qu'il n'a jamais ouverte
    n'apparaît nulle part. L'échantillon est biaisé vers ce qui a attiré son attention —
    typiquement ce qui l'a choqué. Le biais mesuré est donc un PLANCHER.
  • En dessous d'un seuil de corrections, il n'y a rien à conclure. Le script refuse alors
    de trancher plutôt que de rendre un chiffre qui ferait décider à tort.

Usage :
    .venv/bin/python scripts/audit_calibrage.py
    .venv/bin/python scripts/audit_calibrage.py --slack   # si dérive franche seulement
"""
from __future__ import annotations
import argparse
import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import score_memory

log = get_logger("audit-calibrage")

# En dessous, on ne conclut RIEN. Dix corrections ne font pas une tendance : sur une
# échelle de 0 à 10, deux ou trois désaccords marqués suffiraient à fabriquer un « biais »
# qui n'existe pas. Mieux vaut dire « je ne sais pas encore » qu'un chiffre trompeur.
MIN_CORRECTIONS = 10
# Écart moyen au-delà duquel on parle de dérive plutôt que de bruit. Un demi-point sur 10,
# c'est un désaccord d'appréciation ; un point et demi, c'est un critère mal compris.
SEUIL_DERIVE = 1.5
# Taille des groupes secondaires (territoire, catégorie) sous laquelle on n'affiche rien.
MIN_GROUPE = 4


def _delta(c: dict) -> float | None:
    try:
        return float(c["new_score"]) - float(c["old_score"])
    except (TypeError, ValueError, KeyError):
        return None


def analyser(corrections: list[dict]) -> dict:
    """Biais global, par groupe, et évolution. Aucun jugement ici — que des nombres."""
    deltas = [(c, d) for c in corrections if (d := _delta(c)) is not None]
    if not deltas:
        return {"n": 0}

    valeurs = [d for _, d in deltas]
    moyenne = sum(valeurs) / len(valeurs)

    def _par(champ: str) -> list[tuple[str, int, float]]:
        pot = collections.defaultdict(list)
        for c, d in deltas:
            pot[(c.get(champ) or "—")].append(d)
        return sorted(((k, len(v), sum(v) / len(v)) for k, v in pot.items() if len(v) >= MIN_GROUPE),
                      key=lambda t: -abs(t[2]))

    # ÉVOLUTION : moitié ancienne contre moitié récente. Si le calibrage sert, l'écart
    # doit RÉTRÉCIR — l'évaluateur voit les corrections passées dans son prompt.
    moitie = len(valeurs) // 2
    anciens, recents = valeurs[:moitie], valeurs[moitie:]
    evol = None
    if moitie >= MIN_CORRECTIONS // 2:
        evol = (sum(anciens) / len(anciens), sum(recents) / len(recents))

    return {
        "n": len(valeurs), "moyenne": moyenne,
        "sous_notes": sum(1 for d in valeurs if d > 0),
        "sur_notes": sum(1 for d in valeurs if d < 0),
        "par_territoire": _par("territoire"), "par_categorie": _par("categorie"),
        "evolution": evol,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="L'évaluateur note-t-il comme Franck ?")
    p.add_argument("--limit", type=int, default=200,
                   help="Nombre de corrections examinées (les plus récentes).")
    p.add_argument("--slack", action="store_true",
                   help="Alerte Slack UNIQUEMENT en cas de dérive franche.")
    args = p.parse_args(argv)

    corrections = score_memory.load_recent(limit=args.limit)
    a = analyser(corrections)

    print("\n" + "=" * 72)
    print("CALIBRAGE DE L'ÉVALUATEUR — l'écart entre sa note et la tienne")
    print("=" * 72)

    if a["n"] < MIN_CORRECTIONS:
        print(f"\n  {a['n']} correction(s) enregistrée(s) — il en faut au moins "
              f"{MIN_CORRECTIONS} pour conclure quoi que ce soit.")
        print("  Rien n'est affirmé : sur une échelle de 0 à 10, deux ou trois désaccords")
        print("  marqués suffiraient à fabriquer une tendance qui n'existe pas.\n")
        return 0

    m = a["moyenne"]
    sens = "SOUS-NOTE" if m > 0 else "SUR-NOTE"
    print(f"\n  {a['n']} corrections examinées.")
    print(f"  Écart moyen : {m:+.2f} point(s) → l'évaluateur {sens} par rapport à toi.")
    print(f"  ({a['sous_notes']} fois tu as monté la note, {a['sur_notes']} fois tu l'as baissée)")

    if a["evolution"]:
        anc, rec = a["evolution"]
        mieux = abs(rec) < abs(anc)
        print(f"\n  Évolution : {anc:+.2f} sur la première moitié → {rec:+.2f} sur la seconde")
        print(f"    → {'le calibrage RÉDUIT l écart' if mieux else 'l écart ne se réduit PAS'}"
              + ("" if mieux else " — les corrections réinjectées ne portent pas."))

    for titre, lot in (("Par territoire", a["par_territoire"]),
                       ("Par catégorie", a["par_categorie"])):
        if lot:
            print(f"\n  {titre} (groupes d'au moins {MIN_GROUPE}) :")
            for cle, n, moy in lot[:6]:
                print(f"    {moy:+.2f}  sur {n:>3} correction(s)   {cle[:40]}")

    print(f"\n  ⚠️  CE QUE CE CHIFFRE NE DIT PAS : tu ne corriges que ce que tu REGARDES.")
    print(f"      Une fiche mal notée que tu n'as jamais ouverte n'apparaît nulle part.")
    print(f"      L'écart réel est donc au moins celui-ci, jamais moins.\n")

    derive = abs(m) >= SEUIL_DERIVE
    if not args.slack:
        return 1 if derive else 0
    if not derive:
        log.info("Écart de %.2f point — sous le seuil de %.1f, pas d'alerte.", m, SEUIL_DERIVE)
        return 0

    from utils import slack
    lignes = [f"📏 *Calibrage de l'évaluateur* — écart moyen {m:+.2f} point(s) "
              f"sur {a['n']} corrections",
              f"Il {sens.lower()} systématiquement par rapport à toi."]
    if a["par_categorie"]:
        cle, n, moy = a["par_categorie"][0]
        lignes.append(f"Le plus marqué : *{cle}* ({moy:+.2f} sur {n} corrections).")
    lignes.append("_Rappel : ne compte que ce que tu as regardé — l'écart réel est au moins celui-là._")
    slack.notify("\n".join(lignes))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
