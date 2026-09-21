#!/usr/bin/env python3
"""Fixture : la carte des automatisations (/process) ne peut pas mentir en silence.

CE QU'ELLE FERME. Une page de documentation vieillit sans prévenir — c'est exactement
ce qu'a fait `_PIPELINE_SCHEDULE` dans `app/app.py`, qui annonce encore aux visiteurs
de `/pipeline` un « pipeline complet à 6h05 » disparu du crontab depuis des mois.
Personne ne l'a vu parce que rien ne le TESTAIT. Une carte de quarante automatisations
a le même défaut en pire : elle a l'air complète, donc on la croit.

LES QUATRE GARANTIES, et pourquoi chacune :

1. **Aucune ligne de `crontab.txt` sans nœud.** C'est la garantie principale : ajouter
   un cron demain sans sa fiche fait ÉCHOUER cette fixture, donc le commit. Sans elle,
   la carte se dégraderait exactement comme la liste du chien de garde s'était dégradée
   avant le 2026-08-04 (« quatorze » recopié dans trois fichiers, dix-neuf au crontab).

2. **Aucun nœud annonçant un cron que le crontab ne porte pas.** L'inverse du 1 : une
   fiche qui survit à la suppression de son cron raconte un traitement qui ne tourne
   plus. C'est le défaut de `_PIPELINE_SCHEDULE`, pris par l'autre bout.

3. **Les angles morts sont NOMMÉS, pas découverts.** Deux crons ne figurent pas dans la
   liste du chien de garde. Ce n'est pas la fixture qui doit l'interdire — c'est une
   décision, pas un bug — mais elle EXIGE que la carte les compte. Si un troisième
   apparaît, il sera affiché en haut de la page le jour même.

4. **Un cas qui doit PASSER, près de la frontière.** CLAUDE.md l'impose pour tout
   portillon : « la fixture doit contenir un cas qui doit PASSER, choisi près de la
   frontière. Un test qui ne cherche qu'à se donner raison ne prouve rien. » Ici, la
   contre-épreuve est double — on vérifie qu'un crontab de synthèse AVEC une ligne
   inconnue est bien REFUSÉ (le détecteur peut donc virer au rouge), et qu'un crontab
   dont toutes les lignes sont couvertes est bien ACCEPTÉ.

Aucun réseau, aucune base : lecture de fichiers du dépôt.

Lancer : .venv/bin/python -m tests.test_carte_automatisations
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import automatisations as A  # noqa: E402
from app.automatisations_noeuds import LIENS, NOEUDS, ONGLETS  # noqa: E402

echecs = 0


def rate(msg: str) -> None:
    global echecs
    echecs += 1
    print(f"✗ {msg}")


def passe(msg: str) -> None:
    print(f"✓ {msg}")


# ── 0. Cohérence interne : pas d'identifiant en double, pas de lien fantôme ──
ids = [n["id"] for n in NOEUDS]
doublons = sorted({i for i in ids if ids.count(i) > 1})
if doublons:
    rate(f"identifiants de nœud en double : {doublons}")
else:
    passe(f"{len(NOEUDS)} nœuds, tous d'identifiant unique")

flux_connus = {o["id"] for o in ONGLETS}
hors_onglet = [n["id"] for n in NOEUDS if n.get("flux") not in flux_connus]
if hors_onglet:
    rate(f"nœuds rangés dans un onglet inexistant : {hors_onglet}")
else:
    passe(f"{len(ONGLETS)} onglets, tous les nœuds rangés dans l'un d'eux")

connus = set(ids)
casses = [l for l in LIENS if l["de"] not in connus or l["vers"] not in connus]
if casses:
    rate(f"liens vers un nœud inexistant : {casses}")
else:
    passe(f"{len(LIENS)} liens, tous entre des nœuds existants")

# Un lien qui traverse deux onglets ne sera JAMAIS dessiné (le gabarit ne garde que les
# liens intra-onglet). Le laisser en base de données, c'est croire qu'on a représenté
# quelque chose qu'on n'a pas représenté.
par_flux = {n["id"]: n.get("flux") for n in NOEUDS}
traversants = [(l["de"], l["vers"]) for l in LIENS
               if par_flux.get(l["de"]) != par_flux.get(l["vers"])]
if traversants:
    rate(f"liens entre deux onglets différents — ils ne seront pas dessinés : {traversants}")
else:
    passe("aucun lien traversant : tout ce qui est déclaré est effectivement dessiné")


# ── 1. Aucune ligne de crontab sans nœud ────────────────────────────────────
noeuds, orphelines = A.apparier()
if orphelines:
    for o in orphelines:
        rate(f"ligne de crontab sans nœud sur la carte : {o['commande_nue'][:80]}")
    print("   → ajouter une fiche dans app/automatisations_noeuds.py, avec son `cron_cle`.")
else:
    passe(f"{len(A.lignes_crontab())} lignes de crontab, toutes représentées")


# ── 2. Aucun nœud annonçant un cron absent du crontab ───────────────────────
fantomes = [n["id"] for n in noeuds if n.get("cron_absent")]
if fantomes:
    for f in fantomes:
        rate(f"le nœud « {f} » annonce un cron que crontab.txt ne porte pas")
    print("   → le cron a-t-il été retiré ? Retirer la fiche, ou corriger son `cron_cle`.")
else:
    passe("aucune fiche ne décrit un cron disparu")


# ── 3. Les angles morts sont comptés ────────────────────────────────────────
# Volontairement PAS une interdiction : ne pas surveiller un cron peut se décider.
# Ce qui ne se décide pas, c'est de l'ignorer.
carte = A.carte()
angles = [n["label"] for n in carte["angles_morts"]]
attendus = {"Lieux et images des mails", "Notes Yoast"}
if set(angles) != attendus:
    rate(f"la liste des crons non surveillés a changé : {sorted(angles)} "
         f"(attendu {sorted(attendus)})")
    print("   → si c'est volontaire, mettre cette fixture à jour ET vérifier que la page "
          "les affiche. Si c'est un oubli, ajouter la ligne à ATTENDUS dans "
          "scripts/watchdog_crons.py.")
else:
    passe(f"{len(angles)} crons non surveillés, nommés et affichés en haut de la page")


# ── 4. Les contre-épreuves : le détecteur peut-il virer au rouge ? ───────────
# 4a. Un crontab porteur d'une ligne que nul nœud ne réclame DOIT produire une orpheline.
with tempfile.TemporaryDirectory() as tmp:
    faux = Path(tmp) / "crontab.txt"
    faux.write_text(
        "# commentaire ignoré\n"
        "SLACK_DIGEST=1\n"
        "0 8 * * * cd /root/evenements && .venv/bin/python scripts/scraper_events.py "
        ">> logs/scraper.log 2>&1\n"
        "30 4 * * * cd /root/evenements && .venv/bin/python -m scripts.invente_par_la_fixture "
        ">> logs/invente.log 2>&1\n",
        encoding="utf-8")
    lignes = A.lignes_crontab(faux)
    _, orph = A.apparier(NOEUDS, lignes)
    if len(orph) == 1 and "invente_par_la_fixture" in orph[0]["commande"]:
        passe("contre-épreuve : une ligne de crontab inconnue est bien REFUSÉE")
    else:
        rate(f"contre-épreuve ratée — une ligne inconnue n'a pas été signalée : {orph}")

    # 4b. Le cas qui doit PASSER, choisi près de la frontière : le MÊME fichier privé de
    # sa seule ligne intruse doit être accepté sans aucune orpheline. Sans ce second
    # cas, la fixture passerait au vert sur un détecteur qui refuserait TOUT.
    faux.write_text(
        "# commentaire ignoré\n"
        "SLACK_DIGEST=1\n"
        "0 8 * * * cd /root/evenements && .venv/bin/python scripts/scraper_events.py "
        ">> logs/scraper.log 2>&1\n",
        encoding="utf-8")
    _, orph2 = A.apparier(NOEUDS, A.lignes_crontab(faux))
    if orph2:
        rate(f"contre-épreuve ratée — une ligne pourtant couverte a été signalée : {orph2}")
    else:
        passe("contre-épreuve : un crontab entièrement couvert est bien ACCEPTÉ")

# 4c. La lecture de l'horaire : c'est elle qui remplace le chiffre recopié. Si elle se
# trompe, la carte ment avec l'air d'être à jour.
cas = [
    (("30", "7", "*", "*", "0"), "le dimanche à 7h30"),
    (("0", "8", "*", "*", "1"), "le lundi à 8h00"),
    (("50", "7", "*", "*", "*"), "tous les jours à 7h50"),
    (("5", "12", "*", "*", "*"), "tous les jours à 12h05"),
]
mauvais = [(c, A.horaire_humain(*c), v) for c, v in cas if A.horaire_humain(*c) != v]
if mauvais:
    rate(f"horaires mal rendus : {mauvais}")
else:
    passe("les horaires du crontab sont rendus en français, minute par minute")


# ── 5. Les fiches disent-elles quelque chose ? ──────────────────────────────
# Un nœud sans résumé est un nœud qui a l'air documenté et ne l'est pas.
muets = [n["id"] for n in NOEUDS if not (n.get("resume") or "").strip()]
if muets:
    rate(f"nœuds sans résumé : {muets}")
else:
    passe("chaque nœud porte au moins une phrase de résumé")

# Tout état terminal déclaré doit nommer son rouvreur (docs/ETATS_TERMINAUX.md, règle 3).
sans_rouvreur = [n["id"] for n in NOEUDS
                 if (n.get("detail") or {}).get("terminal")
                 and not (n["detail"]["terminal"].get("rouvreur") or "").strip()]
if sans_rouvreur:
    rate(f"états terminaux sans rouvreur nommé : {sans_rouvreur}")
else:
    passe("chaque état terminal décrit nomme qui le rouvre")


print()
if echecs:
    print(f"À REPRENDRE : {echecs} contrôle(s) en échec.")
    sys.exit(1)
print("Carte des automatisations : tout est cohérent.")
