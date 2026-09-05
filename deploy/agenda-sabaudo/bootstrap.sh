#!/usr/bin/env bash
# =============================================================================
# bootstrap.sh — Config WordPress d'Agenda Sabauda en une passe (OVH Pro, SSH).
#
# Fait, via WP-CLI, ce que ni l'API REST ni un MCP ne savent faire :
#   - installe wp-cli.phar si absent (OVH mutualisé ne l'a pas préinstallé) ;
#   - garantit les 3 extensions actives (TEC, Rank Math, Polylang) ;
#   - pose les PERMALIENS (/%postname%/) ;
#   - pose les slugs d'URL de The Events Calendar (evenement / evenements) ;
#   - dépose les mu-plugins (territoire, seed-catégories, noindex, + pont REST) ;
#   - purge les règles de réécriture ;
#   - VÉRIFIE et affiche l'état final.
#
# Idempotent : relançable sans risque (ne réinstalle pas ce qui est déjà là).
# NE TOUCHE PAS à la base de contenu (aucun événement/fiche modifié).
#
# ── UTILISATION (sur le VPS/hébergement OVH, en SSH) ─────────────────────────
#   1. Récupère le dossier deploy/ sur l'hébergement (SFTP ou git).
#   2. cd dans deploy/agenda-sabaudo/
#   3. (si besoin) export WP_PATH="/home/xxx/agendasabauda"   # docroot du site
#      (si besoin) export PHP_BIN="php8.2"                    # binaire PHP CLI OVH
#   4. bash bootstrap.sh
#   5. Colle-moi la sortie : on ajuste si un chemin/une option diffère.
# =============================================================================

set -uo pipefail   # -u : variables non définies = erreur ; pas de -e (on gère les erreurs à la main)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHP_BIN="${PHP_BIN:-php}"
WP_CLI="${WP_CLI:-$HOME/wp-cli.phar}"

say()  { printf '\n\033[1;34m▶ %s\033[0m\n' "$*"; }
ok()   { printf '  \033[1;32m✓ %s\033[0m\n' "$*"; }
warn() { printf '  \033[1;33m! %s\033[0m\n' "$*"; }

# --- 1. Localiser l'installation WordPress -----------------------------------
say "Localisation de WordPress"
if [ -z "${WP_PATH:-}" ]; then
  for d in "$HOME/agendasabauda" "$SCRIPT_DIR" "$PWD"; do
    if [ -f "$d/wp-config.php" ]; then WP_PATH="$d"; break; fi
  done
fi
if [ -z "${WP_PATH:-}" ] || [ ! -f "$WP_PATH/wp-config.php" ]; then
  warn "wp-config.php introuvable. Relance avec : export WP_PATH=\"/chemin/vers/agendasabauda\""
  exit 1
fi
ok "WP_PATH = $WP_PATH"

# --- 2. Installer wp-cli.phar si absent --------------------------------------
say "WP-CLI"
if [ ! -f "$WP_CLI" ]; then
  warn "wp-cli.phar absent → téléchargement…"
  curl -sSLo "$WP_CLI" https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar \
    && ok "téléchargé dans $WP_CLI" || { warn "échec du téléchargement de WP-CLI"; exit 1; }
fi
wp() { "$PHP_BIN" "$WP_CLI" --path="$WP_PATH" "$@"; }
if ! wp core version >/dev/null 2>&1; then
  warn "WP-CLI ne joint pas WordPress. Vérifie PHP_BIN (ex. php8.2) et WP_PATH."
  warn "PHP utilisé : $("$PHP_BIN" -v 2>/dev/null | head -1)"
  exit 1
fi
ok "WordPress $(wp core version) piloté par WP-CLI ($("$PHP_BIN" -r 'echo PHP_VERSION;'))"

# --- 3. Extensions (idempotent : n'installe que si absent) --------------------
say "Extensions"
for slug in the-events-calendar seo-by-rank-math polylang; do
  if wp plugin is-installed "$slug" >/dev/null 2>&1; then
    wp plugin activate "$slug" >/dev/null 2>&1 && ok "$slug actif"
  else
    wp plugin install "$slug" --activate >/dev/null 2>&1 && ok "$slug installé + activé" \
      || warn "$slug : install impossible (DISALLOW_FILE_MODS ? déjà présent sous un autre slug ?)"
  fi
done

# --- 4. Permaliens -----------------------------------------------------------
say "Permaliens"
wp rewrite structure '/%postname%/' --hard >/dev/null 2>&1 && ok "structure = /%postname%/"

# --- 5. Slugs The Events Calendar --------------------------------------------
say "Slugs The Events Calendar"
if wp option get tribe_events_calendar_options >/dev/null 2>&1; then
  wp option patch update tribe_events_calendar_options eventsSlug evenements >/dev/null 2>&1 && ok "base d'archive = evenements"
  wp option patch update tribe_events_calendar_options singleEventSlug evenement >/dev/null 2>&1 && ok "événement = evenement"
else
  warn "options TEC absentes (ouvre une fois Évènements → Réglages pour les initialiser, puis relance)"
fi
# NB : slug des lieux (« luoghi ») = via mu-plugin/filtre, pas une option → traité à part.

# --- 6. Déposer les mu-plugins ------------------------------------------------
say "mu-plugins"
MU_DIR="$WP_PATH/wp-content/mu-plugins"
mkdir -p "$MU_DIR"
# On ne dépose QUE les mu-plugins de lancement (as-*.php). Les mu-plugins du pont
# backoffice→WP (cs-rest-auth / cs-seo-meta) demandent un secret configuré →
# déposés plus tard, à la phase « publisher ».
for f in "$SCRIPT_DIR"/as-*.php; do
  [ -f "$f" ] || continue
  cp -f "$f" "$MU_DIR/" && ok "déposé : $(basename "$f")"
done

# --- 7. Purge des règles de réécriture (après slugs + taxonomies mu-plugins) --
say "Flush des réécritures"
wp rewrite flush --hard >/dev/null 2>&1 && ok "règles régénérées"

# --- 8. Vérification ----------------------------------------------------------
say "Vérification"
echo "  Extensions actives :"
wp plugin list --status=active --field=name 2>/dev/null | sed 's/^/    - /'
echo "  Structure de permaliens : $(wp option get permalink_structure 2>/dev/null)"
echo "  Catégories d'événements (attendu : 11) : $(wp term list tribe_events_cat --format=count 2>/dev/null || echo '?')"
echo "  Territoires (attendu : 4 + villes)       : $(wp term list territoire --format=count 2>/dev/null || echo '? (taxo pas encore chargée)')"
echo "  mu-plugins présents :"
ls -1 "$MU_DIR" 2>/dev/null | sed 's/^/    - /'

say "Terminé. Colle-moi cette sortie — on ajuste ce qui a un ! (avertissement)."
echo "Restent MANUELS (non couverts par ce script) : assistant Rank Math (schéma unique + IndexNow),"
echo "langues Polylang FR/IT + hreflang, slug 'luoghi' des lieux, robots.txt, Google Search Console."
