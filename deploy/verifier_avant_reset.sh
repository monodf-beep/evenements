#!/usr/bin/env bash
# REFUSE de déployer tant que le VPS porte des commits que GitHub n'a pas.
#
# Usage :  bash deploy/verifier_avant_reset.sh <branche>
# Sortie :  0 = on peut réinitialiser sans rien perdre · 1 = il y a du travail local
#
# D'OÙ ÇA VIENT — 2026-09-22 au matin. `deploy/update.sh` fait `git reset --hard` à
# chaque passage. Ce jour-là le VPS portait VINGT-SIX commits jamais poussés (quatre
# fusions de branches faites sur place), et le déploiement les a effacés. La ligne qui
# le disait était pourtant à l'écran :
#
#     Your branch and 'origin/…' have diverged, and have 26 and 3 different commits each
#
# Elle passe dans le flot, elle ne bloque rien, et personne ne la lit. C'est la récidive
# du 08/09 au soir, où deux commits fusionnés avaient été effacés dans la même commande
# — l'incident était déjà écrit dans le CLAUDE.md, ce qui prouve qu'écrire la règle ne
# suffit pas. Il fallait que l'avertissement ait une CONSÉQUENCE.
#
# Ce script est cette conséquence. Il ne répare rien, il n'efface rien, il ne pousse
# rien : il s'arrête et dit quoi taper. Le travail local reste intact tant qu'on n'a
# pas tranché.
#
# CE QU'IL NE VOIT PAS, et qu'il faut savoir :
# les modifications non commitées et NON INDEXÉES.
# Un fichier édité à la main sur le VPS et laissé tel quel sera toujours écrasé
# par le reset — sauf .claude/settings.json, que update.sh met de côté à part. Un
# garde-fou qui laisserait croire qu'il protège tout serait pire que pas de garde-fou.
#
# ⚠️ TROISIÈME OCCURRENCE, 2026-09-29 — et celle-là est passée SOUS ce garde-fou.
#
# Le 28/09 à midi, le VPS portait une FUSION EN COURS : neuf fichiers indexés (trois
# mu-plugins neufs, un gabarit de fiche, trois retouches, deux documents), « All conflicts
# fixed but you are still merging ». Le lendemain matin, plus rien : index vide, arbre
# propre, et les neuf fichiers toujours absents de la branche. Un `reset --hard` était
# passé entre-temps — le déploiement de 7h50, ou une commande à la main.
#
# Ce script n'a rien vu, et pour une raison exacte : **une fusion en cours n'est pas un
# commit**. `git rev-list origin/<branche>..HEAD` rendait ZÉRO, donc « rien à perdre ».
# Le travail ne vivait que dans l'INDEX, que la ligne 36 ne regardait pas.
#
# Il compte donc désormais trois choses et plus une seule : les commits d'avance, une
# fusion (ou un picorage) en cours, et un index non vide. La frontière reste la même —
# ce qui a été DÉLIBÉRÉMENT préparé est protégé, ce qui traîne dans l'arbre de travail ne
# l'est pas — parce qu'un garde-fou qui refuse à tort finit contourné pour de bon.
set -uo pipefail

BRANCHE="${1:?usage: verifier_avant_reset.sh <branche>}"

# Commits présents ici et absents de GitHub. Si la référence distante n'existe pas
# encore (premier déploiement), il n'y a rien à perdre : on laisse passer.
if ! git rev-parse --verify --quiet "origin/$BRANCHE" >/dev/null; then
  exit 0
fi
AVANCE="$(git rev-list --count "origin/$BRANCHE..HEAD" 2>/dev/null || echo 0)"

# Une opération en cours (fusion, picorage, revert) : le travail est là, mais il n'a pas
# encore de commit. C'est l'état du 28/09 au soir.
EN_COURS=""
for tete in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD; do
  if git rev-parse --verify --quiet "$tete" >/dev/null 2>&1; then
    EN_COURS="$tete"
    break
  fi
done
# Un index non vide : des fichiers `git add`és et pas encore commités. Le reset les perd
# aussi. On ne regarde PAS l'arbre de travail (cf. l'en-tête : ce qui n'a pas été préparé
# n'est pas protégé, sinon le garde-fou refuserait à chaque édition de passage).
INDEXE=0
if ! git diff --cached --quiet 2>/dev/null; then
  INDEXE="$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')"
fi

if [ "$AVANCE" -eq 0 ] && [ -z "$EN_COURS" ] && [ "$INDEXE" -eq 0 ]; then
  exit 0
fi

if [ "${DEPLOY_ABANDONNER_LOCAL:-}" = "1" ]; then
  echo "⚠️  Travail local : $AVANCE commit(s), $INDEXE fichier(s) indexé(s)${EN_COURS:+," \
       "$EN_COURS en cours}" "vont être ABANDONNÉS (DEPLOY_ABANDONNER_LOCAL=1)."
  exit 0
fi

# Le cas SANS commit d'avance : une fusion en cours ou un index rempli. Message à part,
# parce que le geste n'est pas le même — il faut d'abord CONCLURE, puis pousser.
if [ "$AVANCE" -eq 0 ]; then
  echo
  echo "⛔ DÉPLOIEMENT ARRÊTÉ — il y a du travail préparé ici, sans commit."
  echo
  if [ -n "$EN_COURS" ]; then
    echo "   Une opération est EN COURS ($EN_COURS) : la fusion n'est pas conclue."
  fi
  if [ "$INDEXE" -gt 0 ]; then
    echo "   $INDEXE fichier(s) sont indexés et pas encore commités :"
    echo
    git --no-pager diff --cached --name-status | sed 's/^/     /'
    echo
  fi
  echo "   Le déploiement commence par « git reset --hard » : tout ceci SERAIT PERDU,"
  echo "   sans un mot. C'est arrivé le 28/09 — neuf fichiers d'une fusion en cours."
  echo
  echo "   ─────────────────────────────────────────────────────────────────"
  echo "   CE QU'IL FAUT FAIRE — conclure, envoyer, puis déployer :"
  echo
  echo "       git commit --no-edit && git push origin $BRANCHE && bash deploy/update.sh"
  echo
  echo "   ─────────────────────────────────────────────────────────────────"
  echo
  echo "   Si — et seulement si — ce travail ne vaut rien et doit être jeté :"
  echo
  echo "       DEPLOY_ABANDONNER_LOCAL=1 bash deploy/update.sh"
  echo
  echo "   Rien n'a été modifié. Le travail local est intact."
  echo
  exit 1
fi

echo
echo "⛔ DÉPLOIEMENT ARRÊTÉ — il y a du travail ici que GitHub n'a pas."
echo
echo "   $AVANCE commit(s) existent sur ce serveur et nulle part ailleurs."
echo "   Le déploiement commence par « git reset --hard » : il les EFFACERAIT."
echo "   (C'est ce qui est arrivé le 22/09 au matin, avec 26 commits.)"
echo
echo "   Les voici, du plus récent au plus ancien :"
echo
git --no-pager log --oneline --decorate "origin/$BRANCHE..HEAD" | sed 's/^/     /'
echo
echo "   ─────────────────────────────────────────────────────────────────"
echo "   CE QU'IL FAUT FAIRE — une seule commande, à taper ici :"
echo
echo "       git push origin $BRANCHE && bash deploy/update.sh"
echo
echo "   Elle envoie ce travail sur GitHub, puis déploie normalement."
echo "   ─────────────────────────────────────────────────────────────────"
echo
echo "   Si — et seulement si — ces commits ne valent rien et doivent être jetés :"
echo
echo "       DEPLOY_ABANDONNER_LOCAL=1 bash deploy/update.sh"
echo
echo "   Rien n'a été modifié. Le travail local est intact."
echo
exit 1
