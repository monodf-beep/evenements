#!/usr/bin/env bash
# Déploie du code WordPress (mu-plugins) vers le serveur OVH d'agendasabauda.eu par
# SFTP/SCP, depuis le VPS. Remplace le collage manuel de snippets : un mu-plugin déposé
# ici est actif immédiatement, sans wp-admin, sans risque de 403.
#
# CONFIG (dans .env du projet) :
#   WP_DEPLOY_SSH=user@host          # identifiant SFTP OVH (ex. monsite@ssh.cluster0XX.hosting.ovh.net)
#   WP_DEPLOY_PORT=22                # port SSH/SFTP (OVH mutualisé : souvent 22)
#   WP_DEPLOY_MU_DIR=www/wp-content/mu-plugins   # chemin du dossier mu-plugins (relatif au home SFTP, ou absolu)
#
# AUTH : idéalement une CLÉ SSH (déploiement sans mot de passe — voir le README plus bas).
# À défaut, sftp demandera le mot de passe de façon interactive.
#
# USAGE :
#   deploy/push-wordpress.sh                       # pousse deploy/wordpress/cs-polylang.php
#   deploy/push-wordpress.sh fichier1.php f2.php   # pousse ces fichiers (chemins ou basenames dans deploy/wordpress/)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Lit UNE clé du .env sans « sourcer » tout le fichier : un `. .env` casse dès qu'une
# valeur contient un espace non quoté (ex. « line 40: Sabaudo: command not found »).
# On extrait seulement les clés dont on a besoin, guillemets éventuels retirés.
read_env() {
  local line
  line=$(grep -E "^[[:space:]]*$1=" "$ROOT/.env" 2>/dev/null | tail -1) || return 0
  line="${line#*=}"
  line="${line%\"}"; line="${line#\"}"
  line="${line%\'}"; line="${line#\'}"
  printf '%s' "$line"
}
[ -f "$ROOT/.env" ] && {
  WP_DEPLOY_SSH="${WP_DEPLOY_SSH:-$(read_env WP_DEPLOY_SSH)}"
  WP_DEPLOY_MU_DIR="${WP_DEPLOY_MU_DIR:-$(read_env WP_DEPLOY_MU_DIR)}"
  WP_DEPLOY_PORT="${WP_DEPLOY_PORT:-$(read_env WP_DEPLOY_PORT)}"
}

: "${WP_DEPLOY_SSH:?Manque WP_DEPLOY_SSH=user@host dans .env}"
: "${WP_DEPLOY_MU_DIR:?Manque WP_DEPLOY_MU_DIR=chemin/vers/wp-content/mu-plugins dans .env}"
PORT="${WP_DEPLOY_PORT:-22}"

# Fichiers à pousser : args (basename résolu dans deploy/wordpress/ si non trouvé tel quel),
# sinon le mu-plugin Polylang par défaut.
FILES=()
if [ "$#" -eq 0 ]; then
  FILES=("$ROOT/deploy/wordpress/cs-polylang.php")
else
  for a in "$@"; do
    if [ -f "$a" ]; then FILES+=("$a")
    elif [ -f "$ROOT/deploy/wordpress/$a" ]; then FILES+=("$ROOT/deploy/wordpress/$a")
    else echo "❌ Fichier introuvable : $a" >&2; exit 2; fi
  done
fi

for f in "${FILES[@]}"; do
  [ -f "$f" ] || { echo "❌ Introuvable : $f" >&2; exit 2; }
done

echo "→ Cible : $WP_DEPLOY_SSH:$WP_DEPLOY_MU_DIR (port $PORT)"
echo "→ Fichiers : ${FILES[*]##*/}"

# On passe par SFTP (compatible OVH mutualisé où le shell SSH est parfois désactivé mais
# le sous-système SFTP actif). « -mkdir » (préfixe '-') ignore l'erreur si le dossier existe.
CMDS="-mkdir \"$WP_DEPLOY_MU_DIR\"\n"
for f in "${FILES[@]}"; do
  CMDS+="put \"$f\" \"$WP_DEPLOY_MU_DIR/\"\n"
done

# Sans clé SSH, sftp -b échoue (batch = pas de mot de passe). On tente d'abord en batch
# (clé) ; si ça échoue, on rejoue en interactif (sftp lit le mot de passe sur le terminal).
if printf "%b" "$CMDS" | sftp -oBatchMode=yes -P "$PORT" "$WP_DEPLOY_SSH" >/dev/null 2>&1; then
  echo "✅ Déployé (clé SSH)."
else
  echo "ℹ️  Pas de clé SSH utilisable — connexion interactive (mot de passe demandé)."
  printf "%b" "$CMDS" | sftp -P "$PORT" "$WP_DEPLOY_SSH"
  echo "✅ Déployé."
fi

echo
echo "Vérifie la route :  curl -s https://agendasabauda.eu/wp-json/cs/v1 | grep link-translations"
