#!/usr/bin/env python3
"""Où part l'argent de l'API — par POSTE, et rapporté à ce que ça produit.

Franck, 2026-08-10 : « je consomme beaucoup trop de token API pour le résultat
médiocre ». La question est juste, et jusqu'à ce jour le dépôt ne savait pas y
répondre : `utils.usage.summarize()` agrège par SEMAINE et par MODÈLE, jamais par
POSTE. Or « c'est Sonnet qui coûte » ne dit pas quoi couper — savoir que le panel de
relecture pèse plus que la rédaction, si.

Deux angles, parce qu'un seul ment :

  • LE COÛT PAR POSTE — combien chaque étape coûte, en euros et en part du total. C'est
    là qu'on voit qu'un poste discret mais très répété dépasse un poste cher mais rare.
  • LE COÛT PAR FICHE PUBLIÉE — le seul chiffre qui réponde à « pour quel résultat ». Un
    pipeline qui dépense 40 € pour mettre 12 fiches en ligne coûte 3,30 € la fiche, et
    c'est ça qu'on discute, pas le total.

⚠️ CE QUE CE RAPPORT NE SAIT PAS. Les postes n'ont commencé à être mesurés qu'au fur et
à mesure : `panel_lecteur`, `site_officiel_recherche`, `datation`, `lieu`,
`traduction_*`, `requete_visuelle` ont été instrumentés le 2026-08-11. Tout ce qui
précède cette date les SOUS-ESTIME — le rapport le dit en tête plutôt que de laisser
croire à une répartition complète (règle 6 : rapporter le résultat, pas l'intention).

LECTURE SEULE : aucune écriture, ni en base ni sur le site.

Exemples :
  .venv/bin/python -m scripts.audit_couts               # 7 derniers jours
  .venv/bin/python -m scripts.audit_couts --jours 30
  .venv/bin/python -m scripts.audit_couts --depuis 2026-08-11   # depuis l'instrumentation
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

USAGE_FILE = ROOT / "logs" / "api_usage.jsonl"
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Date à partir de laquelle TOUS les postes sont instrumentés (cf. docstring). Avant
# cette date, la répartition par poste est incomplète et il faut le dire.
INSTRUMENTATION_COMPLETE = "2026-08-11"

# Ce que chaque poste sert, en une ligne — pour que le tableau se lise sans le code.
QUOI = {
    "enrichissement": "rédaction de l'article (modèle qualité, recherche web)",
    "panel_lecteur": "relecture par les personas (3-4 par fiche, ×2 si révision)",
    "site_officiel_recherche": "recherche de la page officielle (recherche web)",
    "évaluation": "note éditoriale de chaque fiche scrapée",
    "datation": "extraction des dates quand le texte ne suffit pas",
    "date_web": "dernier recours : recherche web de la date",
    "lieu": "extraction du lieu et de la ville",
    "venue_web": "dernier recours : recherche web du lieu",
    "seo": "titre, méta, FAQ (10 fiches/jour)",
    "traduction_titre": "traduction du titre et du chapô",
    "traduction_article": "traduction du corps de l'article",
    "requete_visuelle": "formulation de la requête image",
    "image_verify": "vérification que la photo correspond à l'événement",
    "image_audit": "audit des photos déjà en ligne",
    "image_web_search": "recherche d'image sur le web",
    "image_multi_search": "recherche d'image, seconde passe",
    "conformité": "mise en conformité des articles",
    "extraction newsletter": "lecture des newsletters reçues",
    "social_caption": "légendes réseaux sociaux",
    "panel_site": "relecture du SITE par les personas",
    "classement_cinema": "tri des séances de cinéma",
    "organizer_handle_search": "recherche des comptes sociaux d'un organisateur",
}


def _euros(usd: float) -> str:
    return f"{usd:7.2f} $"


def _lire(depuis: str) -> list[dict]:
    if not USAGE_FILE.exists():
        return []
    out = []
    for ligne in USAGE_FILE.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(ligne)
        except json.JSONDecodeError:
            continue
        if (e.get("ts") or "")[:10] >= depuis:
            out.append(e)
    return out


def _fiches_publiees(depuis: str) -> int:
    """Fiches réellement mises en ligne sur la période — le dénominateur. On compte les
    PUBLICATIONS, pas les fiches en base : c'est ce que l'argent a produit."""
    if not DB_PATH.exists():
        return 0
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM events_raw WHERE published_as_date IS NOT NULL "
            "AND replace(published_as_date,'T',' ') >= ?", (depuis,)).fetchone()[0]
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Coût de l'API par poste (lecture seule).")
    p.add_argument("--jours", type=int, default=7, help="Fenêtre en jours (défaut 7).")
    p.add_argument("--depuis", default="", help="Date de début AAAA-MM-JJ (prioritaire).")
    args = p.parse_args(argv)

    depuis = args.depuis or (
        datetime.now(timezone.utc) - timedelta(days=args.jours)).date().isoformat()
    evts = _lire(depuis)
    if not evts:
        print(f"Aucun appel enregistré depuis le {depuis}.")
        print(f"(journal : {USAGE_FILE})")
        return 0

    par_poste = defaultdict(lambda: {"cost": 0.0, "in": 0, "out": 0, "web": 0, "n": 0})
    total = {"cost": 0.0, "in": 0, "out": 0, "web": 0, "n": 0}
    for e in evts:
        b = par_poste[e.get("label") or "(sans nom)"]
        for cle, champ in (("cost", "cost"), ("in", "in"), ("out", "out"), ("web", "web")):
            b[cle] += e.get(champ, 0) or 0
            total[cle] += e.get(champ, 0) or 0
        b["n"] += 1
        total["n"] += 1

    print(f"═══ Coût API du {depuis} à aujourd'hui ═══\n")
    if depuis < INSTRUMENTATION_COMPLETE:
        print(f"⚠️  Avant le {INSTRUMENTATION_COMPLETE}, plusieurs postes n'étaient pas")
        print("    mesurés (panel de relecture, recherche de site officiel, datation,")
        print("    lieu, traductions, requêtes visuelles). La répartition ci-dessous les")
        print("    SOUS-ESTIME. Pour une image juste, relancer avec")
        print(f"    --depuis {INSTRUMENTATION_COMPLETE} dans quelques jours.\n")

    print(f"{'poste':28} {'coût':>9} {'part':>6} {'appels':>7} {'$/appel':>9}  à quoi ça sert")
    print("─" * 118)
    for nom, b in sorted(par_poste.items(), key=lambda kv: -kv[1]["cost"]):
        part = 100 * b["cost"] / total["cost"] if total["cost"] else 0
        print(f"{nom[:28]:28} {_euros(b['cost'])} {part:5.1f}% {b['n']:7} "
              f"{b['cost']/max(b['n'],1):8.4f} $  {QUOI.get(nom, '')}")
    print("─" * 118)
    print(f"{'TOTAL':28} {_euros(total['cost'])} {100.0:5.1f}% {total['n']:7}")
    print(f"\nJetons : {total['in']:,} en entrée · {total['out']:,} en sortie · "
          f"{total['web']} recherche(s) web".replace(",", " "))

    publiees = _fiches_publiees(depuis)
    print(f"\n═══ Ce que ça a produit ═══\n")
    print(f"{publiees} fiche(s) publiée(s) ou republiée(s) sur la période.")
    if publiees:
        print(f"Coût par fiche mise en ligne : {total['cost']/publiees:.2f} $")
    else:
        # Un dénominateur nul n'est pas un détail : c'est la pire nouvelle du rapport.
        print("Aucune publication sur la période — la totalité de cette dépense n'a rien "
              "mis en ligne.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
