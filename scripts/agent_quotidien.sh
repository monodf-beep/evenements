#!/usr/bin/env bash
# Agent quotidien — 9h45, après la datation et la moisson, avant le lot de 9h30… non :
# après TOUT le pipeline du matin, pour travailler sur ce qui reste vraiment.
#
# POURQUOI IL EXISTE. Franck, 2026-08-11 : « je veux que tu sois le plus autonome possible !
# avec claude dans le vps donne tous les droits, on a assez mis de règles pour pas avoir de
# surprise ». Il a raison sur le constat : la file « À compléter » est passée de 68 à 30 ce
# jour-là, et l'essentiel du gain n'est venu d'AUCUN cron — il est venu d'ouvrir les pages
# une par une et de lire. C'est précisément ce qu'un agent sait faire et qu'un script ne
# saura jamais faire.
#
# CE QU'IL PEUT ÉCRIRE, ET PAR OÙ. Il ne touche pas à SQLite. Il dépose ses trouvailles
# dans un JSON et appelle `scripts/completer_verifie.py --depuis`, qui porte tous les
# garde-fous : n'écrase aucun champ rempli, exige une source, refuse toute colonne autre
# que lieu / ville / dates / url_officiel, recompte après écriture. Un agent qui écrirait
# lui-même pourrait se tromper de colonne ou effacer une correction faite à la main la
# veille ; ici il ne peut que PROPOSER, dans un format vérifiable.
#
# LES INTERDITS NE SONT PAS DANS CE FICHIER, ils sont dans .claude/settings.json — la liste
# « irréversible » de CLAUDE.md : rm -rf, git push --force, git reset --hard, DELETE FROM,
# DROP TABLE, force=true sur wp/v2, lecture du .env. « Tous les droits » veut dire tous les
# droits sur ce qui se DÉFAIT ; ces sept-là ne se défont pas, et les garder fermés est ce
# qui rend le reste possible.
#
# Mêmes verrous de cron que scripts/revue_hebdo.sh : --strict-mcp-config sans --mcp-config,
# sinon le cron hériterait des connecteurs de la session, dont plusieurs savent publier.
set -uo pipefail

cd /root/evenements || exit 1

JOURNAL="logs/agent_quotidien.log"
CLAUDE="/root/.local/bin/claude"

# Lecture, réseau, et l'écriture PAR LA PORTE PRÉVUE. WebFetch est l'outil central : c'est
# lui qui ouvre les pages des organisateurs. Write est autorisé parce que l'agent doit
# déposer son JSON de valeurs — et `logs/` est le seul endroit où la consigne l'y invite.
OUTILS=(
  Read Glob Grep Write WebFetch WebSearch
  "Bash(.venv/bin/python:*)"
  "Bash(python3:*)"
  "Bash(git log:*)"
  "Bash(git status:*)"
  "Bash(cat:*)"
  "Bash(ls:*)"
  "Bash(head:*)"
  "Bash(tail:*)"
  "Bash(grep:*)"
  "Bash(wc:*)"
)
# Edit interdit : l'agent ne modifie pas le code du dépôt. Un correctif écrit la nuit sans
# relecture, sur un dépôt en production, est l'automatisme que Franck refuse — « on ne doit
# pas faire des choses automatiques pour faire des choses automatiques sans réfléchir ».
# Il DÉCRIT ce qu'il voit dans son compte rendu, et le geste reste humain.
INTERDITS=(Edit NotebookEdit)

echo "=== $(date '+%Y-%m-%d %H:%M:%S') — agent quotidien ===" >> "$JOURNAL"

COMPTE_RENDU="$("$CLAUDE" -p "$(cat config/consigne_agent_quotidien.txt)" \
  --allowedTools "${OUTILS[@]}" \
  --disallowedTools "${INTERDITS[@]}" \
  --strict-mcp-config \
  2>> "$JOURNAL")"
CODE=$?

if [ $CODE -ne 0 ]; then
  # Un échec silencieux serait le pire cas : personne ne remarque l'absence d'un message,
  # et c'est justement ce chien de garde qui doit signaler ce qui passe inaperçu. Le
  # plafond d'API (jusqu'au 2026-09-01) fait partie des causes attendues.
  echo "claude -p a échoué (code $CODE)" >> "$JOURNAL"
  printf '%s\n' "⚠️ L'agent quotidien n'a pas pu tourner (claude -p, code $CODE). Voir logs/agent_quotidien.log." \
    | .venv/bin/python scripts/slack_send.py
  exit $CODE
fi

printf '%s\n' "$COMPTE_RENDU" >> "$JOURNAL"
printf '%s\n' "$COMPTE_RENDU" | .venv/bin/python scripts/slack_send.py \
  --prefixe "🤖 *Agent quotidien — $(date '+%d/%m')*"
