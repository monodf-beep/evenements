#!/usr/bin/env python3
"""Fixture : tout fichier PHP de deploy/wordpress/ doit passer `php -l`.

INCIDENT RÉEL, 2026-08-08 → 2026-08-10 : le site est resté INJOIGNABLE pendant deux
jours — front, wp-admin et API REST en HTTP 500 simultanément — à cause d'une seule
ligne :

    Parse error: syntax error, unexpected token "===" in
    /home/ohcqqjv/agendasabauda/wp-content/mu-plugins/cs-source-garde.php on line 20

Un mu-plugin se charge AVANT tout le reste de WordPress : une erreur de syntaxe y tue
le site entier, y compris la porte d'entrée qui permettrait de la réparer. Il n'y avait
aucun moyen de revenir en arrière depuis WordPress — il a fallu du FTP.

Et `cs-source-garde.php` n'existait PAS dans ce dépôt : il a été écrit directement sur
le serveur, sans relecture, sans contrôle de syntaxe, sans copie versionnée. C'est la
vraie leçon : le PHP déposé sur WordPress doit passer par `deploy/wordpress/`, donc par
git, donc par ce test.

Deux volets :
  1. tous les fichiers livrés doivent être syntaxiquement valides ;
  2. CONTRE-ÉPREUVE : un fichier délibérément cassé (la faute EXACTE de l'incident)
     doit être refusé. Sans ce volet, un `php -l` qui ne ferait rien passerait au vert.

`php` absent (c'est le cas sur le VPS, qui n'héberge pas WordPress) : le test le DIT et
sort en 0 — un contrôle qu'on ne peut pas faire ne doit pas bloquer, mais il ne doit pas
non plus se déguiser en succès.

Lancer : .venv/bin/python -m tests.test_php_syntax
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WP_DIR = ROOT / "deploy" / "wordpress"

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


def _lint(chemin: Path) -> tuple[bool, str]:
    """(syntaxe valide ?, sortie brute). `-d display_errors=1` : sans lui, une config
    php.ini en mode production renvoie un code retour non nul SANS message, et on ne
    saurait pas quoi montrer."""
    r = subprocess.run([PHP, "-d", "display_errors=1", "-l", str(chemin)],
                       capture_output=True, text=True)
    sortie = (r.stdout + r.stderr).strip()
    return r.returncode == 0, sortie


PHP = shutil.which("php")
if not PHP:
    print("IGNORÉ — aucun binaire `php` sur cette machine : la syntaxe des mu-plugins")
    print("         n'a PAS été vérifiée. Sur le VPS c'est normal (il n'héberge pas")
    print("         WordPress) ; sur un poste de développement, installer php-cli.")
    sys.exit(0)

print(f"──── php -l sur {WP_DIR.relative_to(ROOT)} ({PHP}) ────")
# LES CORRECTIFS UNIQUES COMPTENT AUTANT QUE LES MU-PLUGINS. Ajouté le 2026-08-12, quand
# on a découvert que `cs-publish.php` n'est pas un fichier du serveur mais un snippet en
# base : on le corrige donc par un script PHP à exécuter, dans deploy/wordpress-patchs/.
# Ce script tourne sur la production avec les mêmes conséquences qu'un mu-plugin — une
# faute de syntaxe y coûte le même site injoignable. Le laisser hors du contrôle aurait
# rouvert la porte que ce fichier existe pour fermer.
fichiers = sorted(WP_DIR.glob("*.php")) + sorted((ROOT / "deploy" / "wordpress-patchs")
                                                 .glob("*.php"))
_check("au moins un mu-plugin à vérifier", bool(fichiers), f"{WP_DIR} vide")
for f in fichiers:
    ok, sortie = _lint(f)
    _check(f"{f.name}", ok, sortie)

# LES COPIES DES SNIPPETS AUSSI (2026-08-17). Trois audits quotidiens vivent dans la base
# WordPress (table wp_snippets) et n'avaient AUCUNE copie ici — le défaut du 12/08, pour
# lequel il a fallu trois heures et quatre transports. Leur code est désormais versionné
# dans deploy/wordpress/code-snippets/, au format de Code Snippets, donc SANS `<?php` :
# on le préfixe pour le contrôler. Une copie de secours syntaxiquement fausse ne se
# découvrirait qu'au moment de restaurer, c'est-à-dire au pire moment.
snippets = sorted((WP_DIR / "code-snippets").glob("*.php"))
if snippets:
    print(f"\n──── php -l sur {(WP_DIR / 'code-snippets').relative_to(ROOT)} "
          f"(préfixés `<?php`) ────")
    for f in snippets:
        tmp = Path(tempfile.mkdtemp()) / f.name
        tmp.write_text("<?php\n" + f.read_text(encoding="utf-8"), encoding="utf-8")
        ok, sortie = _lint(tmp)
        _check(f"{f.name}", ok, sortie)

# ── Contre-épreuve : la faute EXACTE de l'incident doit être attrapée ────────────
print("\n──── contre-épreuve : la faute du 2026-08-08 est bien refusée ────")
casse = Path(tempfile.mkdtemp()) / "cs-source-garde-cassé.php"
casse.write_text(
    "<?php\n"
    "if (!defined('ABSPATH')) { exit; }\n"
    "add_filter('the_content', function ($c) {\n"
    "    if ($c === === '') { return $c; }\n"   # <- « unexpected token \"===\" »
    "    return $c;\n"
    "});\n", encoding="utf-8")
ok, sortie = _lint(casse)
_check("un fichier avec `=== ===` est REFUSÉ", not ok, "php -l l'a accepté !")
_check("le message nomme le jeton fautif", "===" in sortie, sortie)

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
