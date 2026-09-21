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


# ── 3. Aucun cron sans surveillance ─────────────────────────────────────────
# ÉTAT AU 2026-09-21 : zéro. Ce contrôle valait d'abord « les deux angles morts connus
# sont nommés » — la carte en avait trouvé deux (completer_depuis_mail et yoast_scores)
# que la liste du chien de garde ignorait. Ils y sont entrés le jour même, et cette
# fixture a fait ce qu'on attend d'elle : elle est passée au ROUGE sur le changement,
# au lieu de laisser la correction se perdre.
#
# Elle devient donc une interdiction, ce qui est plus fort et plus simple à tenir : un
# cron ajouté sans sa ligne dans ATTENDUS fait échouer le commit. Si un jour on décide
# sciemment de ne pas surveiller un cron — c'est possible, un cron éteint ou purement
# décoratif — il faut l'inscrire ICI avec sa raison, pas juste le laisser passer.
carte = A.carte()
angles = [n["label"] for n in carte["angles_morts"]]
TOLERES: set[str] = set()   # aucun pour l'instant, et c'est bien
if set(angles) - TOLERES:
    for a in sorted(set(angles) - TOLERES):
        rate(f"« {a} » tourne en cron mais n'est surveillé par personne")
    print("   → ajouter sa ligne (libellé, script, fichier de log, tolérance) à ATTENDUS "
          "dans scripts/watchdog_crons.py. Attention : le nom du log suit la REDIRECTION "
          "du crontab, pas le nom du script.")
else:
    passe(f"aucun cron sans surveillance ({len(A.scripts_surveilles())} entrées au chien "
          f"de garde)")


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


# ── 6. La charge : les compteurs peuvent-ils valoir AUTRE CHOSE que zéro ? ───
# « Un témoin ne prouve rien s'il n'a jamais été rouge » (docs/ERREURS_2026-09-14).
# Sans base, la carte écrit « je ne peux pas le savoir » — c'est le bon comportement,
# mais il ne démontre pas que le branchement fonctionne. On le démontre ici sur une base
# JETABLE, jamais sur data/events.db : dix fiches retenues, sept datées, et l'étage
# « Datés » DOIT sortir à 70 %, donc sous le seuil de 90 %, donc désigné comme goulot.
import os as _os  # noqa: E402
import sqlite3 as _sq  # noqa: E402

with tempfile.TemporaryDirectory() as _tmp:
    _bd = Path(_tmp) / "essai.db"
    _avant = _os.environ.get("DB_PATH")
    _os.environ["DB_PATH"] = str(_bd)
    try:
        from scripts.scraper_events import init_db as _init
        _c = _sq.connect(_bd)
        _init(_c)
        for _col in ("date_tentatives INTEGER DEFAULT 0",):
            try:
                _c.execute("ALTER TABLE events_raw ADD COLUMN " + _col)
            except _sq.OperationalError:
                pass
        for _i in range(10):
            _c.execute(
                "INSERT INTO events_raw (title,url_source,statut,llm_score,"
                "date_event_start,lieu,ville,territoire,llm_categorie,url_image) "
                "VALUES (?,?,'evaluated',7,?,'L','V','Savoie','Concerts','http://i/x.jpg')",
                (f"E{_i}", f"http://x/{_i}", "2099-01-01" if _i < 7 else ""))
        _c.execute("INSERT INTO events_raw (title,url_source,statut) "
                   "VALUES ('P','http://p/1','pending')")
        _c.commit()
        _c.close()

        _ch = A.charge()
        if not _ch:
            rate("la charge reste illisible alors qu'une base est disponible")
        elif _ch["etages"]["date"]["pct"] != 70:
            rate(f"l'étage « Datés » devrait valoir 70 %, il vaut "
                 f"{_ch['etages']['date']['pct']} %")
        elif not _ch.get("goulot") or _ch["goulot"]["cle"] != "date":
            rate(f"le goulot devrait être « Datés », c'est "
                 f"{(_ch.get('goulot') or {}).get('cle')}")
        elif _ch["garages"]["pending"]["n"] != 1:
            rate(f"le garage « en attente d'évaluation » devrait valoir 1, il vaut "
                 f"{_ch['garages']['pending']['n']}")
        else:
            passe("contre-épreuve : sur une base nourrie, les files se comptent et le "
                  "goulot est désigné")
    except Exception as exc:  # noqa: BLE001
        rate(f"la contre-épreuve de charge a échoué : {exc}")
    finally:
        if _avant is None:
            _os.environ.pop("DB_PATH", None)
        else:
            _os.environ["DB_PATH"] = _avant


print()
if echecs:
    print(f"À REPRENDRE : {echecs} contrôle(s) en échec.")
    sys.exit(1)
print("Carte des automatisations : tout est cohérent.")
