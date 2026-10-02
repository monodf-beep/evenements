#!/usr/bin/env bash
# Renvoi vers LE script de déploiement : deploy/update.sh
#
# CE FICHIER NE DÉPLOIE PLUS LUI-MÊME (2026-08-31, audit de simplification). Il portait
# 48 lignes qui faisaient le même travail que `deploy/update.sh` — fetch, branche forcée,
# `git reset --hard`, dépendances, redémarrage — À UNE DIFFÉRENCE PRÈS, et elle coûtait
# cher : il ne préservait PAS `.claude/settings.json`.
#
# Cette protection a été ajoutée à `deploy/update.sh` le 2026-08-11 après un incident
# réel : Franck avait posé ses permissions d'autonomie à 18h30, le déploiement de 18h45
# les a effacées en silence, la seule trace étant un « M .claude/settings.json » noyé dans
# la sortie de git. `deploy.sh` rejouait cet incident à l'identique — et
# `docs/DEPLOIEMENT_HOSTINGER.md` envoyait le lecteur ICI, pas vers l'autre.
#
# Rien d'automatique ne l'appelait (vérifié : ni install.sh, ni nginx.conf, ni deploy/,
# ni le crontab). Plutôt que de le supprimer — un document et une habitude pointaient
# dessus — il délègue : la commande continue de marcher, en faisant la bonne chose.
#
# CLAUDE.md, l. 288 : « Déployer sur le VPS, c'est `bash deploy/update.sh` ».
set -euo pipefail

echo "→ deploy.sh délègue à deploy/update.sh (le seul qui préserve .claude/settings.json)."
exec bash "$(dirname "$0")/deploy/update.sh" "$@"
