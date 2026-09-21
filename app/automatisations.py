#!/usr/bin/env python3
"""LE MOTEUR DE LA CARTE DES AUTOMATISATIONS (page `/process`).

Ce module ne contient AUCUN texte de description : les fiches vivent dans
`app/automatisations_noeuds.py`. Ici, seulement la mécanique — apparier les nœuds avec
`crontab.txt`, aller chercher leur dernier passage réel, et rendre le tout prêt à
dessiner.

TROIS PRINCIPES, tirés des règles du dépôt.

1. **L'HORAIRE N'EST JAMAIS RECOPIÉ.** `app/templates/pipeline.html` affiche depuis des
   mois un planning (`_PIPELINE_SCHEDULE`) qui annonce un « pipeline complet à 6h05 » —
   cette ligne n'existe plus dans `crontab.txt`. C'est exactement le défaut que CLAUDE.md
   décrit : un chiffre recopié cesse d'être vrai le jour où on change l'original, et
   personne ne le remarque. Ici, chaque nœud porte une CLÉ (`cron_cle`) qu'on cherche
   dans les commandes du crontab ; l'heure, la commande et le fichier de journal sont
   LUS, jamais écrits à la main.

2. **UN SEUL DÉTECTEUR D'ÉTAT.** `scripts/watchdog_crons.py` sait déjà dire, pour chaque
   automatisation, quand elle a tourné pour la dernière fois et si elle est en retard —
   en croisant la table `pipeline_runs` et la date d'écriture du journal. Écrire un
   second détecteur ici, c'est la faute « deux détecteurs pour la même chose, un seul
   juste » (docs/ERREURS_2026-09-08.md). On appelle donc `watchdog_crons.etat()`.

3. **UN ZÉRO DOIT DIRE D'OÙ IL VIENT.** Ce backoffice tourne aussi sur une machine qui
   n'a ni `logs/` ni base — un conteneur de développement, par exemple. Dans ce cas l'état
   n'est pas « tout va mal », il est INCONNU, et la page doit l'écrire. `etat_par_script()`
   renvoie donc un dict vide plutôt que des nœuds en rouge, et `carte()` pose
   `etat_lisible=False` pour que le gabarit le dise en toutes lettres.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.automatisations_noeuds import LIENS, NOEUDS, ONGLETS  # noqa: E402

CRONTAB = ROOT / "crontab.txt"

# Géométrie de la grille. Le gabarit positionne les nœuds en pixels : une colonne tous les
# COL_PX, une rangée tous les ROW_PX. Les coordonnées viennent des champs `col`/`row` des
# fiches — posés à la main, comme dans n8n, parce qu'un placement automatique produit des
# croisements que personne ne sait lire.
COL_PX = 280
ROW_PX = 120
MARGE = 40


# ───────────────────────────────────────────────────────────── crontab.txt ──

_JOURS = {"0": "dimanche", "1": "lundi", "2": "mardi", "3": "mercredi",
          "4": "jeudi", "5": "vendredi", "6": "samedi", "7": "dimanche"}


def horaire_humain(minute: str, heure: str, jour_mois: str, mois: str, jour_sem: str) -> str:
    """« 30 7 * * 0 » → « le dimanche à 7h30 ». Rendu en français, pour Franck.

    On ne couvre QUE les formes réellement présentes dans `crontab.txt` (minute et heure
    fixes, jour de semaine simple ou joker). Toute autre forme est rendue telle quelle
    plutôt que devinée : une traduction approximative d'un horaire serait pire que
    l'expression brute, parce qu'elle serait crue.
    """
    if not (minute.isdigit() and heure.isdigit()):
        return f"{minute} {heure} {jour_mois} {mois} {jour_sem}"
    quand = f"{int(heure)}h{int(minute):02d}"
    if jour_mois == "*" and mois == "*":
        if jour_sem == "*":
            return f"tous les jours à {quand}"
        if jour_sem in _JOURS:
            return f"le {_JOURS[jour_sem]} à {quand}"
    return f"{minute} {heure} {jour_mois} {mois} {jour_sem} — à {quand}"


def lignes_crontab(chemin: Path | None = None) -> list[dict]:
    """Toutes les lignes ACTIVES de `crontab.txt`, décortiquées.

    Une ligne rend : son expression cron, son horaire en français, la commande nue
    (débarrassée du `cd … &&` et de la redirection), et le journal vers lequel elle écrit.
    Les commentaires et les affectations de variables (`SLACK_DIGEST=1`) sont écartés —
    ce ne sont pas des tâches.
    """
    texte = (chemin or CRONTAB).read_text(encoding="utf-8", errors="replace")
    out: list[dict] = []
    for brut in texte.splitlines():
        ligne = brut.strip()
        if not ligne or ligne.startswith("#"):
            continue
        champs = ligne.split(None, 5)
        if len(champs) < 6 or not (champs[0][0].isdigit() or champs[0][0] in "*/"):
            continue  # SLACK_DIGEST=1 et compagnie
        minute, heure, jm, mois, js, commande = champs
        journal = ""
        m = re.search(r">>\s*(logs/[\w./-]+)", commande)
        if m:
            journal = m.group(1)
        nue = re.sub(r"^cd\s+\S+\s*&&\s*", "", commande)
        nue = re.sub(r"\s*>>\s*logs/\S+\s*2>&1\s*;?", "", nue).strip(" {};")
        out.append({
            "cron": f"{minute} {heure} {jm} {mois} {js}",
            "horaire": horaire_humain(minute, heure, jm, mois, js),
            "heure_tri": (int(heure) * 60 + int(minute)) if heure.isdigit() and minute.isdigit() else 0,
            "quotidien": js == "*",
            "commande": commande,
            "commande_nue": nue,
            "journal": journal,
            "brut": ligne,
        })
    return out


# ──────────────────────────────────────────────────────── état des passages ──

def etat_par_script() -> dict[str, dict]:
    """Dernier passage de chaque automatisation, par `scripts.watchdog_crons.etat()`.

    Renvoie {} — et pas un état dégradé — quand le chien de garde ne peut pas répondre :
    ni journaux, ni base, c'est le cas d'un conteneur de développement. Un nœud sans
    entrée ici s'affiche « état inconnu », jamais « en panne ». La différence n'est pas
    cosmétique : c'est la règle « un zéro ne dit pas s'il vient d'un échec ou d'une
    absence de cas ».
    """
    try:
        from scripts import watchdog_crons
        lignes = watchdog_crons.etat()
    except Exception:  # base absente, import impossible, journaux illisibles
        return {}
    # AUCUNE trace nulle part = on ne SAIT pas, ce n'est pas « tout est en panne ».
    # Sans ce test, une machine de développement (ni `logs/`, ni base) afficherait
    # trente-cinq pastilles oranges parfaitement fausses — la règle 1 du dépôt, et le
    # zéro qui ne dit pas d'où il vient.
    if not any(l.get("vu") for l in lignes):
        return {}
    par_script: dict[str, dict] = {}
    for l in lignes:
        vu: datetime | None = l.get("vu")
        # L'ordre compte : « jamais vu » passe AVANT « en retard », que le chien de garde
        # met aussi à vrai dans ce cas. Les deux méritent d'être dits, jamais confondus.
        if vu is None:
            niveau = "inconnu"
        elif l.get("erreurs"):
            niveau = "erreur"
        elif l.get("en_retard"):
            niveau = "retard"
        else:
            niveau = "ok"
        par_script[l["script"]] = {
            "niveau": niveau,
            "vu": vu.strftime("%d/%m à %Hh%M") if vu else None,
            "age_h": round(l["retard_h"], 1) if l.get("retard_h") is not None else None,
            "age": _age_humain(l.get("retard_h")),
            "source": l.get("source", ""),
            "tolerance": l.get("tolerance"),
            "erreurs": l.get("erreurs") or 0,
            "libelle": l.get("libelle", ""),
        }
    return par_script


def scripts_surveilles() -> set[str]:
    """Les scripts que `watchdog_crons.ATTENDUS` connaît — indépendamment des journaux.

    Sert à répondre à une question que la pastille d'état ne sait pas poser : « ce cron
    est-il seulement SURVEILLÉ ? » Un cron absent de cette liste peut s'arrêter sans que
    rien ne sonne, et son silence ressemblera trait pour trait à son fonctionnement
    normal. La carte le DIT plutôt que de laisser croire à une surveillance complète.
    """
    try:
        from scripts import watchdog_crons
        return {e[1] for e in watchdog_crons.ATTENDUS}
    except Exception:
        return set()


def _age_humain(heures: float | None) -> str:
    if heures is None:
        return "jamais vu"
    if heures < 1:
        return f"il y a {int(heures * 60)} min"
    if heures < 36:
        return f"il y a {int(heures)} h"
    return f"il y a {int(heures // 24)} j"


# ─────────────────────────────────────────────────────────── appariement ──

def apparier(noeuds: list[dict] | None = None,
             lignes: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    """Colle à chaque nœud sa ligne de crontab. Rend (nœuds enrichis, lignes orphelines).

    L'appariement se fait sur `cron_cle` : un fragment de la commande, choisi pour être
    non ambigu (`scripts/dates.py --no-fetch` plutôt que `dates`). Les orphelines sont le
    filet : `tests/test_carte_automatisations.py` échoue si une ligne du crontab n'est
    représentée par aucun nœud, donc un cron ajouté demain ne peut pas disparaître de la
    carte en silence.
    """
    noeuds = [dict(n) for n in (noeuds if noeuds is not None else NOEUDS)]
    lignes = lignes if lignes is not None else lignes_crontab()
    pris: set[int] = set()
    for n in noeuds:
        cle = n.get("cron_cle")
        if not cle:
            continue
        for i, l in enumerate(lignes):
            if cle in l["commande"]:
                pris.add(i)
                n["cron"] = l["cron"]
                n["horaire"] = l["horaire"]
                n["heure_tri"] = l["heure_tri"]
                n["quotidien"] = l["quotidien"]
                n["commande"] = l["commande_nue"]
                n["journal"] = l["journal"]
                break
        else:
            # Le nœud annonce un cron que le crontab ne porte pas : on le DIT, plutôt que
            # d'afficher un horaire qui n'existe plus (le défaut de `_PIPELINE_SCHEDULE`).
            n["horaire"] = "⚠️ aucune ligne de crontab ne correspond"
            n["cron_absent"] = True
    orphelines = [l for i, l in enumerate(lignes) if i not in pris]
    return noeuds, orphelines


# ─────────────────────────────────────────────────────────────── la carte ──

def carte() -> dict:
    """Tout ce dont le gabarit a besoin : onglets, nœuds placés, liens, état.

    Les coordonnées en pixels sont calculées ICI et pas en JavaScript, pour que la page
    soit lisible même si le script ne se charge pas — les nœuds restent alors empilés,
    chacun avec son panneau accessible.
    """
    noeuds, orphelines = apparier()
    etats = etat_par_script()
    veilles = scripts_surveilles()
    par_id = {}
    for n in noeuds:
        n["x"] = MARGE + n.get("col", 0) * COL_PX
        n["y"] = MARGE + n.get("row", 0) * ROW_PX
        e = etats.get(n.get("script") or "")
        n["etat"] = e or {"niveau": "inconnu", "vu": None, "age": "état inconnu",
                          "source": "", "erreurs": 0}
        # Un nœud SANS clé de surveillance n'est pas « inconnu par accident » : il n'est
        # simplement pas surveillé (une action manuelle, un mu-plugin). Le panneau le dira.
        n["surveille"] = bool(n.get("script")) and bool(etats)
        # Un cron QUI TOURNE mais que le chien de garde ignore : c'est le trou le plus
        # coûteux du dépôt (« un mécanisme qui s'arrête sans que personne en soit
        # averti »). On le signale sur la carte au lieu de le laisser se découvrir.
        n["angle_mort"] = (bool(n.get("cron_cle"))
                           and (n.get("script") or "") not in veilles
                           and not n.get("surveille_par"))
        par_id[n["id"]] = n

    liens = []
    for l in LIENS:
        if l["de"] in par_id and l["vers"] in par_id:
            liens.append(dict(l))

    onglets = []
    for o in ONGLETS:
        dedans = [n for n in noeuds if n.get("flux") == o["id"]]
        largeur = max([n["x"] + 236 for n in dedans], default=600) + MARGE
        hauteur = max([n["y"] + 104 for n in dedans], default=400) + MARGE
        onglets.append({**o, "nb": len(dedans), "largeur": largeur, "hauteur": hauteur,
                        "liens": [l for l in liens
                                  if par_id.get(l["de"], {}).get("flux") == o["id"]
                                  and par_id.get(l["vers"], {}).get("flux") == o["id"]]})

    # La frise horaire : toutes les tâches du crontab, dans l'ordre où elles tombent.
    # Elle se construit à partir du CRONTAB, pas de la liste des nœuds — c'est elle qui
    # fait foi sur « ce qui tourne aujourd'hui ».
    frise = sorted([n for n in noeuds if n.get("heure_tri") is not None and n.get("cron")],
                   key=lambda n: (0 if n.get("quotidien") else 1, n.get("heure_tri", 0)))

    return {
        "onglets": onglets,
        "noeuds": noeuds,
        "liens": liens,
        "frise": frise,
        "orphelines": orphelines,
        "etat_lisible": bool(etats),
        "nb_crons": len(lignes_crontab()),
        "angles_morts": [n for n in noeuds if n.get("angle_mort")],
        "compte": {
            "retard": sum(1 for n in noeuds if n["etat"]["niveau"] == "retard"),
            "erreur": sum(1 for n in noeuds if n["etat"]["niveau"] == "erreur"),
            "ok": sum(1 for n in noeuds if n["etat"]["niveau"] == "ok"),
        },
    }
