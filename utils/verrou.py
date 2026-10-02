"""Verrou d'exécution EXCLUSIF entre processus — un seul exemplaire d'un script à la fois.

D'OÙ ÇA VIENT (2026-09-22 au soir). Deux `translate_events.py --apply` ont tourné EN
MÊME TEMPS sur le VPS (PID 54609 et 57330). Chacun a calculé sa file au démarrage —
« originaux publiés sans traduction » —, les deux files se recouvraient, et chaque fiche
commune a été traduite DEUX fois : 11 fiches italiennes en double publiées sur WordPress
(WP#11010 créée à 22:23:55, WP#11011 à 22:23:56, même lieu, même date, une seule liée au
français par Polylang), corbeillées à la main. Les deux exécutions écrivaient en plus dans
le même journal, devenu illisible. Et le cron lance le même script à 10:45 : une
exécution manuelle pendant le cron recrée exactement le même accident.

POURQUOI `flock` ET PAS UN FICHIER PID. Un fichier PID dit « quelqu'un a commencé » ; il
ne dit pas « quelqu'un tourne encore ». Un processus tué (SIGKILL, OOM, reboot) laisse le
fichier derrière lui, et le script suivant refuse de partir pour un détenteur mort —
c'est un état terminal sans rouvreur (règle 3), réglé un jour par un humain qui efface un
fichier. `flock` est tenu par le NOYAU sur la description de fichier ouverte : quand le
processus meurt, de quelque façon que ce soit, le noyau ferme ses descripteurs et le
verrou tombe avec eux. Personne n'a rien à nettoyer.

Le PID écrit dans le fichier n'est donc qu'une INFORMATION pour le message de refus
(« qui tient le verrou ? »), jamais la preuve du verrou : c'est `flock` seul qui décide.
Un PID périmé dans un fichier non verrouillé est normal et sans effet.

Trois précautions, chacune fermant un piège précis :

  · on ouvre SANS tronquer (`O_RDWR | O_CREAT`, pas `open(..., "w")`) : tronquer AVANT
    d'avoir le verrou effacerait le PID du détenteur légitime au moment même où l'on
    va lui être refusé — le message de refus ne saurait plus qui tient la place ;
  · on ne SUPPRIME jamais le fichier en relâchant : supprimer un fichier verrouillé
    laisse un troisième processus créer un nouveau fichier au même chemin et le
    verrouiller pendant que le second tient encore l'ancien — deux « exclusifs » à la fois ;
  · le descripteur est NON HÉRITABLE (défaut de `os.open` depuis Python 3.4, PEP 446) :
    un sous-processus lancé par le script ne garde donc pas le verrou après la mort de
    son parent. (Un `fork` SANS `exec` le garderait ; le dépôt n'en fait pas ici.)

Stdlib seule, aucun import du projet : la fixture `tests/test_translate_lock.py` doit
pouvoir le tester sans `.env`, sans réseau, sans base.
"""
from __future__ import annotations

import fcntl
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Code de sortie d'une exécution REFUSÉE parce qu'une autre tient déjà le verrou.
# 75 = EX_TEMPFAIL de <sysexits.h> : « échec temporaire, réessayer plus tard ». Non nul
# pour que ni un humain ni un cron ne prennent ce refus pour une traduction réussie ;
# distinct de 1 (plantage) et de 2 (argument invalide) pour qu'on sache lequel c'est.
CODE_DEJA_EN_COURS = 75


@dataclass
class Verrou:
    """Résultat d'une tentative. `obtenu` dit tout ; `detenteur` n'est rempli qu'au refus."""
    chemin: Path
    fd: int | None = None
    detenteur: str = ""

    @property
    def obtenu(self) -> bool:
        return self.fd is not None

    def relacher(self) -> None:
        """Relâche explicitement. Facultatif : la mort du processus le fait aussi."""
        if self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
                self.fd = None


def prendre(chemin: Path | str) -> Verrou:
    """Tente de prendre le verrou EXCLUSIF, sans attendre.

    Obtenu : le fichier contient désormais le PID de CE processus, et le verrou reste
    tenu tant que l'objet rendu garde son descripteur ouvert — donc jusqu'à la fin du
    processus si l'appelant le conserve. Refusé : `obtenu` est faux et `detenteur` porte
    ce que le détenteur a écrit (PID, heure, commande), ou "" s'il n'a rien pu écrire.
    """
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(chemin, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        try:
            detenteur = os.read(fd, 512).decode("utf-8", "replace").strip()
        except OSError:
            detenteur = ""
        os.close(fd)
        return Verrou(chemin=chemin, fd=None, detenteur=detenteur)
    except BaseException:
        os.close(fd)
        raise
    # Verrou obtenu : SEULEMENT maintenant on remplace le contenu par notre identité.
    os.ftruncate(fd, 0)
    ident = (f"pid={os.getpid()} depuis={datetime.now().isoformat(timespec='seconds')} "
             f"cmd={' '.join(sys.argv)[:300]}\n")
    os.pwrite(fd, ident.encode("utf-8"), 0)
    return Verrou(chemin=chemin, fd=fd)


def exclusif_si(apply: bool, chemin: Path | str) -> Verrou | None:
    """Le verrou n'est pris QU'EN ÉCRITURE (`--apply`).

    Une simulation ne publie rien et ne marque rien : deux simulations, ou une simulation
    pendant le cron, ne peuvent pas fabriquer de doublon. Les bloquer n'empêcherait aucun
    accident et interdirait de regarder ce que le cron s'apprête à faire pendant qu'il
    tourne. Rend None en simulation — rien n'est ouvert, rien n'est tenu.
    """
    if not apply:
        return None
    return prendre(chemin)
