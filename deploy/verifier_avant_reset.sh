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
# CE QU'IL NE VOIT PAS, et qu'il faut savoir : les modifications non COMMITÉES. Un
# fichier édité à la main sur le VPS sans commit sera toujours écrasé par le reset —
# sauf .claude/settings.json, que update.sh met de côté à part. Un garde-fou qui
# laisserait croire qu'il protège tout serait pire que pas de garde-fou.
set -uo pipefail

BRANCHE="${1:?usage: verifier_avant_reset.sh <branche>}"

# Commits présents ici et absents de GitHub. Si la référence distante n'existe pas
# encore (premier déploiement), il n'y a rien à perdre : on laisse passer.
if ! git rev-parse --verify --quiet "origin/$BRANCHE" >/dev/null; then
  exit 0
fi
AVANCE="$(git rev-list --count "origin/$BRANCHE..HEAD" 2>/dev/null || echo 0)"

if [ "$AVANCE" -eq 0 ]; then
  exit 0
fi

if [ "${DEPLOY_ABANDONNER_LOCAL:-}" = "1" ]; then
  echo "⚠️  $AVANCE commit(s) local(aux) vont être ABANDONNÉS (DEPLOY_ABANDONNER_LOCAL=1)."
  exit 0
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
