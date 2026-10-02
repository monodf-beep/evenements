#!/usr/bin/env python3
"""Fixture : tarif, horaires, réservation — LUS sur la page, jamais devinés.

Franck, 2026-08-11 : « c'est toujours trop de tâches. Il faut que le script aille chercher
les informations dans les ressources officielles. »

Le dépôt ne le permettait pas : sur 81 colonnes, aucune ne stocke un tarif, un horaire ou
une condition d'accès. Ces faits ne vivaient que dans le texte de l'article, donc quand ils
manquaient, la seule issue prévue était d'ouvrir une tâche — d'où les « Tarifs de la Fête
du Fort du Mont », « Langue de la médiation (FR/IT/EN ?) », « Capacités d'accueil des
sorties » qui remplissaient l'écran. Ces informations sont pourtant écrites sur la page de
l'organisateur.

CE QUE LA FIXTURE PROTÈGE AVANT TOUT : que rien ne soit inventé. Un tarif faux sur le site
est pire qu'un tarif absent — une page muette doit rendre un dictionnaire VIDE, et
l'absence de prix ne doit JAMAIS se conclure en « gratuit ».

Les extraits rendus sont volontairement larges (la phrase autour du motif) : « 12 € »
isolé peut être le plein tarif, le réduit, le prix du catalogue ou celui du parking. La
phrase tranche, le nombre seul ment.

Lancer : .venv/bin/python -m tests.test_infos_pratiques
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.infos_pratiques import extraire  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


FR = """<html><body><h1>Festival Baroque</h1>
<p>Ouverture des portes à 19h30, concert à 20h00.</p>
<p>Tarif plein : 18 €, tarif réduit 12 € pour les moins de 26 ans.</p>
<p>Places limitées, sur réservation à la billetterie du théâtre.</p>
<p>Salle accessible aux personnes à mobilité réduite (PMR).</p>
<p>Conférence en français avec traduction simultanée en italien.</p></body></html>"""

IT = """<html><body><p>Ingresso libero fino a esaurimento posti.</p>
<p>Orari: dalle 10.00 alle 18.00, ultimo ingresso alle 17.30.</p>
<p>Visita su prenotazione. Audioguida in italiano e inglese.</p></body></html>"""

MUETTE = "<html><body><p>Un très bel événement culturel vous attend cet été.</p></body></html>"
SCRIPT = ('<html><head><script>var prix = "12 €"; var horaire = "20h00";</script></head>'
          '<body><p>Rien à signaler.</p></body></html>')

print("──── page française complète ────")
fr = extraire(FR)
for cle in ("tarif", "horaires", "reservation", "accessibilite", "langue"):
    _check(f"{cle} trouvé", cle in fr, str(sorted(fr)))
_check("l'extrait de tarif porte le montant, pas juste le mot",
       any("18" in x or "12" in x for x in fr.get("tarif", [])), str(fr.get("tarif")))
_check("l'extrait donne la PHRASE, pas le nombre seul",
       all(len(x) > 25 for x in fr.get("tarif", [])), str(fr.get("tarif")))

print("\n──── page italienne ────")
it = extraire(IT)
_check("ingresso libero reconnu comme tarif", "tarif" in it, str(sorted(it)))
_check("orari reconnus", "horaires" in it, str(sorted(it)))
_check("su prenotazione reconnu", "reservation" in it, str(sorted(it)))
_check("audioguida reconnue comme langue", "langue" in it, str(sorted(it)))

print("\n──── ce qui doit rendre VIDE — le plus important ────")
_check("page sans information pratique → rien du tout", extraire(MUETTE) == {},
       str(extraire(MUETTE)))
_check("l'absence de prix ne devient JAMAIS « gratuit »",
       "tarif" not in extraire(MUETTE), str(extraire(MUETTE)))
_check("le contenu des <script> est ignoré (un prix en JavaScript n'est pas un tarif)",
       extraire(SCRIPT) == {}, str(extraire(SCRIPT)))
_check("page vide → rien, et aucune exception", extraire("") == {})
_check("HTML illisible → rien", extraire("<<<>>>") == {})

print("\n──── bornage ────")
_check("deux extraits au plus par famille (on ne recopie pas la page)",
       all(len(v) <= 2 for v in fr.values()), str({k: len(v) for k, v in fr.items()}))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
