#!/usr/bin/env bash
# Inventaire du code WordPress réel — LANCEMENT MANUEL UNIQUEMENT, jamais en crontab.
#
# D'OÙ ÇA VIENT — docs/DEPLOIEMENT_WORDPRESS.md §4 : le 2026-08-12, le dépôt et la
# production avaient divergé dans les DEUX sens (du code tournait en ligne sans être ici,
# du code était ici sans tourner en ligne). CLAUDE.md le confirme : 34 mu-plugins `cs-*`
# en ligne, 18 seulement ont leur double dans ce dépôt. Avant de modifier quoi que ce
# soit côté WordPress, établir OÙ le code vit — règle 1, transposée au code.
#
# ⚠️ PAS DE CRON POUR CE SCRIPT, ET C'EST DÉLIBÉRÉ. bilan_matin.sh et cerveau.sh bornent
# leur agent par --allowedTools/--disallowedTools AU NIVEAU DE L'OUTIL : Write et Edit y
# sont interdits par la CLI elle-même, aucune formulation de consigne ne peut contourner
# ça. Novamira n'offre pas cette granularité : `novamira/execute-php` EST la capacité
# d'écrire (exécuter du PHP arbitraire), il n'existe pas d'ability « lecture seule ». La
# frontière lecture/écriture ne peut donc reposer QUE sur la consigne — un texte, pas un
# verrou. C'est un niveau de confiance différent, et plus haut, que les deux autres
# agents autonomes de ce dépôt : jamais laissé tourner sans un humain qui lit la sortie.
#
# Usage (à la main, sur le VPS, session ayant Novamira connecté) :
#   scripts/audit_wp_code.sh
set -uo pipefail

cd /root/evenements || exit 1

CLAUDE="/root/.local/bin/claude"

echo "⚠️  Cet audit LIT WordPress via Novamira (novamira/execute-php). Sa consigne"
echo "    (config/consigne_audit_wp_code.txt) interdit toute écriture — mais rien au"
echo "    niveau outil ne peut le garantir mécaniquement, contrairement au cerveau ou"
echo "    au bilan. Lire la sortie avant d'en tirer une conclusion."
echo

"$CLAUDE" -p "$(cat config/consigne_audit_wp_code.txt)"
