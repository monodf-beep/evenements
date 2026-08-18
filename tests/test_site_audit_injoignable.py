#!/usr/bin/env python3
"""Fixture : un site injoignable ne doit pas devenir des centaines de pages « cassées ».

D'OÙ ÇA VIENT — 2026-08-18, 09h58 : l'hébergement du site a cessé de répondre à l'adresse
du VPS, par intermittence (un lot est repassé à 13h01, puis plus rien). Ping perdu à 100 %, ports 80 et 443 expirés, pendant que le reste du réseau
fonctionnait parfaitement. Le cron `site_audit` de 14h aurait relu les fiches publiées une
par une, et `auditer()` rend « page INJOIGNABLE » en gravité GRAVE à chaque échec de
requête : un rapport de plusieurs centaines de lignes graves, toutes fausses, qu'il aurait
fallu démonter à la main pour découvrir qu'il n'y avait qu'UN problème.

CE QUE LA FIXTURE PROTÈGE :

  1. **site injoignable → aucune conclusion, et on le DIT.** Le rapport doit annoncer que
     l'audit n'a PAS eu lieu, pas rendre un verdict sur des pages qu'il n'a pas lues.
     C'est la règle 1 de CLAUDE.md dans sa forme la plus simple : ne jamais conclure sur
     l'état du site sans l'avoir interrogé ;
  2. **le geste utile est nommé.** Une file ne doit contenir que ce qu'un humain peut
     faire (règle 6) ; face à un site hors d'atteinte, c'est « attendre », pas « relire
     trois cents fiches » ;
  3. **LE CAS VOISIN QUI DOIT PASSER** — et c'est lui qui compte, parce qu'un portillon
     qui refuse tout passerait au vert sans lui : quand le site RÉPOND, l'audit doit se
     dérouler normalement. Le contrôle de vie ne doit pas devenir une porte fermée.

Lancer : .venv/bin/python -m tests.test_site_audit_injoignable
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


# ── Le contrôle est-il bien AVANT la boucle, et sans le contourner sur --ids ? ──
# Lecture du source plutôt qu'exécution : `site_audit.main` ouvre la vraie base et
# poste sur Slack. Ce qu'on veut prouver ici est structurel — l'ordre des opérations —
# et il se lit. Les fixtures de comportement du reste du script vivent ailleurs.
src = (ROOT / "scripts" / "site_audit.py").read_text(encoding="utf-8")

i_controle = src.find("Audit du site NON EFFECTUÉ")
i_boucle = src.find("for i, row in enumerate(lot, 1):")
verifier("le contrôle de vie du site existe", i_controle != -1)
verifier("il est placé AVANT la boucle qui juge les fiches une par une",
         -1 < i_controle < i_boucle, f"contrôle={i_controle} boucle={i_boucle}")
verifier("il n'écrit AUCUNE conclusion sur les fiches non relues",
         "Aucune conclusion n'est tirée" in src)
verifier("il nomme le seul geste utile — attendre",
         "le seul geste utile est d'attendre" in src)
verifier("il distingue « hors d'atteinte » de « cassé »",
         "n'est pas un site cassé" in src)
verifier("il sort en code d'erreur : le cron doit savoir que l'audit n'a pas eu lieu",
         "return 1" in src[i_controle:i_controle + 900], src[i_controle:i_controle + 900][-200:])

# ── LE CAS VOISIN QUI DOIT PASSER ──────────────────────────────────────────────
# `--ids` sert à relire des fiches précises, souvent pour vérifier un correctif. Le
# contrôle de vie ne doit pas s'y appliquer : sinon un appel ciblé échouerait sur un
# hoquet de la page d'accueil, et on aurait remplacé un faux positif par un faux refus —
# la faute reprochée aux portillons du 06/08.
verifier("le contrôle NE s'applique PAS à un appel ciblé --ids",
         "if not args.ids:" in src[max(0, i_controle - 1500):i_controle],
         src[max(0, i_controle - 1500):i_controle][-300:])

# ── Et le reste de la chaîne, lui, était déjà correct : on le vérifie, on n'y touche pas ──
# `reconcile_hors_ligne._etat` rend 'indetermine' sur aléa réseau, ce qui n'autorise
# aucune action. C'est ce qui protège `verifier_doublons_publies --en-ligne`, qui tourne
# à 9h50 tous les jours. Le vérifier ici évite qu'un correctif futur le casse sans bruit.
# Lu au source, pas exécuté : `reconcile_hors_ligne` importe `dedupe`, donc
# `scraper_events`, donc `feedparser`, absent de l'environnement où tourne cette fixture.
# Ce qu'on veut prouver est de toute façon structurel — quelle valeur sort de la branche
# d'échec réseau — et c'est exactement ce qui se lit.
etat_src = (ROOT / "scripts" / "reconcile_hors_ligne.py").read_text(encoding="utf-8")
i_def = etat_src.find("def _etat(")
corps = etat_src[i_def:i_def + 1600]
i_exc = corps.find("except requests.RequestException:")
verifier("un aléa réseau rend « indetermine » — jamais « inexistant »",
         -1 < i_exc and 'return "indetermine"' in corps[i_exc:i_exc + 120],
         corps[i_exc:i_exc + 120])


# ── Le faux « tout va bien » de verifier_doublons_publies --en-ligne ────────────
# LE PIÈGE : `_etat` rend « indetermine » quand la requête échoue — c'est le bon choix.
# Mais le filtre ne garde que les groupes dont DEUX pages sont « public ». Site
# injoignable → tous les sondages indéterminés → tous les groupes écartés → le rapport
# annonce « SUSPECTS (VÉRIFIÉS) : 0 ». Un feu vert impeccable, produit par une panne, et
# présenté comme VÉRIFIÉ alors que rien ne l'a été.
#
# C'est « un zéro ne dit pas s'il vient d'un échec ou d'une absence de cas » (CLAUDE.md),
# dans sa version la plus dangereuse : le zéro rassure.
dbl = (ROOT / "scripts" / "verifier_doublons_publies.py").read_text(encoding="utf-8")

verifier("les sondages sans réponse sont COMPTÉS, pas ignorés",
         'compte["indetermines"]' in dbl and 'compte["sondages"]' in dbl)
verifier("un sondage entièrement muet est annoncé comme tel",
         "AUCUNE VÉRIFICATION N'A EU LIEU" in dbl)
verifier("et le zéro rassurant est explicitement DÉSAVOUÉ",
         "ne vaut RIEN" in dbl and "CHIFFRE NON FIABLE" in dbl)
verifier("le rapport dit que ce n'est pas un geste à faire, mais un état à attendre",
         "n'autorise aucun geste" in dbl)
# LE CAS INTERMÉDIAIRE, celui qu'on oublie : quelques sondages échouent, pas tous. Le
# rapport reste utilisable, mais un groupe réel a pu être écarté à tort — il faut le dire
# sans crier au feu, sinon on apprend à ignorer l'avertissement.
verifier("un échec PARTIEL est signalé sans invalider tout le rapport",
         "sondages SANS RÉPONSE" in dbl and "écarté à tort" in dbl)

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
