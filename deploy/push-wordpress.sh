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
# USAGE — la liste des fichiers est OBLIGATOIRE (voir plus bas pourquoi) :
#   deploy/push-wordpress.sh cs-publish.php        # un fichier de deploy/wordpress/
#   deploy/push-wordpress.sh f1.php f2.php         # plusieurs (chemins ou basenames)
#   deploy/push-wordpress.sh                       # refuse, et liste ce qui est disponible
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

# Fichiers à pousser : args (basename résolu dans deploy/wordpress/ si non trouvé tel
# quel). Aucun défaut — voir le refus ci-dessous.
FILES=()
if [ "$#" -eq 0 ]; then
  # PAS DE DÉFAUT. Il y en avait un — cs-polylang.php — et il a coûté un déploiement le
  # 2026-08-12 : on m'a demandé de pousser le correctif de cs-publish.php, la commande a
  # été lancée sans argument, et le script a annoncé « Fichiers : cs-polylang.php ». Le
  # bon fichier n'est jamais parti, et un AUTRE partait à sa place — celui-là même dont
  # on ne voulait pas toucher la version en ligne.
  #
  # Un défaut qui envoie un fichier que personne n'a demandé sur un site en production
  # n'est pas une commodité : c'est un piège, et il est silencieux. On exige donc la
  # liste, et on l'affiche pour qu'elle se compose sans aller la chercher ailleurs.
  echo "Rien à pousser : nomme les fichiers à envoyer." >&2
  echo >&2
  echo "  bash deploy/push-wordpress.sh cs-publish.php" >&2
  echo >&2
  echo "Disponibles dans deploy/wordpress/ :" >&2
  for f in "$ROOT"/deploy/wordpress/*.php; do echo "  · $(basename "$f")" >&2; done
  exit 2
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

# ── Contrôle de syntaxe AVANT d'envoyer ─────────────────────────────────────────
# 2026-08-08 → 2026-08-10 : le site est resté injoignable DEUX JOURS (front, wp-admin
# et API REST en 500 simultanément) pour une seule ligne fautive dans un mu-plugin :
#   Parse error: syntax error, unexpected token "===" ... cs-source-garde.php on line 20
# Un mu-plugin se charge avant tout le reste : une faute de syntaxe y tue aussi la porte
# qui permettrait de la réparer. Il a fallu du FTP pour revenir en arrière.
# D'où ce portillon, qui BLOQUE l'envoi — c'est le seul moment où l'erreur coûte encore
# zéro. Un fichier refusé se corrige puis se repousse : ce n'est pas un cul-de-sac.
if command -v php >/dev/null 2>&1; then
  for f in "${FILES[@]}"; do
    if ! out=$(php -d display_errors=1 -l "$f" 2>&1); then
      echo "❌ Syntaxe PHP invalide, RIEN n'a été envoyé :" >&2
      echo "   $out" >&2
      exit 3
    fi
  done
  echo "→ Syntaxe : ${#FILES[@]} fichier(s) validé(s) par php -l"
else
  # Le VPS n'héberge pas WordPress et n'a donc pas de PHP : on ne peut pas vérifier
  # ici. On le DIT au lieu de laisser croire que le contrôle a eu lieu (règle 6).
  echo "⚠️  Aucun binaire \`php\` : la syntaxe n'a PAS été vérifiée avant l'envoi." >&2
  echo "    Pour l'obtenir :  sudo apt install -y php-cli" >&2
  echo "    Sinon, depuis une machine qui a PHP :  python -m tests.test_php_syntax" >&2
fi

echo "→ Cible : $WP_DEPLOY_SSH:$WP_DEPLOY_MU_DIR (port $PORT)"
echo "→ Fichiers : ${FILES[*]##*/}"

# On passe par SFTP (compatible OVH mutualisé où le shell SSH est parfois désactivé mais
# le sous-système SFTP actif). « -mkdir » (préfixe '-') ignore l'erreur si le dossier existe.
CMDS="-mkdir \"$WP_DEPLOY_MU_DIR\"\n"
for f in "${FILES[@]}"; do
  CMDS+="put \"$f\" \"$WP_DEPLOY_MU_DIR/\"\n"
done

# Deux transports, et le second n'est pas un luxe : le 2026-08-12, SFTP a été refusé deux
# fois de suite par OVH — « Connection closed by 54.36.142.132 port 22 », juste après le
# mot de passe. Sur un hébergement mutualisé, le port 22 n'est ouvert que si SSH a été
# activé dans le manager ; FTPS (port 21) l'est toujours pour le compte FTP principal.
# On tente donc SFTP par clé, puis FTPS, avant de renoncer.
if printf "%b" "$CMDS" | sftp -oBatchMode=yes -P "$PORT" "$WP_DEPLOY_SSH" >/dev/null 2>&1; then
  echo "✅ Envoyé par SFTP (clé SSH)."
else
  echo "ℹ️  SFTP par clé indisponible sur $WP_DEPLOY_SSH."
  # ON FRAPPAIT À LA MAUVAISE PORTE. Le .env porte l'hôte FTP (« ftp.cluster100… »),
  # alors qu'OVH expose SSH sur « ssh.cluster100… » : le port 22 de l'hôte FTP est
  # fermé, celui de l'hôte SSH ne l'est pas forcément. On tente donc la variante avant
  # de renoncer — une lettre d'écart, deux jours d'attente possibles.
  HOTE_SSH=""
  case "$WP_DEPLOY_SSH" in
    *@ftp.*) HOTE_SSH="${WP_DEPLOY_SSH/@ftp./@ssh.}" ;;
  esac
  DEPOSE=0
  if [ -n "$HOTE_SSH" ]; then
    echo "→ Essai sur $HOTE_SSH (mot de passe demandé ; Ctrl-C pour passer)."
    if printf "%b" "$CMDS" | sftp -P "$PORT" "$HOTE_SSH"; then
      echo "✅ Envoyé par SFTP sur l'hôte ssh.*"
      echo "   ⚠️  Corrige .env : WP_DEPLOY_SSH=$HOTE_SSH — sinon on repassera par"
      echo "      l'hôte FTP au prochain déploiement, et on rejouera cet échec."
      DEPOSE=1
    else
      echo "ℹ️  L'hôte ssh.* refuse aussi — bascule sur FTPS."
    fi
  fi
  PY="$ROOT/.venv/bin/python"; [ -x "$PY" ] || PY="python3"
  if [ "$DEPOSE" -eq 0 ] && ! "$PY" "$ROOT/deploy/push_ftp.py" "${FILES[@]}"; then
    echo >&2
    echo "❌ Ni SFTP ni FTPS n'ont abouti — RIEN n'est parti." >&2
    echo "   Deux issues, dans cet ordre :" >&2
    echo "   1. activer SSH sur l'hébergement dans le manager OVH (rubrique FTP-SSH) ;" >&2
    echo "   2. si le serveur refuse TLS sous les deux orthographes, en dernier" >&2
    echo "      recours et en connaissance de cause :" >&2
    echo "      .venv/bin/python deploy/push_ftp.py --clair ${FILES[*]##*/}" >&2
    echo "      (mot de passe en clair sur le réseau — il ouvre TOUT le site) ;" >&2
    echo "   3. à défaut, coller le contenu du fichier dans Code Snippets (wp-admin)," >&2
    echo "      SANS la ligne « <?php » — c'est l'installation B du fichier lui-même." >&2
    exit 4
  fi
fi

# ON NE DIT PAS « DÉPLOYÉ », ON DIT COMMENT LE VÉRIFIER. sftp n'interrompt pas la session
# quand un `put` isolé est refusé : il rendait donc un code 0 sur lequel ce script
# annonçait un succès. Un fichier sur le disque ne prouve de toute façon rien sur ce que
# WordPress EXÉCUTE (règle 1) — seule la route ci-dessous le dit.
echo
echo "VÉRIFIE ce que le site exécute vraiment :"
echo "  curl -s https://agendasabauda.eu/wp-json/cs/v1/version"
echo "Elle doit renvoyer la version écrite en tête de deploy/wordpress/cs-publish.php :"
grep -o "CS_PUBLISH_VERSION', '[^']*'" "$ROOT/deploy/wordpress/cs-publish.php" \
  | sed "s/CS_PUBLISH_VERSION', /  attendu : /" || true
