#!/usr/bin/env python3
"""Dépose des fichiers sur l'hébergement OVH par FTPS — le repli quand SFTP est refusé.

POURQUOI CE FICHIER EXISTE. Le 2026-08-12, `deploy/push-wordpress.sh` a échoué deux fois
de suite sur la même ligne :

    ohcqqjv@ftp.cluster100.hosting.ovh.net's password:
    Connection closed by 54.36.142.132 port 22

Ce n'est pas le mot de passe : c'est le port 22. Sur un hébergement mutualisé OVH, SFTP
n'est ouvert que si SSH a été activé dans le manager.

⚠️ ET LE REPLI N'EST PAS AUSSI SÛR QUE JE L'AI ÉCRIT ICI D'ABORD. La première version de
ce texte affirmait que FTPS « l'est toujours pour le compte FTP principal ». Le serveur a
répondu, dix minutes plus tard : « 500 This security scheme is not implemented ». Une
phrase écrite avec assurance sur un serveur qu'on n'avait pas interrogé — exactement ce
que la règle 1 interdit de faire sur les fiches, et que j'ai fait sur un protocole.
D'où la négociation en deux temps (« AUTH TLS » puis « AUTH SSL ») et, en dernier recours
seulement, `--clair`.

CE QUI DISTINGUE CE SCRIPT DE `sftp`, ET C'EST L'ESSENTIEL. `sftp`, lancé sur une liste de
commandes, n'interrompt PAS sa session quand un `put` isolé est refusé : il rend 0, et le
script appelant annonçait « ✅ Déployé » sans que rien ne soit parti. Ici, chaque envoi est
RELU sur le serveur et sa taille comparée à celle du fichier local. Sans ça on rapporte une
intention, pas un résultat (règle 6).

TLS PAR DÉFAUT, ET PAS DE REPLI SILENCIEUX. Le mot de passe FTP donne accès à tout le site :
il ne traverse pas Internet en clair sans que quelqu'un l'ait décidé. `--clair` existe pour
les serveurs qui ne proposent pas AUTH TLS, et il le dit à l'écran.

  .venv/bin/python deploy/push_ftp.py cs-publish.php
  .venv/bin/python deploy/push_ftp.py --liste          # ce qui est en ligne, sans rien écrire
"""
from __future__ import annotations

import argparse
import ftplib
import os
import ssl
import sys
from getpass import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WP_DIR = ROOT / "deploy" / "wordpress"


def _env(cle: str) -> str:
    """Lit UNE clé du .env sans le sourcer — mêmes précautions que push-wordpress.sh."""
    if os.getenv(cle):
        return os.environ[cle]
    f = ROOT / ".env"
    if not f.exists():
        return ""
    for ligne in f.read_text(encoding="utf-8", errors="replace").splitlines():
        ligne = ligne.strip()
        if ligne.startswith(f"{cle}="):
            v = ligne.split("=", 1)[1].strip()
            return v[1:-1] if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'" else v
    return ""


def _cible() -> tuple[str, str, str]:
    """(hôte, utilisateur, dossier distant), déduits de ce qui est DÉJÀ configuré.

    On réutilise `WP_DEPLOY_SSH` (« user@hôte ») plutôt que d'inventer deux variables de
    plus : c'est le même compte, le même serveur, seul le protocole change. Une deuxième
    façon d'écrire la même chose finit toujours par diverger de la première."""
    ssh = _env("WP_DEPLOY_FTP") or _env("WP_DEPLOY_SSH")
    mu = _env("WP_DEPLOY_MU_DIR")
    if "@" not in ssh:
        raise SystemExit("Manque WP_DEPLOY_SSH=user@hôte dans .env (ou WP_DEPLOY_FTP).")
    user, hote = ssh.split("@", 1)
    if not mu:
        raise SystemExit("Manque WP_DEPLOY_MU_DIR=chemin/vers/mu-plugins dans .env.")
    return hote, user, mu.strip("/")


def _auth_ssl(f: ftplib.FTP_TLS) -> None:
    """Négocie TLS par « AUTH SSL » — la commande d'avant « AUTH TLS ».

    ftplib n'essaie que « AUTH TLS », et le serveur d'OVH a répondu, le 2026-08-12 :
    « 500 This security scheme is not implemented ». Beaucoup de serveurs FTP anciens
    n'acceptent que l'orthographe SSL, pour la MÊME négociation TLS derrière. Reproduit ici
    ce que fait `FTP_TLS.auth()` de CPython, au verbe près."""
    f.voidcmd("AUTH SSL")
    f.sock = f.context.wrap_socket(f.sock, server_hostname=f.host)
    f.file = f.sock.makefile(mode="r", encoding=f.encoding)


def connecte(hote: str, user: str, mdp: str, clair: bool) -> ftplib.FTP:
    if clair:
        print("⚠️  FTP EN CLAIR : le mot de passe traverse le réseau en clair. "
              "Choix explicite (--clair).")
        f: ftplib.FTP = ftplib.FTP(hote, timeout=60)
        f.login(user, mdp)
        return f
    t = ftplib.FTP_TLS(timeout=60, context=ssl.create_default_context())
    t.connect(hote, 21)
    try:
        t.auth()                    # « AUTH TLS »
    except ftplib.error_perm as exc:
        print(f"   AUTH TLS refusé ({str(exc).strip()[:60]}) — seconde tentative en "
              f"AUTH SSL.")
        _auth_ssl(t)
    t.login(user, mdp)
    t.prot_p()                      # chiffre AUSSI le canal de données, pas que le contrôle
    return t


def taille_distante(f: ftplib.FTP, chemin: str) -> int | None:
    """Taille du fichier sur le serveur, ou None s'il n'y est pas.

    C'est LA vérification : sans elle, on annonce un dépôt qu'on n'a pas constaté. SIZE en
    binaire, parce qu'en ASCII le serveur peut compter des fins de ligne qu'il réécrit."""
    try:
        f.voidcmd("TYPE I")
        return f.size(chemin)
    except (ftplib.error_perm, ftplib.error_temp):
        return None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fichiers", nargs="*", help="noms dans deploy/wordpress/, ou chemins")
    ap.add_argument("--liste", action="store_true",
                    help="montre les mu-plugins EN LIGNE et leur taille, sans rien écrire")
    ap.add_argument("--clair", action="store_true",
                    help="FTP sans TLS — seulement si le serveur refuse AUTH TLS")
    args = ap.parse_args(argv)

    hote, user, mu = _cible()
    locaux: list[Path] = []
    for nom in args.fichiers:
        p = Path(nom)
        if not p.is_file():
            p = WP_DIR / nom
        if not p.is_file():
            print(f"❌ Introuvable : {nom}")
            return 2
        locaux.append(p)

    if not locaux and not args.liste:
        print("Rien à envoyer. Nomme les fichiers, ou utilise --liste pour regarder.")
        print("Disponibles :", ", ".join(sorted(f.name for f in WP_DIR.glob("*.php"))))
        return 2

    # SYNTAXE D'ABORD, ET SANS BLUFF. Le site est resté injoignable deux jours pour un
    # « === » dans un mu-plugin (2026-08-08). Si `php` manque, on le DIT au lieu de
    # laisser croire que le contrôle a eu lieu — mais on n'envoie pas pour autant à
    # l'aveugle : la fixture tests/test_php_syntax tourne sur toute machine qui a PHP.
    import shutil
    import subprocess
    php = shutil.which("php")
    if locaux and php:
        for p in locaux:
            r = subprocess.run([php, "-l", str(p)], capture_output=True, text=True)
            if r.returncode != 0:
                print(f"❌ Syntaxe PHP invalide, RIEN n'a été envoyé :\n   "
                      f"{(r.stdout + r.stderr).strip()}")
                return 3
        print(f"→ Syntaxe : {len(locaux)} fichier(s) validé(s) par php -l")
    elif locaux:
        print("⚠️  Aucun binaire `php` ici : la syntaxe n'a PAS été vérifiée.")
        print("    Un mu-plugin fautif rend le site ET son wp-admin inaccessibles.")

    mdp = _env("WP_DEPLOY_FTP_PASSWORD") or getpass(f"Mot de passe FTP de {user} : ")
    try:
        f = connecte(hote, user, mdp, args.clair)
    except ftplib.all_errors as exc:
        print(f"❌ Connexion FTP{'S' if not args.clair else ''} refusée : {exc}")
        if not args.clair:
            print("   Si le serveur ne propose pas AUTH TLS, réessayer avec --clair.")
        return 4
    print(f"→ Connecté en FTP{'' if args.clair else 'S'} à {hote} ({user})")

    try:
        if args.liste:
            print(f"→ {mu} :")
            noms = []
            try:
                noms = sorted(n for n in f.nlst(mu) if n.endswith(".php"))
            except ftplib.all_errors as exc:
                print(f"   (listage impossible : {exc})")
            for n in noms:
                t = taille_distante(f, n)
                base = n.rsplit("/", 1)[-1]
                ici = WP_DIR / base
                marque = ("=" if ici.exists() and t == ici.stat().st_size
                          else "≠" if ici.exists() else "·")
                print(f"   {marque} {base:<34} {t if t is not None else '?':>8} o"
                      + ("   (pas de double dans le dépôt)" if not ici.exists() else ""))
            # LE CHIFFRE ET SON PÉRIMÈTRE (règle 6). « 34 mu-plugins cs-* en ligne dont 18
            # seulement ont leur double ici » était une phrase de CLAUDE.md sans compteur ;
            # elle en a un maintenant.
            sans_double = sum(1 for n in noms if not (WP_DIR / n.rsplit("/", 1)[-1]).exists())
            print(f"\n   {len(noms)} fichier(s) en ligne, dont {sans_double} sans version "
                  f"dans deploy/wordpress/ — ceux-là n'ont jamais été relus.")
            return 0

        echecs = 0
        for p in locaux:
            distant = f"{mu}/{p.name}"
            avant = taille_distante(f, distant)
            with p.open("rb") as fh:
                f.storbinary(f"STOR {distant}", fh)
            apres = taille_distante(f, distant)
            attendu = p.stat().st_size
            # RELU SUR LE SERVEUR, pas déduit de l'absence d'exception.
            if apres == attendu:
                mouvement = (f"{avant} → {apres} o" if avant is not None
                             else f"créé, {apres} o")
                print(f"   ✅ {p.name} — {mouvement}")
            else:
                echecs += 1
                print(f"   ❌ {p.name} — le serveur en annonce {apres}, on en a envoyé "
                      f"{attendu}. NE PAS considérer ce fichier comme déployé.")
        if echecs:
            return 5
    finally:
        try:
            f.quit()
        except ftplib.all_errors:
            f.close()

    print("\nVérifie ce que WordPress EXÉCUTE (un fichier posé ne prouve rien — règle 1) :")
    print("  curl -s https://agendasabauda.eu/wp-json/cs/v1/version")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
