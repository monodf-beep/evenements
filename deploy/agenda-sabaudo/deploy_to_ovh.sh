#!/usr/bin/env bash
# =============================================================================
# deploy_to_ovh.sh — DEPUIS LE VPS : pousse les mu-plugins + bootstrap.sh sur
# l'hébergement OVH et lance la config WP-CLI à distance, en une commande.
#
# Le VPS a déjà le dépôt (le backoffice tourne dessus). Ce script fait le pont
# VPS → OVH : envoi des fichiers (scp) puis exécution de bootstrap.sh (ssh).
#
# ── UTILISATION (sur le VPS) ─────────────────────────────────────────────────
#   1. Mets le dépôt à jour :
#        cd /root/evenements && git fetch origin claude/quirky-davinci-jvqrnw \
#          && git checkout claude/quirky-davinci-jvqrnw \
#          && git reset --hard origin/claude/quirky-davinci-jvqrnw
#   2. Récupère ton accès SSH OVH (Manager OVH → hébergement → onglet FTP-SSH) :
#        export OVH_SSH="TON_LOGIN@ssh.clusterXXX.hosting.ovh.net"
#      (optionnel) export OVH_WP_PATH="/home/xxx/agendasabauda"   # sinon auto-détecté
#      (optionnel) export OVH_PHP_BIN="php8.2"                     # si la CLI PHP est ancienne
#   3. bash deploy/agenda-sabaudo/deploy_to_ovh.sh
#      → il te demandera le MOT DE PASSE SSH OVH (2 fois : scp puis ssh),
#        sauf si tu as posé une clé VPS→OVH. Normal.
#   4. Colle-moi la sortie.
# =============================================================================

set -uo pipefail

: "${OVH_SSH:?Définis d'abord : export OVH_SSH=\"login@ssh.clusterXXX.hosting.ovh.net\"}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_DIR="deploy-agenda-sabaudo"

echo "▶ Envoi des fichiers vers ${OVH_SSH}:~/${REMOTE_DIR}/ …"
ssh "$OVH_SSH" "mkdir -p ~/${REMOTE_DIR}" \
  || { echo "! Connexion SSH OVH impossible — vérifie OVH_SSH et que le SSH est activé (offre Pro)."; exit 1; }
scp "$SCRIPT_DIR"/bootstrap.sh "$SCRIPT_DIR"/as-*.php "$OVH_SSH":"${REMOTE_DIR}/" \
  || { echo "! Échec du transfert scp."; exit 1; }
echo "  ✓ fichiers transférés"

echo "▶ Exécution de bootstrap.sh sur OVH …"
ssh "$OVH_SSH" "cd ~/${REMOTE_DIR} && WP_PATH='${OVH_WP_PATH:-}' PHP_BIN='${OVH_PHP_BIN:-php}' bash bootstrap.sh"

echo "▶ Terminé. Colle-moi la sortie ci-dessus."
