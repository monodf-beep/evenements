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
# LA CONFIG DE L'OPÉRATEUR SURVIT AU DÉPLOIEMENT (2026-08-11). `git reset --hard` annule
# toute modification locale d'un fichier SUIVI — et .claude/settings.json en est un. Franck
# avait installé ses permissions d'autonomie à 18h30 ; le déploiement de 18h45 les a
# effacées en silence, la seule trace étant un « M .claude/settings.json » noyé dans la
# sortie de git. Un script de déploiement n'a pas à défaire une décision d'exploitation.
#
# On met donc ce fichier de côté avant le reset et on le remet après, s'il différait. Le
# contenu n'est PAS choisi ici : c'est celui que l'opérateur a posé, quel qu'il soit.
CONF_LOCALE=""
if ! git diff --quiet -- .claude/settings.json 2>/dev/null; then
  CONF_LOCALE="$(mktemp)"
  cp .claude/settings.json "$CONF_LOCALE"
fi
git reset --hard "origin/$BRANCH"
if [ -n "$CONF_LOCALE" ]; then
  cp "$CONF_LOCALE" .claude/settings.json
  rm -f "$CONF_LOCALE"
  echo "→ .claude/settings.json : votre version locale a été conservée."
fi

echo "→ Dépendances Python…"
.venv/bin/pip install -q -r requirements.txt

echo "→ Redémarrage du service $SERVICE…"
systemctl restart "$SERVICE"
sleep 1
systemctl --no-pager --lines=0 status "$SERVICE" || true

echo "✅ Déploiement terminé ($(git rev-parse --short HEAD))."
