#!/usr/bin/env python3
"""Fixture : scripts.audit_langue_texte voit un texte publié dans l'autre langue que sa
page, et se TAIT quand il ne peut pas justifier son verdict.

Cas réels du 23/09/2026 (fiches des Journées du patrimoine retouchées à la main) :
WP#10487, page française, texte « Torino ospita dal 6 al 18 ottobre… » ; WP#10647, page
italienne, texte « Du 24 au 26 septembre, le centre de Biella… ».

Cas qui doivent PASSER, près de la frontière : une page française dont le texte cite de
longs noms italiens (« Plaisirs de Culture », « Museo regionale di Scienze naturali ») ;
une page courte (pas assez de mots-outils) rend « muet », jamais un écart.

Aucun réseau. Lancer : .venv/bin/python -m tests.test_audit_langue_texte
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.audit_langue_texte import verdict, texte_brut  # noqa: E402

echecs = 0


def _check(label, obtenu, attendu):
    global echecs
    if obtenu == attendu:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} : {obtenu!r}, attendu {attendu!r}")


def page(link, html_):
    return {"link": link, "content": {"rendered": html_}}


FR = "https://agendasabauda.eu/evenement/x/"
IT = "https://agendasabauda.eu/it/evenement/x/"
TXT_IT = ("<p>Torino ospita dal 6 al 18 ottobre 2026 la 31ª edizione del Festival delle "
          "Colline Torinesi, tredici giorni di teatro, danza e performance distribuiti tra il "
          "Teatro Astra e la Fondazione Merz. Il programma della rassegna propone una serie di "
          "spettacoli per il pubblico della città e degli ospiti, con una sezione dedicata "
          "alle nuove generazioni e degli incontri con gli artisti nel foyer.</p>")
TXT_FR = ("<p>Du 24 au 26 septembre, le centre de Biella, dans le Piémont, accueille la "
          "deuxième édition de « La Musica incontra la Moda ». Trois jours de rendez-vous "
          "mêlent la musique, la mode et les archives de la ville, avec des concerts dans les "
          "cours, un défilé dans la rue principale et des conférences pour le public.</p>")

_check("10487 : page française, texte italien → écart",
       verdict(page(FR, TXT_IT))[2], "ecart")
_check("10647 : page italienne, texte français → écart",
       verdict(page(IT, TXT_FR))[2], "ecart")
_check("page française, texte français → ok", verdict(page(FR, TXT_FR))[2], "ok")
_check("FRONTIÈRE : texte français truffé de noms italiens → ok",
       verdict(page(FR, "<p>Le Museo regionale di Scienze naturali, au Castello di "
                        "Saint-Pierre, propose dans le cadre de Plaisirs de Culture en Vallée "
                        "d'Aoste un atelier pour les enfants de la ville et des environs, avec "
                        "des planches de dessin et une visite des salles du musée.</p>"))[2],
       "ok")
_check("FRONTIÈRE : texte trop court → muet, jamais un écart",
       verdict(page(FR, "<p>Castello Gamba, 18.00. Ingresso libero.</p>"))[2], "muet")
_check("le pied « En savoir plus » est retiré avant le compte",
       texte_brut("<p>Texte.</p><p>En savoir plus Site officiel : x.it della della</p>"),
       "Texte.")

print()
if echecs:
    print(f"{echecs} ÉCHEC(S)")
    sys.exit(1)
print("Tout passe.")
