#!/usr/bin/env bash
# Déploiement / mise à jour du backoffice Agenda sur le VPS.
# Récupère la dernière version du code (branche canonique forcée), met à jour les
# dépendances, puis redémarre le service systemd.
#
# Usage :
#   bash deploy.sh                 # pull + deps + restart service
#   DEPLOY_BRANCH=... bash deploy.sh
set -euo pipefail

cd "$(dirname "$0")"

# 1) Mise à jour du code — on FORCE toujours la branche canonique --------------
# (Les secrets/données — .env, config/credentials.json, config/token.json, data/,
#  logs/ — ne sont pas suivis par git, donc intacts. Seul le CODE est réécrit ;
#  sa source de vérité est GitHub.)
BRANCH="${DEPLOY_BRANCH:-claude/quirky-davinci-jvqrnw}"
echo "==> Mise à jour du code (branche forcée : $BRANCH)"
git fetch origin "$BRANCH"
git checkout -B "$BRANCH" "origin/$BRANCH"
git reset --hard "origin/$BRANCH"
echo "==> Maintenant sur : $(git log --oneline -1)"

# 2) Interpréteur Python (venv si présent) ------------------------------------
if [ -x .venv/bin/python ]; then
  echo "==> Mise à jour des dépendances dans .venv"
  ./.venv/bin/pip install --quiet -r requirements.txt
else
  echo "⚠  .venv introuvable — lance d'abord :  bash install.sh"
  exit 1
fi

# 3) Redémarrage du service (si systemd présent) ------------------------------
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q '^agenda-admin'; then
  echo "==> Redémarrage du service agenda-admin"
  sudo systemctl restart agenda-admin
  sudo systemctl --no-pager status agenda-admin | head -5
else
  echo "ℹ  Service agenda-admin non installé — voir docs/DEPLOIEMENT_HOSTINGER.md."
fi

echo ""
echo "✅ Déploiement terminé. Le cron existant prend le relais (collecte + évaluation)."
