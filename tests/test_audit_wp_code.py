#!/usr/bin/env python3
"""Fixture : l'inventaire du code WordPress (scripts/audit_wp_code.sh) reste MANUEL.

D'OÙ ÇA VIENT — 2026-08-28, en préparant cet outil. Contrairement à cerveau.sh et
bilan_matin.sh, dont Write/Edit sont interdits AU NIVEAU DE L'OUTIL (--disallowedTools,
un verrou que la consigne ne peut pas contourner), Novamira n'offre pas d'ability
« lecture seule » : `novamira/execute-php` EST la capacité d'écrire. La frontière ne
peut donc reposer QUE sur le texte de la consigne — un niveau de confiance plus faible,
qu'on ne doit JAMAIS laisser tourner sans supervision. Cette fixture garde les deux
garanties qui restent possibles : la consigne interdit explicitement l'écriture, et le
script n'est PAS planifié en crontab (donc jamais lancé sans qu'un humain tape la
commande et lise la sortie).

Aucun réseau, aucune base : lecture de fichiers du dépôt.

Lancer : .venv/bin/python -m tests.test_audit_wp_code
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


consigne = (ROOT / "config" / "consigne_audit_wp_code.txt").read_text(encoding="utf-8")
harnais = (ROOT / "scripts" / "audit_wp_code.sh").read_text(encoding="utf-8")
crontab = (ROOT / "crontab.txt").read_text(encoding="utf-8")

print("──── la consigne interdit explicitement l'écriture ────")
verifier("novamira/write-file est nommément interdit",
         "novamira/write-file" in consigne)
verifier("une requête PHP qui MODIFIE est nommément interdite",
         "MODIFIE quoi que ce soit" in consigne
         or ("UPDATE" in consigne and "INSERT" in consigne and "DELETE" in consigne))
verifier("la consigne dit ce qu'il faut faire si une lecture semble exiger une écriture "
         "(s'arrêter, pas contourner)",
         "ARRÊTE-TOI" in consigne and "ne contourne pas" in consigne)
verifier("aucune recommandation d'action n'est demandée — seulement un inventaire",
         "N'ÉCRIS AUCUNE RECOMMANDATION" in consigne)

print("\n──── le script N'EST PAS un cron — supervision humaine obligatoire ────")
verifier("le harnais s'annonce lui-même comme LANCEMENT MANUEL",
         "LANCEMENT MANUEL UNIQUEMENT, jamais en crontab" in harnais)
verifier("le harnais explique POURQUOI (Novamira n'a pas d'ability lecture seule)",
         "n'offre pas cette granularité" in harnais or "pas d'ability" in harnais)
verifier("⚠️ ET LE FAIT : crontab.txt ne planifie PAS ce script — la contre-épreuve, "
         "sans elle cette fixture ne prouverait qu'une intention écrite",
         "audit_wp_code.sh" not in crontab, "trouvé dans crontab.txt — RETIRER")
verifier("le harnais affiche l'avertissement à l'écran avant de lancer l'agent",
         "avant d'en tirer une conclusion" in harnais)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
