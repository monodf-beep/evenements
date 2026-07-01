#!/usr/bin/env bash
# Déploiement en UNE commande sur le VPS.
#
# Usage (sur le VPS, dans le dossier du projet) :
#   bash deploy/update.sh
#
# Récupère la dernière version de la branche, installe les dépendances, applique
# les migrations de base (au redémarrage du service) et redémarre le backoffice.
# Sans risque pour les secrets : .env, config/credentials.json, config/token.json
# et data/ sont gitignorés → jamais écrasés.
set -euo pipefail

BRANCH="${DEPLOY_BRANCH:-claude/quirky-davinci-jvqrnw}"
SERVICE="${DEPLOY_SERVICE:-agenda-admin}"
cd "$(dirname "$0")/.."

echo "→ Récupération de origin/$BRANCH…"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "→ Dépendances Python…"
.venv/bin/pip install -q -r requirements.txt

echo "→ Redémarrage du service $SERVICE…"
systemctl restart "$SERVICE"
sleep 1
systemctl --no-pager --lines=0 status "$SERVICE" || true

echo "✅ Déploiement terminé ($(git rev-parse --short HEAD))."
