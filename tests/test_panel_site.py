#!/usr/bin/env python3
"""Fixture : tout ce que le panel de personas + coordinateur peut prouver SANS
appel LLM — doctrine, récupération de page (contre le VRAI site, aucune clé API
nécessaire), construction du prompt, et le coordinateur sur des trouvailles
RECONSTRUITES à la main (jamais générées par un vrai persona : ce module ne peut
pas être testé de bout en bout sans crédit API, cf. docstring de scripts/panel_site.py).

Lancer : .venv/bin/python -m tests.test_panel_site
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import doctrine as doctrine_mod  # noqa: E402
import scripts.panel_site as panel  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ══════════════ utils/doctrine.py ══════════════
print("──── doctrine : fichier réel du dépôt ────")
d = doctrine_mod.load_doctrine()
_check("au moins l'entrée « Pas de prix chiffré » chargée",
      any("prix" in e["titre"].lower() for e in d), str(d))

bloc = doctrine_mod.doctrine_pour_prompt(d)
_check("le bloc de prompt mentionne le prix sans jargon de fichier",
      "prix" in bloc.lower() and "config/" not in bloc, bloc[:200])

print("\n──── doctrine : contredit_doctrine, paraphrases plausibles ────")
cas = [
    ("Il manque le prix de l'entrée sur cette fiche", True),
    ("On ne voit jamais le tarif exact, juste gratuit ou payant", False),  # "tarif" pas "prix"
    ("Le lieu de cet événement n'est pas indiqué", False),
    ("Le prix affiché est faux, il fallait 12€", True),
]
for texte, attendu in cas:
    r = doctrine_mod.contredit_doctrine(texte, d)
    _check(f"« {texte[:45]}… » → contredit={bool(r)} (attendu {attendu})", bool(r) == attendu)

# ══════════════ scripts/panel_site.py : fetch (site réel, pas d'API) ══════════════
print("\n──── fetch_page_text sur le VRAI site (aucune clé API nécessaire) ────")
texte_home = panel.fetch_page_text("https://agendasabauda.eu/")
_check(f"page d'accueil récupérée ({len(texte_home)} caractères)", len(texte_home) > 200)

texte_bidon = panel.fetch_page_text("https://agendasabauda.eu/cette-page-n-existe-pas-du-tout/")
_check("page inexistante → chaîne vide ou tolérée sans exception", isinstance(texte_bidon, str))

# ══════════════ construction du prompt (déterministe) ══════════════
print("\n──── _prompt_persona : construction déterministe ────")
persona_test = {"title": "Kévin (Maurienne)", "text": "Ouvrier de vallée, sceptique."}
prompt = panel._prompt_persona(persona_test, "Accueil", "Contenu de test.",
                               doctrine_mod.doctrine_pour_prompt(d))
_check("le prompt embarque la voix du persona", "Ouvrier de vallée" in prompt)
_check("le prompt embarque le contenu de la page", "Contenu de test." in prompt)
_check("le prompt embarque la doctrine (prix)", "prix" in prompt.lower())

# ══════════════ le coordinateur, sur des trouvailles reconstruites ══════════════
print("\n──── coordonner() : rejet doctrine / isolé / motif ────")
trouvailles = [
    # Deux personas indépendants signalent la MÊME chose sur la home → motif.
    {"type": "hors_saison", "texte": "Un marché de Noël apparaît alors qu'on est en août.",
     "persona": "Kévin", "page": "Accueil"},
    {"type": "hors_saison", "texte": "Événement de Noël visible en plein été, bizarre.",
     "persona": "Manuela", "page": "Accueil"},
    # Un seul persona → isolé.
    {"type": "manque", "texte": "Il n'y a pas assez de concerts de musique classique.",
     "persona": "Chantal", "page": "Accueil"},
    # Contredit la doctrine → rejeté.
    {"type": "info_manquante", "texte": "Il manque le prix sur plusieurs fiches.",
     "persona": "Jean-Pierre", "page": "Savoie / Haute-Savoie"},
    # Même persona répété deux fois ne doit PAS compter comme 2 personas distincts.
    {"type": "exces", "texte": "Trop de festivals de musique électronique.",
     "persona": "Karine", "page": "Comté de Nice"},
    {"type": "exces", "texte": "Encore un festival électro, ça sature.",
     "persona": "Karine", "page": "Comté de Nice"},
]
res = panel.coordonner(trouvailles, d, seuil=2)

_check(f"1 motif détecté (2 personas indépendants, home, hors_saison) : {len(res['motifs'])}",
      len(res["motifs"]) == 1 and res["motifs"][0]["n_personas"] == 2)
_check(f"1 trouvaille rejetée par la doctrine : {len(res['rejetees'])}",
      len(res["rejetees"]) == 1 and "prix" in res["rejetees"][0]["doctrine_contredite"].lower())
_check(f"le reste (Chantal seule, Karine répétée) reste isolé : {len(res['isolees'])}",
      len(res["isolees"]) == 3)  # Chantal (1) + Karine×2 (même persona, jamais un motif)

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
