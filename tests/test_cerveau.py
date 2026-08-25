#!/usr/bin/env python3
"""Fixture : le cerveau (l'agent ACTEUR de 10h40) reste borné au réversible.

Aucun réseau, aucune base, aucun LLM : on lit les fichiers du dépôt — le harnais
(scripts/cerveau.sh), la consigne (config/consigne_cerveau.txt) et le crontab.

D'OÙ ÇA VIENT (2026-08-25). Franck : « les décisions tu dois les prendre en autonomie,
et les informations via les différents scripts ». Un agent Claude non-interactif tourne
donc chaque matin AVEC des outils d'action — c'est la première fois qu'un cron de ce
dépôt a le droit d'écrire en base de sa propre initiative. Ce qui rend ça acceptable
tient à trois verrous, et cette fixture existe pour qu'aucun des trois ne se desserre
en silence :

  1. sa liste d'outils ne contient QUE des gestes que CLAUDE.md classe réversibles —
     un ajout irréfléchi (`git push`, un `--force`, un `rm`) doit passer au ROUGE ici
     avant de passer en production ;
  2. il ne modifie aucun fichier (Write/Edit interdits) : il tape des commandes, il
     n'écrit pas de code. Un correctif de code se relit dans une session, pas un cron ;
  3. l'acteur tourne AVANT le bilan de 11h, pour que le contrôleur (lecture seule)
     relise ses gestes le jour même — pas le lendemain.

Et comme pour test_php_syntax.py : une faute de syntaxe shell dans le harnais ferait
échouer le cron EN SILENCE chaque matin — `bash -n` le vérifie ici, avec contre-épreuve.

Lancer : .venv/bin/python -m tests.test_cerveau
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HARNAIS = ROOT / "scripts" / "cerveau.sh"
CONSIGNE = ROOT / "config" / "consigne_cerveau.txt"
CRONTAB = ROOT / "crontab.txt"

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ─── Les motifs qu'une liste d'outils d'un agent autonome ne doit JAMAIS porter ───
# CLAUDE.md, section « Interdit, et ça ne se négocie pas » — plus git add/commit/push
# et crontab, qui ne sont pas irréversibles mais sont le canal par lequel un cron
# modifierait le dépôt ou ses propres droits, ce que le point 2 ci-dessus interdit.
MOTIFS_INTERDITS = (
    "rm ", "rm:", "--hard", "force", "DELETE", "DROP", "TRUNCATE",
    "git push", "git add", "git commit", "crontab", "systemctl",
    "pip install", "apt", "wp/v2",
)


def outils_du_harnais(source: str) -> list[str]:
    """Les entrées du tableau OUTILS=( … ), commentaires retirés.

    On retire les lignes de commentaire AVANT d'extraire : le tableau en contient
    (elles expliquent la frontière réversible/irréversible), et un motif interdit
    seulement CITÉ en commentaire ne doit pas faire crier la fixture — le défaut
    symétrique de celui que test_contrat_meta_as documente.
    """
    m = re.search(r"OUTILS=\((.*?)\n\)", source, re.DOTALL)
    if not m:
        return []
    lignes = [l for l in m.group(1).splitlines() if not l.strip().startswith("#")]
    bloc = "\n".join(lignes)
    return re.findall(r'"([^"]+)"', bloc) + re.findall(r"^\s*(\w+)\s*$", bloc, re.M)


def motifs_trouves(outils: list[str]) -> list[str]:
    """Les entrées de la liste qui portent un motif interdit."""
    return [o for o in outils for motif in MOTIFS_INTERDITS if motif in o]


source = HARNAIS.read_text(encoding="utf-8")
outils = outils_du_harnais(source)

print("──── la liste d'outils est bien lue (zéro sans dénominateur) ────")
_check(f"le harnais liste des outils ({len(outils)} trouvés)", len(outils) >= 15,
       str(outils))

print("\n──── aucun outil irréversible dans la liste ────")
trouves = motifs_trouves(outils)
_check("aucun motif interdit dans les outils autorisés", not trouves,
       f"→ {trouves} — un agent autonome ne doit JAMAIS porter ces gestes")

print("\n──── contre-épreuve : le contrôle sait-il REFUSER ? ────")
FAUX = ['Bash(git push --force:*)', 'Bash(.venv/bin/python -m scripts.trash_by_ids:*)']
vus = motifs_trouves(FAUX)
_check("une liste portant `git push --force` est bien vue comme fautive",
       'Bash(git push --force:*)' in vus, str(vus))
_check("   et le geste réversible (trash_by_ids, route cs/v1) passe, lui",
       'Bash(.venv/bin/python -m scripts.trash_by_ids:*)' not in vus, str(vus))

print("\n──── le cerveau n'écrit pas de fichiers ────")
m = re.search(r"INTERDITS=\(([^)]*)\)", source)
interdits = m.group(1).split() if m else []
_check("Write et Edit sont explicitement interdits",
       "Write" in interdits and "Edit" in interdits, str(interdits))

print("\n──── la consigne porte ses phrases de charge ────")
consigne = CONSIGNE.read_text(encoding="utf-8").lower()
for phrase, pourquoi in (
    ("dry-run", "règle 4 — lire avant d'appliquer"),
    ("backup_db", "le filet avant les écritures"),
    ("10 fiches", "le plafond par passage"),
    ("escalad", "l'issue pour tout ce qui dépasse le mandat"),
    ("réversible", "la frontière elle-même"),
):
    _check(f"la consigne mentionne « {phrase} » ({pourquoi})", phrase in consigne)

print("\n──── l'acteur tourne avant son contrôleur ────")
cron = CRONTAB.read_text(encoding="utf-8")


def _heure(motif: str):
    m = re.search(rf"^(\d+)\s+(\d+)\s+\*\s+\*\s+\*\s+.*{motif}", cron, re.M)
    return int(m.group(2)) * 60 + int(m.group(1)) if m else None


t_cerveau, t_bilan = _heure(r"cerveau\.sh"), _heure(r"bilan_matin\.sh")
_check("le crontab lance le cerveau (ligne trouvée)", t_cerveau is not None)
_check("le crontab lance le bilan (ligne trouvée)", t_bilan is not None)
_check("le cerveau passe AVANT le bilan — sinon le contrôle a un jour de retard",
       t_cerveau is not None and t_bilan is not None and t_cerveau < t_bilan,
       f"cerveau={t_cerveau} bilan={t_bilan} (minutes depuis minuit)")

print("\n──── le harnais est du shell valide, et exécutable au checkout ────")
r = subprocess.run(["bash", "-n", str(HARNAIS)], capture_output=True, text=True)
_check("bash -n accepte scripts/cerveau.sh", r.returncode == 0, r.stderr[-300:])

# Contre-épreuve, comme test_php_syntax : un shell cassé DOIT être refusé, sinon ce
# contrôle ne prouve que sa capacité à dire oui.
with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
    f.write("if [ ; then\n")
    casse = f.name
r2 = subprocess.run(["bash", "-n", casse], capture_output=True, text=True)
Path(casse).unlink(missing_ok=True)
_check("   et un shell cassé est bien refusé (contre-épreuve)", r2.returncode != 0)

# Le bit exécutable vit dans l'INDEX git : c'est lui que le checkout du VPS applique,
# pas le fichier local de la session qui l'a écrit. Cron lance `scripts/cerveau.sh`
# directement — sans ce bit, panne quotidienne et silencieuse.
r3 = subprocess.run(["git", "ls-files", "-s", "scripts/cerveau.sh"],
                    capture_output=True, text=True, cwd=str(ROOT))
_check("git porte le bit exécutable (mode 100755)", r3.stdout.startswith("100755"),
       r3.stdout.strip() or "(fichier absent de l'index)")

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
